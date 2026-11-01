"""Order status behind a contact check (US3; FR-013…FR-017).

Only `conversation_state` unlocks an order: nothing a customer (or a history message) claims
counts. A wrong contact and an unknown order are indistinguishable from the outside.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.agent import state
from app.tools.context import ToolContext, ToolError
from app.tools.registry import tool


class OrderItemView(BaseModel):
    name: str
    quantity: int


class OrderStatusView(BaseModel):
    order_id: int
    status: str
    order_date: date
    items: list[OrderItemView]
    total_brl: Decimal
    tracking_code: str | None
    estimated_delivery: date | None
    delivery_overdue: bool
    cancellation_reason: str | None


def _same_contact(contact: str, email: str, phone_digits: str) -> bool:
    contact = contact.strip()
    if "@" in contact:
        return contact.casefold() == email.strip().casefold()
    digits = re.sub(r"\D", "", contact)
    if len(digits) > 11 and digits.startswith("55"):
        digits = digits[2:]
    return len(digits) >= 10 and digits == phone_digits


async def _view(conn: psycopg.AsyncConnection, order_id: int, today: date) -> OrderStatusView:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT order_id, status, order_date, total_brl, tracking_code, estimated_delivery, "
            "notes FROM orders WHERE order_id = %s",
            (order_id,),
        )
        order = await cur.fetchone()
        if order is None:
            raise ToolError("verification_failed")
        await cur.execute(
            "SELECT p.name, i.quantity FROM order_items i JOIN products p USING (product_id) "
            "WHERE i.order_id = %s ORDER BY p.product_id",
            (order_id,),
        )
        items = [OrderItemView(**r) for r in await cur.fetchall()]
    overdue = (
        order["status"] == "shipped"
        and order["estimated_delivery"] is not None
        and order["estimated_delivery"] < today
    )
    return OrderStatusView(
        order_id=order["order_id"],
        status=order["status"],
        order_date=order["order_date"],
        items=items,
        total_brl=order["total_brl"],
        tracking_code=order["tracking_code"],
        estimated_delivery=order["estimated_delivery"],
        delivery_overdue=overdue,
        cancellation_reason=order["notes"] if order["status"] == "cancelled" else None,
    )


@tool
async def get_order_status(
    ctx: ToolContext,
    order_id: Annotated[int, Field(ge=1, le=2**31 - 1)],
    contact: str | None = None,
) -> OrderStatusView:
    """Order status, tracking and delivery date. Needs the e-mail or phone on the order, unless
    this order was already verified in this conversation."""
    today = ctx.clock.now().date()
    async with ctx.pool.connection() as conn:
        current = await state.get(conn, ctx.conversation_id)
        if order_id in current.verified_order_ids:
            return await _view(conn, order_id, today)
        if not (contact or "").strip():
            raise ToolError("not_verified")

        # Count the attempt before comparing, so concurrent guesses cannot all get through.
        reservation = await state.reserve_attempt(conn, ctx.conversation_id, order_id)
        if not reservation.allowed:
            raise ToolError("locked")
        cur = await conn.execute(
            "SELECT c.email, c.phone_digits FROM orders o JOIN customers c USING (customer_id) "
            "WHERE o.order_id = %s",
            (order_id,),
        )
        row = await cur.fetchone()
        if row is None or not _same_contact(contact or "", *row):
            raise ToolError("verification_failed")
        await state.confirm_success(conn, ctx.conversation_id, order_id)
        return await _view(conn, order_id, today)
