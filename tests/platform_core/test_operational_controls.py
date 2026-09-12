import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from platform_core.approvals import create_or_get_workflow_approval
from platform_core.database import Base
from platform_core.models import Project, Tenant, TenantMember, User, Workflow, WorkflowRun
from platform_core.policy import ToolPolicy
from platform_core.schemas import ApprovalResponse
from platform_core.tenant_api import list_members
from platform_core import worker


@pytest.mark.asyncio
async def test_list_members_returns_joined_user_rows():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with Session() as session:
        owner = User(email="owner@example.com", password_hash="hash-owner")
        member = User(email="member@example.com", password_hash="hash-member")
        tenant = Tenant(name="Project")
        session.add_all([owner, member, tenant])
        await session.flush()
        project = Project(owner_id=owner.id, tenant_id=tenant.id, name="Project")
        session.add(project)
        await session.flush()
        session.add_all(
            [
                TenantMember(tenant_id=tenant.id, user_id=owner.id, role="owner"),
                TenantMember(tenant_id=tenant.id, user_id=member.id, role="member"),
            ]
        )
        await session.commit()

        rows = await list_members(project.id, user=owner, session=session)

    assert rows == [
        {"user_id": member.id, "email": member.email, "role": "member"},
        {"user_id": owner.id, "email": owner.email, "role": "owner"},
    ]
    await engine.dispose()


class SlowAgent:
    def __init__(self) -> None:
        self.cancelled = False
        self.llm = type("LLM", (), {"total_input_tokens": 0, "total_completion_tokens": 0})()

    async def run(self, _prompt: str) -> str:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return "unexpected"


@pytest.mark.asyncio
async def test_running_agent_can_be_interrupted(monkeypatch):
    agent = SlowAgent()
    checks = 0

    async def fake_cancel_requested(_task_id: str) -> bool:
        nonlocal checks
        checks += 1
        return checks >= 1

    monkeypatch.setattr(worker, "_cancel_requested", fake_cancel_requested)

    with pytest.raises(worker._CancellationRequested):
        await worker._run_agent_with_cancellation(agent, "do work", "task-1")

    assert agent.cancelled is True


@pytest.mark.asyncio
async def test_ci_fake_agent_can_execute_without_provider_credentials(monkeypatch):
    monkeypatch.setenv("PLATFORM_CORE_CI_FAKE_LLM", "true")
    agent = await worker.create_agent(ToolPolicy.defaults(), set())
    result = await agent.run("test request")
    assert result.startswith("CI fake agent completed:")
    assert agent.llm.total_input_tokens > 0
    await agent.cleanup()


@pytest.mark.asyncio
async def test_workflow_approval_can_target_builder_run():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with Session() as session:
        owner = User(email="builder@example.com", password_hash="hash")
        tenant = Tenant(name="Builder Project")
        session.add_all([owner, tenant])
        await session.flush()
        project = Project(owner_id=owner.id, tenant_id=tenant.id, name="Builder Project")
        session.add(project)
        await session.flush()
        workflow = Workflow(
            owner_id=owner.id,
            project_id=project.id,
            name="Build",
            description=None,
            steps_json=[{"name": "Build", "prompt": "Build it", "role": "builder"}],
        )
        session.add(workflow)
        await session.flush()
        run = WorkflowRun(
            workflow_id=workflow.id,
            owner_id=owner.id,
            project_id=project.id,
            input="Build it",
            status="builder_awaiting_approval",
        )
        session.add(run)
        await session.flush()

        approval = await create_or_get_workflow_approval(
            session,
            workflow_run_id=run.id,
            project_id=project.id,
            tool_name="sandbox_shell",
            reason="Sandbox execution needs approval",
        )
        await session.commit()

        response = ApprovalResponse.model_validate(approval)
        assert response.task_id is None
        assert response.workflow_run_id == run.id
        assert response.status == "pending"

    await engine.dispose()
