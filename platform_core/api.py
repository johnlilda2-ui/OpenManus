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
from platform_core.events import add_audit_event, add_task_event
from platform_core.models import Conversation, Message, Project, Task, TaskEvent, User
from platform_core.queue import enqueue_task
from platform_core.schemas import (
    ConversationCreate,
    ConversationResponse,
    LoginRequest,
    MessageResponse,
    ProjectCreate,
    ProjectResponse,
    RegisterRequest,
    TaskCreate,
    TaskEventResponse,
    TaskResponse,
    TokenResponse,
    UserResponse,
)
from platform_core.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="OpenManus Operational Platform",
    version="0.1.0",
    description="Persistent API and task-control plane around the OpenManus agent engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    await add_audit_event(session, "auth.login", actor_user_id=user.id)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/v1/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@app.post("/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = Project(owner_id=user.id, name=payload.name.strip(), description=payload.description)
    session.add(project)
    await session.flush()
    await add_audit_event(session, "project.created", actor_user_id=user.id, project_id=project.id)
    await session.commit()
    return ProjectResponse.model_validate(project)


@app.get("/v1/projects", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    result = await session.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    )
    return [ProjectResponse.model_validate(project) for project in result.all()]


@app.post(
    "/v1/projects/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    project_id: str,
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)

    conversation = Conversation(project_id=project_id, owner_id=user.id, title=payload.title.strip())
    session.add(conversation)
    await session.flush()
    await add_audit_event(session, "conversation.created", actor_user_id=user.id, project_id=project_id)
    await session.commit()
    return ConversationResponse(
        id=conversation.id,
        project_id=conversation.project_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[],
    )


@app.get("/v1/projects/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    result = await session.scalars(
        select(Conversation)
        .where(Conversation.project_id == project_id, Conversation.owner_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return [
        ConversationResponse(
            id=conversation.id,
            project_id=conversation.project_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[],
        )
        for conversation in result.all()
    ]


@app.get("/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conversation = await session.get(Conversation, conversation_id)
    require_owned_conversation(conversation, user)

    messages = await session.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    return ConversationResponse(
        id=conversation.id,
        project_id=conversation.project_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(message) for message in messages.all()],
    )


@app.post(
    "/v1/conversations/{conversation_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(
    conversation_id: str,
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    conversation = await session.get(Conversation, conversation_id)
    require_owned_conversation(conversation, user)
    project = await session.get(Project, conversation.project_id)
    require_owned_project(project, user)

    prompt = payload.prompt.strip()
    task = Task(
        project_id=project.id,
        conversation_id=conversation.id,
        owner_id=user.id,
        prompt=prompt,
        status="queued",
    )
    session.add(task)
    await session.flush()

    session.add(Message(conversation_id=conversation.id, task_id=task.id, role="user", content=prompt))
    await add_task_event(session, task.id, "task.queued", {"status": "queued"})
    await add_audit_event(
        session,
        "task.created",
        actor_user_id=user.id,
        project_id=project.id,
        task_id=task.id,
    )
    await session.commit()

    try:
        await enqueue_task(task.id)
    except Exception as exc:
        # The task is already durable in the database. The worker also sweeps
        # queued tasks, so a temporary Redis outage does not lose the request.
        async with SessionLocal() as audit_session:
            await add_task_event(
                audit_session,
                task.id,
                "task.queue_deferred",
                {"status": "queued", "reason": str(exc)[:1000]},
            )
            await add_audit_event(
                audit_session,
                "task.queue_deferred",
                actor_user_id=user.id,
                project_id=project.id,
                task_id=task.id,
                metadata={"reason": str(exc)[:1000]},
            )
            await audit_session.commit()

    return TaskResponse.model_validate(task)


@app.get("/v1/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    project = await session.get(Project, project_id)
    require_owned_project(project, user)
    result = await session.scalars(
        select(Task).where(Task.project_id == project_id, Task.owner_id == user.id).order_by(Task.created_at.desc())
    )
    return [TaskResponse.model_validate(task) for task in result.all()]


@app.get("/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await session.get(Task, task_id)
    require_owned_task(task, user)
    return TaskResponse.model_validate(task)


@app.post("/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
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

    await add_audit_event(
        session,
        "task.cancel_requested",
        actor_user_id=user.id,
        project_id=task.project_id,
        task_id=task.id,
    )
    await session.commit()
    return TaskResponse.model_validate(task)


@app.get("/v1/tasks/{task_id}/events")
async def task_events(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    last_event_id: int | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    task = await session.get(Task, task_id)
    require_owned_task(task, user)
    starting_id = max(last_event_id or 0, 0)

    async def stream() -> AsyncIterator[str]:
        last_id = starting_id
        keepalive_at = datetime.now(timezone.utc)

        while True:
            async with SessionLocal() as stream_session:
                events = await stream_session.scalars(
                    select(TaskEvent)
                    .where(TaskEvent.task_id == task_id, TaskEvent.id > last_id)
                    .order_by(TaskEvent.id.asc())
                    .limit(100)
                )
                event_rows = events.all()
                current_task = await stream_session.get(Task, task_id)

            sent = False
            for event in event_rows:
                data = json.dumps(
                    TaskEventResponse.model_validate(event).model_dump(mode="json"),
                    separators=(",", ":"),
                )
                yield f"id: {event.id}\nevent: {event.kind}\ndata: {data}\n\n"
                last_id = event.id
                sent = True

            if current_task is None:
                return
            if current_task.status in {"completed", "failed", "cancelled"} and not sent:
                return

            now = datetime.now(timezone.utc)
            if (now - keepalive_at).total_seconds() >= 15:
                yield ": keepalive\n\n"
                keepalive_at = now

            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
