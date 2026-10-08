from pydantic import EmailStr, Field

from app.common.constants import PASSWORD_MIN_LENGTH
from app.common.schemas import Schema
from app.modules.users.schemas import UserOut


class LoginIn(Schema):
    organization: str = Field(min_length=2, max_length=60, description="Organisation slug, e.g. acme")
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(Schema):
    """Customer self sign-up in the portal."""

    organization: str = Field(min_length=2, max_length=60)
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)


class SessionOut(Schema):
    access_token: str
    user: UserOut
    organization_slug: str
