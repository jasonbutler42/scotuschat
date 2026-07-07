"""
Phase 25 Plan 01 — backend job-detail contract tests.

Covers:
  Task 1: RunReadiness / ReadinessBlocker / FailedStepRecovery schemas,
          get_job_readiness, derive_failed_step_recovery, get_failed_step_recovery
          (D-01 through D-08, D-18, D-20, PJOB-01/02/08/22).
  Task 2: PersonCreate side/raw_speaker_label extension, create_person_for_job
          job-scoped mini create-person mutation (D-12, D-13, PJOB-19).
  Task 3: ResolveRowUpdate schema, update_resolve_row_for_job job-scoped
          resolve-row side/title mutation (D-14, D-18, D-19, PJOB-14, PJOB-18).

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


@pytest_asyncio.fixture
async def db_session():
    """Async DB session seeded for each test, rolled back after.

    Requires DATABASE_URL. Each test gets a fresh transaction that is rolled
    back, so seeded rows never persist across tests.
    """
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


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


def test_derive_failed_step_recovery_never_recommends_same_source_rerun() -> None:
    """D-05/PJOB-22 supersession: no guidance string may mention rerun-with-same-source."""
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
