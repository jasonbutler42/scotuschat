"""
Phase 25 Plan 02 — backend resolve-row shape tests.

Covers:
  Task 1: ResolveRow schema, list_resolve_rows_for_job job-scoped listing
          (D-10, D-11, D-18, D-19, PJOB-14/15/16).
  Task 2: Tenure-derived bench_role/missing_tenure/person_edit_href, and
          descriptor/descriptor_hint (advocate-only) via _bench_role_and_missing_tenure
          (D-15, D-16, PJOB-15/16).
  Task 3: GET /api/admin/jobs/{job_id}/resolve-rows endpoint (T-25-04, T-25-06).

Following the project pattern (test_admin_jobs_phase25.py):
  - Schema/pure-function tests run without a database.
  - Structural (source-inspection) tests assert guard patterns without a database.
  - Behavioral tests that need real rows are gated behind a DATABASE_URL skipif.
"""

import datetime
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
# Task 1: ResolveRow schema and job-scoped listing service
# ===========================================================================


# ---------------------------------------------------------------------------
# Schema tests (no DB required)
# ---------------------------------------------------------------------------


def test_resolve_row_schema_fields() -> None:
    """Test 1: ResolveRow serializes raw_speaker_label, resolved person avatar/name
    fields, side, argument_role, descriptor, descriptor_hint, action-supporting fields, and
    editable."""
    from api.models.models import SideEnum
    from api.schemas.admin_people import ResolveRow

    row = ResolveRow(
        participant_id=7,
        raw_speaker_label="MR. SMITH",
        person_id=3,
        full_name="John Smith",
        photo_url="https://example.com/smith.jpg",
        side=SideEnum.PETITIONER,
        argument_role="Petitioner's Counsel",
        descriptor="Counsel for Petitioner",
        descriptor_hint="Counsel for Petitioner",
        bench_role=None,
        missing_tenure=False,
        person_edit_href=None,
        editable=True,
    )
    assert row.participant_id == 7
    assert row.raw_speaker_label == "MR. SMITH"
    assert row.person_id == 3
    assert row.full_name == "John Smith"
    assert row.photo_url == "https://example.com/smith.jpg"
    assert row.side == SideEnum.PETITIONER
    assert row.argument_role == "Petitioner's Counsel"
    assert row.descriptor == "Counsel for Petitioner"
    assert row.descriptor_hint == "Counsel for Petitioner"
    assert row.editable is True


def test_resolve_row_schema_defaults_for_unresolved_row() -> None:
    """An unresolved row (person_id None) must still validate — raw_speaker_label
    is preserved even without a resolved person (D-10, D-11)."""
    from api.models.models import SideEnum
    from api.schemas.admin_people import ResolveRow

    row = ResolveRow(
        participant_id=9,
        raw_speaker_label="UNKNOWN SPEAKER",
        side=SideEnum.UNKNOWN,
    )
    assert row.person_id is None
    assert row.full_name is None
    assert row.missing_tenure is False
    assert row.editable is True


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_list_resolve_rows_for_job_importable() -> None:
    from api.services.admin_people import list_resolve_rows_for_job  # noqa: F401


def test_list_participants_for_job_unaffected() -> None:
    """Task 1 direction: keep the existing list_participants_for_job behavior
    intact for older callers."""
    from api.services.admin_people import list_participants_for_job  # noqa: F401


