from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from redis.asyncio import Redis, from_url
from sqlalchemy import select, update

from app.agent.base import AgentState
from app.schema import Memory
from platform_core.approvals import create_or_get_workflow_approval
from platform_core.artifacts import storage
from platform_core.bootstrap import resolve_runtime_secrets
from platform_core.database import SessionLocal, init_db
from platform_core.events import add_audit_event, add_workflow_event
from platform_core.memory import build_context, search_knowledge, search_memory
from platform_core.model_router import create_llm, resolve_profile
from platform_core.models import ApprovalRequest, Artifact, Project, ProjectPolicy, Workflow, WorkflowRun, WorkflowStepRun
from platform_core.policy import PolicyToolBroker, ToolApprovalRequired, ToolPolicy
from platform_core.queue import enqueue_app_builder
from platform_core.settings import settings
from platform_core.usage import record_usage
from platform_core.website_builder import build_simple_static_files
from platform_core.workflows import get_or_create_step_run, render_step_prompt
from platform_core.worker import PolicyManus

logger = logging.getLogger("openmanus-app-builder-worker")


class _BuilderCancellationRequested(Exception):
    pass


async def _builder_cancel_requested(run_id: str) -> bool:
    async with SessionLocal() as session:
        run = await session.get(WorkflowRun, run_id)
        return bool(run and run.cancel_requested)


async def _run_builder_agent_with_cancellation(agent, prompt: str, run_id: str, role: str) -> str:
    execution = asyncio.create_task(agent.run(prompt))
    last_step = -1
    while not execution.done():
        try:
            await asyncio.wait_for(asyncio.shield(execution), timeout=1.0)
            break
        except asyncio.TimeoutError:
            current_step = int(getattr(agent, "current_step", 0))
            if current_step != last_step:
                last_step = current_step
                async with SessionLocal() as session:
                    run = await session.get(WorkflowRun, run_id)
                    if run is not None and run.status == "builder_running":
                        run.heartbeat_at = datetime.now(timezone.utc)
                        await add_workflow_event(
                            session,
                            run_id,
                            "builder.agent_progress",
                            {
                                "step": current_step,
                                "max_steps": int(getattr(agent, "max_steps", 0)),
                                "role": role,
                            },
                        )
                        await session.commit()
            if await _builder_cancel_requested(run_id):
                execution.cancel()
                try:
                    await execution
                except asyncio.CancelledError:
                    pass
                raise _BuilderCancellationRequested
    return await execution


async def _create_agent(policy: ToolPolicy, role: str, model_profile: str | None, approved_tools: set[str]):
    resolve_runtime_secrets()
    llm = create_llm(role, model_profile)
    if settings.sandbox_enabled:
        if settings.sandbox_backend != "daytona":
            raise RuntimeError(
                "App Builder requires the configured isolated Daytona sandbox in production"
            )
        from platform_core.sandbox_runtime import PolicySandboxManus

        return await PolicySandboxManus.create(
            llm=llm,
            policy_broker=PolicyToolBroker(policy),
            approved_tools=approved_tools,
        )
    return await PolicyManus.create(
        llm=llm,
        policy_broker=PolicyToolBroker(policy),
        approved_tools=approved_tools,
    )


def _builder_agent_step_budget(role: str) -> int:
    budgets = {
        "planner": 8,
        "designer": 10,
        "builder": 12,
        "tester": 10,
        "reviewer": 8,
        "fixer": 10,
    }
    return int(os.getenv("OPENMANUS_BUILDER_AGENT_MAX_STEPS", budgets.get(role, 10)))


def _reset_agent(agent, role: str, model_profile: str | None, max_steps_override: int | None = None) -> None:
    agent.llm = create_llm(role, model_profile)
    agent.state = AgentState.IDLE
    agent.current_step = 0
    agent.max_steps = int(max_steps_override if max_steps_override is not None else _builder_agent_step_budget(role))
    agent.memory = Memory()



