from fastapi import APIRouter

from app.common.enums import STAFF_ROLES
from app.common.schemas import ERROR_RESPONSES
from app.core.deps import ManagerActor, StaffActor, Uow
from app.core.errors import ConflictError, ValidationError
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import AgentIn, UserOut

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get("/staff", response_model=list[UserOut])
async def list_staff(actor: StaffActor, uow: Uow) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in await UserRepository(uow.session, actor.org_id).staff()]


@router.post("/staff", response_model=UserOut, status_code=201)
async def add_staff(body: AgentIn, actor: ManagerActor, uow: Uow) -> UserOut:
    if body.role not in STAFF_ROLES:
        raise ValidationError("Staff members must be owner, admin or agent.")
    repo = UserRepository(uow.session, actor.org_id)
    if await repo.by_email(body.email):
        raise ConflictError("Someone with this email is already in the organisation.")
    user = repo.add(
        User(email=body.email.lower(), full_name=body.full_name, role=body.role, password_hash=hash_password(body.password))
    )
    await uow.commit()
    return UserOut.model_validate(user)
