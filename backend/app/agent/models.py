from typing import Literal

from app.config import LLMProvider, Settings


def chat_model(
    settings: Settings, role: Literal["specialist", "general"], *, script: list | None = None
):
    """The chat model for a role. `script` feeds the fake model (tests and evals)."""
    if settings.llm_provider is LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.specialist_model if role == "specialist" else settings.general_model,
            max_tokens=settings.llm_max_tokens,
            default_request_timeout=settings.llm_timeout_s,
            max_retries=1,
            streaming=True,
            stream_usage=True,
        )
    from app.agent.fakes import FakeToolModel

    return FakeToolModel(script=script or [])
