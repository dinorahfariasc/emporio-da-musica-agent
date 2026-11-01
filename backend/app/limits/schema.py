"""Idempotent DDL for the rate-limit/budget tables; same pattern as app.agent.state."""

from pathlib import Path

import psycopg

SCHEMA = Path(__file__).with_name("schema.sql")

_ensured = False
_DDL_LOCK = 0x6C696D74  # arbitrary app-wide key for this schema's advisory lock


async def ensure_limit_tables(conn: psycopg.AsyncConnection) -> None:
    global _ensured
    await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_DDL_LOCK,))
    await conn.execute(SCHEMA.read_text())
    await conn.commit()
    _ensured = True


def reset_ensured() -> None:
    global _ensured
    _ensured = False


async def ensure_once(conn: psycopg.AsyncConnection) -> None:
    if not _ensured:
        await ensure_limit_tables(conn)
