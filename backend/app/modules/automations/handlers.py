"""System automations run by the worker: auto-assign, SLA scan, auto-close."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.common.constants import AUTO_CLOSE_AFTER_SOLVED_DAYS, SLA_WARNING_MINUTES
from app.common.enums import EventName, Role, SlaState, TicketEventType, TicketStatus
from app.core.deps import Actor
from app.db.unit_of_work import UnitOfWork
from app.modules.automations.assignment import RoundRobin
from app.modules.notifications.service import Email, Notifier
from app.modules.teams.repository import TeamMemberRepository, TeamRepository
from app.modules.tickets.models import Ticket
from app.modules.tickets.repository import TicketEventRepository, TicketRepository, all_org_ids
from app.modules.tickets.service import TicketService
from app.modules.users.repository import UserRepository
from app.realtime.publisher import publish

SYSTEM_USER = uuid.UUID(int=0)


def system_actor(org_id: uuid.UUID) -> Actor:
    return Actor(SYSTEM_USER, org_id, Role.ADMIN)


async def auto_assign(payload: dict[str, Any], uow: UnitOfWork) -> None:
    org_id, ticket_id = uuid.UUID(payload["org_id"]), uuid.UUID(payload["ticket_id"])
    service = TicketService(uow, system_actor(org_id))
    ticket = await service.tickets.for_update(ticket_id)
    if ticket is None or ticket.assignee_id or ticket.team_id is None:
        return
    team = await TeamRepository(uow.session, org_id).lock(ticket.team_id)
    agents = await TeamMemberRepository(uow.session, org_id).active_agents(ticket.team_id)
    chosen = RoundRobin().pick(agents, team.last_assigned_user_id if team else None)
    if chosen is None or team is None:
        return
    team.last_assigned_user_id = chosen
    await service.assign(ticket, chosen, by=None)

    async def push() -> None:
        await publish(org_id, EventName.TICKET_UPDATED, {"id": ticket_id})

    uow.after_commit(push)


async def sla_scan(payload: dict[str, Any], uow: UnitOfWork) -> None:
    """Every minute: warn once before a breach, flag a breach once. Locked rows are skipped
    (another worker has them), so two workers never notify twice."""
    now = datetime.now(UTC)
    for org_id in await all_org_ids(uow.session):
        tickets = TicketRepository(uow.session, org_id)
        for ticket in await tickets.due_for_warning(now + timedelta(minutes=SLA_WARNING_MINUTES)):
            if ticket.resolution_due_at and ticket.resolution_due_at >= now:
                ticket.sla_warned_at = now
                await _alert(
                    uow,
                    org_id,
                    ticket,
                    TicketEventType.SLA_WARNING,
                    EventName.SLA_WARNING,
                    f"#{ticket.number} breaches its SLA in under {SLA_WARNING_MINUTES} minutes",
                    managers=False,
                )
        for ticket in await tickets.overdue(now):
            ticket.sla_state = SlaState.BREACHED
            await _alert(
                uow,
                org_id,
                ticket,
                TicketEventType.SLA_BREACHED,
                EventName.SLA_BREACHED,
                f"#{ticket.number} breached its SLA: {ticket.subject}",
                managers=True,
            )


async def _alert(
    uow: UnitOfWork,
    org_id: uuid.UUID,
    ticket: Ticket,
    event_type: TicketEventType,
    event: EventName,
    message: str,
    managers: bool,
) -> None:
    TicketEventRepository(uow.session, org_id).record(ticket.id, event_type, None)
    users = UserRepository(uow.session, org_id)
    recipients = {u.id: u for u in (await users.managers() if managers else [])}
    if ticket.assignee_id and (assignee := await users.find(ticket.assignee_id)):
        recipients[assignee.id] = assignee
    notifier = Notifier(uow, org_id)
    for user in recipients.values():
        notifier.notify(
            user,
            event,
            message,
            ticket.id,
            email=Email(f"[Relay] {message}", "Open the ticket in the console.") if managers else None,
        )
    ticket_id = ticket.id

    async def push() -> None:
        await publish(org_id, event, {"id": ticket_id})

    uow.after_commit(push)


async def auto_close(payload: dict[str, Any], uow: UnitOfWork) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=AUTO_CLOSE_AFTER_SOLVED_DAYS)
    for org_id in await all_org_ids(uow.session):
        events = TicketEventRepository(uow.session, org_id)
        rows = await uow.session.scalars(
            select(Ticket).where(Ticket.org_id == org_id, Ticket.status == TicketStatus.SOLVED, Ticket.solved_at < cutoff)
        )
        for ticket in rows:
            events.record(ticket.id, TicketEventType.STATUS_CHANGED, None, old=ticket.status, new=TicketStatus.CLOSED)
            ticket.status = TicketStatus.CLOSED
