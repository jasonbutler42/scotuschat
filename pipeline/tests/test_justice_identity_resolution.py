"""
Tests for Phase 52 justice identity resolution.

One justice — `j__byron_r_white` — wired through every layer of the
identity stack, for keeps: mapping row -> import_justices_csv ->
Person.oyez_speaker_id/display_name -> get_argument_with_utterances's
speaker_name COALESCE -> the database's own partial unique index.

Covers JUSTICE-01/02/03/05 (52-01-PLAN.md Task 1's five `<behavior>` cases):
    1. The importer creates exactly one Person with oyez_speaker_id,
       display_name and full_name all correctly set from the mapping + CSV.
    2. Re-running against the same inputs creates no second row.
    3. An existing Person row carrying the mapped oyez_speaker_id but a
       differently-spelled full_name is matched and upgraded, not duplicated.
    4. A second Person row carrying an already-used oyez_speaker_id raises
       sqlalchemy.exc.IntegrityError from Postgres itself; two NULL-id rows
       coexist.
    5. get_argument_with_utterances projects speaker_name as
       COALESCE(display_name, full_name).

DB-dependent tests are skipped when TEST_DATABASE_URL is not configured
(see pipeline/tests/conftest.py's test_db_url fixture).
"""

import argparse
import csv
import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    Argument,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    Person,
)
from api.models.models import Utterance as UtteranceModel
from api.services.arguments import get_argument_with_utterances
from pipeline.commands.import_justices_csv import run_import_justices_csv

# ===========================================================================
# Fixtures shared with pipeline/tests/test_import_justices_csv.py's own
# per-file helpers (not imported — each test module owns its own small
# CSV-writer/session helpers per this project's established convention).
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

_MAPPING_HEADER = [
    "oyez_speaker_id",
    "corpus_display_name",
    "first_name",
    "middle_name",
    "last_name",
    "name_suffix",
]

# Byron Raymond White — real tenure-CSV shape (JFK appointee, 1962-1993).
_BYRON_WHITE_TENURE_ROW = [
    "Byron",
    "Raymond",
    "White",
    "",
    "John F. Kennedy",
    "Democratic",
    "1962-04-16",
    "1993-06-28",
    "Retired",
    "1917-06-08",
    "2002-04-15",
]

_BYRON_WHITE_MAPPING_ROW = [
    "j__byron_r_white",
    "Byron R. White",
    "Byron",
    "Raymond",
    "White",
    "",
]


def _write_justices_csv(tmp_path: Path, associate_rows: list[list[str]]) -> Path:
    """Write a small tenure CSV fixture matching the real file's two-section shape."""
    csv_path = tmp_path / "justices.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Supreme Court Chief Justices"])
        writer.writerow(_CSV_HEADER)
        writer.writerow([])
        writer.writerow(["Supreme Court Associate Justices"])
        writer.writerow(_CSV_HEADER)
        for row in associate_rows:
            writer.writerow(row)
    return csv_path


def _write_mapping_csv(tmp_path: Path, rows: list[list[str]]) -> Path:
    """Write a small justice identity mapping CSV fixture (D-06/D-07/D-08 shape)."""
    mapping_path = tmp_path / "mapping.csv"
    with mapping_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_MAPPING_HEADER)
        for row in rows:
            writer.writerow(row)
    return mapping_path


