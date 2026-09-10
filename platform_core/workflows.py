from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import Workflow, WorkflowRun, WorkflowStepRun


TERMINAL_WORKFLOW_STATUSES = {"completed", "failed", "cancelled"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_steps(steps: list[dict]) -> list[dict]:
    if not steps:
        raise ValueError("Workflow must contain at least one step")
    normalized = []
    for index, step in enumerate(steps):
        name = str(step.get("name") or f"Step {index + 1}").strip()
        prompt = str(step.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"Workflow step {index} is missing prompt")
        normalized.append({"name": name[:200], "prompt": prompt[:50000]})
    return normalized


def render_step_prompt(template: str, *, input_text: str, previous_output: str, step_index: int) -> str:
    return (
        template.replace("{{input}}", input_text)
        .replace("{{previous_output}}", previous_output)
        .replace("{{step_index}}", str(step_index))
    )


async def recover_stale_runs(session: AsyncSession, *, stale_after_seconds: int = 900) -> list[str]:
    cutoff = utcnow() - timedelta(seconds=stale_after_seconds)
    result = await session.scalars(
        select(WorkflowRun).where(
            WorkflowRun.status == "running",
            WorkflowRun.heartbeat_at.is_not(None),
            WorkflowRun.heartbeat_at < cutoff,
        )
    )
    recovered: list[str] = []
    for run in result.all():
        run.status = "queued"
        recovered.append(run.id)
    return recovered


async def get_run_with_workflow(session: AsyncSession, run_id: str) -> tuple[WorkflowRun | None, Workflow | None]:
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        return None, None
    return run, await session.get(Workflow, run.workflow_id)


async def get_or_create_step_run(
    session: AsyncSession,
    *,
    run: WorkflowRun,
    step_index: int,
    step_name: str,
    prompt: str,
) -> WorkflowStepRun:
    result = await session.scalar(
        select(WorkflowStepRun).where(
            WorkflowStepRun.workflow_run_id == run.id,
            WorkflowStepRun.step_index == step_index,
        )
    )
    if result is not None:
        return result
    step = WorkflowStepRun(
        workflow_run_id=run.id,
        step_index=step_index,
        name=step_name,
        prompt=prompt,
    )
    session.add(step)
    await session.flush()
    return step
