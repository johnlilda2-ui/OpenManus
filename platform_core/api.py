import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.auth import create_access_token, get_current_user, hash_password, verify_password
from platform_core.database import SessionLocal, get_db, init_db
from platform_core.events import add_audit_event, add_task_event, add_workflow_event
from platform_core.memory import search_knowledge, search_memory
from platform_core.models import Conversation, KnowledgeDocument, MemoryEntry, Message, Project, ProjectPolicy, Task, TaskEvent, User, Workflow, WorkflowEvent, WorkflowRun, WorkflowStepRun
from platform_core.queue import enqueue_task, enqueue_workflow
from platform_core.schemas import ConversationCreate, ConversationResponse, KnowledgeCreate, KnowledgeResponse, LoginRequest, MemoryCreate, MemoryResponse, MessageResponse, ProjectCreate, ProjectPolicyResponse, ProjectPolicyUpdate, ProjectResponse, RegisterRequest, TaskCreate, TaskEventResponse, TaskResponse, TokenResponse, UserResponse, WorkflowCreate, WorkflowEventResponse, WorkflowResponse, WorkflowRunCreate, WorkflowRunDetailResponse, WorkflowRunResponse, WorkflowStepRunResponse, WorkflowStepSpec
from platform_core.settings import settings
from platform_core.workflows import normalize_steps


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="OpenManus Operational Platform", version="0.2.0", description="Persistent control plane around the OpenManus agent engine.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def require_owned_project(project: Project | None, user: User) -> Project:
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_owned_conversation(conversation: Conversation | None, user: User) -> Conversation:
    if conversation is None or conversation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def require_owned_task(task: Task | None, user: User) -> Task:
    if task is None or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def require_owned_workflow(workflow: Workflow | None, user: User) -> Workflow:
    if workflow is None or workflow.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def require_owned_run(run: WorkflowRun | None, user: User) -> WorkflowRun:
    if run is None or run.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


async def get_or_create_policy(session: AsyncSession, project_id: str) -> ProjectPolicy:
    policy = await session.scalar(select(ProjectPolicy).where(ProjectPolicy.project_id == project_id))
    if policy is not None:
        return policy
    policy = ProjectPolicy(project_id=project_id)
    session.add(policy)
    await session.flush()
    return policy


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "openmanus-platform"}


