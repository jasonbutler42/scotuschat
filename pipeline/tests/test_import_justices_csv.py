"""
Tests for pipeline.commands.import_justices_csv.

Covers:
    - Task 1: reconstruct_full_name() byte-for-byte reproduction of all 13
      existing seed_aliases.py Person.full_name literals from CSV-shaped
      name parts (CORPUS-01; guards Pitfall 1 — a mismatch here means a
      silent duplicate Person row at dedup time).

    - Task 2: run_import_justices_csv() — upgrade-in-place, create-new,
      elevated-justice dual tenures, idempotency, blank end_date handling,
      and the "never touches role_id/speaker_alias" invariant (D-03).

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's async_session fixture -> test_db_url -> pytest.skip).
"""

import argparse
import csv
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import CourtTenure, Person, ReviewState, SpeakerAlias
from pipeline.commands.import_justices_csv import (
    reconstruct_full_name,
    run_import_justices_csv,
)

# ===========================================================================
# Task 1: reconstruct_full_name() — no DB required
# ===========================================================================

# (first, middle, last, suffix, expected seed_aliases.py literal)
# Values taken directly from the real justices tenure CSV rows for these
# 13 people, cross-checked against pipeline/commands/seed_aliases.py's
# _JUSTICES literal names.
_SEEDED_JUSTICE_CASES = [
    ("John", "G.", "Roberts", "Jr.", "John G. Roberts, Jr."),
    ("Clarence", "", "Thomas", "", "Clarence Thomas"),
    ("Samuel", "A.", "Alito", "Jr.", "Samuel A. Alito, Jr."),
    ("Sonia", "", "Sotomayor", "", "Sonia Sotomayor"),
    ("Elena", "", "Kagan", "", "Elena Kagan"),
    ("Neil", "M.", "Gorsuch", "", "Neil M. Gorsuch"),
    ("Brett", "M.", "Kavanaugh", "", "Brett M. Kavanaugh"),
    ("Amy", "Coney", "Barrett", "", "Amy Coney Barrett"),
    ("Ketanji", "Brown", "Jackson", "", "Ketanji Brown Jackson"),
    ("Antonin", "", "Scalia", "", "Antonin Scalia"),
    ("Anthony", "M.", "Kennedy", "", "Anthony M. Kennedy"),
    ("Ruth", "Bader", "Ginsburg", "", "Ruth Bader Ginsburg"),
    ("Stephen", "G.", "Breyer", "", "Stephen G. Breyer"),
]


@pytest.mark.parametrize(
    "first,middle,last,suffix,expected",
    _SEEDED_JUSTICE_CASES,
    ids=[case[4] for case in _SEEDED_JUSTICE_CASES],
)
def test_reconstruct_full_name_matches_seed_aliases_literal(
    first, middle, last, suffix, expected
):
    """Each of the 13 seeded justices must reconstruct byte-identically."""
    assert reconstruct_full_name(first, middle, last, suffix) == expected


def test_reconstruct_full_name_no_middle_name_no_double_space():
    result = reconstruct_full_name("Clarence", "", "Thomas", "")
    assert "  " not in result
    assert result == "Clarence Thomas"


def test_reconstruct_full_name_no_suffix_no_trailing_comma():
    result = reconstruct_full_name("Elena", "", "Kagan", "")
    assert not result.endswith(",")
    assert "," not in result


def test_reconstruct_full_name_with_suffix_matches_exact_seed_form():
    result = reconstruct_full_name("John", "G.", "Roberts", "Jr.")
    assert result == "John G. Roberts, Jr."


def test_reconstruct_full_name_all_13_seeded_justices_reproduced():
    """
    Guards Pitfall 1 directly: every one of the 13 seed_aliases.py literals
    must be reproduced exactly (or via an explicit MANUAL_NAME_OVERRIDES
    entry), or D-02's exact-match dedup silently creates duplicate Person
    rows instead of upgrading the existing seeded row.
    """
    for first, middle, last, suffix, expected in _SEEDED_JUSTICE_CASES:
        assert reconstruct_full_name(first, middle, last, suffix) == expected


# ===========================================================================
# Task 2: run_import_justices_csv() — DB-dependent integration tests
# ===========================================================================

