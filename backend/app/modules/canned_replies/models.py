from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TenantMixin, TimestampMixin


class CannedReply(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "canned_replies"

    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
