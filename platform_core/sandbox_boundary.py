HOST_EXECUTION_PATTERNS = ("bash", "python_execute", "computer_use*", "docker*")
SANDBOX_PATTERNS = ("sandbox*",)


class SandboxBoundaryDenied(PermissionError):
    pass


def _matches(tool_name: str, patterns: tuple[str, ...]) -> bool:
    from fnmatch import fnmatchcase
    return any(fnmatchcase(tool_name, pattern) or fnmatchcase(tool_name.lower(), pattern.lower()) for pattern in patterns)


def enforce_tool_boundary(tool_name: str, *, sandbox_enabled: bool) -> None:
    """Prevent host-side execution of powerful tools; permit them only inside an isolated backend."""
    if _matches(tool_name, HOST_EXECUTION_PATTERNS):
        raise SandboxBoundaryDenied(f"Host execution tool '{tool_name}' is blocked by the platform boundary")
    if _matches(tool_name, SANDBOX_PATTERNS) and not sandbox_enabled:
        raise SandboxBoundaryDenied(f"Sandbox tool '{tool_name}' requires an isolated sandbox backend")
