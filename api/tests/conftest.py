"""
Shared fixtures for api/tests.

DB-gated tests throughout api/tests/*.py build sessions via
api.core.database.AsyncSessionLocal directly, but nothing else in the
suite triggers FastAPI's lifespan() startup — httpx's ASGITransport does
not fire ASGI lifespan events on its own. Without this fixture, every
DB-gated test fails with "Database session factory is not initialised"
whenever DATABASE_URL happens to be present in the environment (see the
rootdir conftest.py's load_dotenv(), which is collected for every
invocation shape because rootdir is an ancestor of every testpaths entry —
not just when tests/ happens to be part of collection).
"""

import os

import pytest
import pytest_asyncio


def _db_configured() -> bool:
    """Same guard every api/tests DB-gated fixture uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.fixture(autouse=True)
def _require_root_conftest_redirect(pytestconfig):
    """
    Fail closed (D-03) if TEST_DATABASE_URL is configured but the rootdir
    conftest.py's redirect did not fire for this invocation.

    No-ops when TEST_DATABASE_URL is unset, matching the suite's existing
    "no-op unless explicitly satisfied" convention — contributors without a
    dedicated test DB see no change in behavior.

    Declared as the first parameter of _api_lifespan below so pytest
    resolves this guard before the lifespan fixture body runs — the
    dependency is explicit, not incidental to autouse ordering.
    """
    if not os.environ.get("TEST_DATABASE_URL"):
        return

    assert getattr(pytestconfig, "_scotus_redirect_fired", False), (
        "The rootdir conftest.py's pytest_configure hook did not fire for "
        "this pytest invocation — refusing to run DB-gated api/tests "
        "against a possibly-unredirected DATABASE_URL rather than silently "
        "falling through to the shared dev DB (D-03)."
    )
    assert os.environ.get("DATABASE_URL") == os.environ.get("TEST_DATABASE_URL"), (
        "DATABASE_URL does not equal TEST_DATABASE_URL even though the "
        "rootdir conftest.py's sentinel fired — refusing to run DB-gated "
        "api/tests against a possibly-unredirected DATABASE_URL rather than "
        "silently falling through to the shared dev DB (D-03)."
    )


@pytest_asyncio.fixture(autouse=True)
async def _api_lifespan(_require_root_conftest_redirect):
    """
    Run FastAPI's lifespan around each api/tests test so AsyncSessionLocal is live.

    Imports lifespan/app locally (not at module level) because
    tests/test_admin_router.py::test_api_main_imports_without_error deletes and
    re-imports every api.* module mid-suite — a module-level import here would
    bind to the pre-reset module object, while fixtures elsewhere that import
    api.main.app inside their own function bodies pick up the post-reset object,
    silently splitting the process into two disconnected module graphs.
    """
    if not _db_configured():
        yield
        return
    from api.core.database import lifespan
    from api.main import app

    async with lifespan(app):
        yield


@pytest_asyncio.fixture
async def db_session():
    """
    Async DB session seeded for each test, rolled back after.

    Requires DATABASE_URL to be set. Each test gets a fresh transaction
    that is rolled back, so seeded rows do not persist across tests.
    """
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()
