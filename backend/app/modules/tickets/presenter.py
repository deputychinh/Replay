"""Turn ticket rows into API shapes with people's names, in one query for the whole page."""

import uuid

from app.modules.tickets.models import Ticket, TicketEvent
from app.modules.tickets.rules import TICKET_TRANSITIONS
from app.modules.tickets.schemas import PersonRef, TicketDetail, TicketEventOut, TicketOut
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


def _person(user: User | None) -> PersonRef | None:
    return PersonRef(id=user.id, full_name=user.full_name, company=user.company) if user else None


async def present_tickets(users: UserRepository, tickets: list[Ticket]) -> list[TicketOut]:
    ids: set[uuid.UUID] = {t.requester_id for t in tickets} | {t.assignee_id for t in tickets if t.assignee_id}
    people = await users.by_ids(ids)
    return [
        TicketOut.model_validate(
            {
                **{k: getattr(t, k) for k in TicketOut.model_fields if k not in {"requester", "assignee"}},
                "requester": _person(people.get(t.requester_id)),
                "assignee": _person(people.get(t.assignee_id)) if t.assignee_id else None,
            }
        )
        for t in tickets
    ]


async def present_ticket(users: UserRepository, ticket: Ticket, staff: bool) -> TicketDetail:
    base = (await present_tickets(users, [ticket]))[0]
    allowed = sorted(TICKET_TRANSITIONS[ticket.status]) if staff else []
    return TicketDetail(**base.model_dump(), allowed_statuses=allowed)


async def present_events(users: UserRepository, events: list[TicketEvent]) -> list[TicketEventOut]:
    people = await users.by_ids({e.actor_id for e in events if e.actor_id})
    return [
        TicketEventOut(
            id=e.id,
            type=e.type,
            actor=_person(people.get(e.actor_id)) if e.actor_id else None,
            data=e.data,
            created_at=e.created_at,
        )
        for e in events
    ]