_CSV_HEADER = [
    "First Name",
    "Middle Name or Initial",
    "Last Name",
    "Suffix",
    "Appointed by",
    "Party",
    "Judicial Oath Taken",
    "Date Service Terminated",
    "Reason Left",
    "Birthdate",
    "Death Date",
]


def _write_justices_csv(
    tmp_path: Path,
    chief_rows: list[list[str]],
    associate_rows: list[list[str]],
) -> Path:
    """Write a small CSV fixture matching the real justices CSV's two-section shape."""
    csv_path = tmp_path / "justices.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Supreme Court Chief Justices"])
        writer.writerow(_CSV_HEADER)
        for row in chief_rows:
            writer.writerow(row)
        writer.writerow([])
        writer.writerow(["Supreme Court Associate Justices"])
        writer.writerow(_CSV_HEADER)
        for row in associate_rows:
            writer.writerow(row)
    return csv_path


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Used to patch pipeline.db.get_session so tests inject a test-owned
    session (rolled back after the test) instead of opening a real,
    separately-committed DB connection. Matches the established pattern in
    pipeline/tests/test_ingest.py.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """
    Function-scoped AsyncSession with its own dedicated engine, rolled back
    after the test and disposed afterward.

    This file has more DB-writing async tests than most pipeline test
    modules. Reusing conftest.py's session-scoped `engine` fixture across
    several of them reproduces a pre-existing Windows/asyncpg +
    pytest-asyncio's function-scoped-event-loop incompatibility — the exact
    same `_ProactorSocketTransport ... AttributeError: 'NoneType' object has
    no attribute 'send'` failure already present, independently of this
    plan, in pipeline/tests/test_import_run.py::test_rerun_creates_new_rows
    (a documented pre-existing issue: the engine's asyncpg connection pool
    binds to whichever event loop was active on first use, then breaks when
    a later test gets a fresh event loop). Giving each test its own engine
    avoids the stale-loop reuse entirely, without touching conftest.py or
    any other test module.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        test_db_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_missing_csv_path_raises_file_not_found():
    """
    Path validation (T-29-08) happens before any DB session is opened, so
    this test requires no DATABASE_URL.
    """
    args = argparse.Namespace(csv=r"C:\definitely\does\not\exist\justices.csv")
    with pytest.raises(FileNotFoundError):
        await run_import_justices_csv(args)


@pytest.mark.asyncio
async def test_upgrades_existing_person_in_place(isolated_session, tmp_path):
    """
    An existing Person row matching a CSV row's reconstructed full_name is
    upgraded (is_justice=True + exactly one CourtTenure added) in place —
    not duplicated (D-02/D-03). role_id is left untouched.
    """
    existing = Person(full_name="Testcase Q. Fixture", is_justice=False)
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id
    original_role_id = existing.role_id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "Q.",
                "Fixture",
                "",
                "Fictional President",
                "Republican",
                "1986-09-26",
                "2016-02-13",
                "Died",
                "1936-03-11",
                "2016-02-13",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase Q. Fixture")
    )
    people = result.scalars().all()
    assert len(people) == 1, "Upgrade must not duplicate the Person row"
    assert people[0].id == existing_id
    assert people[0].is_justice is True
    assert people[0].role_id == original_role_id  # untouched, per D-03

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == existing_id)
    )
    tenures = tenure_result.scalars().all()
    assert len(tenures) == 1
    assert tenures[0].office == "associate"
    assert tenures[0].end_date is not None

    alias_result = await isolated_session.execute(
        select(SpeakerAlias).where(SpeakerAlias.person_id == existing_id)
    )
    assert alias_result.scalars().all() == []


@pytest.mark.asyncio
async def test_elevated_justice_gets_two_tenures(isolated_session, tmp_path):
    """
    A justice appearing in both the Chief and Associate sections (e.g. the
    real Rehnquist/Rutledge cases, D-04) gets both court_tenures rows
    auto-created for a single Person row — not flagged for manual review.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[
            [
                "Testcase",
                "H.",
                "Elevated",
                "",
                "Fictional President A",
                "Republican",
                "1986-09-26",
                "2005-09-03",
                "Died",
                "1924-10-01",
                "2005-09-03",
            ],
        ],
        associate_rows=[
            [
                "Testcase",
                "H.",
                "Elevated",
                "",
                "Fictional President B",
                "Republican",
                "1972-01-07",
                "1986-09-26",
                "Promoted to Chief Justice",
                "1924-10-01",
                "2005-09-03",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase H. Elevated")
    )
    people = result.scalars().all()
    assert len(people) == 1, "Elevated justice must be one Person, not two"

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == people[0].id)
    )
    tenures = tenure_result.scalars().all()
    assert len(tenures) == 2
    assert {t.office for t in tenures} == {"chief", "associate"}
    assert {t.start_date.isoformat() for t in tenures} == {
        "1986-09-26",
        "1972-01-07",
    }


