"""Tool registry: plain async functions -> LangChain tools (and MCP schemas in #8).

Reviews C2/C3: a tool takes `ctx` first; the model-facing schema is built explicitly without it,
and the wrapper is a real closure (`functools.partial` breaks schema inference).
"""

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, get_type_hints

from pydantic import BaseModel, create_model

from app.tools.context import ToolContext, ToolError

logger = logging.getLogger(__name__)

ToolFn = Callable[..., Awaitable[Any]]

REGISTRY: dict[str, ToolFn] = {}

# Every tool name the chat contract (docs/contracts/chat-stream.md) may carry.
CONTRACT_TOOL_NAMES: tuple[str, ...] = (
    "search_products",
    "get_product",
    "find_similar_products",
    "get_active_promotions",
    "calculate_payment_options",
    "search_policies",
    "get_store_info",
    "get_order_status",
    "check_return_eligibility",  # not in the #4 contract table; the UI labels it (T033)
    "request_return",
    "register_complaint",
    "handoff_to_human",
)

# Narrower tool sets cut cost and attack surface; conversation_state is the security boundary.
TOOLS_BY_INTENT: dict[str, tuple[str, ...]] = {
    "product_search": ("search_products", "find_similar_products"),
    "product_details": ("get_product", "find_similar_products", "calculate_payment_options"),
    "promotions": ("get_active_promotions",),
    "payment_options": ("get_product", "calculate_payment_options", "search_policies"),
    "order_status": ("get_order_status",),
    "policy_question": ("search_policies",),
    "store_info": ("get_store_info", "search_policies"),
    "service_request": (
        "get_order_status",
        "check_return_eligibility",
        "request_return",
        "register_complaint",
        "handoff_to_human",
        "search_policies",
    ),
    "greeting": (),
    "out_of_scope": (),
}


def tool(fn: ToolFn) -> ToolFn:
    """Registers a tool under its function name."""
    REGISTRY[fn.__name__] = fn
    return fn


def tool_spec(fn: ToolFn) -> type[BaseModel]:
    """The argument schema shown to the model: the signature without `ctx`."""
    hints = get_type_hints(fn, include_extras=True)
    fields: dict[str, Any] = {}
    for name, param in inspect.signature(fn).parameters.items():
        if name == "ctx":
            continue
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[name] = (hints[name], default)
    return create_model(f"{fn.__name__}_args", **fields)


def langchain_tools(
    ctx: ToolContext, names: tuple[str, ...] | list[str], registry: dict[str, ToolFn] | None = None
) -> list:
    from langchain_core.tools import StructuredTool, ToolException

    registry = REGISTRY if registry is None else registry
    tools = []
    for name in names:
        fn = registry[name]

        def make(fn: ToolFn = fn):
            async def run(**kwargs: Any) -> Any:
                try:
                    result = await fn(ctx, **kwargs)
                except ToolError as exc:
                    raise ToolException(exc.code) from None
                except Exception:
                    logger.exception("tool %s failed", fn.__name__)
                    raise ToolException("unavailable") from None
                return result.model_dump(mode="json") if isinstance(result, BaseModel) else result

            return run

        tools.append(
            StructuredTool(
                name=name,
                description=inspect.getdoc(fn) or name,
                args_schema=tool_spec(fn),
                coroutine=make(),
                handle_tool_error=True,
            )
        )
    return tools
