from app.agent.sandbox_agent import SandboxManus
from pydantic import Field

from platform_core.policy import PolicyToolBroker, ToolPolicy
from platform_core.sandbox_boundary import enforce_tool_boundary
from platform_core.settings import settings


class PolicySandboxManus(SandboxManus):
    policy_broker: PolicyToolBroker = Field(default_factory=lambda: PolicyToolBroker(ToolPolicy.defaults()))

    async def execute_tool(self, command):
        enforce_tool_boundary(command.function.name, sandbox_enabled=True)
        self.policy_broker.authorize(command.function.name)
        return await super().execute_tool(command)


async def create_platform_agent(policy: ToolPolicy):
    if settings.sandbox_enabled:
        if settings.sandbox_backend != "daytona":
            raise RuntimeError("Sandbox execution is enabled but no supported isolated backend is configured")
        return await PolicySandboxManus.create(policy_broker=PolicyToolBroker(policy))
    from platform_core.worker import PolicyManus
    return await PolicyManus.create(policy_broker=PolicyToolBroker(policy))
