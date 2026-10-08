import uuid

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import MessageKind
from app.db.base import Base, IdMixin, TenantMixin, TimestampMixin, pg_enum


class Message(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_ticket_created", "ticket_id", "created_at"),)

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    kind: Mapped[MessageKind] = mapped_column(pg_enum(MessageKind, "message_kind"))
    body: Mapped[str] = mapped_column(Text)
