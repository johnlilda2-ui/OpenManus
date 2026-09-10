import os
from pathlib import Path

from platform_core.settings import settings


class SecretNotFound(RuntimeError):
    pass


def get_secret(name: str, *, required: bool = True) -> str | None:
    """Resolve a secret from Docker/Kubernetes secret files, then environment.

    Never writes secrets to the database or logs them. A config value like
    `secret://openai_api_key` can be resolved through this function.
    """
    normalized = name.removeprefix(settings.api_key_secret_prefix).strip()
    candidates = []
    if normalized:
        candidates.append(Path("/run/secrets") / normalized)
        candidates.append(Path("/run/secrets") / normalized.lower())
        candidates.append(Path("/run/secrets") / normalized.upper())
    env_name = f"OPENMANUS_SECRET_{normalized.upper().replace('-', '_')}"
    value = os.getenv(env_name)
    if value:
        return value.strip()
    for path in candidates:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    if required:
        raise SecretNotFound(f"Secret '{normalized}' is not configured")
    return None


def resolve_config_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(settings.api_key_secret_prefix):
        return get_secret(value)
    return value
