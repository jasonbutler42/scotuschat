"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate env vars at startup and provide
IDE-friendly type-checked access throughout the API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FastAPI application settings."""

    database_url: str  # postgresql+asyncpg://user:pass@host/db

    # Test-DB isolation (Phase 31, D-01): read directly via os.environ by
    # tests/conftest.py (which redirects DATABASE_URL to this value before any
    # module import) and by pipeline/tests/conftest.py's test_db_url fixture.
    # Declared here — not used by the running API — solely so Settings() does
    # not raise extra_forbidden when TEST_DATABASE_URL is present in .env
    # alongside DATABASE_URL.
    test_database_url: str = ""

    # Optional in API — only needed for pipeline steps
    anthropic_api_key: str = ""

    # False in production; enables SQLAlchemy SQL echo when True
    debug: bool = False

    # Required — set via ADMIN_TOKEN env var (D-13).
    # No default value: app refuses to start without this set (fail-fast, T-05-02).
    # Do NOT log or expose this value in any endpoint response.
    admin_token: str

    # Required — set via ENVIRONMENT env var (Phase 43 D-02).
    # No default value: app refuses to start without this set (fail-fast, mirrors
    # admin_token above). The gate is an allow-list, not a block-list: consumers
    # compare this value for equality with the literal "development" string, so
    # an unset, misspelled, or unknown value refuses by default rather than
    # accidentally passing. The comparison itself lives in api/main.py's
    # conditional admin_dev router include, and separately in
    # app/src/routes/admin/+page.server.ts — this field only holds the raw value.
    # SvelteKit reads its OWN independent ENVIRONMENT from app/.env (a separate
    # file with no shared source) — the two must be kept in sync manually.
    environment: str

    # ---------------------------------------------------------------------------
    # DO Spaces — required only for PIPE-13 file upload (operator uploads a local PDF).
    # URL-mode (PIPE-12) works without these credentials — they default to "".
    #
    # DEPLOYMENT TIER NOTE: These credentials must be configured on the FastAPI service
    # in the DO App Platform environment, NOT the SvelteKit service. boto3 runs inside
    # the FastAPI container (Plan 02 upload route) and inside the pipeline subprocess
    # (Plan 03 --spaces-key download). These vars are never used by SvelteKit.
    #
    # DO App Platform env var names:
    #   AWS_ACCESS_KEY_ID     — Spaces access key (from DO Console -> API -> Spaces Keys)
    #   AWS_SECRET_ACCESS_KEY — Spaces secret key (shown once at creation)
    #   DO_SPACES_BUCKET      — Spaces bucket name
    #   DO_SPACES_ENDPOINT    — e.g. "https://nyc3.digitaloceanspaces.com"
    #   DO_SPACES_REGION      — e.g. "nyc3"
    # ---------------------------------------------------------------------------
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    do_spaces_bucket: str = ""
    do_spaces_endpoint: str = ""   # e.g. "https://nyc3.digitaloceanspaces.com"
    do_spaces_region: str = ""     # e.g. "nyc3"

    # ---------------------------------------------------------------------------
    # Phase 6 note: the following env vars are SvelteKit-side ($env/static/private).
    # They are NOT read by the Python API — Python reads only the fields above.
    # Listed here so operators see all required env vars in one place.
    # (SvelteKit also has its own independent ENVIRONMENT var, in app/.env —
    # see the `environment` field's comment above; that one IS read by Python,
    # this block only lists vars Python does not read.)
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
