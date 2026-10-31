# Quickstart: Data Foundation

Validation guide proving the feature end to end. Contracts: [seed CLI](contracts/seed-cli.md),
[retrieval API](contracts/retrieval-api.md), [report](contracts/data-quality-report.md).

## Prerequisites

- Docker and `uv` installed; repo cloned.
- `cp backend/.env.example backend/.env` (defaults: local Postgres on 5433, `EMBEDDINGS_PROVIDER=fake`).

## PR A: store data and report

### 1. Local seed

```bash
docker compose up -d db
cd backend
uv sync
uv run python -m etl
```

**Expected**:
- the first line is `target: localhost/emporio (local)`;
- exit 0, with stdout listing 9 categories, 65 products, 25 promotions, 50 customers, 20 orders
  and 22 order items, each with a checksum;
- `git diff ../docs/data-quality-report.md` is empty.

### 2. Idempotency

```bash
uv run python -m etl > /tmp/run1.txt && uv run python -m etl > /tmp/run2.txt
diff <(grep -v '^embeddings:' /tmp/run1.txt) <(grep -v '^embeddings:' /tmp/run2.txt)
```

**Expected**: no diff.

### 3. Safety refusals

```bash
DATABASE_URL=postgresql://u:p@example.com/db uv run python -m etl         # refused: needs --yes
ENVIRONMENT=production uv run python -m etl                                # refused: fake embedder in production
```

**Expected**: exit 1, the target is printed, and the password is not.

### 4. Tests

```bash
uv run pytest
```

**Expected**: green, including one test per correction rule, the CRLF/NFD fixtures, orders 1/9
NULL handling, the 4 effective promotions and the report drift check.

## PR B: retrieval and production

### 5. Retrieval check (fake embedder)

```bash
uv run python -m etl
uv run python -c "
import asyncio
from app.config import get_settings
from app.db import get_pool
from app.embeddings import get_embedder
from app.retrieval import search_policies, similar_to_product, ProductFilters
async def main():
    s = get_settings()
    async with get_pool(s).connection() as c:
        r = await search_policies(c, get_embedder(s, purpose='query'), 'posso devolver meu pedido?')
        print(r.mode, [(h.section, h.breadcrumb) for h in r.hits[:3]])
        p = await similar_to_product(c, 96, filters=ProductFilters(only_sellable=True, category_id=5))
        print([h.product_id for h in p.hits])
asyncio.run(main())"
```

**Expected**: `hybrid`, with `4.1` among the first three; the similar products exclude 96 and are
all sellable violões.

### 6. Opt-in real provider

```bash
EMBEDDINGS_PROVIDER=gemini GEMINI_API_KEY=... uv run python -m etl
EMBEDDINGS_PROVIDER=gemini GEMINI_API_KEY=... uv run pytest -m gemini
```

**Expected**: the seed takes under 2 min on the free tier (any 429 is retried after the
returned delay); a second seed has `computed=0`; EN/ES queries put §4.1 in the top 3.

### 7. Production (Neon)

```bash
DATABASE_URL_UNPOOLED='<neon direct url>' ENVIRONMENT=production \
EMBEDDINGS_PROVIDER=gemini GEMINI_API_KEY=... uv run python -m etl --yes
```

**Expected**:
- `target: <neon host>/<db> (remote)` and exit 0;
- the **store tables** (categories, products, promotions, customers, orders, order_items) have
  the same counts and checksums as locally. `policy_chunks`, `product_search_docs` and
  `index_metadata` differ by design (Gemini vs fake vectors);
- tables not owned by this feature are unchanged.
