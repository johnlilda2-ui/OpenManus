from __future__ import annotations

import os
from dataclasses import dataclass

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
    normalized_role = (role or "builder").strip().lower()
    if normalized_role not in SUPPORTED_ROLES:
        normalized_role = "builder"

    configured = _configured_names()
    requested = (requested_profile or "").strip().lower()
    env_profile = os.getenv(f"{ROLE_ENV_PREFIX}{normalized_role.upper()}", "").strip().lower()
    candidate = requested or env_profile or normalized_role

    if candidate not in configured:
        candidate = "default" if "default" in configured else next(iter(configured))

    return ModelProfile(role=normalized_role, config_name=candidate)


def create_llm(role: str = "builder", requested_profile: str | None = None) -> LLM:
    profile = resolve_profile(role, requested_profile)
    return LLM(config_name=profile.config_name)


def available_profiles() -> list[str]:
    return sorted(_configured_names())
