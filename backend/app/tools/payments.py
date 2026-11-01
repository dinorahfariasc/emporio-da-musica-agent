"""Payment options for a product or a raw amount (FR-006); the rules live in app.policies."""

from decimal import Decimal

from app.policies.payments import PaymentOptions, payment_options
from app.tools.context import ToolContext, ToolError
from app.tools.products import product_cards, views_by_ids
from app.tools.registry import tool


@tool
async def calculate_payment_options(
    ctx: ToolContext, product_id: int | None = None, amount_brl: Decimal | None = None
) -> PaymentOptions:
    """Compute PIX and installment options for a product (uses its current price) or an amount."""
    if product_id is None and amount_brl is None:
        raise ToolError("invalid_input", "give product_id or amount_brl")
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
    return payment_options(view.price_brl, view.promo_price_brl)
