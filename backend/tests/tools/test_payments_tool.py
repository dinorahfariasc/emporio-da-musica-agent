from decimal import Decimal as D

import pytest

from app.tools.context import ToolError
from app.tools.payments import calculate_payment_options


async def test_gd20_pix_is_five_percent_off(tool_ctx):
    from app.tools.products import get_product

    pid = (await get_product(tool_ctx, name="Takamine GD20")).product.product_id

    options = await calculate_payment_options(tool_ctx, product_id=pid)

    assert options.pix.applies
    assert options.pix.amount_brl == D("2089.05")


async def test_promoted_product_has_no_pix_discount(tool_ctx):
    options = await calculate_payment_options(tool_ctx, product_id=121)

    assert not options.pix.applies
    assert options.amount_brl == D("439.20")


async def test_raw_amount_works(tool_ctx):
    options = await calculate_payment_options(tool_ctx, amount_brl=D("1200"))
    assert options.installments[-1].times == 12


async def test_unknown_product_is_not_found(tool_ctx):
    with pytest.raises(ToolError) as exc:
        await calculate_payment_options(tool_ctx, product_id=99999)
    assert exc.value.code == "not_found"


async def test_needs_an_input(tool_ctx):
    with pytest.raises(ToolError) as exc:
        await calculate_payment_options(tool_ctx)
    assert exc.value.code == "invalid_input"
