from typing import Literal

from app.config import LLMProvider, Settings


def openrouter_chat(
    settings: Settings,
    model: str,
    *,
    max_tokens: int,
    timeout_s: float,
    temperature: float | None = None,
    streaming: bool = False,
    reasoning: bool = True,
):
    """A chat model served by OpenRouter (OpenAI-compatible API)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=settings.openrouter_api_key or "",
        base_url=settings.openrouter_base_url,
        max_tokens=max_tokens,
        timeout=timeout_s,
        max_retries=1,
        temperature=temperature,
        streaming=streaming,
        stream_usage=streaming,
        # Reasoning tokens would eat max_tokens and add latency; the router turns them off.
        extra_body=None if reasoning else {"reasoning": {"enabled": False}},
    )


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
    if settings.llm_provider is LLMProvider.OPENROUTER:
        return openrouter_chat(
            settings,
            settings.specialist_model if role == "specialist" else settings.general_model,
            max_tokens=settings.llm_max_tokens,
            timeout_s=settings.llm_timeout_s,
            streaming=True,
        )
    from app.agent.fakes import FakeToolModel

    return FakeToolModel(script=script or [])
