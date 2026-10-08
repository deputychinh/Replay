"""Tenant isolation by construction (DS-03).

Every repository for a model with org_id subclasses TenantRepository; its
queries start from `self.scoped()`, which always filters by the caller's
organisation. A test checks that every tenant model has such a repository.
"""

import uuid
from typing import Any, ClassVar, cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.base import TenantMixin

TENANT_REPOSITORIES: dict[type, type] = {}


class TenantRepository[ModelT: TenantMixin]:
    model: ClassVar[type[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "model"):
            TENANT_REPOSITORIES[cls.model] = cls

    def __init__(self, session: AsyncSession, org_id: uuid.UUID) -> None:
        self.session = session
        self.org_id = org_id

    def scoped(self, *columns: Any) -> Select[Any]:
        query = select(*columns) if columns else select(self.model)
        return query.where(self.model.org_id == self.org_id)

    async def first(self, query: Select[Any]) -> ModelT | None:
        return cast("ModelT | None", await self.session.scalar(query))

    async def get(self, entity_id: uuid.UUID) -> ModelT:
        row = await self.first(self.scoped().where(self.model.id == entity_id))
        if row is None:
            raise NotFoundError()
        return row

    async def find(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.first(self.scoped().where(self.model.id == entity_id))

    def add(self, entity: ModelT) -> ModelT:
        entity.org_id = self.org_id
        self.session.add(entity)
        return entity
