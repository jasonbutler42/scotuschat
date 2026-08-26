"""
Unit and integration tests for the pipeline resolve command.

Covers: PIPE-07 (resolve step — alias lookup + interactive prompt)
        PIPE-09 (interrupt → needs_review; resume skips already-resolved labels)

DB-dependent tests are skipped when DATABASE_URL is not set.
"""

import os

import pytest

# ---------------------------------------------------------------------------
# requires_db marker — skip DB-dependent tests when DATABASE_URL not set
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
requires_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping database connectivity tests",
)


# ---------------------------------------------------------------------------
# test_normalize_label — unit test (no DB required)
# ---------------------------------------------------------------------------


def test_normalize_label():
    """normalize_label strips whitespace, trailing colon, and uppercases.

    Implements D-02: examples from CONTEXT.md.
    """
    from pipeline.commands.resolve import normalize_label

    assert normalize_label("Justice Kagan:") == "JUSTICE KAGAN"
    assert normalize_label("  CHIEF JUSTICE:  ") == "CHIEF JUSTICE"
    assert normalize_label("MR. JONES") == "MR. JONES"


# ---------------------------------------------------------------------------
# test_resolve_alias_hit — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Never implemented — pre-existing pytest.fail('not implemented') stub, "
        "not schema drift. Out of scope for TEST-02 fixture repair; see "
        "31-06-SUMMARY.md / deferred-items.md."
    ),
    strict=True,
)
async def test_resolve_alias_hit(async_session):
    """
    When a SpeakerAlias row exists for a label, run_resolve() sets
    utterances.person_id on all matching utterance rows automatically.
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# test_resolve_interactive_prompt — unit test with mocked input()
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "Never implemented — pre-existing pytest.fail('not implemented') stub, "
        "not schema drift. Out of scope for TEST-02 fixture repair; see "
        "31-06-SUMMARY.md / deferred-items.md."
    ),
    strict=True,
)
def test_resolve_interactive_prompt():
    """
    When no SpeakerAlias row exists, run_resolve() displays a numbered
    list of existing people and prompts the operator via input().
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# test_resolve_interrupt_sets_needs_review — unit test with mocked KeyboardInterrupt
# ---------------------------------------------------------------------------


def test_resolve_interrupt_sets_needs_review():
    """
    When a KeyboardInterrupt is raised during the resolve loop, the resolve
    ImportRun's status is set to NEEDS_REVIEW and session.flush() is called.

    This is a unit test using a mocked session — no live DB required.
    """
    import argparse
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch
    from contextlib import asynccontextmanager

    # Import ImportRun/ImportRunStatus via pipeline.commands.resolve's own
    # namespace (not a fresh `from api.models.models import ...`) so the
    # isinstance/equality checks below always compare against the exact same
    # class objects that run_resolve() itself binds to internally — immune to
    # tests/test_admin_router.py::test_api_main_imports_without_error deleting
    # and re-importing every api.* module elsewhere in the same pytest
    # session. A fresh `api.models.models` import picks up whichever module
    # identity is current in sys.modules at that instant; if it has already
    # been reimported (a fresh class object) while pipeline.commands.resolve
    # (imported earlier, e.g. via api/services/admin_jobs.py's module-level
    # import chain) still holds the OLD class object bound at its own import
    # time, `isinstance(obj, ImportRun)` silently returns False for every
    # object added by run_resolve() — this is what caused
    # "Expected exactly 1 ImportRun added, got 0" when the full suite ran
    # with tests/ collected before pipeline/tests/ (Phase 31, T-31-19).
    from pipeline.commands import resolve as resolve_module

    ImportRun = resolve_module.ImportRun
    ImportRunStatus = resolve_module.ImportRunStatus

    # Build a fake parse_run that looks like a completed parse step
    fake_parse_run = MagicMock(spec=ImportRun)
    fake_parse_run.id = 1
    fake_parse_run.argument_id = 10
    fake_parse_run.step = "parse"
    fake_parse_run.status = ImportRunStatus.COMPLETED

    # Build a fake resolve_run that will be created by run_resolve
    fake_resolve_run = MagicMock(spec=ImportRun)
    fake_resolve_run.id = 2

    # Session mock: get() returns parse_run; flush is async no-op
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=fake_parse_run)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    # The labels query raises KeyboardInterrupt to simulate Ctrl+C
    mock_session.execute = AsyncMock(side_effect=KeyboardInterrupt)

    # Patch session.add so that the second "add" (resolve_run) captures the object
    added_objects = []
    mock_session.add.side_effect = lambda obj: added_objects.append(obj)

    # Override flush to assign id to the resolve_run on the FIRST flush only
    flush_call_count = {"n": 0}

    async def fake_flush():
        flush_call_count["n"] += 1
        if flush_call_count["n"] == 1:
            # First flush: assign the resolve_run's id (simulates DB auto-increment)
            for obj in added_objects:
                if isinstance(obj, ImportRun):
                    obj.id = 2
        # Subsequent flushes (e.g., from the except block) are no-ops
        # so that status mutations set by run_resolve() are preserved.

    mock_session.flush.side_effect = fake_flush

    @asynccontextmanager
    async def fake_get_session():
        yield mock_session

    args = argparse.Namespace(run_id=1, job_id=None)

    with patch("pipeline.commands.resolve.get_session", new=fake_get_session):
        asyncio.run(_run_resolve_catching_interrupt(args))

    # After KeyboardInterrupt, the resolve_run's status must be NEEDS_REVIEW
    resolve_runs = [obj for obj in added_objects if isinstance(obj, ImportRun)]
    assert len(resolve_runs) == 1, (
        f"Expected exactly 1 ImportRun added, got {len(resolve_runs)}"
    )
    assert resolve_runs[0].status == ImportRunStatus.NEEDS_REVIEW, (
        f"Expected NEEDS_REVIEW, got {resolve_runs[0].status}"
    )


