"""Rate limit and daily budget enforcement (contracts/rate-limit-and-budget.md).

Fixed-window rate limiting (research.md R5): a known, accepted simplification at this scale.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg

from app.limits.store import add_daily_usage, get_daily_usage, increment_rate


@dataclass(frozen=True)
class Reservation:
    allowed: bool
    retry_after_seconds: int | None = None


def current_local_date(tz_name: str, now: datetime | None = None) -> date:
    moment = now or datetime.now(UTC)
    return moment.astimezone(ZoneInfo(tz_name)).date()


def _seconds_to_next_minute(now: datetime) -> int:
    next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
    return max(1, int((next_minute - now).total_seconds()))


def _seconds_to_next_local_midnight(tz_name: str, now: datetime) -> int:
    local_now = now.astimezone(ZoneInfo(tz_name))
    next_midnight = (local_now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((next_midnight - local_now).total_seconds()))


async def check_rate_limit(
    conn: psycopg.AsyncConnection, user_id: str, limit: int, now: datetime | None = None
) -> Reservation:
    moment = now or datetime.now(UTC)
    window_start = moment.replace(second=0, microsecond=0)
    count = await increment_rate(conn, user_id, window_start)
    if count <= limit:
        return Reservation(True)
    return Reservation(False, _seconds_to_next_minute(moment))


async def check_budget(
    conn: psycopg.AsyncConnection,
    user_id: str,
    budget: int,
    tz_name: str,
    now: datetime | None = None,
) -> Reservation:
    moment = now or datetime.now(UTC)
    usage_date = current_local_date(tz_name, moment)
    used = await get_daily_usage(conn, user_id, usage_date)
    if used < budget:
        return Reservation(True)
    return Reservation(False, _seconds_to_next_local_midnight(tz_name, moment))


async def record_usage(
    conn: psycopg.AsyncConnection,
    user_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    tz_name: str,
    now: datetime | None = None,
) -> None:
    moment = now or datetime.now(UTC)
    usage_date = current_local_date(tz_name, moment)
    await add_daily_usage(conn, user_id, usage_date, prompt_tokens + completion_tokens)
