"""
Phase 44 Plan 09 (Task 4 remediation, tenure-preview follow-up) —
bench_role_preview_for_job / GET /api/admin/jobs/{job_id}/people/{person_id}/bench-role-preview.

The gap this closes: `list_resolve_rows_for_job`'s bench_role/missing_tenure
are computed from `ArgumentParticipant.person_id`, which stays NULL until the
Resolve card's batch `?/resolve` submit commits an operator's person pick —
so a freshly-picked bench candidate's tenure-derived Argument Role read
"(resolve person first)" until commit, even though the pick (and the tenure
data needed to derive a role for it) already existed. This endpoint previews
the same (bench_role, missing_tenure) pair `_bench_role_and_missing_tenure`
would eventually produce, against a person who is NOT YET a participant on
the argument for this job.

Covers:
  Service — `bench_role_preview_for_job` (api/services/admin_people.py):
    calculated / missing-tenure / not-yet-a-participant / job-not-found /
    job-not-linked.
  Router — GET /api/admin/jobs/{job_id}/people/{person_id}/bench-role-preview
    (api/routers/admin.py): route registration, 200 body shape, 422 mapping,
    401 without X-Admin-Token.

Following the project pattern (test_admin_people_phase25.py,
test_phase44_live_tenure_recompute.py): DB-guarded tests use the shared
`db_session` fixture (scotus_test, auto-reset per session boundary — Phase 31);
no `@pytest.mark.skipif` gate is needed because the fixture itself requires
TEST_DATABASE_URL.
"""

import datetime
import inspect

import pytest


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_bench_role_preview_route_registered() -> None:
    """The route exists, is registered on the shared admin router (so it
    inherits the router-level X-Admin-Token dependency), and maps the
    service's ValueError to a 422 — mirroring the sibling resolve-rows route's
    own registration/error-mapping contract."""
    from api.routers import admin

    source = inspect.getsource(admin)
    assert (
        '@router.get(\n    "/jobs/{job_id}/people/{person_id}/bench-role-preview"'
        in source
        or '/jobs/{job_id}/people/{person_id}/bench-role-preview"' in source
    )

    func_start = source.find("async def preview_bench_role")
    assert func_start != -1, "could not find preview_bench_role route function"
    next_func = source.find("\n@router.", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "except ValueError" in func_body
    assert "HTTPException(status_code=422" in func_body


def test_bench_role_preview_service_reuses_bench_role_and_missing_tenure() -> None:
    """The service function must call the shared derivation, not reimplement
    it — the 44-06 prohibition this plan's own continue-here doc names
    explicitly: a tenure-derived role must never drift from the one
    `_bench_role_and_missing_tenure` produces for the committed path."""
    from api.services import admin_people

    source = inspect.getsource(admin_people)
    func_start = source.find("async def bench_role_preview_for_job")
    assert func_start != -1
    next_def = source.find("\nasync def ", func_start + 1)
    func_body = source[func_start:next_def] if next_def != -1 else source[func_start:]

    assert "_bench_role_and_missing_tenure(" in func_body
    assert "CourtTenure" in func_body


# ---------------------------------------------------------------------------
# Service-level behavioral tests (bench_role_preview_for_job)
# ---------------------------------------------------------------------------


ARGUED_DATE = datetime.date(1966, 3, 1)
COVERING_START = datetime.date(1960, 1, 1)
NOT_COVERING_START = datetime.date(1967, 1, 1)


@pytest.mark.asyncio
async def test_preview_returns_calculated_role_for_a_person_not_yet_a_participant(
    db_session,
) -> None:
    """The exact gap this endpoint closes: a person with a covering tenure who
    is NOT YET an ArgumentParticipant on this argument (an uncommitted pick)
    still gets a real (bench_role, missing_tenure=False) preview."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        office_title,
    )
    from api.services.admin_people import bench_role_preview_for_job

    person = Person(full_name="Justice Preview Uncommitted", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=COVERING_START)
    db_session.add(tenure)

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1, argued_date=ARGUED_DATE)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    # No ArgumentParticipant row links `person` to `arg` at all — the preview
    # must still work.
    bench_role, missing_tenure = await bench_role_preview_for_job(db_session, job.id, person.id)
    assert missing_tenure is False
    assert bench_role == office_title(OFFICE_ASSOCIATE)


@pytest.mark.asyncio
async def test_preview_returns_missing_tenure_when_no_covering_tenure(db_session) -> None:
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_CHIEF,
        Person,
    )
    from api.services.admin_people import bench_role_preview_for_job

    person = Person(full_name="Justice Preview Missing Tenure", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    tenure = CourtTenure(person_id=person.id, office=OFFICE_CHIEF, start_date=NOT_COVERING_START)
    db_session.add(tenure)

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1, argued_date=ARGUED_DATE)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    bench_role, missing_tenure = await bench_role_preview_for_job(db_session, job.id, person.id)
    assert missing_tenure is True
    assert bench_role is None


@pytest.mark.asyncio
async def test_preview_matches_the_committed_value_for_the_same_person_and_argument(
    db_session,
) -> None:
    """The preview and the eventual committed row must agree exactly for the
    same person/argument — proven by calling both the preview (pre-commit)
    and list_resolve_rows_for_job (post-commit) against the identical tenure
    state, not merely asserting each in isolation."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        SideEnum,
    )
    from api.services.admin_people import bench_role_preview_for_job, list_resolve_rows_for_job

    person = Person(full_name="Justice Preview Matches Commit", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=COVERING_START)
    db_session.add(tenure)

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1, argued_date=ARGUED_DATE)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    preview_role, preview_missing = await bench_role_preview_for_job(db_session, job.id, person.id)

    # Now commit the pick — mirrors what the batch ?/resolve submit does.
    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="JUSTICE PREVIEW MATCHES COMMIT",
        side=SideEnum.BENCH,
    )
    db_session.add(participant)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)
    committed_row = next(r for r in rows if r["participant_id"] == participant.id)

    assert committed_row["bench_role"] == preview_role
    assert committed_row["missing_tenure"] == preview_missing


