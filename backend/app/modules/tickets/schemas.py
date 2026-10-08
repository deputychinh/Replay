import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.common.constants import (
    BODY_MAX_LENGTH,
    BULK_UPDATE_MAX,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    SEARCH_MAX_LENGTH,
    SUBJECT_MAX_LENGTH,
    TAGS_MAX,
)
from app.common.enums import (
    SlaState,
    TicketChannel,
    TicketEventType,
    TicketPriority,
    TicketSort,
    TicketStatus,
    TicketView,
)
from app.common.schemas import Schema


class PersonRef(Schema):
    id: uuid.UUID
    full_name: str
    company: str | None = None


class TicketCreate(Schema):
    subject: str = Field(min_length=3, max_length=SUBJECT_MAX_LENGTH)
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)
    priority: TicketPriority = TicketPriority.NORMAL
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    requester_id: uuid.UUID | None = Field(default=None, description="Staff only: open on behalf of a customer")


class TicketUpdate(Schema):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: uuid.UUID | None = None
    unassign: bool = False
    tags: list[str] | None = Field(default=None, max_length=TAGS_MAX)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return sorted({t.strip().lower()[:40] for t in tags if t.strip()})


class BulkUpdate(TicketUpdate):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=BULK_UPDATE_MAX)


class TicketQuery(Schema):
    view: TicketView = TicketView.ALL
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: uuid.UUID | None = None
    tag: str | None = None
    q: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    sort: TicketSort = TicketSort.NEWEST
    cursor: str | None = None
    limit: int = Field(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX)


class TicketOut(Schema):
    id: uuid.UUID
    number: int
    subject: str
    status: TicketStatus
    priority: TicketPriority
    channel: TicketChannel
    requester: PersonRef
    assignee: PersonRef | None
    tags: list[str]
    sla_state: SlaState
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_responded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketOut):
    allowed_statuses: list[TicketStatus]


class TicketEventOut(Schema):
    id: uuid.UUID
    type: TicketEventType
    actor: PersonRef | None
    data: dict[str, object]
    created_at: datetime
