from collections.abc import AsyncIterator
from typing import Any

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

import app.db.models
from app.cache.redis import get_redis
from app.common.enums import Role
from app.db.base import Base
from app.db.session import engine
from app.jobs import queue
from app.main import app
from app.seed import seed_org
from app.worker import process

API = "/api/v1"
PASSWORD = "Demo@1234"


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    admin = await asyncpg.connect("postgresql://relay:relay@localhost:5442/relay")
    if not await admin.fetchval("select 1 from pg_database where datname = 'relay_test'"):
        await admin.execute("create database relay_test")
    await admin.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await get_redis().flushdb()
    await seed_org(
        "Acme Cloud",
        "acme",
        [
            ("lead@acme.demo", "Morgan Reyes", Role.OWNER),
            ("agent@acme.demo", "Priya Natarajan", Role.AGENT),
            ("sam@acme.demo", "Sam Okafor", Role.AGENT),
        ],
        customers=6,
        tickets=60,
    )
    await seed_org("Initech", "initech", [("lead@initech.demo", "Bill Lumbergh", Role.OWNER)], customers=2, tickets=3)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_rate_limits() -> None:
    redis = get_redis()
    keys = [k async for k in redis.scan_iter("relay:rl:*")]
    if keys:
        await redis.delete(*keys)


class Jobs:
    """Captures what the API sends to SQS; `run()` processes it like the worker would."""

    def __init__(self) -> None:
        self.bodies: list[str] = []

    async def send(self, body: str) -> None:
        self.bodies.append(body)

    async def run(self) -> int:
        count = 0
        while self.bodies:
            await process(self.bodies.pop(0))
            count += 1
        return count


@pytest.fixture
def jobs(monkeypatch: pytest.MonkeyPatch) -> Jobs:
    captured = Jobs()
    monkeypatch.setattr(queue, "_send", captured.send)
    return captured


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def login(client: AsyncClient, email: str, org: str = "acme") -> dict[str, str]:
    response = await client.post(f"{API}/auth/login", json={"organization": org, "email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def agent(client: AsyncClient) -> dict[str, str]:
    return await login(client, "agent@acme.demo")


@pytest.fixture
async def lead(client: AsyncClient) -> dict[str, str]:
    return await login(client, "lead@acme.demo")


@pytest.fixture
async def customer(client: AsyncClient) -> dict[str, str]:
    return await login(client, "customer@globex.demo")


@pytest.fixture
async def other_org(client: AsyncClient) -> dict[str, str]:
    return await login(client, "lead@initech.demo", org="initech")


def body(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()
