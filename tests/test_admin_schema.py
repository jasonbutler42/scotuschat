"""
Static-analysis smoke tests for the Phase 5 admin schema (migration 0003 + ORM model).

Per D-15: Phase 5 uses smoke/static checks only — no DB connection required.
These tests verify the migration file and ORM model exist with the correct
structure, column names, and constraints.

Run with:
    pytest tests/test_admin_schema.py -x -q
"""

import os
import pathlib


# ---------------------------------------------------------------------------
# Helper: resolve project root from this file's location
# ---------------------------------------------------------------------------


def _project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Task 1 — Migration 0003 static checks
# ---------------------------------------------------------------------------


def test_migration_0003_file_exists():
    """Migration file alembic/versions/0003_add_admin_jobs.py must exist."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    assert migration.exists(), (
        "Expected alembic/versions/0003_add_admin_jobs.py to exist — migration file is missing"
    )


def test_migration_0003_revision_identifiers():
    """Migration must declare revision='0003' and down_revision='0002'."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert 'revision: str = "0003"' in content or "revision = \"0003\"" in content, (
        "Expected migration to declare revision '0003'"
    )
    assert '"0002"' in content, (
        "Expected migration to declare down_revision '0002'"
    )
    assert "down_revision" in content, (
        "Expected 'down_revision' identifier in migration"
    )


def test_migration_0003_table_name():
    """Migration must reference the admin_jobs table."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert "admin_jobs" in content, (
        "Expected 'admin_jobs' table name in migration 0003"
    )


def test_migration_0003_all_10_columns():
    """Migration must include all 10 required column names for admin_jobs."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    required_columns = [
        "id",
        "status",
        "current_step",
        "argument_id",
        "pdf_url",
        "spaces_key",
        "discrepancies",
        "error_message",
        "created_at",
        "updated_at",
    ]
    for col in required_columns:
        assert f'"{col}"' in content, (
            f"Expected column '{col}' to appear in migration 0003 — column is missing"
        )


def test_migration_0003_fk_to_arguments():
    """Migration must include a FK reference to arguments.id."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert "arguments.id" in content, (
        "Expected FK reference to 'arguments.id' in migration 0003"
    )


def test_migration_0003_no_create_all():
    """Migration must NOT call Base.metadata.create_all (Alembic is sole DDL authority)."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "Migration 0003 must NOT call create_all — Alembic is the sole DDL authority (CLAUDE.md)"
    )


def test_migration_0003_enum_types():
    """Migration must define both PG enum types: admin_job_status and admin_job_step."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert "admin_job_status" in content, (
        "Expected PG enum type 'admin_job_status' in migration 0003"
    )
    assert "admin_job_step" in content, (
        "Expected PG enum type 'admin_job_step' in migration 0003"
    )


def test_migration_0003_has_downgrade():
    """Migration must define a downgrade() function that drops the table and enum types."""
    migration = _project_root() / "alembic" / "versions" / "0003_add_admin_jobs.py"
    content = migration.read_text(encoding="utf-8")
    assert "def downgrade()" in content, (
        "Expected 'def downgrade()' in migration 0003"
    )
    assert "drop_table" in content or "DROP TABLE" in content, (
        "Expected drop_table or DROP TABLE in downgrade() of migration 0003"
    )


# ---------------------------------------------------------------------------
# Task 2 — ORM model static checks (added in Task 2)
# ---------------------------------------------------------------------------


def test_models_has_admin_job_classes():
    """api/models/models.py must define AdminJob, AdminJobStatus, and AdminJobStep."""
    models = _project_root() / "api" / "models" / "models.py"
    content = models.read_text(encoding="utf-8")
    assert "class AdminJob" in content, (
        "Expected 'class AdminJob' in api/models/models.py"
    )
    assert "class AdminJobStatus" in content, (
        "Expected 'class AdminJobStatus' in api/models/models.py"
    )
    assert "class AdminJobStep" in content, (
        "Expected 'class AdminJobStep' in api/models/models.py"
    )


def test_models_admin_job_all_10_columns():
    """AdminJob ORM model must define all 10 column names matching migration 0003."""
    models = _project_root() / "api" / "models" / "models.py"
    content = models.read_text(encoding="utf-8")
    required_columns = [
        "id",
        "status",
        "current_step",
        "argument_id",
        "pdf_url",
        "spaces_key",
        "discrepancies",
        "error_message",
        "created_at",
        "updated_at",
    ]
    for col in required_columns:
        assert col in content, (
            f"Expected column '{col}' to appear in api/models/models.py AdminJob class"
        )


def test_models_no_create_all_regression():
    """api/models/models.py must NOT call Base.metadata.create_all."""
    models = _project_root() / "api" / "models" / "models.py"
    content = models.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "api/models/models.py must NOT call create_all — Alembic is the sole DDL authority (CLAUDE.md)"
    )


def test_config_has_admin_token_required():
    """api/core/config.py must declare admin_token as a required field (no default)."""
    config = _project_root() / "api" / "core" / "config.py"
    content = config.read_text(encoding="utf-8")
    assert "admin_token" in content, (
        "Expected 'admin_token' field in api/core/config.py"
    )
    # Verify admin_token: str appears and does NOT have a default assignment
    lines = content.splitlines()
    admin_token_lines = [l for l in lines if "admin_token" in l and ":" in l]
    assert admin_token_lines, (
        "Expected a line declaring 'admin_token' with a type annotation in config.py"
    )
    for line in admin_token_lines:
        # Strip comments and check for default assignment
        code_part = line.split("#")[0].strip()
        assert "=" not in code_part, (
            f"admin_token must have NO default value (fail-fast per D-13), "
            f"but found: {line.strip()!r}"
        )


def test_models_module_imports_cleanly():
    """api.models.models must import without error (smoke import test)."""
    import importlib
    import sys

    # Ensure project root is on path for the import
    project_root = str(_project_root())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        mod = importlib.import_module("api.models.models")
        assert hasattr(mod, "AdminJob"), (
            "api.models.models imported but AdminJob class is not defined"
        )
        assert hasattr(mod, "AdminJobStatus"), (
            "api.models.models imported but AdminJobStatus is not defined"
        )
        assert hasattr(mod, "AdminJobStep"), (
            "api.models.models imported but AdminJobStep is not defined"
        )
    except ImportError as exc:
        raise AssertionError(
            f"api.models.models failed to import: {exc}"
        ) from exc
