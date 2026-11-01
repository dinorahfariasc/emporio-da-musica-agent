"""Postgres reads/writes for the rate-limit and daily-budget counters (data-model.md)."""

from datetime import date, datetime, timedelta

import psycopg

from app.limits.schema import ensure_once


async def increment_rate(
    conn: psycopg.AsyncConnection, user_id: str, window_start: datetime
) -> int:
    await ensure_once(conn)
    async with conn.transaction():
        # Keep the table small; a row older than 2 minutes can never be read again.
        await conn.execute(
            "DELETE FROM rate_limit_minute WHERE window_start < %s",
            (window_start - timedelta(minutes=2),),
        )
        cur = await conn.execute(
            "INSERT INTO rate_limit_minute (user_id, window_start, request_count) "
            "VALUES (%s, %s, 1) "
            "ON CONFLICT (user_id, window_start) DO UPDATE SET "
            "request_count = rate_limit_minute.request_count + 1 "
            "RETURNING request_count",
            (user_id, window_start),
        )
        row = await cur.fetchone()
    await conn.commit()
    return row[0]


async def get_daily_usage(conn: psycopg.AsyncConnection, user_id: str, usage_date: date) -> int:
    await ensure_once(conn)
    cur = await conn.execute(
        "SELECT tokens_used FROM token_usage_daily WHERE user_id = %s AND usage_date = %s",
        (user_id, usage_date),
    )
    row = await cur.fetchone()
    return row[0] if row else 0


async def add_daily_usage(
    conn: psycopg.AsyncConnection, user_id: str, usage_date: date, tokens: int
) -> None:
    if tokens <= 0:
        return
    await ensure_once(conn)
    await conn.execute(
        "INSERT INTO token_usage_daily (user_id, usage_date, tokens_used) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id, usage_date) DO UPDATE SET "
        "tokens_used = token_usage_daily.tokens_used + %s",
        (user_id, usage_date, tokens, tokens),
    )
    await conn.commit()
