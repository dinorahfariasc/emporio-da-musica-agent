import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import chat, health, stream_test
from app.auth.dependency import ServiceAuthMisconfigured, ServiceAuthUnauthorized
from app.chat import protocol as p
from app.config import Environment, LLMProvider, Settings, get_settings

logger = logging.getLogger("app.startup")

settings = get_settings()
mcp_app = None
if settings.mcp_api_key:
    from app.mcp import build_mcp_app

    mcp_app = build_mcp_app(settings)


def check_fail_closed_config(settings: Settings | None = None) -> None:
    """Refuse to serve chat requests with missing production secrets (FR-015, research.md R7)."""
    settings = settings or get_settings()
    if settings.environment is not Environment.PRODUCTION:
        return
    required = [
        ("SERVICE_JWT_SECRET", settings.service_jwt_secret),
        ("DATABASE_URL", settings.database_url),
    ]
    # The fake provider needs no key; it is a deliberate choice, not a missing one.
    if settings.llm_provider is LLMProvider.ANTHROPIC:
        required.append(("ANTHROPIC_API_KEY", settings.anthropic_api_key))
    elif settings.llm_provider is LLMProvider.OPENROUTER:
        required.append(("OPENROUTER_API_KEY", settings.openrouter_api_key))
    missing = [name for name, value in required if not value]
    if missing:
        raise RuntimeError(
            f"Refusing to start in production with missing required config: {', '.join(missing)}"
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    check_fail_closed_config()
    async with AsyncExitStack() as stack:
        if mcp_app is not None:
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))
        yield


app = FastAPI(title="Empório da Música Agent API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(stream_test.router)
app.include_router(chat.router)
if mcp_app is not None:
    # Protected only by MCP_API_KEY (BearerAuthMiddleware in app.mcp), never by a user's service
    # JWT: external MCP clients have no login (specs/004-auth-limits-deploy does not touch /mcp).
    app.mount("/mcp", mcp_app)


@app.exception_handler(ServiceAuthUnauthorized)
async def _unauthorized_handler(request: Request, exc: ServiceAuthUnauthorized) -> JSONResponse:
    body = p.ErrorResponse(
        error=p.ErrorBody(
            code="unauthorized", message="Sua sessão expirou. Entre novamente para continuar."
        )
    )
    return JSONResponse(
        body.model_dump(mode="json", by_alias=True, exclude_none=True), status_code=401
    )


@app.exception_handler(ServiceAuthMisconfigured)
async def _misconfigured_handler(request: Request, exc: ServiceAuthMisconfigured) -> JSONResponse:
    logger.error("auth misconfigured: %s", exc)
    return JSONResponse({"detail": "server misconfigured"}, status_code=500)
