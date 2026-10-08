from httpx import AsyncClient

from app.common.constants import LOGIN_RATE_LIMIT, REFRESH_COOKIE_NAME
from tests.integration.conftest import API, PASSWORD


async def test_login_sets_refresh_cookie_and_me_works(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/auth/login", json={"organization": "acme", "email": "agent@acme.demo", "password": PASSWORD}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert REFRESH_COOKIE_NAME in cookie and "HttpOnly" in cookie and "Path=/api/v1/auth" in cookie
    me = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.json()["user"]["role"] == "agent"


async def test_wrong_password_and_unknown_user_look_the_same(client: AsyncClient) -> None:
    wrong = await client.post(f"{API}/auth/login", json={"organization": "acme", "email": "agent@acme.demo", "password": "nope"})
    unknown = await client.post(
        f"{API}/auth/login", json={"organization": "acme", "email": "ghost@acme.demo", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert wrong.json()["error"]["request_id"]


async def test_refresh_rotates_and_reuse_revokes_the_family(client: AsyncClient) -> None:
    login = await client.post(f"{API}/auth/login", json={"organization": "acme", "email": "sam@acme.demo", "password": PASSWORD})
    first = login.cookies[REFRESH_COOKIE_NAME]

    rotated = await client.post(f"{API}/auth/refresh", cookies={REFRESH_COOKIE_NAME: first})
    assert rotated.status_code == 200
    second = rotated.cookies[REFRESH_COOKIE_NAME]
    assert second != first

    # Someone replays the old token: refused, and the whole family is revoked.
    replay = await client.post(f"{API}/auth/refresh", cookies={REFRESH_COOKIE_NAME: first})
    assert replay.status_code == 401
    after = await client.post(f"{API}/auth/refresh", cookies={REFRESH_COOKIE_NAME: second})
    assert after.status_code == 401


async def test_login_is_rate_limited(client: AsyncClient) -> None:
    requests, _ = LOGIN_RATE_LIMIT
    payload = {"organization": "acme", "email": "rio@acme.demo", "password": "wrong"}
    for _ in range(requests):
        assert (await client.post(f"{API}/auth/login", json=payload)).status_code == 401
    blocked = await client.post(f"{API}/auth/login", json=payload)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


async def test_customer_self_sign_up(client: AsyncClient) -> None:
    payload = {"organization": "acme", "email": "new.person@hooli.demo", "full_name": "New Person", "password": "Longpass1"}
    created = await client.post(f"{API}/auth/register", json=payload)
    assert created.status_code == 201 and created.json()["user"]["role"] == "customer"
    again = await client.post(f"{API}/auth/register", json=payload)
    assert again.status_code == 409
