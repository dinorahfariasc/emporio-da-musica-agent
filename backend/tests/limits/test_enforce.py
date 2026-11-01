import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.db import connect
from app.limits import enforce

TZ = "America/Campo_Grande"


@pytest.fixture
async def conn(database_url):
    async with await connect(database_url) as c:
        yield c


def _uid() -> str:
    return str(uuid.uuid4())


async def test_twenty_requests_per_minute_succeed_the_21st_is_refused(conn):
    user_id = _uid()
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    for _ in range(20):
        result = await enforce.check_rate_limit(conn, user_id, limit=20, now=now)
        assert result.allowed
    result = await enforce.check_rate_limit(conn, user_id, limit=20, now=now)
    assert not result.allowed
    assert result.retry_after_seconds and result.retry_after_seconds <= 60


async def test_a_new_minute_resets_the_count(conn):
    user_id = _uid()
    first_minute = datetime(2026, 11, 1, 12, 0, 30, tzinfo=UTC)
    for _ in range(20):
        assert (await enforce.check_rate_limit(conn, user_id, limit=20, now=first_minute)).allowed
    assert not (await enforce.check_rate_limit(conn, user_id, limit=20, now=first_minute)).allowed

    next_minute = datetime(2026, 11, 1, 12, 1, 5, tzinfo=UTC)
    assert (await enforce.check_rate_limit(conn, user_id, limit=20, now=next_minute)).allowed


async def test_two_accounts_have_independent_rate_limits(conn):
    user_a, user_b = _uid(), _uid()
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    for _ in range(20):
        assert (await enforce.check_rate_limit(conn, user_a, limit=20, now=now)).allowed
    assert not (await enforce.check_rate_limit(conn, user_a, limit=20, now=now)).allowed
    # B is unaffected by A exhausting its own limit.
    assert (await enforce.check_rate_limit(conn, user_b, limit=20, now=now)).allowed


async def test_budget_refuses_at_the_limit_and_reports_reset_time(conn):
    user_id = _uid()
    now = datetime(2026, 11, 1, 20, 0, 0, tzinfo=UTC)  # 16:00 Campo Grande
    await enforce.record_usage(conn, user_id, 150_000, 49_999, TZ, now=now)

    result = await enforce.check_budget(conn, user_id, budget=200_000, tz_name=TZ, now=now)
    assert result.allowed  # 199_999 < 200_000

    await enforce.record_usage(conn, user_id, 1, 0, TZ, now=now)
    result = await enforce.check_budget(conn, user_id, budget=200_000, tz_name=TZ, now=now)
    assert not result.allowed
    assert result.retry_after_seconds and result.retry_after_seconds <= 24 * 3600


async def test_budget_is_available_again_after_local_midnight(conn):
    user_id = _uid()
    before_midnight = datetime(2026, 11, 1, 23, 59, 0, tzinfo=ZoneInfo(TZ))
    await enforce.record_usage(conn, user_id, 200_000, 0, TZ, now=before_midnight)
    assert not (
        await enforce.check_budget(conn, user_id, budget=200_000, tz_name=TZ, now=before_midnight)
    ).allowed

    after_midnight = datetime(2026, 11, 2, 0, 0, 1, tzinfo=ZoneInfo(TZ))
    assert (
        await enforce.check_budget(conn, user_id, budget=200_000, tz_name=TZ, now=after_midnight)
    ).allowed


async def test_two_accounts_have_independent_budgets(conn):
    user_a, user_b = _uid(), _uid()
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    await enforce.record_usage(conn, user_a, 200_000, 0, TZ, now=now)
    assert not (
        await enforce.check_budget(conn, user_a, budget=200_000, tz_name=TZ, now=now)
    ).allowed
    assert (await enforce.check_budget(conn, user_b, budget=200_000, tz_name=TZ, now=now)).allowed


async def test_checking_the_budget_never_mutates_usage(conn):
    """check_budget is a pure read (data-model.md): only record_usage, called by the handler
    after a turn actually runs, may increment tokens_used. A rate-limit refusal in particular
    happens before record_usage is ever reached, so repeatedly checking (or being refused
    elsewhere) must never move usage on its own."""
    from app.limits.store import get_daily_usage

    user_id = _uid()
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    usage_date = enforce.current_local_date(TZ, now)

    for _ in range(5):
        result = await enforce.check_budget(conn, user_id, budget=200_000, tz_name=TZ, now=now)
        assert result.allowed

    assert await get_daily_usage(conn, user_id, usage_date) == 0
