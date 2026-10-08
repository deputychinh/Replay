"""SLA maths: pure functions, no I/O (NFR-05).

All arithmetic happens on aware datetimes converted to UTC, so daylight-saving
changes in the calendar's zone are handled by zoneinfo, not by us.
"""

from datetime import UTC, datetime, timedelta

from app.sla.calendar import BusinessCalendar

MAX_DAYS_SCANNED = 3660  # ten years: enough for any target, stops a calendar with no open days


def _overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    start, end = max(a_start, b_start), min(a_end, b_end)
    return max(0.0, (end - start).total_seconds() / 60)


def business_minutes_between(start: datetime, end: datetime, calendar: BusinessCalendar | None) -> int:
    """Whole business minutes from start to end (0 if end is before start). No calendar = 24/7."""
    if end <= start:
        return 0
    if calendar is None:
        return int((end - start).total_seconds() // 60)
    total = 0.0
    day = calendar.local_date(start)
    last = calendar.local_date(end)
    while day <= last:
        window = calendar.window(day)
        if window:
            total += _overlap_minutes(start, end, window[0], window[1])
        day += timedelta(days=1)
    return int(total)


def due_at(start: datetime, minutes: int, calendar: BusinessCalendar | None) -> datetime:
    """The moment `minutes` business minutes after `start`."""
    if calendar is None:
        return start + timedelta(minutes=minutes)
    remaining = float(minutes)
    day = calendar.local_date(start)
    for _ in range(MAX_DAYS_SCANNED):
        window = calendar.window(day)
        if window:
            opens, closes = window
            segment_start = max(start, opens)
            if segment_start < closes:
                available = (closes - segment_start).total_seconds() / 60
                if remaining <= available:
                    return (segment_start + timedelta(minutes=remaining)).astimezone(UTC)
                remaining -= available
        day += timedelta(days=1)
    raise ValueError("The business calendar has no open hours")
