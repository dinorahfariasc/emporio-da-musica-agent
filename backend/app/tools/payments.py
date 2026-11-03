"""Payment options for a product or a raw amount (FR-006); the rules live in app.policies."""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.policies.payments import PaymentOptions, payment_options
from app.tools.context import ToolContext, ToolError
from app.tools.products import get_product, product_cards, views_by_ids
from app.tools.registry import tool


@tool
async def calculate_payment_options(
    ctx: ToolContext,
    product_id: int | None = None,
    amount_brl: Decimal | None = None,
    quantity: Annotated[int, Field(ge=1)] = 1,
    name: str | None = None,
) -> PaymentOptions:
    """Compute PIX and installment options for a product (uses its current price, times
    `quantity` units) or an amount. Identify the product by `product_id`, or by `name` when the
    id is not known yet (for example, in the same step as get_product)."""
    if product_id is None and amount_brl is None and (name or "").strip():
        found = (await get_product(ctx, name=name)).product
        if found is None:
            raise ToolError("invalid_input", "ambiguous name: call get_product and pass product_id")
        product_id = found.product_id
    if product_id is None and amount_brl is None:
        raise ToolError("invalid_input", "give product_id, name or amount_brl")
    if product_id is None:
        if amount_brl <= 0:  # type: ignore[operator]
            raise ToolError("invalid_input", "amount_brl must be positive")
        return payment_options(amount_brl)  # type: ignore[arg-type]
    async with ctx.pool.connection() as conn:
        views = await views_by_ids(conn, [product_id])
    if not views:
        raise ToolError("not_found")
    product_cards(ctx, views)
    view = views[0]
    promo = view.promo_price_brl * quantity if view.promo_price_brl is not None else None
    return payment_options(view.price_brl * quantity, promo)
