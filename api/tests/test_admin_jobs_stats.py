"""
Tests for parse stats in AdminJobResponse (Phase 17, PIPE-21).

Behaviors tested:
  1. get_job for a job whose parse step completed returns parse_stats with
     utterance_count == COUNT(utterances WHERE pipeline_run_id == latest parse run id)
     and speaker_count == COUNT(DISTINCT argument_participants.raw_speaker_label
     WHERE argument_id == job.argument_id)
  2. get_job for a job with no parse run (or argument_id is None) returns parse_stats == None
  3. When two parse runs exist for the same argument_id, parse_stats reflects the
     latest run (get_run_id_for_step orders created_at DESC LIMIT 1) — D-09
  4. AdminJobResponse.model_validate(job, from_attributes=True) populates parse_stats

DB-guarded: all tests are skipped when DATABASE_URL is not configured.
"""

import os
from datetime import date, datetime, timezone, timedelta

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
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Schema / unit tests (no DB required)
# ---------------------------------------------------------------------------


def test_parse_stats_model_has_required_fields() -> None:
    """ParseStats model must have utterance_count and speaker_count fields."""
    from api.schemas.admin_jobs import ParseStats

    ps = ParseStats(utterance_count=5, speaker_count=3)
    assert ps.utterance_count == 5
    assert ps.speaker_count == 3


def test_parse_stats_has_no_from_attributes_config() -> None:
    """ParseStats must NOT have from_attributes config — it's assembled from scalar results."""
    from api.schemas.admin_jobs import ParseStats

    # from_attributes would appear as model_config = {"from_attributes": True}
    config = getattr(ParseStats, "model_config", {})
    assert not config.get("from_attributes", False), (
        "ParseStats must not have from_attributes=True — it is assembled from scalar "
        "query results, not an ORM row. Only AdminJobResponse needs from_attributes."
    )


def test_admin_job_response_has_parse_stats_and_original_filename_fields() -> None:
    """AdminJobResponse must have optional parse_stats and original_filename fields."""
    from api.schemas.admin_jobs import AdminJobResponse
    import inspect

    fields = AdminJobResponse.model_fields
    assert "parse_stats" in fields, "AdminJobResponse missing parse_stats field"
    assert "original_filename" in fields, "AdminJobResponse missing original_filename field"

    # Both must be Optional (default None)
    assert fields["parse_stats"].default is None, "parse_stats default must be None"
    assert fields["original_filename"].default is None, "original_filename default must be None"


def test_admin_job_response_retains_from_attributes() -> None:
    """AdminJobResponse must retain model_config from_attributes = True."""
    from api.schemas.admin_jobs import AdminJobResponse

    config = getattr(AdminJobResponse, "model_config", {})
    assert config.get("from_attributes", False), (
        "AdminJobResponse must retain model_config = {'from_attributes': True}"
    )


