import time

from daytona import (
    CreateSandboxFromImageParams,
    Daytona,
    DaytonaConfig,
    Resources,
    Sandbox,
    SandboxState,
    SessionExecuteRequest,
)

from app.config import config
from app.utils.logger import logger
from platform_core.secrets import resolve_config_secret


daytona_settings = config.daytona
# Resolve secret:// references before the SDK client is constructed.
daytona_api_key = resolve_config_secret(daytona_settings.daytona_api_key)
daytona_config = DaytonaConfig(
    api_key=daytona_api_key,
    server_url=daytona_settings.daytona_server_url,
    target=daytona_settings.daytona_target,
)

if daytona_config.api_key:
    logger.info("Daytona API key configured successfully")
else:
    logger.warning("No Daytona API key configured")

if daytona_config.server_url:
    logger.info("Daytona server URL configured")

if daytona_config.target:
    logger.info("Daytona target configured")

daytona = Daytona(daytona_config)


async def get_or_start_sandbox(sandbox_id: str):
    """Retrieve a sandbox by ID, check its state, and start it if needed."""
    try:
        sandbox = daytona.get(sandbox_id)
        if sandbox.state in {SandboxState.ARCHIVED, SandboxState.STOPPED}:
            daytona.start(sandbox)
            sandbox = daytona.get(sandbox_id)
            start_supervisord_session(sandbox)
        return sandbox
    except Exception as exc:
        logger.error(f"Error retrieving or starting sandbox: {exc}")
        raise


def start_supervisord_session(sandbox: Sandbox):
    """Start supervisord in a session."""
    session_id = "supervisord-session"
    try:
        sandbox.process.create_session(session_id)
        sandbox.process.execute_session_command(
            session_id,
            SessionExecuteRequest(
                command="exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
                run_async=True,
            ),
        )
        time.sleep(5)
    except Exception as exc:
        logger.error(f"Error starting supervisord session: {exc}")
        raise


def create_sandbox(password: str | None = None, project_id: str | None = None):
    """Create a private Daytona sandbox for isolated agent execution."""
    labels = {"project_id": project_id} if project_id else None
    resolved_password = resolve_config_secret(password or daytona_settings.VNC_password) or ""
    if not resolved_password:
        raise ValueError("A VNC password must be configured for sandbox access")

    params = CreateSandboxFromImageParams(
        image=daytona_settings.sandbox_image_name,
        public=False,
        labels=labels,
        env_vars={
            "CHROME_PERSISTENT_SESSION": "true",
            "RESOLUTION": "1024x768x24",
            "RESOLUTION_WIDTH": "1024",
            "RESOLUTION_HEIGHT": "768",
            "VNC_PASSWORD": resolved_password,
            "ANONYMIZED_TELEMETRY": "false",
            "CHROME_PATH": "",
            "CHROME_USER_DATA": "",
            "CHROME_DEBUGGING_PORT": "9222",
            "CHROME_DEBUGGING_HOST": "localhost",
            "CHROME_CDP": "",
        },
        resources=Resources(cpu=2, memory=4, disk=5),
        auto_stop_interval=15,
        auto_archive_interval=24 * 60,
    )
    sandbox = daytona.create(params)
    start_supervisord_session(sandbox)
    return sandbox


async def delete_sandbox(sandbox_id: str):
    """Delete a sandbox by its ID."""
    try:
        sandbox = daytona.get(sandbox_id)
        daytona.delete(sandbox)
        return True
    except Exception as exc:
        logger.error(f"Error deleting sandbox {sandbox_id}: {exc}")
        raise
