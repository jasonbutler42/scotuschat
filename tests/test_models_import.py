"""
TDD RED: Verify that the ORM models can be imported and have the expected structure.
This test file intentionally fails before models.py is created.
"""

import pytest


def test_all_tables_count():
    """All 14 ORM model tables must be importable from api.models.models."""
    from api.models.models import Base
    tables = list(Base.metadata.tables.keys())
    assert len(tables) == 14, f"Expected 14 tables, got {len(tables)}: {tables}"


def test_expected_table_names():
    """All 14 exact table names must be present."""
    from api.models.models import Base
    tables = set(Base.metadata.tables.keys())
    expected = {
        "roles", "people", "court_tenures", "cases", "arguments",
        "case_arguments", "case_appearances", "argument_participants",
        "import_run", "utterances", "speaker_alias", "admin_jobs",
        "argument_status_log",
        # Phase 49 — migration 0028 (plan 49-01): per-value operator-review
        # bookkeeping table (D-13), unrelated to the legacy
        # admin_jobs.discrepancies JSONB blob (D-14).
        "value_discrepancy",
    }
    assert tables == expected, f"Table mismatch: {tables.symmetric_difference(expected)}"


def test_side_enum_values():
    """SideEnum must have exactly BENCH, ADVOCATE, UNKNOWN, PETITIONER, RESPONDENT, AMICUS."""
    from api.models.models import SideEnum
    values = [e.value for e in SideEnum]
    assert "BENCH" in values
    assert "ADVOCATE" in values
    assert "UNKNOWN" in values
    assert "PETITIONER" in values
    assert "RESPONDENT" in values
    assert "AMICUS" in values
    assert len(values) == 6


def test_import_run_status_values():
    """ImportRunStatus must have exactly 5 values."""
    from api.models.models import ImportRunStatus
    values = [e.value for e in ImportRunStatus]
    assert "pending" in values
    assert "running" in values
    assert "completed" in values
    assert "failed" in values
    assert "needs_review" in values
    assert len(values) == 5


def test_import_source_values():
    """ImportSource is a closed vocabulary of exactly 4 values (D-02) — a
    standing exhaustiveness guard so the enum cannot silently grow or shrink."""
    from api.models.models import ImportSource
    values = [e.value for e in ImportSource]
    assert "operator" in values
    assert "corpus" in values
    assert "pdf_pipeline" in values
    assert "seed" in values
    assert len(values) == 4


def test_import_method_values():
    """ImportMethod is a closed vocabulary of exactly 5 values (D-02) — a
    standing exhaustiveness guard so the enum cannot silently grow or shrink."""
    from api.models.models import ImportMethod
    values = [e.value for e in ImportMethod]
    assert "manual" in values
    assert "direct" in values
    assert "normalized" in values
    assert "rule_based" in values
    assert "llm_corrective" in values
    assert len(values) == 5


def test_case_argument_composite_pk():
    """CaseArgument must have composite primary key (case_id, argument_id)."""
    from api.models.models import CaseArgument
    pk_cols = [c.name for c in CaseArgument.__table__.primary_key]
    assert "case_id" in pk_cols
    assert "argument_id" in pk_cols


def test_utterance_unique_constraint():
    """Utterance must have unique constraint named uq_utterance_arg_run_seq."""
    from api.models.models import Utterance
    constraint_names = [c.name for c in Utterance.__table__.constraints]
    assert "uq_utterance_arg_run_seq" in constraint_names, (
        f"Expected 'uq_utterance_arg_run_seq' in constraints: {constraint_names}"
    )


def test_utterance_indexes():
    """Utterance must have indexes on argument_id and import_run_id."""
    from api.models.models import Utterance
    index_names = [i.name for i in Utterance.__table__.indexes]
    assert "ix_utterances_argument_id" in index_names, (
        f"Expected ix_utterances_argument_id in: {index_names}"
    )
    assert "ix_utterances_import_run_id" in index_names, (
        f"Expected ix_utterances_import_run_id in: {index_names}"
    )


def test_no_create_all_in_models():
    """models.py must not contain Base.metadata.create_all."""
    import inspect
    import api.models.models as m
    source = inspect.getsource(m)
    assert "create_all" not in source, "create_all found in models.py — violates Alembic-only DDL constraint"
