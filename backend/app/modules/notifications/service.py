"""In-app notification + live push + email job, in one call."""

import uuid
from dataclasses import dataclass

from app.common.enums import EventName, JobType
from app.db.unit_of_work import UnitOfWork
from app.jobs.queue import enqueue
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository
from app.modules.users.models import User
from app.realtime.publisher import publish


@dataclass(frozen=True)
class Email:
    subject: str
    text: str


class Notifier:
    def __init__(self, uow: UnitOfWork, org_id: uuid.UUID) -> None:
        self.uow = uow
        self.org_id = org_id
        self.repo = NotificationRepository(uow.session, org_id)

    def notify(
        self,
        user: User,
        kind: EventName,
        message: str,
        ticket_id: uuid.UUID | None = None,
        email: Email | None = None,
        in_app: bool = True,
    ) -> None:
        """Queued in the unit of work; the push and the email go out only after commit."""
        if in_app:
            note = self.repo.add(Notification(user_id=user.id, ticket_id=ticket_id, kind=kind, message=message))

            async def push() -> None:
                await publish(
                    self.org_id,
                    EventName.NOTIFICATION,
                    {"id": note.id, "message": message, "ticket_id": ticket_id, "kind": kind},
                    user_id=user.id,
                )

            self.uow.after_commit(push)
        if email:
            key = f"email:{kind}:{ticket_id}:{user.id}:{uuid.uuid4()}"

            async def send() -> None:
                await enqueue(JobType.SEND_EMAIL, {"to": user.email, "subject": email.subject, "text": email.text}, key)

            self.uow.after_commit(send)
