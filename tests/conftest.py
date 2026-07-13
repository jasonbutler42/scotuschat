"""
Root-level pytest conftest.

Loads .env so DATABASE_URL and other env vars are available to all test
modules in the `tests/` directory.

Also wires the whole suite (api + pipeline) onto a dedicated test database
(`TEST_DATABASE_URL`) when configured.
"""

import os

from dotenv import load_dotenv

# Load .env before any tests run.
# Tests that need DATABASE_URL will get it from os.environ after this call.
load_dotenv()

# Capture the real (shared) dev-DB URL BEFORE any override below. A future
# leak-detection hook checks THIS value — never the (possibly overridden)
# os.environ["DATABASE_URL"] — so the guard keeps inspecting the real dev DB
# even when test isolation is active (T-31-05).
_REAL_DATABASE_URL = os.environ.get("DATABASE_URL")

# Redirect DATABASE_URL onto the dedicated test DB for the whole suite
# (api + pipeline) whenever TEST_DATABASE_URL is configured (D-01). This
# redirects api.core.config.settings.database_url, api.core.database.lifespan,
# and every AsyncSessionLocal() without touching any production module —
# both of those modules read the env var lazily via Settings()/
# create_async_engine(), and this conftest is collected before either is
# imported. If TEST_DATABASE_URL is unset, DATABASE_URL is left untouched
# (tests run against the real dev DB).
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
