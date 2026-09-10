import os
from pathlib import Path

from platform_core.settings import settings


class SecretNotFound(RuntimeError):
    pass


def get_secret(name: str, *, required: bool = True) -> str | None:
    """Resolve a secret without persisting or logging its value."""
    if name.startswith("/"):
        candidates = [Path(name)]
        normalized = Path(name).name
        env_name = f"OPENMANUS_SECRET_{normalized.upper().replace('-', '_')}"
    else:
        normalized = name.removeprefix(settings.api_key_secret_prefix).strip()
        candidates = [Path("/run/secrets") / normalized, Path("/run/secrets") / normalized.lower()]
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