@pytest.mark.asyncio
async def test_preview_raises_for_missing_job(db_session) -> None:
    from api.services.admin_people import bench_role_preview_for_job

    with pytest.raises(ValueError):
        await bench_role_preview_for_job(db_session, 999999, 1)


@pytest.mark.asyncio
async def test_preview_raises_for_unlinked_job(db_session) -> None:
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Person
    from api.services.admin_people import bench_role_preview_for_job

    person = Person(full_name="Justice Preview Unlinked", is_justice=True)
    db_session.add(person)
    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=None)
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(ValueError):
        await bench_role_preview_for_job(db_session, job.id, person.id)


@pytest.mark.asyncio
async def test_preview_raises_for_nonexistent_person(db_session) -> None:
    """Code review finding WR-01: a valid job/argument but a person_id that
    does not refer to any Person must raise, matching every sibling
    person-scoped route's existence check — not silently return
    (None, True) as if the person exists but has no covering tenure."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Argument, ArgumentStatusEnum
    from api.services.admin_people import bench_role_preview_for_job

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1, argued_date=ARGUED_DATE)
    db_session.add(arg)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(ValueError, match="Person 999999 not found"):
        await bench_role_preview_for_job(db_session, job.id, 999999)


# ---------------------------------------------------------------------------
# Router-level behavioral tests (via FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bench_role_preview_endpoint_returns_preview(db_session) -> None:
    """GET /api/admin/jobs/{job_id}/people/{person_id}/bench-role-preview
    returns 200 with the BenchRolePreview shape, for a person who is not yet
    a participant on the job's linked argument."""
    from httpx import ASGITransport, AsyncClient

    from api.core.config import settings
    from api.core.database import get_db
    from api.main import app
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        office_title,
    )

    person = Person(full_name="Justice Preview Endpoint", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=COVERING_START)
    db_session.add(tenure)

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1, argued_date=ARGUED_DATE)
    db_session.add(arg)
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
                f"/api/admin/jobs/{job.id}/people/{person.id}/bench-role-preview",
                headers={"X-Admin-Token": settings.admin_token},
            )
        assert response.status_code == 200
        body = response.json()
        assert body == {"bench_role": office_title(OFFICE_ASSOCIATE), "missing_tenure": False}
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_bench_role_preview_endpoint_maps_missing_job_to_422(db_session) -> None:
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
                "/api/admin/jobs/999999/people/1/bench-role-preview",
                headers={"X-Admin-Token": settings.admin_token},
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_bench_role_preview_endpoint_requires_admin_token() -> None:
    """No DATABASE_URL required — verify_admin_token (router-level dependency)
    raises 401 before any DB call, matching test_get_resolve_rows_endpoint_
    requires_admin_token's identical no-op get_db override pattern. The header
    must be PRESENT but wrong, not omitted — an omitted required header fails
    FastAPI's own request validation with 422 before verify_admin_token ever
    runs, which would test the wrong layer."""
    from typing import AsyncGenerator

    from httpx import ASGITransport, AsyncClient

    from api.core.database import get_db
    from api.main import app

    async def _noop_get_db() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = _noop_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/admin/jobs/1/people/1/bench-role-preview",
                headers={"X-Admin-Token": "invalid-token-value"},
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
