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


settings = Settings()
settings.validate()
