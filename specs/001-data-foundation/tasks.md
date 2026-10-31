---
description: "Task list for 001 Data foundation (epic #5)"
---

# Tasks: Data Foundation

**Input**: Design documents from `specs/001-data-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED (issue #5 asks for one test per rule; constitution IV). Within each story,
write the tests first and confirm they fail.

**Delivery**: 2 implementation PRs, about 3–4 h in total (revised after the PR #27 review).
- **PR A** (T001–T020): store data, quality report, safe seed. `Part of #5`.
- **PR B** (T021–T033): retrieval and production seed. `Closes #5`.

**Paths**: relative to the repo root. Commands run from `backend/`. Destructive integration
tests use the `local_database_url` fixture (T005).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependency on unfinished tasks)
- **[Story]**: US1–US5 from spec.md

---

# PR A: store data, quality report, safe seed (~1h45)

## Phase 1: Setup

- [ ] T001 Update `backend/pyproject.toml`:
  - move `httpx>=0.28` to `[project] dependencies` and add `pydantic>=2.9` and `psycopg-pool>=3.2`;
  - add `[dependency-groups] etl = ["pypdf>=5"]` and `[tool.uv] default-groups = ["dev", "etl"]`;
  - add the pytest marker `voyage: calls the real Voyage API (opt-in)` and `addopts = "-m 'not voyage'"`;
  - run `uv lock`.
- [ ] T002 [P] Add a root `.gitattributes` with `challenge/** -text` and `backend/tests/fixtures/*.csv -text`. Confirm with `git ls-files --eol challenge/data/` that the CSVs keep `crlf` in the index and in the working tree.
- [ ] T003 [P] Add `etl/**` to `services.backend.functions["app/main.py"].excludeFiles` in the root `vercel.json`.
- [ ] T004 [P] Add `embeddings_model: str = "voyage-4"` and `database_url_unpooled: str | None = None` to `Settings` in `backend/app/config.py`; add `EMBEDDINGS_MODEL=voyage-4` and `DATABASE_URL_UNPOOLED=` (with a matrix comment: Neon direct URL, seed only) to `backend/.env.example`; extend `backend/tests/test_config.py`.
- [ ] T005 [P] In `backend/tests/conftest.py`, add the fixture `local_database_url`: it skips unless `DATABASE_URL` is set **and** its host is `localhost`, `127.0.0.1` or `::1`, or `ALLOW_DESTRUCTIVE_TESTS=1`.

## Phase 2: Foundational

- [ ] T006 [P] Write `backend/tests/test_text.py`, then implement `nfc()` and `normalize_for_cache()` in `backend/app/text.py` (contracts/retrieval-api.md). Cases:
  - `nfc("Ponta Pora" + "\u0303") == "Ponta Porã"`;
  - U+200B..U+200D and U+FEFF are removed;
  - `normalize_for_cache("  Posso  DEVOLVER? ") == "posso devolver?"`.
- [ ] T007 Add `async def connect(url: str) -> psycopg.AsyncConnection` (`prepare_threshold=None`, `connect_timeout=10`) to `backend/app/db.py`; make `ping()` reuse it.
- [ ] T008 Write `backend/etl/schema.sql`:
  - `CREATE EXTENSION IF NOT EXISTS vector` and `unaccent`;
  - a `DO $$ ... $$` block that creates `pt_unaccent` (copy of `portuguese`, mapping `asciiword, word, hword, hword_part, hword_asciipart, asciihword` to `unaccent, portuguese_stem`) only if `pg_ts_config` has no such config;
  - `CREATE TABLE IF NOT EXISTS embedding_cache` (data-model.md);
  - plain `CREATE TABLE` for the store tables, with every column, CHECK and FK from data-model.md: `status IN ('active','discontinued','coming_soon')`, the order status and payment enums, `discount_percent BETWEEN 1 AND 100`, `price_brl > 0`, `stock_quantity >= 0`, `quantity > 0`, and nullable `tracking_code`, `estimated_delivery` and `notes`.
