"""Runtime configuration loaded from environment variables.

Secrets (database password, JWT secret, OpenAI key) stay outside the image.
See the repo-root .env.example for the variable names.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "postgresql://campusbite:change-me@localhost:5433/campusbite"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    # One day is convenient for a campus demo; shorten this in a real deployment.
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Orders left in PLACED or ACCEPTED longer than this get an owner reminder.
    reminder_stale_minutes: int = 15
    reminder_interval_seconds: int = 60
    # Per-user cap for the insights endpoint. One uvicorn worker, in-memory limiter.
    ai_requests_per_minute: int = 8

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    @property
    def sqlalchemy_url(self) -> str:
        """Accept a plain postgresql:// URL and drive it with psycopg 3."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
