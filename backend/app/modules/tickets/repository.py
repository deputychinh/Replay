import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.common.enums import SlaState, TicketSort, TicketView
from app.core.deps import Actor
from app.db.tenant import TenantRepository
from app.modules.tickets.filters import apply_filters, apply_sort, next_cursor
from app.modules.tickets.models import Ticket, TicketEvent
from app.modules.tickets.rules import OPEN_STATUSES
from app.modules.tickets.schemas import TicketQuery


class TicketRepository(TenantRepository[Ticket]):
    model = Ticket

    async def search(self, params: TicketQuery, actor: Actor) -> tuple[list[Ticket], str | None]:
        # "Breaching soon" is always ordered by the nearest deadline: the only order that makes sense for it,
        # and the one its index serves.
        sort = TicketSort.SLA_DUE if params.view == TicketView.BREACHING_SOON and actor.is_staff else params.sort
        query = apply_sort(apply_filters(self.scoped(), params, actor), sort, params.cursor, params.limit)
        rows = list((await self.session.scalars(query)).all())
        return rows[: params.limit], next_cursor(rows, sort, params.limit)

    async def for_update(self, ticket_id: uuid.UUID) -> Ticket | None:
        return await self.first(self.scoped().where(Ticket.id == ticket_id).with_for_update())

    async def many_for_update(self, ids: list[uuid.UUID]) -> list[Ticket]:
        query = self.scoped().where(Ticket.id.in_(ids)).order_by(Ticket.id).with_for_update()
        return list((await self.session.scalars(query)).all())

    async def due_for_warning(self, until: datetime) -> list[Ticket]:
        query = (
            self.scoped()
            .where(
                Ticket.status.in_(OPEN_STATUSES),
                Ticket.sla_state == SlaState.ACTIVE,
                Ticket.sla_warned_at.is_(None),
                Ticket.resolution_due_at <= until,
            )
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(query)).all())

    async def overdue(self, now: datetime) -> list[Ticket]:
        query = (
            self.scoped()
            .where(
                Ticket.status.in_(OPEN_STATUSES),
                Ticket.sla_state == SlaState.ACTIVE,
                (Ticket.resolution_due_at < now) | (Ticket.first_responded_at.is_(None) & (Ticket.first_response_due_at < now)),
            )
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.scalars(query)).all())


class TicketEventRepository(TenantRepository[TicketEvent]):
    model = TicketEvent

    async def for_ticket(self, ticket_id: uuid.UUID) -> list[TicketEvent]:
        query = self.scoped().where(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at)
        return list((await self.session.scalars(query)).all())

    def record(self, ticket_id: uuid.UUID, event_type: Any, actor_id: uuid.UUID | None, **data: Any) -> None:
        self.add(
            TicketEvent(
                ticket_id=ticket_id,
                type=event_type,
                actor_id=actor_id,
                data={k: str(v) if v is not None else None for k, v in data.items()},
            )
        )


async def all_org_ids(session: Any) -> list[uuid.UUID]:
    """For system jobs that sweep every tenant (SLA scan, auto-close)."""
    from app.modules.organizations.models import Organization

    return list((await session.scalars(select(Organization.id))).all())
