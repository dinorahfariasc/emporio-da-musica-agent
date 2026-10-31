"""Walking-skeleton endpoint proving that SSE reaches the browser unbuffered in production."""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

CHUNKS = 10
INTERVAL_SECONDS = 0.3


async def _events(chunks: int, interval: float) -> AsyncIterator[str]:
    for i in range(1, chunks + 1):
        yield f"data: chunk {i}/{chunks}\n\n"
        await asyncio.sleep(interval)
    yield "data: [DONE]\n\n"


@router.get("/api/stream-test")
async def stream_test() -> StreamingResponse:
    return StreamingResponse(
        _events(CHUNKS, INTERVAL_SECONDS),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
