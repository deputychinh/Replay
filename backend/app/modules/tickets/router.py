import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.schemas import ERROR_RESPONSES, CursorPage, Schema
from app.core.deps import CurrentActor, StaffActor, Uow
from app.modules.messages.schemas import MessageCreate, MessageOut
from app.modules.messages.service import MessageService
from app.modules.tickets.presenter import present_events, present_ticket, present_tickets
from app.modules.tickets.schemas import (
    BulkUpdate,
    TicketCreate,
    TicketDetail,
    TicketEventOut,
    TicketOut,
    TicketQuery,
    TicketUpdate,
)
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"], responses=ERROR_RESPONSES)


class BulkResult(Schema):
    updated: int


@router.get("", response_model=CursorPage[TicketOut])
async def list_tickets(params: Annotated[TicketQuery, Depends()], actor: CurrentActor, uow: Uow) -> CursorPage[TicketOut]:
    service = TicketService(uow, actor)
    rows, cursor = await service.tickets.search(params, actor)
    return CursorPage(items=await present_tickets(service.users, rows), next_cursor=cursor)


@router.post("", response_model=TicketDetail, status_code=201)
async def create_ticket(body: TicketCreate, actor: CurrentActor, uow: Uow) -> TicketDetail:
    return await TicketService(uow, actor).create(body)


@router.post("/bulk", response_model=BulkResult)
async def bulk_update(body: BulkUpdate, actor: StaffActor, uow: Uow) -> BulkResult:
    return BulkResult(updated=await TicketService(uow, actor).bulk_update(body))


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: uuid.UUID, actor: CurrentActor, uow: Uow) -> TicketDetail:
    service = TicketService(uow, actor)
    return await present_ticket(service.users, await service.get_visible(ticket_id), actor.is_staff)


@router.patch("/{ticket_id}", response_model=TicketDetail)
async def update_ticket(ticket_id: uuid.UUID, body: TicketUpdate, actor: StaffActor, uow: Uow) -> TicketDetail:
    return await TicketService(uow, actor).update(ticket_id, body)


@router.get("/{ticket_id}/events", response_model=list[TicketEventOut])
async def ticket_events(ticket_id: uuid.UUID, actor: StaffActor, uow: Uow) -> list[TicketEventOut]:
    service = TicketService(uow, actor)
    await service.get_visible(ticket_id)
    return await present_events(service.users, await service.events.for_ticket(ticket_id))


@router.get("/{ticket_id}/messages", response_model=list[MessageOut])
async def list_messages(ticket_id: uuid.UUID, actor: CurrentActor, uow: Uow) -> list[MessageOut]:
    return await MessageService(uow, actor).for_ticket(ticket_id)


@router.post("/{ticket_id}/messages", response_model=MessageOut, status_code=201)
async def add_message(ticket_id: uuid.UUID, body: MessageCreate, actor: CurrentActor, uow: Uow) -> MessageOut:
    return await MessageService(uow, actor).add(ticket_id, body)
