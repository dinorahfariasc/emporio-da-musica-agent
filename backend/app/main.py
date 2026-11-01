import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import chat, health, stream_test
from app.auth.dependency import ServiceAuthMisconfigured, ServiceAuthUnauthorized
from app.chat import protocol as p
from app.config import check_fail_closed_config, get_settings, is_production

logger = logging.getLogger("app.startup")

settings = get_settings()
mcp_app = None
if settings.mcp_api_key:
    from app.mcp import build_mcp_app

    mcp_app = build_mcp_app(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    check_fail_closed_config()
    async with AsyncExitStack() as stack:
        if mcp_app is not None:
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))
        yield


# In production: no public OpenAPI/Swagger/ReDoc (the schema otherwise discloses every internal
# route), and /api/stream-test (a walking-skeleton demo endpoint, no auth, no business value once
# the real chat endpoint is live) is not mounted at all.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None} if is_production(settings) else {}
)
app = FastAPI(
    title="Empório da Música Agent API", version="0.1.0", lifespan=lifespan, **_docs_kwargs
)
app.include_router(health.router)
if not is_production(settings):
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
