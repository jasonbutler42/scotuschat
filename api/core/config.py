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

    # ---------------------------------------------------------------------------
    # Phase 6 note: the following env vars are SvelteKit-side ($env/static/private).
    # They are NOT read by the Python API — Python reads only the fields above.
    # Listed here so operators see all required env vars in one place.
    #
    # SESSION_SECRET   — HMAC-SHA256 key for the scotus_admin_session cookie.
    #                    Minimum 32 characters. Rotating this key invalidates all
    #                    existing sessions.
    # ADMIN_USERNAME   — Operator login username (plain text, compared via
    #                    timingSafeEqual in the SvelteKit login action).
    # ADMIN_PASSWORD   — Operator login password (plain text; no DB-backed hashing;
    #                    store a strong random value, not a memorable password).
    # ---------------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
