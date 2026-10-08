"""Ticket status machine — the only place that says which status may follow which."""

from app.common.enums import TicketStatus as S

TICKET_TRANSITIONS: dict[S, frozenset[S]] = {
    S.NEW: frozenset({S.OPEN, S.PENDING_CUSTOMER, S.ON_HOLD, S.SOLVED}),
    S.OPEN: frozenset({S.PENDING_CUSTOMER, S.ON_HOLD, S.SOLVED}),
    S.PENDING_CUSTOMER: frozenset({S.OPEN, S.ON_HOLD, S.SOLVED}),
    S.ON_HOLD: frozenset({S.OPEN, S.PENDING_CUSTOMER, S.SOLVED}),
    S.SOLVED: frozenset({S.OPEN, S.CLOSED}),
    S.CLOSED: frozenset(),
}

# The resolution clock stops while we wait for the customer.
PAUSING_STATUSES = frozenset({S.PENDING_CUSTOMER})
# A customer reply on these reopens the ticket.
REOPEN_ON_CUSTOMER_REPLY = frozenset({S.NEW, S.PENDING_CUSTOMER, S.SOLVED})
OPEN_STATUSES = frozenset({S.NEW, S.OPEN, S.PENDING_CUSTOMER, S.ON_HOLD})


def can_transition(current: S, target: S) -> bool:
    return target in TICKET_TRANSITIONS[current]
