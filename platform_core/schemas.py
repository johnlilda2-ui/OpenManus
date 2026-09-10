from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    is_active: bool
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    allowed_tool_patterns: list[str]
    denied_tool_patterns: list[str]
    approval_required_patterns: list[str]
    version: int
    created_at: datetime
    updated_at: datetime


class ProjectPolicyUpdate(BaseModel):
    allowed_tool_patterns: list[str] = Field(default_factory=list)
    denied_tool_patterns: list[str] = Field(default_factory=list)
    approval_required_patterns: list[str] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    task_id: str | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)


class TaskCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=50000)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    conversation_id: str | None
    prompt: str
    status: str
    result: str | None
    error: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TaskEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: str
    kind: str
    payload: dict
    created_at: datetime


class MemoryCreate(BaseModel):
    kind: str = Field(default="note", min_length=1, max_length=64)
    key: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    importance: int = Field(default=50, ge=0, le=100)
    metadata_json: dict = Field(default_factory=dict)


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str | None
    kind: str
    key: str | None
    content: str
    metadata_json: dict
    importance: int
    created_at: datetime
    updated_at: datetime


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=100000)
    source: str | None = Field(default=None, max_length=1000)
    metadata_json: dict = Field(default_factory=dict)


class KnowledgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    content: str
    source: str | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class WorkflowStepSpec(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=50000)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    steps: list[WorkflowStepSpec] = Field(min_length=1, max_length=50)


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    description: str | None
    steps: list[WorkflowStepSpec]
    created_at: datetime
    updated_at: datetime


class WorkflowRunCreate(BaseModel):
    input: str = Field(min_length=1, max_length=50000)


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workflow_id: str
    project_id: str
    input: str
    status: str
    current_step: int
    output: str | None
    error: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class WorkflowStepRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    step_index: int
    name: str
    prompt: str
    status: str
    result: str | None
    error: str | None
    attempt: int
    started_at: datetime | None
    completed_at: datetime | None


class WorkflowRunDetailResponse(WorkflowRunResponse):
    steps: list[WorkflowStepRunResponse] = Field(default_factory=list)


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workflow_run_id: str
    kind: str
    payload: dict
    created_at: datetime
