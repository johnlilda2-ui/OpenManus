from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import ProjectQuota, Task, UsageRecord
from platform_core.settings import settings


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000.0) * settings.usage_input_rate_per_1k + (output_tokens / 1000.0) * settings.usage_output_rate_per_1k


async def get_or_create_quota(session: AsyncSession, project_id: str) -> ProjectQuota:
    quota = await session.scalar(select(ProjectQuota).where(ProjectQuota.project_id == project_id))
    if quota is not None:
        return quota
    quota = ProjectQuota(project_id=project_id)
    session.add(quota)
    await session.flush()
    return quota


def month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


async def current_usage(session: AsyncSession, project_id: str) -> dict[str, int]:
    start, end = month_bounds()
    token_total = await session.scalar(select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(UsageRecord.project_id == project_id, UsageRecord.created_at >= start, UsageRecord.created_at <= end))
    task_total = await session.scalar(select(func.count(Task.id)).where(Task.project_id == project_id, Task.created_at >= start, Task.created_at <= end))
    running_total = await session.scalar(select(func.count(Task.id)).where(Task.project_id == project_id, Task.status.in_(["queued", "running", "awaiting_approval"])))
    return {"tokens": int(token_total or 0), "tasks": int(task_total or 0), "concurrent": int(running_total or 0)}


async def check_quota(session: AsyncSession, project_id: str, prompt: str) -> tuple[bool, str, ProjectQuota]:
    quota = await get_or_create_quota(session, project_id)
    usage = await current_usage(session, project_id)
    estimated = estimate_tokens(prompt)
    if usage["tasks"] >= quota.monthly_task_limit:
        return False, "monthly task quota exceeded", quota
    if usage["concurrent"] >= quota.max_concurrent_tasks:
        return False, "maximum concurrent task limit reached", quota
    if usage["tokens"] + estimated >= quota.monthly_token_limit:
        return False, "monthly token quota exceeded", quota
    return True, "ok", quota


async def record_usage(
    session: AsyncSession,
    *,
    owner_id: str,
    project_id: str,
    task_id: str | None,
    input_text: str,
    output_text: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    usage_source: str = "estimated",
) -> UsageRecord:
    input_count = max(0, int(input_tokens if input_tokens is not None else estimate_tokens(input_text)))
    output_count = max(0, int(output_tokens if output_tokens is not None else estimate_tokens(output_text)))
    record = UsageRecord(
        owner_id=owner_id,
        project_id=project_id,
        task_id=task_id,
        input_tokens=input_count,
        output_tokens=output_count,
        total_tokens=input_count + output_count,
        usage_source=usage_source,
        estimated_cost_usd=estimate_cost(input_count, output_count),
    )
    session.add(record)
    await session.flush()
    return record
