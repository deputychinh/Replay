import uuid
from datetime import datetime

from pydantic import Field

from app.common.constants import BODY_MAX_LENGTH
from app.common.enums import MessageKind, TicketStatus
from app.common.schemas import Schema
from app.modules.tickets.schemas import PersonRef


class MessageCreate(Schema):
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)
    kind: MessageKind = MessageKind.PUBLIC_REPLY
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    status_after: TicketStatus | None = Field(
        default=None, description="Staff only. Defaults to pending_customer after a public reply."
    )


class AttachmentOut(Schema):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int


class MessageOut(Schema):
    id: uuid.UUID
    kind: MessageKind
    body: str
    author: PersonRef
    author_is_staff: bool
    attachments: list[AttachmentOut]
    created_at: datetime
