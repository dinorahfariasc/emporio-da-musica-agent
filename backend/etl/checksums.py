"""Per-table row count and content checksum, to prove two seeds produce the same data."""

import psycopg

from etl.load import STORE_TABLES

PRIMARY_KEYS = {
    "categories": "category_id",
    "products": "product_id",
    "promotions": "promotion_id",
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_id, product_id",
}


async def table_stats(conn: psycopg.AsyncConnection) -> list[tuple[str, int, str]]:
    stats = []
    for table in STORE_TABLES:
        cur = await conn.execute(
            f"SELECT count(*), coalesce(md5(string_agg(row_to_json(t)::text, E'\\n' "
            f"ORDER BY {PRIMARY_KEYS[table]})), '') FROM {table} t"
        )
        count, checksum = await cur.fetchone()
        stats.append((table, count, checksum))
    return stats
