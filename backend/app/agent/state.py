"""Verification state per conversation, kept in Postgres (data-model.md)."""

from pathlib import Path

import psycopg

SCHEMA = Path(__file__).with_name("schema.sql")

_ensured = False


async def ensure_agent_tables(conn: psycopg.AsyncConnection) -> None:
    """Idempotent DDL; runs at the end of the seed and once per process on first use."""
    global _ensured
    await conn.execute(SCHEMA.read_text())
    await conn.commit()
    _ensured = True


def reset_ensured() -> None:
    global _ensured
    _ensured = False
