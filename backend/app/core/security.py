"""Passwords, access tokens (JWT) and refresh tokens (opaque, stored hashed)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.common.constants import ACCESS_TOKEN_TTL_MINUTES
from app.common.enums import Role
from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: Role


def create_access_token(claims: TokenClaims) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(claims.user_id),
        "org": str(claims.org_id),
        "role": claims.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenClaims | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
        return TokenClaims(uuid.UUID(payload["sub"]), uuid.UUID(payload["org"]), Role(payload["role"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_opaque_token() -> tuple[str, str]:
    """A random token for the client and its sha256 hash for the database."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
