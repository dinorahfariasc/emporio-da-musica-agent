# Contract: Seed CLI

Run from `backend/`:

```bash
uv run python -m etl [--yes]
```

| Option | Meaning |
|---|---|
| `--yes` | Required when the target host is not local (`localhost`, `127.0.0.1`, `::1`) |

Paths are fixed (`../challenge/data`, `../docs/data-quality-report.md`); tests call the
pipeline functions with `tmp_path` instead of the CLI.

**Environment** (via `app.config.Settings`):
- `DATABASE_URL_UNPOOLED` (used when set), else `DATABASE_URL`;
- `ENVIRONMENT`;
- `EMBEDDINGS_PROVIDER` (`fake` \| `gemini`), `EMBEDDINGS_MODEL` (default `gemini-embedding-001`);
- `GEMINI_API_KEY` (required when the provider is `gemini`).

**Refusals** (exit 1 before any write):
- no database URL;
- non-local host without `--yes`;
- `ENVIRONMENT=production` with `EMBEDDINGS_PROVIDER=fake`;
- `gemini` without an API key.

**Exit codes**: `0` success; `1` any failure (refusal, validation error `file:row field: reason`,
PDF table-of-contents mismatch, embeddings unavailable after retries, database error). On `1`
the owned tables are unchanged; `embedding_cache` may keep vectors computed before the failure.

**Output**. First line, always: `target: <host>/<dbname> (local|remote)`. The URL, user and
password are never printed. On success:

```text
categories        9  <md5>
products         65  <md5>
promotions       25  <md5>
customers        50  <md5>
orders           20  <md5>
order_items      22  <md5>
policy_chunks    NN  <md5>      # PR B
product_search_docs 65 <md5>    # PR B
embeddings: provider=fake model=fake-ngram-v1 computed=N reused=M   # PR B
report: ../docs/data-quality-report.md
```

Logs go to stderr.
