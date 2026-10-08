import uuid

from pydantic import EmailStr, Field

from app.common.constants import PASSWORD_MIN_LENGTH
from app.common.enums import Role
from app.common.schemas import Schema


class UserOut(Schema):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    company: str | None = None


class AgentIn(Schema):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    role: Role = Role.AGENT
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
