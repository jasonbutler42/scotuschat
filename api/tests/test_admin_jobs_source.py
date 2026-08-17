"""
Tests for the AdminJobResponse.source derivation (Phase 30 Plan 02, PJOB-01).

source is "corpus" when the job's linked Argument has any ImportRun row with
source == ImportSource.CORPUS (via an exists() subquery, duplication-safe
over the 1:many Argument -> ImportRun relationship), else "pdf".

DB-gated: all tests are skipped when DATABASE_URL is not configured, matching
the established pattern in test_admin_jobs_list.py.
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# source derivation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_source_is_corpus_for_declared_corpus_import_run(db_session: AsyncSession) -> None:
    """A job whose linked Argument has an ImportRun with source=CORPUS must report
    source='corpus' from both list_jobs() and get_job() (parity, not a hardcoded default)."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
    )
    from api.services.admin_jobs import get_job, list_jobs

    argument = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
    db_session.add(argument)
    await db_session.flush()

    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    db_session.add(run)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matched = next(j for j in jobs if j.id == job.id)
    assert matched.__dict__["source"] == "corpus"

    detail = await get_job(db_session, job.id)
    assert detail is not None
    assert detail.__dict__["source"] == "corpus"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_source_is_pdf_for_non_corpus_run(db_session: AsyncSession) -> None:
    """A job whose linked Argument has only a non-corpus ImportRun must report source='pdf'
    from both list_jobs() and get_job()."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
    )
    from api.services.admin_jobs import get_job, list_jobs

    argument = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
    db_session.add(argument)
    await db_session.flush()

    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.LLM_CORRECTIVE,
    )
    db_session.add(run)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.COMPLETED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matched = next(j for j in jobs if j.id == job.id)
    assert matched.__dict__["source"] == "pdf"

    detail = await get_job(db_session, job.id)
    assert detail is not None
    assert detail.__dict__["source"] == "pdf"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_source_is_pdf_when_no_pipeline_run(db_session: AsyncSession) -> None:
    """A job whose linked Argument has no ImportRun rows at all must report source='pdf'."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Argument, ArgumentStatusEnum
    from api.services.admin_jobs import get_job, list_jobs

    argument = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
    db_session.add(argument)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.RUNNING,
        current_step=AdminJobStep.PARSE,
        argument_id=argument.id,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matched = next(j for j in jobs if j.id == job.id)
    assert matched.__dict__["source"] == "pdf"

    detail = await get_job(db_session, job.id)
    assert detail is not None
    assert detail.__dict__["source"] == "pdf"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_source_is_pdf_when_no_linked_argument(db_session: AsyncSession) -> None:
    """A job with no linked argument (argument_id=None) must report source='pdf'."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import get_job, list_jobs

    job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        argument_id=None,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matched = next(j for j in jobs if j.id == job.id)
    assert matched.__dict__["source"] == "pdf"

    detail = await get_job(db_session, job.id)
    assert detail is not None
    assert detail.__dict__["source"] == "pdf"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_source_is_corpus_and_no_duplicate_row_with_mixed_import_runs(
    db_session: AsyncSession,
) -> None:
    """Guard case: an argument with BOTH a corpus and a non-corpus ImportRun
    still classifies as 'corpus' and its job appears exactly once in
    list_jobs() output — proves the exists() derivation is duplication-safe
    over the 1:many Argument -> ImportRun relationship (no naive join)."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
    )
    from api.services.admin_jobs import list_jobs

    argument = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
    db_session.add(argument)
    await db_session.flush()

    db_session.add(
        ImportRun(
            argument_id=argument.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.RULE_BASED,
        )
    )
    db_session.add(
        ImportRun(
            argument_id=argument.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
        )
    )
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.COMPLETED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matches = [j for j in jobs if j.id == job.id]
    assert len(matches) == 1, (
        f"Expected exactly one AdminJob row for job.id={job.id}, got {len(matches)} "
        "(duplication would indicate a naive join was used instead of exists())"
    )
    assert matches[0].__dict__["source"] == "corpus"