@pytest.mark.asyncio
async def test_idempotent_rerun_creates_no_duplicates(isolated_session, tmp_path):
    """
    Running the same import twice must not create duplicate people or
    duplicate tenures, including for the elevated-justice dual-tenure case.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[
            [
                "Testcase",
                "H.",
                "Rerun",
                "",
                "Fictional President A",
                "Republican",
                "1986-09-26",
                "2005-09-03",
                "Died",
                "1924-10-01",
                "2005-09-03",
            ],
        ],
        associate_rows=[
            [
                "Testcase",
                "H.",
                "Rerun",
                "",
                "Fictional President B",
                "Republican",
                "1972-01-07",
                "1986-09-26",
                "Promoted to Chief Justice",
                "1924-10-01",
                "2005-09-03",
            ],
            [
                "Testcase",
                "M.",
                "Single",
                "",
                "Fictional President C",
                "Republican",
                "2017-04-10",
                "",
                "Still in Office",
                "1967-08-29",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))
    session_cm = _make_session_cm(isolated_session)

    for _ in range(2):
        with patch(
            "pipeline.commands.import_justices_csv.get_session", new=session_cm
        ):
            await run_import_justices_csv(args)

    people_result = await isolated_session.execute(
        select(Person).where(
            Person.full_name.in_(["Testcase H. Rerun", "Testcase M. Single"])
        )
    )
    people = people_result.scalars().all()
    assert len(people) == 2, f"Expected 2 people after 2 runs, got {len(people)}"

    person_ids = [p.id for p in people]
    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id.in_(person_ids))
    )
    tenures = tenure_result.scalars().all()
    assert len(tenures) == 3, (
        f"Expected 3 tenures (2 for Rerun + 1 for Single) after 2 runs, "
        f"got {len(tenures)} — idempotency failure"
    )


@pytest.mark.asyncio
async def test_blank_end_date_yields_none(isolated_session, tmp_path):
    """A blank 'Date Service Terminated' cell yields CourtTenure.end_date=None."""
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "M.",
                "Active",
                "",
                "Fictional President",
                "Republican",
                "2017-04-10",
                "",
                "Still in Office",
                "1967-08-29",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase M. Active")
    )
    person = result.scalar_one()

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == person.id)
    )
    tenure = tenure_result.scalar_one()
    assert tenure.end_date is None
    assert tenure.start_date.isoformat() == "2017-04-10"


@pytest.mark.asyncio
async def test_new_person_gets_structured_parts_and_provenance(
    isolated_session, tmp_path
):
    """
    Phase 38 (D-14, D-18): a brand-new justice created by this command gets
    its structured parts populated directly from the CSV row (not left
    blank), plus a provenance_metadata envelope stamped
    source="import_justices_csv", confidence="High", auto_applied=True — and
    review_state is never left needs_review, since CSV columns are
    authoritative per-column ground truth, not an inferred split.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "P.",
                "Provenance",
                "Jr.",
                "Fictional President",
                "Democratic",
                "1990-01-01",
                "",
                "Still in Office",
                "1940-01-01",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase P. Provenance, Jr.")
    )
    person = result.scalar_one()

    assert person.first_name == "Testcase"
    assert person.middle_name == "P."
    assert person.last_name == "Provenance"
    assert person.name_suffix == "Jr."
    assert person.review_state == ReviewState.UNREVIEWED
    assert person.provenance_metadata is not None
    assert person.provenance_metadata["source"] == "import_justices_csv"
    assert person.provenance_metadata["confidence"] == "High"
    assert person.provenance_metadata["auto_applied"] is True
    assert (
        person.provenance_metadata["raw"] == "Testcase P. Provenance, Jr."
    )


