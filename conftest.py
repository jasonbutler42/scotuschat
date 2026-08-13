"""
Root-level (pytest rootdir) conftest.

This file lives at the pytest rootdir — the same directory as pytest.ini —
precisely because the rootdir is an ancestor of every `testpaths` entry
(`tests`, `pipeline/tests`, `api/tests`). pytest's conftest.py discovery is
strictly hierarchical: a conftest.py's hooks/module-level side effects apply
only to test paths at or below its own directory. A conftest at the rootdir
is collected for EVERY invocation shape — bare (`pytest`), explicit single
file (`pytest api/tests/test_foo.py`), or explicit multi-path
(`pytest api/tests/test_foo.py pipeline/tests/test_bar.py`) — because the
rootdir is, by construction, an ancestor of anything under it.

This file used to live at `tests/conftest.py`, a SIBLING of `api/tests/` and
`pipeline/tests/`, not their ancestor. Any pytest invocation with explicit
paths under those sibling directories never walked up into `tests/`, so this
redirect and the row-count tripwire below silently no-op'd — the DATABASE_URL
redirect never fired, and DB-gated tests ran directly against the shared dev
database. This wiped the dev DB to 0 rows twice during Phase 45 (see D-03,
`.planning/todos/pending/2026-08-12-pytest-explicit-paths-bypass-db-isolation.md`).
Relocating this file here is the actual fix — see
`tests/test_pytest_isolation_invocation_shapes.py` for the permanent
regression test proving all three invocation shapes now redirect correctly.

Loads .env so DATABASE_URL and other env vars are available to all test
modules across the whole suite (tests/, api/tests/, pipeline/tests/).

Also wires the whole suite (api + pipeline) onto a dedicated test database
(`TEST_DATABASE_URL`) when configured, and enforces a self-checking guard
that the shared dev DB (the real `DATABASE_URL`) is never mutated by a
pytest session — see pytest_sessionstart/pytest_sessionfinish below.
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
# imported, for every invocation shape (it lives at rootdir). If
# TEST_DATABASE_URL is unset, DATABASE_URL is left untouched (tests run
# against the real dev DB).
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


def _db_configured(url: str | None) -> bool:
    """Same placeholder guard every DB-gated fixture in this suite uses."""
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def pytest_configure(config):
    """
    Set a sentinel that other conftests (api/tests, pipeline/tests) can
    assert on before running any DB-gated test (D-03 fail-closed guard).

    This hook is guaranteed to run for every invocation shape because THIS
    FILE is at the pytest rootdir — an ancestor of every testpaths entry —
    so pytest always collects it regardless of which explicit paths (if any)
    are passed on the command line.
    """
    config._scotus_redirect_fired = True


def pytest_sessionstart(session):
    """
    Snapshot Person/Argument row counts on the REAL shared dev DB (D-11).

    Always uses _REAL_DATABASE_URL (captured above, before any
    TEST_DATABASE_URL override) — never the possibly-overridden
    os.environ["DATABASE_URL"] — so this guard keeps watching the dev DB
    even while isolation is active.

    Silently no-ops (D-13) when the real URL is unset or matches one of the
    placeholder guards — a pytest_sessionstart hook has no test context, so
    pytest.skip() is not available here; just return.
    """
    if not _db_configured(_REAL_DATABASE_URL):
        return

    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _snapshot():
        engine = create_async_engine(
            _REAL_DATABASE_URL,
            connect_args={"statement_cache_size": 0},
            pool_size=2,
            echo=False,
        )
        try:
            async with engine.connect() as conn:
                people = (await conn.execute(text("SELECT COUNT(*) FROM people"))).scalar_one()
                arguments = (await conn.execute(text("SELECT COUNT(*) FROM arguments"))).scalar_one()
                return people, arguments
        finally:
            await engine.dispose()

    people_count, arguments_count = asyncio.run(_snapshot())
    session.config._scotus_pre_counts = {"people": people_count, "arguments": arguments_count}


def pytest_sessionfinish(session, exitstatus):
    """
    Re-query Person/Argument counts on the real dev DB and assert unchanged (D-11, D-12).

    Only checks `people` and `arguments` — not the full clean_db table list —
    to keep the failure message unambiguous. Silently no-ops (D-13) under the
    same guard as pytest_sessionstart.
    """
    if not _db_configured(_REAL_DATABASE_URL):
        return

    pre_counts = getattr(session.config, "_scotus_pre_counts", None)
    if pre_counts is None:
        # pytest_sessionstart didn't run (e.g. guard tripped differently, or
        # a collection-only invocation) — nothing to compare against.
        return

    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _recheck():
        engine = create_async_engine(
            _REAL_DATABASE_URL,
            connect_args={"statement_cache_size": 0},
            pool_size=2,
            echo=False,
        )
        try:
            async with engine.connect() as conn:
                people = (await conn.execute(text("SELECT COUNT(*) FROM people"))).scalar_one()
                arguments = (await conn.execute(text("SELECT COUNT(*) FROM arguments"))).scalar_one()
                return people, arguments
        finally:
            await engine.dispose()

    post_people, post_arguments = asyncio.run(_recheck())
    post_counts = {"people": post_people, "arguments": post_arguments}

    mismatches = [
        f"{table}: before={pre_counts[table]} after={post_counts[table]}"
        for table in ("people", "arguments")
        if pre_counts[table] != post_counts[table]
    ]
    if mismatches:
        raise AssertionError(
            "Shared dev DB row counts changed during this pytest session — "
            "a test leaked writes into the real database instead of the "
            "isolated test DB (" + "; ".join(mismatches) + ")"
        )
