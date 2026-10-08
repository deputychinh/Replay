"""Publish domain events to Redis. Every API task forwards them to its sockets (DS-06)."""

import json
import uuid
from typing import Any

from app.cache.redis import get_redis
from app.common.constants import EVENTS_CHANNEL
from app.common.enums import EventName


def event_message(org_id: uuid.UUID, name: EventName, data: dict[str, Any], user_id: uuid.UUID | None = None) -> str:
    """user_id limits the event to one person (e.g. a notification); otherwise all staff of the org get it."""
    return json.dumps(
        {"org_id": str(org_id), "user_id": str(user_id) if user_id else None, "event": name, "data": data}, default=str
    )


async def publish(org_id: uuid.UUID, name: EventName, data: dict[str, Any], user_id: uuid.UUID | None = None) -> None:
    await get_redis().publish(EVENTS_CHANNEL, event_message(org_id, name, data, user_id))
