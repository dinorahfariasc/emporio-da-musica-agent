from dataclasses import replace
from datetime import datetime

import pytest

from app.db import connect
from app.tools.actions import (
    check_return_eligibility,
    handoff_to_human,
    register_complaint,
    request_return,
)
from app.tools.context import STORE_TZ, FixedClock, ToolError
from app.tools.orders import get_order_status

# Order 4: bought 2025-12-10, delivered (estimated) 2025-12-22; phone below.
PHONE = "67998123456"


@pytest.fixture(autouse=True)
async def _clean(seeded_db):
    yield
    async with await connect(seeded_db) as conn:
        await conn.execute("DELETE FROM order_verification_failures")
        await conn.execute("DELETE FROM service_requests WHERE conversation_id LIKE 'test-%'")
        await conn.execute("DELETE FROM conversation_state WHERE conversation_id LIKE 'test-%'")
        await conn.commit()


def _on(ctx, year, month, day):
    return replace(ctx, clock=FixedClock(datetime(year, month, day, 10, 0, tzinfo=STORE_TZ)))


async def _verified(ctx, on=(2025, 12, 25)):
    ctx = _on(ctx, *on)
    await get_order_status(ctx, 4, PHONE)
    return ctx


async def _rows(seeded_db, conversation_id):
    async with await connect(seeded_db) as conn:
        cur = await conn.execute(
            "SELECT type, order_id, reason, eligibility FROM service_requests "
            "WHERE conversation_id = %s",
            (conversation_id,),
        )
        return await cur.fetchall()


async def _code(awaitable) -> str:
    with pytest.raises(ToolError) as exc:
        await awaitable
    return exc.value.code


async def test_eligibility_needs_a_verified_order(tool_ctx):
    assert await _code(check_return_eligibility(tool_ctx, 4, "defect")) == "not_verified"


async def test_check_is_read_only(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx)
    result = await check_return_eligibility(ctx, 4, "regret", True)
    assert result.eligible and result.rule == "4.1"
    assert await _rows(seeded_db, ctx.conversation_id) == []


async def test_regret_return_is_recorded_on_explicit_request(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx)
    receipt = await request_return(
        ctx, 4, "regret", "Não gostei, ligue em 67998123456", True, bought_online=True
    )
    assert receipt.type == "return" and receipt.request_id > 0
    [(kind, order_id, reason, decision)] = await _rows(seeded_db, ctx.conversation_id)
    assert (kind, order_id) == ("return", 4)
    assert "67998123456" not in reason  # personal data masked
    assert decision["rule"] == "4.1" and decision["eligible"] is True


async def test_nothing_is_recorded_without_confirmation(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx)
    code = await _code(request_return(ctx, 4, "regret", "devolver", False, bought_online=True))
    assert code == "not_confirmed"
    assert await _code(register_complaint(ctx, "atraso")) == "not_confirmed"
    assert await _code(handoff_to_human(ctx, "quero falar com alguém")) == "not_confirmed"
    assert await _rows(seeded_db, ctx.conversation_id) == []


async def test_an_ineligible_return_is_refused_and_not_recorded(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx, on=(2026, 3, 1))  # 69 days after delivery
    code = await _code(request_return(ctx, 4, "regret", "devolver", True, bought_online=True))
    assert code == "not_eligible"
    assert await _rows(seeded_db, ctx.conversation_id) == []


async def test_regret_without_the_channel_is_not_recorded(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx)
    assert await _code(request_return(ctx, 4, "regret", "devolver", True)) == "not_eligible"


async def test_defect_exchange_inside_30_days(tool_ctx, seeded_db):
    ctx = await _verified(tool_ctx, on=(2026, 1, 5))
    receipt = await request_return(ctx, 4, "defect", "Trinca no braço", True)
    assert receipt.type == "exchange_defect"


async def test_request_for_an_unverified_order_is_refused(tool_ctx, seeded_db):
    ctx = _on(tool_ctx, 2025, 12, 25)
    assert await _code(request_return(ctx, 4, "defect", "x", True)) == "not_verified"


async def test_complaint_states_the_response_time(tool_ctx, seeded_db):
    receipt = await register_complaint(tool_ctx, "Atendimento demorado", True)
    assert receipt.response_within == "24 horas úteis"
    [(kind, order_id, _, decision)] = await _rows(seeded_db, tool_ctx.conversation_id)
    assert (kind, order_id, decision) == ("complaint", None, None)


async def test_complaint_about_an_order_needs_it_verified(tool_ctx):
    assert await _code(register_complaint(tool_ctx, "atraso", True, order_id=4)) == "not_verified"


async def test_handoff_gives_channel_and_hours(tool_ctx, seeded_db):
    receipt = await handoff_to_human(tool_ctx, "Quero falar com uma pessoa", True)
    assert "3321-4500" in receipt.channel and "3341-4444" in receipt.channel
    assert "09:00" in receipt.hours
    assert len(await _rows(seeded_db, tool_ctx.conversation_id)) == 1


async def test_reason_is_truncated(tool_ctx, seeded_db):
    await register_complaint(tool_ctx, "x" * 5000, True)
    [(_, _, reason, _)] = await _rows(seeded_db, tool_ctx.conversation_id)
    assert len(reason) == 1000
