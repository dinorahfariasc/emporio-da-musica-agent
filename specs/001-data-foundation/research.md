# Research: Data Foundation

All Technical Context unknowns are resolved below. Each entry: Decision / Rationale / Alternatives.

## R1. Embeddings model

- **Decision**: Voyage `voyage-4`, `output_dimension=1024`, `input_type="document"` for indexing and
  `"query"` for searches. Model name is configurable (`EMBEDDINGS_MODEL`, default `voyage-4`);
  the dimension is a code constant (`EMBEDDING_DIM = 1024`) shared by the fake embedder and the
  `vector(1024)` columns.
- **Rationale**: multilingual (PT/EN/ES needed for the cross-language criterion), current
  general-purpose model, Matryoshka dimensions. 1024 is a good balance: the corpus is under 100
  documents, so storage and scan cost don't matter.
- **Alternatives**: `voyage-4-large` (better quality, twice the price; not needed for about 100
  docs); `voyage-multilingual-2` (older); 2048 dims (no benefit at this size).

## R2. Voyage client

- **Decision**: call `POST https://api.voyageai.com/v1/embeddings` directly with `httpx.AsyncClient`
  (httpx moves from dev to runtime deps). Batches of up to 128 inputs.
  - Seeding: up to 4 attempts with exponential backoff (1, 2, 4 s), retrying on 429/5xx/timeouts;
    then raise `EmbeddingsUnavailable` and the seed aborts (FR-023).
  - Query time: 1 attempt, 3 s timeout; any failure raises `EmbeddingsUnavailable` and search
    falls back to full-text (FR-018).
- **Rationale**: one endpoint, no SDK needed (constitution VI, YAGNI); explicit control of
  timeouts and retries.
- **Alternatives**: the `voyageai` SDK (extra deps, hides retry behaviour); `tenacity` (a simple loop is enough).

## R3. Deterministic fake embedder

- **Decision**: feature hashing of character 3- to 5-grams of the normalized text (NFC, casefold,
  accents stripped, word boundaries padded), bucketed into 1024 dims with a stable hash
  (`blake2b`), signed, then L2-normalized. No network, same input gives the same vector, across
  processes and platforms.
- **Rationale**: plain hash-of-text vectors are random, so similarity would mean nothing and the
  CI criterion ("posso devolver meu pedido?" → §4.1 in top 3) would hold only by luck.
  Character n-grams give real lexical similarity: *devolver* and *devolução* share `dev`, `evo`,
  `vol`, so the CI test is meaningful and stable. Cross-language similarity is out of scope for
  the fake; it is covered by the opt-in `-m voyage` tests.
- **Alternatives**: a random vector seeded by hash (meaningless); a local model such as
  fastembed (heavy, not deterministic across versions, rejected in DL-002).

## R4. Hybrid ranking

- **Decision**: Reciprocal Rank Fusion (RRF, k = 60) of two candidate lists (top 20 each):
  1. Full-text: `websearch_to_tsquery('pt_unaccent', q)` ranked by `ts_rank_cd`.
  2. Vector: cosine distance `embedding <=> query_vec`.

  All of it runs in one SQL query with two CTEs. Exact scan, no ANN index (under 100 rows per table).
- **Rationale**: RRF needs no score calibration between BM25-like ranks and cosine values;
  standard and well understood.
- **Alternatives**: a weighted sum of normalized scores (needs tuning); vector only (loses exact
  keywords such as "PIX", "boleto", product codes); HNSW index (not needed at this size; easy to
  add later).

## R5. Portuguese full-text with accents

- **Decision**: `CREATE EXTENSION unaccent`, plus a text search configuration `pt_unaccent`
  copied from `portuguese` with `unaccent, portuguese_stem` mapped for word tokens. Each indexed
  table has a stored generated column `tsv tsvector GENERATED ALWAYS AS
  (to_tsvector('pt_unaccent', search_text)) STORED` and a GIN index.
- **Rationale**: customers type without accents ("devolucao", "Ponta Pora"). Both extensions are
  available on Neon and in `pgvector/pgvector:pg16`.
- **Alternatives**: the plain `portuguese` config (misses unaccented queries); `pg_trgm` (adds
  little next to the vector side).

## R6. PDF extraction and chunking

