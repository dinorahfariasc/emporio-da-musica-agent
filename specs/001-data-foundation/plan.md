# Implementation Plan: Data Foundation

**Branch**: `001-data-foundation` | **Date**: 2026-10-31 (revised after the PR #27 review) | **Spec**: [spec.md](spec.md) | **Epic**: #5

**Input**: Feature specification from `specs/001-data-foundation/spec.md`

## Summary

A reproducible ETL (`uv run python -m etl`) reads the read-only challenge CSVs and policy PDF,
validates them with Pydantic, applies the DL-002 correction rules, normalizes text to NFC and
loads Postgres in one locked transaction that drops and recreates only the tables it owns. It
renders a deterministic `docs/data-quality-report.md` from in-memory data, and CI checks it for
drift.

Retrieval adds two hybrid indexes (policy sections, products):
- Portuguese full-text matching any term, plus pgvector, fused with RRF;
- an `Embedder` interface with Gemini (`gemini-embedding-001`, 768 dims normalized after
  truncation, retrieval task types, token-budget batching honouring 429/`Retry-After`) and a
  deterministic n-gram fake;
- a persistent `embedding_cache`, full-text fallback, filters, similar-product search from stored
  vectors, and a module-level connection pool for serverless.

**Delivery: 2 implementation PRs, about 3–4 h in total.**

| PR | Scope | Stories | Estimate |
|---|---|---|---|
| **A** `feat: store data, quality report and safe seed` | schema (store tables), validation, rules, load, CLI safety, report + drift test | US1, US2, US5 (safety) | ~1h45 |
| **B** `feat: hybrid retrieval and production seed` | embeddings (fake, Gemini, cache), PDF chunks, product docs, search/filters/similar, pool, Neon seed | US3, US4, US5 (production run) | ~2h |

## Technical Context

**Language/Version**: Python 3.13 (from #3)

**Primary Dependencies**: Pydantic v2 / pydantic-settings, psycopg 3 (async) + psycopg-pool,
httpx (Gemini REST), pypdf (ETL group only)

**Storage**: Postgres 16 with `vector` and `unaccent` (docker `pgvector/pgvector:pg16` locally and
in CI; Neon in production, seeded through the unpooled URL)

**Testing**: pytest + pytest-asyncio. Destructive integration tests use a `local_database_url`
fixture; marker `gemini` is opt-in.

**Target Platform**: ETL runs on a developer machine or CI; retrieval runs inside the FastAPI
backend service on Vercel (Services, DL-004).

**Project Type**: web service backend (data layer + CLI)

**Performance Goals**: seed < 30 s with the fake, < 2 min with Gemini on the free tier (SC-001);
warm policy search without connection setup (pool)

**Constraints**:
- no paid calls in CI;
- Gemini free tier: 100 RPM, 1,000 RPD, 30K TPM;
- Neon PgBouncer (`prepare_threshold=None`);
- the backend bundle excludes `etl/**`.

**Scale/Scope**: 9 categories, 65 products, 25 promotions, 50 customers, 20 orders, 22 items,
about 25 policy chunks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
|---|---|---|
| I. Facts from the system | Availability, sellability, effective discount and promo price come from pure functions in `app/catalog/rules.py`, stored as columns; search returns IDs, category and availability, never prices or stock; order totals kept as paid; all SQL parameterized | ✅ |
| II. LLM only where it adds value | No LLM in this feature | ✅ (n/a) |
| III. Clean, traceable data | Inputs read-only and byte-stable (`.gitattributes`); Pydantic validation; one explicit rule per anomaly, each tested; DL-001 traceability table in the report; NFC everywhere | ✅ |
| IV. Tested before done | Unit tests per rule, sources, chunker, fake embedder, report drift; integration tests for idempotency, retrieval (vector rank asserted), fallback, cache, filters; fake embedder in CI; Gemini opt-in | ✅ |
| V. Safe and respectful | Emails masked in the report; DB URL never printed; `--yes` for remote targets; fake refused in production; destructive tests only on local hosts | ✅ |
| VI. Simple, modular, replaceable | `Embedder` protocol selected by config; no SDK, ORM, migrations framework, ANN index or numpy; review cuts applied (no `--check`, fingerprint, heuristics, PDF conflict regex) | ✅ |
| Tech constraints | uv, ruff, pytest; Postgres + pgvector; Gemini embeddings (constitution 1.0.2); `.env.example` updated | ✅ |

Post-design re-check: passing.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-foundation/
├── spec.md · plan.md · research.md (R1–R14) · data-model.md · quickstart.md
├── contracts/ seed-cli.md · retrieval-api.md · data-quality-report.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
.gitattributes                    # challenge/** -text ; backend/tests/fixtures/*.csv -text      (A)
vercel.json                       # services.backend excludeFiles += etl/**                       (A)
backend/
├── app/
│   ├── config.py                 # + embeddings_model, database_url_unpooled                    (A)
│   ├── db.py                     # + connect(), get_pool()                                       (A connect, B pool)
│   ├── text.py                   # nfc(), normalize_for_cache()                                  (A)
│   ├── catalog/rules.py          # availability, is_sellable, effective_promotion, promo_price  (A)
│   ├── embeddings/               # __init__ (protocol, factory), fake.py, gemini.py, cache.py   (B)
│   └── retrieval/                # __init__ (models, search_*, similar_to_product), hybrid.py   (B)
├── etl/
│   ├── __main__.py               # CLI: target print, --yes, refusals, exit 0/1                  (A, B wires index)
│   ├── schema.sql                # extensions, pt_unaccent DO block, embedding_cache IF NOT EXISTS,
│   │                             # owned tables CREATE (store: A; retrieval: B)
│   ├── sources.py                # CSV read (newline="", NFC, '' handling), PDF path             (A)
│   ├── models.py                 # Pydantic rows + per-category specs                            (A)
│   ├── rules.py                  # anomaly detection, derivations, static policy conflicts       (A)
│   ├── pipeline.py               # build_payload(data_dir) → rows + anomalies (pure, no DB)      (A)
│   ├── load.py                   # OWNED_TABLES, reload(): lock, drop/create, insert             (A)
│   ├── checksums.py              # per-table count + md5                                         (A)
│   ├── report.py                 # render(payload) -> str                                        (A)
│   ├── policies.py               # PDF → chunks with ToC check                                   (B)
│   └── documents.py              # product search_text                                           (B)
└── tests/
    ├── conftest.py               # + local_database_url fixture (destructive guard)              (A)
    ├── fixtures/                 # nfd_customers.csv, crlf_customers.csv, promotions_multi_active.csv,
    │                             # policy_reference_queries.json (B)
    ├── test_text.py, catalog/test_rules.py
    ├── etl/                      # test_sources, test_models, test_rules, test_report (incl. drift),
    │                             # test_seed (DB), test_cli, test_policies (B), test_documents (B)
    ├── embeddings/               # test_fake, test_cache (DB), test_gemini (mock 429 + marker gemini)
    └── retrieval/                # test_search_policies, test_search_products (DB), *_gemini (marker)
docs/data-quality-report.md       # generated, committed                                          (A)
README.md                         # "Data" section incl. Gemini free-tier limits and data-use note (A, B)
```

**Structure Decision**: follow the flat `app/` package from #3 (DL-004). Code the agent needs at
runtime goes in `app/`; ETL-only code goes in `etl/` (excluded from the bundle). `etl` imports
from `app`, never the reverse. `etl/pipeline.py` keeps the payload build pure, so the report and
its drift test run without a database.

## Key Design Points

1. **Pipeline** (R7): `build_payload` (read → validate → rules → derive → chunks/docs) → embed
   through the cache (B, outside the transaction) → `reload` (advisory lock, drop/create owned
   tables without `CASCADE`, insert, metadata) → checksums → report.
2. **Safety** (R12): print the target, `--yes` for remote, refuse fake in production, unpooled
   URL, destructive tests local-only, exit 0/1.
3. **Retrieval** (R4, R11): any-term full-text + vector, RRF k=60, filters joined from
   `products`, `similar_to_product` from stored vectors, pooled connections, `index_metadata`
   cached for 5 min.
4. **Determinism**: rows inserted in PK order; anomalies sorted; report with no timestamps;
   document embeddings reused by exact text.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Character n-gram fake embedder | Makes the CI retrieval criterion meaningful; the test asserts the vector rank | A random-by-hash fake tests nothing |
| `index_metadata` provider check (cached) | Prevents comparing fake and Gemini vectors after an env mix-up | Wrong policy sections would be returned silently |
| `psycopg-pool` | About 1.7 s per new connection from Vercel to Neon (DL-004) | A connection per request makes every warm query slow |
