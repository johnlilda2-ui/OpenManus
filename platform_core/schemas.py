from datetime import datetime
from typing import Literal

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
    allowed_tool_patterns: list[str] = Field(min_length=1, max_length=100)
    denied_tool_patterns: list[str] = Field(default_factory=list, max_length=100)
    approval_required_patterns: list[str] = Field(default_factory=list, max_length=100)


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    project_id: str
    tool_name: str
    reason: str
    status: str
    decided_by: str | None
    requested_at: datetime
    decided_at: datetime | None


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
    role: str = Field(default="builder", min_length=1, max_length=64)
    model_profile: str | None = Field(default=None, max_length=100)
    max_attempts: int = Field(default=1, ge=1, le=10)
    browser_required: bool = False


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


class AppBuilderCreate(BaseModel):
    requirements: str = Field(min_length=20, max_length=100000)
    name: str = Field(default="AI App Builder", min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    mode: Literal["app", "website"] = "app"


class AppBuilderResponse(BaseModel):
    workflow: WorkflowResponse
    run_id: str
    status: str
    workspace: str
    mode: Literal["app", "website"]


class WebsiteIterationCreate(BaseModel):
    section_id: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=5, max_length=10000)


class WebsiteSectionResponse(BaseModel):
    section_id: str
    page: str
    name: str
    anchor: str | None = None
    selector: str | None = None
    description: str | None = None
    sort_order: int = 0


class WebsiteExperienceResponse(BaseModel):
    mode: Literal["website"] = "website"
    run_id: str
    status: str
    workspace: str
    sections: list[WebsiteSectionResponse] = Field(default_factory=list)
    design_system: dict = Field(default_factory=dict)
    assets: list[dict] = Field(default_factory=list)
    visual_score: float | None = None


class VisualScoreResponse(BaseModel):
    run_id: str
    status: str
    score: float | None
    baseline_hash: str | None = None
    current_hash: str | None = None
    url: str | None = None


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


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    task_id: str | None
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    download_url: str


class ProjectQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: str
    monthly_token_limit: int
    monthly_task_limit: int
    max_concurrent_tasks: int
    hard_block: bool


class ProjectQuotaUpdate(BaseModel):
    monthly_token_limit: int = Field(ge=1, le=1000000000)
    monthly_task_limit: int = Field(ge=1, le=10000000)
    max_concurrent_tasks: int = Field(ge=1, le=1000)
    hard_block: bool = True


class UsageSummaryResponse(BaseModel):
    project_id: str
    tokens: int
    tasks: int
    concurrent: int
