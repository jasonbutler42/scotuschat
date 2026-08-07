"""
Phase 25 Plan 01 — backend job-detail contract tests.

Covers:
  Task 1: RunReadiness / ReadinessBlocker / FailedStepRecovery schemas,
          get_job_readiness, derive_failed_step_recovery, get_failed_step_recovery
          (D-01 through D-08, D-18, D-20, PJOB-01/02/08/22).
  Task 2: PersonCreate side/raw_speaker_label extension, create_person_for_job
          job-scoped mini create-person mutation (D-12, D-13, PJOB-19).
  Task 3: ResolveRowUpdate schema, update_resolve_row_for_job job-scoped
          resolve-row side/descriptor mutation (D-14, D-18, D-19, PJOB-14, PJOB-18).

Following the project pattern (test_admin_jobs_stats.py, test_admin_jobs_service.py):
  - Schema/pure-function tests run without a database.
  - Structural (source-inspection) tests assert guard patterns without a database.
  - Behavioral tests that need real rows are gated behind a DATABASE_URL skipif.
"""

import inspect
import os

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ===========================================================================
# Task 1: Run readiness and failed recovery
# ===========================================================================


# ---------------------------------------------------------------------------
# Schema tests (no DB required)
# ---------------------------------------------------------------------------


def test_readiness_blocker_schema_fields() -> None:
    from api.schemas.admin_jobs import ReadinessBlocker

    blocker = ReadinessBlocker(code="no_docket", message="Add at least one docket.")
    assert blocker.code == "no_docket"
    assert blocker.message == "Add at least one docket."


def test_run_readiness_schema_states() -> None:
    from api.schemas.admin_jobs import ReadinessBlocker, RunReadiness

    ready = RunReadiness(state="ready", blockers=[])
    assert ready.state == "ready"
    assert ready.blockers == []
    assert ready.argument_edit_href is None

    not_ready = RunReadiness(
        state="not_ready",
        blockers=[ReadinessBlocker(code="no_argument", message="No linked argument yet.")],
    )
    assert not_ready.state == "not_ready"
    assert len(not_ready.blockers) == 1

    already_created = RunReadiness(
        state="already_created", blockers=[], argument_edit_href="/admin/arguments/42"
    )
    assert already_created.argument_edit_href == "/admin/arguments/42"


def test_run_readiness_rejects_unknown_state() -> None:
    from pydantic import ValidationError

    from api.schemas.admin_jobs import RunReadiness

    with pytest.raises(ValidationError):
        RunReadiness(state="bogus", blockers=[])


def test_failed_step_recovery_schema_fields() -> None:
    from api.schemas.admin_jobs import FailedStepRecovery

    recovery = FailedStepRecovery(
        step="ingest",
        guidance="Check the PDF source or upload, then start a new run.",
        href="/admin/pipeline/",
        raw_error="HTTP 404 fetching PDF",
    )
    assert recovery.step == "ingest"
    assert recovery.href == "/admin/pipeline/"
    assert recovery.raw_error == "HTTP 404 fetching PDF"
    # Guidance and raw_error are separate fields (T-25-03) — never merged.
    assert recovery.raw_error not in recovery.guidance


def test_admin_job_response_unaffected_by_phase25_schemas() -> None:
    """Adding RunReadiness/FailedStepRecovery must not break AdminJobResponse."""
    from api.schemas.admin_jobs import AdminJobResponse

    config = getattr(AdminJobResponse, "model_config", {})
    assert config.get("from_attributes", False), (
        "AdminJobResponse must retain from_attributes=True after Phase 25 additions"
    )


# ---------------------------------------------------------------------------
# Pure-function tests (no DB required) — Test 3: failed recovery guidance
# ---------------------------------------------------------------------------


def test_derive_failed_step_recovery_ingest_guidance() -> None:
    from api.models.models import AdminJobStep
    from api.services.admin_jobs import derive_failed_step_recovery

    recovery = derive_failed_step_recovery(AdminJobStep.INGEST, "raw ingest error")
    assert recovery.step == "ingest"
    assert "PDF" in recovery.guidance
    assert recovery.href == "/admin/pipeline/"
    assert recovery.raw_error == "raw ingest error"
    assert recovery.raw_error not in recovery.guidance


