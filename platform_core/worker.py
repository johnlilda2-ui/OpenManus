import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pydantic import Field
from redis.asyncio import Redis, from_url
from sqlalchemy import select, update

from app.agent.manus import Manus
from platform_core.database import SessionLocal, init_db
from platform_core.events import add_audit_event, add_task_event, add_workflow_event
from platform_core.memory import build_context, search_knowledge, search_memory
from platform_core.models import Conversation, MemoryEntry, Message, ProjectPolicy, Task, Workflow, WorkflowRun, WorkflowStepRun
from platform_core.policy import PolicyDenied, PolicyToolBroker, ToolPolicy
from platform_core.queue import enqueue_workflow
from platform_core.settings import settings
from platform_core.workflows import TERMINAL_WORKFLOW_STATUSES, get_or_create_step_run, render_step_prompt


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("openmanus-platform-worker")
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class PolicyManus(Manus):
    policy_broker: PolicyToolBroker = Field(default_factory=lambda: PolicyToolBroker(ToolPolicy.defaults()))

    async def execute_tool(self, command):
        self.policy_broker.authorize(command.function.name)
        return await super().execute_tool(command)


async def get_project_policy(session, project_id: str) -> ToolPolicy:
    policy = await session.scalar(select(ProjectPolicy).where(ProjectPolicy.project_id == project_id))
    return ToolPolicy.from_model(policy)


async def build_agent_prompt(session, *, owner_id: str, project_id: str, conversation_id: str | None, prompt: str, previous_output: str = "") -> str:
    recent_messages = []
    if conversation_id:
        result = await session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(12))
        recent_messages = list(reversed(result.all()))
    memories = await search_memory(session, owner_id=owner_id, project_id=project_id, query=prompt, limit=8)
    documents = await search_knowledge(session, owner_id=owner_id, project_id=project_id, query=prompt, limit=6)
    if previous_output:
        prompt = f"{prompt}\n\nPREVIOUS WORKFLOW STEP OUTPUT:\n{previous_output}"
    return build_context(prompt=prompt, recent_messages=recent_messages, memories=memories, documents=documents)


async def claim_queued_task(task_id: str | None = None) -> str | None:
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        if task_id:
            candidate_id = task_id
        else:
            candidate_id = await session.scalar(select(Task.id).where(Task.status == "queued").order_by(Task.created_at.asc()).limit(1))
            if candidate_id is None:
                return None
        result = await session.execute(update(Task).where(Task.id == candidate_id, Task.status == "queued", Task.cancel_requested.is_(False)).values(status="running", started_at=now))
        if result.rowcount != 1:
            task = await session.get(Task, candidate_id)
            if task is not None and task.status == "queued" and task.cancel_requested:
                task.status = "cancelled"
                task.completed_at = now
                await add_task_event(session, task.id, "task.cancelled", {"status": task.status})
                await session.commit()
            return None
        task = await session.get(Task, candidate_id)
        await add_task_event(session, task.id, "task.started", {"status": task.status})
        await add_audit_event(session, "task.started", actor_user_id=task.owner_id, project_id=task.project_id, task_id=task.id)
        await session.commit()
        return task.id


