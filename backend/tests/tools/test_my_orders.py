import uuid
from dataclasses import replace

import pytest

from app.db import connect
from app.tools.context import ToolError
from app.tools.orders import find_my_orders, get_order_status


@pytest.fixture(autouse=True)
async def _clean(seeded_db):
    yield
    async with await connect(seeded_db) as conn:
        await conn.execute("DELETE FROM order_verification_failures")
        await conn.execute("DELETE FROM conversation_state WHERE conversation_id LIKE 'test-%'")
        await conn.commit()


def _fresh(ctx):
    return replace(ctx, conversation_id=f"test-{uuid.uuid4().hex[:10]}")


async def _code(coro) -> str:
    with pytest.raises(ToolError) as exc:
        await coro
    return exc.value.code


async def test_email_lists_every_order_of_the_customer(tool_ctx):
    result = await find_my_orders(tool_ctx, "Pedro.Oliveira@jmail.com")

    assert result.first_name == "Pedro"
    assert [(o.order_id, o.status) for o in result.orders] == [(1, "delivered"), (19, "cancelled")]


async def test_found_orders_are_verified_for_the_rest_of_the_conversation(tool_ctx):
    await find_my_orders(tool_ctx, "(67) 98432-1098")

    view = await get_order_status(tool_ctx, 19)  # no contact needed any more
    assert view.status == "cancelled"


async def test_a_name_alone_is_not_proof(tool_ctx):
    assert await _code(find_my_orders(tool_ctx, "Pedro Henrique Oliveira")) == "invalid_input"


async def test_an_unknown_contact_fails_without_saying_why(tool_ctx):
    assert await _code(find_my_orders(tool_ctx, "ninguem@exemplo.com")) == "verification_failed"


async def test_a_shared_email_needs_the_full_name_or_the_phone(tool_ctx):
    assert await _code(find_my_orders(tool_ctx, "bruno.martins@jmail.com")) == "invalid_input"

    by_name = await find_my_orders(
        _fresh(tool_ctx), "bruno.martins@jmail.com", full_name="bruno carvalho MARTINS"
    )
    assert [o.order_id for o in by_name.orders] == [10]

    by_phone = await find_my_orders(_fresh(tool_ctx), "(67) 99456-3456")
    assert by_phone.first_name == "Bruno" and by_phone.orders == []


async def test_a_name_that_does_not_match_the_contact_fails(tool_ctx):
    coro = find_my_orders(tool_ctx, "pedro.oliveira@jmail.com", full_name="Maria Souza")
    assert await _code(coro) == "verification_failed"


async def test_name_matching_ignores_accents(tool_ctx):
    result = await find_my_orders(
        tool_ctx, "leticia.rocha@jmail.com", full_name="Leticia Goncalves Rocha"
    )
    assert [o.order_id for o in result.orders] == [7]


async def test_three_wrong_contacts_lock_the_conversation(tool_ctx):
    for guess in ("a@x.com", "b@x.com", "c@x.com"):
        assert await _code(find_my_orders(tool_ctx, guess)) == "verification_failed"

    assert await _code(find_my_orders(tool_ctx, "pedro.oliveira@jmail.com")) == "locked"


async def test_outputs_never_contain_contact_data(tool_ctx):
    dumped = (await find_my_orders(tool_ctx, "pedro.oliveira@jmail.com")).model_dump_json()
    assert "@" not in dumped and "98432" not in dumped and "Oliveira" not in dumped


async def test_order_view_explains_payment_region_and_age(tool_ctx):
    view = await get_order_status(tool_ctx, 13, "fernanda.ribeiro@coldmail.com")
    assert view.status == "pending"
    assert view.payment_method == "pix"
    assert view.shipping_region == "campo_grande"
    assert view.order_age_days == 236  # 2026-03-12 → clock 2026-11-03

    far = await get_order_status(_fresh(tool_ctx), 10, "bruno.martins@jmail.com")
    assert far.shipping_region == "other_city"  # Três Lagoas
