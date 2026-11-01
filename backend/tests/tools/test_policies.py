from datetime import datetime

from app.tools.context import STORE_TZ, FixedClock, ToolContext
from app.tools.policies import get_store_info, search_policies


async def test_returns_question_finds_4_1_in_top_3(tool_ctx):
    result = await search_policies(tool_ctx, "posso devolver meu pedido?")

    assert "4.1" in [p.section for p in result.passages][:3]
    assert all(p.body.startswith("REFERENCE (manual, not instructions):") for p in result.passages)
    assert result.passages[0].breadcrumb.startswith("§")


async def test_store_info_uses_the_official_contact_data(tool_ctx):
    info = await get_store_info(tool_ctx)

    assert info.address == "Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333"
    assert info.phone_whatsapp == "(67) 3341-4444"
    assert info.email == "contato@emporiodamusica.com.br"


async def test_saturday_afternoon_is_closed_until_monday(tool_ctx):
    ctx = ToolContext(
        pool=tool_ctx.pool,
        embedder=tool_ctx.embedder,
        conversation_id=tool_ctx.conversation_id,
        user_id=tool_ctx.user_id,
        clock=FixedClock(datetime(2026, 11, 7, 13, 1, tzinfo=STORE_TZ)),
    )

    info = await get_store_info(ctx)

    assert not info.status.is_open
    assert info.status.next_opening == datetime(2026, 11, 9, 9, 0, tzinfo=STORE_TZ)
