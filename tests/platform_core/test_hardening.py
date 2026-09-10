from platform_core.policy import PolicyDenied, ToolApprovalRequired, ToolPolicy
from platform_core.sandbox_boundary import SandboxBoundaryDenied, enforce_tool_boundary
from platform_core.usage import estimate_cost, estimate_tokens


def test_default_policy_blocks_host_tools():
    policy = ToolPolicy.defaults()
    try:
        policy.authorize("bash")
    except PolicyDenied:
        pass
    else:
        raise AssertionError("bash must be denied")


def test_sandbox_tools_require_approval():
    policy = ToolPolicy.defaults()
    try:
        policy.authorize("sandbox_shell")
    except ToolApprovalRequired:
        pass
    else:
        raise AssertionError("sandbox tools must require approval")


def test_host_execution_boundary():
    try:
        enforce_tool_boundary("docker_exec", sandbox_enabled=True)
    except SandboxBoundaryDenied:
        pass
    else:
        raise AssertionError("docker execution must remain blocked")


def test_usage_estimation_is_deterministic():
    assert estimate_tokens("12345678") == 2
    assert estimate_cost(1000, 1000) > 0