- [ ] T009 Implement `backend/etl/load.py`:
  - `OWNED_TABLES` in dependency order;
  - `async def reload(conn, payload)`, one transaction that runs `SELECT pg_advisory_xact_lock(hashtext('emporio:seed'))`, applies the extension/config/cache part of the schema, runs `DROP TABLE IF EXISTS` on each owned table in reverse order (**no `CASCADE`**), runs the `CREATE TABLE` statements, and inserts the rows in PK order.
- [ ] T010 [P] Implement `backend/etl/checksums.py`: `async def table_stats(conn) -> list[tuple[str, int, str]]`, using the row count and `md5(string_agg(row_to_json(t)::text, E'\n' ORDER BY <pk>))` per owned table (excluding `embedding_cache` and the `tsv` columns).

## Phase 3: US1: Seed a clean, trustworthy store database (P1)

**Independent test**: seed twice on local; counts 9/65/25/50/20/22, identical checksums, per-rule facts.

- [ ] T011 [P] [US1] Write the fixtures as bytes from a small script (so the escapes are exact):
  - `backend/tests/fixtures/nfd_customers.csv`: one row with "Ponta Pora" + U+0303 and one with "Ponta Porã";
  - `backend/tests/fixtures/crlf_customers.csv`: CRLF line endings, last row without a trailing newline, "Ponta Porã" on a middle row and on the last row;
  - `backend/tests/fixtures/promotions_multi_active.csv`: product 90 with active 10% and 25%, and a tie case.
- [ ] T012 [P] [US1] Tests in `backend/tests/etl/test_sources.py` and `backend/tests/etl/test_models.py`.
  - **Sources**:
    - the CRLF fixture yields no value ending in `\r`; both "Ponta Porã" rows are equal and the last row is read;
    - the NFD fixture yields equal cities and an NFC-change count of 1;
    - the real `customers.csv` has exactly one distinct "Ponta Porã" (6 customers).
  - **Models**:
    - each category's specs schema accepts a real row and rejects a missing or extra key;
    - an invalid status or payment method is rejected;
    - real order 1 keeps `tracking_code="BRAB1234567BR"` and `estimated_delivery=2025-10-25`; real order 9 gets `None` for both;
    - an empty required field (e.g. `price_brl`) raises with a `file:row field` message;
    - an order item with an unknown product raises.
- [ ] T013 [P] [US1] Tests in `backend/tests/catalog/test_rules.py` and `backend/tests/etl/test_rules.py`, one per rule:
  - **availability**: 136 → `discontinued`, 113 → `discontinued`, 130 → `coming_soon`, 96 → `out_of_stock`, active with stock > 0 → `available`;
  - **promotions**: `effective_promotion` on the multi-active fixture gives 25%, and a tie goes to the lowest id. On the real data, exactly the effective promotions `{90: 18, 94: 8, 121: 20, 127: 10}`; 96 has none;
  - **price**: `promo_price(Decimal("599.90"), 18) == Decimal("491.92")`, and with 0% it equals the price;
  - **orders**: 3 (3450 vs 3498) and 20 (1400 vs 1488) are flagged and keep `total_brl`; orders 3 and 14 are `non_sellable_in_order`;
  - **products**: 135–144 have `description_trusted=False`;
  - **customers**: 11 and 43 are `shared_email`;
  - **other anomalies**: categories 6–8 are `empty_category`; all 20 orders are `missing_purchase_channel`; all 25 promotions are `no_promotion_validity_dates`; exactly 3 `policy_conflict` records.
- [ ] T014 [US1] `backend/tests/etl/test_seed.py` (integration, `local_database_url`):
  - seed and check the row counts, the T013 facts in the DB (including `promo_price_brl` for 90) and the NULLs for order 9;
  - a second seed gives identical `table_stats`;
  - the `challenge/data` bytes are unchanged;
  - a validation error leaves a previously seeded DB unchanged;
  - after adding a column to `products` by hand, a reseed restores the declared shape (drop/recreate).
