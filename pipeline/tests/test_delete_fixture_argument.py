"""
Tests for scripts.delete_fixture_argument (Phase 42 Plan 02, CORPUS-14).

Covers:
    - Cascade completeness (every dependent table, plus the argument itself,
      clears with no ForeignKeyViolation).
    - Scoping: deleting one argument leaves a second, unrelated argument's
      rows completely intact.
    - Zero/multi conversation-id match: both refuse and delete nothing.
    - Report-only default: without --yes, every seeded row survives.
    - Case-link guard: --delete-case retains a case with another argument
      still linked to it, and removes a case with no other link.
    - Person safety: a referenced person row is never touched.
    - Single-transaction rollback: a mid-cascade failure leaves every row,
      including ones already deleted earlier in the same cascade, intact.

Never runs against the real dev DB -- every test seeds rows directly through
the isolated_session fixture (rolled back after the test) and patches
scripts.delete_fixture_argument.get_session so the routine under test writes
into that same rolled-back session, exactly like
pipeline/tests/test_import_convokit_core.py's established pattern.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.sql import Delete

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    Case,
    CaseArgument,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    Person,
    SideEnum,
    Utterance,
)
from scripts.delete_fixture_argument import _run

# ===========================================================================
# Shared fixtures / helpers
# ===========================================================================


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Used to patch scripts.delete_fixture_argument.get_session so tests
    inject a test-owned session (rolled back after the test) instead of
    opening a real, separately-committed DB connection. Matches the
    established pattern in pipeline/tests/test_import_convokit_core.py.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


def patch_get_session(session):
    """Shorthand for the common `with patch(..., new=_make_session_cm(session)):` call site."""
    return patch("scripts.delete_fixture_argument.get_session", new=_make_session_cm(session))


def _make_savepoint_session_cm(session):
    """
    Like _make_session_cm, but wraps the yielded session in a SAVEPOINT
    (session.begin_nested()) that rolls back to itself on any exception --
    mirroring pipeline.db.get_session's own rollback-on-exception contract
    without touching the OUTER, still-uncommitted transaction that this
    test's seed data lives in. Used only by the single-transaction test,
    where the whole point is to prove a mid-cascade failure undoes rows
    already deleted earlier in the same cascade while leaving the seed data
    (flushed, never committed, in the outer transaction) untouched.
    """

    @asynccontextmanager
    async def _cm():
        async with session.begin_nested():
            yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """
    Function-scoped AsyncSession with its own dedicated engine, rolled back
    after the test and disposed afterward -- avoids the pre-existing
    Windows/asyncpg + pytest-asyncio stale-event-loop issue documented in
    pipeline/tests/test_import_justices_csv.py's identical fixture.
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


async def _seed_person(session, full_name: str) -> Person:
    person = Person(full_name=full_name)
    session.add(person)
    await session.flush()
    return person


async def _seed_case(session, docket_number: str, term_year: int) -> Case:
    case = Case(
        docket_number=docket_number,
        docket_number_norm=docket_number,
        case_name=f"Case {docket_number}",
        term_year=term_year,
        slug=f"case-{docket_number}-{term_year}",
    )
    session.add(case)
    await session.flush()
    return case


async def _seed_argument(session, oyez_transcript_id: str, source_docket: str | None) -> Argument:
    argument = Argument(
        oyez_transcript_id=oyez_transcript_id,
        source_docket=source_docket,
        status=ArgumentStatusEnum.PIPELINE,
    )
    session.add(argument)
    await session.flush()
    return argument