@pytest.mark.asyncio
async def test_rerun_preserves_operator_edited_parts_blank_only_prefill(
    isolated_session, tmp_path
):
    """
    Phase 38 (D-16/T-38-11): a rerun of this import must never overwrite a
    part an operator has already saved on the matched row — even though the
    CSV row's own reconstructed full_name string is what located the row —
    but any part still blank on that row gets prefilled from the CSV.
    """
    existing = Person(
        full_name="Testcase Q. Preserve",
        is_justice=False,
        first_name="OperatorEdited",  # deliberately differs from CSV's "Testcase"
        # middle_name/last_name/name_suffix intentionally left blank —
        # eligible for CSV blank-only prefill.
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "Q.",
                "Preserve",
                "",
                "Fictional President",
                "Republican",
                "1980-01-01",
                "",
                "Still in Office",
                "1930-01-01",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.id == existing_id)
    )
    person = result.scalar_one()

    # Operator-edited first_name is preserved byte-for-byte, never overwritten.
    assert person.first_name == "OperatorEdited"
    # middle_name/last_name were blank — prefilled from the CSV row.
    assert person.middle_name == "Q."
    assert person.last_name == "Preserve"
    assert person.is_justice is True
    # Provenance still refreshed even though no CSV-authoritative part won.
    assert person.provenance_metadata["source"] == "import_justices_csv"
    assert person.review_state == ReviewState.UNREVIEWED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operator_state",
    [ReviewState.OPERATOR_CONFIRMED, ReviewState.OPERATOR_EDITED],
)
async def test_rerun_preserves_operator_review_state(
    isolated_session, tmp_path, operator_state
):
    """
    CR-03 fix (49-REVIEW.md): a rerun of this (explicitly rerunnable)
    importer must never discard an operator-authored review_state.
    review_state was the ONE field in the "person already exists" branch
    that was NOT blank-only-prefill-guarded — it was unconditionally reset
    to UNREVIEWED on every rerun, silently re-injecting an already-reviewed
    Justice back into the People review queue
    (`_person_attention_predicate` includes UNREVIEWED). Mirrors
    pipeline/commands/import_convokit.py's
    `_apply_extracted_name_provenance`, which never mints OR erases a
    human-only review state.
    """
    existing = Person(
        full_name="Testcase Q. Preserve",
        is_justice=False,
        review_state=operator_state,
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "Q.",
                "Preserve",
                "",
                "Fictional President",
                "Republican",
                "1980-01-01",
                "",
                "Still in Office",
                "1930-01-01",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.id == existing_id)
    )
    person = result.scalar_one()

    # The operator-authored review_state survives the rerun byte-for-byte —
    # never reset to UNREVIEWED — even though every other eligible field
    # (is_justice, blank name parts, provenance_metadata) is still updated.
    assert person.review_state == operator_state
    assert person.is_justice is True
    assert person.provenance_metadata["source"] == "import_justices_csv"


