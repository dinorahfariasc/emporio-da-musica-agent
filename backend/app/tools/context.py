from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

from psycopg_pool import AsyncConnectionPool

from app.embeddings import Embedder

STORE_TZ = ZoneInfo("America/Campo_Grande")


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(STORE_TZ)


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=STORE_TZ)
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


ErrorCode = Literal[
    "not_found",
    "verification_failed",
    "locked",
    "not_verified",
    "not_eligible",
    "unavailable",
    "invalid_input",
]


class ToolError(Exception):
    def __init__(self, code: ErrorCode, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


def _no_emit(event: dict) -> None:
    return None


@dataclass(frozen=True)
class ToolContext:
    pool: AsyncConnectionPool
    embedder: Embedder
    conversation_id: str
    clock: Clock = field(default_factory=SystemClock)
    # The agent sets this to LangGraph's stream writer; MCP keeps the no-op.
    emit: Callable[[dict], None] = _no_emit