def _is_simple_static_request(requirements: str) -> bool:
    normalized = (requirements or "").lower().replace("—", "-").replace("–", "-")
    one_page = "one-page" in normalized or "one page" in normalized
    html_js = (
        "plain html" in normalized
        or "html/css/javascript" in normalized
        or "html/css/js" in normalized
        or ("html" in normalized and "css" in normalized and "javascript" in normalized)
    )
    excluded = (
        "marketplace", "e-commerce", "ecommerce", "saas", "booking",
        "dashboard", "database", "authentication", "multi-page", "multi page",
    )
    return one_page and html_js and not any(term in normalized for term in excluded)

async def _run_deterministic_static_build(
    agent,
    run_id: str,
    project_id: str,
    requirements: str,
) -> str:
    """Build the narrow one-page HTML/CSS/JS path without spending LLM cycles."""
    from app.daytona.sandbox import SessionExecuteRequest

    if await _builder_cancel_requested(run_id):
        raise _BuilderCancellationRequested

    files = build_simple_static_files(requirements)
    remote_root = f"/workspace/projects/{project_id}"
    session_id = "cataron-workspace-bootstrap"
    progress = (
        ("files", "Generating the website files"),
        ("server", "Starting the live preview server"),
        ("verify", "Verifying the generated page"),
    )

    for key, message in progress:
        async with SessionLocal() as session:
            await add_workflow_event(
                session,
                run_id,
                "builder.fast_path_progress",
                {"stage": key, "message": message},
            )
            await session.commit()

        if await _builder_cancel_requested(run_id):
            raise _BuilderCancellationRequested

        if key == "files":
            for filename, content in files.items():
                encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
                command = (
                    "python -c \"import base64; "
                    f"open('{remote_root}/{filename}','wb').write(base64.b64decode('{encoded}'))\""
                )
                response = agent.sandbox.process.execute_session_command(
                    session_id,
                    SessionExecuteRequest(command=command, run_async=False, cwd=remote_root),
                    timeout=30,
                )
                if getattr(response, "exit_code", 1) not in {0, None}:
                    raise RuntimeError(f"Failed to write {filename} in the sandbox")

        elif key == "server":
            command = (
                "python -m http.server 8081 --bind 0.0.0.0 "
                f">/tmp/cataron-preview.log 2>&1 & echo $!"
            )
            response = agent.sandbox.process.execute_session_command(
                session_id,
                SessionExecuteRequest(command=command, run_async=False, cwd=remote_root),
                timeout=30,
            )
            if getattr(response, "exit_code", 1) not in {0, None}:
                raise RuntimeError("Failed to start the preview server on port 8081")

        elif key == "verify":
            checks = (
                f"curl --noproxy '*' -fsS http://127.0.0.1:8081/ >/dev/null && "
                f"curl --noproxy '*' -fsS http://127.0.0.1:8081/styles.css >/dev/null && "
                f"curl --noproxy '*' -fsS http://127.0.0.1:8081/script.js >/dev/null"
            )
            response = agent.sandbox.process.execute_session_command(
                session_id,
                SessionExecuteRequest(command=checks, run_async=False, cwd=remote_root),
                timeout=30,
            )
            if getattr(response, "exit_code", 1) not in {0, None}:
                raise RuntimeError("Generated website failed the local preview checks")

            from app.tool.sandbox.sb_preview_tool import SandboxPreviewTool

            preview_result = await SandboxPreviewTool.create_with_sandbox(agent.sandbox).execute(port=8081)
            if preview_result.error:
                raise RuntimeError(preview_result.error)
            preview_data = (
                json.loads(preview_result.output)
                if isinstance(preview_result.output, str)
                else (preview_result.output or {})
            )
            preview_url = str(preview_data.get("url") or "").strip()
            if not preview_url:
                raise RuntimeError("Daytona did not return a preview URL")

            return (
                f"PREVIEW_URL: {preview_url}\n"
                "WEBSITE_READY: true\n"
                "BUILD_MODE: deterministic_static\n"
            )

    raise RuntimeError("Deterministic static build did not reach verification")


