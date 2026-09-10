from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("OPENMANUS_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./openmanus_platform.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("OPENMANUS_JWT_SECRET", "development-only-change-me")
    jwt_algorithm: str = os.getenv("OPENMANUS_JWT_ALGORITHM", "HS256")
    access_token_minutes: int = int(os.getenv("OPENMANUS_ACCESS_TOKEN_MINUTES", "60"))
    queue_name: str = os.getenv("OPENMANUS_QUEUE", "openmanus:tasks")
    workflow_stale_seconds: int = int(os.getenv("OPENMANUS_WORKFLOW_STALE_SECONDS", "900"))
    auto_create_db: bool = os.getenv("OPENMANUS_AUTO_CREATE_DB", "true").lower() in {"1", "true", "yes"}
    sandbox_enabled: bool = os.getenv("OPENMANUS_SANDBOX_ENABLED", "false").lower() in {"1", "true", "yes"}
    artifact_root: str = os.getenv("OPENMANUS_ARTIFACT_ROOT", "./platform_data/artifacts")
    artifact_max_bytes: int = int(os.getenv("OPENMANUS_ARTIFACT_MAX_BYTES", str(50 * 1024 * 1024)))
    s3_bucket: str = os.getenv("OPENMANUS_S3_BUCKET", "")
    s3_endpoint_url: str = os.getenv("OPENMANUS_S3_ENDPOINT_URL", "")
    s3_region: str = os.getenv("AWS_REGION", "")
    usage_input_rate_per_1k: float = float(os.getenv("OPENMANUS_USAGE_INPUT_RATE", "0.003"))
    usage_output_rate_per_1k: float = float(os.getenv("OPENMANUS_USAGE_OUTPUT_RATE", "0.015"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("OPENMANUS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    )

    def validate(self) -> None:
        if self.environment.lower() in {"production", "prod"} and self.jwt_secret == "development-only-change-me":
            raise RuntimeError("OPENMANUS_JWT_SECRET must be changed in production")
        if self.workflow_stale_seconds < 60:
            raise RuntimeError("OPENMANUS_WORKFLOW_STALE_SECONDS must be at least 60 seconds")
        if self.artifact_max_bytes < 1:
            raise RuntimeError("OPENMANUS_ARTIFACT_MAX_BYTES must be positive")
        if self.usage_input_rate_per_1k < 0 or self.usage_output_rate_per_1k < 0:
            raise RuntimeError("Usage rates cannot be negative")


settings = Settings()
settings.validate()
