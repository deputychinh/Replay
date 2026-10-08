import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.constants import DEFAULT_TIMEZONE
from app.db.base import Base, IdMixin, TenantMixin, TimestampMixin


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    ticket_seq: Mapped[int] = mapped_column(Integer, default=0)
    brand_color: Mapped[str | None] = mapped_column(String(7))


class BusinessCalendar(TenantMixin, Base):
    """Working hours for SLA maths. weekly_hours: {"0": [540, 1020], ...} = Monday 09:00-17:00 (minutes)."""

    __tablename__ = "business_calendars"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    timezone: Mapped[str] = mapped_column(String(60), default=DEFAULT_TIMEZONE)
    weekly_hours: Mapped[dict[str, list[int]]] = mapped_column(JSONB)


class Holiday(IdMixin, TenantMixin, Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("org_id", "day"),)

    day: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(120))
