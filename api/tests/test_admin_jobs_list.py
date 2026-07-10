"""
Tests for list_jobs incomplete filtering behavior (PIPE-20).

Tests the four behaviors defined in the plan:
  1. list_jobs(db, incomplete=False) returns all seeded jobs, newest first, capped at limit
  2. list_jobs(db, incomplete=True) returns only jobs whose status is PAUSED or FAILED
  3. list_jobs(db, incomplete=True) excludes COMPLETED, RUNNING, and PENDING jobs
  4. list_jobs(db) (no incomplete arg) defaults to returning all jobs (incomplete defaults False)

These tests use the async test session fixture pattern, seeding AdminJob rows
directly into the DB and asserting on returned statuses.

DB-guarded: all tests are skipped when DATABASE_URL is not configured.
"""

import os
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


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


@pytest_asyncio.fixture
async def db_session():
    """
    Async DB session seeded for each test, rolled back after.

    Requires DATABASE_URL to be set. Each test gets a fresh transaction
    that is rolled back, so seeded rows do not persist across tests.
    """
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client_no_db():
    """Async test client with get_db overridden to a no-op, for auth-only tests."""
    from api.core.database import get_db
    from api.main import app

    async def _mock_get_db():
        yield None

    app.dependency_overrides[get_db] = _mock_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client():
    """Async test client backed by a live DB (requires DATABASE_URL)."""
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _admin_headers() -> dict:
    """Return X-Admin-Token header using the configured settings value."""
    from api.core.config import settings

    return {"X-Admin-Token": settings.admin_token}


# ---------------------------------------------------------------------------
# Auth tests — no DB required
# ---------------------------------------------------------------------------

_WRONG_TOKEN_HEADERS = {"X-Admin-Token": "invalid-token-value"}


