import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import STAFF_ROLES, Role
from app.db.tenant import TenantRepository
from app.modules.users.models import RefreshToken, User


class UserRepository(TenantRepository[User]):
    model = User

    async def by_email(self, email: str) -> User | None:
        return await self.first(self.scoped().where(User.email == email.lower()))

    async def staff(self) -> list[User]:
        query = self.scoped().where(User.role.in_(STAFF_ROLES), User.is_active.is_(True)).order_by(User.full_name)
        return list((await self.session.scalars(query)).all())

    async def by_ids(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
        if not ids:
            return {}
        rows = await self.session.scalars(self.scoped().where(User.id.in_(ids)))
        return {user.id: user for user in rows}

    async def managers(self) -> list[User]:
        return [user for user in await self.staff() if user.role in {Role.OWNER, Role.ADMIN}]


class RefreshTokenRepository:
    """Refresh tokens belong to a user; the user's org was already checked at sign-in."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def user(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)