def test_list_resolve_rows_for_job_scoped_by_argument() -> None:
    """Structural guard: the participant query must be scoped by
    ArgumentParticipant.argument_id == argument.id (T-25-06), never a
    client-supplied argument_id."""
    from api.services import admin_people

    source = inspect.getsource(admin_people)
    func_start = source.find("async def list_resolve_rows_for_job(")
    assert func_start != -1
    next_func = source.find("\nasync def ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "ArgumentParticipant.argument_id == argument.id" in func_body


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_resolve_rows_scoped_to_job_argument(db_session) -> None:
    """Test 2: rows are returned for the job's linked argument only and preserve
    raw labels even when person_id is null."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.services.admin_people import list_resolve_rows_for_job

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
    job_participant = ArgumentParticipant(
        argument_id=job_arg.id,
        person_id=None,
        raw_speaker_label="UNRESOLVED SPEAKER",
        side=SideEnum.UNKNOWN,
    )
    db_session.add_all([other_participant, job_participant])
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=job_arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["raw_speaker_label"] == "UNRESOLVED SPEAKER"
    assert rows[0]["person_id"] is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_resolve_rows_editable_false_when_argument_not_pipeline(db_session) -> None:
    """Test 3: editable is false when linked argument.status is not pipeline
    (D-18, D-19)."""
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
    from api.services.admin_people import list_resolve_rows_for_job

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

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["editable"] is False


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_resolve_rows_raises_for_missing_job(db_session) -> None:
    from api.services.admin_people import list_resolve_rows_for_job

    with pytest.raises(ValueError):
        await list_resolve_rows_for_job(db_session, 999999)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_resolve_rows_raises_for_unlinked_job(db_session) -> None:
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_people import list_resolve_rows_for_job

    job = AdminJob(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.INGEST)
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(ValueError):
        await list_resolve_rows_for_job(db_session, job.id)


# ===========================================================================
# Task 2: Tenure-derived bench role and Missing tenure flags
# ===========================================================================


# ---------------------------------------------------------------------------
# Pure-function tests (no DB required)
# ---------------------------------------------------------------------------


class _FakeTenure:
    """Minimal stand-in for a CourtTenure ORM row (office, start_date, end_date)."""

    def __init__(self, office, start_date, end_date=None):
        self.office = office
        self.start_date = start_date
        self.end_date = end_date


def test_bench_role_and_missing_tenure_covers_argued_date() -> None:
    """bench_role is the formal office title, not the canonical storage
    value (D-15)."""
    from api.services.admin_people import _bench_role_and_missing_tenure

    tenures = [
        _FakeTenure("associate", datetime.date(2010, 1, 1), None),
    ]
    bench_role, missing_tenure = _bench_role_and_missing_tenure(
        tenures, datetime.date(2024, 1, 10)
    )
    assert bench_role == "Associate Justice"
    assert missing_tenure is False


def test_bench_role_and_missing_tenure_covers_argued_date_chief() -> None:
    """Chief office maps to the formal 'Chief Justice' title (D-15)."""
    from api.services.admin_people import _bench_role_and_missing_tenure

    tenures = [
        _FakeTenure("chief", datetime.date(2010, 1, 1), None),
    ]
    bench_role, missing_tenure = _bench_role_and_missing_tenure(
        tenures, datetime.date(2024, 1, 10)
    )
    assert bench_role == "Chief Justice"
    assert missing_tenure is False


def test_bench_role_and_missing_tenure_no_covering_tenure() -> None:
    """No fallback to most-recent tenure — Missing tenure is explicit (D-15)."""
    from api.services.admin_people import _bench_role_and_missing_tenure

    tenures = [
        _FakeTenure("associate", datetime.date(2010, 1, 1), datetime.date(2015, 12, 31)),
    ]
    bench_role, missing_tenure = _bench_role_and_missing_tenure(
        tenures, datetime.date(2024, 1, 10)
    )
    assert bench_role is None
    assert missing_tenure is True


def test_bench_role_and_missing_tenure_no_argued_date() -> None:
    from api.services.admin_people import _bench_role_and_missing_tenure

    tenures = [
        _FakeTenure("associate", datetime.date(2010, 1, 1), None),
    ]
    bench_role, missing_tenure = _bench_role_and_missing_tenure(tenures, None)
    assert bench_role is None
    assert missing_tenure is True


def test_bench_role_and_missing_tenure_empty_tenures() -> None:
    from api.services.admin_people import _bench_role_and_missing_tenure

    bench_role, missing_tenure = _bench_role_and_missing_tenure([], datetime.date(2024, 1, 10))
    assert bench_role is None
    assert missing_tenure is True


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_row_with_covering_tenure_returns_role(db_session) -> None:
    """Test 1: a BENCH participant with a CourtTenure covering Argument.argued_date
    returns bench_role from the tenure's formal office title and missing_tenure
    false."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        Person,
        SideEnum,
    )
    from api.services.admin_people import list_resolve_rows_for_job

    person = Person(full_name="Justice Example", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    tenure = CourtTenure(
        person_id=person.id,
        office="associate",
        start_date=datetime.date(2010, 1, 1),
        end_date=None,
    )
    db_session.add(tenure)
    await db_session.flush()

    arg = Argument(
        status=ArgumentStatusEnum.PIPELINE,
        question_number=1,
        argued_date=datetime.date(2024, 1, 10),
    )
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="JUSTICE EXAMPLE",
        side=SideEnum.BENCH,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["bench_role"] == "Associate Justice"
    assert rows[0]["missing_tenure"] is False
    assert rows[0]["person_edit_href"] is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_row_without_covering_tenure_returns_missing_tenure(db_session) -> None:
    """Test 2: a BENCH participant without a covering tenure returns bench_role
    null, missing_tenure true, and person_edit_href for /admin/people/{id}."""
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
    from api.services.admin_people import list_resolve_rows_for_job

    person = Person(full_name="Justice No Tenure", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    arg = Argument(
        status=ArgumentStatusEnum.PIPELINE,
        question_number=1,
        argued_date=datetime.date(2024, 1, 10),
    )
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="JUSTICE NO TENURE",
        side=SideEnum.BENCH,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["bench_role"] is None
    assert rows[0]["missing_tenure"] is True
    assert rows[0]["person_edit_href"] == f"/admin/people/{person.id}"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_advocate_row_no_missing_tenure_keeps_role_and_descriptor(db_session) -> None:
    """Test 3: advocate rows do not show Missing tenure and keep argument
    role/descriptor editable data."""
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
    from api.services.admin_people import list_resolve_rows_for_job

    person = Person(full_name="Advocate Example")
    db_session.add(person)
    await db_session.flush()

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="MR. ADVOCATE",
        side=SideEnum.PETITIONER,
        descriptor="Counsel for Petitioner",
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    row = rows[0]
    assert row["missing_tenure"] is False
    assert row["bench_role"] is None
    assert row["argument_role"] == "Petitioner's Counsel"
    assert row["descriptor"] == "Counsel for Petitioner"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_row_descriptor_null_advocate_row_descriptor_present(db_session) -> None:
    """Test 4: bench rows return descriptor null and descriptor_hint null so the Descriptor
    column stays advocate-only per PJOB-15; advocate rows still carry
    descriptor/descriptor_hint."""
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
    from api.services.admin_people import list_resolve_rows_for_job

    bench_person = Person(full_name="Bench Example", is_justice=True)
    advocate_person = Person(full_name="Advocate Example 2")
    db_session.add_all([bench_person, advocate_person])
    await db_session.flush()

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    bench_participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=bench_person.id,
        raw_speaker_label="JUSTICE BENCH",
        side=SideEnum.BENCH,
    )
    advocate_participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=advocate_person.id,
        raw_speaker_label="MR. ADVOCATE 2",
        side=SideEnum.RESPONDENT,
        descriptor="Counsel for Respondent",
    )
    db_session.add_all([bench_participant, advocate_participant])
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)
    rows_by_label = {r["raw_speaker_label"]: r for r in rows}

    assert rows_by_label["JUSTICE BENCH"]["descriptor"] is None
    assert rows_by_label["JUSTICE BENCH"]["descriptor_hint"] is None
    assert rows_by_label["MR. ADVOCATE 2"]["descriptor"] == "Counsel for Respondent"
    assert rows_by_label["MR. ADVOCATE 2"]["descriptor_hint"] == "Counsel for Respondent"


