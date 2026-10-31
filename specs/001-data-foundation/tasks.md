---
description: "Task list for 001 Data foundation (epic #5)"
---

# Tasks: Data Foundation

**Input**: Design documents from `specs/001-data-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED. Issue #5 asks for one test per rule, and constitution IV requires
deterministic tests. Within each story, write the tests first and confirm they fail before
implementing.

**Paths**: all code paths are relative to the repo root. Commands run from `backend/`.
Integration tests use the existing `database_url` fixture in `backend/tests/conftest.py` (they
skip without `DATABASE_URL`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

- [ ] T001 Update `backend/pyproject.toml`:
  - move `httpx>=0.28` to `[project] dependencies` and add `pydantic>=2.9`;
  - add `[dependency-groups] etl = ["pypdf>=5"]` and `[tool.uv] default-groups = ["dev", "etl"]`;
  - add the pytest marker `voyage: calls the real Voyage API (opt-in)` and `addopts = "-m 'not voyage'"`;
  - run `uv lock`.
- [ ] T002 [P] Add `"etl/**"` to `excludeFiles` in `backend/vercel.json`.
- [ ] T003 [P] Add `embeddings_model: str = "voyage-4"` to `Settings` in `backend/app/config.py`; add `EMBEDDINGS_MODEL=voyage-4` to `backend/.env.example`; extend `backend/tests/test_config.py` for the new default.
- [ ] T004 [P] Create empty packages `backend/app/catalog/__init__.py`, `backend/app/embeddings/__init__.py`, `backend/app/retrieval/__init__.py`, `backend/etl/__init__.py`, and test dirs `backend/tests/{etl,catalog,embeddings,retrieval,fixtures}/` (with `__init__.py` where needed for pytest).

---

## Phase 2: Foundational (blocks all stories)

- [ ] T005 [P] Write `backend/tests/test_text.py`: `nfc("Ponta Porã") == "Ponta Porã"`; zero-width characters U+200B..U+200D and U+FEFF are removed; `normalize_for_cache("  Posso  DEVOLVER? ")` gives `"posso devolver?"`.
- [ ] T006 [P] Implement `nfc()` and `normalize_for_cache()` in `backend/app/text.py` per contracts/retrieval-api.md.
- [ ] T007 Add `async def connect(database_url: str) -> psycopg.AsyncConnection` to `backend/app/db.py`, using `prepare_threshold=None` and `connect_timeout=10`; make `ping()` reuse it.
- [ ] T008 Write `backend/etl/schema.sql` with idempotent DDL for **all** owned tables in data-model.md:
  - `CREATE EXTENSION IF NOT EXISTS vector` and `unaccent`;
  - the `pt_unaccent` text search config (copy of `portuguese`, mapping `asciiword, word, hword, hword_part, hword_asciipart, asciihword` to `unaccent, portuguese_stem`), created only if missing;
  - tables with the exact columns, CHECKs and FKs from data-model.md: `status IN ('active','discontinued','coming_soon')`, the order status and payment enums, `discount_percent BETWEEN 1 AND 100`, `price_brl > 0`, `stock_quantity >= 0`, `quantity > 0`;
  - generated `tsv` columns with GIN indexes;
  - `vector(1024)` columns;
  - `embedding_cache` PK `(provider, model, input_type, text_hash)`;
  - singleton `index_metadata`.
- [ ] T009 Implement `backend/etl/load.py` skeleton:
  - `OWNED_TABLES` (truncation order; `embedding_cache` excluded);
  - `async def apply_schema(conn)`;
  - `async def reload(conn, payload)`: one transaction that applies the schema, runs a single `TRUNCATE <all owned tables> RESTART IDENTITY` (**no `CASCADE`**: a foreign key from a non-owned table must make the seed fail, not empty that table), inserts in PK order and upserts `index_metadata`.
- [ ] T010 [P] Implement `backend/etl/checksums.py`: `async def table_stats(conn) -> list[tuple[str, int, str]]`, using row count and `md5(string_agg(row_to_json(t)::text, E'\n' ORDER BY <pk>))` per owned table (excluding `embedding_cache`, and excluding the `tsv` column).
- [ ] T011 [P] Implement `backend/etl/sources.py`:
  - read the CSVs with `csv.DictReader` (CRLF/LF safe, no trailing newline);
  - apply `nfc()` to every string cell;
  - record per-file/row/field which cells changed under NFC (feeds the `nfc_normalized` anomaly);
  - `dataset_fingerprint(paths)` = sha256 over sorted file bytes.
- [ ] T012 Implement the CLI skeleton in `backend/etl/__main__.py` per contracts/seed-cli.md:
  - argparse with `--data-dir`, `--report`, `--check`;
  - exit codes 0–4 via typed exceptions (`ValidationFailed`, `ConfigError`, `EmbeddingsUnavailable`, DB errors);
  - logs to stderr with the DB URL redacted to host/dbname;
  - prints the table stats.

**Checkpoint**: `uv run python -m etl --check` runs (no stages yet), and the schema applies cleanly to an empty DB.

---

## Phase 3: User Story 1: Seed a clean, trustworthy store database (P1) 🎯 MVP

**Goal**: catalog, customers, orders, items and promotions loaded with the DL-002 rules, NFC and idempotency.

**Independent test**: seed an empty DB twice; check counts (9/65/25/50/20/22), checksums and per-rule facts.

### Tests (write first, must fail)

- [ ] T013 [P] [US1] `backend/tests/catalog/test_rules.py`:
  - `availability`: `discontinued`+13 → `discontinued` (136); `discontinued`+0 → `discontinued` (113); `coming_soon` → `coming_soon` (130); `active`+0 → `out_of_stock` (96); `active`+5 → `available`;
  - `effective_promotion`: inactive only → None (96: 18% and 40% both inactive); two active 10% and 25% → 25%; tie → lowest `promotion_id`.
- [ ] T014 [P] [US1] `backend/tests/etl/test_models.py`:
  - each category's specs schema accepts a real row and rejects a missing or extra key;
  - an unknown category schema is rejected;
  - an invalid status or payment method is rejected;
  - an order item with an unknown product is rejected with a `file:row field` message.
- [ ] T015 [P] [US1] `backend/tests/etl/test_rules.py`, one test per rule:
  - order 3 (stored 3450, items 3498) and order 20 (stored 1400, items 1488) are flagged and keep the original `total_brl`;
  - 135–144 get `description_trusted=False` and everything else True; the heuristic contradiction set ⊆ `UNTRUSTED_DESCRIPTION_IDS`;
  - only active promotions apply and the max wins;
  - 113/136 are not sellable; 96 is unavailable; 130 is `coming_soon` and orders 3 and 14 are flagged `non_sellable_in_order`;
  - customers 11 and 43 are flagged `shared_email`;
  - all 20 orders are flagged `missing_purchase_channel` (one anomaly row listing every order);
  - `backend/tests/fixtures/nfd_customers.csv` (NFD and NFC "Ponta Porã") gives equal cities and `nfc_normalized` count 1;
  - categories 6, 7 and 8 are flagged `empty_category`.
- [ ] T016 [P] [US1] Create the fixtures `backend/tests/fixtures/nfd_customers.csv` (write the decomposed form with explicit `̃` bytes) and `backend/tests/fixtures/promotions_multi_active.csv`.
- [ ] T017 [US1] `backend/tests/etl/test_seed.py` (integration):
  - seed the store tables (no index tables yet; they arrive with T039 and T044); check the row counts; the facts from T015 queried from the DB; that a second run gives identical `table_stats`;
  - the dataset fingerprint of `challenge/` is the same before and after the seed (inputs read-only, FR-001);
  - a validation error leaves a previously seeded DB unchanged.

### Implementation

- [ ] T018 [P] [US1] Implement `backend/app/catalog/rules.py` per contracts/retrieval-api.md (`availability`, `is_sellable`, `effective_promotion` with a `PromotionLike` Protocol).
- [ ] T019 [P] [US1] Implement `backend/etl/models.py` with Pydantic row models:
  - `CategoryRow`, `ProductRow` (`status: Literal["active","discontinued","coming_soon"]`, `price_brl > 0`, `stock_quantity >= 0`, `specs` parsed from JSON and validated by the category → schema map in data-model.md), `PromotionRow` (`discount_percent` 1–100, `is_active` 0/1 → bool), `CustomerRow` (phone `^\(\d{2}\) \d{4,5}-\d{4}$`, email lowercased), `OrderRow` (status/payment enums from data-model.md, dates), `OrderItemRow` (`quantity > 0`);
  - `validate_dataset()` that checks referential integrity and raises `ValidationFailed` listing every error as `file:row field: reason`.
- [ ] T020 [US1] Implement `backend/etl/rules.py`:
  - an `Anomaly` dataclass (`type`, `entity`, `record_ids`, `detail`, `rule`);
  - `UNTRUSTED_DESCRIPTION_IDS` with a reason per ID, plus the verification heuristic (brand mismatch, strings/keys mismatch);
  - detectors and derivations for every catalogue type in data-model.md except `policy_conflict` (added in US3), returning enriched rows (`items_total_brl`, `total_mismatch`, `description_trusted`, `availability`, `is_sellable`, `effective_*`, `email_shared`, `phone_digits`, `product_not_sellable`) and a sorted anomaly list;
  - emails masked in `detail`.
- [ ] T021 [US1] Extend `backend/etl/load.py` to insert the store tables and `data_anomalies` from the payload in PK order.
- [ ] T022 [US1] Wire stages in `backend/etl/__main__.py`: read → validate → rules → load → stats. `--check` stops before the DB step.

**Checkpoint**: T013–T017 green; quickstart steps 1–3 pass for the store tables.

---

## Phase 4: User Story 2: Data quality report (P1)

**Goal**: a deterministic `docs/data-quality-report.md` matching DL-001.

**Independent test**: generate twice and compare byte for byte; counts match the data-model catalogue.

- [ ] T023 [P] [US2] `backend/tests/etl/test_report.py`:
  - rendering the real dataset's anomalies gives the summary counts from the data-model catalogue (2, 10, 1, 2, 1, 2, 3, 1, 1, 0, 3, and 3 once US3 lands);
  - zero-count types are listed;
  - no `@` followed by a full local part (emails masked);
  - no digits matching a phone pattern;
  - each Details section starts with the type's one-line description;
  - two renders are identical.
- [ ] T024 [US2] Implement `backend/etl/report.py` per contracts/data-quality-report.md: fixed type order, summary table, per-type details, load summary, fingerprint header, no timestamps.
- [ ] T025 [US2] Call the report after commit in `backend/etl/__main__.py` (`--report` path); then generate and commit `docs/data-quality-report.md`.

**Checkpoint**: report regenerated, `git diff` empty on a second run.

---

## Phase 5: User Story 3: Search the policy manual (P1)

**Goal**: section-level policy chunks with hybrid search, cache and full-text fallback.

**Independent test**: with the fake embedder, "posso devolver meu pedido?" puts §4.1 in the top 3; a failing embedder gives `mode="fulltext"` with results; a repeated query hits the cache.

### Tests (write first, must fail)

- [ ] T026 [P] [US3] `backend/tests/embeddings/test_fake.py`:
  - vectors have 1024 dims and are L2-normalized;
  - same input gives the same vector, also across a subprocess (stability);
  - cos("devolver", "devolução") > cos("devolver", "garantia").
- [ ] T027 [P] [US3] `backend/tests/etl/test_policies.py`:
  - the extracted headings equal the expected ToC (10 sections, 18 subsections);
  - §4.1 has title "Direito de Arrependimento (Compras Online)", parent "4", and its body contains "7 (sete) dias";
  - no chunk contains the page header, `​` or the cover text;
  - §2, §9 and §10 are single chunks;
  - the §4 intro chunk exists;
  - a corrupted ToC (fixture text with a missing heading) raises `ValidationFailed`;
  - `policy_conflict` anomalies (3) are detected.
- [ ] T028 [P] [US3] `backend/tests/embeddings/test_cache.py` (integration):
  - the first `embed_cached` call invokes a counting fake once per text; the second call invokes it zero times;
  - keys separate provider, model and input_type;
  - cache rows survive a reseed.
- [ ] T029 [P] [US3] `backend/tests/retrieval/test_search_policies.py` (integration, fake embedder):
  - §4.1 in the top 3 for "posso devolver meu pedido?";
  - an accent-less "devolucao" also finds §4.*;
  - create `backend/tests/fixtures/policy_reference_queries.json` and, for each query in it (returns → 4.1, shipping → 5.x, installments → 3.1, warranty → 8.x, WhatsApp/contact → 1.2 or 7), the expected section is in the top 3 with the fake embedder, and the full-text-only mode still returns non-empty hits (SC-005);
  - an embedder raising `EmbeddingsUnavailable` gives `mode="fulltext"`, non-empty hits and one warning logged;
  - an `index_metadata` provider mismatch gives `mode="fulltext"` with `degraded_reason="index_provider_mismatch"`;
  - an empty query gives no hits.
- [ ] T030 [P] [US3] `backend/tests/embeddings/test_voyage.py` (marker `voyage`): `embed(["olá"], "query")` returns 1 vector of 1024 floats.
- [ ] T031 [P] [US3] `backend/tests/retrieval/test_search_policies_voyage.py` (marker `voyage`): "can I return my order?" and "¿puedo devolver mi pedido?" both put §4.1 in the top 3 after seeding with Voyage.
- [ ] T032 [P] [US3] `backend/tests/embeddings/test_voyage_errors.py`, using `httpx.MockTransport`:
  - seed profile: 429, 429, 200 succeeds; four 500s raise `EmbeddingsUnavailable`;
  - query profile: one timeout raises immediately;
  - the API key is never in the exception message.

### Implementation

- [ ] T033 [P] [US3] Implement the `backend/app/embeddings/__init__.py` exports: `EMBEDDING_DIM`, `InputType`, `EmbeddingsUnavailable`, the `Embedder` Protocol, and `get_embedder(settings, purpose)` (`voyage` without an API key raises `ConfigError`).
- [ ] T034 [P] [US3] Implement `backend/app/embeddings/fake.py`, `FakeEmbedder(model="fake-ngram-v1")`: casefold, strip accents, char 3–5-grams with word padding, blake2b bucket and sign, L2 norm (research R3).
- [ ] T035 [P] [US3] Implement `backend/app/embeddings/voyage.py`: `VoyageEmbedder` over httpx `POST /v1/embeddings` (`model`, `input_type`, `output_dimension=1024`, batches ≤128), seed profile (4 attempts, backoff 1/2/4 s on 429/5xx/timeout) and query profile (1 attempt, 3 s timeout).
- [ ] T036 [US3] Implement `backend/app/embeddings/cache.py`: `embed_cached(conn, embedder, texts, input_type)` keyed by sha256(`normalize_for_cache(text)`), batched lookup, embeds only the misses, inserts with `ON CONFLICT DO NOTHING`, vectors passed as `'[..]'::vector` text literals.
- [ ] T037 [US3] Implement `backend/etl/policies.py` (research R6):
  - pypdf extraction; drop the cover page and the repeated header; clean bullets and U+200B; join wrapped lines; `nfc`;
  - heading regex plus the `EXPECTED_TOC` check;
  - chunk rules (subsections, non-empty parent intros, leaf top-level sections);
  - breadcrumb `search_text`, `content_hash`, `ordinal`;
  - `policy_conflict` detectors (WhatsApp §1.2 vs §7, accented email in §1.2, installment table vs §3.1).
- [ ] T038 [US3] Implement `backend/app/retrieval/hybrid.py` and `backend/app/retrieval/__init__.py`:
  - `PolicyHit`, `SearchResult`, `search_policies()` per contract;
  - one parameterized SQL query: an FTS CTE (`websearch_to_tsquery('pt_unaccent', %s)`, `ts_rank_cd`, top 20), a vector CTE (`embedding <=> %s::vector`, top 20), RRF k=60;
  - provider check against `index_metadata`;
  - fallback to the FTS-only query on `EmbeddingsUnavailable` or mismatch, with one `logger.warning`.
- [ ] T039 [US3] Wire into the ETL:
  - `backend/etl/__main__.py`: parse policies → `embed_cached` for documents **before** the write transaction (exit 3 on `EmbeddingsUnavailable`);
  - `backend/etl/load.py`: insert `policy_chunks` and set `index_metadata` (provider, model, fingerprint).

**Checkpoint**: T026–T032 green (voyage tests opt-in); quickstart step 5 passes.

---

## Phase 6: User Story 4: Search the product catalog (P2)

**Goal**: products searchable over name, category, specs and trusted descriptions only.

**Independent test**: no text from 135–144 descriptions is in `product_search_docs.search_text` or in embedding inputs; "Yamaha C40" ranks first.

- [ ] T040 [P] [US4] `backend/tests/etl/test_documents.py`:
  - for each of 135–144, `search_text` contains none of the description's distinctive tokens (e.g. "Fender Jazz Bass" for 135, "88 teclas" for 142);
  - trusted products include their description;
  - specs are rendered as `key: value` in sorted key order;
  - all 65 products get a doc.
- [ ] T041 [P] [US4] `backend/tests/retrieval/test_search_products.py` (integration, fake):
  - "Yamaha C40" ranks product 81 first;
  - a spy embedder shows that no embedding input contains a 135–144 description;
  - the fallback works as for policies.
- [ ] T042 [US4] Implement `backend/etl/documents.py`: `build_product_doc(product, category)` gives name + category name + specs (sorted `key: value`) + description only if `description_trusted`, plus `content_hash`.
- [ ] T043 [US4] Add `ProductHit` and `search_products()` to `backend/app/retrieval/__init__.py`, reusing the hybrid query over `product_search_docs` (returns `product_id`, `name` only).
- [ ] T044 [US4] Wire product docs into the ETL embed step and `backend/etl/load.py` (`product_search_docs`).

**Checkpoint**: T040–T041 green.

---

## Phase 7: User Story 5: Seed any environment (P2)

**Goal**: the same command seeds local or Neon safely, touching only owned tables.

**Independent test**: seed with an extra foreign table present: it is unchanged; missing `DATABASE_URL` exits 2.

- [ ] T045 [P] [US5] `backend/tests/etl/test_seed_env.py` (integration):
  - create `other_epic_table` with rows, seed, and check the rows are untouched;
  - create `other_epic_ref` with a foreign key to `orders`: the seed fails with exit 4 and both `other_epic_ref` and the store tables are unchanged (no `CASCADE`);
  - without `DATABASE_URL` (and without `--check`) the exit code is 2 and the message names the variable;
  - `EMBEDDINGS_PROVIDER=voyage` without a key exits 2;
  - an embedder failing after retries exits 3, leaves the store tables unchanged and keeps the cache rows computed before the failure;
  - stdout never contains the password from the URL.
- [ ] T046 [US5] Harden `backend/etl/__main__.py` and `backend/etl/load.py` to satisfy T045 (config validation up front, redaction, exit-code mapping).
- [ ] T047 [US5] Manual: run quickstart step 7 against Neon with Voyage; record the row counts and the seed wall time (SC-001: under 2 min) and confirm the checksums of the store tables match local (closes the "Seed runs successfully against Neon prod" criterion).

---

## Phase 8: Polish & Cross-Cutting

- [ ] T048 [P] Append a DL entry to `docs/decision-log.md` for the data-foundation implementation: rules as implemented, fake-embedder design, RRF, and the DL-001 correction (the "Ponta Porã" two-encodings finding came from the original download; the repo copy is all NFC; the rule is tested with a fixture).
- [ ] T049 [P] Add a "Data" section to `README.md`: the seed command, the report link and the env vars.
- [ ] T050 Run the full quickstart (steps 1–6) and `uv run ruff check . && uv run ruff format --check . && uv run pytest`; check that the fake-embedder seed takes under 30 s (SC-001); fix any findings.
- [ ] T051 Tick the acceptance criteria in issue #5 against the evidence (test names and the report).

---

## Dependencies & Execution Order

```text
Setup (T001–T004)
  └─> Foundational (T005–T012)
        ├─> US1 (T013–T022) ──> US2 (T023–T025)
        │        └──────────────> US3 (T026–T039) ──> US4 (T040–T044)
        └─────────────────────────────────────────────> US5 (T045–T047, after US1; T045's exit-3 case after US3)
                                                          └─> Polish (T048–T051)
```

- US1 is the MVP: store data correct and idempotent.
- US2 needs US1's anomalies; the `policy_conflict` row appears once US3 lands (T023 expects it then).
- US3 needs the loader (US1) only for wiring (T039); embeddings, chunker and search tests can start right after Foundational.
- US4 reuses US3's embeddings and hybrid query.
- Within each story: tests → models/pure functions → loader/search → CLI wiring.

## Parallel Examples

- **After Foundational**: T013, T014, T015 and T016 (US1 tests) alongside T026, T027 and T032 (US3 unit tests). They touch different files.
- **US1 implementation**: T018 (`app/catalog/rules.py`) ∥ T019 (`etl/models.py`), then T020 → T021 → T022.
- **US3 implementation**: T033 ∥ T034 ∥ T035, then T036 → T037 ∥ T038 → T039.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1, then stop and validate (quickstart 1–3). Store facts are
   enough for epic 002's price, stock and order tools to start.
2. Add US2 (report), the visible evidence for the evaluator.
3. Add US3 (policy search), which unblocks the agent's policy node.
4. Add US4 (product search), then US5 (Neon seed) before the deploy epic.
5. One PR per phase where possible, each `Part of #5`; the last one `Closes #5`.
