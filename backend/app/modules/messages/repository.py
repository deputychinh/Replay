import uuid

from app.common.enums import MessageKind
from app.db.tenant import TenantRepository
from app.modules.messages.models import Message


class MessageRepository(TenantRepository[Message]):
    model = Message

    async def for_ticket(self, ticket_id: uuid.UUID, include_internal: bool) -> list[Message]:
        query = self.scoped().where(Message.ticket_id == ticket_id)
        if not include_internal:
            query = query.where(Message.kind == MessageKind.PUBLIC_REPLY)
        return list((await self.session.scalars(query.order_by(Message.created_at))).all())