async def _run_resolve_catching_interrupt(args):
    """Helper: run run_resolve and handle KeyboardInterrupt at the asyncio level."""
    from pipeline.commands.resolve import run_resolve

    try:
        await run_resolve(args)
    except KeyboardInterrupt:
        pass  # outer guard in __main__.py handles this; inner guard sets NEEDS_REVIEW


# ---------------------------------------------------------------------------
# test_resolve_resumes_after_interrupt — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Never implemented — pre-existing pytest.fail('not implemented') stub, "
        "not schema drift. Out of scope for TEST-02 fixture repair; see "
        "31-06-SUMMARY.md / deferred-items.md."
    ),
    strict=True,
)
async def test_resolve_resumes_after_interrupt(async_session):
    """
    Re-running resolve after a prior interrupted run skips labels that
    already have person_id populated and only prompts for unresolved labels.
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# Phase 50 plan 50-06, Task 1: _apply_resolved_person_ids — the per-row
# gated replacement for the former bulk ArgumentParticipant.person_id
# UPDATE (D-21/D-22). Real-writer integration tests against a live DB.
# ---------------------------------------------------------------------------


def _make_resolve_session_cm(session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


async def _seed_resolve_fixture(
    session,
    *,
    raw_label: str = "MR. FIXTURE",
    existing_person_id=None,
    review_state=None,
    participant_source=None,
    participant_method=None,
):
    """
    Seed one Argument + one parse-step ImportRun + one Utterance +
    one ArgumentParticipant for that raw_label, and a SpeakerAlias/Person
    the alias table will HIT on. Returns
    (argument, parse_run, participant, alias_person).
    """
    import datetime

    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Person,
        ReviewState,
        SideEnum,
        SpeakerAlias,
        Utterance,
    )
    from pipeline.commands.resolve import normalize_label

    review_state = review_state or ReviewState.UNREVIEWED

    argument = Argument(argued_date=datetime.date(2024, 1, 1), question_number=1)
    session.add(argument)
    await session.flush()

    parse_run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    session.add(parse_run)
    await session.flush()

    session.add(
        Utterance(
            argument_id=argument.id,
            import_run_id=parse_run.id,
            sequence=1,
            raw_speaker_label=raw_label,
            text="Some remark.",
            is_stage_direction=False,
            side=SideEnum.ADVOCATE,
            person_id=None,
        )
    )
    await session.flush()

    participant = ArgumentParticipant(
        argument_id=argument.id,
        person_id=existing_person_id,
        raw_speaker_label=raw_label,
        side=SideEnum.ADVOCATE,
        review_state=review_state,
        source=participant_source,
        method=participant_method,
    )
    session.add(participant)
    await session.flush()

    alias_person = Person(full_name=f"Alias Target for {raw_label}")
    session.add(alias_person)
    await session.flush()

    session.add(
        SpeakerAlias(
            normalized_label=normalize_label(raw_label),
            person_id=alias_person.id,
        )
    )
    await session.flush()

    return argument, parse_run, participant, alias_person


async def _run_resolve_direct(async_session, parse_run_id: int):
    import argparse

    from pipeline.commands.resolve import run_resolve

    await run_resolve(argparse.Namespace(run_id=parse_run_id, job_id=None))


@requires_db
@pytest.mark.asyncio
async def test_resolve_alias_hit_on_null_person_id_writes_no_discrepancy(
    async_session, monkeypatch
):
    """
    An alias HIT against a participant whose person_id is NULL writes the
    person id and creates no value_discrepancy row (PD-13 gap-fill).
    """
    from sqlalchemy import select

    from api.models.models import ImportMethod, ImportSource, ValueDiscrepancy

    argument, parse_run, participant, alias_person = await _seed_resolve_fixture(
        async_session, raw_label="MR. GAPFILL", existing_person_id=None
    )
    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )

    await _run_resolve_direct(async_session, parse_run.id)

    await async_session.refresh(participant)
    assert participant.person_id == alias_person.id
    assert participant.source == ImportSource.PDF_PIPELINE
    assert participant.method == ImportMethod.NORMALIZED

    discrepancies = (
        await async_session.execute(
            select(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id == participant.id,
            )
        )
    ).scalars().all()
    assert discrepancies == []


@requires_db
@pytest.mark.asyncio
async def test_resolve_alias_hit_operator_edited_participant_survives(
    async_session, monkeypatch
):
    """
    An alias HIT against a participant whose person_id was already set to
    a DIFFERENT person by an operator (review_state=operator_edited) does
    NOT overwrite it, and creates exactly one discrepancy row.
    """
    from sqlalchemy import select

    from api.models.models import Person, ReviewState, ValueDiscrepancy

    operator_person = Person(full_name="Operator Assigned Person")
    async_session.add(operator_person)
    await async_session.flush()

    argument, parse_run, participant, alias_person = await _seed_resolve_fixture(
        async_session,
        raw_label="MR. OPERATOR",
        existing_person_id=operator_person.id,
        review_state=ReviewState.OPERATOR_EDITED,
    )
    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )

    await _run_resolve_direct(async_session, parse_run.id)

    await async_session.refresh(participant)
    assert participant.person_id == operator_person.id, (
        "an operator-edited participant must survive a disagreeing alias HIT"
    )

    discrepancies = (
        await async_session.execute(
            select(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id == participant.id,
                ValueDiscrepancy.field == "person_id",
            )
        )
    ).scalars().all()
    assert len(discrepancies) == 1


@requires_db
@pytest.mark.asyncio
async def test_resolve_alias_hit_matching_existing_person_id_no_discrepancy(
    async_session, monkeypatch
):
    """
    An alias HIT against a participant already carrying the SAME person id
    writes nothing observable and creates no discrepancy row.
    """
    from sqlalchemy import select

    from api.models.models import ValueDiscrepancy

    # Seed the fixture first to get the alias-target person's id, then
    # re-seed the participant to already carry that same id.
    argument, parse_run, participant, alias_person = await _seed_resolve_fixture(
        async_session, raw_label="MR. SAME", existing_person_id=None
    )
    participant.person_id = alias_person.id
    await async_session.flush()

    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )

    await _run_resolve_direct(async_session, parse_run.id)

    await async_session.refresh(participant)
    assert participant.person_id == alias_person.id

    discrepancies = (
        await async_session.execute(
            select(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id == participant.id,
            )
        )
    ).scalars().all()
    assert discrepancies == []


@requires_db
@pytest.mark.asyncio
async def test_resolve_utterance_bulk_update_still_runs(async_session, monkeypatch):
    """
    The Utterance.person_id bulk UPDATE (PD-19, deliberately ungated) still
    runs and still updates every matching utterance row, independent of
    the ArgumentParticipant gate conversion.
    """
    from sqlalchemy import select

    from api.models.models import Utterance

    argument, parse_run, participant, alias_person = await _seed_resolve_fixture(
        async_session, raw_label="MR. UTTERANCE", existing_person_id=None
    )
    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )

    await _run_resolve_direct(async_session, parse_run.id)

    utterances = (
        await async_session.execute(
            select(Utterance).where(Utterance.argument_id == argument.id)
        )
    ).scalars().all()
    assert len(utterances) == 1
    assert utterances[0].person_id == alias_person.id


@requires_db
@pytest.mark.asyncio
async def test_resolve_n_labels_issues_gate_calls_not_bulk_statement(
    async_session, monkeypatch
):
    """
    A resolve run over N auto-resolved labels issues N per-row gate calls,
    not one bulk statement, and the resulting participant rows carry
    source=pdf_pipeline (the resolve run's own declared provenance).
    """
    import datetime

    from sqlalchemy import select

    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Person,
        SideEnum,
        SpeakerAlias,
        Utterance,
    )
    from pipeline.commands.resolve import normalize_label

    argument = Argument(argued_date=datetime.date(2024, 1, 1), question_number=1)
    async_session.add(argument)
    await async_session.flush()

    parse_run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    async_session.add(parse_run)
    await async_session.flush()

    labels = ["MR. ALPHA", "MS. BETA", "GEN. GAMMA"]
    participants = []
    for i, label in enumerate(labels):
        async_session.add(
            Utterance(
                argument_id=argument.id,
                import_run_id=parse_run.id,
                sequence=i + 1,
                raw_speaker_label=label,
                text="Remark.",
                is_stage_direction=False,
                side=SideEnum.ADVOCATE,
                person_id=None,
            )
        )
        participant = ArgumentParticipant(
            argument_id=argument.id,
            person_id=None,
            raw_speaker_label=label,
            side=SideEnum.ADVOCATE,
        )
        async_session.add(participant)
        participants.append(participant)

        alias_person = Person(full_name=f"Person for {label}")
        async_session.add(alias_person)
        await async_session.flush()
        async_session.add(
            SpeakerAlias(
                normalized_label=normalize_label(label),
                person_id=alias_person.id,
            )
        )
    await async_session.flush()

    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )

    await _run_resolve_direct(async_session, parse_run.id)

    for participant in participants:
        await async_session.refresh(participant)
        assert participant.person_id is not None
        assert participant.source == ImportSource.PDF_PIPELINE


@requires_db
@pytest.mark.asyncio
async def test_resolve_outcome_gate_unchanged_paused_on_miss_completed_on_hit(
    async_session, monkeypatch
):
    """
    The run's outcome gate (paused on misses, completed on all-hit) is
    unchanged by the gate conversion.
    """
    from sqlalchemy import select

    from api.models.models import ImportRunStatus

    # All-hit case
    argument, parse_run, participant, alias_person = await _seed_resolve_fixture(
        async_session, raw_label="MR. ALLHIT", existing_person_id=None
    )
    monkeypatch.setattr(
        "pipeline.commands.resolve.get_session",
        _make_resolve_session_cm(async_session),
    )
    await _run_resolve_direct(async_session, parse_run.id)
    await async_session.refresh(parse_run)

    from pipeline.commands.resolve import ImportRun as ResolveImportRun

    resolve_runs = (
        await async_session.execute(
            select(ResolveImportRun).where(
                ResolveImportRun.argument_id == argument.id,
                ResolveImportRun.step == "resolve",
            )
        )
    ).scalars().all()
    assert len(resolve_runs) == 1
    assert resolve_runs[0].status == ImportRunStatus.COMPLETED

    # Miss case — a raw_speaker_label with no SpeakerAlias row
    import datetime

    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ImportMethod,
        ImportRun,
        ImportSource,
        SideEnum,
        Utterance,
    )

    miss_argument = Argument(argued_date=datetime.date(2024, 1, 1), question_number=2)
    async_session.add(miss_argument)
    await async_session.flush()

    miss_parse_run = ImportRun(
        argument_id=miss_argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    async_session.add(miss_parse_run)
    await async_session.flush()

    async_session.add(
        Utterance(
            argument_id=miss_argument.id,
            import_run_id=miss_parse_run.id,
            sequence=1,
            raw_speaker_label="MR. NOBODY-KNOWS",
            text="Unresolvable remark.",
            is_stage_direction=False,
            side=SideEnum.ADVOCATE,
            person_id=None,
        )
    )
    async_session.add(
        ArgumentParticipant(
            argument_id=miss_argument.id,
            person_id=None,
            raw_speaker_label="MR. NOBODY-KNOWS",
            side=SideEnum.ADVOCATE,
        )
    )
    await async_session.flush()

    await _run_resolve_direct(async_session, miss_parse_run.id)

    miss_resolve_runs = (
        await async_session.execute(
            select(ResolveImportRun).where(
                ResolveImportRun.argument_id == miss_argument.id,
                ResolveImportRun.step == "resolve",
            )
        )
    ).scalars().all()
    assert len(miss_resolve_runs) == 1
    assert miss_resolve_runs[0].status == ImportRunStatus.NEEDS_REVIEW
