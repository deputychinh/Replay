"""Business hours of an organisation, in its own time zone."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MINUTES_PER_DAY = 24 * 60

# Monday to Friday, 09:00-17:00
DEFAULT_WEEKLY_HOURS: dict[str, list[int]] = {str(day): [9 * 60, 17 * 60] for day in range(5)}


@dataclass(frozen=True)
class BusinessCalendar:
    timezone: str
    weekly_hours: dict[int, tuple[int, int]]  # weekday (0 = Monday) → (open minute, close minute)
    holidays: frozenset[date] = field(default_factory=frozenset)

    @classmethod
    def from_settings(
        cls, timezone: str, weekly_hours: dict[str, list[int]], holidays: set[date] | None = None
    ) -> "BusinessCalendar":
        hours = {int(day): (span[0], span[1]) for day, span in weekly_hours.items() if span[1] > span[0]}
        return cls(timezone, hours, frozenset(holidays or ()))

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def window(self, day: date) -> tuple[datetime, datetime] | None:
        """Opening and closing time of a local day, as aware datetimes, or None when closed."""
        if day in self.holidays or day.weekday() not in self.weekly_hours:
            return None
        open_minute, close_minute = self.weekly_hours[day.weekday()]
        return self._at(day, open_minute), self._at(day, close_minute)

    def _at(self, day: date, minute: int) -> datetime:
        if minute >= MINUTES_PER_DAY:
            return datetime.combine(day + timedelta(days=1), time(0), self.zone)
        return datetime.combine(day, time(minute // 60, minute % 60), self.zone)

    def local_date(self, moment: datetime) -> date:
        return moment.astimezone(self.zone).date()