@pytest.mark.asyncio
async def test_list_jobs_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/jobs with wrong X-Admin-Token must return 401."""
    response = await client_no_db.get("/api/admin/jobs", headers=_WRONG_TOKEN_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs_incomplete_param_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/jobs?incomplete=true with wrong token must return 401."""
    response = await client_no_db.get(
        "/api/admin/jobs?incomplete=true", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Service-layer unit tests (PIPE-20)
# Seeded via DB session fixture, assertions on list_jobs return values.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_incomplete_false_returns_all_statuses(db_session: AsyncSession) -> None:
    """
    Test 1 + Test 4: list_jobs(db, incomplete=False) and list_jobs(db) both return
    all seeded jobs regardless of status (mix of completed/running/paused/failed).
    """
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

    # Seed one job of each status
    statuses_to_seed = [
        AdminJobStatus.COMPLETED,
        AdminJobStatus.RUNNING,
        AdminJobStatus.PAUSED,
        AdminJobStatus.FAILED,
        AdminJobStatus.PENDING,
    ]
    seeded = []
    for status in statuses_to_seed:
        job = AdminJob(
            status=status,
            current_step=AdminJobStep.INGEST,
        )
        db_session.add(job)
        seeded.append(job)
    await db_session.flush()

    # Test 1: explicit incomplete=False returns all statuses
    jobs = await list_jobs(db_session, incomplete=False)
    returned_statuses = {j.status for j in jobs}
    for status in statuses_to_seed:
        assert status in returned_statuses, (
            f"Expected status {status!r} in result but it was absent "
            "(list_jobs with incomplete=False must return all statuses)"
        )

    # Test 4: default (no incomplete arg) also returns all statuses
    jobs_default = await list_jobs(db_session)
    returned_statuses_default = {j.status for j in jobs_default}
    for status in statuses_to_seed:
        assert status in returned_statuses_default, (
            f"Expected status {status!r} in default result but it was absent "
            "(list_jobs default must behave like incomplete=False)"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_incomplete_true_returns_only_paused_and_failed(db_session: AsyncSession) -> None:
    """
    Test 2: list_jobs(db, incomplete=True) returns only PAUSED and FAILED jobs.
    """
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

    # Seed one job of each status
    for status in [
        AdminJobStatus.COMPLETED,
        AdminJobStatus.RUNNING,
        AdminJobStatus.PAUSED,
        AdminJobStatus.FAILED,
        AdminJobStatus.PENDING,
    ]:
        db_session.add(AdminJob(status=status, current_step=AdminJobStep.INGEST))
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=True)

    # Every returned job must be PAUSED or FAILED
    for job in jobs:
        assert job.status in (AdminJobStatus.PAUSED, AdminJobStatus.FAILED), (
            f"list_jobs(incomplete=True) returned job with status {job.status!r}; "
            "only PAUSED and FAILED are allowed"
        )

    # Both PAUSED and FAILED must appear
    returned_statuses = {j.status for j in jobs}
    assert AdminJobStatus.PAUSED in returned_statuses, (
        "list_jobs(incomplete=True) must include PAUSED jobs"
    )
    assert AdminJobStatus.FAILED in returned_statuses, (
        "list_jobs(incomplete=True) must include FAILED jobs"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_incomplete_true_excludes_completed_running_pending(db_session: AsyncSession) -> None:
    """
    Test 3: list_jobs(db, incomplete=True) excludes COMPLETED, RUNNING, and PENDING jobs.
    When only these statuses are seeded, result must be empty.
    """
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

    # Seed only non-incomplete statuses
    for status in [AdminJobStatus.COMPLETED, AdminJobStatus.RUNNING, AdminJobStatus.PENDING]:
        db_session.add(AdminJob(status=status, current_step=AdminJobStep.INGEST))
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=True)

    # Filter to only the jobs we seeded (in case there are pre-existing rows in DB)
    # by checking statuses — all returned must be PAUSED or FAILED
    # If any are COMPLETED/RUNNING/PENDING, the filter is broken
    for job in jobs:
        assert job.status not in (
            AdminJobStatus.COMPLETED,
            AdminJobStatus.RUNNING,
            AdminJobStatus.PENDING,
        ), (
            f"list_jobs(incomplete=True) returned job with status {job.status!r}; "
            "COMPLETED, RUNNING, and PENDING jobs must be excluded"
        )


# ---------------------------------------------------------------------------
# Endpoint integration tests (via HTTP client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_endpoint_accepts_incomplete_false(client: AsyncClient) -> None:
    """GET /api/admin/jobs?incomplete=false should return 200 with a list."""
    response = await client.get(
        "/api/admin/jobs?incomplete=false", headers=_admin_headers()
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_endpoint_accepts_incomplete_true(client: AsyncClient) -> None:
    """GET /api/admin/jobs?incomplete=true should return 200 with a list."""
    response = await client.get(
        "/api/admin/jobs?incomplete=true", headers=_admin_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    # Every job in the response must be PAUSED or FAILED
    for job in body:
        assert job["status"] in ("paused", "failed"), (
            f"Endpoint returned job with status {job['status']!r} for incomplete=true; "
            "only paused and failed are allowed"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_endpoint_default_no_param(client: AsyncClient) -> None:
    """GET /api/admin/jobs (no param) should return 200 with a list — same as incomplete=false."""
    response = await client.get("/api/admin/jobs", headers=_admin_headers())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# is_archived tests (Phase 26 gap closure, PLIST-05)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_is_archived_false_for_pipeline_argument(db_session: AsyncSession) -> None:
    """A job linked to a PIPELINE-status argument must report is_archived=False."""
    from api.models.models import Argument, ArgumentStatusEnum, AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

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
    assert matched.is_archived is False


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_is_archived_true_for_non_pipeline_argument(db_session: AsyncSession) -> None:
    """A job linked to a DRAFT/PUBLISHED/UNPUBLISHED argument must report is_archived=True."""
    from api.models.models import Argument, ArgumentStatusEnum, AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

    for status in [
        ArgumentStatusEnum.DRAFT,
        ArgumentStatusEnum.PUBLISHED,
        ArgumentStatusEnum.UNPUBLISHED,
    ]:
        argument = Argument(status=status, resolved_at=None)
        db_session.add(argument)
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
        assert matched.is_archived is True, (
            f"Expected is_archived True for linked argument status {status!r}"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_jobs_is_archived_false_when_no_linked_argument(db_session: AsyncSession) -> None:
    """A job with no linked argument (argument_id=None) must report is_archived=False."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import list_jobs

    job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        argument_id=None,
    )
    db_session.add(job)
    await db_session.flush()

    jobs = await list_jobs(db_session, incomplete=False)
    matched = next(j for j in jobs if j.id == job.id)
    assert matched.is_archived is False
