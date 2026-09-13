from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from app.config import config
from app.llm import LLM


@dataclass(frozen=True)
class ModelProfile:
    role: str
    config_name: str


ROLE_ENV_PREFIX = "OPENMANUS_MODEL_"
SUPPORTED_ROLES = (
    "planner",
    "builder",
    "designer",
    "tester",
    "fixer",
    "reviewer",
)


def _configured_names() -> set[str]:
    return set(config.llm.keys())


def resolve_profile(role: str, requested_profile: str | None = None) -> ModelProfile:
    raw_role = (role or "builder").strip().lower()
    if raw_role == "default":
        return ModelProfile(role="default", config_name="default")
    normalized_role = raw_role if raw_role in SUPPORTED_ROLES else "builder"

    configured = _configured_names()
    requested = (requested_profile or "").strip().lower()
    env_profile = os.getenv(f"{ROLE_ENV_PREFIX}{normalized_role.upper()}", "").strip().lower()
    candidate = requested or env_profile or normalized_role

    if candidate not in configured:
        candidate = "default" if "default" in configured else next(iter(configured))

    return ModelProfile(role=normalized_role, config_name=candidate)


def _message_text(messages: Iterable[Any]) -> str:
    parts: list[str] = []
    for message in messages or []:
        role = getattr(message, "role", None)
        if role not in {None, "user"}:
            continue
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            if message.get("role") not in {None, "user"}:
                continue
            content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
    return "\n".join(parts)


def _should_escalate(messages: Iterable[Any]) -> bool:
    text = _message_text(messages)
    lowered = text.lower()
    threshold = int(os.getenv("OPENMANUS_ESCALATION_MAX_INPUT_CHARS", "100000"))
    critical_terms = (
        "data loss",
        "critical incident",
        "incident response",
        "deploy to production",
    )
    return len(text) >= threshold or any(term in lowered for term in critical_terms)


class RoutedLLM(LLM):
    """LLM-compatible router that uses the configured specialist first and escalates once."""

    def __new__(cls, primary: LLM, escalation: LLM):
        return object.__new__(cls)

    def __init__(self, primary: LLM, escalation: LLM):
        self._primary = primary
        self._escalation = escalation
        self._active = primary
        self._escalated = False

    @property
    def model(self) -> str:
        return self._active.model

    @property
    def total_input_tokens(self) -> int:
        return int(getattr(self._primary, "total_input_tokens", 0)) + int(
            getattr(self._escalation, "total_input_tokens", 0)
        )

    @property
    def total_completion_tokens(self) -> int:
        return int(getattr(self._primary, "total_completion_tokens", 0)) + int(
            getattr(self._escalation, "total_completion_tokens", 0)
        )

    @property
    def escalated(self) -> bool:
        return self._escalated

    def __getattr__(self, name: str):
        return getattr(self._active, name)

    def _activate_escalation(self, reason: str) -> None:
        if self._escalated:
            return
        self._active = self._escalation
        self._escalated = True
        from app.logger import logger

        logger.warning(
            "Cataron model escalation: %s -> %s (%s)",
            self._primary.model,
            self._escalation.model,
            reason,
        )

    async def ask(self, messages, system_msgs=None, stream=True, temperature=None):
        if os.getenv("OPENMANUS_ESCALATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}:
            if not self._escalated and _should_escalate(messages):
                self._activate_escalation("critical_or_complex_request")
        if self._escalated:
            return await self._escalation.ask(messages, system_msgs=system_msgs, stream=stream, temperature=temperature)
        try:
            return await self._primary.ask(messages, system_msgs=system_msgs, stream=stream, temperature=temperature)
        except Exception:
            self._activate_escalation("primary_model_failure")
            return await self._escalation.ask(messages, system_msgs=system_msgs, stream=stream, temperature=temperature)

    async def ask_tool(self, *args, **kwargs):
        messages = kwargs.get("messages") if "messages" in kwargs else (args[0] if args else [])
        if os.getenv("OPENMANUS_ESCALATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}:
            if not self._escalated and _should_escalate(messages):
                self._activate_escalation("critical_or_complex_request")
        if self._escalated:
            return await self._escalation.ask_tool(*args, **kwargs)
        try:
            return await self._primary.ask_tool(*args, **kwargs)
        except Exception:
            self._activate_escalation("primary_model_failure")
            return await self._escalation.ask_tool(*args, **kwargs)


def create_llm(role: str = "builder", requested_profile: str | None = None) -> LLM:
    profile = resolve_profile(role, requested_profile)
    primary = LLM(config_name=profile.config_name)

    enabled = os.getenv("OPENMANUS_ESCALATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    escalation_model = os.getenv("OPENMANUS_ESCALATION_MODEL", "").strip()
    if not enabled or not escalation_model or profile.config_name == "__cataron_escalation__":
        return primary

    base_settings = config.llm.get(profile.config_name, config.llm["default"])
    escalation_settings = base_settings.model_copy(update={"model": escalation_model})
    escalation = LLM(
        config_name="__cataron_escalation__",
        llm_config={"__cataron_escalation__": escalation_settings, "default": base_settings},
    )
    return RoutedLLM(primary, escalation)


def available_profiles() -> list[str]:
    return sorted(_configured_names())
