import uuid
from datetime import UTC, datetime

from sqlalchemy import func, update

from app.common.constants import PAGE_SIZE_DEFAULT
from app.db.tenant import TenantRepository
from app.modules.notifications.models import Notification


class NotificationRepository(TenantRepository[Notification]):
    model = Notification

    async def for_user(self, user_id: uuid.UUID, limit: int = PAGE_SIZE_DEFAULT) -> list[Notification]:
        query = self.scoped().where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit)
        return list((await self.session.scalars(query)).all())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        query = self.scoped(func.count()).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        return int(await self.session.scalar(query) or 0)

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Notification)
            .where(Notification.org_id == self.org_id, Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
