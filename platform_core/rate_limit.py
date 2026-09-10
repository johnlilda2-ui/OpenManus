import hashlib
import time

from redis.asyncio import Redis

from platform_core.settings import settings


class RateLimitExceeded(PermissionError):
    def __init__(self, limit: int, retry_after: int):
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; retry after {retry_after} seconds")


async def check_rate_limit(redis: Redis, *, key: str, limit: int, window_seconds: int = 60) -> None:
    bucket = int(time.time() // window_seconds)
    redis_key = f"{settings.rate_limit_prefix}:{bucket}:{hashlib.sha256(key.encode()).hexdigest()}"
    count = await redis.incr(redis_key)
    if count == 1:
        await redis.expire(redis_key, window_seconds + 2)
    if count > limit:
        retry_after = window_seconds - (int(time.time()) % window_seconds)
        raise RateLimitExceeded(limit, max(1, retry_after))