def test_derive_failed_step_recovery_parse_guidance() -> None:
    from api.models.models import AdminJobStep
    from api.services.admin_jobs import derive_failed_step_recovery

    recovery = derive_failed_step_recovery(AdminJobStep.PARSE, "raw parse error")
    assert recovery.step == "parse"
    assert "transcript" in recovery.guidance.lower()
    assert recovery.raw_error == "raw parse error"


def test_derive_failed_step_recovery_resolve_guidance() -> None:
    from api.models.models import AdminJobStep
    from api.services.admin_jobs import derive_failed_step_recovery

    recovery = derive_failed_step_recovery(AdminJobStep.RESOLVE, "raw resolve error")
    assert recovery.step == "resolve"
    assert "alias" in recovery.guidance.lower() or "people" in recovery.guidance.lower()


def test_derive_failed_step_recovery_unknown_step_default_guidance() -> None:
    from api.services.admin_jobs import derive_failed_step_recovery

    recovery = derive_failed_step_recovery(None, "raw unknown error")
    assert recovery.step is None
    assert recovery.href == "/admin/pipeline/"
    assert "new run" in recovery.guidance.lower()


def test_ordinary_new_run_recovery_never_recommends_same_source_recreation() -> None:
    """Recovery remains step-specific and never recommends recreating the same source."""
    from api.models.models import AdminJobStep
    from api.services.admin_jobs import derive_failed_step_recovery

    for step in (AdminJobStep.INGEST, AdminJobStep.PARSE, AdminJobStep.RESOLVE, None):
        recovery = derive_failed_step_recovery(step, None)
        assert "same source" not in recovery.guidance.lower()
        assert "rerun" not in recovery.guidance.lower()
        assert "re-run" not in recovery.guidance.lower()


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_get_job_readiness_importable() -> None:
    from api.services.admin_jobs import get_job_readiness  # noqa: F401