async def _seed_full_fixture(session, conversation_id: str, docket: str, term_year: int) -> dict:
    """
    Seeds one Argument with a complete dependent-row set: one Utterance, one
    ImportRun, one ArgumentParticipant (linked to a real Person), one
    CaseArgument (linked to a real Case), one ArgumentStatusLog row, and one
    AdminJob referencing the argument. Returns every created row so callers
    can assert on ids and re-count afterward.
    """
    person = await _seed_person(session, full_name=f"Person for {conversation_id}")
    case = await _seed_case(session, docket, term_year)
    argument = await _seed_argument(session, conversation_id, source_docket=docket)

    import_run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    session.add(import_run)
    await session.flush()

    utterance = Utterance(
        argument_id=argument.id,
        import_run_id=import_run.id,
        sequence=1,
        text="Hello, Court.",
        side=SideEnum.PETITIONER,
        person_id=person.id,
        raw_speaker_label="MR. TEST",
    )
    session.add(utterance)

    participant = ArgumentParticipant(
        argument_id=argument.id,
        person_id=person.id,
        raw_speaker_label="MR. TEST",
        side=SideEnum.PETITIONER,
    )
    session.add(participant)

    case_argument = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    session.add(case_argument)

    status_log = ArgumentStatusLog(argument_id=argument.id, status=ArgumentStatusEnum.PIPELINE)
    session.add(status_log)

    admin_job = AdminJob(argument_id=argument.id)
    session.add(admin_job)

    await session.flush()
    return {
        "person": person,
        "case": case,
        "argument": argument,
        "import_run": import_run,
        "utterance": utterance,
        "participant": participant,
        "case_argument": case_argument,
        "status_log": status_log,
        "admin_job": admin_job,
    }


async def _count_dependents(session, argument_id: int) -> dict[str, int]:
    counts = {}
    for label, model in (
        ("utterances", Utterance),
        ("import_run", ImportRun),
        ("argument_participants", ArgumentParticipant),
        ("case_arguments", CaseArgument),
        ("argument_status_log", ArgumentStatusLog),
    ):
        result = await session.execute(
            select(func.count()).select_from(model).where(model.argument_id == argument_id)
        )
        counts[label] = result.scalar_one()
    return counts


async def _argument_count(session, argument_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Argument).where(Argument.id == argument_id)
    )
    return result.scalar_one()


# ===========================================================================
# Cascade completeness + scoping
# ===========================================================================


@pytest.mark.asyncio
async def test_destructive_delete_clears_full_cascade_no_fk_violation(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "cascade-1", "111", 1970)
    argument_id = seeded["argument"].id

    with patch_get_session(isolated_session):
        exit_code = await _run("cascade-1", False, True)

    assert exit_code == 0
    counts = await _count_dependents(isolated_session, argument_id)
    assert counts == {
        "utterances": 0,
        "import_run": 0,
        "argument_participants": 0,
        "case_arguments": 0,
        "argument_status_log": 0,
    }
    assert await _argument_count(isolated_session, argument_id) == 0

    # The cascade's AdminJob update uses synchronize_session=False (by
    # design -- see scripts/delete_fixture_argument.py), so the ORM identity
    # map still holds the pre-update in-memory value; expire it first to
    # force a fresh read from the DB rather than asserting on stale state.
    await isolated_session.refresh(seeded["admin_job"])
    assert seeded["admin_job"].argument_id is None


@pytest.mark.asyncio
async def test_scoping_deleting_one_argument_leaves_the_other_intact(isolated_session):
    target = await _seed_full_fixture(isolated_session, "scope-target", "222", 1971)
    other = await _seed_full_fixture(isolated_session, "scope-other", "333", 1972)

    with patch_get_session(isolated_session):
        exit_code = await _run("scope-target", False, True)

    assert exit_code == 0
    assert await _argument_count(isolated_session, target["argument"].id) == 0

    other_counts = await _count_dependents(isolated_session, other["argument"].id)
    assert other_counts == {
        "utterances": 1,
        "import_run": 1,
        "argument_participants": 1,
        "case_arguments": 1,
        "argument_status_log": 1,
    }
    assert await _argument_count(isolated_session, other["argument"].id) == 1


# ===========================================================================
# Zero / multi match refusal
# ===========================================================================


@pytest.mark.asyncio
async def test_zero_match_returns_nonzero_and_deletes_nothing(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "present-id", "444", 1973)

    with patch_get_session(isolated_session):
        exit_code = await _run("no-such-conversation-id", False, True)

    assert exit_code != 0
    counts = await _count_dependents(isolated_session, seeded["argument"].id)
    assert counts == {
        "utterances": 1,
        "import_run": 1,
        "argument_participants": 1,
        "case_arguments": 1,
        "argument_status_log": 1,
    }
    assert await _argument_count(isolated_session, seeded["argument"].id) == 1


