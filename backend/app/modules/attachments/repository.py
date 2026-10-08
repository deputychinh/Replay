import uuid

from sqlalchemy import update

from app.db.tenant import TenantRepository
from app.modules.attachments.models import Attachment


class AttachmentRepository(TenantRepository[Attachment]):
    model = Attachment

    async def link(self, ids: list[uuid.UUID], ticket_id: uuid.UUID, message_id: uuid.UUID, uploaded_by: uuid.UUID) -> None:
        """Attach the caller's own, still unlinked uploads to a message."""
        if not ids:
            return
        await self.session.execute(
            update(Attachment)
            .where(
                Attachment.org_id == self.org_id,
                Attachment.id.in_(ids),
                Attachment.uploaded_by == uploaded_by,
                Attachment.message_id.is_(None),
            )
            .values(ticket_id=ticket_id, message_id=message_id)
        )

    async def for_messages(self, message_ids: list[uuid.UUID]) -> list[Attachment]:
        if not message_ids:
            return []
        return list((await self.session.scalars(self.scoped().where(Attachment.message_id.in_(message_ids)))).all())
