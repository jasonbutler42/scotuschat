"""
Integration tests for Alembic revision 0022 (person name review/provenance).

Exercises the real migration against the isolated `scotus_test` database
(never DATABASE_URL/the shared dev DB — T-38-06): guarded backfill of
legacy `Person.full_name` rows into structured name parts via
api.domain.person_names.split_legacy_full_name (Plan 01), the durable
`name_needs_review` flag (D-04/D-10-D-12), and independently-persisted
`name_extraction_metadata` provenance — plus upgrade repeatability and a
downgrade that removes only this migration's own two columns (never
rewrites names or pre-existing structured operator data).

HARD SAFETY GUARD (T-38-06, mirrors the T-31-01/tests/conftest.py
convention): this module resolves TEST_DATABASE_URL directly and refuses
to run unless it is set AND its database name is exactly "scotus_test" —
it never falls back to DATABASE_URL, because these tests issue real
ALTER TABLE/backfill DDL that must never touch the shared dev DB.

To run:
    1. Ensure `alembic upgrade head` has been applied through at least
       revision 0021 against the dedicated scotus_test database.
    2. Set TEST_DATABASE_URL in .env (or the environment).
    3. pytest api/tests/test_migration_0022_person_name_authority.py -q
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = REPO_ROOT / "alembic"
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "person_name_cases.json"

BASELINE_REVISION = "0021"
TARGET_REVISION = "0022"

_CLEAN_TABLES_SQL = (
    "TRUNCATE TABLE utterances, pipeline_runs, case_arguments, "
    "case_appearances, argument_participants, arguments, cases, "
    "court_tenures, people, roles CASCADE"
)


def _resolve_test_database_url() -> Optional[str]:
    """
    Resolve the dedicated scotus_test database URL directly from
    TEST_DATABASE_URL — never DATABASE_URL — so this migration-DDL suite
    can never run against a possibly-production database (T-38-06).
    """
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        return None
    try:
        parsed = make_url(url)
    except Exception:
        return None
    if parsed.database != "scotus_test":
        return None
    return url


TEST_DATABASE_URL = _resolve_test_database_url()

# Point alembic/env.py's os.environ["DATABASE_URL"] read at the resolved
# isolated test database for the remainder of this process — env.py always
# reads os.environ["DATABASE_URL"] directly (never the Config object's own
# sqlalchemy.url option), matching the same override idiom tests/conftest.py
# already uses to redirect the whole suite onto TEST_DATABASE_URL (T-31-01).
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason=(
        "TEST_DATABASE_URL must be set to the dedicated scotus_test "
        "database to run migration 0022 integration tests (T-38-06) — "
        "this suite never runs against DATABASE_URL/the shared dev DB."
    ),
)


def _load_legacy_split_cases() -> list:
    with FIXTURES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)["legacy_split_cases"]


LEGACY_CASES = _load_legacy_split_cases()
EXPECTED_APPLIED = sum(1 for c in LEGACY_CASES if c["expected_auto_apply"])
EXPECTED_REVIEWED = sum(1 for c in LEGACY_CASES if not c["expected_auto_apply"])


def _sync_url(async_url: str) -> str:
    """
    psycopg2 sync URL for test-side row setup/verification queries only —
    the migration itself always runs through alembic/env.py's own async
    engine, exactly like every other revision in this repository.
    """
    return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest.fixture()
def engine():
    eng = create_engine(_sync_url(TEST_DATABASE_URL or ""), future=True)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def alembic_config():
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    return cfg


def _current_revision(engine) -> Optional[str]:
    from alembic.runtime.migration import MigrationContext

    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


@pytest.fixture(autouse=True)
def _baseline_at_0021(engine, alembic_config):
    """
    Ensure every test in this module starts from a clean revision-0021
    baseline, downgrading away any 0022 state a prior test in this same
    process left behind.
    """
    if _current_revision(engine) != BASELINE_REVISION:
        command.downgrade(alembic_config, BASELINE_REVISION)
    yield


@pytest.fixture(scope="module", autouse=True)
def _leave_database_at_head():
    """
    Other DB-gated test modules in this suite assume `alembic upgrade head`
    has already been applied (pipeline/tests/conftest.py's own documented
    convention) — this module's own tests intentionally downgrade to 0021
    mid-run, so restore the shared test database to head once after every
    test in this module has finished, regardless of pass/fail/skip.
    """
    yield
    if TEST_DATABASE_URL is None:
        return
    eng = create_engine(_sync_url(TEST_DATABASE_URL), future=True)
    try:
        if _current_revision(eng) != TARGET_REVISION:
            cfg = Config(str(ALEMBIC_INI))
            cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
            command.upgrade(cfg, TARGET_REVISION)
    finally:
        eng.dispose()


def _seed_people(engine, rows: list) -> None:
    """
    TRUNCATE `people` (CASCADE, matching the project's clean_db convention)
    and insert exactly the given legacy full_name-only rows — no
    first_name/middle_name/last_name/name_suffix — simulating the truly
    unconverted legacy shape this migration must backfill.
    """
    with engine.begin() as conn:
        conn.execute(text(_CLEAN_TABLES_SQL))
        for row in rows:
            conn.execute(
                text("INSERT INTO people (full_name, is_justice) VALUES (:full_name, false)"),
                {"full_name": row["full_name"]},
            )


def _fetch_full_names(engine) -> dict:
    """Pre-upgrade snapshot helper — selects only columns that exist at the
    0021 baseline (no Phase 38 columns yet)."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, full_name FROM people ORDER BY id"))
        return {row.full_name: dict(row._mapping) for row in result}