# ---------------------------------------------------------------------------
# Service-layer tests (require DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_parse_stats_counts_from_latest_parse_run(db_session: AsyncSession) -> None:
    """
    Test 1: get_job returns parse_stats with utterance_count == N seeded utterances
    and speaker_count == N distinct raw_speaker_label values in the current parse run.
    """
    from api.models.models import (
        Argument,
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        PipelineRun,
        PipelineRunStatus,
        Utterance,
    )
    from api.services.admin_jobs import get_job

    # Seed an argument (Argument has no case_id FK — cases link via CaseArgument M:M)
    arg = Argument(
        argued_date=date(2022, 10, 1),
        status="pipeline",
    )
    db_session.add(arg)
    await db_session.flush()

    # Seed an AdminJob linked to the argument
    job = AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    # Seed an ingest PipelineRun (needed for the job chain)
    ingest_run = PipelineRun(
        argument_id=arg.id,
        step="ingest",
        status=PipelineRunStatus.COMPLETED,
    )
    db_session.add(ingest_run)
    await db_session.flush()

    # Seed a parse PipelineRun
    parse_run = PipelineRun(
        argument_id=arg.id,
        step="parse",
        status=PipelineRunStatus.COMPLETED,
    )
    db_session.add(parse_run)
    await db_session.flush()

    # Seed N=5 utterances under this parse run
    N = 5
    for i in range(N):
        utt = Utterance(
            argument_id=arg.id,
            pipeline_run_id=parse_run.id,
            sequence=i,
            raw_speaker_label=f"SPEAKER_{i}",
            text=f"Utterance {i} text.",
            strategy="rule_based",
        )
        db_session.add(utt)
    await db_session.flush()

    # Act
    result = await get_job(db_session, job.id)

    # Assert
    # speaker_count is now scoped to the current parse run via Utterance.raw_speaker_label
    # (WR-02 fix) — each of the N utterances has a distinct label, so speaker_count == N.
    assert result is not None, "get_job returned None"
    assert result.__dict__["parse_stats"] is not None, (
        "parse_stats should not be None when parse run exists"
    )
    ps = result.__dict__["parse_stats"]
    assert ps["utterance_count"] == N, (
        f"Expected utterance_count={N}, got {ps['utterance_count']}"
    )
    assert ps["speaker_count"] == N, (
        f"Expected speaker_count={N} (distinct labels in parse run), got {ps['speaker_count']}"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_parse_stats_none_when_no_parse_run(db_session: AsyncSession) -> None:
    """
    Test 2: get_job for a job with no parse run returns parse_stats == None.
    """
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Argument
    from api.services.admin_jobs import get_job

    arg = Argument(
        argued_date=date(2022, 10, 2),
        status="pipeline",
    )
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.RUNNING,
        current_step=AdminJobStep.PARSE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    # No parse PipelineRun seeded intentionally

    result = await get_job(db_session, job.id)

    assert result is not None
    assert result.__dict__["parse_stats"] is None, (
        "parse_stats must be None when no parse run exists for the job"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_parse_stats_none_when_argument_id_is_none(db_session: AsyncSession) -> None:
    """
    Test 2b: get_job for a job with argument_id == None returns parse_stats == None.
    """
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import get_job

    job = AdminJob(
        status=AdminJobStatus.RUNNING,
        current_step=AdminJobStep.INGEST,
        argument_id=None,
    )
    db_session.add(job)
    await db_session.flush()

    result = await get_job(db_session, job.id)

    assert result is not None
    assert result.__dict__["parse_stats"] is None, (
        "parse_stats must be None when argument_id is None"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_job_parse_stats_uses_latest_parse_run_when_two_exist(db_session: AsyncSession) -> None:
    """
    Test 3 (D-09): When two parse runs exist for the same argument_id,
    parse_stats reflects the latest run (most recent created_at).
    """
    from api.models.models import (
        Argument,
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        PipelineRun,
        PipelineRunStatus,
        Utterance,
    )
    from api.services.admin_jobs import get_job

    arg = Argument(
        argued_date=date(2022, 10, 3),
        status="pipeline",
    )
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=arg.id,
    )
    db_session.add(job)
    await db_session.flush()

    now = datetime.now(tz=timezone.utc)

    # First (older) parse run — 2 utterances
    old_parse_run = PipelineRun(
        argument_id=arg.id,
        step="parse",
        status=PipelineRunStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    db_session.add(old_parse_run)
    await db_session.flush()

    for i in range(2):
        db_session.add(Utterance(
            argument_id=arg.id,
            pipeline_run_id=old_parse_run.id,
            sequence=i,
            raw_speaker_label=f"OLD_SPEAKER_{i}",
            text=f"Old utterance {i}.",
            strategy="rule_based",
        ))
    await db_session.flush()

    # Second (newer) parse run — 7 utterances (D-09: stats must reflect this run)
    new_parse_run = PipelineRun(
        argument_id=arg.id,
        step="parse",
        status=PipelineRunStatus.COMPLETED,
        created_at=now - timedelta(hours=1),
    )
    db_session.add(new_parse_run)
    await db_session.flush()

    for i in range(7):
        db_session.add(Utterance(
            argument_id=arg.id,
            pipeline_run_id=new_parse_run.id,
            sequence=i,
            raw_speaker_label=f"NEW_SPEAKER_{i}",
            text=f"New utterance {i}.",
            strategy="rule_based",
        ))
    await db_session.flush()

    # Act
    result = await get_job(db_session, job.id)

    assert result is not None
    ps = result.__dict__["parse_stats"]
    assert ps is not None, "parse_stats must not be None when latest parse run has utterances"

    # Must reflect the LATEST parse run (7 utterances, not 2).
    # speaker_count is scoped to the latest parse run via Utterance.raw_speaker_label
    # (WR-02 fix): the latest run has 7 utterances with 7 distinct labels (NEW_SPEAKER_0..6).
    assert ps["utterance_count"] == 7, (
        f"Expected utterance_count=7 (latest run), got {ps['utterance_count']} — "
        "D-09: stats must reflect the latest parse run"
    )
    assert ps["speaker_count"] == 7, (
        f"Expected speaker_count=7 (distinct labels in latest parse run), got {ps['speaker_count']}"
    )
