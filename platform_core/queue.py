from redis.asyncio import Redis, from_url

from platform_core.settings import settings


def get_redis() -> Redis:
    return from_url(settings.redis_url, decode_responses=True)


async def enqueue_item(item: str, queue_name: str | None = None) -> None:
    redis = get_redis()
    try:
        await redis.lpush(queue_name or settings.queue_name, item)
    finally:
        await redis.aclose()


async def enqueue_task(task_id: str) -> None:
    await enqueue_item(f"task:{task_id}")


async def enqueue_workflow(run_id: str) -> None:
    await enqueue_item(f"workflow:{run_id}")


async def enqueue_app_builder(run_id: str) -> None:
    await enqueue_item(f"builder:{run_id}", settings.builder_queue_name)
