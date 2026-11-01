"""Builds the agent for one turn. Built per request so a ToolContext never leaks between
requests (review L1); tool sets narrow cost and surface, conversation_state is the boundary."""

from collections.abc import Callable
from typing import Any, Literal

from app.agent.models import chat_model
from app.agent.prompts import system_prompt
from app.agent.router import Route, choose_path
from app.config import Settings
from app.tools.context import ToolContext
from app.tools.registry import REGISTRY, TOOLS_BY_INTENT, ToolFn, langchain_tools

ModelFactory = Callable[[Literal["specialist", "general"]], Any]


def build_agent(
    settings: Settings,
    ctx: ToolContext,
    route: Route,
    *,
    model_factory: ModelFactory | None = None,
    registry: dict[str, ToolFn] | None = None,
) -> tuple[Any, Route]:
    """Returns (compiled agent, route with `path` and `model` filled in)."""
    from langchain.agents import create_agent

    registry = REGISTRY if registry is None else registry
    clock = getattr(ctx, "clock", None)  # test doubles may not carry one
    now = clock.now() if clock else None
    path = choose_path(route, settings)
    role: Literal["specialist", "general"] = path
    if path == "specialist":
        # Filtered by the registry so tests can use a small one; a gate test (T029) checks that
        # every contract tool is registered in the real one.
        names = tuple(n for n in TOOLS_BY_INTENT[route.intent] if n in registry)
        prompt = system_prompt(route.intent, now)
        model_name = settings.specialist_model
    else:
        names = tuple(registry)
        prompt = system_prompt(now=now)
        model_name = settings.general_model
    factory = model_factory or (lambda r: chat_model(settings, r))
    agent = create_agent(
        factory(role),
        langchain_tools(ctx, names, registry),
        system_prompt=prompt,
    )
    return agent, route.model_copy(update={"path": path, "model": model_name})
