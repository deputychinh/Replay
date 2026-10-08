"""Apply the SLA rules (app/sla) to a ticket when it is created or changes."""

from datetime import datetime

from app.common.enums import SlaState, TicketStatus
from app.modules.tickets.models import Ticket
from app.modules.tickets.rules import PAUSING_STATUSES
from app.sla.calendar import BusinessCalendar
from app.sla.policy import Targets, initial_due_dates, is_breached, remaining_minutes, resumed_due_at


def start_clock(ticket: Ticket, start: datetime, targets: Targets, calendar: BusinessCalendar | None) -> None:
    ticket.first_response_due_at, ticket.resolution_due_at = initial_due_dates(start, targets, calendar)
    ticket.sla_state = SlaState.ACTIVE
    ticket.resolution_remaining_minutes = None
    ticket.sla_warned_at = None


def on_status_change(
    ticket: Ticket, old: TicketStatus, new: TicketStatus, now: datetime, calendar: BusinessCalendar | None
) -> None:
    if ticket.sla_state == SlaState.BREACHED and new not in {TicketStatus.SOLVED, TicketStatus.CLOSED}:
        return  # a breach stays a breach; only solving changes the record
    if new in PAUSING_STATUSES and old not in PAUSING_STATUSES and ticket.resolution_due_at:
        ticket.resolution_remaining_minutes = remaining_minutes(now, ticket.resolution_due_at, calendar)
        ticket.resolution_due_at = None
        ticket.sla_state = SlaState.PAUSED
    elif old in PAUSING_STATUSES and new not in PAUSING_STATUSES and ticket.resolution_remaining_minutes is not None:
        ticket.resolution_due_at = resumed_due_at(now, ticket.resolution_remaining_minutes, calendar)
        ticket.resolution_remaining_minutes = None
        ticket.sla_state = SlaState.ACTIVE
    if new == TicketStatus.SOLVED:
        ticket.solved_at = now
        breached = (
            ticket.sla_state == SlaState.BREACHED
            or is_breached(ticket.resolution_due_at, now, now)
            or (is_breached(ticket.first_response_due_at, ticket.first_responded_at, now))
        )
        ticket.sla_state = SlaState.BREACHED if breached else SlaState.MET
    elif old == TicketStatus.SOLVED and new == TicketStatus.OPEN:
        ticket.solved_at = None
        ticket.sla_state = SlaState.BREACHED if is_breached(ticket.resolution_due_at, None, now) else SlaState.ACTIVE


def record_first_response(ticket: Ticket, now: datetime) -> None:
    if ticket.first_responded_at is None:
        ticket.first_responded_at = now
