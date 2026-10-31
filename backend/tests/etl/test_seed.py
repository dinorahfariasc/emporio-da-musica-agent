import hashlib
import shutil
from pathlib import Path

import pytest

from app.db import connect
from etl.__main__ import seed
from etl.checksums import table_stats
from etl.pipeline import DATA_DIR


def _fingerprint(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.iterdir()):
        digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()


async def _stats(url: str):
    async with await connect(url) as conn:
        return await table_stats(conn)


async def _fetch(url: str, sql: str):
    async with await connect(url) as conn:
        cur = await conn.execute(sql)
        return await cur.fetchall()


async def test_seed_loads_store_tables_and_is_idempotent(local_database_url, tmp_path):
    before = _fingerprint(DATA_DIR)

    await seed(local_database_url, report_path=tmp_path / "report.md")
    first = await _stats(local_database_url)
    await seed(local_database_url, report_path=tmp_path / "report.md")
    second = await _stats(local_database_url)

    assert {t: n for t, n, _ in first} == {
        "categories": 9,
        "products": 65,
        "promotions": 25,
        "customers": 50,
        "orders": 20,
        "order_items": 22,
    }
    assert first == second
    assert _fingerprint(DATA_DIR) == before


async def test_seeded_facts(local_database_url, tmp_path):
    await seed(local_database_url, report_path=tmp_path / "report.md")

    assert await _fetch(
        local_database_url,
        "SELECT product_id, effective_discount_percent FROM products "
        "WHERE effective_promotion_id IS NOT NULL ORDER BY product_id",
    ) == [(90, 18), (94, 8), (121, 20), (127, 10)]
    assert await _fetch(
        local_database_url, "SELECT promo_price_brl::text FROM products WHERE product_id = 90"
    ) == [("1967.18",)]
    assert await _fetch(
        local_database_url,
        "SELECT order_id, total_brl::text, items_total_brl::text FROM orders "
        "WHERE total_mismatch ORDER BY order_id",
    ) == [(3, "3450.00", "3498.00"), (20, "1400.00", "1488.00")]
    assert await _fetch(
        local_database_url,
        "SELECT tracking_code, estimated_delivery FROM orders WHERE order_id = 9",
    ) == [(None, None)]
    assert await _fetch(
        local_database_url,
        "SELECT product_id, availability FROM products "
        "WHERE product_id IN (96, 113, 130, 136) ORDER BY product_id",
    ) == [(96, "out_of_stock"), (113, "discontinued"), (130, "coming_soon"), (136, "discontinued")]


async def test_validation_error_leaves_database_unchanged(local_database_url, tmp_path):
    await seed(local_database_url, report_path=tmp_path / "report.md")
    before = await _stats(local_database_url)
    broken = tmp_path / "data"
    shutil.copytree(DATA_DIR, broken)
    csv = broken / "products.csv"
    csv.write_bytes(csv.read_bytes().replace(b",active,", b",archived,", 1))

    with pytest.raises(Exception, match="status"):
        await seed(local_database_url, data_dir=broken, report_path=tmp_path / "broken.md")

    assert await _stats(local_database_url) == before
    assert not (tmp_path / "broken.md").exists()


async def test_reseed_restores_the_declared_schema(local_database_url, tmp_path):
    await seed(local_database_url, report_path=tmp_path / "report.md")
    async with await connect(local_database_url) as conn:
        await conn.execute("ALTER TABLE products ADD COLUMN stale_column int")
        await conn.commit()

    await seed(local_database_url, report_path=tmp_path / "report.md")

    columns = await _fetch(
        local_database_url,
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'products'",
    )
    assert ("stale_column",) not in columns
