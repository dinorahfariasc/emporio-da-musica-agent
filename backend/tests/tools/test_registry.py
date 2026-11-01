from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage

from app.agent.fakes import FakeToolModel
from app.tools.context import ToolContext, ToolError
from app.tools.registry import (
    CONTRACT_TOOL_NAMES,
    TOOLS_BY_INTENT,
    langchain_tools,
    tool_spec,
)


async def missing(ctx: ToolContext, order_id: int) -> dict:
    """Always not found."""
    raise ToolError("not_found")


async def crashing(ctx: ToolContext, text: str) -> dict:
    """Crashes with an internal error."""
    raise RuntimeError("secret internal detail")


def _call(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "c1"}])


async def _run(tools, script):
    agent = create_agent(FakeToolModel(script=script), tools)
    return (await agent.ainvoke({"messages": [("human", "go")]}))["messages"]


async def test_tool_error_becomes_an_error_message_and_the_run_continues():
    tools = langchain_tools(None, ["missing"], {"missing": missing})  # type: ignore[arg-type]

    messages = await _run(tools, [_call("missing", {"order_id": 1}), "Não encontrei."])

    tool_message = next(m for m in messages if isinstance(m, ToolMessage))
    assert tool_message.status == "error"
    assert tool_message.content == "not_found"
    assert messages[-1].content == "Não encontrei."


async def test_unexpected_exceptions_are_hidden_behind_unavailable():
    tools = langchain_tools(None, ["crashing"], {"crashing": crashing})  # type: ignore[arg-type]

    messages = await _run(tools, [_call("crashing", {"text": "x"}), "Erro."])

    tool_message = next(m for m in messages if isinstance(m, ToolMessage))
    assert tool_message.content == "unavailable"
    assert "secret" not in str(tool_message.content)


def test_schema_has_no_ctx():
    schema = tool_spec(missing).model_json_schema()
    assert list(schema["properties"]) == ["order_id"]
    assert schema["required"] == ["order_id"]


def test_intent_tool_sets_are_part_of_the_contract():
    used = {name for names in TOOLS_BY_INTENT.values() for name in names}
    assert used <= set(CONTRACT_TOOL_NAMES)
