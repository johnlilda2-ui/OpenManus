from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tool.firecrawl_web_search import FirecrawlWebSearch
from platform_core.auth import get_current_user
from platform_core.database import get_db
from platform_core.models import Project, User
from platform_core.permissions import PermissionDenied, require_project_role


router = APIRouter(tags=["research"])


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    country: str | None = Field(default=None, min_length=2, max_length=2)


class ResearchResult(BaseModel):
    query: str
    results: list[dict]
    provider: str = "firecrawl"


async def _require_project_member(
    session: AsyncSession,
    project_id: str,
    user: User,
) -> Project:
    project = await session.get(Project, project_id)
    try:
        return await require_project_role(session, project, user.id, "member")
    except PermissionDenied as exc:
        raise HTTPException(status_code=404 if project is None else 403, detail=str(exc)) from exc


@router.post("/v1/projects/{project_id}/research", response_model=ResearchResult)
async def research_only(
    project_id: str,
    payload: ResearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchResult:
    await _require_project_member(session, project_id, user)

    search = FirecrawlWebSearch()
    result = await search.execute(
        query=payload.query.strip(),
        num_results=2,
        lang="en",
        country=payload.country,
    )
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    return ResearchResult(query=result.query, results=result.results[:2])
