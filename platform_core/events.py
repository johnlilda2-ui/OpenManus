from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import AuditEvent, TaskEvent, WorkflowEvent


async def add_task_event(session: AsyncSession, task_id: str, kind: str, payload: dict[str, Any] | None = None) -> TaskEvent:
    event = TaskEvent(task_id=task_id, kind=kind, payload=payload or {})
    session.add(event)
    await session.flush()
    return event


async def add_workflow_event(session: AsyncSession, workflow_run_id: str, kind: str, payload: dict[str, Any] | None = None) -> WorkflowEvent:
    event = WorkflowEvent(workflow_run_id=workflow_run_id, kind=kind, payload=payload or {})
    session.add(event)
    await session.flush()
    return event


async def add_audit_event(
    session: AsyncSession,
    action: str,
    *,
    actor_user_id: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        project_id=project_id,
        task_id=task_id,
        action=action,
        metadata_json=metadata or {},
    )
    session.add(event)
    await session.flush()
    return event
