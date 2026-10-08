import uuid
from datetime import UTC, datetime, timedelta

import pytest

import app.db.models  # noqa: F401  (register every model)
from app.common.enums import SlaState, TicketPriority, TicketStatus
from app.db.base import Base, TenantMixin
from app.db.tenant import TENANT_REPOSITORIES
from app.modules.automations.assignment import RoundRobin
from app.modules.tickets import sla
from app.modules.tickets.models import Ticket
from app.modules.tickets.rules import TICKET_TRANSITIONS, can_transition
from app.sla.policy import Targets

S = TicketStatus
NOW = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)


def test_every_tenant_model_has_a_scoped_repository() -> None:
    """DS-03: a table with org_id can only be read through TenantRepository.scoped()."""
    import app.main  # noqa: F401  (every router and its repositories)
    from app.jobs.registry import handlers

    handlers()  # worker-only repositories

    tenant_models = {m.class_ for m in Base.registry.mappers if issubclass(m.class_, TenantMixin)}
    assert tenant_models - set(TENANT_REPOSITORIES) == set()


def test_closed_is_final_and_solved_can_reopen() -> None:
    assert TICKET_TRANSITIONS[S.CLOSED] == frozenset()
    assert can_transition(S.SOLVED, S.OPEN)
    assert not can_transition(S.NEW, S.CLOSED)
    assert not can_transition(S.OPEN, S.NEW)


@pytest.mark.parametrize("status", list(S))
def test_no_status_moves_to_itself(status: TicketStatus) -> None:
    assert status not in TICKET_TRANSITIONS[status]


def _ticket() -> Ticket:
    ticket = Ticket(status=S.OPEN, priority=TicketPriority.NORMAL)
    sla.start_clock(ticket, NOW, Targets(60, 600), None)
    return ticket


def test_pause_and_resume_keep_the_remaining_time() -> None:
    ticket = _ticket()
    sla.on_status_change(ticket, S.OPEN, S.PENDING_CUSTOMER, NOW + timedelta(minutes=100), None)
    assert ticket.sla_state == SlaState.PAUSED
    assert ticket.resolution_due_at is None and ticket.resolution_remaining_minutes == 500

    later = NOW + timedelta(days=3)
    sla.on_status_change(ticket, S.PENDING_CUSTOMER, S.OPEN, later, None)
    assert ticket.sla_state == SlaState.ACTIVE
    assert ticket.resolution_due_at == later + timedelta(minutes=500)


def test_solving_in_time_meets_the_sla() -> None:
    ticket = _ticket()
    sla.record_first_response(ticket, NOW + timedelta(minutes=30))
    sla.on_status_change(ticket, S.OPEN, S.SOLVED, NOW + timedelta(minutes=200), None)
    assert ticket.sla_state == SlaState.MET


def test_late_first_response_breaches_even_if_solved_in_time() -> None:
    ticket = _ticket()
    sla.record_first_response(ticket, NOW + timedelta(minutes=90))
    sla.on_status_change(ticket, S.OPEN, S.SOLVED, NOW + timedelta(minutes=200), None)
    assert ticket.sla_state == SlaState.BREACHED


def test_a_breach_is_not_undone_by_pausing() -> None:
    ticket = _ticket()
    ticket.sla_state = SlaState.BREACHED
    sla.on_status_change(ticket, S.OPEN, S.PENDING_CUSTOMER, NOW, None)
    assert ticket.sla_state == SlaState.BREACHED


def test_round_robin_cycles_and_survives_agents_leaving() -> None:
    a, b, c = (uuid.UUID(int=i) for i in (1, 2, 3))
    rr = RoundRobin()
    assert rr.pick([a, b, c], None) == a
    assert rr.pick([a, b, c], a) == b
    assert rr.pick([a, b, c], c) == a
    assert rr.pick([a, c], b) == a  # b left the team
    assert rr.pick([], a) is None
