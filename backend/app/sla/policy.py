"""SLA rules on top of the clock: initial targets, pause / resume, breach checks."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.common.constants import SLA_WARNING_MINUTES
from app.sla.calendar import BusinessCalendar
from app.sla.clock import business_minutes_between, due_at


@dataclass(frozen=True)
class Targets:
    first_response_minutes: int
    resolution_minutes: int


def initial_due_dates(created_at: datetime, targets: Targets, calendar: BusinessCalendar | None) -> tuple[datetime, datetime]:
    return (
        due_at(created_at, targets.first_response_minutes, calendar),
        due_at(created_at, targets.resolution_minutes, calendar),
    )


def remaining_minutes(now: datetime, due: datetime, calendar: BusinessCalendar | None) -> int:
    """Business minutes left until `due` (0 when already due). Stored while the clock is paused."""
    return business_minutes_between(now, due, calendar)


def resumed_due_at(now: datetime, remaining: int, calendar: BusinessCalendar | None) -> datetime:
    return due_at(now, remaining, calendar)


def is_breached(due: datetime | None, done_at: datetime | None, now: datetime) -> bool:
    """A target is breached if it was met late, or is still open past its due time."""
    if due is None:
        return False
    return (done_at or now) > due


def is_warning(due: datetime | None, now: datetime) -> bool:
    """Due within the warning window and not yet past."""
    return due is not None and now <= due <= now + timedelta(minutes=SLA_WARNING_MINUTES)
