from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.approvals import decide_approval
from platform_core.artifacts import storage
from platform_core.auth import get_current_user
from platform_core.database import get_db
from platform_core.events import add_audit_event, add_task_event
from platform_core.models import ApprovalRequest, Artifact, KnowledgeDocument, MemoryEntry, Project, ProjectPolicy, ProjectQuota, Task, User
from platform_core.queue import enqueue_task
from platform_core.schemas import ApprovalResponse, ArtifactResponse, KnowledgeCreate, KnowledgeResponse, MemoryCreate, MemoryResponse, ProjectPolicyResponse, ProjectPolicyUpdate, ProjectQuotaResponse, ProjectQuotaUpdate, UsageSummaryResponse
from platform_core.usage import check_quota, current_usage, get_or_create_quota


router = APIRouter()
UI_FILE = Path(__file__).with_name("static") / "index.html"


def owned_project(project: Project | None, user: User) -> Project:
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/", include_in_schema=False)
async def platform_console():
    return FileResponse(UI_FILE)


@router.get("/v1/projects/{project_id}/policy", response_model=ProjectPolicyResponse)
async def get_policy(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    policy = await session.scalar(select(ProjectPolicy).where(ProjectPolicy.project_id == project.id))
    if policy is None:
        policy = ProjectPolicy(project_id=project.id)
        session.add(policy)
        await session.flush()
        await session.commit()
    return ProjectPolicyResponse.model_validate(policy)


@router.put("/v1/projects/{project_id}/policy", response_model=ProjectPolicyResponse)
async def update_policy(project_id: str, payload: ProjectPolicyUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    policy = await session.scalar(select(ProjectPolicy).where(ProjectPolicy.project_id == project.id))
    if policy is None:
        policy = ProjectPolicy(project_id=project.id)
        session.add(policy)
    policy.allowed_tool_patterns = payload.allowed_tool_patterns
    policy.denied_tool_patterns = payload.denied_tool_patterns
    policy.approval_required_patterns = payload.approval_required_patterns
    policy.version += 1
    await add_audit_event(session, "policy.updated", actor_user_id=user.id, project_id=project.id, metadata={"version": policy.version})
    await session.commit()
    return ProjectPolicyResponse.model_validate(policy)


@router.get("/v1/projects/{project_id}/approvals", response_model=list[ApprovalResponse])
async def list_approvals(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    rows = await session.scalars(select(ApprovalRequest).where(ApprovalRequest.project_id == project.id).order_by(ApprovalRequest.requested_at.desc()).limit(100))
    return [ApprovalResponse.model_validate(row) for row in rows.all()]


async def decide_approval_request(approval_id: str, approved: bool, user: User, session: AsyncSession) -> ApprovalResponse:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None or approval.project_id is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    project = owned_project(await session.get(Project, approval.project_id), user)
    if approval.status != "pending":
        return ApprovalResponse.model_validate(approval)
    await decide_approval(session, approval, decided_by=user.id, approved=approved)
    task = await session.get(Task, approval.task_id)
    if task is not None:
        if approved:
            task.status = "queued"
            await add_task_event(session, task.id, "approval.granted", {"approval_id": approval.id, "tool": approval.tool_name, "status": task.status})
        else:
            task.status = "failed"
            task.error = f"Tool approval denied: {approval.tool_name}"
            task.completed_at = datetime.now(timezone.utc)
            await add_task_event(session, task.id, "approval.denied", {"approval_id": approval.id, "tool": approval.tool_name, "status": task.status})
        await add_audit_event(session, "approval.decided", actor_user_id=user.id, project_id=project.id, task_id=task.id, metadata={"approval_id": approval.id, "approved": approved, "tool": approval.tool_name})
    await session.commit()
    if approved and task is not None:
        try:
            await enqueue_task(task.id)
        except Exception:
            # The durable database state remains queued; worker recovery can enqueue it later.
            pass
    return ApprovalResponse.model_validate(approval)


@router.post("/v1/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(approval_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await decide_approval_request(approval_id, True, user, session)


@router.post("/v1/approvals/{approval_id}/deny", response_model=ApprovalResponse)
async def deny(approval_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await decide_approval_request(approval_id, False, user, session)


@router.get("/v1/projects/{project_id}/quota", response_model=ProjectQuotaResponse)
async def get_quota(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    quota = await get_or_create_quota(session, project.id)
    await session.commit()
    return ProjectQuotaResponse.model_validate(quota)


@router.put("/v1/projects/{project_id}/quota", response_model=ProjectQuotaResponse)
async def update_quota(project_id: str, payload: ProjectQuotaUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    quota = await get_or_create_quota(session, project.id)
    quota.monthly_token_limit = payload.monthly_token_limit
    quota.monthly_task_limit = payload.monthly_task_limit
    quota.max_concurrent_tasks = payload.max_concurrent_tasks
    quota.hard_block = payload.hard_block
    await add_audit_event(session, "quota.updated", actor_user_id=user.id, project_id=project.id)
    await session.commit()
    return ProjectQuotaResponse.model_validate(quota)


@router.get("/v1/projects/{project_id}/usage", response_model=UsageSummaryResponse)
async def get_usage(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    usage = await current_usage(session, project.id)
    return UsageSummaryResponse(project_id=project.id, **usage)


@router.post("/v1/projects/{project_id}/memory", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(project_id: str, payload: MemoryCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    memory = MemoryEntry(owner_id=user.id, project_id=project.id, kind=payload.kind, key=payload.key, content=payload.content, importance=payload.importance, metadata_json=payload.metadata_json)
    session.add(memory)
    await session.commit()
    return MemoryResponse.model_validate(memory)


@router.get("/v1/projects/{project_id}/memory", response_model=list[MemoryResponse])
async def list_memory(project_id: str, query: str = "", user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    rows = await session.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == user.id, (MemoryEntry.project_id == project.id) | (MemoryEntry.project_id.is_(None))).order_by(MemoryEntry.updated_at.desc()).limit(100))
    return [MemoryResponse.model_validate(row) for row in rows.all()]


@router.post("/v1/projects/{project_id}/knowledge", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(project_id: str, payload: KnowledgeCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    document = KnowledgeDocument(owner_id=user.id, project_id=project.id, title=payload.title, content=payload.content, source=payload.source, metadata_json=payload.metadata_json)
    session.add(document)
    await session.commit()
    return KnowledgeResponse.model_validate(document)


@router.get("/v1/projects/{project_id}/knowledge", response_model=list[KnowledgeResponse])
async def list_knowledge(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    rows = await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.owner_id == user.id, KnowledgeDocument.project_id == project.id).order_by(KnowledgeDocument.updated_at.desc()).limit(100))
    return [KnowledgeResponse.model_validate(row) for row in rows.all()]


@router.post("/v1/projects/{project_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_artifact(project_id: str, file: UploadFile = File(...), task_id: str | None = None, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    if task_id is not None:
        task = await session.get(Task, task_id)
        if task is None or task.owner_id != user.id or task.project_id != project.id:
            raise HTTPException(status_code=404, detail="Task not found")
    safe_name = Path(file.filename or "artifact.bin").name
    artifact_id = __import__("uuid").uuid4().hex
    storage_key = f"{project.id}/{artifact_id}/{safe_name}"
    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as temp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 50 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Artifact exceeds 50 MB limit")
            temp.write(chunk)
        temp.seek(0)
        stored_size = storage.put(storage_key, temp)
    artifact = Artifact(id=artifact_id, owner_id=user.id, project_id=project.id, task_id=task_id, filename=safe_name, content_type=file.content_type or "application/octet-stream", storage_key=storage_key, size_bytes=stored_size or size)
    session.add(artifact)
    await add_audit_event(session, "artifact.created", actor_user_id=user.id, project_id=project.id, task_id=task_id, metadata={"artifact_id": artifact.id, "size": artifact.size_bytes})
    await session.commit()
    url = storage.presigned_url(artifact.storage_key) or f"/v1/artifacts/{artifact.id}"
    return ArtifactResponse(id=artifact.id, project_id=artifact.project_id, task_id=artifact.task_id, filename=artifact.filename, content_type=artifact.content_type, size_bytes=artifact.size_bytes, created_at=artifact.created_at, download_url=url)


@router.get("/v1/projects/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = owned_project(await session.get(Project, project_id), user)
    rows = await session.scalars(select(Artifact).where(Artifact.project_id == project.id, Artifact.owner_id == user.id).order_by(Artifact.created_at.desc()).limit(100))
    result = []
    for artifact in rows.all():
        url = storage.presigned_url(artifact.storage_key) or f"/v1/artifacts/{artifact.id}"
        result.append(ArtifactResponse(id=artifact.id, project_id=artifact.project_id, task_id=artifact.task_id, filename=artifact.filename, content_type=artifact.content_type, size_bytes=artifact.size_bytes, created_at=artifact.created_at, download_url=url))
    return result


@router.get("/v1/artifacts/{artifact_id}")
async def download_artifact(artifact_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    artifact = await session.get(Artifact, artifact_id)
    if artifact is None or artifact.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    signed = storage.presigned_url(artifact.storage_key)
    if signed:
        return JSONResponse({"download_url": signed})
    handle = storage.open(artifact.storage_key)
    if handle is None:
        raise HTTPException(status_code=404, detail="Artifact data unavailable")
    return FileResponse(handle.name, media_type=artifact.content_type, filename=artifact.filename)
