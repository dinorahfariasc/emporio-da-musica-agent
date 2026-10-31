from decimal import Decimal

from app.retrieval import ProductFilters, search_products, similar_to_product

NOT_SELLABLE = {96, 113, 130, 136}


async def test_exact_model_ranks_first(conn, embedder):
    result = await search_products(conn, embedder, "Yamaha C40")

    top = result.hits[0]
    assert top.product_id == 81
    assert top.category_id == 5
    assert top.availability == "in_stock"


async def test_filters(conn, embedder):
    sellable = await search_products(
        conn,
        embedder,
        "baixo guitarra violão",
        filters=ProductFilters(only_sellable=True),
        limit=65,
    )
    assert not NOT_SELLABLE & {h.product_id for h in sellable.hits}

    violoes = await search_products(
        conn, embedder, "violão", filters=ProductFilters(category_id=5), limit=65
    )
    assert violoes.hits and {h.category_id for h in violoes.hits} == {5}

    excluded = await search_products(
        conn, embedder, "Yamaha C40", filters=ProductFilters(exclude_ids=frozenset({81}))
    )
    assert 81 not in {h.product_id for h in excluded.hits}

    cheap = await search_products(
        conn, embedder, "violão", filters=ProductFilters(max_price=Decimal("1000")), limit=65
    )
    cur = await conn.execute("SELECT product_id FROM products WHERE promo_price_brl <= 1000")
    allowed = {r[0] for r in await cur.fetchall()}
    assert cheap.hits and {h.product_id for h in cheap.hits} <= allowed


async def test_similar_uses_stored_embedding_only(conn):
    result = await similar_to_product(
        conn, 96, filters=ProductFilters(only_sellable=True, category_id=None)
    )

    ids = {h.product_id for h in result.hits}
    assert result.mode == "vector"
    assert result.hits
    assert 96 not in ids and not NOT_SELLABLE & ids


async def test_similar_to_unknown_product_is_empty(conn):
    assert (await similar_to_product(conn, 99999)).hits == []
