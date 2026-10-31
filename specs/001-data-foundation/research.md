# Research: Data Foundation

All Technical Context unknowns are resolved below. Each entry: Decision / Rationale / Alternatives.
Revised after the PR #27 QA + senior review (scope cut to about 3–4 h in 2 PRs).

## R1. Embeddings model

- **Decision**: Gemini `gemini-embedding-001` (DL-007).
  - `taskType=RETRIEVAL_DOCUMENT` for indexed documents and `RETRIEVAL_QUERY` for searches.
  - `outputDimensionality=768`. Vectors are **L2-normalized after truncation**: Matryoshka outputs
    below 3072 dims are not unit-length.
  - The model name is configurable (`EMBEDDINGS_MODEL`, default `gemini-embedding-001`). The
    dimension is a code constant (`EMBEDDING_DIM = 768`) shared by the fake embedder and the
    `vector(768)` columns.
- **Rationale**: free tier, multilingual (PT/EN/ES needed for the cross-language criterion),
  retrieval-specific task types. 768 dims is enough for under 100 documents and keeps rows small.
- **Alternatives**: 3072 dims (no benefit at this size); a local model (bundle size and cold start,
  see DL-007).

## R2. Gemini client and rate limits

- **Decision**: call
  `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents`
  directly with `httpx.AsyncClient`. Header `x-goog-api-key: $GEMINI_API_KEY`. Body:
  `{"requests": [{"model": "models/gemini-embedding-001", "content": {"parts": [{"text": ...}]},
  "taskType": ..., "outputDimensionality": 768}, ...]}`. The response is
  `{"embeddings": [{"values": [...]}]}`, in request order.
  - **Batching by token budget**: estimate tokens as `ceil(len(text) / 3)` (conservative for
    Portuguese). Pack inputs into batches of at most 20,000 estimated tokens and 100 requests, so
    one batch stays under the free tier's 30K TPM.
  - **Rate limits** (free tier: 100 RPM, 1,000 RPD, 30K TPM): on 429 or 503, wait for the delay
    from the `Retry-After` header, or else from the error body's `RetryInfo.retryDelay` (e.g.
    `"30s"`), defaulting to 30 s, then retry the same batch. Give up after 5 attempts per batch or
    120 s in total. Batches are sent one after another.
  - **Query time**: 1 attempt with a 3 s timeout; any failure raises `EmbeddingsUnavailable` and
    search falls back to full-text.
  - **The cache matters**: the seed embeds about 90 documents once (1–2 requests), and repeated
    queries hit `embedding_cache`, so the 1,000 RPD budget goes to new queries only.
  - The API key is never logged or included in exception messages (it travels in a header, not
    the URL).
- **Known limitation** (DL-007): on the free tier Google may use submitted content to improve its
  products. That is acceptable for fictional store data, and the README documents it.
- **Alternatives**: the `google-genai` SDK (extra dependency for one endpoint); one request per
  text (wastes RPM).

## R3. Deterministic fake embedder

- **Decision**: feature hashing of character 3- to 5-grams of the normalized text (NFC, casefold,
  accents stripped, word boundaries padded), bucketed into 768 dims with `blake2b`, signed, then
  L2-normalized. No network; same input → same vector (`blake2b` is not salted per process,
  unlike `hash()`).
- **Rationale**: lexical similarity (*devolver* ~ *devolução*) makes the CI retrieval criterion
  meaningful. The test asserts §4.1 is in the top 3 of the **vector ranking alone**, so the fake
  is actually exercised.
- **Alternatives**: random vector per text (meaningless); a local model (heavy, rejected in DL-002).

## R4. Hybrid ranking

- **Decision**: Reciprocal Rank Fusion (k = 60) of two top-20 candidate lists, in one SQL query:
  1. Full-text, matching **any** query term:
     `q := (SELECT string_agg(quote_literal(l), ' | ') FROM unnest(tsvector_to_array(to_tsvector('pt_unaccent', :query))) l)::tsquery`,
     ranked by `ts_rank_cd(tsv, q)`. If the query has no lexemes (only stopwords), the list is empty.
  2. Vector: cosine distance `embedding <=> :vec`.

  Exact scan, no ANN index. Filters (product search) apply to both lists before ranking.
