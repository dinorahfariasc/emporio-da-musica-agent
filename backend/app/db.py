import psycopg


async def connect(database_url: str) -> psycopg.AsyncConnection:
    # prepare_threshold=None: Neon's pooled endpoint runs PgBouncer in transaction mode,
    # which does not support server-side prepared statements.
    return await psycopg.AsyncConnection.connect(
        database_url, prepare_threshold=None, connect_timeout=10
    )


async def ping(database_url: str) -> None:
    async with await connect(database_url) as conn:
        await conn.execute("SELECT 1")
