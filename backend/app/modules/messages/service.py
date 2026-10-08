"""Replies and internal notes, with the status and SLA effects of each."""

import uuid
from datetime import UTC, datetime

from app.common.enums import STAFF_ROLES, EventName, MessageKind, TicketEventType, TicketStatus
from app.core.deps import Actor
from app.core.errors import ForbiddenError, InvalidTransitionError
from app.db.unit_of_work import UnitOfWork
from app.modules.attachments.repository import AttachmentRepository
from app.modules.messages.models import Message
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import AttachmentOut, MessageCreate, MessageOut
from app.modules.notifications.service import Email
from app.modules.organizations.repository import CalendarRepository
from app.modules.tickets import sla
from app.modules.tickets.models import Ticket
from app.modules.tickets.rules import REOPEN_ON_CUSTOMER_REPLY, can_transition
from app.modules.tickets.schemas import PersonRef
from app.modules.tickets.service import TicketService
from app.realtime.publisher import publish


class MessageService:
    def __init__(self, uow: UnitOfWork, actor: Actor) -> None:
        self.uow, self.actor = uow, actor
        self.tickets = TicketService(uow, actor)
        self.messages = MessageRepository(uow.session, actor.org_id)
        self.attachments = AttachmentRepository(uow.session, actor.org_id)

    async def for_ticket(self, ticket_id: uuid.UUID) -> list[MessageOut]:
        await self.tickets.get_visible(ticket_id)
        rows = await self.messages.for_ticket(ticket_id, include_internal=self.actor.is_staff)
        return await self._present(rows)

    async def add(self, ticket_id: uuid.UUID, body: MessageCreate) -> MessageOut:
        ticket = await self.tickets.get_visible(ticket_id)
        ticket = await self.tickets.tickets.for_update(ticket.id) or ticket
        if ticket.status == TicketStatus.CLOSED:
            raise InvalidTransitionError("This ticket is closed. Please open a new one.")
        if not self.actor.is_staff and (body.kind != MessageKind.PUBLIC_REPLY or body.status_after):
            raise ForbiddenError()

        now = datetime.now(UTC)
        message = self.messages.add(Message(ticket_id=ticket.id, author_id=self.actor.user_id, kind=body.kind, body=body.body))
        await self.uow.session.flush()
        await self.attachments.link(body.attachment_ids, ticket.id, message.id, self.actor.user_id)

        if body.kind == MessageKind.INTERNAL_NOTE:
            self.tickets.events.record(ticket.id, TicketEventType.NOTE_ADDED, self.actor.user_id)
        elif self.actor.is_staff:
            await self._after_agent_reply(ticket, body, now)
        else:
            await self._after_customer_reply(ticket, now)

        ticket.updated_at = now
        org_id, tid, mid, kind = self.actor.org_id, ticket.id, message.id, body.kind

        async def push() -> None:
            await publish(org_id, EventName.REPLY_ADDED, {"ticket_id": tid, "message_id": mid, "kind": kind})

        self.uow.after_commit(push)
        await self.uow.commit()
        return (await self._present([message]))[0]

    async def _after_agent_reply(self, ticket: Ticket, body: MessageCreate, now: datetime) -> None:
        sla.record_first_response(ticket, now)
        target = body.status_after or TicketStatus.PENDING_CUSTOMER
        if target != ticket.status:
            if not can_transition(ticket.status, target):
                raise InvalidTransitionError()
            calendar = await CalendarRepository(self.uow.session, self.actor.org_id).calendar()
            sla.on_status_change(ticket, ticket.status, target, now, calendar)
            self.tickets.events.record(
                ticket.id, TicketEventType.STATUS_CHANGED, self.actor.user_id, old=ticket.status, new=target
            )
            ticket.status = target
        if ticket.assignee_id is None:
            ticket.assignee_id = self.actor.user_id
        self.tickets.events.record(ticket.id, TicketEventType.REPLIED, self.actor.user_id)
        requester = await self.tickets.users.find(ticket.requester_id)
        if requester:
            self.tickets.notifier.notify(
                requester,
                EventName.REPLY_ADDED,
                f"New reply on #{ticket.number}",
                ticket.id,
                email=Email(f"[Relay] Re: {ticket.subject} (#{ticket.number})", f"{body.body}\n\nReply in the portal."),
            )

    async def _after_customer_reply(self, ticket: Ticket, now: datetime) -> None:
        if ticket.status in REOPEN_ON_CUSTOMER_REPLY and ticket.status != TicketStatus.NEW:
            calendar = await CalendarRepository(self.uow.session, self.actor.org_id).calendar()
            sla.on_status_change(ticket, ticket.status, TicketStatus.OPEN, now, calendar)
            self.tickets.events.record(
                ticket.id, TicketEventType.STATUS_CHANGED, self.actor.user_id, old=ticket.status, new=TicketStatus.OPEN
            )
            ticket.status = TicketStatus.OPEN
        self.tickets.events.record(ticket.id, TicketEventType.REPLIED, self.actor.user_id)
        assignee = await self.tickets.users.find(ticket.assignee_id) if ticket.assignee_id else None
        if assignee:
            self.tickets.notifier.notify(
                assignee,
                EventName.REPLY_ADDED,
                f"Customer replied on #{ticket.number}",
                ticket.id,
                email=Email(f"[Relay] Customer replied: #{ticket.number}", ticket.subject),
            )

    async def _present(self, rows: list[Message]) -> list[MessageOut]:
        people = await self.tickets.users.by_ids({m.author_id for m in rows})
        files: dict[uuid.UUID, list[AttachmentOut]] = {}
        for a in await self.attachments.for_messages([m.id for m in rows]):
            files.setdefault(a.message_id, []).append(AttachmentOut.model_validate(a))  # type: ignore[arg-type]
        result = []
        for m in rows:
            author = people[m.author_id]
            result.append(
                MessageOut(
                    id=m.id,
                    kind=m.kind,
                    body=m.body,
                    created_at=m.created_at,
                    author=PersonRef(id=author.id, full_name=author.full_name, company=author.company),
                    author_is_staff=author.role in STAFF_ROLES,
                    attachments=files.get(m.id, []),
                )
            )
        return result
