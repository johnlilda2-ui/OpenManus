from dataclasses import dataclass
import os


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("OPENMANUS_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./openmanus_platform.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("OPENMANUS_JWT_SECRET", "development-only-change-me")
    jwt_secret_file: str = os.getenv("OPENMANUS_JWT_SECRET_FILE", "/run/secrets/openmanus_jwt_secret")
    jwt_algorithm: str = os.getenv("OPENMANUS_JWT_ALGORITHM", "HS256")
    access_token_minutes: int = int(os.getenv("OPENMANUS_ACCESS_TOKEN_MINUTES", "60"))
    queue_name: str = os.getenv("OPENMANUS_QUEUE", "openmanus:tasks")
    workflow_stale_seconds: int = int(os.getenv("OPENMANUS_WORKFLOW_STALE_SECONDS", "900"))
    auto_create_db: bool = _bool("OPENMANUS_AUTO_CREATE_DB", True)
    sandbox_enabled: bool = _bool("OPENMANUS_SANDBOX_ENABLED", False)
    sandbox_backend: str = os.getenv("OPENMANUS_SANDBOX_BACKEND", "none").lower()
    artifact_root: str = os.getenv("OPENMANUS_ARTIFACT_ROOT", "./platform_data/artifacts")
    artifact_max_bytes: int = int(os.getenv("OPENMANUS_ARTIFACT_MAX_BYTES", str(50 * 1024 * 1024)))
    s3_bucket: str = os.getenv("OPENMANUS_S3_BUCKET", "")
    s3_endpoint_url: str = os.getenv("OPENMANUS_S3_ENDPOINT_URL", "")
    s3_region: str = os.getenv("AWS_REGION", "")
    usage_input_rate_per_1k: float = float(os.getenv("OPENMANUS_USAGE_INPUT_RATE", "0.003"))
    usage_output_rate_per_1k: float = float(os.getenv("OPENMANUS_USAGE_OUTPUT_RATE", "0.015"))
    rate_limit_per_minute: int = int(os.getenv("OPENMANUS_RATE_LIMIT_PER_MINUTE", "120"))
    rate_limit_auth_per_minute: int = int(os.getenv("OPENMANUS_RATE_LIMIT_AUTH_PER_MINUTE", "10"))
    rate_limit_prefix: str = os.getenv("OPENMANUS_RATE_LIMIT_PREFIX", "openmanus:rl")
    rate_limit_fail_open: bool = _bool("OPENMANUS_RATE_LIMIT_FAIL_OPEN", True)
    api_key_secret_prefix: str = os.getenv("OPENMANUS_API_KEY_SECRET_PREFIX", "secret://")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("OPENMANUS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    )

    def validate(self) -> None:
        env = self.environment.lower()
        if env in {"production", "prod"}:
            if self.jwt_secret == "development-only-change-me" and not os.path.isfile(self.jwt_secret_file):
                raise RuntimeError("Set OPENMANUS_JWT_SECRET or mount OPENMANUS_JWT_SECRET_FILE in production")
            if self.auto_create_db:
                raise RuntimeError("Disable OPENMANUS_AUTO_CREATE_DB in production; run Alembic migrations")
            if self.rate_limit_per_minute < 1 or self.rate_limit_auth_per_minute < 1:
                raise RuntimeError("Production rate limits must be positive")
            if self.sandbox_backend not in {"daytona"} or not self.sandbox_enabled:
                raise RuntimeError("Production requires OPENMANUS_SANDBOX_ENABLED=true and OPENMANUS_SANDBOX_BACKEND=daytona")
        if self.workflow_stale_seconds < 60:
            raise RuntimeError("OPENMANUS_WORKFLOW_STALE_SECONDS must be at least 60 seconds")
        if self.artifact_max_bytes < 1:
            raise RuntimeError("OPENMANUS_ARTIFACT_MAX_BYTES must be positive")
        if self.usage_input_rate_per_1k < 0 or self.usage_output_rate_per_1k < 0:
            raise RuntimeError("Usage rates cannot be negative")


settings = Settings()
settings.validate()
