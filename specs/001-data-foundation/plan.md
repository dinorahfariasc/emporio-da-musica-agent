# Implementation Plan: Data Foundation

**Branch**: `001-data-foundation` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md) | **Epic**: #5

**Input**: Feature specification from `specs/001-data-foundation/spec.md`

## Summary

A reproducible ETL (`uv run python -m etl`) reads the read-only challenge CSVs and policy PDF,
validates them with Pydantic, applies the DL-002 correction rules, normalizes text to NFC and
loads Postgres in one transaction. It also builds two hybrid search indexes (Portuguese
full-text + pgvector, fused with RRF): one over policy sections and one over products. It writes
a deterministic `docs/data-quality-report.md`.

Embeddings go through an `Embedder` interface with a Voyage (`voyage-4`, 1024 dims) and a
deterministic character-n-gram fake. A persistent `embedding_cache` table serves both the
query-embedding cache and re-seed reuse. At query time, search degrades to full-text when the
provider fails. Runtime pieces (embeddings, retrieval, catalog rules) live in `backend/app/`
for the agent epic. ETL-only code lives in `backend/etl/`.

## Technical Context

**Language/Version**: Python 3.13 (from #3 scaffolding)

**Primary Dependencies**: Pydantic v2 / pydantic-settings, psycopg 3 (async), httpx (Voyage
REST), pypdf (ETL group only)

**Storage**: Postgres 16 with `vector` and `unaccent` (docker `pgvector/pgvector:pg16` locally
and in CI; Neon in production)

**Testing**: pytest (+ pytest-asyncio). Integration tests use the existing `database_url` fixture.
Marker `voyage` is opt-in.

**Target Platform**: ETL runs on a developer machine or CI against any `DATABASE_URL`; retrieval
code runs inside the FastAPI app on Vercel Python functions.

**Project Type**: web service backend (data layer + CLI)

**Performance Goals**: seed < 30 s with fake / < 2 min with Voyage (SC-001); policy search
< 300 ms excluding the provider call (exact scan over < 100 rows)

**Constraints**: no paid calls in CI; Neon PgBouncer (`prepare_threshold=None`); Voyage free tier
(embed only changed content); Vercel bundle excludes `etl/` and `challenge/`

**Scale/Scope**: 9 categories, 65 products, 25 promotions, 50 customers, 20 orders, 22 items,
about 25 policy chunks (18 subsections + non-empty intros + leaf sections)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
|---|---|---|
| I. Facts from the system | Availability, sellability and effective discount are computed by pure functions in `app/catalog/rules.py` and stored as columns; search returns IDs only, never prices or stock; order totals kept as paid; all SQL parameterized | ✅ |
| II. LLM only where it adds value | No LLM in this feature; embeddings only | ✅ (n/a) |
| III. Clean, traceable data | Inputs read-only; Pydantic validation; one explicit rule per anomaly, each tested; generated report + DL entry; NFC everywhere (`app/text.py`) | ✅ |
| IV. Tested before done | Unit tests per rule, chunker, fake embedder, report; DB integration tests for idempotency, retrieval, fallback, cache; fake embedder in CI; Voyage tests opt-in | ✅ |
| V. Safe and respectful | Emails masked in report; DB URL never logged; secrets only from env | ✅ |
| VI. Simple, modular, replaceable | `Embedder` protocol selected by `EMBEDDINGS_PROVIDER`; no SDK, no ORM, no migrations framework, no ANN index, no numpy | ✅ |
| Tech constraints | uv, ruff, pytest; Postgres + pgvector; Voyage; `.env.example` updated | ✅ |

Post-design re-check (after data-model and contracts): still passing. One deliberate addition is
justified below.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-foundation/
├── spec.md
├── plan.md               # this file
├── research.md           # R1–R12 decisions
├── data-model.md         # tables, rules, anomaly catalogue
├── quickstart.md         # validation guide
├── contracts/
│   ├── seed-cli.md
│   ├── retrieval-api.md
│   └── data-quality-report.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code

```text
backend/
├── app/                          # runtime (shipped to Vercel)
│   ├── config.py                 # + embeddings_model setting
│   ├── db.py                     # existing; + connect() helper reused by ETL and retrieval
│   ├── text.py                   # nfc(), normalize_for_cache()
│   ├── catalog/
│   │   ├── __init__.py
│   │   └── rules.py              # availability, is_sellable, effective_promotion
│   ├── embeddings/
│   │   ├── __init__.py           # Embedder protocol, EMBEDDING_DIM, EmbeddingsUnavailable, get_embedder
│   │   ├── fake.py               # char n-gram feature hashing
│   │   ├── voyage.py             # httpx client, seed/query profiles
│   │   └── cache.py              # embed_cached() over embedding_cache
│   └── retrieval/
│       ├── __init__.py           # search_policies, search_products, result models
│       └── hybrid.py             # RRF SQL, fallback logic
├── etl/                          # ETL only (excluded from Vercel bundle)
│   ├── __init__.py
│   ├── __main__.py               # CLI (contracts/seed-cli.md)
│   ├── schema.sql                # idempotent DDL: extensions, pt_unaccent, owned tables
│   ├── sources.py                # read CSVs/PDF, dataset fingerprint
│   ├── models.py                 # Pydantic row models + per-category specs schemas
│   ├── rules.py                  # anomaly detection & corrections → Anomaly records
│   ├── policies.py               # PDF clean-up, heading detection, ToC check, chunks
│   ├── documents.py              # product search_text builder
│   ├── load.py                   # OWNED_TABLES, transaction: DDL, truncate, load, metadata
│   ├── checksums.py              # per-table row count + md5
│   └── report.py                 # deterministic markdown renderer
├── tests/
│   ├── fixtures/                 # nfd_customers.csv, promotions_multi_active.csv, tiny dataset
│   ├── etl/                      # test_models, test_rules (one per rule), test_policies,
│   │                             # test_documents, test_report, test_seed (DB: counts, idempotency,
│   │                             # owned-tables-only, rollback)
│   ├── catalog/test_rules.py
│   ├── embeddings/               # test_fake, test_cache (DB), test_voyage (marker voyage)
│   └── retrieval/                # test_search (DB: §4.1 top 3, product name top 1, fallback,
│                                 # provider mismatch, cache hit), test_search_voyage (EN/ES)
├── pyproject.toml                # deps, etl group, default-groups, voyage marker
docs/data-quality-report.md       # generated, committed
vercel.json                       # services.backend excludeFiles += etl/**
```

**Structure Decision**: follow the flat `app/` package from #3 (DL-004). Code the agent needs
at runtime goes in `app/`; ETL-only code (PDF parsing, validation, reporting) goes in `etl/`, so
`pypdf` and the challenge files stay out of the serverless bundle. `etl` imports from `app`
(`text`, `catalog.rules`, `embeddings`), never the reverse.

## Key Design Points

1. **Pipeline order** (research R7): read → validate → normalize → detect anomalies/derive →
   build chunks and docs → embed through the cache (outside the write transaction) → one
   transaction (DDL, truncate owned tables, load, metadata) → checksums → report.
2. **Failure semantics**: validation, ToC or config errors exit before touching the DB; an
   embeddings failure after retries exits 3 before the write transaction; a DB error rolls back.
3. **Retrieval**: one SQL query, two CTEs (full-text and vector), RRF k=60. If the index was built
   with another provider/model (`index_metadata`) or the embedder fails, the query runs
   full-text only and returns `mode="fulltext"`.
4. **Determinism**: the fake embedder is stable across processes. Rows are inserted in PK order,
   anomalies are sorted, the report has no timestamps, and embeddings are reused by hash.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Character n-gram fake embedder (instead of a trivial hash) | Makes the CI retrieval criterion (§4.1 top 3) meaningful and stable | A random-by-hash fake would pass or fail by chance and test nothing |
| `index_metadata` provider check | Prevents comparing fake vectors with Voyage query vectors (or the reverse) after an env mix-up | Without it, a misconfigured prod would return wrong policy sections silently |