@pytest.mark.asyncio
async def test_rerun_refreshes_provenance_metadata_on_second_run(
    isolated_session, tmp_path
):
    """
    Phase 38 (D-17): a second run against an already-imported justice row
    still replaces provenance_metadata with a fresh envelope (never
    leaves the first run's envelope stale), even though no new part is
    written the second time.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "R.",
                "Refresh",
                "",
                "Fictional President",
                "Republican",
                "1988-01-01",
                "",
                "Still in Office",
                "1938-01-01",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))
    session_cm = _make_session_cm(isolated_session)

    for _ in range(2):
        with patch(
            "pipeline.commands.import_justices_csv.get_session", new=session_cm
        ):
            await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase R. Refresh")
    )
    person = result.scalar_one()
    assert person.provenance_metadata is not None
    assert person.provenance_metadata["source"] == "import_justices_csv"
    assert person.provenance_metadata["confidence"] == "High"
    assert person.provenance_metadata["auto_applied"] is True


@pytest.mark.asyncio
async def test_new_person_never_gets_role_id_or_speaker_alias(isolated_session, tmp_path):
    """A brand-new justice created by this command never gets role_id or a
    speaker_alias row — those remain the sole province of seed_aliases.py."""
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "",
                "NoAlias",
                "",
                "Fictional President",
                "Democratic",
                "1955-11-15",
                "1970-01-01",
                "Retired",
                "1900-01-01",
                "1980-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase NoAlias")
    )
    person = result.scalar_one()
    assert person.role_id is None
    assert person.oyez_speaker_id is None

    alias_result = await isolated_session.execute(
        select(SpeakerAlias).where(SpeakerAlias.person_id == person.id)
    )
    assert alias_result.scalars().all() == []


# ===========================================================================
# Phase 39 Plan 02: birthdate / death_date / reason_left backfill contract
# ===========================================================================


@pytest.mark.asyncio
async def test_new_person_and_tenure_gets_birthdate_death_date_and_reason_left(
    isolated_session, tmp_path
):
    """
    A brand-new person + new tenure from a CSV row with Birthdate, Death
    Date and Reason Left=Died gets Person.birthdate, Person.death_date set
    from the CSV and CourtTenure.reason_left == 'died' (D-04, D-05).
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "D.",
                "Died",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",
                "1920-01-01",
                "1990-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase D. Died")
    )
    person = result.scalar_one()
    assert person.birthdate.isoformat() == "1920-01-01"
    assert person.death_date.isoformat() == "1990-01-01"

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == person.id)
    )
    tenure = tenure_result.scalar_one()
    assert tenure.reason_left == "died"


@pytest.mark.asyncio
async def test_backfill_never_overwrites_operator_birthdate_or_death_date(
    isolated_session, tmp_path
):
    """
    D-06 regression guard: a pre-existing Person with an operator-set
    birthdate AND an operator-set death_date that differ from the CSV
    retains BOTH operator values, unchanged, after import.
    """
    existing = Person(
        full_name="Testcase O. Preserved",
        is_justice=False,
        birthdate=date(1900, 5, 5),
        death_date=date(1985, 5, 5),
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "O.",
                "Preserved",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",
                "1920-01-01",  # differs from the operator-set birthdate above
                "1990-01-01",  # differs from the operator-set death_date above
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.id == existing_id)
    )
    person = result.scalar_one()
    assert person.birthdate == date(1900, 5, 5)
    assert person.death_date == date(1985, 5, 5)


@pytest.mark.asyncio
async def test_backfill_fills_blank_birthdate_and_death_date(
    isolated_session, tmp_path
):
    """
    A pre-existing Person with birthdate=None, death_date=None gets both
    filled from the CSV after import.
    """
    existing = Person(full_name="Testcase B. Blank", is_justice=False)
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "B.",
                "Blank",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",
                "1920-01-01",
                "1990-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.id == existing_id)
    )
    person = result.scalar_one()
    assert person.birthdate.isoformat() == "1920-01-01"
    assert person.death_date.isoformat() == "1990-01-01"


@pytest.mark.asyncio
async def test_backfill_fills_blank_tenure_reason_left(isolated_session, tmp_path):
    """
    A pre-existing CourtTenure matching (person_id, office, start_date) with
    reason_left=None gets filled from the CSV after import.
    """
    existing_person = Person(full_name="Testcase T. Blankreason", is_justice=True)
    isolated_session.add(existing_person)
    await isolated_session.flush()

    existing_tenure = CourtTenure(
        person_id=existing_person.id,
        office="associate",
        start_date=date(1970, 1, 1),
        end_date=date(1990, 1, 1),
        reason_left=None,
    )
    isolated_session.add(existing_tenure)
    await isolated_session.flush()
    tenure_id = existing_tenure.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "T.",
                "Blankreason",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",
                "1920-01-01",
                "1990-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.id == tenure_id)
    )
    tenure = result.scalar_one()
    assert tenure.reason_left == "died"


