"""Fixed-window rate limit in Redis, shared by every API task."""

import time

from app.cache import keys
from app.cache.redis import get_redis
from app.core.errors import RateLimitedError


async def hit(scope: str, identity: str, limit: tuple[int, int]) -> None:
    requests, window = limit
    window_start = int(time.time()) // window * window
    key = keys.rate_limit(scope, identity, window_start)
    redis = get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    if count > requests:
        raise RateLimitedError(retry_after=window_start + window - int(time.time()))