@pytest.mark.asyncio
async def test_multi_match_returns_nonzero_and_deletes_nothing(isolated_session):
    dup_id = "duplicate-conversation-id"
    first = await _seed_argument(isolated_session, dup_id, source_docket=None)
    second = await _seed_argument(isolated_session, dup_id, source_docket=None)

    with patch_get_session(isolated_session):
        exit_code = await _run(dup_id, False, True)

    assert exit_code != 0
    assert await _argument_count(isolated_session, first.id) == 1
    assert await _argument_count(isolated_session, second.id) == 1


# ===========================================================================
# Report-only default
# ===========================================================================


@pytest.mark.asyncio
async def test_report_only_default_deletes_nothing(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "report-only-id", "555", 1974)

    with patch_get_session(isolated_session):
        exit_code = await _run("report-only-id", False, False)

    assert exit_code == 0
    counts = await _count_dependents(isolated_session, seeded["argument"].id)
    assert counts == {
        "utterances": 1,
        "import_run": 1,
        "argument_participants": 1,
        "case_arguments": 1,
        "argument_status_log": 1,
    }
    assert await _argument_count(isolated_session, seeded["argument"].id) == 1


# ===========================================================================
# Case-link guard
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_case_retains_case_when_another_argument_still_links_to_it(
    isolated_session,
):
    seeded = await _seed_full_fixture(isolated_session, "case-retain-id", "666", 1975)
    case = seeded["case"]

    other_argument = await _seed_argument(isolated_session, "case-retain-other", source_docket="666-b")
    isolated_session.add(
        CaseArgument(case_id=case.id, argument_id=other_argument.id, is_lead=False)
    )
    await isolated_session.flush()

    with patch_get_session(isolated_session):
        exit_code = await _run("case-retain-id", True, True)

    assert exit_code == 0
    retained_case = (
        await isolated_session.execute(select(Case).where(Case.id == case.id))
    ).scalar_one_or_none()
    assert retained_case is not None


@pytest.mark.asyncio
async def test_delete_case_removes_case_when_only_the_fixture_links_to_it(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "case-delete-id", "777", 1976)
    case_id = seeded["case"].id

    with patch_get_session(isolated_session):
        exit_code = await _run("case-delete-id", True, True)

    assert exit_code == 0
    deleted_case = (
        await isolated_session.execute(select(Case).where(Case.id == case_id))
    ).scalar_one_or_none()
    assert deleted_case is None


# ===========================================================================
# Person safety
# ===========================================================================


@pytest.mark.asyncio
async def test_person_row_survives_delete(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "person-safety-id", "888", 1977)
    person_id = seeded["person"].id

    with patch_get_session(isolated_session):
        exit_code = await _run("person-safety-id", True, True)

    assert exit_code == 0
    person = (
        await isolated_session.execute(select(Person).where(Person.id == person_id))
    ).scalar_one_or_none()
    assert person is not None


# ===========================================================================
# Single-transaction rollback on mid-cascade failure
# ===========================================================================


@pytest.mark.asyncio
async def test_single_transaction_rollback_on_mid_cascade_failure(isolated_session):
    seeded = await _seed_full_fixture(isolated_session, "rollback-id", "999", 1978)
    argument_id = seeded["argument"].id

    original_execute = isolated_session.execute

    async def _execute_with_injected_failure(statement, *args, **kwargs):
        # Fail on the SECOND delete statement in the cascade (import_run)
        # -- the FIRST delete statement (utterances) has already succeeded
        # by this point, proving the rollback also undoes earlier steps of
        # the same cascade, not just the one that raised.
        if isinstance(statement, Delete) and getattr(statement.table, "name", None) == "import_run":
            raise RuntimeError("Injected mid-cascade failure for test coverage")
        return await original_execute(statement, *args, **kwargs)

    isolated_session.execute = _execute_with_injected_failure
    try:
        with patch("scripts.delete_fixture_argument.get_session", new=_make_savepoint_session_cm(isolated_session)):
            with pytest.raises(RuntimeError, match="Injected mid-cascade failure"):
                await _run("rollback-id", False, True)
    finally:
        isolated_session.execute = original_execute

    counts = await _count_dependents(isolated_session, argument_id)
    assert counts == {
        "utterances": 1,
        "import_run": 1,
        "argument_participants": 1,
        "case_arguments": 1,
        "argument_status_log": 1,
    }
    assert await _argument_count(isolated_session, argument_id) == 1