- **Decision**: `pypdf` text extraction in the ETL only (dependency group `etl`, not shipped in
  the Vercel function). Clean-up: drop the cover page and the repeated page header
  ("Empório da Música Manual de Políticas e Procedimentos"), remove `•` + U+200B bullet artifacts,
  join wrapped lines, and NFC-normalize.

  Chunking: split on heading lines matching `^(\d{1,2})(?:\.(\d))?\.?\s+\S`. The detected
  heading list is then **validated against a hard-coded expected table of contents** (10
  sections, 18 subsections). If they don't match, the ETL fails loudly instead of indexing
  garbage.

  Chunk rules:
  - one chunk per subsection (e.g. 4.1);
  - a chunk for a top-level section's own intro text when it is non-empty (e.g. §4 intro, §3
    payment table);
  - top-level sections without subsections (2, 9, 10) are one chunk.

  Each chunk's `search_text` is prefixed with its breadcrumb (`4 Política de Trocas e
  Devoluções > 4.1 Direito de Arrependimento (Compras Online)`).
- **Rationale**: section-level citation ("§4.1") is required by the agent. The ToC check makes
  the extraction deterministic and testable. Tables come out flattened (label/value lines), which
  is fine because numbers are never computed from RAG (constitution I).
- **Alternatives**: `pdfplumber` (better tables, heavier; not needed); a hand-written markdown
  copy of the manual (drifts from the source PDF, which is read-only input).

## R7. Seed transaction, ownership and idempotency

- **Decision**: one async psycopg connection (`prepare_threshold=None`, as in `app/db.py`, for
  Neon's PgBouncer):
  1. Read and validate all inputs, apply rules, and build chunks/docs in memory (no DB writes).
  2. Compute all needed embeddings *before* opening the write transaction, reading from and
     writing to `embedding_cache`. Cache writes are committed on their own so paid work is never
     lost.
  3. In one transaction: run idempotent DDL (`CREATE ... IF NOT EXISTS`), `TRUNCATE` the owned
     tables (except `embedding_cache`) in one statement with `RESTART IDENTITY` and **without**
     `CASCADE` (a foreign key from another feature's table must fail the seed, not silently empty
     that table), `COPY`/insert everything, and
     write `index_metadata`.
  4. Commit, compute checksums, and write the report.

  The owned tables are an explicit list in `etl/load.py`; nothing else is touched.
- **Idempotency check**: per-table checksum
  `md5(string_agg(row_to_json(t)::text, '\n' ORDER BY <pk>))`. Embeddings are identical across
  runs because they come from `embedding_cache` (FR-019).
- **Rationale**: matches clarifications 2 and 3; the report is written only after a successful commit.
- **Alternatives**: Alembic migrations (overkill for a rebuild-from-source dataset; revisit when
  other epics add mutable tables); `DROP SCHEMA` (would hit other epics' tables).

## R8. Derived business rules: where they live

- **Decision**: pure functions in `app/catalog/rules.py`: `effective_promotion(promos)`,
  `availability(status, stock)`, `is_sellable(...)`. The ETL stores their results in columns
  (`products.availability`, `products.effective_discount_percent`, `products.effective_promotion_id`)
  for cheap reads, and the agent tools (epic 002) reuse the same functions.
  Data-quality detection rules (total mismatch, untrusted descriptions, shared email,
  non-sellable items in orders, empty categories, NFC changes, policy conflicts) live in
  `etl/rules.py`.
- **Rationale**: one deterministic source of truth for availability and discount (constitution I).
  ETL-only detection code stays out of the runtime bundle.

## R9. Untrusted descriptions (IDs 135–144)

- **Decision**: an explicit, versioned rule `UNTRUSTED_DESCRIPTION_IDS = range(135, 145)` with the
  reason per ID, kept next to a heuristic check. The heuristic flags descriptions that mention a
  brand different from the product name's brand, or a string/key count that differs from specs.
  It is used **only to verify** that the explicit list is complete. The test asserts heuristic ⊆
  explicit list, so a new contradiction would fail CI instead of being silently trusted.
- **Rationale**: DL-002 names the IDs; a pure heuristic would be fragile, and a pure list would
  not be self-checking.

## R10. Report determinism and PII

- **Decision**: the report is rendered from the `data_anomalies` rows sorted by (type, record IDs).
  It contains no timestamps, only the dataset fingerprint (sha256 of the input files). Emails are
  masked (`b***@jmail.com`) and customers are referred to by ID.
- **Rationale**: SC-003 (identical reports) and constitution V (mask personal data).

## R11. Test layout and markers

- **Decision**:
  - Unit tests (no DB) for schemas, rules, chunking, the fake embedder and the report.
  - Integration tests use the existing `database_url` fixture (they skip when `DATABASE_URL` is
    unset; CI provides Postgres).
  - Marker `voyage` for opt-in real-provider tests; `addopts = "-m 'not voyage'"` keeps them out
    of default runs, and `uv run pytest -m voyage` runs them.
  - A Neon smoke test is a manual quickstart step, not CI.

## R12. Dependencies added

| Dependency | Group | Why |
|---|---|---|
| `httpx` | runtime (moved from dev) | Voyage client |
| `pydantic` | runtime (already transitive) | row schemas, typed results |
| `pypdf` | `etl` group | PDF text extraction |

The `etl` group is in `[tool.uv] default-groups` for local/CI; the Vercel function excludes
`etl/**` and the challenge files. No `pgvector` Python package: vectors are passed as text
literals cast to `vector` (avoids pulling in numpy).
