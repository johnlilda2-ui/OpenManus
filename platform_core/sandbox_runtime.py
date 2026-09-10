from pydantic import Field

from app.agent.sandbox_agent import SandboxManus
from app.tool.sandbox.sb_preview_tool import SandboxPreviewTool
from app.tool.sandbox.sb_visual_browser_tool import SandboxVisualBrowserTool
from app.tool.tool_collection import ToolCollection

from platform_core.policy import PolicyToolBroker, ToolPolicy
from platform_core.sandbox_boundary import enforce_tool_boundary
from platform_core.settings import settings


class PolicySandboxManus(SandboxManus):
    policy_broker: PolicyToolBroker = Field(default_factory=lambda: PolicyToolBroker(ToolPolicy.defaults()))
    approved_tools: set[str] = Field(default_factory=set)

    @classmethod
    async def create(cls, **kwargs) -> "PolicySandboxManus":
        instance = await super().create(**kwargs)
        tools = [tool for tool in instance.available_tools.tools if tool.name != "sandbox_browser"]
        instance.available_tools = ToolCollection(*tools)
        instance.available_tools.add_tools(
            SandboxVisualBrowserTool.create_with_sandbox(instance.sandbox),
            SandboxPreviewTool.create_with_sandbox(instance.sandbox),
        )
        return instance

    async def execute_tool(self, command):
        tool_name = command.function.name
        enforce_tool_boundary(tool_name, sandbox_enabled=True)
        self.policy_broker.authorize(tool_name, approved=tool_name in self.approved_tools)
        return await super().execute_tool(command)


async def create_platform_agent(policy: ToolPolicy, approved_tools: set[str] | None = None):
    approved = approved_tools or set()
    if settings.sandbox_enabled:
        if settings.sandbox_backend != "daytona":
            raise RuntimeError("Sandbox execution is enabled but no supported isolated backend is configured")
        return await PolicySandboxManus.create(policy_broker=PolicyToolBroker(policy), approved_tools=approved)
    from platform_core.worker import PolicyManus
    return await PolicyManus.create(policy_broker=PolicyToolBroker(policy), approved_tools=approved)
