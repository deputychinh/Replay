import uuid
from datetime import date
from zoneinfo import available_timezones

from pydantic import Field, field_validator

from app.common.schemas import Schema


class OrganizationOut(Schema):
    id: uuid.UUID
    name: str
    slug: str
    brand_color: str | None


class HolidayIn(Schema):
    day: date
    name: str = Field(min_length=1, max_length=120)


class HolidayOut(HolidayIn):
    id: uuid.UUID


class CalendarIn(Schema):
    timezone: str
    # weekday 0 (Monday) … 6 → [open minute, close minute]; a missing day is closed
    weekly_hours: dict[str, list[int]]

    @field_validator("timezone")
    @classmethod
    def known_zone(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError("Unknown time zone")
        return value

    @field_validator("weekly_hours")
    @classmethod
    def valid_hours(cls, value: dict[str, list[int]]) -> dict[str, list[int]]:
        for day, span in value.items():
            if day not in {str(d) for d in range(7)} or len(span) != 2 or not 0 <= span[0] < span[1] <= 1440:
                raise ValueError("Each day needs [open, close] minutes between 0 and 1440")
        return value


class CalendarOut(CalendarIn):
    holidays: list[HolidayOut] = []
