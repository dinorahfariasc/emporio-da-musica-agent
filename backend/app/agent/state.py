"""Verification state per conversation, kept in Postgres (data-model.md)."""

import re
from dataclasses import dataclass, field
from datetime import timedelta
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


async def _ensure_once(conn: psycopg.AsyncConnection) -> None:
    if not _ensured:
        await ensure_agent_tables(conn)


CONVERSATION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CONVERSATION_LOCK_AT = 3
ORDER_LOCK_AT = 5
ORDER_LOCK_FOR = timedelta(minutes=30)


class InvalidConversationId(ValueError):
    pass


@dataclass(frozen=True)
class ConversationState:
    verified_order_ids: frozenset[int] = frozenset()
    failed_attempts: int = 0
    locked: bool = False


@dataclass(frozen=True)
class Reservation:
    allowed: bool
    reason: str | None = None  # "locked" (conversation) or "order_locked"
    extra: dict = field(default_factory=dict)


def check_conversation_id(conversation_id: str) -> str:
    if not CONVERSATION_ID.fullmatch(conversation_id):
        raise InvalidConversationId("conversation_id must match ^[A-Za-z0-9_-]{1,128}$")
    return conversation_id


async def get(conn: psycopg.AsyncConnection, conversation_id: str) -> ConversationState:
    check_conversation_id(conversation_id)
    await _ensure_once(conn)
    cur = await conn.execute(
        "SELECT verified_order_ids, failed_attempts, locked FROM conversation_state "
        "WHERE conversation_id = %s",
        (conversation_id,),
    )
    row = await cur.fetchone()
    return ConversationState(frozenset(row[0]), row[1], row[2]) if row else ConversationState()


async def reserve_attempt(
    conn: psycopg.AsyncConnection, conversation_id: str, order_id: int
) -> Reservation:
    """Counts the attempt BEFORE the contact is compared, so concurrent requests cannot all pass.

    On success the caller calls `confirm_success`, which gives the attempt back.
    """
    check_conversation_id(conversation_id)
    await _ensure_once(conn)
    async with conn.transaction():
        await conn.execute(
            "INSERT INTO conversation_state (conversation_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (conversation_id,),
        )
        cur = await conn.execute(
            "UPDATE conversation_state SET failed_attempts = failed_attempts + 1, "
            "locked = failed_attempts + 1 >= %s, updated_at = now() "
            "WHERE conversation_id = %s AND NOT locked RETURNING failed_attempts",
            (CONVERSATION_LOCK_AT, conversation_id),
        )
        if await cur.fetchone() is None:
            return Reservation(False, "locked")
        await conn.execute(
            "INSERT INTO order_verification_failures (order_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (order_id,),
        )
        cur = await conn.execute(
            "UPDATE order_verification_failures SET failed_attempts = failed_attempts + 1, "
            "locked_until = CASE WHEN failed_attempts + 1 >= %s THEN now() + %s "
            "ELSE locked_until END, "
            "updated_at = now() "
            "WHERE order_id = %s AND (locked_until IS NULL OR locked_until <= now()) "
            "RETURNING failed_attempts",
            (ORDER_LOCK_AT, ORDER_LOCK_FOR, order_id),
        )
        if await cur.fetchone() is None:
            # The attempt must not count against the conversation either.
            await _release_conversation(conn, conversation_id)
            return Reservation(False, "order_locked")
    return Reservation(True)


async def _release_conversation(conn: psycopg.AsyncConnection, conversation_id: str) -> None:
    await conn.execute(
        "UPDATE conversation_state SET failed_attempts = greatest(failed_attempts - 1, 0), "
        "locked = false WHERE conversation_id = %s",
        (conversation_id,),
    )


async def confirm_success(
    conn: psycopg.AsyncConnection, conversation_id: str, order_id: int
) -> None:
    check_conversation_id(conversation_id)
    async with conn.transaction():
        await conn.execute(
            "UPDATE conversation_state SET failed_attempts = greatest(failed_attempts - 1, 0), "
            "locked = false, updated_at = now(), "
            "verified_order_ids = CASE WHEN %s = ANY(verified_order_ids) THEN verified_order_ids "
            "ELSE array_append(verified_order_ids, %s) END "
            "WHERE conversation_id = %s",
            (order_id, order_id, conversation_id),
        )
        await conn.execute(
            "UPDATE order_verification_failures SET "
            "failed_attempts = greatest(failed_attempts - 1, 0), "
            "locked_until = CASE WHEN failed_attempts - 1 < %s THEN NULL ELSE locked_until END "
            "WHERE order_id = %s",
            (ORDER_LOCK_AT, order_id),
        )
