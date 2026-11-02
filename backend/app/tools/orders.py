"""Order status behind a contact check (US3; FR-013…FR-017).

Only `conversation_state` unlocks an order: nothing a customer (or a history message) claims
counts. A wrong contact and an unknown order are indistinguishable from the outside.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

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
    payment_method: str
    # §5.1 (Campo Grande, 1–3 business days by motoboy) vs §5.2 (carriers, other cities).
    shipping_region: Literal["campo_grande", "other_city"]
    order_age_days: int


class OrderSummary(BaseModel):
    order_id: int
    order_date: date
    status: str
    total_brl: Decimal


class MyOrders(BaseModel):
    first_name: str
    orders: list[OrderSummary]


def _digits(contact: str) -> str:
    digits = re.sub(r"\D", "", contact)
    return digits[2:] if len(digits) > 11 and digits.startswith("55") else digits


def _same_contact(contact: str, email: str, phone_digits: str) -> bool:
    contact = contact.strip()
    if "@" in contact:
        return contact.casefold() == email.strip().casefold()
    digits = _digits(contact)
    return len(digits) >= 10 and digits == phone_digits


def _plain(text: str) -> str:
    """Case-, accent- and spacing-insensitive form for comparing names."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def _looks_like_contact(text: str) -> bool:
    return "@" in text or len(re.sub(r"\D", "", text)) >= 10


async def _view(conn: psycopg.AsyncConnection, order_id: int, today: date) -> OrderStatusView:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT o.order_id, o.status, o.order_date, o.total_brl, o.tracking_code, "
            "o.estimated_delivery, o.notes, o.payment_method, c.city "
            "FROM orders o JOIN customers c USING (customer_id) WHERE o.order_id = %s",
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
        payment_method=order["payment_method"],
        shipping_region="campo_grande" if _plain(order["city"]) == "campo grande" else "other_city",
        order_age_days=(today - order["order_date"]).days,
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
        current = await state.get(conn, ctx.user_id, ctx.conversation_id)
        if order_id in current.verified_order_ids:
            return await _view(conn, order_id, today)
        if not (contact or "").strip():
            raise ToolError("not_verified")

        # Count the attempt before comparing, so concurrent guesses cannot all get through.
        reservation = await state.reserve_attempt(conn, ctx.user_id, ctx.conversation_id, order_id)
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
        await state.confirm_success(conn, ctx.user_id, ctx.conversation_id, order_id)
        return await _view(conn, order_id, today)


@tool
async def find_my_orders(ctx: ToolContext, contact: str, full_name: str | None = None) -> MyOrders:
    """List the customer's own orders from the e-mail or phone on file (a name alone is not
    proof). When an e-mail is shared by two customers, also give the full name. Every order
    found is verified for the rest of the conversation."""
    if not _looks_like_contact(contact):
        raise ToolError("invalid_input", "give the e-mail or phone on file")
    async with ctx.pool.connection() as conn:
        reservation = await state.reserve_contact_attempt(conn, ctx.user_id, ctx.conversation_id)
        if not reservation.allowed:
            raise ToolError("locked")
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT customer_id, name, email, phone_digits FROM customers "
                "WHERE lower(email) = lower(%s) OR phone_digits = %s",
                (contact.strip(), _digits(contact)),
            )
            rows = await cur.fetchall()
        matches = [r for r in rows if _same_contact(contact, r["email"], r["phone_digits"])]
        if full_name is not None:
            matches = [r for r in matches if _plain(r["name"]) == _plain(full_name)]
        if not matches:
            raise ToolError("verification_failed")
        if len(matches) > 1:
            # A shared e-mail: give the attempt back and ask for the full name or the phone.
            await state.verify_orders(conn, ctx.user_id, ctx.conversation_id, [])
            raise ToolError("invalid_input", "contact shared by several customers")
        customer = matches[0]
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT order_id, order_date, status, total_brl FROM orders "
                "WHERE customer_id = %s ORDER BY order_id",
                (customer["customer_id"],),
            )
            orders = [OrderSummary(**r) for r in await cur.fetchall()]
        await state.verify_orders(
            conn, ctx.user_id, ctx.conversation_id, [o.order_id for o in orders]
        )
    return MyOrders(first_name=customer["name"].split()[0], orders=orders)
