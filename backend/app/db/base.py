import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    # Fetch server-generated values (defaults, onupdate, computed columns) with RETURNING,
    # so reading them after a flush never triggers lazy I/O in async code.
    __mapper_args__ = {"eager_defaults": True}


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TenantMixin:
    """Every row that belongs to an organisation. Only TenantRepository may query these."""

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)


def pg_enum(enum_cls: type, name: str) -> Enum:
    """Store a StrEnum by its value, as a Postgres enum type with this name."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
