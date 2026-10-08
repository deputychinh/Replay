import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ExportStatus
from app.db.base import Base, IdMixin, TenantMixin, TimestampMixin, pg_enum


class Export(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "exports"

    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ExportStatus] = mapped_column(pg_enum(ExportStatus, "export_status"), default=ExportStatus.PENDING)
    s3_key: Mapped[str | None] = mapped_column(String(300))
    row_count: Mapped[int | None] = mapped_column(Integer)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
