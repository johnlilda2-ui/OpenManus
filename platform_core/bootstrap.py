from app.config import config

from platform_core.secrets import resolve_config_secret


def resolve_runtime_secrets() -> None:
    """Resolve secret:// references in loaded OpenManus config without logging values."""
    app_config = getattr(config, "_config", None)
    if app_config is None:
        return
    for llm_settings in app_config.llm.values():
        llm_settings.api_key = resolve_config_secret(llm_settings.api_key) or llm_settings.api_key
    daytona = getattr(app_config, "daytona_config", None)
    if daytona is not None:
        daytona.daytona_api_key = resolve_config_secret(daytona.daytona_api_key) or daytona.daytona_api_key
        if getattr(daytona, "VNC_password", None):
            daytona.VNC_password = resolve_config_secret(daytona.VNC_password) or daytona.VNC_password
