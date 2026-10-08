import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import SlaState, TicketChannel, TicketEventType, TicketPriority, TicketStatus
from app.db.base import Base, IdMixin, TenantMixin, TimestampMixin, pg_enum


class Ticket(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("org_id", "number"),
        # One index per list order, so keyset pages read ~25 index entries instead of scanning the table (NFR-01).
        Index("ix_tickets_org_updated", "org_id", text("updated_at DESC"), text("id DESC")),
        Index("ix_tickets_org_priority", "org_id", text("priority DESC"), text("updated_at DESC"), text("id DESC")),
        Index("ix_tickets_org_sla_due", "org_id", "sla_due_at", "id", postgresql_where=text("sla_due_at IS NOT NULL")),
        Index("ix_tickets_org_assignee_status", "org_id", "assignee_id", "status"),
        Index(
            "ix_tickets_unassigned_open",
            "org_id",
            text("updated_at DESC"),
            text("id DESC"),
            postgresql_where=text("assignee_id IS NULL AND status IN ('new', 'open', 'pending_customer', 'on_hold')"),
        ),
        Index("ix_tickets_search", "search", postgresql_using="gin"),
    )

    number: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[TicketStatus] = mapped_column(pg_enum(TicketStatus, "ticket_status"), default=TicketStatus.NEW)
    priority: Mapped[TicketPriority] = mapped_column(pg_enum(TicketPriority, "ticket_priority"), default=TicketPriority.NORMAL)
    channel: Mapped[TicketChannel] = mapped_column(pg_enum(TicketChannel, "ticket_channel"), default=TicketChannel.PORTAL)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list, server_default="{}")

    # SLA (business-hours maths in app/sla)
    sla_state: Mapped[SlaState] = mapped_column(pg_enum(SlaState, "sla_state"), default=SlaState.ACTIVE)
    first_response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_remaining_minutes: Mapped[int | None] = mapped_column(Integer)  # set while paused
    sla_warned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    search: Mapped[Any] = mapped_column(TSVECTOR, Computed("to_tsvector('english', subject)", persisted=True))
    # The next SLA deadline: first response until it happens, then resolution. Kept by Postgres.
    sla_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        Computed(
            "CASE WHEN first_responded_at IS NULL THEN LEAST(first_response_due_at, resolution_due_at) "
            "ELSE resolution_due_at END",
            persisted=True,
        ),
    )


class TicketEvent(IdMixin, TenantMixin, TimestampMixin, Base):
    """Audit log: who changed what, and when."""

    __tablename__ = "ticket_events"

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[TicketEventType] = mapped_column(pg_enum(TicketEventType, "ticket_event_type"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
