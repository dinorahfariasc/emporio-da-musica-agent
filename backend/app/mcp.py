"""MCP server exposing the store tools to external AI clients (US7, issue #8).

Each tool is the exact function the chat agent calls (`app.tools.registry.REGISTRY`); the
wrapper only builds a `ToolContext` from the MCP client connection. No business logic lives here
(constitution VI). Access is a single bearer key (`MCP_API_KEY`); the server is not mounted when
it is unset.
"""

import hmac
import inspect
from collections.abc import Awaitable, Callable

from fastmcp import Context, FastMCP
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.tools.context import ToolContext
from app.tools.registry import CONTRACT_TOOL_NAMES, REGISTRY, ToolFn


class BearerAuthMiddleware:
    """Checks `Authorization: Bearer <MCP_API_KEY>` with a constant-time comparison."""

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        token = auth.removeprefix("Bearer ") if auth.startswith("Bearer ") else ""
        if not token or not hmac.compare_digest(token, self.api_key):
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


async def _tool_context(settings: Settings, ctx: Context) -> ToolContext:
    from app.db import get_pool
    from app.embeddings import get_embedder

    return ToolContext(
        pool=await get_pool(settings),
        embedder=get_embedder(settings, purpose="query"),
        conversation_id=f"mcp:{ctx.client_id or 'unknown'}",
    )


def _wrap(fn: ToolFn, settings: Settings) -> Callable[..., Awaitable[object]]:
    """A real function with `fn`'s signature minus `ctx`, plus an injected `Context`.

    FastMCP builds the exposed input schema from `inspect.signature`/`__annotations__` and drops
    `Context`-typed parameters from it, so the schema seen by clients has no `ctx` (US7-1).
    """
    sig = inspect.signature(fn)
    names = [name for name in sig.parameters if name != "ctx"]
    hints = inspect.get_annotations(fn, eval_str=False)
    namespace: dict[str, object] = {
        "_fn": fn,
        "_settings": settings,
        "_tool_context": _tool_context,
    }
    params = ["_ctx"]
    for name in names:
        default = sig.parameters[name].default
        if default is inspect.Parameter.empty:
            params.append(name)
        else:
            key = f"_default_{name}"
            namespace[key] = default
            params.append(f"{name}={key}")
    call_args = ", ".join(f"{name}={name}" for name in names)
    source = (
        f"async def _tool({', '.join(params)}):\n"
        f"    tool_ctx = await _tool_context(_settings, _ctx)\n"
        f"    result = await _fn(tool_ctx, {call_args})\n"
        f"    return result.model_dump(mode='json') if hasattr(result, 'model_dump') else result\n"
    )
    exec(source, namespace)  # noqa: S102 - builds the real signature FastMCP needs for the schema
    wrapper = namespace["_tool"]
    wrapper.__annotations__ = {"_ctx": Context, **{name: hints[name] for name in names}}
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = inspect.getdoc(fn) or fn.__name__
    return wrapper


def build_mcp(settings: Settings) -> FastMCP:
    import app.tools  # noqa: F401 - registers every tool in REGISTRY

    mcp = FastMCP("Empório da Música tools")
    for name in CONTRACT_TOOL_NAMES:
        mcp.add_tool(_wrap(REGISTRY[name], settings))
    return mcp


def build_mcp_app(settings: Settings) -> ASGIApp:
    """The `/mcp` ASGI app: stateless streamable HTTP behind the bearer middleware.

    Callers check `settings.mcp_api_key` before calling this; it is not optional here.
    """
    if not settings.mcp_api_key:
        raise RuntimeError("MCP_API_KEY is not set")
    mcp = build_mcp(settings)
    middleware = [Middleware(BearerAuthMiddleware, api_key=settings.mcp_api_key)]
    return mcp.http_app(path="/", stateless_http=True, json_response=True, middleware=middleware)
