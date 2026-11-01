from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agent.fakes import FakeRouter, FakeToolModel
from app.agent.router import Route


@tool
def echo(text: str) -> str:
    """Echo the text."""
    return f"echo:{text}"


async def test_tool_loop_calls_the_tool_then_streams_the_answer():
    model = FakeToolModel(
        script=[
            AIMessage(
                content="", tool_calls=[{"name": "echo", "args": {"text": "hi"}, "id": "c1"}]
            ),
            "Done with echo hi",
        ]
    )
    agent = create_agent(model, [echo])

    streamed = []
    async for chunk, _meta in agent.astream(
        {"messages": [("human", "go")]}, stream_mode="messages"
    ):
        if chunk.content:
            streamed.append(chunk.content)

    assert "echo:hi" in streamed  # the ToolMessage
    assert "".join(c for c in streamed if c != "echo:hi") == "Done with echo hi"


async def test_fake_router_returns_the_scripted_route():
    route = Route(intent="greeting", confidence=0.99)
    router = FakeRouter({"oi": route}, default=Route(intent="unclear", confidence=0))

    assert (await router.classify("oi")).intent == "greeting"
    assert (await router.classify("???")).intent == "unclear"
