"""Ticket use cases. One transaction each; live events and jobs go out after commit."""

import uuid
from datetime import UTC, datetime

from app.common.enums import (
    EventName,
    JobType,
    MessageKind,
    Role,
    SlaState,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)
from app.core.deps import Actor
from app.core.errors import ForbiddenError, InvalidTransitionError, NotFoundError, ValidationError
from app.db.unit_of_work import UnitOfWork
from app.jobs.queue import enqueue
from app.modules.attachments.repository import AttachmentRepository
from app.modules.messages.models import Message
from app.modules.notifications.service import Email, Notifier
from app.modules.organizations.repository import CalendarRepository, OrganizationRepository
from app.modules.sla_policies.repository import SlaPolicyRepository
from app.modules.teams.repository import TeamRepository
from app.modules.tickets import sla
from app.modules.tickets.models import Ticket
from app.modules.tickets.presenter import present_ticket
from app.modules.tickets.repository import TicketEventRepository, TicketRepository
from app.modules.tickets.rules import can_transition
from app.modules.tickets.schemas import BulkUpdate, TicketCreate, TicketDetail, TicketUpdate
from app.modules.users.repository import UserRepository
from app.realtime.publisher import publish


class TicketService:
    def __init__(self, uow: UnitOfWork, actor: Actor) -> None:
        self.uow, self.actor = uow, actor
        session, org = uow.session, actor.org_id
        self.tickets = TicketRepository(session, org)
        self.events = TicketEventRepository(session, org)
        self.users = UserRepository(session, org)
        self.notifier = Notifier(uow, org)

    async def get_visible(self, ticket_id: uuid.UUID) -> Ticket:
        """Customers may only see their own tickets; anything else is a 404, not a 403."""
        ticket = await self.tickets.get(ticket_id)
        if not self.actor.is_staff and ticket.requester_id != self.actor.user_id:
            raise NotFoundError()
        return ticket

    async def create(self, body: TicketCreate) -> TicketDetail:
        requester_id = self.actor.user_id
        if body.requester_id:
            if not self.actor.is_staff:
                raise ForbiddenError()
            requester = await self.users.find(body.requester_id)
            if requester is None or requester.role != Role.CUSTOMER:
                raise ValidationError("The requester must be a customer of this organisation.")
            requester_id = requester.id

        now = datetime.now(UTC)
        session, org_id = self.uow.session, self.actor.org_id
        team = await TeamRepository(session, org_id).default()
        ticket = self.tickets.add(
            Ticket(
                number=await OrganizationRepository(session).next_ticket_number(org_id),
                subject=body.subject.strip(),
                priority=body.priority,
                status=TicketStatus.NEW,
                requester_id=requester_id,
                team_id=team.id if team else None,
                tags=[],
                created_at=now,
                updated_at=now,
            )
        )
        targets = await SlaPolicyRepository(session, org_id).targets(body.priority)
        sla.start_clock(ticket, now, targets, await CalendarRepository(session, org_id).calendar())
        await session.flush()

        message = Message(ticket_id=ticket.id, author_id=requester_id, kind=MessageKind.PUBLIC_REPLY, body=body.body)
        message.org_id = org_id
        session.add(message)
        await session.flush()
        await AttachmentRepository(session, org_id).link(body.attachment_ids, ticket.id, message.id, self.actor.user_id)
        self.events.record(ticket.id, TicketEventType.CREATED, self.actor.user_id, priority=body.priority)

        ticket_id = ticket.id

        async def announce() -> None:
            await publish(org_id, EventName.TICKET_CREATED, {"id": ticket_id})
            await enqueue(JobType.AUTO_ASSIGN, {"org_id": org_id, "ticket_id": ticket_id}, f"assign:{ticket_id}")

        self.uow.after_commit(announce)
        await self.uow.commit()
        return await present_ticket(self.users, ticket, self.actor.is_staff)

    async def update(self, ticket_id: uuid.UUID, body: TicketUpdate) -> TicketDetail:
        ticket = await self.tickets.for_update(ticket_id)
        if ticket is None:
            raise NotFoundError()
        await self._apply(ticket, body)
        await self.uow.commit()
        return await present_ticket(self.users, ticket, True)

    async def bulk_update(self, body: BulkUpdate) -> int:
        tickets = await self.tickets.many_for_update(body.ids)
        for ticket in tickets:
            await self._apply(ticket, body)
        await self.uow.commit()
        return len(tickets)

    async def _apply(self, ticket: Ticket, body: TicketUpdate) -> None:
        now = datetime.now(UTC)
        session, org_id = self.uow.session, self.actor.org_id
        changed = False

        if body.status and body.status != ticket.status:
            if not can_transition(ticket.status, body.status):
                raise InvalidTransitionError(f"A {ticket.status} ticket cannot become {body.status}.")
            calendar = await CalendarRepository(session, org_id).calendar()
            sla.on_status_change(ticket, ticket.status, body.status, now, calendar)
            self.events.record(ticket.id, TicketEventType.STATUS_CHANGED, self.actor.user_id, old=ticket.status, new=body.status)
            ticket.status, changed = body.status, True

        if body.priority and body.priority != ticket.priority:
            await self._change_priority(ticket, body.priority)
            changed = True

        if body.unassign and ticket.assignee_id:
            ticket.assignee_id, changed = None, True
            self.events.record(ticket.id, TicketEventType.ASSIGNED, self.actor.user_id, assignee=None)
        elif body.assignee_id and body.assignee_id != ticket.assignee_id:
            await self.assign(ticket, body.assignee_id, by=self.actor.user_id)
            changed = True

        if body.tags is not None and body.tags != ticket.tags:
            ticket.tags, changed = body.tags, True

        if changed:
            ticket.updated_at = now
            self._announce_update(ticket.id)

    async def _change_priority(self, ticket: Ticket, priority: TicketPriority) -> None:
        """New targets, measured from when the ticket was opened (unless already paused or done)."""
        session, org_id = self.uow.session, self.actor.org_id
        self.events.record(ticket.id, TicketEventType.PRIORITY_CHANGED, self.actor.user_id, old=ticket.priority, new=priority)
        ticket.priority = priority
        if ticket.sla_state == SlaState.ACTIVE:
            targets = await SlaPolicyRepository(session, org_id).targets(priority)
            calendar = await CalendarRepository(session, org_id).calendar()
            first_response_at = ticket.first_responded_at
            sla.start_clock(ticket, ticket.created_at, targets, calendar)
            ticket.first_responded_at = first_response_at

    async def assign(self, ticket: Ticket, assignee_id: uuid.UUID, by: uuid.UUID | None) -> None:
        assignee = await self.users.find(assignee_id)
        if assignee is None or not assignee.is_active or assignee.role == Role.CUSTOMER:
            raise ValidationError("Tickets can only be assigned to active staff.")
        ticket.assignee_id = assignee.id
        if ticket.status == TicketStatus.NEW:
            ticket.status = TicketStatus.OPEN
        self.events.record(ticket.id, TicketEventType.ASSIGNED, by, assignee=assignee.full_name)
        if assignee.id != by:
            self.notifier.notify(
                assignee,
                EventName.TICKET_UPDATED,
                f"#{ticket.number} was assigned to you: {ticket.subject}",
                ticket.id,
                email=Email(f"[Relay] #{ticket.number} assigned to you", f"{ticket.subject}\n\nOpen it in the console."),
            )

    def _announce_update(self, ticket_id: uuid.UUID) -> None:
        org_id = self.actor.org_id

        async def push() -> None:
            await publish(org_id, EventName.TICKET_UPDATED, {"id": ticket_id})

        self.uow.after_commit(push)