def _fetch_people(engine) -> dict:
    """Return {full_name: row-dict} — fixture full_name values are unique
    natural keys for this suite's own seeded rows."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, full_name, first_name, middle_name, last_name, "
                "name_suffix, name_needs_review, name_extraction_metadata "
                "FROM people ORDER BY id"
            )
        )
        return {row.full_name: dict(row._mapping) for row in result}


def _columns(engine) -> set:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'people'")
        )
        return {row.column_name for row in result}


# ---------------------------------------------------------------------------
# T-38-06: database-identity guard
# ---------------------------------------------------------------------------


def test_database_guard_rejects_non_test_database(monkeypatch):
    """The resolver must reject any database name other than scotus_test —
    proves this suite can never silently fall back to a production DB."""
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://user@host/scotus_dev")
    assert _resolve_test_database_url() is None


def test_database_guard_rejects_unset_url(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    assert _resolve_test_database_url() is None


# ---------------------------------------------------------------------------
# Upgrade: guarded backfill (D-04, D-10-D-12, T-38-04)
# ---------------------------------------------------------------------------


def test_upgrade_backfills_confident_rows_and_flags_ambiguous_rows(engine, alembic_config, capsys):
    """
    Confident (two/three-part, with/without suffix), whitespace near-miss,
    single-part, particle, compound, and punctuation-order fixtures — the
    full legacy_split_cases fixture set shared with Plan 01 — all produce
    deterministic reviewed/applied outcomes.
    """
    _seed_people(engine, LEGACY_CASES)
    pre_snapshot = _fetch_full_names(engine)
    assert set(pre_snapshot) == {c["full_name"] for c in LEGACY_CASES}

    command.upgrade(alembic_config, TARGET_REVISION)

    post = _fetch_people(engine)

    applied = 0
    reviewed = 0
    for case in LEGACY_CASES:
        row = post[case["full_name"]]
        # Must-have truth 1: full_name is byte-for-byte preserved for every
        # row, confident or ambiguous — this migration never writes it.
        assert row["full_name"] == case["full_name"]

        if case["expected_auto_apply"]:
            applied += 1
            assert row["first_name"] == case["expected_first_name"]
            assert row["middle_name"] == case["expected_middle_name"]
            assert row["last_name"] == case["expected_last_name"]
            assert row["name_suffix"] == case["expected_name_suffix"]
            assert row["name_needs_review"] is False
        else:
            reviewed += 1
            assert row["first_name"] is None
            assert row["middle_name"] is None
            assert row["last_name"] is None
            assert row["name_suffix"] is None
            assert row["name_needs_review"] is True

        metadata = row["name_extraction_metadata"]
        assert metadata is not None
        assert metadata["confidence"] == case["expected_confidence"]
        assert metadata["raw"] == case["full_name"]
        assert metadata["auto_applied"] == case["expected_auto_apply"]

    assert applied == EXPECTED_APPLIED
    assert reviewed == EXPECTED_REVIEWED

    report = capsys.readouterr().out
    assert f"{EXPECTED_APPLIED} applied" in report
    assert f"{EXPECTED_REVIEWED} flagged for review" in report


def test_upgrade_never_touches_rows_with_existing_structured_parts(engine, alembic_config):
    """A row that already carries any operator/import-authored name part is
    left completely untouched — never split, never flagged for review."""
    with engine.begin() as conn:
        conn.execute(text(_CLEAN_TABLES_SQL))
        conn.execute(
            text(
                "INSERT INTO people (full_name, first_name, last_name, is_justice) "
                "VALUES (:full_name, :first, :last, false)"
            ),
            {"full_name": "Sonia Sotomayor", "first": "Sonia", "last": "Sotomayor"},
        )

    command.upgrade(alembic_config, TARGET_REVISION)

    row = _fetch_people(engine)["Sonia Sotomayor"]
    assert row["first_name"] == "Sonia"
    assert row["last_name"] == "Sotomayor"
    assert row["name_needs_review"] is False
    assert row["name_extraction_metadata"] is None


def test_upgrade_aborts_on_blank_full_name_invariant_drift(engine, alembic_config):
    """
    A blank (whitespace-only) full_name violates the pre-upgrade invariant
    — the whole migration must abort/roll back rather than guess or
    silently skip it.
    """
    with engine.begin() as conn:
        conn.execute(text(_CLEAN_TABLES_SQL))
        conn.execute(
            text("INSERT INTO people (full_name, is_justice) VALUES (:full_name, false)"),
            {"full_name": "   "},
        )

    # Matched against the migration's own abort message (not just "any
    # exception") so this test cannot pass for the wrong reason — e.g. the
    # revision simply not existing yet raises a *different* CommandError
    # message ("Can't locate revision...") that must NOT satisfy this match.
    with pytest.raises(Exception, match="blank/NULL full_name"):
        command.upgrade(alembic_config, TARGET_REVISION)

    # Transactional DDL rolled the whole migration back — still at 0021,
    # the new columns were never added.
    assert _current_revision(engine) == BASELINE_REVISION
    assert "name_needs_review" not in _columns(engine)


def test_upgrade_is_repeatable_without_double_processing(engine, alembic_config):
    """
    Re-invoking upgrade at a revision it is already at is alembic's own
    no-op — running it twice must never re-process rows or change any
    persisted state (repeatability guard, T-38-04).
    """
    _seed_people(engine, LEGACY_CASES)

    command.upgrade(alembic_config, TARGET_REVISION)
    first_pass = _fetch_people(engine)

    command.upgrade(alembic_config, TARGET_REVISION)
    second_pass = _fetch_people(engine)

    assert first_pass == second_pass


# ---------------------------------------------------------------------------
# Downgrade: removes only Phase 38 state (D-04)
# ---------------------------------------------------------------------------


def test_downgrade_drops_only_phase38_columns_never_rewrites_names(engine, alembic_config):
    _seed_people(engine, LEGACY_CASES)
    command.upgrade(alembic_config, TARGET_REVISION)
    post_upgrade = _fetch_people(engine)

    command.downgrade(alembic_config, BASELINE_REVISION)

    columns = _columns(engine)
    assert "name_needs_review" not in columns
    assert "name_extraction_metadata" not in columns
    # Pre-existing structured/full_name columns are untouched by the drop.
    assert {"full_name", "first_name", "middle_name", "last_name", "name_suffix"} <= columns

    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, full_name, first_name, middle_name, last_name, name_suffix "
                "FROM people ORDER BY id"
            )
        )
        post_downgrade = {row.full_name: dict(row._mapping) for row in result}

    for full_name, pre_row in post_upgrade.items():
        post_row = post_downgrade[full_name]
        # Downgrade never reconstructs/rewrites names — every row (both
        # applied and reviewed) keeps exactly the values upgrade left it
        # with, not just full_name.
        assert post_row["full_name"] == pre_row["full_name"]
        assert post_row["first_name"] == pre_row["first_name"]
        assert post_row["middle_name"] == pre_row["middle_name"]
        assert post_row["last_name"] == pre_row["last_name"]
        assert post_row["name_suffix"] == pre_row["name_suffix"]
