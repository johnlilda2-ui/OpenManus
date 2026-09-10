import asyncio
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis, from_url
from sqlalchemy import select

from app.agent.manus import Manus
from platform_core.database import SessionLocal, init_db
from platform_core.events import add_audit_event, add_task_event
from platform_core.models import Conversation, Message, Task
from platform_core.settings import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("openmanus-platform-worker")
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


async def claim_queued_task(task_id: str | None = None) -> str | None:
    async with SessionLocal() as session:
        if task_id:
            task = await session.get(Task, task_id)
        else:
            task = await session.scalar(
                select(Task).where(Task.status == "queued").order_by(Task.created_at.asc()).limit(1)
            )

        if task is None or task.status in TERMINAL_STATUSES:
            return None
        if task.cancel_requested:
            task.status = "cancelled"
            task.completed_at = datetime.now(timezone.utc)
            await add_task_event(session, task.id, "task.cancelled", {"status": task.status})
            await session.commit()
            return None

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await add_task_event(session, task.id, "task.started", {"status": task.status})
        await add_audit_event(
            session,
            "task.started",
            actor_user_id=task.owner_id,
            project_id=task.project_id,
            task_id=task.id,
        )
        await session.commit()
        return task.id


async def process_task(task_id: str) -> None:
    logger.info("Starting OpenManus task %s", task_id)

    try:
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is None:
                return
            prompt = task.prompt

        agent = await Manus.create()
        result = await agent.run(prompt)

        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is None:
                return

            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            if task.cancel_requested:
                task.status = "cancelled"
                event_kind = "task.cancelled"
            else:
                task.status = "completed"
                event_kind = "task.completed"

            if task.conversation_id and task.status == "completed":
                session.add(
                    Message(
                        conversation_id=task.conversation_id,
                        task_id=task.id,
                        role="assistant",
                        content=result,
                    )
                )
                conversation = await session.get(Conversation, task.conversation_id)
                if conversation is not None:
                    conversation.updated_at = datetime.now(timezone.utc)

            await add_task_event(
                session,
                task.id,
                event_kind,
                {
                    "status": task.status,
                    "result": result if task.status == "completed" else None,
                },
            )
            await add_audit_event(
                session,
                event_kind,
                actor_user_id=task.owner_id,
                project_id=task.project_id,
                task_id=task.id,
            )
            await session.commit()

        logger.info("Finished task %s", task_id)
    except Exception as exc:
        logger.exception("OpenManus task %s failed", task_id)
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is not None:
                task.status = "failed"
                task.error = str(exc)[:10000]
                task.completed_at = datetime.now(timezone.utc)
                await add_task_event(
                    session,
                    task.id,
                    "task.failed",
                    {"status": task.status, "error": task.error},
                )
                await add_audit_event(
                    session,
                    "task.failed",
                    actor_user_id=task.owner_id,
                    project_id=task.project_id,
                    task_id=task.id,
                )
                await session.commit()


async def worker_loop() -> None:
    await init_db()
    redis: Redis = from_url(settings.redis_url, decode_responses=True)
    logger.info("OpenManus worker listening on %s", settings.queue_name)
    try:
        while True:
            item = await redis.brpop(settings.queue_name, timeout=5)
            selected_task_id = item[1] if item else None
            claimed_id = await claim_queued_task(selected_task_id)
            if claimed_id is None:
                # Recovery sweep: the database is the durable source of truth,
                # so tasks committed while Redis was unavailable are still picked up.
                continue
            await process_task(claimed_id)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(worker_loop())