# ===========================================================================
# Task 3: Job-scoped GET endpoint exposing resolve rows over HTTP
# ===========================================================================


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_list_resolve_rows_route_registered() -> None:
    """Test 1/2: the route exists, is registered on the shared admin router
    (so it inherits the router-level X-Admin-Token dependency), and calls
    the Task 1 service function."""
    from api.routers import admin

    source = inspect.getsource(admin)
    assert '@router.get("/jobs/{job_id}/resolve-rows"' in source
    assert "list_resolve_rows_for_job" in source


def test_list_resolve_rows_route_maps_value_error_to_4xx() -> None:
    """Test 3: an unknown or unlinked job_id maps the service ValueError to a
    4xx response rather than a 500."""
    from api.routers import admin

    source = inspect.getsource(admin)
    func_start = source.find("async def list_resolve_rows(")
    assert func_start != -1
    next_func = source.find("\n@router.", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "except ValueError" in func_body
    assert "HTTPException(status_code=422" in func_body


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests (via FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_resolve_rows_endpoint_returns_rows(db_session) -> None:
    """Test 1: GET /api/admin/jobs/{job_id}/resolve-rows returns 200 with the
    ResolveRow list produced by list_resolve_rows_for_job for the job's linked
    argument."""
    from httpx import ASGITransport, AsyncClient

    from api.core.config import settings
    from api.core.database import get_db
    from api.main import app
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=None,
        raw_speaker_label="MS. ENDPOINT",
        side=SideEnum.UNKNOWN,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/admin/jobs/{job.id}/resolve-rows",
                headers={"X-Admin-Token": settings.admin_token},
            )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["raw_speaker_label"] == "MS. ENDPOINT"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_resolve_rows_endpoint_requires_admin_token() -> None:
    """Test 2: the endpoint requires the X-Admin-Token dependency and rejects
    unauthenticated requests, matching the other admin job routes.

    No DATABASE_URL required — verify_admin_token (router-level dependency)
    raises 401 before any DB call, so get_db is overridden to a no-op
    (mirrors test_admin_people.py's client_no_db fixture pattern)."""
    from typing import AsyncGenerator

    from httpx import ASGITransport, AsyncClient

    from api.core.database import get_db
    from api.main import app

    async def _mock_get_db() -> AsyncGenerator:
        yield None  # Auth check raises 401 before this is used

    app.dependency_overrides[get_db] = _mock_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/admin/jobs/1/resolve-rows",
                headers={"X-Admin-Token": "invalid-token-value"},
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_resolve_rows_endpoint_unknown_job_returns_4xx(db_session) -> None:
    """Test 3: an unknown or unlinked job_id maps the service ValueError to a
    4xx response rather than a 500."""
    from httpx import ASGITransport, AsyncClient

    from api.core.config import settings
    from api.core.database import get_db
    from api.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/admin/jobs/999999/resolve-rows",
                headers={"X-Admin-Token": settings.admin_token},
            )
        assert 400 <= response.status_code < 500
    finally:
        app.dependency_overrides.pop(get_db, None)
