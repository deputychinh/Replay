"""Cache-aside helpers with JSON values."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.cache.redis import get_redis


async def cached(key: str, ttl_seconds: int, load: Callable[[], Awaitable[Any]]) -> Any:
    redis = get_redis()
    hit = await redis.get(key)
    if hit is not None:
        return json.loads(hit)
    value = await load()
    await redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    return value


async def invalidate(*keys: str) -> None:
    if keys:
        await get_redis().delete(*keys)
