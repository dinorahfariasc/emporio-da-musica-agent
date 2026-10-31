import psycopg


async def ping(database_url: str) -> None:
    # prepare_threshold=None: Neon's pooled endpoint runs PgBouncer in transaction mode,
    # which does not support server-side prepared statements.
    async with await psycopg.AsyncConnection.connect(
        database_url, prepare_threshold=None, connect_timeout=5
    ) as conn:
        await conn.execute("SELECT 1")