- **Rationale**: `websearch_to_tsquery`/`plainto_tsquery` AND all terms, so "posso devolver meu
  pedido?" could match nothing. OR-ing the stemmed lexemes keeps recall and lets `ts_rank_cd`
  order by how many terms match. Building the tsquery from `to_tsvector` lexemes avoids
  stemming them twice.
- **Alternatives**: `plainto_tsquery` (AND semantics); weighted score sum (needs tuning).

## R5. Portuguese full-text with accents

- **Decision**: `CREATE EXTENSION IF NOT EXISTS unaccent` and `vector`. The text search config
  `pt_unaccent` is created inside a `DO` block that checks `pg_ts_config`, because there is no
  `CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS`. It is a copy of `portuguese` with word token
  types mapped to `unaccent, portuguese_stem`. Indexed tables have a stored generated column
  `tsv = to_tsvector('pt_unaccent', search_text)` with a GIN index.
- **Rationale**: customers type without accents ("devolucao"). Both extensions are available on
  Neon and in `pgvector/pgvector:pg16`.

## R6. PDF extraction and chunking

- **Decision**: `pypdf` (ETL dependency group only).
  - **Clean-up**: drop the cover page and the repeated page header, remove `•` + U+200B bullet
    artifacts, join wrapped lines, NFC.
  - **Chunking**: split on heading lines `^(\d{1,2})(?:\.(\d))?\.?\s+\S`, validated against a
    hard-coded expected table of contents (10 sections, 18 subsections). If they don't match,
    the ETL fails.
  - **Chunks**: one per subsection; one for a top-level section's own intro text when it is
    non-empty; top-level sections without subsections (2, 9, 10) are one chunk.
  - **Search text**: prefixed with the breadcrumb (`4 Política de Trocas e Devoluções > 4.1
    Direito de Arrependimento (Compras Online)`). `parent_title` is stored for citations.
- **Policy conflicts**: the three known conflicts (WhatsApp number §1.2 vs §7, accented email in
  §1.2 vs cover, installment table vs §3.1) are **static anomaly records** in `etl/rules.py`. They
  are not detected from the PDF text; a regex detector would cost more than it is worth for three
  fixed facts.

## R7. Seed transaction, schema evolution, concurrency

