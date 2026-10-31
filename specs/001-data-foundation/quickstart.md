# Quickstart: Data Foundation

Validation guide proving the feature end to end. Contracts: [seed CLI](contracts/seed-cli.md),
[retrieval API](contracts/retrieval-api.md), [report](contracts/data-quality-report.md).

## Prerequisites

- Docker and `uv` installed; repo cloned.
- `cp backend/.env.example backend/.env` (defaults: local Postgres on 5433, `EMBEDDINGS_PROVIDER=fake`).

## 1. Local seed with the fake embedder

```bash
docker compose up -d db
cd backend
uv sync
uv run python -m etl
```

**Expected**: exit 0; stdout lists 9 categories, 65 products, 25 promotions, 50 customers,
20 orders and 22 order items with checksums; `docs/data-quality-report.md` is regenerated, and
`git diff docs/data-quality-report.md` is empty on an unchanged dataset.

## 2. Idempotency

```bash
uv run python -m etl > /tmp/run1.txt
uv run python -m etl > /tmp/run2.txt
diff <(grep -v '^embeddings:' /tmp/run1.txt) <(grep -v '^embeddings:' /tmp/run2.txt)
```

**Expected**: no diff. The second run reports `computed=0` embeddings (all reused).

## 3. Dry run (no database)

```bash
uv run python -m etl --check
```

**Expected**: exit 0; prints the anomaly summary matching the data-model catalogue.

## 4. Tests

```bash
uv run pytest                   # unit + integration (integration needs DATABASE_URL)
uv run pytest -m voyage         # opt-in, needs VOYAGE_API_KEY; EN/ES → §4.1 top 3
```

**Expected**: green. Includes one test per correction rule, the §4.1 retrieval test with the fake
embedder, the full-text fallback test and the cache-hit test.

## 5. Manual retrieval check

```bash
uv run python -c "
import asyncio, psycopg
from app.config import get_settings
from app.embeddings import get_embedder
from app.retrieval import search_policies
async def main():
    s = get_settings()
    async with await psycopg.AsyncConnection.connect(s.database_url, prepare_threshold=None) as c:
        r = await search_policies(c, get_embedder(s, purpose='query'), 'posso devolver meu pedido?')
        print(r.mode, [(h.section, h.title) for h in r.hits[:3]])
asyncio.run(main())"
```

**Expected**: `hybrid` and `4.1` among the three sections.

## 6. Real provider (local)

Set `EMBEDDINGS_PROVIDER=voyage` and `VOYAGE_API_KEY`, then rerun steps 1 and 5. **Expected**:
`provider=voyage model=voyage-4`; a second run has `computed=0`.

## 7. Production (Neon)

```bash
DATABASE_URL='<neon url>' EMBEDDINGS_PROVIDER=voyage VOYAGE_API_KEY=... uv run python -m etl
```

**Expected**: exit 0 with the same row counts and store-table checksums as locally. Tables not
owned by this feature are unchanged (compare `\dt` row counts before and after).
