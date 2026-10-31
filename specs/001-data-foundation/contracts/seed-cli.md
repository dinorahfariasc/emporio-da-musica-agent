# Contract: Seed CLI

Run from `backend/`:

```bash
uv run python -m etl [--data-dir ../challenge] [--report ../docs/data-quality-report.md] [--check]
```

| Option | Default | Meaning |
|---|---|---|
| `--data-dir` | `../challenge` | Folder containing `data/*.csv` and `data/store_policies.pdf` (read-only) |
| `--report` | `../docs/data-quality-report.md` | Report output path |
| `--check` | off | Validate and build everything in memory, print the anomaly summary, write nothing (no DB, no report) |

**Environment** (via `app.config.Settings`): `DATABASE_URL` (required unless `--check`),
`EMBEDDINGS_PROVIDER` (`fake` \| `voyage`), `EMBEDDINGS_MODEL` (default `voyage-4`),
`VOYAGE_API_KEY` (required when provider is `voyage`).

**Exit codes**

| Code | When | DB state |
|---|---|---|
| 0 | Success | Owned tables reloaded; report written |
| 1 | Validation error (message: `file:row field: reason`) or PDF ToC mismatch | Unchanged |
| 2 | Configuration error (missing `DATABASE_URL`, missing API key) | Unchanged |
| 3 | Embeddings provider unavailable after retries | Store tables unchanged (`embedding_cache` may hold the vectors computed before the failure) |
| 4 | Database error | Unchanged (transaction rolled back) |

**Stdout on success** (stable, used by the quickstart and the idempotency test):

```text
categories        9  <md5>
products         65  <md5>
promotions       25  <md5>
customers        50  <md5>
orders           20  <md5>
order_items      22  <md5>
policy_chunks    NN  <md5>
product_search_docs 65 <md5>
data_anomalies   NN  <md5>
embeddings: provider=fake model=fake-ngram-v1 computed=N reused=M
report: ../docs/data-quality-report.md
```

Logs go to stderr. The database URL is never printed (only host and database name).
