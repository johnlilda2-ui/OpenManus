from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import ApprovalRequest


async def get_pending_approval(session: AsyncSession, *, task_id: str, tool_name: str) -> ApprovalRequest | None:
    return await session.scalar(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.task_id == task_id,
            ApprovalRequest.tool_name == tool_name,
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.requested_at.desc())
    )


async def get_pending_workflow_approval(
    session: AsyncSession, *, workflow_run_id: str, tool_name: str
) -> ApprovalRequest | None:
    return await session.scalar(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.workflow_run_id == workflow_run_id,
            ApprovalRequest.tool_name == tool_name,
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.requested_at.desc())
    )


async def create_or_get_approval(
    session: AsyncSession,
    *,
    task_id: str,
    project_id: str,
    tool_name: str,
    reason: str,
) -> ApprovalRequest:
    existing = await get_pending_approval(session, task_id=task_id, tool_name=tool_name)
    if existing is not None:
        return existing
    approval = ApprovalRequest(
        task_id=task_id,
        project_id=project_id,
        tool_name=tool_name,
        reason=reason,
        status="pending",
    )
    session.add(approval)
    await session.flush()
    return approval


async def create_or_get_workflow_approval(
    session: AsyncSession,
    *,
    workflow_run_id: str,
    project_id: str,
    tool_name: str,
    reason: str,
) -> ApprovalRequest:
    existing = await get_pending_workflow_approval(
        session, workflow_run_id=workflow_run_id, tool_name=tool_name
    )
    if existing is not None:
        return existing
    approval = ApprovalRequest(
        workflow_run_id=workflow_run_id,
        project_id=project_id,
        tool_name=tool_name,
        reason=reason,
        status="pending",
    )
    session.add(approval)
    await session.flush()
    return approval


async def decide_approval(
    session: AsyncSession,
    approval: ApprovalRequest,
    *,
    decided_by: str,
    approved: bool,
) -> ApprovalRequest:
    approval.status = "approved" if approved else "denied"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)
    await session.flush()
    return approval
