from redis.asyncio import Redis, from_url

from platform_core.settings import settings


def get_redis() -> Redis:
    return from_url(settings.redis_url, decode_responses=True)


async def enqueue_task(task_id: str) -> None:
    redis = get_redis()
    try:
        await redis.lpush(settings.queue_name, task_id)
    finally:
        await redis.aclose()
