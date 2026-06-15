"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate env vars at startup and provide
IDE-friendly type-checked access throughout the API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FastAPI application settings."""

    database_url: str  # postgresql+asyncpg://user:pass@host/db

    # Optional in API — only needed for pipeline steps
    anthropic_api_key: str = ""

    # False in production; enables SQLAlchemy SQL echo when True
    debug: bool = False

    # Required — set via ADMIN_TOKEN env var (D-13).
    # No default value: app refuses to start without this set (fail-fast, T-05-02).
    # Do NOT log or expose this value in any endpoint response.
    admin_token: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
