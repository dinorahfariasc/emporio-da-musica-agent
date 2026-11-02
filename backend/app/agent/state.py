"""Verification state per (account, conversation), kept in Postgres (data-model.md).

specs/004-auth-limits-deploy: scoped to `user_id` as well as `conversation_id` so a conversation id
alone never grants access to another account's verified order data (closes DL-012).
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import psycopg

SCHEMA = Path(__file__).with_name("schema.sql")

_ensured = False
_DDL_LOCK = 0x656D706F  # arbitrary app-wide key for the schema advisory lock


async def _migrate_old_shape_conversation_state(conn: psycopg.AsyncConnection) -> None:
    """`CREATE TABLE IF NOT EXISTS` is a no-op against a `conversation_state` table that already
    exists from before specs/004-auth-limits-deploy (no `user_id` column) — exactly the shape a
    production database redeployed before this change would have. Detect that shape and migrate
    it in place. The table holds only ephemeral per-turn verification state (data-model.md), never
    anything a customer would notice missing, so dropping and recreating it under the same
    advisory lock used for the rest of this DDL is an acceptable migration at this scale."""
    cur = await conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'conversation_state' AND column_name = 'user_id'"
    )
    if await cur.fetchone() is not None:
        return  # already the new shape (or the table doesn't exist yet)
    cur = await conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_state'"
    )
    if await cur.fetchone() is None:
        return  # table doesn't exist yet; the CREATE TABLE below creates the new shape directly
    await conn.execute("DROP TABLE conversation_state")


async def ensure_agent_tables(conn: psycopg.AsyncConnection) -> None:
    """Idempotent DDL; runs at the end of the seed and once per process on first use."""
    global _ensured
    # Concurrent first requests would otherwise collide on the catalog.
    await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_DDL_LOCK,))
    await _migrate_old_shape_conversation_state(conn)
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


async def get(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str
) -> ConversationState:
    check_conversation_id(conversation_id)
    await _ensure_once(conn)
    cur = await conn.execute(
        "SELECT verified_order_ids, failed_attempts, locked FROM conversation_state "
        "WHERE user_id = %s AND conversation_id = %s",
        (user_id, conversation_id),
    )
    row = await cur.fetchone()
    return ConversationState(frozenset(row[0]), row[1], row[2]) if row else ConversationState()


async def reserve_attempt(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str, order_id: int
) -> Reservation:
    """Counts the attempt BEFORE the contact is compared, so concurrent requests cannot all pass.

    On success the caller calls `confirm_success`, which gives the attempt back.
    """
    check_conversation_id(conversation_id)
    await _ensure_once(conn)
    reason: str | None = None
    async with conn.transaction():
        await conn.execute(
            "INSERT INTO conversation_state (user_id, conversation_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (user_id, conversation_id),
        )
        cur = await conn.execute(
            "UPDATE conversation_state SET failed_attempts = failed_attempts + 1, "
            "locked = failed_attempts + 1 >= %s, updated_at = now() "
            "WHERE user_id = %s AND conversation_id = %s AND NOT locked "
            "RETURNING failed_attempts",
            (CONVERSATION_LOCK_AT, user_id, conversation_id),
        )
        if await cur.fetchone() is None:
            reason = "locked"
        else:
            await conn.execute(
                "INSERT INTO order_verification_failures (order_id) VALUES (%s) "
                "ON CONFLICT DO NOTHING",
                (order_id,),
            )
            cur = await conn.execute(
                "UPDATE order_verification_failures SET failed_attempts = failed_attempts + 1, "
                "locked_until = CASE WHEN failed_attempts + 1 >= %s THEN now() + %s "
                "ELSE locked_until END, updated_at = now() "
                "WHERE order_id = %s AND (locked_until IS NULL OR locked_until <= now()) "
                "RETURNING failed_attempts",
                (ORDER_LOCK_AT, ORDER_LOCK_FOR, order_id),
            )
            if await cur.fetchone() is None:
                # The attempt must not count against the conversation either.
                await _release_conversation(conn, user_id, conversation_id)
                reason = "order_locked"
    # Commit now: a caller that raises next (a failed check) must not roll the attempt back.
    await conn.commit()
    return Reservation(reason is None, reason)


async def _release_conversation(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str
) -> None:
    await conn.execute(
        "UPDATE conversation_state SET failed_attempts = greatest(failed_attempts - 1, 0), "
        "locked = false WHERE user_id = %s AND conversation_id = %s",
        (user_id, conversation_id),
    )


async def confirm_success(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str, order_id: int
) -> None:
    check_conversation_id(conversation_id)
    async with conn.transaction():
        await conn.execute(
            "UPDATE conversation_state SET failed_attempts = greatest(failed_attempts - 1, 0), "
            "locked = false, updated_at = now(), "
            "verified_order_ids = CASE WHEN %s = ANY(verified_order_ids) THEN verified_order_ids "
            "ELSE array_append(verified_order_ids, %s) END "
            "WHERE user_id = %s AND conversation_id = %s",
            (order_id, order_id, user_id, conversation_id),
        )
        await conn.execute(
            "UPDATE order_verification_failures SET "
            "failed_attempts = greatest(failed_attempts - 1, 0), "
            "locked_until = CASE WHEN failed_attempts - 1 < %s THEN NULL ELSE locked_until END "
            "WHERE order_id = %s",
            (ORDER_LOCK_AT, order_id),
        )
    await conn.commit()


async def reserve_contact_attempt(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str
) -> Reservation:
    """Like `reserve_attempt`, for a lookup by contact (no order id yet): counts against the
    conversation only, before the contact is compared. `verify_orders` gives it back."""
    check_conversation_id(conversation_id)
    await _ensure_once(conn)
    async with conn.transaction():
        await conn.execute(
            "INSERT INTO conversation_state (user_id, conversation_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (user_id, conversation_id),
        )
        cur = await conn.execute(
            "UPDATE conversation_state SET failed_attempts = failed_attempts + 1, "
            "locked = failed_attempts + 1 >= %s, updated_at = now() "
            "WHERE user_id = %s AND conversation_id = %s AND NOT locked "
            "RETURNING failed_attempts",
            (CONVERSATION_LOCK_AT, user_id, conversation_id),
        )
        allowed = await cur.fetchone() is not None
    await conn.commit()
    return Reservation(allowed, None if allowed else "locked")


async def verify_orders(
    conn: psycopg.AsyncConnection, user_id: str, conversation_id: str, order_ids: list[int]
) -> None:
    """A contact matched: unlock all of that customer's orders and give the attempt back."""
    check_conversation_id(conversation_id)
    async with conn.transaction():
        await conn.execute(
            "UPDATE conversation_state SET failed_attempts = greatest(failed_attempts - 1, 0), "
            "locked = false, updated_at = now(), "
            "verified_order_ids = ARRAY(SELECT DISTINCT unnest(verified_order_ids || %s::int[])) "
            "WHERE user_id = %s AND conversation_id = %s",
            (order_ids, user_id, conversation_id),
        )
    await conn.commit()