@pytest.mark.asyncio
async def test_backfill_never_overwrites_operator_reason_left(
    isolated_session, tmp_path
):
    """
    D-06 regression guard: a pre-existing CourtTenure with an operator-set
    reason_left='retired' keeps that exact value after import, even though
    the matching CSV row's Reason Left cell says Died.
    """
    existing_person = Person(full_name="Testcase T. Operatorreason", is_justice=True)
    isolated_session.add(existing_person)
    await isolated_session.flush()

    existing_tenure = CourtTenure(
        person_id=existing_person.id,
        office="associate",
        start_date=date(1970, 1, 1),
        end_date=date(1990, 1, 1),
        reason_left="retired",
    )
    isolated_session.add(existing_tenure)
    await isolated_session.flush()
    tenure_id = existing_tenure.id

    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "T.",
                "Operatorreason",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",  # differs from the operator-set 'retired' above
                "1920-01-01",
                "1990-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.id == tenure_id)
    )
    tenure = result.scalar_one()
    assert tenure.reason_left == "retired"


@pytest.mark.asyncio
async def test_still_in_office_tenure_has_no_reason_left(isolated_session, tmp_path):
    """
    D-02: a CSV row with Reason Left=Still in Office creates a tenure with
    reason_left is None — an open tenure never carries a reason.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "S.",
                "Open",
                "",
                "Fictional President",
                "Democratic",
                "2020-01-01",
                "",
                "Still in Office",
                "1970-01-01",
                "",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase S. Open")
    )
    person = result.scalar_one()

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == person.id)
    )
    tenure = tenure_result.scalar_one()
    assert tenure.reason_left is None


@pytest.mark.asyncio
async def test_unrecognised_reason_left_is_null_and_reported(
    isolated_session, tmp_path, capsys
):
    """
    A CSV Reason Left value outside the recognised vocabulary (e.g.
    'Impeached') stores reason_left=None on the created tenure AND the
    run's captured stdout names the unrecognised value — an unrecognised
    value must be surfaced, not only silently coerced.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "I.",
                "Impeached",
                "",
                "Fictional President",
                "Democratic",
                "1900-01-01",
                "1910-01-01",
                "Impeached",
                "1860-01-01",
                "1915-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    captured = capsys.readouterr()
    assert "Impeached" in captured.out

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase I. Impeached")
    )
    person = result.scalar_one()

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == person.id)
    )
    tenure = tenure_result.scalar_one()
    assert tenure.reason_left is None


@pytest.mark.asyncio
async def test_second_run_creates_no_duplicates_and_changes_no_field_values(
    isolated_session, tmp_path
):
    """
    D-07: two consecutive runs over the same CSV create no duplicate people
    or tenures, and the second run changes no field values from what the
    first run wrote.
    """
    csv_path = _write_justices_csv(
        tmp_path,
        chief_rows=[],
        associate_rows=[
            [
                "Testcase",
                "I.",
                "Dempotent",
                "",
                "Fictional President",
                "Republican",
                "1970-01-01",
                "1990-01-01",
                "Died",
                "1920-01-01",
                "1990-01-01",
            ],
        ],
    )
    args = argparse.Namespace(csv=str(csv_path))
    session_cm = _make_session_cm(isolated_session)

    with patch("pipeline.commands.import_justices_csv.get_session", new=session_cm):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase I. Dempotent")
    )
    person_after_first = result.scalar_one()
    first_birthdate = person_after_first.birthdate
    first_death_date = person_after_first.death_date

    tenure_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == person_after_first.id)
    )
    tenure_after_first = tenure_result.scalar_one()
    first_reason_left = tenure_after_first.reason_left

    with patch("pipeline.commands.import_justices_csv.get_session", new=session_cm):
        await run_import_justices_csv(args)

    people_result = await isolated_session.execute(
        select(Person).where(Person.full_name == "Testcase I. Dempotent")
    )
    people = people_result.scalars().all()
    assert len(people) == 1, "Second run must not create a duplicate Person"
    assert people[0].birthdate == first_birthdate
    assert people[0].death_date == first_death_date

    tenures_result = await isolated_session.execute(
        select(CourtTenure).where(CourtTenure.person_id == people[0].id)
    )
    tenures = tenures_result.scalars().all()
    assert len(tenures) == 1, "Second run must not create a duplicate CourtTenure"
    assert tenures[0].reason_left == first_reason_left
