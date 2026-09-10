from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from redis.asyncio import Redis, from_url
from sqlalchemy import select, update

from app.agent.base import AgentState
from app.schema import Memory
from platform_core.artifacts import storage
from platform_core.bootstrap import resolve_runtime_secrets
from platform_core.database import SessionLocal, init_db
from platform_core.events import add_audit_event, add_workflow_event
from platform_core.memory import build_context, search_knowledge, search_memory
from platform_core.model_router import create_llm, resolve_profile
from platform_core.models import Artifact, Project, ProjectPolicy, Workflow, WorkflowRun, WorkflowStepRun
from platform_core.policy import PolicyToolBroker, ToolPolicy
from platform_core.queue import enqueue_app_builder
from platform_core.settings import settings
from platform_core.workflows import get_or_create_step_run, render_step_prompt
from platform_core.worker import PolicyManus

logger = logging.getLogger("openmanus-app-builder-worker")


async def _create_agent(policy: ToolPolicy, role: str, model_profile: str | None):
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
            approved_tools=set(),
        )
    class_builder = PolicyManus
    return await class_builder.create(
        llm=llm,
        policy_broker=PolicyToolBroker(policy),
        approved_tools=set(),
    )


def _reset_agent(agent, role: str, model_profile: str | None) -> None:
    agent.llm = create_llm(role, model_profile)
    agent.state = AgentState.IDLE
    agent.current_step = 0
    agent.memory = Memory()


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
    session_id = "app-builder-finalize"
    agent.sandbox.process.create_session(session_id)
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
                step = await get_or_create_step_run(
                    session,
                    run=run,
                    step_index=step_index,
                    step_name=spec["name"],
                    prompt=spec["prompt"],
                )
                prompt = render_step_prompt(
                    spec["prompt"],
                    input_text=run.input,
                    previous_output=run.output or "",
                    step_index=step_index,
                )
                enriched = await _enriched_prompt(session, run, prompt)
                await session.commit()

            agent = await _create_agent(policy, role, model_profile) if agent is None else agent
            _reset_agent(agent, role, model_profile)

            completed = False
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
                            "name": spec["name"],
                            "attempt": attempt,
                            "role": role,
                            "model_profile": profile.config_name,
                            "browser_required": bool(spec.get("browser_required", False)),
                        },
                    )
                    await session.commit()

                _reset_agent(agent, role, model_profile)
                before_input = int(getattr(agent.llm, "total_input_tokens", 0))
                before_output = int(getattr(agent.llm, "total_completion_tokens", 0))
                try:
                    result = await agent.run(enriched)
                    completed = True
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

                if completed:
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
                            "attempts": max_attempts,
                            "error": last_error[:2000],
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
                step.status = "completed"
                step.result = result[:50000]
                step.completed_at = datetime.now(timezone.utc)
                run.output = result
                run.current_step = step_index + 1
                run.heartbeat_at = datetime.now(timezone.utc)
                await add_workflow_event(
                    session,
                    run_id,
                    "builder.step_completed",
                    {"step_index": step_index, "next_step": run.current_step},
                )
                await session.commit()

        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            project = await session.get(Project, run.project_id)
            run.output = run.output or "Application build completed."
            run.status = "builder_completed"
            run.completed_at = datetime.now(timezone.utc)
            archive = (
                _sandbox_package(agent, project.id)
                if settings.sandbox_enabled
                else _package_local_workspace(project.id)
            )
            try:
                download_url = await _record_artifact(session, run, project, archive)
            finally:
                archive.unlink(missing_ok=True)
            await add_workflow_event(
                session,
                run_id,
                "builder.artifact_created",
                {
                    "status": run.status,
                    "download_url": download_url,
                    "filename": "application.zip",
                },
            )
            await add_workflow_event(
                session,
                run_id,
                "builder.completed",
                {"status": run.status, "artifact": download_url},
            )
            await add_audit_event(
                session,
                "builder.completed",
                actor_user_id=run.owner_id,
                project_id=project.id,
                metadata={"run_id": run.id, "artifact": download_url},
            )
            await session.commit()
    except Exception as exc:
        logger.exception("Builder run %s failed", run_id)
        async with SessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is not None:
                run.status = "builder_failed"
                run.error = str(exc)[:10000]
                run.completed_at = datetime.now(timezone.utc)
                await add_workflow_event(
                    session,
                    run_id,
                    "builder.failed",
                    {"status": run.status, "error": run.error[:2000]},
                )
                await add_audit_event(
                    session,
                    "builder.failed",
                    actor_user_id=run.owner_id,
                    project_id=run.project_id,
                    metadata={"run_id": run.id},
                )
                await session.commit()
    finally:
        if agent is not None:
            try:
                await agent.cleanup()
            except Exception:
                logger.exception("Builder agent cleanup failed for %s", run_id)


async def recover_stale_builder_runs() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.workflow_stale_seconds)
    async with SessionLocal() as session:
        rows = await session.scalars(
            select(WorkflowRun).where(
                WorkflowRun.status == "builder_running",
                WorkflowRun.heartbeat_at.is_not(None),
                WorkflowRun.heartbeat_at < cutoff,
            )
        )
        recovered = []
        for run in rows.all():
            run.status = "builder_queued"
            recovered.append(run.id)
            await add_workflow_event(
                session,
                run.id,
                "builder.recovered",
                {"status": "builder_queued", "reason": "stale heartbeat"},
            )
        await session.commit()
    for run_id in recovered:
        try:
            await enqueue_app_builder(run_id)
        except Exception:
            logger.exception("Failed to requeue builder run %s", run_id)


async def builder_worker_loop() -> None:
    if settings.auto_create_db:
        await init_db()
    redis: Redis = from_url(settings.redis_url, decode_responses=True)
    logger.info("OpenManus App Builder listening on %s", settings.builder_queue_name)
    last_recovery = datetime.min.replace(tzinfo=timezone.utc)
    try:
        while True:
            now = datetime.now(timezone.utc)
            if (now - last_recovery).total_seconds() >= 30:
                await recover_stale_builder_runs()
                last_recovery = now
            item = await redis.brpop(settings.builder_queue_name, timeout=5)
            if item:
                run_id = item[1].split(":", 1)[1] if item[1].startswith("builder:") else item[1]
                claimed = await claim_builder_run(run_id)
                if claimed:
                    await process_builder_run(claimed)
                continue
            run_id = await claim_builder_run()
            if run_id:
                await process_builder_run(run_id)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(builder_worker_loop())
