import uuid

from sqlalchemy import select

from app.common.enums import STAFF_ROLES
from app.db.tenant import TenantRepository
from app.modules.teams.models import Team, TeamMember
from app.modules.users.models import User


class TeamRepository(TenantRepository[Team]):
    model = Team

    async def default(self) -> Team | None:
        return await self.first(self.scoped().where(Team.is_default.is_(True)))

    async def list_all(self) -> list[Team]:
        return list((await self.session.scalars(self.scoped().order_by(Team.name))).all())

    async def lock(self, team_id: uuid.UUID) -> Team | None:
        """Row lock so two workers never pick the same next agent."""
        return await self.first(self.scoped().where(Team.id == team_id).with_for_update())


class TeamMemberRepository(TenantRepository[TeamMember]):
    model = TeamMember

    async def active_agents(self, team_id: uuid.UUID) -> list[uuid.UUID]:
        query = (
            select(User.id)
            .join(TeamMember, TeamMember.user_id == User.id)
            .where(
                TeamMember.org_id == self.org_id,
                TeamMember.team_id == team_id,
                User.is_active.is_(True),
                User.role.in_(STAFF_ROLES),
            )
            .order_by(User.full_name, User.id)
        )
        return list((await self.session.scalars(query)).all())
