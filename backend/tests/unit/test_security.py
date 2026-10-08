import uuid

from app.common.enums import Role
from app.core.security import (
    TokenClaims,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    stored = hash_password("Demo@1234")
    assert stored != "Demo@1234"
    assert verify_password("Demo@1234", stored)
    assert not verify_password("demo@1234", stored)


def test_access_token_round_trip_and_tampering() -> None:
    claims = TokenClaims(uuid.uuid4(), uuid.uuid4(), Role.AGENT)
    token = create_access_token(claims)
    assert decode_access_token(token) == claims
    assert decode_access_token(token[:-2] + "xx") is None
    assert decode_access_token("not-a-token") is None


def test_opaque_tokens_are_random_and_stored_hashed() -> None:
    first, first_hash = new_opaque_token()
    second, _ = new_opaque_token()
    assert first != second
    assert hash_token(first) == first_hash and first not in first_hash