async def process_task(task_id: str) -> None:
    try:
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is None:
                return
            policy = await get_project_policy(session, task.project_id)
            prompt = await build_agent_prompt(session, owner_id=task.owner_id, project_id=task.project_id, conversation_id=task.conversation_id, prompt=task.prompt)
        agent = await PolicyManus.create(policy_broker=PolicyToolBroker(policy))
        result = await agent.run(prompt)
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is None:
                return
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            event_kind = "task.cancelled" if task.cancel_requested else "task.completed"
            task.status = "cancelled" if task.cancel_requested else "completed"
            if task.status == "completed":
                session.add(MemoryEntry(owner_id=task.owner_id, project_id=task.project_id, kind="task_result", key=f"task:{task.id}", content=result[:20000], importance=40, metadata_json={"task_id": task.id}))
                if task.conversation_id:
                    session.add(Message(conversation_id=task.conversation_id, task_id=task.id, role="assistant", content=result))
                    conversation = await session.get(Conversation, task.conversation_id)
                    if conversation is not None:
                        conversation.updated_at = datetime.now(timezone.utc)
            await add_task_event(session, task.id, event_kind, {"status": task.status, "result": result if task.status == "completed" else None})
            await add_audit_event(session, event_kind, actor_user_id=task.owner_id, project_id=task.project_id, task_id=task.id)
            await session.commit()
    except PolicyDenied as exc:
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is not None:
                task.status = "failed"
                task.error = str(exc)[:10000]
                task.completed_at = datetime.now(timezone.utc)
                await add_task_event(session, task.id, "policy.denied", {"status": task.status, "tool": exc.tool_name, "reason": exc.reason})
                await add_audit_event(session, "policy.tool_denied", actor_user_id=task.owner_id, project_id=task.project_id, task_id=task.id, metadata={"tool": exc.tool_name, "reason": exc.reason})
                await session.commit()
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        async with SessionLocal() as session:
            task = await session.get(Task, task_id)
            if task is not None:
                task.status = "failed"
                task.error = str(exc)[:10000]
                task.completed_at = datetime.now(timezone.utc)
                await add_task_event(session, task.id, "task.failed", {"status": task.status, "error": task.error})
                await add_audit_event(session, "task.failed", actor_user_id=task.owner_id, project_id=task.project_id, task_id=task.id)
                await session.commit()


async def claim_workflow_run(run_id: str | None = None) -> str | None:
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        if run_id:
            candidate_id = run_id
        else:
            candidate_id = await session.scalar(select(WorkflowRun.id).where(WorkflowRun.status == "queued").order_by(WorkflowRun.created_at.asc()).limit(1))
            if candidate_id is None:
                return None
        result = await session.execute(update(WorkflowRun).where(WorkflowRun.id == candidate_id, WorkflowRun.status == "queued", WorkflowRun.cancel_requested.is_(False)).values(status="running", started_at=now, heartbeat_at=now))
        if result.rowcount != 1:
            run = await session.get(WorkflowRun, candidate_id)
            if run is not None and run.status == "queued" and run.cancel_requested:
                run.status = "cancelled"
                run.completed_at = now
                await add_workflow_event(session, run.id, "workflow.cancelled", {"status": run.status})
                await session.commit()
            return None
        run = await session.get(WorkflowRun, candidate_id)
        await add_workflow_event(session, run.id, "workflow.started", {"status": run.status, "step": run.current_step})
        await session.commit()
        return run.id


