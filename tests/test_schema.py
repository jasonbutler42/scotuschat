"""
Smoke tests for the database schema.

These tests verify:
1. All 12 expected tables exist after running `alembic upgrade head`
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

    conn = await asyncpg.connect(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    yield conn
    await conn.close()


# ---------------------------------------------------------------------------
# Test 1: All 12 tables exist post-migration
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
    "import_run",
    "utterances",
    "speaker_alias",
    "argument_status_log",
}


@requires_db
@pytest.mark.asyncio
async def test_all_tables_exist(db_conn):
    """All 12 tables must exist in the public schema after alembic upgrade head.

    Phase 47 (PROV-01): `import_run` generalizes the retired `pipeline_runs`
    table — this same test also asserts `pipeline_runs` is gone from the live
    schema, and that `utterances` carries `import_run_id` (not the dropped
    per-row `strategy` column), so a future backslide back to the old table
    name or column shape is caught here, not inferred.
    """
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
    assert 'pipeline_runs' not in actual_tables, (
        "The retired pipeline_runs table must not exist after migration 0026 — "
        "import_run replaces it (D-01 clean rebuild)."
    )

    column_rows = await db_conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'utterances'
        """
    )
    utterance_columns = {row["column_name"] for row in column_rows}
    assert "import_run_id" in utterance_columns, (
        "utterances.import_run_id must exist — utterances FK to import_run, "
        "not the retired pipeline_runs table."
    )
    assert "strategy" not in utterance_columns, (
        "utterances.strategy must be dropped — provenance is now declared on "
        "the parent import_run row's source/method columns (D-05)."
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


# ---------------------------------------------------------------------------
# Test 4: people.is_justice column exists, is NOT NULL, and has DEFAULT FALSE
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_people_has_is_justice_column(db_conn):
    """
    people.is_justice must exist as a BOOLEAN NOT NULL column with a DEFAULT FALSE.

    Asserts:
    - Exactly one row returned from information_schema.columns for the column
    - data_type is 'boolean'
    - is_nullable is 'NO' (NOT NULL constraint)
    - column_default is not NULL and contains 'false' (case-insensitive)

    Added by migration 0010 (Phase 18 — PEOPLE-05).
    """
    rows = await db_conn.fetch(
        """
        SELECT data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'people'
          AND column_name = 'is_justice'
        """
    )
    assert len(rows) == 1, (
        f"Expected exactly 1 row for people.is_justice in information_schema.columns, "
        f"got {len(rows)}. Has migration 0010 been applied?"
    )
    row = rows[0]
    assert row["data_type"] == "boolean", (
        f"Expected data_type='boolean', got '{row['data_type']}'"
    )
    assert row["is_nullable"] == "NO", (
        f"Expected is_nullable='NO' (NOT NULL), got '{row['is_nullable']}'"
    )
    assert row["column_default"] is not None, (
        "Expected a non-NULL column_default (DEFAULT FALSE), got NULL"
    )
    assert "false" in row["column_default"].lower(), (
        f"Expected column_default to contain 'false', got '{row['column_default']}'"
    )


# ---------------------------------------------------------------------------
# Test 5: utterances.speaker_undetermined / is_inaudible_marker /
# verbatim_text columns + both CHECK constraints (Phase 53 plan 53-01, D-05)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_utterances_carry_undetermined_and_marker_columns(db_conn):
    """
    Migration 0033 adds three nullable utterance columns with NO
    database-side default (NULL means "written before 0033", fails
    closed) plus two CHECK constraints that make the trust branch's
    assumptions structural.

    Asserts:
    - speaker_undetermined: boolean, nullable, NULL column_default
    - is_inaudible_marker: boolean, nullable, NULL column_default
    - verbatim_text: text, nullable, NULL column_default
    - both CHECK constraint names exist on utterances
    """
    column_rows = await db_conn.fetch(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'utterances'
          AND column_name IN ('speaker_undetermined', 'is_inaudible_marker', 'verbatim_text')
        """
    )
    columns_by_name = {row["column_name"]: row for row in column_rows}
    assert set(columns_by_name) == {
        "speaker_undetermined",
        "is_inaudible_marker",
        "verbatim_text",
    }, (
        f"Expected exactly speaker_undetermined/is_inaudible_marker/verbatim_text, "
        f"got {sorted(columns_by_name)}. Has migration 0033 been applied?"
    )

    for name, expected_type in (
        ("speaker_undetermined", "boolean"),
        ("is_inaudible_marker", "boolean"),
        ("verbatim_text", "text"),
    ):
        row = columns_by_name[name]
        assert row["data_type"] == expected_type, (
            f"Expected {name}.data_type='{expected_type}', got '{row['data_type']}'"
        )
        assert row["is_nullable"] == "YES", (
            f"Expected {name}.is_nullable='YES', got '{row['is_nullable']}'"
        )
        assert row["column_default"] is None, (
            f"Expected {name}.column_default IS NULL (no database-side default, "
            f"reseed-don't-migrate), got '{row['column_default']}'"
        )

    constraint_rows = await db_conn.fetch(
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'utterances'
          AND constraint_type = 'CHECK'
        """
    )
    constraint_names = {row["constraint_name"] for row in constraint_rows}
    assert "ck_utterances_undetermined_unattributed" in constraint_names, (
        f"Expected CHECK constraint 'ck_utterances_undetermined_unattributed' not found.\n"
        f"Found CHECK constraints: {sorted(constraint_names)}"
    )
    assert "ck_utterances_inaudible_marker_not_stage" in constraint_names, (
        f"Expected CHECK constraint 'ck_utterances_inaudible_marker_not_stage' not found.\n"
        f"Found CHECK constraints: {sorted(constraint_names)}"
    )


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
            # Skip nested test directories (e.g. api/tests/, pipeline/tests/) —
            # the docstring above promises "excludes test files", but a bare
            # rglob() over api/ or pipeline/ also walks their own tests/
            # subdirectories, where an assertion string can legitimately
            # contain the literal substring "create_all" without violating
            # the Alembic-only DDL constraint this test actually guards.
            if "tests" in py_file.relative_to(search_dir).parts[:-1]:
                continue
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
