from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.auth import get_current_user
from platform_core.database import get_db
from platform_core.models import Project, TenantMember, User
from platform_core.permissions import PermissionDenied, project_role, require_project_role

router = APIRouter()


async def get_project(session: AsyncSession, project_id: str, user: User, minimum_role: str = "viewer") -> Project:
    project = await session.get(Project, project_id)
    try:
        return await require_project_role(session, project, user.id, minimum_role)
    except PermissionDenied as exc:
        raise HTTPException(status_code=404 if project is None else 403, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}/members")
async def list_members(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = await get_project(session, project_id, user, "viewer")
    if project.tenant_id is None:
        return [{"user_id": project.owner_id, "email": user.email, "role": "owner"}]
    rows = await session.scalars(select(TenantMember, User).join(User, User.id == TenantMember.user_id).where(TenantMember.tenant_id == project.tenant_id).order_by(TenantMember.role.desc(), User.email.asc()))
    result = []
    for member, member_user in rows.all():
        result.append({"user_id": member.user_id, "email": member_user.email, "role": member.role})
    return result


@router.post("/v1/projects/{project_id}/members")
async def add_member(project_id: str, payload: dict, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = await get_project(session, project_id, user, "admin")
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", "member")).lower()
    if not email or role not in {"admin", "member", "viewer"}:
        raise HTTPException(status_code=400, detail="Valid email and role are required")
    target = await session.scalar(select(User).where(User.email == email))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found; they must register first")
    if project.tenant_id is None:
        raise HTTPException(status_code=409, detail="Project predates tenant memberships; migrate and recreate membership")
    existing = await session.scalar(select(TenantMember).where(TenantMember.tenant_id == project.tenant_id, TenantMember.user_id == target.id))
    if existing is not None:
        existing.role = role
    else:
        session.add(TenantMember(tenant_id=project.tenant_id, user_id=target.id, role=role))
    await session.commit()
    return {"user_id": target.id, "email": target.email, "role": role}


@router.patch("/v1/projects/{project_id}/members/{user_id}")
async def change_member(project_id: str, user_id: str, payload: dict, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = await get_project(session, project_id, user, "admin")
    role = str(payload.get("role", "")).lower()
    if role not in {"admin", "member", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_id == project.owner_id:
        raise HTTPException(status_code=409, detail="Project owner role cannot be changed")
    membership = await session.scalar(select(TenantMember).where(TenantMember.tenant_id == project.tenant_id, TenantMember.user_id == user_id)) if project.tenant_id else None
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    current_role = await project_role(session, project, user.id)
    if current_role != "owner" and membership.role == "admin":
        raise HTTPException(status_code=403, detail="Only the owner can modify an admin")
    membership.role = role
    await session.commit()
    return {"user_id": user_id, "role": role}


@router.delete("/v1/projects/{project_id}/members/{user_id}")
async def remove_member(project_id: str, user_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    project = await get_project(session, project_id, user, "admin")
    if user_id == project.owner_id:
        raise HTTPException(status_code=409, detail="Project owner cannot be removed")
    membership = await session.scalar(select(TenantMember).where(TenantMember.tenant_id == project.tenant_id, TenantMember.user_id == user_id)) if project.tenant_id else None
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    current_role = await project_role(session, project, user.id)
    if current_role != "owner" and membership.role == "admin":
        raise HTTPException(status_code=403, detail="Only the owner can remove an admin")
    await session.delete(membership)
    await session.commit()
    return {"removed": True}
