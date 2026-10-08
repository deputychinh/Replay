"""Ticket list filters and keyset sort orders (Specification pattern)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, literal, or_, tuple_
from sqlalchemy.orm import InstrumentedAttribute

from app.common.constants import BREACHING_SOON_HOURS
from app.common.enums import SlaState, TicketSort, TicketView
from app.common.schemas import decode_cursor, encode_cursor
from app.core.deps import Actor
from app.modules.tickets.models import Ticket
from app.modules.tickets.rules import OPEN_STATUSES
from app.modules.tickets.schemas import TicketQuery


@dataclass(frozen=True)
class SortSpec:
    columns: tuple[InstrumentedAttribute[Any], ...]
    descending: bool


SORTS: dict[TicketSort, SortSpec] = {
    TicketSort.NEWEST: SortSpec((Ticket.updated_at, Ticket.id), descending=True),
    TicketSort.OLDEST: SortSpec((Ticket.updated_at, Ticket.id), descending=False),
    TicketSort.PRIORITY: SortSpec((Ticket.priority, Ticket.updated_at, Ticket.id), descending=True),
    TicketSort.SLA_DUE: SortSpec((Ticket.sla_due_at, Ticket.id), descending=False),
}


def apply_filters(query: Select[Any], params: TicketQuery, actor: Actor, now: datetime | None = None) -> Select[Any]:
    now = now or datetime.now(UTC)
    if not actor.is_staff:
        return query.where(Ticket.requester_id == actor.user_id)  # customers see only their own tickets

    if params.view == TicketView.MINE:
        query = query.where(Ticket.assignee_id == actor.user_id, Ticket.status.in_(OPEN_STATUSES))
    elif params.view == TicketView.UNASSIGNED:
        query = query.where(Ticket.assignee_id.is_(None), Ticket.status.in_(OPEN_STATUSES))
    elif params.view == TicketView.BREACHING_SOON:
        soon = now + timedelta(hours=BREACHING_SOON_HOURS)
        query = query.where(
            Ticket.status.in_(OPEN_STATUSES),
            Ticket.sla_state.in_([SlaState.ACTIVE, SlaState.BREACHED]),
            Ticket.sla_due_at <= soon,
        )
    if params.status:
        query = query.where(Ticket.status == params.status)
    if params.priority:
        query = query.where(Ticket.priority == params.priority)
    if params.assignee_id:
        query = query.where(Ticket.assignee_id == params.assignee_id)
    if params.tag:
        query = query.where(Ticket.tags.contains([params.tag.lower()]))
    if params.q:
        text = params.q.strip()
        match = Ticket.search.op("@@")(func.websearch_to_tsquery("english", text))
        query = query.where(or_(match, Ticket.number == int(text))) if text.isdigit() else query.where(match)
    return query


def apply_sort(query: Select[Any], sort: TicketSort, cursor: str | None, limit: int) -> Select[Any]:
    spec = SORTS[sort]
    if sort == TicketSort.SLA_DUE:
        query = query.where(Ticket.sla_due_at.is_not(None))
    if cursor:
        values = decode_cursor(cursor)["v"]
        keys = tuple_(*spec.columns)
        bound = tuple_(*[_cursor_value(col, value) for col, value in zip(spec.columns, values, strict=True)])
        query = query.where(keys < bound if spec.descending else keys > bound)
    order = [col.desc() if spec.descending else col.asc() for col in spec.columns]
    return query.order_by(*order).limit(limit + 1)


def next_cursor(rows: list[Ticket], sort: TicketSort, limit: int) -> str | None:
    if len(rows) <= limit:
        return None
    last = rows[limit - 1]
    return encode_cursor({"v": [getattr(last, col.key) for col in SORTS[sort].columns]})


def _cursor_value(column: InstrumentedAttribute[Any], value: Any) -> Any:
    """Bind the cursor value with the column's own type (enum, timestamp, uuid)."""
    if column.key in {"updated_at", "sla_due_at"}:
        value = datetime.fromisoformat(value)
    return literal(value, column.type)