async def process_workflow_run(run_id: str) -> None:
    try:
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is None or run.status in TERMINAL_WORKFLOW_STATUSES:
                return
            workflow = await session.get(Workflow, run.workflow_id)
            if workflow is None:
                raise RuntimeError("Workflow definition no longer exists")
            if run.cancel_requested:
                run.status = "cancelled"
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "workflow.cancelled", {"status": run.status})
                await session.commit()
                return
            steps = workflow.steps_json
            if run.current_step >= len(steps):
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "workflow.completed", {"status": run.status, "output": run.output or ""})
                await session.commit()
                return
            spec = steps[run.current_step]
            step = await get_or_create_step_run(session, run=run, step_index=run.current_step, step_name=spec["name"], prompt=spec["prompt"])
            step.status = "running"
            step.attempt += 1
            step.started_at = datetime.now(timezone.utc)
            run.heartbeat_at = datetime.now(timezone.utc)
            policy = await get_project_policy(session, run.project_id)
            rendered = render_step_prompt(spec["prompt"], input_text=run.input, previous_output=run.output or "", step_index=run.current_step)
            enriched = await build_agent_prompt(session, owner_id=run.owner_id, project_id=run.project_id, conversation_id=None, prompt=rendered)
            await add_workflow_event(session, run.id, "workflow.step_started", {"step_index": run.current_step, "name": spec["name"], "attempt": step.attempt})
            await session.commit()

        agent = await PolicyManus.create(policy_broker=PolicyToolBroker(policy))
        result = await agent.run(enriched)

        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is None:
                return
            step = await session.scalar(select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run.id, WorkflowStepRun.step_index == run.current_step))
            if step is not None:
                step.status = "completed"
                step.result = result[:50000]
                step.completed_at = datetime.now(timezone.utc)
            run.output = result
            run.current_step += 1
            run.heartbeat_at = datetime.now(timezone.utc)
            total_steps = len((await session.get(Workflow, run.workflow_id)).steps_json)
            await add_workflow_event(session, run.id, "workflow.step_completed", {"step_index": run.current_step - 1, "next_step": run.current_step, "result": result[:10000]})
            if run.cancel_requested:
                run.status = "cancelled"
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "workflow.cancelled", {"status": run.status})
            elif run.current_step >= total_steps:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "workflow.completed", {"status": run.status, "output": result[:10000]})
                await add_audit_event(session, "workflow.completed", actor_user_id=run.owner_id, project_id=run.project_id, metadata={"workflow_id": run.workflow_id, "run_id": run.id})
            else:
                run.status = "queued"
                await add_workflow_event(session, run.id, "workflow.queued_next", {"status": run.status, "step": run.current_step})
            session.add(MemoryEntry(owner_id=run.owner_id, project_id=run.project_id, kind="workflow_step", key=f"{run.workflow_id}:{run.current_step - 1}", content=result[:20000], importance=35, metadata_json={"workflow_run_id": run.id, "step_index": run.current_step - 1}))
            await session.commit()
            next_status = run.status
        if next_status == "queued":
            try:
                await enqueue_workflow(run_id)
            except Exception:
                logger.exception("Could not requeue workflow %s; recovery sweep will handle it", run_id)
    except PolicyDenied as exc:
        logger.error("Policy denied workflow %s: %s", run_id, exc)
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is not None:
                run.status = "failed"
                run.error = str(exc)[:10000]
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "policy.denied", {"status": run.status, "tool": exc.tool_name, "reason": exc.reason})
                await add_audit_event(session, "policy.tool_denied", actor_user_id=run.owner_id, project_id=run.project_id, metadata={"tool": exc.tool_name, "reason": exc.reason, "run_id": run.id})
                await session.commit()
    except Exception as exc:
        logger.exception("Workflow run %s failed", run_id)
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is not None:
                run.status = "failed"
                run.error = str(exc)[:10000]
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "workflow.failed", {"status": run.status, "error": run.error})
                await add_audit_event(session, "workflow.failed", actor_user_id=run.owner_id, project_id=run.project_id, metadata={"workflow_id": run.workflow_id, "run_id": run.id})
                await session.commit()


async def recover_stale_workflows() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.workflow_stale_seconds)
    async with SessionLocal() as session:
        result = await session.scalars(select(WorkflowRun).where(WorkflowRun.status == "running", WorkflowRun.heartbeat_at.is_not(None), WorkflowRun.heartbeat_at < cutoff))
        recovered = []
        for run in result.all():
            run.status = "queued"
            recovered.append(run.id)
            await add_workflow_event(session, run.id, "workflow.recovered", {"status": "queued", "reason": "stale heartbeat"})
        await session.commit()
    for run_id in recovered:
        try:
            await enqueue_workflow(run_id)
        except Exception:
            logger.exception("Failed to enqueue recovered workflow %s", run_id)


async def worker_loop() -> None:
    await init_db()
    redis: Redis = from_url(settings.redis_url, decode_responses=True)
    logger.info("OpenManus worker listening on %s", settings.queue_name)
    last_recovery = datetime.min.replace(tzinfo=timezone.utc)
    try:
        while True:
            now = datetime.now(timezone.utc)
            if (now - last_recovery).total_seconds() >= 30:
                await recover_stale_workflows()
                last_recovery = now
            item = await redis.brpop(settings.queue_name, timeout=5)
            selected_item = item[1] if item else None
            if selected_item:
                if selected_item.startswith("workflow:"):
                    claimed = await claim_workflow_run(selected_item.split(":", 1)[1])
                    if claimed:
                        await process_workflow_run(claimed)
                else:
                    task_id = selected_item.split(":", 1)[1] if selected_item.startswith("task:") else selected_item
                    claimed = await claim_queued_task(task_id)
                    if claimed:
                        await process_task(claimed)
                continue
            task_id = await claim_queued_task()
            if task_id:
                await process_task(task_id)
                continue
            workflow_id = await claim_workflow_run()
            if workflow_id:
                await process_workflow_run(workflow_id)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(worker_loop())
