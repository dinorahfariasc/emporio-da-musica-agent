from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from app.api import chat, health, stream_test
from app.config import get_settings

settings = get_settings()
mcp_app = None
if settings.mcp_api_key:
    from app.mcp import build_mcp_app

    mcp_app = build_mcp_app(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        if mcp_app is not None:
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))
        yield


app = FastAPI(title="Empório da Música Agent API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(stream_test.router)
app.include_router(chat.router)
if mcp_app is not None:
    app.mount("/mcp", mcp_app)
