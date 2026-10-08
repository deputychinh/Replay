from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProcessedJob(Base):
    """Idempotency: a job whose key is here has already run (DS-05)."""

    __tablename__ = "processed_jobs"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
