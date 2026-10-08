import uuid

from fastapi import APIRouter
from pydantic import Field

from app.common.constants import BODY_MAX_LENGTH
from app.common.schemas import ERROR_RESPONSES, Schema
from app.core.deps import ManagerActor, StaffActor, Uow
from app.db.tenant import TenantRepository
from app.modules.canned_replies.models import CannedReply

router = APIRouter(prefix="/canned-replies", tags=["canned replies"], responses=ERROR_RESPONSES)


class CannedReplyRepository(TenantRepository[CannedReply]):
    model = CannedReply

    async def list_all(self) -> list[CannedReply]:
        return list((await self.session.scalars(self.scoped().order_by(CannedReply.title))).all())


class CannedReplyIn(Schema):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(
        min_length=1,
        max_length=BODY_MAX_LENGTH,
        description="Placeholders: {{customer.name}}, {{agent.name}}, {{ticket.number}}",
    )


class CannedReplyOut(CannedReplyIn):
    id: uuid.UUID


@router.get("", response_model=list[CannedReplyOut])
async def list_replies(actor: StaffActor, uow: Uow) -> list[CannedReplyOut]:
    return [CannedReplyOut.model_validate(r) for r in await CannedReplyRepository(uow.session, actor.org_id).list_all()]


@router.post("", response_model=CannedReplyOut, status_code=201)
async def create_reply(body: CannedReplyIn, actor: ManagerActor, uow: Uow) -> CannedReplyOut:
    reply = CannedReplyRepository(uow.session, actor.org_id).add(CannedReply(**body.model_dump()))
    await uow.commit()
    return CannedReplyOut.model_validate(reply)


@router.delete("/{reply_id}", status_code=204)
async def delete_reply(reply_id: uuid.UUID, actor: ManagerActor, uow: Uow) -> None:
    repo = CannedReplyRepository(uow.session, actor.org_id)
    await uow.session.delete(await repo.get(reply_id))
    await uow.commit()