def test_get_job_readiness_already_created_short_circuits() -> None:
    """Source-level guard: already_created must be derived from argument.status,
    independent of any other blocker check (D-01, D-04, D-18, D-20)."""
    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def get_job_readiness(")
    assert func_start != -1
    next_func = source.find("\nasync def ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "already_created" in func_body
    assert "ArgumentStatusEnum.PIPELINE" in func_body


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_readiness_already_created_when_argument_not_pipeline(db_session) -> None:
    """Test 1: readiness is already_created when the linked argument is no longer
    pipeline, matching D-01, D-04, D-18, and D-20."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
    )
    from api.services.admin_jobs import get_job_readiness

    arg = Argument(status=ArgumentStatusEnum.DRAFT, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.COMPLETED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    readiness = await get_job_readiness(db_session, job.id)

    assert readiness.state == "already_created"
    assert readiness.blockers == []
    assert readiness.argument_edit_href == f"/admin/arguments/{arg.id}"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_readiness_ready_when_all_conditions_met(db_session) -> None:
    """Test 2: readiness is ready only when the job has an argument, docket,
    question number, argued date, all resolve rows dispositioned, and no
    failed/running blocker per D-02 and D-03."""
    import datetime

    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.services.admin_jobs import get_job_readiness

    person = Person(full_name="Jordan Rivera")
    db_session.add(person)
    await db_session.flush()

    arg = Argument(
        status=ArgumentStatusEnum.PIPELINE,
        question_number=1,
        argued_date=datetime.date(2024, 1, 10),
        source_docket="23-100",
        source_dockets=["23-100"],
    )
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="MS. RIVERA",
        side=SideEnum.PETITIONER,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    readiness = await get_job_readiness(db_session, job.id)

    assert readiness.state == "ready"
    assert readiness.blockers == []


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_readiness_not_ready_with_strict_blockers(db_session) -> None:
    """Test 2b: missing docket/argued_date/unresolved rows and a failed job all
    surface as strict not_ready blockers (D-02)."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.services.admin_jobs import get_job_readiness

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    unresolved = ArgumentParticipant(
        argument_id=arg.id,
        person_id=None,
        raw_speaker_label="MR. UNKNOWN",
        side=SideEnum.UNKNOWN,
    )
    db_session.add(unresolved)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.FAILED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    readiness = await get_job_readiness(db_session, job.id)

    assert readiness.state == "not_ready"
    codes = {b.code for b in readiness.blockers}
    assert "no_docket" in codes
    assert "no_argued_date" in codes
    assert "unresolved_rows" in codes
    assert "job_failed" in codes


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_failed_step_recovery_loads_job_and_derives_guidance(db_session) -> None:
    """Test 3: failed recovery returns step-specific guidance, a pipeline-page
    href, and the raw error separately per D-05 through D-08 and PJOB-22."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import get_failed_step_recovery

    job = AdminJob(
        status=AdminJobStatus.FAILED,
        current_step=AdminJobStep.PARSE,
        error_message="Traceback: LLM extraction failed",
    )
    db_session.add(job)
    await db_session.flush()

    recovery = await get_failed_step_recovery(db_session, job.id)

    assert recovery.step == "parse"
    assert recovery.href == "/admin/pipeline/"
    assert recovery.raw_error == "Traceback: LLM extraction failed"
    assert recovery.raw_error not in recovery.guidance


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_readiness_raises_for_missing_job(db_session) -> None:
    from api.services.admin_jobs import get_job_readiness

    with pytest.raises(ValueError):
        await get_job_readiness(db_session, 999999)


# ===========================================================================
# Task 2: Mini create-person job support with side and is_justice
# ===========================================================================


# ---------------------------------------------------------------------------
# Schema tests (no DB required)
# ---------------------------------------------------------------------------


def test_person_create_accepts_raw_speaker_label_and_side() -> None:
    from api.models.models import SideEnum
    from api.schemas.admin_jobs import PersonCreate

    body = PersonCreate(
        last_name="Jackson",
        first_name="Ketanji",
        middle_name="Brown",
        raw_speaker_label="JUSTICE JACKSON",
        side=SideEnum.BENCH,
    )
    assert body.raw_speaker_label == "JUSTICE JACKSON"
    assert body.side == SideEnum.BENCH


def test_person_create_backward_compatible_without_side() -> None:
    """Legacy callers that omit raw_speaker_label/side must still validate (backward compat)."""
    from api.schemas.admin_jobs import PersonCreate

    body = PersonCreate(first_name="Jane", last_name="Doe", role_name="Law Clerk")
    assert body.raw_speaker_label is None
    assert body.side is None


# ---------------------------------------------------------------------------
# Phase 38 (T-38-07): PersonCreate rejects a client-supplied full_name and
# enforces the D-09 first-or-last minimum-data invariant server-side
# ---------------------------------------------------------------------------


def test_person_create_rejects_full_name_as_extra_field() -> None:
    """PersonCreate has no full_name field; posting one is a ValidationError
    (D-01, D-04, T-38-07) — Full Name is always derived server-side."""
    import pydantic

    from api.schemas.admin_jobs import PersonCreate

    with pytest.raises(pydantic.ValidationError):
        PersonCreate(full_name="Should Be Rejected")


def test_person_create_accepts_name_parts_without_full_name() -> None:
    """PersonCreate accepts only structured parts; the first-or-last
    minimum-data invariant (D-09) is enforced by create_person_for_job's
    shared prepare_person_name call, not by this schema."""
    from api.schemas.admin_jobs import PersonCreate

    body = PersonCreate(last_name="Souter")
    assert body.last_name == "Souter"
    assert body.first_name is None
    assert "full_name" not in PersonCreate.model_fields


@pytest.mark.asyncio
async def test_create_person_for_job_rejects_missing_first_and_last() -> None:
    """create_person_for_job rejects a request with neither first_name nor
    last_name (D-09) — api.domain.person_names.PersonNameError is raised by
    the shared prepare_person_name helper BEFORE any job/DB lookup, so this
    test needs no DATABASE_URL/live database at all (db=None is never
    touched)."""
    from api.domain.person_names import PersonNameError
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    body = PersonCreate()
    with pytest.raises(PersonNameError):
        await create_person_for_job(None, 999999, body)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_create_person_for_job_validates_participant_before_person_insert() -> None:
    """Guard ordering (Pitfall 5 pattern): the participant lookup/validation must
    happen before Person(...) is constructed, so an unknown raw_speaker_label
    never creates a phantom Person row."""
    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def create_person_for_job(")
    assert func_start != -1
    next_func = source.find("\nasync def ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    participant_check_idx = func_body.find("participant_result")
    person_insert_idx = func_body.find("person = Person(")
    assert participant_check_idx != -1
    assert person_insert_idx != -1
    assert participant_check_idx < person_insert_idx, (
        "Participant validation must run before the Person row is constructed"
    )


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_bench_sets_is_justice_and_participant_side() -> None:
    """Test 1: a BENCH mini person request creates Person.is_justice true and
    updates the target argument_participants row to BENCH for the job's linked
    argument per D-12.

    Uses AsyncSessionLocal() directly rather than the shared db_session
    fixture — create_person_for_job commits internally (D-12/D-13), which
    raises "Can't operate on closed transaction" when nested inside
    db_session's outer session.begin() wrapper. This mirrors the multi-block
    AsyncSessionLocal pattern used throughout test_admin_arguments_service.py
    for the same reason (Phase 31, T-31-12: fixed in test usage, not by
    changing the service's commit semantics).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=None,
            raw_speaker_label="JUSTICE JACKSON",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id

    body = PersonCreate(
        first_name="Ketanji",
        middle_name="Brown",
        last_name="Jackson",
        raw_speaker_label="JUSTICE JACKSON",
        side=SideEnum.BENCH,
    )

    async with AsyncSessionLocal() as db:
        person = await create_person_for_job(db, job_id, body)
        person_id = person.id
        assert person.is_justice is True
        assert person.full_name == "Ketanji Brown Jackson"
        assert person.first_name == "Ketanji"
        assert person.last_name == "Jackson"

    async with AsyncSessionLocal() as db:
        participant = await db.get(ArgumentParticipant, participant_id)
        assert participant.person_id == person_id
        assert participant.side == SideEnum.BENCH

        # cleanup — create_person_for_job commits internally, so nothing here
        # is protected by a rollback; must delete explicitly.
        await db.delete(participant)
        job = await db.get(AdminJob, job_id)
        await db.delete(job)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        person = await db.get(Person, person_id)
        await db.delete(person)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_advocate_sets_is_justice_false() -> None:
    """Test 2: an advocate mini person request creates Person.is_justice false
    and updates the target participant side to the submitted advocate side
    per PJOB-19.

    Uses AsyncSessionLocal() directly rather than the shared db_session
    fixture — create_person_for_job commits internally (see the bench test
    above for the full explanation).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=None,
            raw_speaker_label="MR. SMITH",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id

    body = PersonCreate(
        first_name="John",
        last_name="Smith",
        raw_speaker_label="MR. SMITH",
        side=SideEnum.PETITIONER,
    )

    async with AsyncSessionLocal() as db:
        person = await create_person_for_job(db, job_id, body)
        person_id = person.id
        assert person.is_justice is False
        assert person.full_name == "John Smith"

    async with AsyncSessionLocal() as db:
        participant = await db.get(ArgumentParticipant, participant_id)
        assert participant.person_id == person_id
        assert participant.side == SideEnum.PETITIONER

        # cleanup
        await db.delete(participant)
        job = await db.get(AdminJob, job_id)
        await db.delete(job)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        person = await db.get(Person, person_id)
        await db.delete(person)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_rejects_wrong_job_state(db_session) -> None:
    """Test 3a: a non-PAUSED job rejects the mini create-person request."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    job = AdminJob(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.RESOLVE)
    db_session.add(job)
    await db_session.flush()

    body = PersonCreate(last_name="Someone", raw_speaker_label="MR. X")
    with pytest.raises(ValueError):
        await create_person_for_job(db_session, job.id, body)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_rejects_unknown_raw_speaker_label(db_session) -> None:
    """Test 3b: an unknown raw_speaker_label is rejected before any Person row is created."""
    from sqlalchemy import select

    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Argument, ArgumentStatusEnum, Person
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    body = PersonCreate(last_name="Nobody", raw_speaker_label="NO SUCH LABEL")
    with pytest.raises(ValueError):
        await create_person_for_job(db_session, job.id, body)

    # No phantom Person row created
    result = await db_session.execute(select(Person).where(Person.full_name == "Nobody"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_rejects_participant_outside_job_argument(db_session) -> None:
    """Test 3c: a raw_speaker_label that matches a participant on a DIFFERENT
    argument is rejected — the lookup is scoped to job.argument_id only."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    other_arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    job_arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add_all([other_arg, job_arg])
    await db_session.flush()

    # Participant with a matching label lives under a DIFFERENT argument.
    other_participant = ArgumentParticipant(
        argument_id=other_arg.id,
        person_id=None,
        raw_speaker_label="SHARED LABEL",
        side=SideEnum.UNKNOWN,
    )
    db_session.add(other_participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=job_arg.id)
    db_session.add(job)
    await db_session.flush()

    body = PersonCreate(last_name="Cross Argument", raw_speaker_label="SHARED LABEL", side=SideEnum.BENCH)
    with pytest.raises(ValueError):
        await create_person_for_job(db_session, job.id, body)

    await db_session.refresh(other_participant)
    assert other_participant.person_id is None, (
        "The participant under the OTHER argument must never be mutated (IDOR guard)"
    )


# ===========================================================================
# Task 3: Guarded resolve-row side and descriptor mutation
# ===========================================================================


# ---------------------------------------------------------------------------
# Schema tests (no DB required)
# ---------------------------------------------------------------------------


def test_resolve_row_update_schema_allows_bench() -> None:
    """Unlike ParticipantSideUpdate, ResolveRowUpdate must allow BENCH."""
    from api.models.models import SideEnum
    from api.schemas.admin_jobs import ResolveRowUpdate

    body = ResolveRowUpdate(participant_id=7, side=SideEnum.BENCH, descriptor=None)
    assert body.side == SideEnum.BENCH
    assert body.descriptor is None


def test_resolve_row_update_schema_fields() -> None:
    from api.models.models import SideEnum
    from api.schemas.admin_jobs import ResolveRowUpdate

    body = ResolveRowUpdate(participant_id=7, side=SideEnum.PETITIONER, descriptor="Counsel for Petitioner")
    assert body.participant_id == 7
    assert body.side == SideEnum.PETITIONER
    assert body.descriptor == "Counsel for Petitioner"


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_update_resolve_row_for_job_does_not_reuse_advocate_side_endpoint() -> None:
    """RESEARCH.md Common Pitfalls: this function must NOT route through
    admin_arguments.update_participant_side, which rejects BENCH by design."""
    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def update_resolve_row_for_job(")
    assert func_start != -1
    next_func = source.find("\nasync def ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "update_participant_side(" not in func_body, (
        "update_resolve_row_for_job must not call update_participant_side — "
        "that path rejects BENCH by design"
    )
    assert "ArgumentStatusEnum.PIPELINE" in func_body, (
        "update_resolve_row_for_job must guard on argument.status == pipeline (D-18, D-19)"
    )
    assert "synchronize_session=False" in func_body


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_bench_side_persists() -> None:
    """Test 1: updating an already-resolved bench participant to BENCH succeeds
    and persists ArgumentParticipant.side on the job's linked argument (D-18,
    PJOB-18) — the old advocate-side path rejects BENCH.

    Uses AsyncSessionLocal() directly rather than the shared db_session
    fixture — update_resolve_row_for_job commits internally, which raises
    "Can't operate on closed transaction" when nested inside db_session's
    outer session.begin() wrapper (Phase 31, T-31-12: fixed in test usage,
    not by changing the service's commit semantics).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Justice Example")
        db.add(person)
        await db.flush()

        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE EXAMPLE",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id

    body = ResolveRowUpdate(participant_id=participant_id, side=SideEnum.BENCH, descriptor=None)

    async with AsyncSessionLocal() as db:
        updated = await update_resolve_row_for_job(db, job_id, body)
        assert updated.side == SideEnum.BENCH
        assert updated.descriptor is None

    async with AsyncSessionLocal() as db:
        # cleanup
        participant = await db.get(ArgumentParticipant, participant_id)
        await db.delete(participant)
        job = await db.get(AdminJob, job_id)
        await db.delete(job)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        person = await db.get(Person, person_id)
        await db.delete(person)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_advocate_descriptor_persists_bench_descriptor_preserved() -> None:
    """Test 2: updating an advocate row persists its descriptor and the selected
    non-bench side (D-14, PJOB-14). A bench-row payload leaves whatever descriptor
    is already stored on that participant untouched — the client-supplied bench
    descriptor is never written (RESOLVE-13). This reverses PJOB-15's storage
    half: the read path (`list_resolve_rows_for_job`) still reports null for
    bench rows, so the value is preserved in the DB but hidden, not shown, not
    cleared.

    Uses AsyncSessionLocal() directly rather than the shared db_session
    fixture — update_resolve_row_for_job commits internally (see the bench
    test above for the full explanation).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    async with AsyncSessionLocal() as db:
        advocate_person = Person(full_name="Advocate Example")
        bench_person = Person(full_name="Bench Example", is_justice=True)
        db.add_all([advocate_person, bench_person])
        await db.flush()

        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        advocate_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate_person.id,
            raw_speaker_label="MR. ADVOCATE",
            side=SideEnum.UNKNOWN,
        )
        # Bench participant starts with a real stored descriptor so the
        # preservation assertion below is unambiguous in a failure diff.
        bench_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=bench_person.id,
            raw_speaker_label="JUSTICE BENCH",
            side=SideEnum.UNKNOWN,
            descriptor="Solicitor General",
        )
        db.add_all([advocate_participant, bench_participant])
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        advocate_person_id = advocate_person.id
        bench_person_id = bench_person.id
        arg_id = arg.id
        advocate_participant_id = advocate_participant.id
        bench_participant_id = bench_participant.id
        job_id = job.id

    advocate_body = ResolveRowUpdate(
        participant_id=advocate_participant_id,
        side=SideEnum.RESPONDENT,
        descriptor="Counsel for Respondent",
    )

    async with AsyncSessionLocal() as db:
        updated_advocate = await update_resolve_row_for_job(db, job_id, advocate_body)
        assert updated_advocate.side == SideEnum.RESPONDENT
        assert updated_advocate.descriptor == "Counsel for Respondent"

    # Bench payload sends a DIFFERENT descriptor — the service must ignore it
    # and leave the already-stored value ("Solicitor General") untouched.
    # This single assertion proves both halves at once: the stored value was
    # preserved, and the client-supplied bench descriptor was not written.
    bench_body = ResolveRowUpdate(
        participant_id=bench_participant_id,
        side=SideEnum.BENCH,
        descriptor="Should not be written",
    )

    async with AsyncSessionLocal() as db:
        updated_bench = await update_resolve_row_for_job(db, job_id, bench_body)
        assert updated_bench.side == SideEnum.BENCH
        assert updated_bench.descriptor == "Solicitor General"

    # Re-read in a fresh session so the assertion is about the committed row,
    # not a stale identity-mapped instance.
    async with AsyncSessionLocal() as db:
        refreshed_bench = await db.get(ArgumentParticipant, bench_participant_id)
        assert refreshed_bench.descriptor == "Solicitor General"

    async with AsyncSessionLocal() as db:
        # cleanup
        advocate_participant = await db.get(ArgumentParticipant, advocate_participant_id)
        await db.delete(advocate_participant)
        bench_participant = await db.get(ArgumentParticipant, bench_participant_id)
        await db.delete(bench_participant)
        job = await db.get(AdminJob, job_id)
        await db.delete(job)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        advocate_person = await db.get(Person, advocate_person_id)
        await db.delete(advocate_person)
        bench_person = await db.get(Person, bench_person_id)
        await db.delete(bench_person)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_descriptor_survives_advocate_bench_advocate_round_trip() -> None:
    """RESOLVE-13: an operator who types a descriptor, toggles the row to Bench,
    and toggles it back sees their own text again — the descriptor survives a
    three-step advocate -> bench -> advocate round trip across three separate
    sessions and a fresh re-read.

    Step 3 sends the descriptor back deliberately: the real client's hidden
    form has no descriptor field in the DOM while bench is selected, so on
    switching back the browser submits whatever the input now shows, which is
    the value the read path just returned. This test mirrors that.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Round Trip Example")
        db.add(person)
        await db.flush()

        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. ROUND TRIP",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id

    try:
        # Step 1: PETITIONER with a real descriptor — both stored.
        step1_body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.PETITIONER,
            descriptor="Counsel for Petitioner",
        )
        async with AsyncSessionLocal() as db:
            updated1 = await update_resolve_row_for_job(db, job_id, step1_body)
            assert updated1.side == SideEnum.PETITIONER
            assert updated1.descriptor == "Counsel for Petitioner"

        # Step 2: toggle to BENCH with descriptor=None (the hidden form has no
        # descriptor field while bench is selected) — side moves, descriptor
        # is untouched.
        step2_body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.BENCH,
            descriptor=None,
        )
        async with AsyncSessionLocal() as db:
            updated2 = await update_resolve_row_for_job(db, job_id, step2_body)
            assert updated2.side == SideEnum.BENCH
            assert updated2.descriptor == "Counsel for Petitioner"

        # Step 3: toggle back to RESPONDENT, sending the descriptor the read
        # path returned — descriptor intact, side moved. Re-read in a fresh
        # session to assert the committed row, not a stale instance.
        step3_body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.RESPONDENT,
            descriptor="Counsel for Petitioner",
        )
        async with AsyncSessionLocal() as db:
            updated3 = await update_resolve_row_for_job(db, job_id, step3_body)
            assert updated3.side == SideEnum.RESPONDENT
            assert updated3.descriptor == "Counsel for Petitioner"

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ArgumentParticipant, participant_id)
            assert refreshed.side == SideEnum.RESPONDENT
            assert refreshed.descriptor == "Counsel for Petitioner"
    finally:
        async with AsyncSessionLocal() as db:
            seeded_participant = await db.get(ArgumentParticipant, participant_id)
            if seeded_participant is not None:
                await db.delete(seeded_participant)
            seeded_job = await db.get(AdminJob, job_id)
            if seeded_job is not None:
                await db.delete(seeded_job)
            seeded_arg = await db.get(Argument, arg_id)
            if seeded_arg is not None:
                await db.delete(seeded_arg)
            seeded_person = await db.get(Person, person_id)
            if seeded_person is not None:
                await db.delete(seeded_person)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_rejects_participant_outside_job_argument(db_session) -> None:
    """Test 3a: a participant_id outside the job's linked argument is rejected
    before any mutation (IDOR guard)."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    other_arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    job_arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add_all([other_arg, job_arg])
    await db_session.flush()

    other_participant = ArgumentParticipant(
        argument_id=other_arg.id,
        person_id=None,
        raw_speaker_label="OTHER ARG SPEAKER",
        side=SideEnum.UNKNOWN,
    )
    db_session.add(other_participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=job_arg.id)
    db_session.add(job)
    await db_session.flush()

    body = ResolveRowUpdate(participant_id=other_participant.id, side=SideEnum.BENCH, descriptor=None)
    with pytest.raises(ValueError):
        await update_resolve_row_for_job(db_session, job.id, body)

    await db_session.refresh(other_participant)
    assert other_participant.side == SideEnum.UNKNOWN, (
        "The participant under the OTHER argument must never be mutated (IDOR guard)"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_rejects_edit_when_argument_not_pipeline(db_session) -> None:
    """Test 3b: any resolve-row edit is rejected when the linked argument.status
    is not pipeline (D-18, D-19)."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    person = Person(full_name="Already Created Example")
    db_session.add(person)
    await db_session.flush()

    arg = Argument(status=ArgumentStatusEnum.DRAFT, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="ALREADY RESOLVED",
        side=SideEnum.PETITIONER,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.COMPLETED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    body = ResolveRowUpdate(participant_id=participant.id, side=SideEnum.BENCH, descriptor=None)
    with pytest.raises(ValueError):
        await update_resolve_row_for_job(db_session, job.id, body)

    await db_session.refresh(participant)
    assert participant.side == SideEnum.PETITIONER, (
        "No mutation may occur once the argument has left the pipeline state"
    )
