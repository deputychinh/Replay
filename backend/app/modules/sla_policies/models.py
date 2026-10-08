from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import TicketPriority
from app.db.base import Base, IdMixin, TenantMixin, pg_enum


class SlaPolicy(IdMixin, TenantMixin, Base):
    """Targets in business minutes for one priority."""

    __tablename__ = "sla_policies"
    __table_args__ = (UniqueConstraint("org_id", "priority"),)

    priority: Mapped[TicketPriority] = mapped_column(pg_enum(TicketPriority, "ticket_priority"))
    first_response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)
