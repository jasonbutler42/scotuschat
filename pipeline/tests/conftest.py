"""
Shared pytest fixtures for pipeline tests.

Provides:
    - test_db_url:    session-scoped test database URL
    - engine:         session-scoped async SQLAlchemy engine
    - async_session:  function-scoped AsyncSession with rollback isolation
    - clean_db:       function-scoped table truncation (opt-in, autouse=False)

HARD CONSTRAINT: Alembic is the sole DDL authority (CLAUDE.md).
No DDL calls are made here. Tests assume that `alembic upgrade head`
has already been run against the test database.

To run DB-dependent tests:
    1. Run `alembic upgrade head` against your test database
    2. Set DATABASE_URL or TEST_DATABASE_URL in .env
    3. Run: pytest pipeline/tests/ -x -q
"""

import os

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env so DATABASE_URL is available
load_dotenv()


# ---------------------------------------------------------------------------
# Session-scoped fixtures (created once per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """
    Return the test database URL.

    HARD SAFETY GUARD (T-31-01): this fixture must never fall back to
    DATABASE_URL. It reads TEST_DATABASE_URL only, and additionally requires
    the resolved database name to be exactly "scotus_test" before returning
    it — mirroring _reset_test_db's guard below. engine/async_session/
    clean_db all build on top of this fixture's return value, so this is the
    single choke point that keeps them from ever truncating the shared dev
    DB (the exact D-02/D-03 incident class this phase exists to close).

    If TEST_DATABASE_URL is unset, or does not target scotus_test, all
    DB-dependent tests are skipped via pytest.skip() rather than silently
    proceeding against DATABASE_URL.
    """
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL not configured — skipping DB-dependent tests. "
            "clean_db/async_session must never fall back to DATABASE_URL (T-31-01)."
        )

    from sqlalchemy.engine import make_url

    if make_url(url).database != "scotus_test":
        pytest.skip(
            "TEST_DATABASE_URL does not target scotus_test — refusing to run "
            "DB-dependent tests against a database that isn't the dedicated "
            "test DB (T-31-01)."
        )
    return url


@pytest.fixture(scope="session")
def engine(test_db_url: str):
    """
    Create a session-scoped async SQLAlchemy engine for tests.

    connect_args={"statement_cache_size": 0} is mandatory for asyncpg
    compatibility behind PgBouncer Transaction mode (CLAUDE.md constraint).

    No DDL calls here — Alembic manages schema (run `alembic upgrade head` first).
    """
    return create_async_engine(
        test_db_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )


# ---------------------------------------------------------------------------
# Function-scoped fixtures (created fresh for each test)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def async_session(engine) -> AsyncSession:
    """
    Yield an AsyncSession for each test, rolling back after the test completes.

    This ensures test isolation: each test sees a clean slate without needing
    to truncate tables manually.

    expire_on_commit=False is mandatory in async SQLAlchemy to avoid
    MissingGreenlet errors on attribute access after commit.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def clean_db(async_session: AsyncSession) -> None:
    """
    Truncate all pipeline-relevant tables with CASCADE.

    Opt-in fixture — only add to tests that need a truly empty DB.
    Usage:
        async def test_something(async_session, clean_db):
            ...

    Tables are truncated in dependency order to satisfy FK constraints
    (CASCADE handles the rest).
    """
    from sqlalchemy import text

    await async_session.execute(
        text(
            """
            TRUNCATE TABLE
                utterances,
                import_run,
                case_arguments,
                case_appearances,
                argument_participants,
                arguments,
                cases,
                court_tenures,
                people,
                roles
            CASCADE
            """
        )
    )
    await async_session.flush()


@pytest.fixture(scope="session", autouse=True)
def _require_root_conftest_redirect(pytestconfig):
    """
    Fail closed (D-03) if TEST_DATABASE_URL is configured but the rootdir
    conftest.py's redirect did not fire for this invocation.

    Session-scoped because the fixture it must precede, _reset_test_db, is
    itself session-scoped and TRUNCATEs tables — a function-scoped guard
    cannot run before it. No-ops when TEST_DATABASE_URL is unset, matching
    the suite's existing "no-op unless explicitly satisfied" convention.
    """
    if not os.environ.get("TEST_DATABASE_URL"):
        return

    assert getattr(pytestconfig, "_scotus_redirect_fired", False), (
        "The rootdir conftest.py's pytest_configure hook did not fire for "
        "this pytest invocation — refusing to run DB-gated pipeline/tests "
        "against a possibly-unredirected DATABASE_URL rather than silently "
        "falling through to the shared dev DB (D-03)."
    )
    assert os.environ.get("DATABASE_URL") == os.environ.get("TEST_DATABASE_URL"), (
        "DATABASE_URL does not equal TEST_DATABASE_URL even though the "
        "rootdir conftest.py's sentinel fired — refusing to run DB-gated "
        "pipeline/tests against a possibly-unredirected DATABASE_URL rather "
        "than silently falling through to the shared dev DB (D-03)."
    )


@pytest.fixture(scope="session", autouse=True)
async def _reset_test_db(_require_root_conftest_redirect):
    """
    Session-scoped auto-reset: TRUNCATE all pipeline-relevant tables once,
    before the suite runs (D-02), so tests start from an empty database.

    HARD SAFETY GUARD (T-31-01): this fixture must never TRUNCATE the shared
    dev DB. It reads TEST_DATABASE_URL directly (NOT the test_db_url/engine
    fixtures below, which fall back to DATABASE_URL and would truncate the
    shared dev DB if TEST_DATABASE_URL were unset) and no-ops unless BOTH:
        1. TEST_DATABASE_URL is set, AND
        2. the resolved database name is exactly "scotus_test".

    Reuses the exact table list/order from `clean_db` above — do not
    re-derive it.
    """
    test_url = os.getenv("TEST_DATABASE_URL", "")
    if not test_url:
        # Never fall back to DATABASE_URL here — no dedicated test DB means
        # no auto-reset, full stop.
        yield
        return

    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    if make_url(test_url).database != "scotus_test":
        yield
        return

    reset_engine = create_async_engine(
        test_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    try:
        async with reset_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    TRUNCATE TABLE
                        utterances,
                        import_run,
                        case_arguments,
                        case_appearances,
                        argument_participants,
                        arguments,
                        cases,
                        court_tenures,
                        people,
                        roles
                    CASCADE
                    """
                )
            )
    finally:
        await reset_engine.dispose()

    yield
