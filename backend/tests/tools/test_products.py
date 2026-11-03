from decimal import Decimal as D

import pytest

from app.tools.context import ToolError
from app.tools.products import (
    find_similar_products,
    get_active_promotions,
    get_product,
    search_products,
)

NOT_SELLABLE = {96, 113, 136}


async def test_violao_under_1000_only_sellable_violoes(tool_ctx):
    result = await search_products(
        tool_ctx, "violão", max_price_brl=D("1000"), only_sellable=True, limit=10
    )

    assert result.count > 0
    for product in result.products:
        assert product.category == "Violões"
        assert product.is_sellable
        assert (product.promo_price_brl or product.price_brl) <= 1000


async def test_get_product_by_name_without_promo(tool_ctx):
    lookup = await get_product(tool_ctx, name="Takamine GD20")

    assert lookup.product.price_brl == D("2199.00")
    assert lookup.product.promo_price_brl is None


async def test_product_exposes_its_stock_quantity(tool_ctx):
    product = (await get_product(tool_ctx, product_id=107)).product

    assert product.stock_quantity == 6


@pytest.mark.parametrize(("quantity", "enough"), [(5, True), (6, True), (7, False)])
async def test_requested_quantity_is_checked_against_stock(tool_ctx, quantity, enough):
    lookup = await get_product(tool_ctx, product_id=107, quantity=quantity)

    assert lookup.requested_quantity == quantity
    assert lookup.enough_stock is enough


async def test_unsellable_product_never_has_enough_stock(tool_ctx):
    lookup = await get_product(tool_ctx, product_id=113, quantity=1)

    assert lookup.enough_stock is False


async def test_promoted_product_shows_both_prices(tool_ctx):
    product = (await get_product(tool_ctx, product_id=121)).product

    assert product.promo_price_brl == D("439.20")
    assert product.price_brl == D("549.00")
    assert product.discount_percent == 20


async def test_discontinued_product_is_flagged_and_not_sellable(tool_ctx):
    product = (await get_product(tool_ctx, product_id=136)).product

    assert product.availability == "discontinued"
    assert not product.is_sellable
    assert not product.ready_to_ship


async def test_coming_soon_product_is_sold_without_immediate_delivery(tool_ctx):
    lookup = await get_product(tool_ctx, product_id=130, quantity=1)

    assert lookup.product.availability == "coming_soon"
    assert lookup.product.is_sellable
    assert not lookup.product.ready_to_ship
    assert lookup.enough_stock is None  # nothing on hand to count: it ships when it arrives


async def test_untrusted_description_is_hidden_and_name_wins(tool_ctx):
    product = (await get_product(tool_ctx, product_id=135)).product
    assert product.description is None

    # "Alder" and "single-coil" only appear in 135's untrusted description, so they must not
    # make it rank first (the specs say Ash).
    result = await search_products(tool_ctx, "baixo corpo em Alder captadores single-coil")
    assert result.products[0].product_id != 135


async def test_ambiguous_name_returns_candidates(tool_ctx):
    lookup = await get_product(tool_ctx, name="Yamaha")

    assert lookup.product is None
    assert len(lookup.candidates) > 1


async def test_unknown_product_is_not_found(tool_ctx):
    with pytest.raises(ToolError) as exc:
        await get_product(tool_ctx, product_id=99999)
    assert exc.value.code == "not_found"


async def test_get_product_needs_an_identifier(tool_ctx):
    with pytest.raises(ToolError) as exc:
        await get_product(tool_ctx)
    assert exc.value.code == "invalid_input"


async def test_active_promotions_are_exactly_the_four_known(tool_ctx):
    result = await get_active_promotions(tool_ctx)

    assert {p.product_id for p in result.products} == {90, 94, 121, 127}
    assert all(p.discount_percent for p in result.products)


async def test_cards_are_emitted_and_capped_at_six(tool_ctx, tool_events):
    await search_products(tool_ctx, "violão", limit=10, only_sellable=False)

    (event,) = tool_events
    assert event["type"] == "data-products"
    assert 0 < len(event["data"]["products"]) <= 6
    assert {"id", "name", "categoryId", "priceBrl", "promoPriceBrl"} <= set(
        event["data"]["products"][0]
    )


async def test_similar_excludes_the_product_and_unsellable_ones(tool_ctx):
    result = await find_similar_products(tool_ctx, product_id=96)

    ids = {p.product_id for p in result.products}
    assert 96 not in ids and not NOT_SELLABLE & ids
    assert len({p.category for p in result.products}) <= 1


async def test_similar_by_description_only_offers_sellable(tool_ctx):
    result = await find_similar_products(tool_ctx, description="baixo elétrico 4 cordas")

    assert result.products and all(p.is_sellable for p in result.products)


async def test_out_of_stock_product_gets_at_least_two_sellable_alternatives(tool_ctx):
    result = await find_similar_products(tool_ctx, product_id=96)

    assert len(result.products) >= 2
    assert all(p.is_sellable and p.category == "Violões" for p in result.products)


async def test_description_constraints_are_respected(tool_ctx):
    result = await find_similar_products(
        tool_ctx, description="violão elétrico de aço", max_price_brl=D("2000"), limit=3
    )

    assert result.products
    for product in result.products:
        assert (product.promo_price_brl or product.price_brl) <= 2000
        assert product.category == "Violões"
        assert product.specs["strings"] == "steel"
        assert product.specs["electronics"] == "yes"


async def test_an_empty_category_gives_an_empty_list_not_unrelated_products(tool_ctx):
    result = await search_products(tool_ctx, "flauta transversal", category_id=6)

    assert result.count == 0 and result.products == []


async def test_views_carry_specs_for_the_shared_trait_and_difference(tool_ctx):
    result = await find_similar_products(tool_ctx, product_id=95)

    assert all(p.specs for p in result.products)


async def test_description_search_can_be_limited_to_a_category(tool_ctx):
    result = await find_similar_products(
        tool_ctx, description="som suave para quem está começando", category_id=5, limit=5
    )

    assert result.products
    assert all(p.category == "Violões" and p.is_sellable for p in result.products)
