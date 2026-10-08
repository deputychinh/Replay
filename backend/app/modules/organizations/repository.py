import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tenant import TenantRepository
from app.modules.organizations.models import BusinessCalendar, Holiday, Organization
from app.sla.calendar import BusinessCalendar as Calendar


class OrganizationRepository:
    """Organisations are the tenants themselves, so they are looked up by id or slug."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_slug(self, slug: str) -> Organization | None:
        return await self.session.scalar(select(Organization).where(Organization.slug == slug))

    async def by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self.session.get(Organization, org_id)

    async def next_ticket_number(self, org_id: uuid.UUID) -> int:
        """Atomic per-organisation counter (row lock via UPDATE … RETURNING)."""
        number = await self.session.scalar(
            update(Organization)
            .where(Organization.id == org_id)
            .values(ticket_seq=Organization.ticket_seq + 1)
            .returning(Organization.ticket_seq)
        )
        return int(number or 0)


class CalendarRepository(TenantRepository[BusinessCalendar]):
    model = BusinessCalendar

    async def settings(self) -> BusinessCalendar | None:
        return await self.first(self.scoped())

    async def calendar(self) -> Calendar | None:
        """The SLA calendar of the organisation, or None for 24/7."""
        row = await self.settings()
        if row is None:
            return None
        return Calendar.from_settings(row.timezone, row.weekly_hours, await HolidayRepository(self.session, self.org_id).days())


class HolidayRepository(TenantRepository[Holiday]):
    model = Holiday

    async def days(self) -> set[date]:
        return set((await self.session.scalars(self.scoped(Holiday.day))).all())

    async def list_all(self) -> list[Holiday]:
        return list((await self.session.scalars(self.scoped().order_by(Holiday.day))).all())
