from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.auth import get_current_user
from platform_core.database import get_db
from platform_core.events import add_audit_event, add_workflow_event
from platform_core.models import Project, ProjectPolicy, User, Workflow, WorkflowRun, WorkflowStepRun
from platform_core.permissions import PermissionDenied, require_project_role
from platform_core.queue import enqueue_app_builder
from platform_core.schemas import WebsiteExperienceResponse, WebsiteIterationCreate, WebsiteSectionResponse, VisualScoreResponse
from platform_core.usage import check_quota
from platform_core.website_iteration import build_website_section_iteration_steps
from platform_core.website_manifest import extract_visual_score, extract_website_manifests
from platform_core.workflows import normalize_steps
from platform_core.website_models import WebsiteIteration


def _is_website_workflow(workflow: Workflow | None) -> bool:
    if workflow is None or not workflow.steps_json:
        return False
    first_name = str(workflow.steps_json[0].get("name", "")).lower()
    return "website strategy" in first_name or "section iteration" in first_name


async def _access(session: AsyncSession, project_id: str, user: User, minimum_role: str) -> Project:
    project = await session.get(Project, project_id)
    try:
        return await require_project_role(session, project, user.id, minimum_role)
    except PermissionDenied as exc:
        raise HTTPException(status_code=404 if project is None else 403, detail=str(exc)) from exc


async def _run_and_steps(session: AsyncSession, run_id: str, user: User) -> tuple[WorkflowRun, Workflow, list[WorkflowStepRun]]:
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Builder run not found")
    await _access(session, run.project_id, user, "viewer")
    workflow = await session.get(Workflow, run.workflow_id)
    if not _is_website_workflow(workflow):
        raise HTTPException(status_code=409, detail="Run is not a Website Builder run")
    rows = await session.scalars(
        select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run.id).order_by(WorkflowStepRun.step_index.asc())
    )
    return run, workflow, rows.all()


def _step_results(steps: list[WorkflowStepRun]) -> list[str]:
    return [step.result or "" for step in steps if step.result]


def register(router) -> None:
    @router.get("/v1/app-builder/runs/{run_id}/website-experience", response_model=WebsiteExperienceResponse)
    async def website_experience(
        run_id: str,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> WebsiteExperienceResponse:
        run, _, steps = await _run_and_steps(session, run_id, user)
        design_system, sections, assets = extract_website_manifests(_step_results(steps))
        visual = extract_visual_score(_step_results(steps))
        return WebsiteExperienceResponse(
            run_id=run.id,
            status=run.status,
            workspace=f"workspace/projects/{run.project_id}",
            sections=[WebsiteSectionResponse(**item) for item in sections],
            design_system=design_system,
            assets=assets,
            visual_score=visual.get("score"),
        )

    @router.get("/v1/app-builder/runs/{run_id}/website-sections", response_model=list[WebsiteSectionResponse])
    async def website_sections(
        run_id: str,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> list[WebsiteSectionResponse]:
        _, _, steps = await _run_and_steps(session, run_id, user)
        _, sections, _ = extract_website_manifests(_step_results(steps))
        return [WebsiteSectionResponse(**item) for item in sections]

    @router.get("/v1/app-builder/runs/{run_id}/visual-score", response_model=VisualScoreResponse)
    async def website_visual_score(
        run_id: str,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> VisualScoreResponse:
        run, _, steps = await _run_and_steps(session, run_id, user)
        visual = extract_visual_score(_step_results(steps))
        return VisualScoreResponse(
            run_id=run.id,
            status=run.status,
            score=visual.get("score"),
            baseline_hash=visual.get("baseline_hash"),
            current_hash=visual.get("current_hash"),
            url=visual.get("url"),
        )

    @router.post("/v1/app-builder/runs/{run_id}/sections/{section_id}/iterate", status_code=202)
    async def iterate_website_section(
        run_id: str,
        section_id: str,
        payload: WebsiteIterationCreate,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> dict:
        parent_run, _, _ = await _run_and_steps(session, run_id, user)
        if parent_run.status != "builder_completed":
            raise HTTPException(status_code=409, detail="Website must be completed before section iteration")
        if payload.section_id != section_id:
            raise HTTPException(status_code=400, detail="section_id in path and body must match")
        active = await session.scalar(
            select(WorkflowRun.id).where(
                WorkflowRun.project_id == parent_run.project_id,
                WorkflowRun.status.in_(["builder_queued", "builder_running"]),
            ).limit(1)
        )
        if active is not None:
            raise HTTPException(status_code=409, detail="Another builder run is active for this project")
        allowed, reason, _ = await check_quota(session, parent_run.project_id, payload.instruction)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)
        workflow = Workflow(
            owner_id=user.id,
            project_id=parent_run.project_id,
            name=f"Website section iteration: {section_id}",
            description="Targeted Website Builder iteration",
            steps_json=normalize_steps(build_website_section_iteration_steps(parent_run.project_id, section_id, payload.instruction)),
        )
        session.add(workflow)
        await session.flush()
        child_run = WorkflowRun(
            workflow_id=workflow.id,
            owner_id=user.id,
            project_id=parent_run.project_id,
            input=payload.instruction.strip(),
            status="builder_queued",
        )
        session.add(child_run)
        await session.flush()
        iteration = WebsiteIteration(
            project_id=parent_run.project_id,
            parent_run_id=parent_run.id,
            workflow_run_id=child_run.id,
            section_id=section_id,
            instruction=payload.instruction.strip(),
            status="queued",
        )
        session.add(iteration)
        await add_workflow_event(
            session,
            child_run.id,
            "builder.iteration_queued",
            {"parent_run_id": parent_run.id, "section_id": section_id, "instruction": payload.instruction.strip()},
        )
        await add_audit_event(
            session,
            "website.section_iteration_created",
            actor_user_id=user.id,
            project_id=parent_run.project_id,
            metadata={"parent_run_id": parent_run.id, "run_id": child_run.id, "section_id": section_id},
        )
        await session.commit()
        try:
            await enqueue_app_builder(child_run.id)
        except Exception:
            await session.rollback()
            async with session.begin():
                child_run.status = "builder_queued"
            raise
        return {
            "iteration_id": iteration.id,
            "run_id": child_run.id,
            "parent_run_id": parent_run.id,
            "section_id": section_id,
            "status": child_run.status,
        }