- [ ] T015 [P] [US1] Implement `backend/app/catalog/rules.py`: `availability`, `is_sellable`, `effective_promotion` (with a `PromotionLike` Protocol) and `promo_price` (`Decimal`, `ROUND_HALF_UP`, 2 places).
- [ ] T016 [P] [US1] Implement `backend/etl/sources.py` and `backend/etl/models.py`.
  - **Sources**: open the CSVs with `newline=""` + `csv.DictReader`, apply `nfc()` to every cell and record NFC changes.
  - **Models** (Pydantic rows, data-model.md):
    - per-category specs map;
    - `''` → `None` for `tracking_code`, `estimated_delivery` and `notes`, and an error for required fields;
    - email lowercased; phone `^\(\d{2}\) \d{4,5}-\d{4}$`;
    - `validate_dataset()` checks referential integrity and raises `ValidationFailed` with every error as `file:row field: reason`.
- [ ] T017 [US1] Implement `backend/etl/rules.py` and `backend/etl/pipeline.py`.
  - **`rules.py`**:
    - `Anomaly` dataclass and `UNTRUSTED_DESCRIPTION_IDS` (reason per ID);
    - detectors and derivations for every catalogue type in data-model.md (`items_total_brl` from current prices, `total_mismatch`, `description_trusted`, `availability`, `is_sellable`, `effective_*`, `promo_price_brl`, `email_shared`, `phone_digits`, `product_not_sellable`);
    - the 3 static `policy_conflict` records;
    - emails masked in `detail`.
  - **`pipeline.py`**: `build_payload(data_dir) -> Payload` (rows + sorted anomalies + row counts), pure, no DB.

## Phase 4: US2: Data quality report (P1)

- [ ] T018 [P] [US2] Write `backend/tests/etl/test_report.py` (renders only to `tmp_path`):
  - the summary counts equal the data-model catalogue (2, 10, 1, 2, 1, 2, 3, 4, 25, 2, 20, 0, 3, 3);
  - the DL-001 traceability table is present with every row from data-model.md;
  - each Details section starts with its description line;
  - emails are masked and no phone numbers appear;
  - **drift**: `render(build_payload(challenge/data))` equals the committed `docs/data-quality-report.md` byte for byte.
- [ ] T019 [US2] Implement `backend/etl/report.py` (`render(payload) -> str`, per contracts/data-quality-report.md). Generate and commit `docs/data-quality-report.md`.

## Phase 5: US5 (safety part): Seed any environment safely

- [ ] T020 [US5] Implement `backend/etl/__main__.py` per contracts/seed-cli.md, with tests in `backend/tests/etl/test_cli.py`.
  - **Implementation**:
    - resolve the URL (`DATABASE_URL_UNPOOLED` or `DATABASE_URL`);
    - print `target: host/db (local|remote)`;
    - refuse remote targets without `--yes`, `ENVIRONMENT=production` with the fake embedder, and a missing URL;
    - run `build_payload` → `reload` → `table_stats` → write the report;
    - exit 0/1; logs to stderr.
  - **Tests** (call `main([...])`; no DB is needed for the refusals):
    - each refusal exits 1 and prints the target without the password;
    - `--yes` with a remote host passes the guard (stop before connecting via monkeypatch).

**PR A checkpoint**: quickstart steps 1–4 pass; `ruff` and `pytest` are green in CI.

---

# PR B: retrieval and production seed (~2h)

## Phase 6: US3: Search the policy manual (P1)

- [ ] T021 [P] [US3] Tests:
  - `backend/tests/embeddings/test_fake.py`: 1024 dims, L2 norm, deterministic within the process, cos("devolver", "devolução") > cos("devolver", "garantia");
  - `backend/tests/etl/test_policies.py`:
    - headings equal the expected ToC (10 sections, 18 subsections);
    - §4.1 has title "Direito de Arrependimento (Compras Online)", parent "4", parent title "Política de Trocas e Devoluções", and its body contains "7 (sete) dias";
    - no chunk contains the page header, U+200B or cover text;
    - §2, §9 and §10 are single chunks.