def _make_session_cm(session):
    """Context manager yielding a test-owned session in place of pipeline.db.get_session."""

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """
    Function-scoped AsyncSession with its own dedicated engine, rolled back
    after the test and disposed afterward. Own engine per test avoids the
    documented event-loop-reuse asyncpg issue (see the identical fixture in
    pipeline/tests/test_import_justices_csv.py for the full rationale).
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


# ===========================================================================
# Behavior 1-3: mapping row + CSV row -> import_justices_csv
# ===========================================================================


@pytest.mark.asyncio
async def test_import_creates_person_with_mapped_identity(isolated_session, tmp_path):
    """
    Given the mapping row for j__byron_r_white and the source CSV row for
    Byron Raymond White, the importer creates exactly one Person with
    oyez_speaker_id="j__byron_r_white", display_name="Byron R. White" and
    full_name="Byron Raymond White".
    """
    csv_path = _write_justices_csv(tmp_path, associate_rows=[_BYRON_WHITE_TENURE_ROW])
    mapping_path = _write_mapping_csv(tmp_path, [_BYRON_WHITE_MAPPING_ROW])
    args = argparse.Namespace(csv=str(csv_path), mapping_csv=str(mapping_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.oyez_speaker_id == "j__byron_r_white")
    )
    people = result.scalars().all()
    assert len(people) == 1, "Exactly one Person row for the mapped justice"
    person = people[0]
    assert person.display_name == "Byron R. White"
    assert person.full_name == "Byron Raymond White"
    assert person.is_justice is True


@pytest.mark.asyncio
async def test_rerun_creates_no_second_white_row(isolated_session, tmp_path):
    """Re-running the importer against the same inputs leaves the person count unchanged."""
    csv_path = _write_justices_csv(tmp_path, associate_rows=[_BYRON_WHITE_TENURE_ROW])
    mapping_path = _write_mapping_csv(tmp_path, [_BYRON_WHITE_MAPPING_ROW])
    args = argparse.Namespace(csv=str(csv_path), mapping_csv=str(mapping_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.oyez_speaker_id == "j__byron_r_white")
    )
    people = result.scalars().all()
    assert len(people) == 1, "Rerun must not create a second White row"


@pytest.mark.asyncio
async def test_existing_person_with_id_but_different_full_name_is_upgraded(
    isolated_session, tmp_path
):
    """
    An existing Person row that already carries
    oyez_speaker_id="j__byron_r_white" but a differently-spelled full_name
    is matched and upgraded in place, not duplicated.
    """
    existing = Person(
        full_name="A Misspelled Byron White Full Name",
        oyez_speaker_id="j__byron_r_white",
        is_justice=False,
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    csv_path = _write_justices_csv(tmp_path, associate_rows=[_BYRON_WHITE_TENURE_ROW])
    mapping_path = _write_mapping_csv(tmp_path, [_BYRON_WHITE_MAPPING_ROW])
    args = argparse.Namespace(csv=str(csv_path), mapping_csv=str(mapping_path))

    with patch(
        "pipeline.commands.import_justices_csv.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_justices_csv(args)

    result = await isolated_session.execute(
        select(Person).where(Person.oyez_speaker_id == "j__byron_r_white")
    )
    people = result.scalars().all()
    assert len(people) == 1, "Matched-by-id row must be upgraded, not duplicated"
    assert people[0].id == existing_id
    assert people[0].is_justice is True
    assert people[0].display_name == "Byron R. White"
    # full_name is never rewritten in place by this importer (pre-existing
    # behavior, unaffected by Phase 52) — only oyez_speaker_id/display_name
    # and the name-part ladder fields are touched on upgrade.
    assert people[0].full_name == "A Misspelled Byron White Full Name"


# ===========================================================================
# Behavior 4: the database itself refuses a duplicate oyez_speaker_id
# ===========================================================================


@pytest.mark.asyncio
async def test_duplicate_oyez_speaker_id_raises_integrity_error(isolated_session):
    """
    Inserting a second Person row carrying an already-used
    oyez_speaker_id raises sqlalchemy.exc.IntegrityError — refused by the
    database's uq_people_oyez_speaker_id partial unique index itself, not
    only by application code (JUSTICE-05, Success Criterion 4).
    """
    first = Person(full_name="Duplicate Id Speaker One", oyez_speaker_id="j__duplicate_test_id")
    isolated_session.add(first)
    await isolated_session.flush()

    second = Person(full_name="Duplicate Id Speaker Two", oyez_speaker_id="j__duplicate_test_id")
    isolated_session.add(second)
    with pytest.raises(IntegrityError):
        await isolated_session.flush()

    # Leave the session usable for its own rollback-based teardown.
    await isolated_session.rollback()


@pytest.mark.asyncio
async def test_multiple_null_oyez_speaker_id_rows_coexist(isolated_session):
    """
    Inserting two Person rows both carrying oyez_speaker_id=None succeeds —
    the partial unique index's WHERE oyez_speaker_id IS NOT NULL predicate
    exempts NULLs, which is what lets D-04's Barrett/Jackson (and every
    non-corpus-resolved advocate) coexist.
    """
    first = Person(full_name="Null Id Speaker One")
    second = Person(full_name="Null Id Speaker Two")
    isolated_session.add_all([first, second])
    await isolated_session.flush()  # must not raise

    assert first.id is not None
    assert second.id is not None
    assert first.oyez_speaker_id is None
    assert second.oyez_speaker_id is None


# ===========================================================================
# Behavior 5: speaker_name COALESCE(display_name, full_name)
# ===========================================================================


@pytest.mark.asyncio
async def test_speaker_name_coalesces_display_name_then_full_name(isolated_session):
    """
    get_argument_with_utterances returns speaker_name="Byron R. White" for
    an utterance spoken by a person with that display_name, and the
    unchanged full_name for a person whose display_name is NULL.
    """
    justice = Person(
        full_name="Byron Raymond White",
        display_name="Byron R. White",
        oyez_speaker_id="j__byron_r_white",
        is_justice=True,
    )
    advocate = Person(full_name="Test Fixture Advocate")  # display_name NULL
    isolated_session.add_all([justice, advocate])
    await isolated_session.flush()

    arg = Argument(
        status=ArgumentStatusEnum.PUBLISHED,
        argued_date=datetime.date(2020, 1, 1),
        question_number=1,
        resolved_at=datetime.datetime.now(datetime.timezone.utc),
        # get_argument_with_utterances gates on published_at AND status ==
        # PUBLISHED (BUG-01/D-02) — publish so the COALESCE assertions run.
        published_at=datetime.datetime.now(datetime.timezone.utc),
    )
    isolated_session.add(arg)
    await isolated_session.flush()

    case = Case(
        docket_number="TEST-52-01-COALESCE",
        docket_number_norm="test-52-01-coalesce",
        case_name="Test Justice Identity Coalesce Case",
        term_year=2020,
        slug="test-justice-identity-coalesce-case-52-01",
    )
    isolated_session.add(case)
    await isolated_session.flush()
    isolated_session.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

    run = ImportRun(
        argument_id=arg.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    isolated_session.add(run)
    await isolated_session.flush()

    isolated_session.add_all(
        [
            UtteranceModel(
                argument_id=arg.id,
                import_run_id=run.id,
                sequence=1,
                raw_speaker_label="JUSTICE WHITE",
                text="A justice utterance.",
                person_id=justice.id,
            ),
            UtteranceModel(
                argument_id=arg.id,
                import_run_id=run.id,
                sequence=2,
                raw_speaker_label="MR. ADVOCATE",
                text="An advocate utterance.",
                person_id=advocate.id,
            ),
        ]
    )
    await isolated_session.flush()

    result = await get_argument_with_utterances(isolated_session, arg.id)
    assert result is not None
    utterances_by_seq = {u["sequence"]: u for u in result["utterances"]}
    assert utterances_by_seq[1]["speaker_name"] == "Byron R. White"
    assert utterances_by_seq[2]["speaker_name"] == "Test Fixture Advocate"
