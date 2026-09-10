from app.config import config

from platform_core.secrets import resolve_config_secret


def resolve_runtime_secrets() -> None:
    """Resolve secret:// references in loaded OpenManus config without persisting values."""
    app_config = getattr(config, "_config", None)
    if app_config is None:
        return
    for settings_obj in app_config.llm.values():
        settings_obj.api_key = resolve_config_secret(settings_obj.api_key) or settings_obj.api_key
    daytona = getattr(app_config, "daytona_config", None)
    if daytona is not None and getattr(daytona, "daytona_api_key", None):
        daytona.daytona_api_key = resolve_config_secret(daytona.daytona_api_key) or daytona.daytona_api_key
