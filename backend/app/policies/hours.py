"""Store opening hours (policy §2) and national holidays 2026-2027."""

from datetime import date, datetime, time, timedelta

from pydantic import BaseModel

# weekday() -> (opens, closes); Sunday is absent: closed.
HOURS: dict[int, tuple[time, time]] = {
    **dict.fromkeys(range(5), (time(9, 0), time(18, 0))),
    5: (time(9, 0), time(13, 0)),
}

HOLIDAYS: dict[date, str] = {
    date(2026, 1, 1): "Confraternização Universal",
    date(2026, 4, 3): "Sexta-feira Santa",
    date(2026, 4, 21): "Tiradentes",
    date(2026, 5, 1): "Dia do Trabalho",
    date(2026, 9, 7): "Independência do Brasil",
    date(2026, 10, 12): "Nossa Senhora Aparecida",
    date(2026, 11, 2): "Finados",
    date(2026, 11, 15): "Proclamação da República",
    date(2026, 11, 20): "Dia da Consciência Negra",
    date(2026, 12, 25): "Natal",
    date(2027, 1, 1): "Confraternização Universal",
    date(2027, 3, 26): "Sexta-feira Santa",
    date(2027, 4, 21): "Tiradentes",
    date(2027, 5, 1): "Dia do Trabalho",
    date(2027, 9, 7): "Independência do Brasil",
    date(2027, 10, 12): "Nossa Senhora Aparecida",
    date(2027, 11, 2): "Finados",
    date(2027, 11, 15): "Proclamação da República",
    date(2027, 11, 20): "Dia da Consciência Negra",
    date(2027, 12, 25): "Natal",
}


class StoreStatus(BaseModel):
    is_open: bool
    today_hours: str | None
    next_opening: datetime
    holiday_name: str | None


def _hours_for(day: date) -> tuple[time, time] | None:
    return None if day in HOLIDAYS else HOURS.get(day.weekday())


def store_status(now: datetime) -> StoreStatus:
    """`now` must be tz-aware in the store's timezone."""
    today = _hours_for(now.date())
    is_open = bool(today and today[0] <= now.time() < today[1])
    if today and now.time() < today[0]:
        next_opening = datetime.combine(now.date(), today[0], tzinfo=now.tzinfo)
    else:
        day = now.date()
        while True:
            day += timedelta(days=1)
            if opens := _hours_for(day):
                next_opening = datetime.combine(day, opens[0], tzinfo=now.tzinfo)
                break
    return StoreStatus(
        is_open=is_open,
        today_hours=f"{today[0]:%H:%M} às {today[1]:%H:%M}" if today else None,
        next_opening=next_opening,
        holiday_name=HOLIDAYS.get(now.date()),
    )
