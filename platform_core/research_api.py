from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import LLM
from app.tool.firecrawl_web_search import FirecrawlWebSearch
from platform_core.auth import get_current_user
from platform_core.database import get_db
from platform_core.model_router import resolve_profile
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


class ResearchSynthesisRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    results: list[dict] = Field(min_length=1, max_length=2)


class ResearchSynthesisResult(BaseModel):
    query: str
    provider: str = "deepseek-v4-pro-0813"
    synthesis: str
    input_results: int


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


@router.post("/v1/projects/{project_id}/research/synthesize", response_model=ResearchSynthesisResult)
async def synthesize_research(
    project_id: str,
    payload: ResearchSynthesisRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchSynthesisResult:
    await _require_project_member(session, project_id, user)

    compact_results = []
    for item in payload.results[:2]:
        compact_results.append(
            {
                "title": str(item.get("title") or "Untitled")[:300],
                "url": str(item.get("url") or "")[:1000],
                "description": str(item.get("description") or "")[:1000],
                "markdown": str(item.get("markdown") or "")[:3500],
            }
        )

    research_context = "\n\n".join(
        f"Reference {index + 1}:\n"
        f"Title: {item['title']}\n"
        f"URL: {item['url']}\n"
        f"Description: {item['description']}\n"
        f"Extracted content:\n{item['markdown']}"
        for index, item in enumerate(compact_results)
    )
    messages = [
        {
            "role": "user",
            "content": (
                "Summarize these two research references for the user's request. "
                "Return a concise professional synthesis with: (1) strongest shared UX patterns, "
                "(2) useful visual/design patterns, and (3) three practical recommendations for Cataron. "
                "Use only the supplied references; do not invent facts.\n\n"
                f"User request: {payload.query.strip()}\n\n{research_context}"
            ),
        }
    ]

    profile = resolve_profile("planner")
    llm = LLM(config_name=profile.config_name)
    try:
        synthesis = await llm.ask(
            messages,
            system_msgs=[
                {
                    "role": "system",
                    "content": "You are Cataron's planning/research analyst. Be concise, evidence-based, and practical.",
                }
            ],
            stream=False,
            temperature=0.2,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Planner synthesis failed: {exc}") from exc

    return ResearchSynthesisResult(
        query=payload.query.strip(),
        synthesis=synthesis,
        input_results=len(compact_results),
    )
