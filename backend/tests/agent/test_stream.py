import json

import pytest
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from app.agent.fakes import FakeToolModel
from app.agent.prompts import ERROR_MESSAGES
from app.agent.stream import to_ui_stream
from app.chat import protocol as p
from app.tools.context import ToolError
from app.tools.registry import langchain_tools

ROUTE = p.Route(intent="product_search", confidence=0.9, router="fake")
CARD = {
    "id": 81,
    "name": "Yamaha C40",
    "categoryId": 5,
    "priceBrl": 599.9,
    "promoPriceBrl": None,
    "discountPercent": None,
    "availability": "in_stock",
}


@tool
async def find(query: str) -> dict:
    """Find products."""
    get_stream_writer()({"type": "data-products", "id": "cards-1", "data": {"products": [CARD]}})
    return {"count": 1, "productIds": [81]}


async def _missing(ctx, query: str) -> dict:
    """Always fails."""
    raise ToolError("not_found")


boom = langchain_tools(None, ["boom"], {"boom": _missing})[0]  # type: ignore[arg-type]
boom.name = "boom"


def _call(name, args, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


async def _lines(script, tools, *, config=None, lang="pt"):
    agent = create_agent(FakeToolModel(script=script), tools)
    events = agent.astream(
        {"messages": [("human", "oi")]},
        stream_mode=["messages", "updates", "custom"],
        config=config or {},
    )
    out = []
    async for line in to_ui_stream(events, route=ROUTE, model_name="fake", lang=lang):
        out.append(line)
    return out


def _chunks(lines):
    parsed = []
    for line in lines:
        payload = line.removeprefix("data: ").strip()
        if payload != "[DONE]":
            parsed.append(p.chunk_adapter.validate_python(json.loads(payload)))
    return parsed


async def test_order_matches_the_contract_for_a_tool_turn():
    lines = await _lines([_call("find", {"query": "violão"}), "Achei um violão."], [find])
    types = [c.type for c in _chunks(lines)]

    assert lines[-1] == p.DONE
    assert types == [
        "start",
        "start-step",
        "tool-input-available",
        "tool-output-available",
        "data-products",
        "finish-step",
        "start-step",
        "text-start",
        "text-delta",
        "text-delta",
        "text-delta",
        "text-end",
        "finish-step",
        "message-metadata",
        "finish",
    ]


async def test_tool_output_and_cards_carry_the_data():
    chunks = _chunks(await _lines([_call("find", {"query": "x"}), "ok"], [find]))

    output = next(c for c in chunks if c.type == "tool-output-available")
    cards = next(c for c in chunks if c.type == "data-products")
    assert output.output == {"count": 1, "productIds": [81]}
    assert cards.data.products[0].id == 81


async def test_tool_error_becomes_tool_output_error_with_the_code():
    chunks = _chunks(await _lines([_call("boom", {"query": "x"}), "Não achei."], [boom]))

    error = next(c for c in chunks if c.type == "tool-output-error")
    assert error.error_text == "not_found"
    assert chunks[-1].type == "finish"


async def test_metadata_has_route_model_and_zero_usage_with_fakes():
    chunks = _chunks(await _lines(["Olá!"], []))

    meta = next(c for c in chunks if c.type == "message-metadata").message_metadata
    assert meta.route.intent == "product_search" and meta.model == "fake"
    assert (meta.usage.input_tokens, meta.usage.output_tokens) == (0, 0)


async def test_recursion_limit_yields_one_catalog_error_then_done():
    loop = [_call("find", {"query": "x"}, f"c{i}") for i in range(10)]

    lines = await _lines(loop, [find], config={"recursion_limit": 4})

    chunks = _chunks(lines)
    errors = [c for c in chunks if c.type == "error"]
    assert len(errors) == 1
    assert errors[0].error_text == ERROR_MESSAGES["pt"]["too_many_steps"]
    assert lines[-1] == p.DONE and chunks[-1].type == "error"


@pytest.mark.parametrize(
    ("exc", "kind"), [(TimeoutError("x"), "timeout"), (RuntimeError("secret"), "internal")]
)
async def test_other_failures_never_leak_the_exception_text(exc, kind):
    async def failing():
        raise exc
        yield  # pragma: no cover

    lines = [line async for line in to_ui_stream(failing(), route=ROUTE, model_name="fake")]

    error = _chunks(lines)[-1]
    assert error.error_text == ERROR_MESSAGES["pt"][kind]
    assert "secret" not in "".join(lines)
