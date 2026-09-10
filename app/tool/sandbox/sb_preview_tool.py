from typing import Optional

from app.daytona.tool_base import Sandbox, SandboxToolsBase
from app.tool.base import ToolResult


class SandboxPreviewTool(SandboxToolsBase):
    """Expose a safe Daytona preview URL for a port already running in the sandbox."""

    name: str = "sandbox_preview"
    description: str = (
        "Get the browser-accessible preview URL for a port running inside the current "
        "isolated sandbox. Use after starting the project's development server."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "port": {
                "type": "integer",
                "minimum": 1,
                "maximum": 65535,
                "description": "TCP port used by the application's preview server",
            }
        },
        "required": ["port"],
    }

    def __init__(
        self, sandbox: Optional[Sandbox] = None, thread_id: Optional[str] = None, **data
    ):
        super().__init__(**data)
        if sandbox is not None:
            self._sandbox = sandbox

    async def execute(self, port: int, **kwargs) -> ToolResult:
        if not 1 <= int(port) <= 65535:
            return self.fail_response("Port must be between 1 and 65535")
        await self._ensure_sandbox()
        preview = self.sandbox.get_preview_link(int(port))
        url = preview.url if hasattr(preview, "url") else str(preview)
        return self.success_response(
            {
                "port": int(port),
                "url": url,
                "message": "Preview URL ready. Keep the application process running while testing.",
            }
        )

    @classmethod
    def create_with_sandbox(cls, sandbox: Sandbox) -> "SandboxPreviewTool":
        return cls(sandbox=sandbox)
