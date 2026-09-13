import asyncio
import time
from typing import Any, Dict, Optional, TypeVar
from uuid import uuid4

from app.daytona.tool_base import Sandbox, SandboxToolsBase
from app.tool.base import ToolResult
from app.utils.logger import logger


Context = TypeVar("Context")
_SHELL_DESCRIPTION = """\
Execute a shell command in the workspace directory.
IMPORTANT: Commands are non-blocking by default and run in a tmux session.
This is ideal for long-running operations like starting servers or build processes.
Uses sessions to maintain state between commands.
This tool is essential for running CLI tools, installing packages, and managing system operations.
"""


class SandboxShellTool(SandboxToolsBase):
    """Tool for executing tasks in a Daytona sandbox with browser-use capabilities."""

    name: str = "sandbox_shell"
    description: str = _SHELL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "execute_command",
                    "check_command_output",
                    "terminate_command",
                    "list_commands",
                ],
                "description": "The shell action to perform",
            },
            "command": {
                "type": "string",
                "description": "Shell command for execute_command.",
            },
            "folder": {"type": "string", "description": "Optional relative folder."},
            "session_name": {"type": "string", "description": "Optional tmux session name."},
            "blocking": {
                "type": "boolean",
                "description": "Whether to wait for completion.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout for blocking commands.",
                "default": 60,
            },
            "kill_session": {
                "type": "boolean",
                "description": "Terminate the session after checking output.",
                "default": False,
            },
        },
        "required": ["action"],
        "dependencies": {
            "execute_command": ["command"],
            "check_command_output": ["session_name"],
            "terminate_command": ["session_name"],
            "list_commands": [],
        },
    }

    def __init__(self, sandbox: Optional[Sandbox] = None, thread_id: Optional[str] = None, **data):
        super().__init__(**data)
        if sandbox is not None:
            self._sandbox = sandbox

    async def _ensure_session(self, session_name: str = "default") -> str:
        if session_name not in self._sessions:
            session_id = str(uuid4())
            await self._ensure_sandbox()
            self.sandbox.process.create_session(session_id)
            self._sessions[session_name] = session_id
        return self._sessions[session_name]

    async def _cleanup_session(self, session_name: str):
        if session_name in self._sessions:
            try:
                await self._ensure_sandbox()
                self.sandbox.process.delete_session(self._sessions[session_name])
                del self._sessions[session_name]
            except Exception as e:
                logger.warning(f"Failed to cleanup session {session_name}: {e}")

    @staticmethod
    def _logs_to_text(logs: Any) -> str:
        if logs is None:
            return ""
        if isinstance(logs, str):
            return logs
        if isinstance(logs, dict):
            for key in ("output", "stdout", "stderr", "logs", "text"):
                value = logs.get(key)
                if value is not None:
                    return str(value)
            return str(logs)
        for attr in ("output", "stdout", "stderr", "logs", "text"):
            value = getattr(logs, attr, None)
            if value is not None:
                return str(value)
        return str(logs)

    async def _execute_raw_command(self, command: str) -> Dict[str, Any]:
        session_id = await self._ensure_session("raw_commands")
        from app.daytona.sandbox import SessionExecuteRequest

        req = SessionExecuteRequest(command=command, run_async=False, cwd=self.workspace_path)
        response = self.sandbox.process.execute_session_command(
            session_id=session_id,
            req=req,
            timeout=30,
        )
        logs = self.sandbox.process.get_session_command_logs(
            session_id=session_id,
            command_id=response.cmd_id,
        )
        return {
            "output": self._logs_to_text(logs),
            "exit_code": getattr(response, "exit_code", None),
        }

    async def _execute_command(
        self,
        command: str,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
    ) -> ToolResult:
        try:
            await self._ensure_sandbox()
            cwd = self.workspace_path
            if folder:
                cwd = f"{cwd}/{folder.strip('/')}"
            if not session_name:
                session_name = f"session_{str(uuid4())[:8]}"

            check_session = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in check_session.get("output", ""):
                await self._execute_raw_command(f"tmux new-session -d -s {session_name}")

            full_command = f"cd {cwd} && {command}"
            wrapped_command = full_command.replace('"', '\\"')
            await self._execute_raw_command(
                f'tmux send-keys -t {session_name} "{wrapped_command}" Enter'
            )

            if not blocking:
                return self.success_response({
                    "session_name": session_name,
                    "cwd": cwd,
                    "message": f"Command sent to tmux session '{session_name}'. Use check_command_output to view results.",
                    "completed": False,
                })

            start_time = time.time()
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(2)
                check_result = await self._execute_raw_command(
                    f"tmux has-session -t {session_name} 2>/dev/null || echo 'ended'"
                )
                if "ended" in check_result.get("output", ""):
                    break
                output_result = await self._execute_raw_command(
                    f"tmux capture-pane -t {session_name} -p -S - -E -"
                )
                current_output = output_result.get("output", "")
                last_lines = current_output.split("\n")[-3:]
                if any(
                    indicator in line
                    for indicator in ("$", "#", ">", "Done", "Completed", "Finished", "✓")
                    for line in last_lines
                ):
                    break

            output_result = await self._execute_raw_command(
                f"tmux capture-pane -t {session_name} -p -S - -E -"
            )
            final_output = output_result.get("output", "")
            await self._execute_raw_command(f"tmux kill-session -t {session_name}")
            return self.success_response({
                "output": final_output,
                "session_name": session_name,
                "cwd": cwd,
                "completed": True,
            })
        except Exception as e:
            if session_name:
                try:
                    await self._execute_raw_command(f"tmux kill-session -t {session_name}")
                except Exception:
                    pass
            return self.fail_response(f"Error executing command: {str(e)}")

    async def _check_command_output(self, session_name: str, kill_session: bool = False) -> ToolResult:
        try:
            await self._ensure_sandbox()
            check_result = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in check_result.get("output", ""):
                return self.fail_response(f"Tmux session '{session_name}' does not exist.")
            output_result = await self._execute_raw_command(
                f"tmux capture-pane -t {session_name} -p -S - -E -"
            )
            output = output_result.get("output", "")
            if kill_session:
                await self._execute_raw_command(f"tmux kill-session -t {session_name}")
                status = "Session terminated."
            else:
                status = "Session still running."
            return self.success_response({"output": output, "session_name": session_name, "status": status})
        except Exception as e:
            return self.fail_response(f"Error checking command output: {str(e)}")

    async def _terminate_command(self, session_name: str) -> ToolResult:
        try:
            await self._ensure_sandbox()
            check_result = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in check_result.get("output", ""):
                return self.fail_response(f"Tmux session '{session_name}' does not exist.")
            await self._execute_raw_command(f"tmux kill-session -t {session_name}")
            return self.success_response({"message": f"Tmux session '{session_name}' terminated successfully."})
        except Exception as e:
            return self.fail_response(f"Error terminating command: {str(e)}")

    async def _list_commands(self) -> ToolResult:
        try:
            await self._ensure_sandbox()
            result = await self._execute_raw_command("tmux list-sessions 2>/dev/null || echo 'No sessions'")
            output = result.get("output", "")
            if "No sessions" in output or not output.strip():
                return self.success_response({"message": "No active tmux sessions found.", "sessions": []})
            sessions = [line.split(":")[0].strip() for line in output.split("\n") if line.strip()]
            return self.success_response({"message": f"Found {len(sessions)} active sessions.", "sessions": sessions})
        except Exception as e:
            return self.fail_response(f"Error listing commands: {str(e)}")

    async def execute(
        self,
        action: str,
        command: Optional[str] = None,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
        kill_session: bool = False,
    ) -> ToolResult:
        try:
            if action == "execute_command":
                if not command:
                    return self.fail_response("command is required for execute_command")
                return await self._execute_command(command, folder, session_name, blocking, timeout)
            if action == "check_command_output":
                if session_name is None:
                    return self.fail_response("session_name is required for check_command_output")
                return await self._check_command_output(session_name, kill_session)
            if action == "terminate_command":
                if session_name is None:
                    return self.fail_response("session_name is required for terminate_command")
                return await self._terminate_command(session_name)
            if action == "list_commands":
                return await self._list_commands()
            return self.fail_response(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error executing shell action: {e}")
            return self.fail_response(f"Error executing shell action: {e}")

    async def cleanup(self):
        for session_name in list(self._sessions.keys()):
            await self._cleanup_session(session_name)
        try:
            await self._ensure_sandbox()
            await self._execute_raw_command("tmux kill-server 2>/dev/null || true")
        except Exception as e:
            logger.error(f"Error shell box cleanup action: {e}")
