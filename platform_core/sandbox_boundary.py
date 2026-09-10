from fnmatch import fnmatchcase


HOST_EXECUTION_PATTERNS = ("bash", "computer_use*", "docker*")
SANDBOX_PATTERNS = ("sandbox*",)


class SandboxBoundaryDenied(PermissionError):
    pass


def enforce_tool_boundary(tool_name: str, *, sandbox_enabled: bool) -> None:
    lowered = tool_name.lower()
    if any(fnmatchcase(lowered, pattern.lower()) for pattern in HOST_EXECUTION_PATTERNS):
        raise SandboxBoundaryDenied(
            f"Host execution tool '{tool_name}' is blocked by the platform execution boundary"
        )
    if any(fnmatchcase(lowered, pattern.lower()) for pattern in SANDBOX_PATTERNS) and not sandbox_enabled:
        raise SandboxBoundaryDenied(
            f"Sandbox tool '{tool_name}' is disabled; enable an isolated sandbox worker before use"
        )
