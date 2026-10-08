"""WebSocket connections held by this API process, grouped by organisation."""

import asyncio
import contextlib
import json
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket
from redis.asyncio import Redis

from app.common.constants import EVENTS_CHANNEL
from app.core.config import get_settings
from app.core.logging import logger


@dataclass(eq=False)
class Connection:
    socket: WebSocket
    user_id: uuid.UUID


@dataclass
class Hub:
    by_org: dict[uuid.UUID, set[Connection]] = field(default_factory=dict)

    def add(self, org_id: uuid.UUID, connection: Connection) -> None:
        self.by_org.setdefault(org_id, set()).add(connection)

    def remove(self, org_id: uuid.UUID, connection: Connection) -> None:
        self.by_org.get(org_id, set()).discard(connection)

    async def deliver(self, raw: str) -> None:
        message = json.loads(raw)
        org_id = uuid.UUID(message["org_id"])
        target = message.get("user_id")
        payload = json.dumps({"event": message["event"], "data": message["data"]})
        for connection in list(self.by_org.get(org_id, ())):
            if target and str(connection.user_id) != target:
                continue
            with contextlib.suppress(Exception):  # a closed socket is removed by its own handler
                await connection.socket.send_text(payload)

    async def listen(self) -> None:
        """Forward every event published by any API task or worker to the sockets on this task."""
        # A dedicated connection: a subscribed connection cannot run other commands.
        client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(EVENTS_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.deliver(message["data"])
        except asyncio.CancelledError:
            await pubsub.unsubscribe(EVENTS_CHANNEL)
            await client.aclose()
            raise
        except Exception:
            logger.exception("event listener stopped")
            raise


hub = Hub()
