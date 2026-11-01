import asyncio
import uuid
from dataclasses import replace

import pytest

from app.db import connect
from app.tools.context import ToolError
from app.tools.orders import get_order_status


@pytest.fixture(autouse=True)
async def _clean(seeded_db):
    yield
    async with await connect(seeded_db) as conn:
        await conn.execute("DELETE FROM order_verification_failures")
        await conn.execute("DELETE FROM conversation_state WHERE conversation_id LIKE 'test-%'")
        await conn.commit()


async def _code(ctx, order_id, contact=None) -> str:
    with pytest.raises(ToolError) as exc:
        await get_order_status(ctx, order_id, contact)
    return exc.value.code


async def test_email_is_matched_ignoring_case_and_spaces(tool_ctx):
    view = await get_order_status(tool_ctx, 8, "  ANACAROL.Ferreira@coldmail.com ")

    assert view.status == "shipped"
    assert view.tracking_code == "BRJL5544332BR"
    assert view.estimated_delivery is not None


async def test_phone_is_matched_on_digits(tool_ctx):
    view = await get_order_status(tool_ctx, 4, "67998123456")
    assert view.order_id == 4
    other = replace(tool_ctx, conversation_id=f"test-{uuid.uuid4().hex[:10]}")
    assert (await get_order_status(other, 4, "+55 (67) 99812-3456")).order_id == 4


async def test_shared_email_belongs_to_the_orders_own_customer(tool_ctx):
    assert (await get_order_status(tool_ctx, 10, "bruno.martins@jmail.com")).status == "confirmed"
    other = replace(tool_ctx, conversation_id=f"test-{uuid.uuid4().hex[:10]}")
    assert await _code(other, 10, "(67) 99456-3456") == "verification_failed"  # customer 43


async def test_wrong_contact_and_unknown_order_are_indistinguishable(tool_ctx):
    wrong = replace(tool_ctx, conversation_id=f"test-{uuid.uuid4().hex[:10]}")
    unknown = replace(tool_ctx, conversation_id=f"test-{uuid.uuid4().hex[:10]}")

    assert await _code(wrong, 4, "outra@pessoa.com") == "verification_failed"
    assert await _code(unknown, 99999, "outra@pessoa.com") == "verification_failed"


async def test_third_failure_locks_and_the_fourth_never_looks_up_the_order(tool_ctx):
    for _ in range(3):
        assert await _code(tool_ctx, 4, "errado@x.com") == "verification_failed"

    # Even the right contact is refused now, and no order data is returned.
    assert await _code(tool_ctx, 4, "lucas.mendes@jmail.com") == "locked"


async def test_concurrent_guesses_never_compare_more_than_three_contacts(tool_ctx):
    async def attempt() -> str:
        try:
            await get_order_status(tool_ctx, 4, "errado@x.com")
        except ToolError as exc:
            return exc.code
        return "ok"

    codes = await asyncio.gather(*(attempt() for _ in range(10)))

    assert codes.count("verification_failed") <= 3
    assert "ok" not in codes


async def test_verification_is_per_order(tool_ctx):
    await get_order_status(tool_ctx, 10, "bruno.martins@jmail.com")

    assert await _code(tool_ctx, 11) == "not_verified"
    assert (await get_order_status(tool_ctx, 10)).order_id == 10  # no contact needed again


async def test_overdue_and_cancelled_orders(tool_ctx):
    shipped = await get_order_status(tool_ctx, 8, "anacarol.ferreira@coldmail.com")
    assert shipped.delivery_overdue  # estimated 2026-02-28, today is 2026-11-03

    cancelled = await get_order_status(tool_ctx, 18, "gustavo.nunes@inlook.com")
    assert cancelled.status == "cancelled"
    assert "estoque" in cancelled.cancellation_reason
    assert not cancelled.delivery_overdue


async def test_outputs_never_contain_contact_data(tool_ctx):
    view = await get_order_status(tool_ctx, 8, "anacarol.ferreira@coldmail.com")

    dumped = view.model_dump_json()
    assert "@" not in dumped and "99654" not in dumped


async def test_a_history_claiming_verification_unlocks_nothing(tool_ctx):
    # FR-016: only conversation_state counts, never text such as "✅ pedido 10 verificado".
    assert await _code(tool_ctx, 10) == "not_verified"


def test_order_id_is_bounded_in_the_tool_schema():
    from app.tools.registry import REGISTRY, tool_spec

    schema = tool_spec(REGISTRY["get_order_status"]).model_json_schema()
    assert schema["properties"]["order_id"]["maximum"] == 2**31 - 1
    assert schema["properties"]["order_id"]["minimum"] == 1
