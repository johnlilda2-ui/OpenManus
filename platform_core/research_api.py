from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.config import LLMSettings
from app.llm import LLM
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


class ResearchSynthesisRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    results: list[dict] = Field(min_length=1, max_length=2)


class ResearchSynthesisResult(BaseModel):
    query: str
    provider: str = "deepseek/deepseek-v4-pro-0813"
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


def _research_planner_llm() -> LLM:
    """Build an isolated, non-escalating OpenRouter client for the research test."""
    api_key = (
        os.getenv("OPENMANUS_SECRET_OPENMANUS_LLM_API_KEY", "").strip()
        or os.getenv("OPENROUTER_API_KEY", "").strip()
        or os.getenv("OPENMANUS_LLM_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError("OpenRouter planner API key is not configured")

    model = os.getenv("OPENMANUS_MODEL_PLANNER", "deepseek/deepseek-v4-pro-0813").strip()
    if "/" not in model:
        model = f"deepseek/{model}"

    settings = LLMSettings(
        model=model,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=1600,
        temperature=0.2,
        api_type="openai",
        api_version="",
    )
    return LLM(
        config_name="__cataron_research_planner__",
        llm_config={"__cataron_research_planner__": settings, "default": settings},
    )


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
                "markdown": str(item.get("markdown") or "")[:2200],
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
                "Summarize these research references for the user's request. "
                "Return a concise professional synthesis with: (1) strongest shared UX patterns, "
                "(2) useful visual/design patterns, and (3) three practical recommendations for Cataron. "
                "Use only the supplied references; do not invent facts.\n\n"
                f"User request: {payload.query.strip()}\n\n{research_context}"
            ),
        }
    ]

    try:
        llm = _research_planner_llm()
        formatted_messages = llm.format_messages(
            [
                {
                    "role": "system",
                    "content": "You are Cataron's planning/research analyst. Be concise, evidence-based, and practical.",
                },
                *messages,
            ],
            supports_images=False,
        )
        input_tokens = llm.count_message_tokens(formatted_messages)
        if not llm.check_token_limit(input_tokens):
            raise RuntimeError(llm.get_limit_error_message(input_tokens))

        # DeepSeek V4 Pro supports reasoning, but this small synthesis task does not
        # need hidden reasoning. Disabling it prevents a short max_tokens budget from
        # being consumed entirely by reasoning tokens and leaving message.content empty.
        response = await llm.client.chat.completions.create(
            model=llm.model,
            messages=formatted_messages,
            max_tokens=llm.max_tokens,
            temperature=0.2,
            stream=False,
            extra_body={"reasoning": {"enabled": False}},
        )
        message = response.choices[0].message if response.choices else None
        synthesis = (getattr(message, "content", None) or "").strip() if message else ""
        if not synthesis:
            raise RuntimeError("Planner returned no synthesis text")

        usage = response.usage
        if usage:
            llm.update_token_count(usage.prompt_tokens, usage.completion_tokens)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Planner synthesis failed: {type(exc).__name__}: {exc}",
        ) from exc

    return ResearchSynthesisResult(
        query=payload.query.strip(),
        synthesis=synthesis,
        input_results=len(compact_results),
    )
