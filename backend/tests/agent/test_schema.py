from app.agent.state import ensure_agent_tables, get, reset_ensured
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


async def test_migrates_an_old_shape_conversation_state_table(seeded_db):
    """Senior review (#44): a production database that ran before specs/004-auth-limits-deploy
    already has conversation_state without `user_id`; CREATE TABLE IF NOT EXISTS alone is a no-op
    against it, so every user_id-scoped query would fail. Simulate that starting shape."""
    async with await connect(seeded_db) as conn:
        await conn.execute("DROP TABLE IF EXISTS conversation_state")
        await conn.execute(
            "CREATE TABLE conversation_state ("
            "conversation_id text PRIMARY KEY, "
            "verified_order_ids int[] NOT NULL DEFAULT '{}', "
            "failed_attempts int NOT NULL DEFAULT 0, "
            "locked boolean NOT NULL DEFAULT false, "
            "updated_at timestamptz NOT NULL DEFAULT now())"
        )
        await conn.execute(
            "INSERT INTO conversation_state (conversation_id) VALUES ('pre-existing-row')"
        )
        await conn.commit()

    reset_ensured()
    async with await connect(seeded_db) as conn:
        await ensure_agent_tables(conn)
        cur = await conn.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'conversation_state' AND column_name = 'user_id'"
        )
        assert await cur.fetchone() is not None

        # The table is usable the new way right after migrating (old ephemeral rows are not
        # expected to survive the shape change — see the migration's docstring).
        state = await get(conn, "00000000-0000-0000-0000-000000000001", "fresh-after-migration")
        assert state.verified_order_ids == frozenset()


async def test_reseed_keeps_agent_rows(seeded_db, tmp_path):
    user_id = "00000000-0000-0000-0000-000000000001"
    async with await connect(seeded_db) as conn:
        await ensure_agent_tables(conn)
        await conn.execute(
            "INSERT INTO conversation_state (user_id, conversation_id) VALUES (%s, 'keep-me') "
            "ON CONFLICT DO NOTHING",
            (user_id,),
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