async def claim_builder_run(run_id: str | None = None) -> str | None:
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        candidate = run_id or await session.scalar(
            select(WorkflowRun.id)
            .where(WorkflowRun.status == "builder_queued")
            .order_by(WorkflowRun.created_at.asc())
            .limit(1)
        )
        if candidate is None:
            return None
        result = await session.execute(
            update(WorkflowRun)
            .where(
                WorkflowRun.id == candidate,
                WorkflowRun.status == "builder_queued",
                WorkflowRun.cancel_requested.is_(False),
            )
            .values(status="builder_running", started_at=now, heartbeat_at=now)
        )
        if result.rowcount != 1:
            return None
        run = await session.get(WorkflowRun, candidate)
        await add_workflow_event(session, run.id, "builder.started", {"status": run.status})
        await session.commit()
        return run.id


def _local_workspace(project_id: str) -> Path:
    root = Path(os.getenv("OPENMANUS_WORKSPACE_ROOT", "workspace")).resolve()
    path = root / "projects" / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _package_local_workspace(project_id: str) -> Path:
    workspace = _local_workspace(project_id)
    fd, name = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    output = Path(name)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
                continue
            archive.write(path, path.relative_to(workspace))
    return output


def _sandbox_package(agent, project_id: str) -> Path:
    from daytona import SessionExecuteRequest

    remote_root = f"/workspace/projects/{project_id}"
    # Reuse the bootstrap process session created by PolicySandboxManus.create().
    # Creating a second Daytona process session here can fail after the website
    # has already been generated, turning a successful build into "Failed to create session".
    session_id = "cataron-workspace-bootstrap"
    archive_path = "/tmp/application.zip"
    command = (
        "python -c \"import shutil; "
        f"shutil.make_archive('/tmp/application', 'zip', '{remote_root}')\""
    )
    response = agent.sandbox.process.execute_session_command(
        session_id,
        SessionExecuteRequest(command=command, run_async=False, cwd=remote_root),
        timeout=120,
    )
    if getattr(response, "exit_code", 1) not in {0, None}:
        raise RuntimeError("Failed to package the generated application inside the sandbox")
    fd, name = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    local_path = Path(name)
    agent.sandbox.fs.download_file(archive_path, str(local_path))
    return local_path


async def _record_artifact(session, run: WorkflowRun, project: Project, local_path: Path) -> str:
    size = local_path.stat().st_size
    if size > settings.artifact_max_bytes:
        raise RuntimeError(
            f"Generated application archive exceeds {settings.artifact_max_bytes} byte limit"
        )
    digest = hashlib.sha256()
    with local_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    artifact_id = f"builder-{run.id}"
    storage_key = f"{project.id}/builder/{artifact_id}/application.zip"
    with local_path.open("rb") as stream:
        storage.put(storage_key, stream)
    artifact = Artifact(
        id=artifact_id,
        owner_id=run.owner_id,
        project_id=project.id,
        task_id=None,
        filename="application.zip",
        content_type="application/zip",
        storage_key=storage_key,
        size_bytes=size,
        sha256=digest.hexdigest(),
    )
    session.add(artifact)
    await session.flush()
    return storage.presigned_url(storage_key) or f"/v1/artifacts/{artifact.id}"


async def _enriched_prompt(session, run: WorkflowRun, prompt: str) -> str:
    memories = await search_memory(
        session,
        owner_id=run.owner_id,
        project_id=run.project_id,
        query=prompt,
        limit=6,
    )
    documents = await search_knowledge(
        session,
        owner_id=run.owner_id,
        project_id=run.project_id,
        query=prompt,
        limit=4,
    )
    return build_context(prompt=prompt, recent_messages=[], memories=memories, documents=documents)


async def _approved_tools(session, run_id: str) -> set[str]:
    rows = await session.scalars(
        select(ApprovalRequest.tool_name).where(
            ApprovalRequest.workflow_run_id == run_id,
            ApprovalRequest.status == "approved",
        )
    )
    return set(rows.all())


