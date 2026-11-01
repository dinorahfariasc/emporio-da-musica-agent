from app.agent.state import ensure_agent_tables
from app.db import connect
from etl.__main__ import seed


async def _count(conn, table):
    cur = await conn.execute(f"SELECT count(*) FROM {table}")
    return (await cur.fetchone())[0]


async def test_ensure_agent_tables_is_idempotent(seeded_db):
    async with await connect(seeded_db) as conn:
        await ensure_agent_tables(conn)
        await ensure_agent_tables(conn)
        assert await _count(conn, "conversation_state") >= 0


async def test_reseed_keeps_agent_rows(seeded_db, tmp_path):
    async with await connect(seeded_db) as conn:
        await ensure_agent_tables(conn)
        await conn.execute(
            "INSERT INTO conversation_state (conversation_id) VALUES ('keep-me') "
            "ON CONFLICT DO NOTHING"
        )
        await conn.commit()

    await seed(seeded_db, report_path=tmp_path / "r.md")

    async with await connect(seeded_db) as conn:
        cur = await conn.execute(
            "SELECT count(*) FROM conversation_state WHERE conversation_id = 'keep-me'"
        )
        assert (await cur.fetchone())[0] == 1
        await conn.execute("DELETE FROM conversation_state WHERE conversation_id = 'keep-me'")
        await conn.commit()