- [ ] T022 [P] [US3] Test `backend/tests/embeddings/test_voyage.py`:
  - one `httpx.MockTransport` test: a 429 with `Retry-After: 1`, then 200, succeeds after about 1 s, and the batches respect the 8,000-token estimate (a long input list is split);
  - one `@pytest.mark.voyage` smoke test against the real API.
- [ ] T023 [US3] Test `backend/tests/retrieval/test_search_policies.py` (integration, fake):
  - "posso devolver meu pedido?" puts §4.1 in the top 3 **and** has `vector_rank <= 3`;
  - full-text only (embedder raising `EmbeddingsUnavailable`) still returns §4.1 for that query (any-term matching) with `mode="fulltext"`, and one warning is logged;
  - each query in the new `backend/tests/fixtures/policy_reference_queries.json` (5 queries: returns → 4.1, shipping → 5.x, installments → 3.1, warranty → 8.x, contact → 1.2 or 7) has its expected section in the top 3, and the full-text-only run returns non-empty hits (SC-005);
  - a second identical query makes zero embedder calls (counting fake);
  - seeding twice with a counting fake makes zero document embed calls on the second seed (FR-019; documents keyed by exact NFC text), and changing one chunk's text re-embeds only that chunk;
  - an `index_metadata` provider mismatch degrades with `index_provider_mismatch`;
  - `PolicyHit.breadcrumb` starts with "§4".
  - Also add `backend/tests/retrieval/test_search_policies_voyage.py` (marker `voyage`): EN and ES variants put §4.1 in the top 3.
- [ ] T024 [P] [US3] Implement `backend/app/embeddings/__init__.py` (`EMBEDDING_DIM`, `InputType`, `EmbeddingsUnavailable`, the `Embedder` Protocol, `get_embedder(settings, purpose)`) and `backend/app/embeddings/fake.py` (`FakeEmbedder`, model `fake-ngram-v1`, research R3).
- [ ] T025 [P] [US3] Implement `backend/app/embeddings/voyage.py` per research R2:
  - token-budget batching (≤ 8,000 estimated tokens, ≤ 128 inputs);
  - on 429, sleep `Retry-After` (default 20 s); up to 5 attempts per batch, 180 s in total;
  - query profile: 1 attempt, 3 s timeout;
  - the API key never appears in errors.
- [ ] T026 [US3] Implement `backend/app/embeddings/cache.py`, `embed_cached()`:
  - documents keyed by `sha256(nfc(text))`, queries by `sha256(normalize_for_cache(text))`;
  - batched lookup; embeds only the misses; `ON CONFLICT DO NOTHING`;
  - vectors passed as `'[..]'::vector` literals.
- [ ] T027 [US3] Implement `backend/etl/policies.py` (pypdf, clean-up, ToC check, chunk rules, breadcrumb `search_text`, `parent_title`). Add `policy_chunks` and `index_metadata` to `backend/etl/schema.sql` and `OWNED_TABLES`.
- [ ] T028 [US3] Implement `backend/app/db.py::get_pool()` (module-level `AsyncConnectionPool`, `min_size=0`, `max_size=4`, `open=False` then lazy `await pool.open()`, `kwargs={"prepare_threshold": None}`). Implement `backend/app/retrieval/hybrid.py` and `backend/app/retrieval/__init__.py`:
  - `PolicyHit` (with `parent_title` and `breadcrumb`), `SearchResult` and `search_policies()`;
  - one parameterized SQL query: a full-text CTE with the OR'd tsquery from research R4 and `ts_rank_cd` (top 20), a vector CTE (top 20) and RRF k=60;
  - `index_metadata` read through a 5-minute in-process cache;
  - fallback to full-text only, with one warning.
