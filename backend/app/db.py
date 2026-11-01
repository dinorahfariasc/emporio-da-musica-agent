import psycopg
from psycopg_pool import AsyncConnectionPool

from app.config import Settings


async def connect(database_url: str) -> psycopg.AsyncConnection:
    # prepare_threshold=None: Neon's pooled endpoint runs PgBouncer in transaction mode,
    # which does not support server-side prepared statements.
    return await psycopg.AsyncConnection.connect(
        database_url, prepare_threshold=None, connect_timeout=10
    )


async def ping(database_url: str) -> None:
    async with await connect(database_url) as conn:
        await conn.execute("SELECT 1")


_pool: AsyncConnectionPool | None = None


async def get_pool(settings: Settings) -> AsyncConnectionPool:
    """Process-wide pool over the pooled URL, opened lazily (research R11)."""
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = AsyncConnectionPool(
            settings.database_url,
            min_size=0,
            max_size=4,
            open=False,
            timeout=5,  # waiting for a connection must not eat the turn budget
            kwargs={"prepare_threshold": None},
        )
    await _pool.open()  # no-op once open
    return _pool
