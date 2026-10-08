"""App factory: routers, middleware, error envelope, WebSocket, health checks."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.cache.redis import get_redis
from app.common.constants import API_PREFIX
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import SessionFactory, engine
from app.modules.attachments.router import router as attachments
from app.modules.auth.router import router as auth
from app.modules.canned_replies.router import router as canned_replies
from app.modules.notifications.router import router as notifications
from app.modules.organizations.router import router as organization
from app.modules.reports.router import router as reports
from app.modules.sla_policies.router import router as sla_policies
from app.modules.tickets.router import router as tickets
from app.modules.users.router import router as users
from app.realtime.gateway import router as realtime
from app.realtime.hub import hub


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    listener = asyncio.create_task(hub.listen())
    yield
    listener.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await listener
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="Relay API",
        version="1.0.0",
        lifespan=lifespan,
        description="Customer support & SLA platform. Errors use one envelope: "
        "`{ error: { code, message, details, request_id } }`.",
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_error_handlers(app)

    for router in (auth, organization, users, tickets, attachments, sla_policies, canned_replies, notifications, reports):
        app.include_router(router, prefix=API_PREFIX)
    app.include_router(realtime, prefix=API_PREFIX)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness: the process answers."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    @app.get(f"{API_PREFIX}/ready", tags=["ops"], include_in_schema=False)  # same check through CloudFront (/api/*)
    async def ready() -> dict[str, bool]:
        """Readiness: database and Redis reachable (the load balancer uses this)."""
        async with SessionFactory() as session:
            db = (await session.execute(text("select 1"))).scalar() == 1
        cache = bool(await get_redis().ping())
        return {"db": db, "redis": cache}

    return app


app = create_app()
