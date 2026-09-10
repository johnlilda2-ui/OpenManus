import pytest

from platform_core.permissions import ROLE_ORDER
from platform_core.policy import PolicyDenied, ToolApprovalRequired, ToolPolicy
from platform_core.rate_limit import RateLimitExceeded, check_rate_limit
from platform_core.sandbox_boundary import SandboxBoundaryDenied, enforce_tool_boundary
from platform_core.secrets import resolve_config_secret
from platform_core.usage import estimate_cost, estimate_tokens


def test_default_policy_blocks_host_tools():
    policy = ToolPolicy.defaults()
    with pytest.raises(PolicyDenied):
        policy.authorize("bash")


def test_sandbox_tools_require_approval():
    policy = ToolPolicy.defaults()
    with pytest.raises(ToolApprovalRequired):
        policy.authorize("sandbox_shell")


def test_host_execution_boundary():
    with pytest.raises(SandboxBoundaryDenied):
        enforce_tool_boundary("docker_exec", sandbox_enabled=True)


def test_usage_estimation_is_deterministic():
    assert estimate_tokens("12345678") == 2
    assert estimate_cost(1000, 1000) > 0


def test_role_order_is_monotonic():
    assert ROLE_ORDER["viewer"] < ROLE_ORDER["member"] < ROLE_ORDER["admin"] < ROLE_ORDER["owner"]


def test_non_secret_config_value_is_unchanged():
    assert resolve_config_secret("plain-value") == "plain-value"


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.ttls = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, ttl):
        self.ttls[key] = ttl
        return True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit():
    redis = FakeRedis()
    await check_rate_limit(redis, key="test-user", limit=2, window_seconds=60)
    await check_rate_limit(redis, key="test-user", limit=2, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit(redis, key="test-user", limit=2, window_seconds=60)
