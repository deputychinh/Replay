import uuid
from datetime import datetime

from fastapi import APIRouter

from app.common.enums import EventName
from app.common.schemas import ERROR_RESPONSES, Schema
from app.core.deps import CurrentActor, Uow
from app.modules.notifications.repository import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"], responses=ERROR_RESPONSES)


class NotificationOut(Schema):
    id: uuid.UUID
    kind: EventName
    message: str
    ticket_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(Schema):
    items: list[NotificationOut]
    unread: int


@router.get("", response_model=NotificationList)
async def list_notifications(actor: CurrentActor, uow: Uow) -> NotificationList:
    repo = NotificationRepository(uow.session, actor.org_id)
    items = await repo.for_user(actor.user_id)
    return NotificationList(
        items=[NotificationOut.model_validate(n) for n in items], unread=await repo.unread_count(actor.user_id)
    )


@router.post("/read", status_code=204)
async def mark_read(actor: CurrentActor, uow: Uow) -> None:
    await NotificationRepository(uow.session, actor.org_id).mark_all_read(actor.user_id)
    await uow.commit()
