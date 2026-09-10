from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import Project, TenantMember

ROLE_ORDER = {"viewer": 10, "member": 20, "admin": 30, "owner": 40}


class PermissionDenied(PermissionError):
    pass


async def project_role(session: AsyncSession, project: Project, user_id: str) -> str | None:
    if project.owner_id == user_id:
        return "owner"
    if not project.tenant_id:
        return None
    membership = await session.scalar(
        select(TenantMember).where(
            TenantMember.tenant_id == project.tenant_id,
            TenantMember.user_id == user_id,
        )
    )
    return membership.role if membership else None


async def require_project_role(
    session: AsyncSession,
    project: Project | None,
    user_id: str,
    minimum_role: str = "viewer",
) -> Project:
    if project is None:
        raise PermissionDenied("Project not found")
    role = await project_role(session, project, user_id)
    if role is None or ROLE_ORDER.get(role, 0) < ROLE_ORDER[minimum_role]:
        raise PermissionDenied("Insufficient project permission")
    return project
