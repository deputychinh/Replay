"""Integration tests run against real Postgres, Redis and LocalStack (docker compose up),
in a separate database `relay_test` that is rebuilt for each test session."""

import os

os.environ.setdefault("RELAY_ENV", "test")
os.environ["RELAY_DATABASE_URL"] = "postgresql+asyncpg://relay:relay@localhost:5442/relay_test"
os.environ["RELAY_REDIS_URL"] = "redis://localhost:6389/1"
