from langchain_core.messages import AIMessage, ToolMessage

from app.agent.agent import build_agent
from app.agent.fakes import FakeToolModel
from app.agent.router import Route
from app.config import Settings

SETTINGS = Settings(_env_file=None)
CALLS: list[str] = []


async def search_products(ctx, query: str) -> dict:
    """Search."""
    CALLS.append("search_products")
    return {"ok": True}


async def get_order_status(ctx, order_id: int) -> dict:
    """Order."""
    CALLS.append("get_order_status")
    return {"ok": True}


REGISTRY = {"search_products": search_products, "get_order_status": get_order_status}


def _call(name, args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "c1"}])


def _build(route, script):
    model = FakeToolModel(script=script)
    agent, routed = build_agent(
        SETTINGS,
        None,
        route,
        model_factory=lambda role: model,
        registry=REGISTRY,  # type: ignore[arg-type]
    )
    return agent, routed, model


async def test_confident_product_search_uses_the_specialist_and_its_tools():
    agent, routed, _ = _build(
        Route(intent="product_search", confidence=0.95),
        [_call("search_products", {"query": "x"}), "ok"],
    )
    CALLS.clear()

    await agent.ainvoke({"messages": [("human", "violão")]})

    assert routed.path == "specialist"
    assert routed.model == SETTINGS.specialist_model
    assert CALLS == ["search_products"]


async def test_an_off_list_tool_request_is_refused_and_nothing_runs():
    agent, _, _ = _build(
        Route(intent="product_search", confidence=0.95),
        [_call("get_order_status", {"order_id": 4}), "Não posso."],
    )
    CALLS.clear()

    result = await agent.ainvoke({"messages": [("human", "pedido 4")]})

    assert CALLS == []
    tool_message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_message.status == "error"


async def test_unclear_goes_to_the_general_path_with_every_tool():
    agent, routed, _ = _build(
        Route(intent="unclear", confidence=0.0), [_call("get_order_status", {"order_id": 4}), "ok"]
    )
    CALLS.clear()

    await agent.ainvoke({"messages": [("human", "hm")]})

    assert routed.path == "general"
    assert routed.model == SETTINGS.general_model
    assert CALLS == ["get_order_status"]


async def test_greeting_uses_the_specialist_model_without_tools():
    _, routed, _ = _build(Route(intent="greeting", confidence=0.99), ["Olá!"])
    assert (routed.path, routed.model) == ("specialist", SETTINGS.specialist_model)


def test_system_prompt_carries_the_store_date():
    from datetime import datetime

    from app.agent.prompts import system_prompt
    from app.tools.context import STORE_TZ

    text = system_prompt("store_info", datetime(2026, 11, 7, 13, 1, tzinfo=STORE_TZ))
    assert "07/11/2026 13:01 (sábado)" in text
    assert "sexta-feira" in system_prompt(None, datetime(2026, 11, 6, 9, 0, tzinfo=STORE_TZ))
