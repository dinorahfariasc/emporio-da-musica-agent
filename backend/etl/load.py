"""Reloads the tables this feature owns, in one locked transaction (research R7)."""

from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

HERE = Path(__file__).parent
CACHE_SCHEMA = HERE / "cache.sql"
SCHEMA = HERE / "schema.sql"

# Insert order (parents first). The seed drops these and nothing else; embedding_cache persists.
# A new table that references one of these must be added here (and to schema.sql); otherwise the
# drop fails, by design, because the seed never touches tables it does not own.
STORE_TABLES = ("categories", "products", "promotions", "customers", "orders", "order_items")
# Derived search index; rebuilt from the store tables and the policy PDF on every seed.
INDEX_TABLES = ("policy_chunks", "product_search_docs", "index_metadata")
OWNED_TABLES = STORE_TABLES + INDEX_TABLES


async def ensure_cache(conn: psycopg.AsyncConnection) -> None:
    """Creates embedding_cache (committed on its own) so paid embeddings survive a failed seed."""
    await conn.execute(CACHE_SCHEMA.read_text())
    await conn.commit()


async def reload(conn: psycopg.AsyncConnection, tables: dict[str, list[dict]]) -> None:
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext('emporio:seed'))")
        # One statement, no CASCADE: dependencies among owned tables are fine, but a table from
        # another feature that references them makes this fail instead of being touched.
        await conn.execute(f"DROP TABLE IF EXISTS {', '.join(reversed(OWNED_TABLES))}")
        await conn.execute(CACHE_SCHEMA.read_text())
        await conn.execute(SCHEMA.read_text())
        async with conn.cursor() as cur:
            for table in OWNED_TABLES:
                rows = tables[table]
                if not rows:
                    continue
                columns = list(rows[0])
                marks = ["%s::vector" if c == "embedding" else "%s" for c in columns]
                sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(marks)})"
                await cur.executemany(sql, [[_adapt(row[c]) for c in columns] for row in rows])


def _adapt(value: object) -> object:
    return Jsonb(value) if isinstance(value, dict) else value
