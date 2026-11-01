from datetime import datetime

from app.policies.hours import store_status
from app.tools.context import STORE_TZ


def _at(*args) -> datetime:
    return datetime(*args, tzinfo=STORE_TZ)


def test_saturday_after_close_opens_monday():
    status = store_status(_at(2026, 11, 7, 13, 1))
    assert not status.is_open
    assert status.next_opening == _at(2026, 11, 9, 9, 0)


def test_next_opening_skips_a_monday_holiday():
    status = store_status(_at(2026, 10, 31, 13, 1))
    assert not status.is_open
    assert status.next_opening == _at(2026, 11, 3, 9, 0)


def test_sunday_is_closed():
    status = store_status(_at(2026, 11, 8, 11, 0))
    assert not status.is_open
    assert status.today_hours is None


def test_holiday_is_closed_and_named():
    status = store_status(_at(2026, 11, 2, 10, 0))
    assert not status.is_open
    assert status.holiday_name == "Finados"


def test_weekday_in_hours_is_open():
    status = store_status(_at(2026, 11, 3, 10, 0))
    assert status.is_open
    assert status.today_hours == "09:00 às 18:00"


def test_before_opening_opens_today():
    status = store_status(_at(2026, 11, 3, 8, 0))
    assert not status.is_open
    assert status.next_opening == _at(2026, 11, 3, 9, 0)
