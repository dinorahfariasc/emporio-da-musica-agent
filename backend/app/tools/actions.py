"""Actions that write (US6): return eligibility and requests, complaints, human handoff.

Every write needs an explicit customer request (FR-020): the system prompt asks for one, and
`confirmed_by_customer` is a second guard inside the tool. Orders are reachable only when verified
in this conversation (the same boundary as `get_order_status`).
"""

from typing import Annotated, Literal

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.agent import state
from app.agent.logging import mask_pii
from app.policies.returns import Eligibility, Reason, ReturnOrder, eligibility
from app.tools.context import ToolContext, ToolError
from app.tools.policies import PHONE, WHATSAPP
from app.tools.registry import tool

REASON_MAX_CHARS = 1000
COMPLAINT_RESPONSE_WITHIN = "24 horas úteis"  # §7.3
HANDOFF_HOURS = "Segunda a sexta, 09:00 às 18:00; sábado, 09:00 às 13:00 (horário de Campo Grande)"
REQUEST_TYPE = {
    "regret": "return",
    "defect": "exchange_defect",
    "preference": "exchange_preference",
}
OrderId = Annotated[int, Field(ge=1, le=2**31 - 1)]


class ReturnReceipt(BaseModel):
    request_id: int
    type: Literal["return", "exchange_defect", "exchange_preference"]
    next_step: str


class ComplaintReceipt(BaseModel):
    request_id: int
    response_within: str


class HandoffReceipt(BaseModel):
    request_id: int
    channel: str
    hours: str


def _clean(text: str) -> str:
    return mask_pii(text.strip())[:REASON_MAX_CHARS] or "(sem detalhes)"


async def _verified(conn: psycopg.AsyncConnection, ctx: ToolContext, order_id: int) -> None:
    current = await state.get(conn, ctx.user_id, ctx.conversation_id)
    if order_id not in current.verified_order_ids:
        raise ToolError("not_verified")


async def _decide(
    conn: psycopg.AsyncConnection,
    ctx: ToolContext,
    order_id: int,
    reason: Reason,
    bought_online: bool | None,
) -> Eligibility:
    await _verified(conn, ctx, order_id)
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT status, order_date, estimated_delivery FROM orders WHERE order_id = %s",
            (order_id,),
        )
        order = await cur.fetchone()
        if order is None:
            raise ToolError("not_verified")
        await cur.execute(
            "SELECT p.name FROM order_items i JOIN products p USING (product_id) "
            "WHERE i.order_id = %s",
            (order_id,),
        )
        names = tuple(row["name"] for row in await cur.fetchall())
    return eligibility(
        ReturnOrder(order["status"], order["order_date"], order["estimated_delivery"], names),
        reason,
        bought_online,
        ctx.clock.now().date(),
    )


async def _record(
    conn: psycopg.AsyncConnection,
    ctx: ToolContext,
    kind: str,
    reason: str,
    order_id: int | None = None,
    decision: Eligibility | None = None,
) -> int:
    cur = await conn.execute(
        "INSERT INTO service_requests (conversation_id, type, order_id, reason, eligibility) "
        "VALUES (%s, %s, %s, %s, %s::jsonb) RETURNING request_id",
        (
            ctx.conversation_id,
            kind,
            order_id,
            _clean(reason),
            decision.model_dump_json() if decision else None,
        ),
    )
    row = await cur.fetchone()
    assert row is not None
    return int(row[0])


def _require_confirmation(confirmed_by_customer: bool) -> None:
    if confirmed_by_customer is not True:
        raise ToolError("not_confirmed")


@tool
async def check_return_eligibility(
    ctx: ToolContext,
    order_id: OrderId,
    reason: Reason,
    bought_online: bool | None = None,
) -> Eligibility:
    """Whether a verified order can be returned (regret, online only) or exchanged (defect,
    preference). Reads only: records nothing. For regret, ask whether it was bought online."""
    async with ctx.pool.connection() as conn:
        return await _decide(conn, ctx, order_id, reason, bought_online)


@tool
async def request_return(
    ctx: ToolContext,
    order_id: OrderId,
    reason: Reason,
    details: str,
    confirmed_by_customer: bool = False,
    bought_online: bool | None = None,
) -> ReturnReceipt:
    """Opens a return or exchange request. Only after the customer explicitly asked for it and
    the eligibility check says eligible (it runs again here)."""
    _require_confirmation(confirmed_by_customer)
    async with ctx.pool.connection() as conn:
        decision = await _decide(conn, ctx, order_id, reason, bought_online)
        if not decision.eligible:
            raise ToolError("not_eligible")
        request_id = await _record(conn, ctx, REQUEST_TYPE[reason], details, order_id, decision)
    return ReturnReceipt(
        request_id=request_id,
        type=REQUEST_TYPE[reason],
        next_step="A equipe da loja entra em contato para combinar a coleta e o reembolso ou a "
        "troca. " + decision.next_step,
    )


@tool
async def register_complaint(
    ctx: ToolContext,
    summary: str,
    confirmed_by_customer: bool = False,
    order_id: OrderId | None = None,
) -> ComplaintReceipt:
    """Records a complaint, only after the customer explicitly asked. Citing an order needs it
    verified in this conversation."""
    _require_confirmation(confirmed_by_customer)
    async with ctx.pool.connection() as conn:
        if order_id is not None:
            await _verified(conn, ctx, order_id)
        request_id = await _record(conn, ctx, "complaint", summary, order_id)
    return ComplaintReceipt(request_id=request_id, response_within=COMPLAINT_RESPONSE_WITHIN)


@tool
async def handoff_to_human(
    ctx: ToolContext, reason: str, confirmed_by_customer: bool = False
) -> HandoffReceipt:
    """Records a handoff to a human attendant, only after the customer asked for one or after
    Melody explained it cannot resolve the issue and the customer agreed."""
    _require_confirmation(confirmed_by_customer)
    async with ctx.pool.connection() as conn:
        request_id = await _record(conn, ctx, "handoff", reason)
    return HandoffReceipt(
        request_id=request_id,
        channel=f"WhatsApp {WHATSAPP} ou telefone {PHONE}",
        hours=HANDOFF_HOURS,
    )


__all__ = [
    "check_return_eligibility",
    "handoff_to_human",
    "register_complaint",
    "request_return",
]