- [ ] T029 [US3] Wire the index into the ETL. In `backend/etl/__main__.py`, after `build_payload`:
  - call `get_embedder(settings, purpose="seed")` and `embed_cached` for the policy chunks, before `reload`, committed separately;
  - `reload` inserts `policy_chunks` and `index_metadata`;
  - print the `embeddings:` line.

## Phase 7: US4: Search and recommend products (P2)

- [ ] T030 [P] [US4] Tests:
  - `backend/tests/etl/test_documents.py`:
    - for each of 135–144, `search_text` contains none of its description's distinctive tokens (e.g. "Fender Jazz Bass" for 135, "88 teclas" for 142);
    - trusted products include their description;
    - specs are rendered as sorted `key: value`;
    - all 65 products get a doc;
  - `backend/tests/retrieval/test_search_products.py` (integration, fake):
    - "Yamaha C40" ranks 81 first, and the hit has `category_id=5` and `availability="available"`;
    - with `only_sellable`, no 96/113/130/136; with `category_id=5`, only violões; with `max_price`, every hit has `promo_price_brl <= max_price`; with `exclude_ids`, those IDs are absent;
    - `similar_to_product(96, only_sellable, category_id=…)` excludes 96 and the non-sellable products, returns `mode="vector"` and makes zero embedder calls (no embedder is passed).
- [ ] T031 [US4] Implement `backend/etl/documents.py` (`build_product_doc`). Add `product_search_docs` to the schema, `OWNED_TABLES`, the embed step and `reload`. Implement `ProductHit`, `ProductFilters`, `search_products()` and `similar_to_product()` in `backend/app/retrieval/` (filters join `products`; `similar_to_product` orders by `embedding <=> (SELECT embedding FROM product_search_docs WHERE product_id = %s)`).

## Phase 8: US5 (production part) and polish

- [ ] T032 [US5] Manual. Before running, add a payment method to the Voyage account (the free token allowance still applies), or accept the free-tier limit. Run quickstart step 7 against Neon (`DATABASE_URL_UNPOOLED`, `--yes`, Voyage), then record:
  - the wall time (SC-001: under 3 min);
  - that the **store-table** counts and checksums match local (excluding `policy_chunks`, `product_search_docs` and `index_metadata`);
  - that non-owned tables are unchanged.
- [ ] T033 Polish:
  - README "Data" section: the seed command, `--yes`, the env vars, and the Voyage free-tier note (3 RPM / 10K TPM; payment method needed in production);
  - a DL entry for the implementation (rules as built, any-term full-text + RRF, the pool, the review cuts);
  - run the full quickstart plus `ruff` and `pytest`; check that the fake seed takes under 30 s;
  - tick the issue #5 acceptance criteria with evidence.

---

## Dependencies & Execution Order

```text
PR A: Setup (T001–T005) → Foundational (T006–T010) → US1 (T011–T017) → US2 (T018–T019) → US5 safety (T020)
PR B: US3 (T021–T029) → US4 (T030–T031) → production seed and polish (T032–T033)
```

- PR B starts after PR A merges (it extends `schema.sql`, `load.py` and the CLI).
- Within each story: tests → pure functions/models → loader/search → CLI wiring.

## Parallel Examples

- PR A: T002 ∥ T003 ∥ T004 ∥ T005; then T011 ∥ T012 ∥ T013 (tests) and T015 ∥ T016 (implementation); T017 → T018/T019 → T020.
- PR B: T021 ∥ T022 (tests) and T024 ∥ T025; then T026 → T027 → T028 → T029; T030 → T031.

## Cut in the PR #27 review (do not re-add without a need)

`--check` mode; five exit codes; `dataset_fingerprint`; the 135–144 heuristic double-check; the
fake-embedder subprocess test; extra retry tests; the PDF regex for policy conflicts (now static
records); the cross-epic FK test; the spy embedder; the `data_anomalies` table.
