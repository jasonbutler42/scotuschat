"""
Structural and behavioral tests for admin_jobs service delete_job function (Phase 21 Plan 02).

Scope:
  - Verify delete_job is importable from admin_jobs service.
  - Verify delete_job removes only the admin_job row (not argument/pipeline_runs/utterances).
  - Verify delete_job returns False for a non-existent job_id.
  - Structural source assertion: the only table in a delete() call is AdminJob.
  - Structural source assertion: .execution_options(synchronize_session=False) guard present.

DB-touching tests are guarded behind DATABASE_URL skip marker.
No-DB structural assertions run without a live database.
"""

import os

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------


def test_delete_job_importable() -> None:
    """delete_job must be importable from admin_jobs service (ADMIN-02)."""
    from api.services.admin_jobs import delete_job  # noqa: F401


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_delete_job_only_deletes_admin_jobs() -> None:
    """The delete_job function body must contain a delete() call against AdminJob only.

    No other table (Argument, PipelineRun, Utterance, ArgumentParticipant, CaseArgument)
    may appear inside a delete() or update() call within the function (D-10, D-11, Pitfall 6).
    """
    import inspect

    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def delete_job(")
    assert func_start != -1, "delete_job not found in source"
    # Isolate the function body (up to the next top-level async def)
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    # The ONLY allowed table in a delete() call is AdminJob
    assert "delete(AdminJob)" in func_body, (
        "delete(AdminJob) not found in delete_job body — function must delete the admin_job row"
    )
    # No other tables may appear in delete() calls
    forbidden_deletes = [
        "delete(Argument)",
        "delete(PipelineRun)",
        "delete(Utterance)",
        "delete(ArgumentParticipant)",
        "delete(CaseArgument)",
    ]
    for forbidden in forbidden_deletes:
        assert forbidden not in func_body, (
            f"{forbidden} found in delete_job body — job delete must NOT cascade "
            "into argument or its downstream data (D-10, D-11, Pitfall 6)"
        )


def test_delete_job_has_synchronize_session_false() -> None:
    """The delete(AdminJob) statement in delete_job must include
    .execution_options(synchronize_session=False) (consistent with all other
    bulk-statement guards in the module).
    """
    import inspect

    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def delete_job(")
    assert func_start != -1, "delete_job not found in source"
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "synchronize_session=False" in func_body, (
        "delete_job body missing .execution_options(synchronize_session=False) — "
        "required guard for all bulk statements in this module"
    )


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_job_returns_false_for_missing_id() -> None:
    """delete_job must return False when job_id does not exist (no row deleted)."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_jobs import delete_job

    async with AsyncSessionLocal() as db:
        result = await delete_job(db, 999999)
    assert result is False


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_job_removes_only_admin_job_row() -> None:
    """delete_job removes the admin_job row and returns True.

    The linked argument, its PipelineRun step rows, and its Utterance rows
    must all survive the delete (D-10, D-11).
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        PipelineRun,
        Utterance,
    )
    from api.services.admin_jobs import delete_job

    async with AsyncSessionLocal() as db:
        # --- seed: argument ---
        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            resolved_at=None,
        )
        db.add(arg)
        await db.flush()

        # --- seed: pipeline run (ingest) ---
        run = PipelineRun(
            argument_id=arg.id,
            step="ingest",
            status="completed",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(run)
        await db.flush()

        # --- seed: utterance (linked to argument + pipeline run) ---
        utt = Utterance(
            argument_id=arg.id,
            pipeline_run_id=run.id,
            sequence=1,
            raw_speaker_label="CHIEF JUSTICE ROBERTS",
            raw_text="We'll hear argument next in this case.",
        )
        db.add(utt)
        await db.flush()

        # --- seed: admin_job linked to the argument ---
        job = AdminJob(
            status=AdminJobStatus.COMPLETED,
            current_step=AdminJobStep.INGEST,
            argument_id=arg.id,
        )
        db.add(job)
        await db.commit()

        job_id = job.id
        arg_id = arg.id
        run_id = run.id
        utt_id = utt.id

    # --- act: delete the job ---
    async with AsyncSessionLocal() as db:
        result = await delete_job(db, job_id)

    assert result is True, "delete_job must return True when the job row is deleted"

    # --- assert: admin_job is gone ---
    async with AsyncSessionLocal() as db:
        deleted_job = await db.get(AdminJob, job_id)
        assert deleted_job is None, "AdminJob row must be removed by delete_job"

        # --- assert: argument, pipeline_run, utterance all survive ---
        surviving_arg = await db.get(Argument, arg_id)
        assert surviving_arg is not None, (
            "Argument must NOT be deleted by delete_job (D-10, D-11)"
        )

        surviving_run = await db.get(PipelineRun, run_id)
        assert surviving_run is not None, (
            "PipelineRun must NOT be deleted by delete_job (D-10, D-11)"
        )

        surviving_utt = await db.get(Utterance, utt_id)
        assert surviving_utt is not None, (
            "Utterance must NOT be deleted by delete_job (D-10, D-11)"
        )

        # --- cleanup: remove seeded data ---
        await db.delete(surviving_utt)
        await db.delete(surviving_run)
        await db.delete(surviving_arg)
        await db.commit()


# ---------------------------------------------------------------------------
# approve_job — ArgumentStatusLog "Created" audit row (Phase 26 Plan 01, D-08)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_approve_job_writes_one_draft_log_row() -> None:
    """approve_job on a PIPELINE argument sets status=DRAFT, resolved_at=now(),
    completes the job, and writes exactly one ArgumentStatusLog row with
    status=DRAFT for that argument_id (the "Created" transition, D-08).
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ArgumentStatusLog,
    )
    from api.services.admin_jobs import approve_job

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
        db.add(arg)
        await db.flush()

        job = AdminJob(
            status=AdminJobStatus.PAUSED,
            current_step=AdminJobStep.RESOLVE,
            argument_id=arg.id,
        )
        db.add(job)
        await db.commit()

        arg_id = arg.id
        job_id = job.id

    async with AsyncSessionLocal() as db:
        updated_job = await approve_job(db, job_id)

    assert updated_job.status == AdminJobStatus.COMPLETED

    async with AsyncSessionLocal() as db:
        arg = await db.get(Argument, arg_id)
        assert arg.status == ArgumentStatusEnum.DRAFT
        assert arg.resolved_at is not None

        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        log_rows = log_result.scalars().all()
        assert len(log_rows) == 1
        assert log_rows[0].status == ArgumentStatusEnum.DRAFT

        # --- cleanup ---
        job = await db.get(AdminJob, job_id)
        for row in log_rows:
            await db.delete(row)
        await db.delete(job)
        await db.delete(arg)
        await db.commit()