@app.post("/v1/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    session.add(user)
    await session.flush()
    await add_audit_event(session, "auth.register", actor_user_id=user.id, metadata={"email": email})
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    await add_audit_event(session, "auth.login", actor_user_id=user.id)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/v1/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@app.post("/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> ProjectResponse:
    project = Project(owner_id=user.id, name=payload.name.strip(), description=payload.description)
    session.add(project)
    await session.flush()
    await get_or_create_policy(session, project.id)
    await add_audit_event(session, "project.created", actor_user_id=user.id, project_id=project.id)
    await session.commit()
    return ProjectResponse.model_validate(project)


@app.get("/v1/projects", response_model=list[ProjectResponse])
async def list_projects(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[ProjectResponse]:
    result = await session.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc()))
    return [ProjectResponse.model_validate(project) for project in result.all()]


@app.get("/v1/projects/{project_id}/policy", response_model=ProjectPolicyResponse)
async def get_policy(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> ProjectPolicyResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    policy = await get_or_create_policy(session, project_id)
    await session.commit()
    return ProjectPolicyResponse.model_validate(policy)


@app.put("/v1/projects/{project_id}/policy", response_model=ProjectPolicyResponse)
async def update_policy(project_id: str, payload: ProjectPolicyUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> ProjectPolicyResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    policy = await get_or_create_policy(session, project_id)
    policy.allowed_tool_patterns = payload.allowed_tool_patterns
    policy.denied_tool_patterns = payload.denied_tool_patterns
    policy.approval_required_patterns = payload.approval_required_patterns
    policy.version += 1
    await add_audit_event(session, "project.policy_updated", actor_user_id=user.id, project_id=project_id, metadata={"version": policy.version})
    await session.commit()
    return ProjectPolicyResponse.model_validate(policy)


@app.post("/v1/projects/{project_id}/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(project_id: str, payload: ConversationCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> ConversationResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    conversation = Conversation(project_id=project_id, owner_id=user.id, title=payload.title.strip())
    session.add(conversation)
    await session.flush()
    await add_audit_event(session, "conversation.created", actor_user_id=user.id, project_id=project_id)
    await session.commit()
    return ConversationResponse(id=conversation.id, project_id=conversation.project_id, title=conversation.title, created_at=conversation.created_at, updated_at=conversation.updated_at, messages=[])


@app.get("/v1/projects/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[ConversationResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    result = await session.scalars(select(Conversation).where(Conversation.project_id == project_id, Conversation.owner_id == user.id).order_by(Conversation.updated_at.desc()))
    return [ConversationResponse(id=c.id, project_id=c.project_id, title=c.title, created_at=c.created_at, updated_at=c.updated_at, messages=[]) for c in result.all()]


@app.get("/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> ConversationResponse:
    conversation = await session.get(Conversation, conversation_id)
    require_owned_conversation(conversation, user)
    messages = await session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()))
    return ConversationResponse(id=conversation.id, project_id=conversation.project_id, title=conversation.title, created_at=conversation.created_at, updated_at=conversation.updated_at, messages=[MessageResponse.model_validate(message) for message in messages.all()])


@app.post("/v1/conversations/{conversation_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(conversation_id: str, payload: TaskCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> TaskResponse:
    conversation = await session.get(Conversation, conversation_id)
    require_owned_conversation(conversation, user)
    project = await session.get(Project, conversation.project_id)
    require_owned_project(project, user)
    prompt = payload.prompt.strip()
    task = Task(project_id=project.id, conversation_id=conversation.id, owner_id=user.id, prompt=prompt, status="queued")
    session.add(task)
    await session.flush()
    session.add(Message(conversation_id=conversation.id, task_id=task.id, role="user", content=prompt))
    await add_task_event(session, task.id, "task.queued", {"status": "queued"})
    await add_audit_event(session, "task.created", actor_user_id=user.id, project_id=project.id, task_id=task.id)
    await session.commit()
    try:
        await enqueue_task(task.id)
    except Exception as exc:
        async with SessionLocal() as audit_session:
            await add_task_event(audit_session, task.id, "task.queue_deferred", {"status": "queued", "reason": str(exc)[:1000]})
            await add_audit_event(audit_session, "task.queue_deferred", actor_user_id=user.id, project_id=project.id, task_id=task.id, metadata={"reason": str(exc)[:1000]})
            await audit_session.commit()
    return TaskResponse.model_validate(task)


@app.get("/v1/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[TaskResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    result = await session.scalars(select(Task).where(Task.project_id == project_id, Task.owner_id == user.id).order_by(Task.created_at.desc()))
    return [TaskResponse.model_validate(task) for task in result.all()]


@app.get("/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> TaskResponse:
    task = await session.get(Task, task_id)
    require_owned_task(task, user)
    return TaskResponse.model_validate(task)


@app.post("/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> TaskResponse:
    task = await session.get(Task, task_id)
    task = require_owned_task(task, user)
    if task.status in {"completed", "failed", "cancelled"}:
        return TaskResponse.model_validate(task)
    task.cancel_requested = True
    if task.status == "queued":
        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)
        await add_task_event(session, task.id, "task.cancelled", {"status": task.status})
    else:
        await add_task_event(session, task.id, "task.cancel_requested", {"status": task.status})
    await add_audit_event(session, "task.cancel_requested", actor_user_id=user.id, project_id=task.project_id, task_id=task.id)
    await session.commit()
    return TaskResponse.model_validate(task)


@app.get("/v1/tasks/{task_id}/events")
async def task_events(task_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db), last_event_id: int | None = Header(default=None, alias="Last-Event-ID")) -> StreamingResponse:
    task = await session.get(Task, task_id)
    require_owned_task(task, user)
    starting_id = max(last_event_id or 0, 0)

    async def stream() -> AsyncIterator[str]:
        last_id = starting_id
        keepalive_at = datetime.now(timezone.utc)
        while True:
            async with SessionLocal() as stream_session:
                events = await stream_session.scalars(select(TaskEvent).where(TaskEvent.task_id == task_id, TaskEvent.id > last_id).order_by(TaskEvent.id.asc()).limit(100))
                event_rows = events.all()
                current_task = await stream_session.get(Task, task_id)
            sent = False
            for event in event_rows:
                data = json.dumps(TaskEventResponse.model_validate(event).model_dump(mode="json"), separators=(",", ":"))
                yield f"id: {event.id}\nevent: {event.kind}\ndata: {data}\n\n"
                last_id = event.id
                sent = True
            if current_task is None or (current_task.status in {"completed", "failed", "cancelled"} and not sent):
                return
            now = datetime.now(timezone.utc)
            if (now - keepalive_at).total_seconds() >= 15:
                yield ": keepalive\n\n"
                keepalive_at = now
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@app.post("/v1/projects/{project_id}/memory", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(project_id: str, payload: MemoryCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> MemoryResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    entry = MemoryEntry(owner_id=user.id, project_id=project_id, kind=payload.kind, key=payload.key, content=payload.content, importance=payload.importance, metadata_json=payload.metadata_json)
    session.add(entry)
    await add_audit_event(session, "memory.created", actor_user_id=user.id, project_id=project_id, metadata={"kind": payload.kind})
    await session.commit()
    return MemoryResponse.model_validate(entry)


@app.get("/v1/projects/{project_id}/memory", response_model=list[MemoryResponse])
async def list_memory(project_id: str, q: str | None = None, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[MemoryResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    if q:
        rows = await search_memory(session, owner_id=user.id, project_id=project_id, query=q, limit=20)
    else:
        result = await session.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == user.id, MemoryEntry.project_id == project_id).order_by(MemoryEntry.updated_at.desc()).limit(50))
        rows = result.all()
    return [MemoryResponse.model_validate(row) for row in rows]


@app.post("/v1/projects/{project_id}/knowledge", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(project_id: str, payload: KnowledgeCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> KnowledgeResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    document = KnowledgeDocument(owner_id=user.id, project_id=project_id, title=payload.title.strip(), content=payload.content, source=payload.source, metadata_json=payload.metadata_json)
    session.add(document)
    await add_audit_event(session, "knowledge.created", actor_user_id=user.id, project_id=project_id, metadata={"title": payload.title})
    await session.commit()
    return KnowledgeResponse.model_validate(document)


@app.get("/v1/projects/{project_id}/knowledge", response_model=list[KnowledgeResponse])
async def list_knowledge(project_id: str, q: str | None = None, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[KnowledgeResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    if q:
        rows = await search_knowledge(session, owner_id=user.id, project_id=project_id, query=q, limit=20)
    else:
        result = await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.owner_id == user.id, KnowledgeDocument.project_id == project_id).order_by(KnowledgeDocument.updated_at.desc()).limit(50))
        rows = result.all()
    return [KnowledgeResponse.model_validate(row) for row in rows]


@app.post("/v1/projects/{project_id}/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(project_id: str, payload: WorkflowCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> WorkflowResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    try:
        steps = normalize_steps([step.model_dump() for step in payload.steps])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    workflow = Workflow(owner_id=user.id, project_id=project_id, name=payload.name.strip(), description=payload.description, steps_json=steps)
    session.add(workflow)
    await session.flush()
    await add_audit_event(session, "workflow.created", actor_user_id=user.id, project_id=project_id, metadata={"workflow_id": workflow.id})
    await session.commit()
    return WorkflowResponse(id=workflow.id, project_id=workflow.project_id, name=workflow.name, description=workflow.description, steps=[WorkflowStepSpec.model_validate(step) for step in workflow.steps_json], created_at=workflow.created_at, updated_at=workflow.updated_at)


@app.get("/v1/projects/{project_id}/workflows", response_model=list[WorkflowResponse])
async def list_workflows(project_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[WorkflowResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    result = await session.scalars(select(Workflow).where(Workflow.owner_id == user.id, Workflow.project_id == project_id).order_by(Workflow.updated_at.desc()))
    return [WorkflowResponse(id=w.id, project_id=w.project_id, name=w.name, description=w.description, steps=[WorkflowStepSpec.model_validate(step) for step in w.steps_json], created_at=w.created_at, updated_at=w.updated_at) for w in result.all()]


@app.post("/v1/workflows/{workflow_id}/runs", response_model=WorkflowRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_workflow_run(workflow_id: str, payload: WorkflowRunCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> WorkflowRunResponse:
    workflow = await session.get(Workflow, workflow_id)
    require_owned_workflow(workflow, user)
    run = WorkflowRun(workflow_id=workflow.id, owner_id=user.id, project_id=workflow.project_id, input=payload.input.strip(), status="queued")
    session.add(run)
    await session.flush()
    await add_workflow_event(session, run.id, "workflow.queued", {"status": run.status})
    await add_audit_event(session, "workflow.run_created", actor_user_id=user.id, project_id=workflow.project_id, metadata={"workflow_id": workflow.id, "run_id": run.id})
    await session.commit()
    try:
        await enqueue_workflow(run.id)
    except Exception as exc:
        async with SessionLocal() as audit_session:
            await add_workflow_event(audit_session, run.id, "workflow.queue_deferred", {"status": "queued", "reason": str(exc)[:1000]})
            await add_audit_event(audit_session, "workflow.queue_deferred", actor_user_id=user.id, project_id=workflow.project_id, metadata={"workflow_id": workflow.id, "run_id": run.id, "reason": str(exc)[:1000]})
            await audit_session.commit()
    return WorkflowRunResponse.model_validate(run)


@app.get("/v1/workflows/{workflow_id}/runs", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(workflow_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> list[WorkflowRunResponse]:
    workflow = await session.get(Workflow, workflow_id)
    require_owned_workflow(workflow, user)
    result = await session.scalars(select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id, WorkflowRun.owner_id == user.id).order_by(WorkflowRun.created_at.desc()))
    return [WorkflowRunResponse.model_validate(run) for run in result.all()]


@app.get("/v1/workflow-runs/{run_id}", response_model=WorkflowRunDetailResponse)
async def get_workflow_run(run_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> WorkflowRunDetailResponse:
    run = await session.get(WorkflowRun, run_id)
    require_owned_run(run, user)
    steps = await session.scalars(select(WorkflowStepRun).where(WorkflowStepRun.workflow_run_id == run_id).order_by(WorkflowStepRun.step_index.asc()))
    return WorkflowRunDetailResponse(**WorkflowRunResponse.model_validate(run).model_dump(), steps=[WorkflowStepRunResponse.model_validate(step) for step in steps.all()])


@app.post("/v1/workflow-runs/{run_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_workflow_run(run_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> WorkflowRunResponse:
    run = await session.get(WorkflowRun, run_id)
    run = require_owned_run(run, user)
    if run.status in {"completed", "failed", "cancelled"}:
        return WorkflowRunResponse.model_validate(run)
    run.cancel_requested = True
    if run.status == "queued":
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        await add_workflow_event(session, run.id, "workflow.cancelled", {"status": run.status})
    else:
        await add_workflow_event(session, run.id, "workflow.cancel_requested", {"status": run.status})
    await add_audit_event(session, "workflow.cancel_requested", actor_user_id=user.id, project_id=run.project_id, metadata={"run_id": run.id, "workflow_id": run.workflow_id})
    await session.commit()
    return WorkflowRunResponse.model_validate(run)


@app.get("/v1/workflow-runs/{run_id}/events")
async def workflow_events(run_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db), last_event_id: int | None = Header(default=None, alias="Last-Event-ID")) -> StreamingResponse:
    run = await session.get(WorkflowRun, run_id)
    require_owned_run(run, user)
    starting_id = max(last_event_id or 0, 0)

    async def stream() -> AsyncIterator[str]:
        last_id = starting_id
        keepalive_at = datetime.now(timezone.utc)
        while True:
            async with SessionLocal() as stream_session:
                events = await stream_session.scalars(select(WorkflowEvent).where(WorkflowEvent.workflow_run_id == run_id, WorkflowEvent.id > last_id).order_by(WorkflowEvent.id.asc()).limit(100))
                event_rows = events.all()
                current_run = await stream_session.get(WorkflowRun, run_id)
            sent = False
            for event in event_rows:
                data = json.dumps(WorkflowEventResponse.model_validate(event).model_dump(mode="json"), separators=(",", ":"))
                yield f"id: {event.id}\nevent: {event.kind}\ndata: {data}\n\n"
                last_id = event.id
                sent = True
            if current_run is None or (current_run.status in {"completed", "failed", "cancelled"} and not sent):
                return
            now = datetime.now(timezone.utc)
            if (now - keepalive_at).total_seconds() >= 15:
                yield ": keepalive\n\n"
                keepalive_at = now
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
