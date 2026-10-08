from datetime import UTC, date, datetime

import pytest

from app.sla.calendar import DEFAULT_WEEKLY_HOURS, BusinessCalendar
from app.sla.clock import business_minutes_between, due_at

NY = BusinessCalendar.from_settings("America/New_York", DEFAULT_WEEKLY_HOURS, {date(2026, 11, 26)})  # Thanksgiving


def ny(*args: int) -> datetime:
    return datetime(*args, tzinfo=NY.zone)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("start", "minutes", "expected"),
    [
        # Inside the day.
        (ny(2026, 10, 6, 10, 0), 60, ny(2026, 10, 6, 11, 0)),
        # Runs past 17:00 → continues next morning.
        (ny(2026, 10, 6, 16, 30), 60, ny(2026, 10, 7, 9, 30)),
        # Opened at night → clock starts at 09:00.
        (ny(2026, 10, 6, 22, 0), 30, ny(2026, 10, 7, 9, 30)),
        # Friday afternoon → Monday.
        (ny(2026, 10, 9, 16, 0), 120, ny(2026, 10, 12, 10, 0)),
        # Weekend start.
        (ny(2026, 10, 10, 12, 0), 15, ny(2026, 10, 12, 9, 15)),
        # Holiday (Thanksgiving, Thu) is skipped.
        (ny(2026, 11, 25, 16, 0), 120, ny(2026, 11, 27, 10, 0)),
        # DST ends Sunday 1 Nov 2026: Friday 16:00 EDT + 2 h → Monday 10:00 EST.
        (ny(2026, 10, 30, 16, 0), 120, ny(2026, 11, 2, 10, 0)),
        # A full week of business time (5 days of 8 hours).
        (ny(2026, 10, 5, 9, 0), 2400, ny(2026, 10, 9, 17, 0)),
    ],
)
def test_due_at(start: datetime, minutes: int, expected: datetime) -> None:
    assert due_at(start, minutes, NY) == expected.astimezone(UTC)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (ny(2026, 10, 6, 10, 0), ny(2026, 10, 6, 11, 30), 90),
        (ny(2026, 10, 6, 16, 0), ny(2026, 10, 7, 10, 0), 120),
        (ny(2026, 10, 9, 16, 0), ny(2026, 10, 12, 10, 0), 120),
        (ny(2026, 10, 10, 8, 0), ny(2026, 10, 11, 20, 0), 0),  # weekend only
        (ny(2026, 10, 6, 12, 0), ny(2026, 10, 6, 11, 0), 0),  # end before start
    ],
)
def test_business_minutes_between(start: datetime, end: datetime, expected: int) -> None:
    assert business_minutes_between(start, end, NY) == expected


def test_round_trip_is_consistent() -> None:
    start = ny(2026, 10, 7, 13, 17)
    for minutes in (1, 59, 480, 999, 4321):
        assert business_minutes_between(start, due_at(start, minutes, NY), NY) == minutes


def test_without_calendar_counts_wall_clock() -> None:
    start = datetime(2026, 10, 10, 23, 0, tzinfo=UTC)
    assert due_at(start, 90, None) == datetime(2026, 10, 11, 0, 30, tzinfo=UTC)
    assert business_minutes_between(start, datetime(2026, 10, 11, 1, 0, tzinfo=UTC), None) == 120


def test_calendar_without_open_days_fails_loudly() -> None:
    closed = BusinessCalendar.from_settings("UTC", {})
    with pytest.raises(ValueError, match="no open hours"):
        due_at(datetime(2026, 1, 1, tzinfo=UTC), 10, closed)


def test_other_time_zone() -> None:
    saigon = BusinessCalendar.from_settings("Asia/Ho_Chi_Minh", DEFAULT_WEEKLY_HOURS)
    start = datetime(2026, 10, 6, 1, 0, tzinfo=UTC)  # 08:00 in Saigon
    assert due_at(start, 60, saigon) == datetime(2026, 10, 6, 3, 0, tzinfo=UTC)  # 10:00 local
