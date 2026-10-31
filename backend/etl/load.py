"""Reloads the tables this feature owns, in one locked transaction (research R7)."""

from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

SCHEMA = Path(__file__).with_name("schema.sql")

# Insert order (parents first). The seed drops these and nothing else; embedding_cache persists.
OWNED_TABLES = ("categories", "products", "promotions", "customers", "orders", "order_items")


async def reload(conn: psycopg.AsyncConnection, tables: dict[str, list[dict]]) -> None:
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext('emporio:seed'))")
        # One statement, no CASCADE: dependencies among owned tables are fine, but a table from
        # another feature that references them makes this fail instead of being touched.
        await conn.execute(f"DROP TABLE IF EXISTS {', '.join(reversed(OWNED_TABLES))}")
        await conn.execute(SCHEMA.read_text())
        async with conn.cursor() as cur:
            for table in OWNED_TABLES:
                rows = tables[table]
                if not rows:
                    continue
                columns = list(rows[0])
                sql = (
                    f"INSERT INTO {table} ({', '.join(columns)}) "
                    f"VALUES ({', '.join(['%s'] * len(columns))})"
                )
                await cur.executemany(sql, [[_adapt(row[c]) for c in columns] for row in rows])


def _adapt(value: object) -> object:
    return Jsonb(value) if isinstance(value, dict) else value
