from fastapi import APIRouter
from pydantic import Field

from app.common.enums import TicketPriority
from app.common.schemas import ERROR_RESPONSES, Schema
from app.core.deps import ManagerActor, StaffActor, Uow
from app.modules.sla_policies.models import SlaPolicy
from app.modules.sla_policies.repository import FALLBACK_TARGETS, SlaPolicyRepository

router = APIRouter(prefix="/sla-policies", tags=["sla"], responses=ERROR_RESPONSES)

WEEK_MINUTES = 7 * 24 * 60


class SlaPolicyIn(Schema):
    first_response_minutes: int = Field(ge=5, le=WEEK_MINUTES)
    resolution_minutes: int = Field(ge=15, le=4 * WEEK_MINUTES)


class SlaPolicyOut(SlaPolicyIn):
    priority: TicketPriority


@router.get("", response_model=list[SlaPolicyOut])
async def list_policies(actor: StaffActor, uow: Uow) -> list[SlaPolicyOut]:
    stored = {p.priority: p for p in await SlaPolicyRepository(uow.session, actor.org_id).list_all()}
    result = []
    for priority in TicketPriority:
        policy = stored.get(priority)
        targets = FALLBACK_TARGETS[priority]
        result.append(
            SlaPolicyOut(
                priority=priority,
                first_response_minutes=policy.first_response_minutes if policy else targets.first_response_minutes,
                resolution_minutes=policy.resolution_minutes if policy else targets.resolution_minutes,
            )
        )
    return result


@router.put("/{priority}", response_model=SlaPolicyOut)
async def set_policy(priority: TicketPriority, body: SlaPolicyIn, actor: ManagerActor, uow: Uow) -> SlaPolicyOut:
    """Applies to tickets created (or re-prioritised) from now on."""
    repo = SlaPolicyRepository(uow.session, actor.org_id)
    policy = await repo.by_priority(priority) or repo.add(SlaPolicy(priority=priority))
    policy.first_response_minutes = body.first_response_minutes
    policy.resolution_minutes = body.resolution_minutes
    await uow.commit()
    return SlaPolicyOut(priority=priority, **body.model_dump())
