from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Iterable


class PolicyDenied(PermissionError):
    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool '{tool_name}' denied by platform policy: {reason}")


class ToolApprovalRequired(PolicyDenied):
    def __init__(self, tool_name: str):
        super().__init__(tool_name, "human approval is required before this tool can execute")


@dataclass(frozen=True)
class ToolPolicy:
    allowed_tool_patterns: tuple[str, ...]
    denied_tool_patterns: tuple[str, ...]
    approval_required_patterns: tuple[str, ...]

    @classmethod
    def defaults(cls) -> "ToolPolicy":
        return cls(
            allowed_tool_patterns=(
                "terminate", "planning", "python_execute", "str_replace_editor", "ask_human",
                "web_search", "crawl4ai", "create_chat_completion", "browser_*",
            ),
            denied_tool_patterns=("bash", "computer_use*", "docker*"),
            approval_required_patterns=("sandbox*",),
        )

    @classmethod
    def from_model(cls, policy_model) -> "ToolPolicy":
        if policy_model is None:
            return cls.defaults()
        return cls(
            allowed_tool_patterns=tuple(policy_model.allowed_tool_patterns or ()),
            denied_tool_patterns=tuple(policy_model.denied_tool_patterns or ()),
            approval_required_patterns=tuple(policy_model.approval_required_patterns or ()),
        )

    @staticmethod
    def matches(tool_name: str, patterns: Iterable[str]) -> bool:
        return any(
            fnmatchcase(tool_name, pattern) or fnmatchcase(tool_name.lower(), pattern.lower())
            for pattern in patterns
        )

    def authorize(self, tool_name: str, *, approved: bool = False) -> None:
        if self.matches(tool_name, self.denied_tool_patterns):
            raise PolicyDenied(tool_name, "explicitly denied")
        if self.matches(tool_name, self.approval_required_patterns) and not approved:
            raise ToolApprovalRequired(tool_name)
        if self.allowed_tool_patterns and not self.matches(tool_name, self.allowed_tool_patterns) and not approved:
            raise PolicyDenied(tool_name, "not present in the project allowlist")


class PolicyToolBroker:
    def __init__(self, policy: ToolPolicy):
        self.policy = policy

    def authorize(self, tool_name: str, *, approved: bool = False) -> None:
        self.policy.authorize(tool_name, approved=approved)