async def process_builder_run(run_id: str) -> None:
    agent = None
    try:
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is None or run.status in {
                "builder_completed",
                "builder_failed",
                "builder_cancelled",
            }:
                return
            workflow = await session.get(Workflow, run.workflow_id)
            project = await session.get(Project, run.project_id)
            policy_row = await session.scalar(
                select(ProjectPolicy).where(ProjectPolicy.project_id == run.project_id)
            )
            if workflow is None or project is None:
                raise RuntimeError("App Builder workflow or project no longer exists")
            policy = ToolPolicy.from_model(policy_row)

        for step_index in range(run.current_step, len(workflow.steps_json)):
            async with SessionLocal() as session:
                run = await session.get(WorkflowRun, run_id)
                workflow = await session.get(Workflow, run.workflow_id)
                if run is None or workflow is None:
                    raise RuntimeError("Builder run disappeared during execution")
                if run.cancel_requested:
                    run.status = "builder_cancelled"
                    run.completed_at = datetime.now(timezone.utc)
                    await session.commit()
                    return
                spec = workflow.steps_json[step_index]
                role = str(spec.get("role") or "builder")
                model_profile = spec.get("model_profile")
                max_attempts = int(spec.get("max_attempts", 1))
                approved_tools = await _approved_tools(session, run.id)
                step = await get_or_create_step_run(
                    session,
                    run=run,
                    step_index=step_index,
                    step_name=spec["name"],
                    prompt=spec["prompt"],
                )
                # A worker restart can occur after the step work commits but before
                # run.current_step is advanced. Never execute an already-completed
                # builder phase a second time.
                if step.status == "completed":
                    run.current_step = step_index + 1
                    run.output = step.result or run.output
                    run.heartbeat_at = datetime.now(timezone.utc)
                    await add_workflow_event(
                        session,
                        run_id,
                        "builder.step_already_completed",
                        {
                            "step_index": step_index,
                            "next_step": run.current_step,
                        },
                    )
                    await session.commit()
                    continue
                prompt = render_step_prompt(
                    spec["prompt"],
                    input_text=run.input,
                    previous_output=run.output or "",
                    step_index=step_index,
                )
                enriched = (
                    prompt
                    if spec.get("execution_mode") == "deterministic_static"
                    else await _enriched_prompt(session, run, prompt)
                )
                await session.commit()

            agent = await _create_agent(policy, role, model_profile, approved_tools) if agent is None else agent
            agent_max_steps = spec.get("max_agent_steps")
            _reset_agent(agent, role, model_profile, int(agent_max_steps) if agent_max_steps is not None else None)

            completed = False
            blocked_by_approval = False
            cancelled = False
            last_error = ""
            result = ""
            for attempt in range(1, max_attempts + 1):
                async with SessionLocal() as session:
                    run = await session.get(WorkflowRun, run_id)
                    step = await session.scalar(
                        select(WorkflowStepRun).where(
                            WorkflowStepRun.workflow_run_id == run_id,
                            WorkflowStepRun.step_index == step_index,
                        )
                    )
                    if run.cancel_requested:
                        run.status = "builder_cancelled"
                        run.completed_at = datetime.now(timezone.utc)
                        step.status = "cancelled"
                        await session.commit()
                        return
                    step.status = "running"
                    step.attempt = attempt
                    step.started_at = datetime.now(timezone.utc)
                    run.heartbeat_at = datetime.now(timezone.utc)
                    profile = resolve_profile(role, model_profile)
                    await add_workflow_event(
                        session,
                        run_id,
                        "builder.step_started",
                        {
                            "step_index": step_index,
                            "phase": step_index + 1,
                            "total_phases": len(workflow.steps_json),
                            "name": spec["name"],
                            "attempt": attempt,
                            "role": role,
                            "model_profile": profile.config_name,
                            "browser_required": bool(spec.get("browser_required", False)),
                        },
                    )
                    await session.commit()

                _reset_agent(agent, role, model_profile, int(agent_max_steps) if agent_max_steps is not None else None)
                before_input = int(getattr(agent.llm, "total_input_tokens", 0))
                before_output = int(getattr(agent.llm, "total_completion_tokens", 0))
                try:
                    fast_static = _is_simple_static_request(run.input)
                    if spec.get("execution_mode") == "deterministic_static" or fast_static:
                        result = await _run_deterministic_static_build(
                            agent,
                            run_id,
                            run.project_id,
                            run.input,
                        )
                    else:
                        result = await _run_builder_agent_with_cancellation(agent, enriched, run_id, role)
                    completed = True
                except _BuilderCancellationRequested:
                    cancelled = True
                    async with SessionLocal() as session:
                        run = await session.get(WorkflowRun, run_id)
                        step = await session.scalar(
                            select(WorkflowStepRun).where(
                                WorkflowStepRun.workflow_run_id == run_id,
                                WorkflowStepRun.step_index == step_index,
                            )
                        )
                        if run is not None:
                            run.status = "builder_cancelled"
                            run.error = None
                            run.completed_at = datetime.now(timezone.utc)
                        if step is not None:
                            step.status = "cancelled"
                            step.error = None
                            step.completed_at = datetime.now(timezone.utc)
                        await add_workflow_event(session, run_id, "builder.cancelled", {"status": "builder_cancelled", "step_index": step_index, "interrupted": True})
                        await session.commit()
                    return
                except ToolApprovalRequired as exc:
                    blocked_by_approval = True
                    async with SessionLocal() as session:
                        run = await session.get(WorkflowRun, run_id)
                        approval = await create_or_get_workflow_approval(
                            session,
                            workflow_run_id=run_id,
                            project_id=run.project_id,
                            tool_name=exc.tool_name,
                            reason=exc.reason,
                        )
                        run.status = "builder_awaiting_approval"
                        run.error = None
                        await add_workflow_event(
                            session,
                            run_id,
                            "approval.required",
                            {
                                "status": run.status,
                                "approval_id": approval.id,
                                "tool": exc.tool_name,
                                "reason": exc.reason,
                                "step_index": step_index,
                            },
                        )
                        await add_audit_event(
                            session,
                            "approval.requested",
                            actor_user_id=run.owner_id,
                            project_id=run.project_id,
                            metadata={
                                "approval_id": approval.id,
                                "tool": exc.tool_name,
                                "workflow_run_id": run.id,
                                "step_index": step_index,
                            },
                        )
                        await session.commit()
                    return
                except Exception as exc:
                    last_error = str(exc)
                    completed = False
                    logger.exception(
                        "Builder step %s attempt %s failed", step_index, attempt
                    )

                after_input = int(getattr(agent.llm, "total_input_tokens", 0))
                after_output = int(getattr(agent.llm, "total_completion_tokens", 0))
                step_input_tokens = max(0, after_input - before_input)
                step_output_tokens = max(0, after_output - before_output)

                if blocked_by_approval or cancelled:
                    return
                if await _builder_cancel_requested(run_id):
                    async with SessionLocal() as session:
                        run = await session.get(WorkflowRun, run_id)
                        step = await session.scalar(
                            select(WorkflowStepRun).where(
                                WorkflowStepRun.workflow_run_id == run_id,
                                WorkflowStepRun.step_index == step_index,
                            )
                        )
                        if run is not None:
                            run.status = "builder_cancelled"
                            run.completed_at = datetime.now(timezone.utc)
                        if step is not None:
                            step.status = "cancelled"
                            step.completed_at = datetime.now(timezone.utc)
                        await add_workflow_event(session, run_id, "builder.cancelled", {"status": "builder_cancelled", "step_index": step_index, "interrupted": False})
                        await session.commit()
                    return
                if completed:
                    preview_match = re.search(r"PREVIEW_URL\s*[:=]\s*(https?://[^\s)]+)", result or "", flags=re.IGNORECASE)
                    async with SessionLocal() as session:
                        if preview_match:
                            await add_workflow_event(session, run_id, "builder.preview_ready", {"url": preview_match.group(1).rstrip(".,"), "step_index": step_index})
                        await session.commit()
                    async with SessionLocal() as session:
                        run = await session.get(WorkflowRun, run_id)
                        await record_usage(
                            session,
                            owner_id=run.owner_id,
                            project_id=run.project_id,
                            task_id=None,
                            input_text=enriched,
                            output_text=result,
                            input_tokens=step_input_tokens or None,
                            output_tokens=step_output_tokens or None,
                            usage_source="provider",
                        )
                        await session.commit()
                    break
                if attempt < max_attempts:
                    enriched += (
                        f"\n\nPrevious attempt failed with: {last_error[:2000]}\n"
                        "Re-evaluate the implementation, correct the failure, and try again."
                    )

            if not completed:
                async with SessionLocal() as session:
                    run = await session.get(WorkflowRun, run_id)
                    step = await session.scalar(
                        select(WorkflowStepRun).where(
                            WorkflowStepRun.workflow_run_id == run_id,
                            WorkflowStepRun.step_index == step_index,
                        )
                    )
                    if run.cancel_requested:
                        run.status = "builder_cancelled"
                        run.completed_at = datetime.now(timezone.utc)
                        if step is not None:
                            step.status = "cancelled"
                            step.completed_at = datetime.now(timezone.utc)
                        await session.commit()
                        return
                    step.status = "failed"
                    step.error = last_error[:10000]
                    step.completed_at = datetime.now(timezone.utc)
                    run.status = "builder_failed"
                    run.error = (
                        f"Builder step {step_index} failed after {max_attempts} attempts: "
                        f"{last_error}"
                    )[:10000]
                    run.completed_at = datetime.now(timezone.utc)
                    await add_workflow_event(
                        session,
                        run_id,
                        "builder.failed",
                        {
                            "status": run.status,
                            "step_index": step_index,
                            "error": run.error,
                        },
                    )
                    await session.commit()
                return

            async with SessionLocal() as session:
                run = await session.get(WorkflowRun, run_id)
                step = await session.scalar(
                    select(WorkflowStepRun).where(
                        WorkflowStepRun.workflow_run_id == run_id,
                        WorkflowStepRun.step_index == step_index,
                    )
                )
                if run is None:
                    return
                now = datetime.now(timezone.utc)
                if step is not None:
                    step.status = "completed"
                    step.result = result[:50000]
                    step.error = None
                    step.completed_at = now
                run.output = result
                run.current_step = step_index + 1
                run.heartbeat_at = now
                await add_workflow_event(session, run_id, "builder.step_completed", {"step_index": step_index, "next_step": run.current_step, "result": result[:10000]})
                await session.commit()

        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            project = await session.get(Project, run.project_id)
            if run.cancel_requested:
                run.status = "builder_cancelled"
                run.completed_at = datetime.now(timezone.utc)
                await session.commit()
                return
            try:
                local_zip = _sandbox_package(agent, project.id) if settings.sandbox_enabled else _package_local_workspace(project.id)
                artifact_url = await _record_artifact(session, run, project, local_zip)
                run.output = f"Application generated successfully. Artifact: {artifact_url}"
                run.status = "builder_completed"
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "builder.artifact_created", {"artifact_url": artifact_url, "status": run.status})
                await add_workflow_event(session, run.id, "builder.completed", {"status": run.status, "output": run.output})
                await session.commit()
            except Exception as exc:
                run.status = "builder_failed"
                run.error = str(exc)[:10000]
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(session, run.id, "builder.failed", {"status": run.status, "error": run.error})
                await session.commit()
    except Exception as exc:
        logger.exception("Builder run %s failed", run_id)
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is not None:
                run.status = "builder_failed"
                run.error = str(exc)[:10000]
                run.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        try:
            if agent is not None:
                await agent.cleanup()
        except Exception:
            logger.exception("Builder cleanup failed for run %s", run_id)
