"""Sign-in, customer sign-up and refresh-token rotation."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.cache import rate_limit
from app.common.constants import LOGIN_RATE_LIMIT, REFRESH_TOKEN_TTL_DAYS
from app.common.enums import Role
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    TokenClaims,
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.db.unit_of_work import UnitOfWork
from app.modules.auth.schemas import LoginIn, RegisterIn
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.users.models import RefreshToken, User
from app.modules.users.repository import RefreshTokenRepository, UserRepository

# Same answer for "no such user" and "wrong password", so emails cannot be probed.
_BAD_LOGIN = "The email or password is not correct."


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    user: User
    organization: Organization


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.orgs = OrganizationRepository(uow.session)
        self.tokens = RefreshTokenRepository(uow.session)

    async def login(self, body: LoginIn, client_ip: str) -> IssuedSession:
        await rate_limit.hit("login", f"{client_ip}:{body.email.lower()}", LOGIN_RATE_LIMIT)
        org = await self.orgs.by_slug(body.organization.lower())
        user = await UserRepository(self.uow.session, org.id).by_email(body.email) if org else None
        if org is None or user is None or not user.is_active or not verify_password(body.password, user.password_hash):
            raise UnauthorizedError(_BAD_LOGIN)
        return await self._issue(user, org, family_id=uuid.uuid4())

    async def register_customer(self, body: RegisterIn) -> IssuedSession:
        org = await self.orgs.by_slug(body.organization.lower())
        if org is None:
            raise NotFoundError("This organisation does not exist.")
        users = UserRepository(self.uow.session, org.id)
        if await users.by_email(body.email):
            raise ConflictError("An account with this email already exists. Please sign in.")
        user = users.add(
            User(
                email=body.email.lower(),
                full_name=body.full_name,
                company=body.company,
                role=Role.CUSTOMER,
                password_hash=hash_password(body.password),
            )
        )
        await self.uow.session.flush()
        return await self._issue(user, org, family_id=uuid.uuid4())

    async def refresh(self, refresh_token: str | None) -> IssuedSession:
        """Rotate: the old token is revoked and a new one issued in the same family.
        Presenting a token that was already rotated means it leaked: revoke the whole family."""
        stored = await self.tokens.by_hash(hash_token(refresh_token)) if refresh_token else None
        if stored is None:
            raise UnauthorizedError()
        if stored.revoked_at is not None:
            await self.tokens.revoke_family(stored.family_id)
            await self.uow.commit()
            raise UnauthorizedError()
        if stored.expires_at <= datetime.now(UTC):
            raise UnauthorizedError()
        user = await self.tokens.user(stored.user_id)
        org = await self.orgs.by_id(user.org_id) if user else None
        if user is None or org is None or not user.is_active:
            raise UnauthorizedError()
        stored.revoked_at = datetime.now(UTC)
        return await self._issue(user, org, family_id=stored.family_id)

    async def logout(self, refresh_token: str | None) -> None:
        stored = await self.tokens.by_hash(hash_token(refresh_token)) if refresh_token else None
        if stored:
            await self.tokens.revoke_family(stored.family_id)
            await self.uow.commit()

    async def _issue(self, user: User, org: Organization, family_id: uuid.UUID) -> IssuedSession:
        token, token_hash = new_opaque_token()
        self.tokens.add(
            RefreshToken(
                user_id=user.id,
                family_id=family_id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
            )
        )
        await self.uow.commit()
        access = create_access_token(TokenClaims(user.id, org.id, user.role))
        return IssuedSession(access, token, user, org)
