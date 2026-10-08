from app.common.enums import TicketPriority
from app.db.tenant import TenantRepository
from app.modules.sla_policies.models import SlaPolicy
from app.sla.policy import Targets

# Used when an organisation has no policy for a priority (business minutes).
FALLBACK_TARGETS: dict[TicketPriority, Targets] = {
    TicketPriority.URGENT: Targets(30, 240),
    TicketPriority.HIGH: Targets(60, 480),
    TicketPriority.NORMAL: Targets(240, 1440),
    TicketPriority.LOW: Targets(480, 2880),
}


class SlaPolicyRepository(TenantRepository[SlaPolicy]):
    model = SlaPolicy

    async def list_all(self) -> list[SlaPolicy]:
        return list((await self.session.scalars(self.scoped())).all())

    async def by_priority(self, priority: TicketPriority) -> SlaPolicy | None:
        return await self.first(self.scoped().where(SlaPolicy.priority == priority))

    async def targets(self, priority: TicketPriority) -> Targets:
        policy = await self.by_priority(priority)
        if policy is None:
            return FALLBACK_TARGETS[priority]
        return Targets(policy.first_response_minutes, policy.resolution_minutes)
