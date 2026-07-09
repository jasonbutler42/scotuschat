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
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import CourtTenure, Person, SpeakerAlias
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
    plan, in pipeline/tests/test_pipeline_run.py::test_rerun_creates_new_rows
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
    assert tenures[0].seat == "Associate Justice"
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
    assert {t.seat for t in tenures} == {"Chief Justice", "Associate Justice"}
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
