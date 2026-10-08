"""FastAPI dependencies: database unit of work and the calling user (actor)."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MANAGER_ROLES, STAFF_ROLES, Role
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.logging import org_id_var
from app.core.security import decode_access_token
from app.db.session import get_session
from app.db.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class Actor:
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: Role

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_manager(self) -> bool:
        return self.role in MANAGER_ROLES


async def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> AsyncIterator[UnitOfWork]:
    uow = UnitOfWork(session)
    try:
        yield uow
    except Exception:
        await uow.rollback()
        raise


def actor_from_token(token: str | None) -> Actor:
    claims = decode_access_token(token) if token else None
    if claims is None:
        raise UnauthorizedError()
    org_id_var.set(str(claims.org_id))
    return Actor(claims.user_id, claims.org_id, claims.role)


async def current_actor(authorization: Annotated[str | None, Header()] = None) -> Actor:
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    return actor_from_token(token)


async def staff_actor(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
    if not actor.is_staff:
        raise ForbiddenError()
    return actor


async def manager_actor(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
    if not actor.is_manager:
        raise ForbiddenError()
    return actor


Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentActor = Annotated[Actor, Depends(current_actor)]
StaffActor = Annotated[Actor, Depends(staff_actor)]
ManagerActor = Annotated[Actor, Depends(manager_actor)]