- **Decision**: one connection to `DATABASE_URL_UNPOOLED` when set (Neon's direct endpoint),
  else `DATABASE_URL`; `prepare_threshold=None` in both cases.
  1. Read, validate, apply rules, and build chunks/docs and anomalies in memory (no DB writes).
  2. Compute document embeddings through `embedding_cache` (committed on its own, so paid work
     is kept) **before** the write transaction.
  3. In one transaction:
     - `SELECT pg_advisory_xact_lock(hashtext('emporio:seed'))`;
     - create the extensions, `pt_unaccent` (DO block) and `embedding_cache` if missing;
     - `DROP TABLE IF EXISTS` the owned tables in reverse dependency order (**no `CASCADE`**);
     - `CREATE TABLE` them from `etl/schema.sql`, then insert everything in PK order and write
       `index_metadata`.
  4. Commit, compute checksums, write the report.
- **Rationale**: drop and recreate means column changes always apply (`CREATE TABLE IF NOT
  EXISTS` would silently keep an old shape on Neon). No `CASCADE`: if another feature's table has
  a foreign key to an owned table, the seed fails instead of touching it. The advisory lock
  serializes concurrent seeds. The unpooled URL avoids PgBouncer for a long DDL transaction.
- **Idempotency check**: per owned table, row count and
  `md5(string_agg(row_to_json(t)::text, E'\n' ORDER BY <pk>))`, excluding the generated `tsv`
  column.
- **Alternatives**: Alembic (overkill for a rebuild-from-source dataset); truncate (keeps stale
  columns).

## R8. Derived business rules: where they live

- **Decision**: pure functions in `app/catalog/rules.py`:
  - `availability(status, stock)` and `is_sellable(status, stock)`;
  - `effective_promotion(promos)`;
  - `promo_price(price, discount_percent) -> Decimal` (`ROUND_HALF_UP`, 2 places).

  The ETL stores their results (`availability`, `is_sellable`, `effective_promotion_id`,
  `effective_discount_percent`, `promo_price_brl`) and the #6 tools read the columns or call the
  same functions. Payment-method pricing builds on `promo_price_brl` in #6.

  Data-quality detection lives in `etl/rules.py`.
- **Untrusted descriptions**: an explicit `UNTRUSTED_DESCRIPTION_IDS = range(135, 145)` with a
  reason per ID. No heuristic double-check (cut in review).

## R9. Report

- **Decision**: rendered from the in-memory anomaly list and the in-memory row counts, so no
  database is needed. Fixed type order, records sorted by numeric ID, emails masked
  (`b***@jmail.com`), no timestamps, no dataset fingerprint. The CLI writes it to
  `docs/data-quality-report.md`; tests render it to `tmp_path`. A CI test renders it and
  compares it with the committed file (drift check).
- **Rationale**: SC-003, and the report doubles as reviewable evidence in git.
- **Alternatives**: a `data_anomalies` table (dropped: nothing reads it yet; easy to add for the
  P2 admin dashboard).

## R10. Embedding cache keys

- **Decision**: one table, `embedding_cache(provider, model, input_type, text_key, embedding)`.
  - Documents: `text_key = sha256(nfc(text))`, the exact text, so any change re-embeds.
  - Queries: `text_key = sha256(normalize_for_cache(text))` (NFC, casefold, collapsed whitespace),
    so trivially different queries share a vector.

## R11. Connections at runtime (serverless)

- **Decision**: `app/db.py` exposes a lazily opened, module-level
  `psycopg_pool.AsyncConnectionPool(min_size=0, max_size=4, kwargs={"prepare_threshold": None})`
  over `DATABASE_URL` (pooled endpoint). Warm invocations reuse connections.

  `index_metadata` (provider/model the index was built with) is read once per process and cached
  for 5 minutes, so a re-seed with a different provider is picked up without a redeploy.
- **Rationale**: a fresh connection from `iad1` to Neon costs about 1.7 s warm (DL-004). Reuse
  removes that from every warm request.
- **Alternatives**: a connection per request (current skeleton; too slow).

## R12. Production safety

- **Decision**:
  - The CLI prints `target: <host>/<db>`. Hosts other than `localhost`, `127.0.0.1` and `::1`
    require `--yes`.
  - `ENVIRONMENT=production` with `EMBEDDINGS_PROVIDER=fake` is refused.
  - Exit codes are only 0 (success) and 1 (any failure, with a message).
  - Destructive integration tests use a `local_database_url` fixture that skips on non-local
    hosts unless `ALLOW_DESTRUCTIVE_TESTS=1`.

## R13. Test layout and markers

- **Decision**:
  - Unit tests (no DB): schemas, rules, sources, chunking, fake embedder, report and its drift
    check.
  - Integration tests (local DB): seed, idempotency, retrieval, fallback, cache.
  - Marker `gemini` is opt-in (`addopts = "-m 'not gemini'"`) and covers the EN/ES retrieval and
    the real-API smoke test.
  - One mocked-transport test covers the Gemini 429/`Retry-After` path and post-truncation
    normalization.
  - The Neon seed is a manual quickstart step.

## R14. Dependencies added

| Dependency | Group | Why |
|---|---|---|
| `httpx` | runtime (moved from dev) | Gemini client |
| `pydantic` | runtime (already transitive) | row schemas, typed results |
| `psycopg-pool` | runtime | serverless connection reuse (R11) |
| `pypdf` | `etl` group | PDF text extraction |

The `etl` group is in `[tool.uv] default-groups` for local/CI. The root `vercel.json` backend
service excludes `etl/**`. No `pgvector` Python package: vectors are passed as text literals
cast to `vector` (avoids numpy).
