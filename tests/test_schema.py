"""
Smoke tests for the database schema.

These tests verify:
1. All 11 expected tables exist after running `alembic upgrade head`
2. The utterances unique constraint is in place
3. No Base.metadata.create_all() call exists anywhere in the codebase

Tests 1 and 2 require a running PostgreSQL instance with DATABASE_URL set.
Test 3 (test_no_create_all_in_codebase) is a static analysis check — runs always.

Run with:
    pytest tests/test_schema.py -x -q
"""

import os
import pathlib

import pytest


# ---------------------------------------------------------------------------
# Helper: skip marker for tests that need a live database
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
requires_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping database connectivity tests",
)


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_conn():
    """
    Async asyncpg connection to the test database.
    Skipped automatically if DATABASE_URL is not set.
    """
    import asyncpg

    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


# ---------------------------------------------------------------------------
# Test 1: All 10 tables exist post-migration
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "roles",
    "people",
    "court_tenures",
    "cases",
    "arguments",
    "case_arguments",
    "case_appearances",
    "argument_participants",
    "pipeline_runs",
    "utterances",
    "speaker_alias",
}


@requires_db
@pytest.mark.asyncio
async def test_all_tables_exist(db_conn):
    """All 11 tables must exist in the public schema after alembic upgrade head."""
    rows = await db_conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        """
    )
    actual_tables = {row["table_name"] for row in rows}

    missing = EXPECTED_TABLES - actual_tables
    assert not missing, (
        f"Missing tables after migration: {sorted(missing)}\n"
        f"Found tables: {sorted(actual_tables)}"
    )


# ---------------------------------------------------------------------------
# Test 2: utterances unique constraint exists
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_utterances_unique_constraint(db_conn):
    """Unique constraint uq_utterance_arg_run_seq must exist on utterances table."""
    rows = await db_conn.fetch(
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'utterances'
          AND constraint_type = 'UNIQUE'
        """
    )
    constraint_names = {row["constraint_name"] for row in rows}
    assert "uq_utterance_arg_run_seq" in constraint_names, (
        f"Expected constraint 'uq_utterance_arg_run_seq' not found.\n"
        f"Found constraints: {sorted(constraint_names)}"
    )


# ---------------------------------------------------------------------------
# Test 3: Static analysis — no create_all() call in production code
# Excludes test files from the search since test code may reference the
# pattern in assertions. Checks only api/ and alembic/ source trees.
# ---------------------------------------------------------------------------


def test_no_create_all_in_codebase():
    """
    No Base.metadata.create_all() call must exist in production source files.

    Alembic is the sole DDL authority (CLAUDE.md hard constraint).
    Searches api/ and alembic/ directories only (excludes test files).
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Search production source directories — exclude tests
    search_dirs = [
        os.path.join(project_root, "api"),
        os.path.join(project_root, "alembic"),
        os.path.join(project_root, "pipeline"),
    ]

    offending_files = []
    for search_dir in search_dirs:
        for py_file in pathlib.Path(search_dir).rglob("*.py"):
            try:
                if "create_all" in py_file.read_text(encoding="utf-8", errors="ignore"):
                    offending_files.append(str(py_file))
            except OSError:
                pass

    assert not offending_files, (
        "Found 'create_all' in production source files — "
        "violates Alembic-only DDL constraint (CLAUDE.md):\n"
        + "\n".join(f"  {f}" for f in offending_files)
    )
