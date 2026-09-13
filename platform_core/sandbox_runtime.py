from pydantic import Field

from app.agent.sandbox_agent import SandboxManus
from app.tool.sandbox.sb_preview_tool import SandboxPreviewTool
from app.tool.sandbox.sb_visual_browser_tool import SandboxVisualBrowserTool
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch

from platform_core.policy import PolicyToolBroker, ToolPolicy
from platform_core.sandbox_boundary import enforce_tool_boundary
from platform_core.settings import settings


class PolicySandboxManus(SandboxManus):
    policy_broker: PolicyToolBroker = Field(default_factory=lambda: PolicyToolBroker(ToolPolicy.defaults()))
    approved_tools: set[str] = Field(default_factory=set)

    @classmethod
    async def create(cls, **kwargs) -> "PolicySandboxManus":
        instance = await super().create(**kwargs)

        # The builder prompts historically used the host-style workspace path
        # (for example /app/workspace). In Daytona that path does not exist;
        # the isolated sandbox workspace is /workspace. Create the shared
        # project root up front and make the runtime contract explicit so all
        # sandbox tools operate on the same filesystem.
        try:
            from daytona import SessionExecuteRequest

            bootstrap_session = "cataron-workspace-bootstrap"
            instance.sandbox.process.create_session(bootstrap_session)
            response = instance.sandbox.process.execute_session_command(
                bootstrap_session,
                SessionExecuteRequest(
                    command="mkdir -p /workspace/projects",
                    run_async=False,
                    cwd="/workspace",
                ),
                timeout=30,
            )
            if getattr(response, "exit_code", 0) not in {0, None}:
                raise RuntimeError("Unable to initialize the Daytona workspace root")
            instance.system_prompt = (
                instance.system_prompt
                + "\n\nCATARON SANDBOX RUNTIME: This task runs inside an isolated Daytona sandbox. "
                "The writable project root is /workspace/projects. Always use /workspace/projects "
                "for the current project. Never use /app/workspace or the host filesystem."
            )
        except Exception:
            # Sandbox creation itself remains authoritative; a clear runtime
            # error will be produced if the workspace cannot be initialized.
            raise

        tools = [
            tool
            for tool in instance.available_tools.tools
            if tool.name not in {"sandbox_browser", "ask_human"}
        ]
        instance.available_tools = ToolCollection(*tools)
        instance.available_tools.add_tools(
            SandboxVisualBrowserTool.create_with_sandbox(instance.sandbox),
            SandboxPreviewTool.create_with_sandbox(instance.sandbox),
            WebSearch(),
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
