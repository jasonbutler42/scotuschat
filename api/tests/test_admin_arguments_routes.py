"""
Tests for the admin arguments endpoints (Phase 11 Plan 02).

Auth tests (no DB required):
  - Assert each new admin arguments path returns 401 without an X-Admin-Token header
    (proves router-level auth dependency covers the new routes — T-11-AC, ASVS V4).
  - Uses the client_no_db fixture so these tests run without a live database:
    get_db is overridden to yield None — auth is checked before any DB call,
    so a 401 response is returned before the None session is used.

DB-guarded tests (skipped when DATABASE_URL is not configured):
  - Missing-argument id returns 404 (IDOR guard T-11-IDOR).
"""

import os
from typing import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_metadata_duplicate_contract_from_service(monkeypatch) -> None:
    from fastapi import HTTPException
    from api.routers import admin
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import DuplicateArgumentError

    db = AsyncMock()
    monkeypatch.setattr(admin.arguments_service, "update_argument_metadata", AsyncMock(side_effect=DuplicateArgumentError(42, "24-1", 2)))
    with pytest.raises(HTTPException) as exc:
        await admin.update_argument_metadata(7, MetadataUpdate(), db)
    assert exc.value.status_code == 409
    assert exc.value.detail == {"code": "duplicate_argument", "message": "An argument already uses docket 24-1, question 2.", "conflicting_argument_id": 42}


@pytest.mark.asyncio
async def test_metadata_non_target_integrity_error_is_sanitized(monkeypatch) -> None:
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError
    from api.routers import admin
    from api.schemas.admin_arguments import MetadataUpdate

    db = AsyncMock()
    err = IntegrityError("statement", {}, SimpleNamespace(diag=SimpleNamespace(constraint_name="other_constraint")))
    monkeypatch.setattr(admin.arguments_service, "update_argument_metadata", AsyncMock(side_effect=err))
    with pytest.raises(HTTPException) as exc:
        await admin.update_argument_metadata(7, MetadataUpdate(), db)
    db.rollback.assert_awaited_once()
    assert exc.value.status_code == 409
    assert exc.value.detail == {"code": "constraint_violation", "message": "The update violates a database constraint."}


@pytest.mark.asyncio
async def test_publish_uncertain_tier_blocked_maps_to_structured_422(monkeypatch) -> None:
    """TrustGateBlocked -> 422 with a structured detail dict carrying the
    tier and the blocker breakdown (Phase 48 D-19/D-20/T-48-SWALLOW)."""
    from fastapi import HTTPException
    from api.domain.trust import TrustTier
    from api.routers import admin
    from api.services.trust import TrustGateBlocked

    db = AsyncMock()
    blockers = [{"code": "unresolved_utterance_speaker", "count": 2}]
    monkeypatch.setattr(
        admin.arguments_service,
        "publish_argument",
        AsyncMock(side_effect=TrustGateBlocked(TrustTier.UNCERTAIN, blockers)),
    )
    with pytest.raises(HTTPException) as exc:
        await admin.publish_argument(7, None, db)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "uncertain_tier_blocked"
    assert exc.value.detail["trust_tier"] == "uncertain"
    assert exc.value.detail["blockers"] == blockers
    assert "message" in exc.value.detail


@pytest.mark.asyncio
async def test_publish_blank_override_reason_maps_to_structured_422(monkeypatch) -> None:
    """The blank-reason ValueError -> 422 with a distinct structured code so
    the client can tell "you did not give a reason" from "you have not
    tried yet" (D-17)."""
    from fastapi import HTTPException
    from api.routers import admin
    from api.schemas.admin_arguments import PublishRequest

    db = AsyncMock()
    monkeypatch.setattr(
        admin.arguments_service,
        "publish_argument",
        AsyncMock(side_effect=ValueError("blank_override_reason")),
    )
    with pytest.raises(HTTPException) as exc:
        await admin.publish_argument(7, PublishRequest(override_reason="   "), db)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "blank_override_reason"
    assert "message" in exc.value.detail


@pytest.mark.asyncio
async def test_publish_resolve_gate_still_maps_to_plain_string_422(monkeypatch) -> None:
    """The pre-existing resolve-gate ValueError must still map to a
    byte-identical plain-string 422 detail — unchanged by the new gate
    (Phase 48 D-14)."""
    from fastapi import HTTPException
    from api.routers import admin

    db = AsyncMock()
    monkeypatch.setattr(
        admin.arguments_service,
        "publish_argument",
        AsyncMock(side_effect=ValueError("Cannot publish: resolve step not yet complete")),
    )
    with pytest.raises(HTTPException) as exc:
        await admin.publish_argument(7, None, db)
    assert exc.value.status_code == 422
    assert exc.value.detail == "Cannot publish: resolve step not yet complete"


@pytest.mark.asyncio
async def test_publish_already_published_still_maps_to_plain_string_422(monkeypatch) -> None:
    """The pre-existing already-PUBLISHED ValueError must still map to a
    byte-identical plain-string 422 detail — unchanged by the new gate."""
    from fastapi import HTTPException
    from api.routers import admin

    db = AsyncMock()
    monkeypatch.setattr(
        admin.arguments_service,
        "publish_argument",
        AsyncMock(side_effect=ValueError("Already published")),
    )
    with pytest.raises(HTTPException) as exc:
        await admin.publish_argument(7, None, db)
    assert exc.value.status_code == 422
    assert exc.value.detail == "Already published"


@pytest.mark.asyncio
async def test_metadata_target_race_rolls_back_then_returns_winner(monkeypatch) -> None:
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError
    from api.routers import admin
    from api.schemas.admin_arguments import MetadataUpdate

    db = AsyncMock()
    orig = SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_arguments_source_docket_question"))
    err = IntegrityError("statement", {}, orig)
    err.argument_pair = ("24-1", 2)
    monkeypatch.setattr(admin.arguments_service, "update_argument_metadata", AsyncMock(side_effect=err))
    lookup = AsyncMock(return_value=42)
    monkeypatch.setattr(admin.arguments_service, "find_argument_by_pair", lookup)
    with pytest.raises(HTTPException) as exc:
        await admin.update_argument_metadata(7, MetadataUpdate(), db)
    db.rollback.assert_awaited_once()
    lookup.assert_awaited_once_with(db, "24-1", 2, exclude_argument_id=7)
    assert exc.value.detail == {"code": "duplicate_argument", "message": "An argument already uses docket 24-1, question 2.", "conflicting_argument_id": 42}


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
async def client_no_db():
    """
    Async test client with the get_db dependency overridden to a no-op.

    Allows auth tests to run without a live DB. The verify_admin_token dependency
    is resolved before get_db, so a wrong token raises 401 before the mock session
    is ever accessed.
    """
    from api.core.database import get_db
    from api.main import app

    async def _mock_get_db() -> AsyncGenerator:
        yield None  # Auth check raises 401 before this is used

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
    """
    Async test client for the FastAPI app (requires a live DB via DATABASE_URL).

    Uses ASGITransport so tests run without a real network socket.
    """
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "payload", "field", "service_name"),
    [
        ("/api/admin/arguments/7", {"case_name": None}, "case_name", "update_argument"),
        ("/api/admin/arguments/7", {"docket_number": " \t"}, "docket_number", "update_argument"),
        ("/api/admin/arguments/7/metadata", {"case_name": "\u2003"}, "case_name", "update_argument_metadata"),
        ("/api/admin/arguments/7/metadata", {"source_docket": None}, "source_docket", "update_argument_metadata"),
        ("/api/admin/arguments/7/metadata", {"source_dockets": []}, "source_dockets", "update_argument_metadata"),
    ],
)
async def test_required_patch_validation_returns_loc_422_before_service(
    client_no_db: AsyncClient, monkeypatch, path, payload, field, service_name
) -> None:
    from api.routers import admin

    service = AsyncMock()
    monkeypatch.setattr(admin.arguments_service, service_name, service)
    response = await client_no_db.patch(path, json=payload, headers=_admin_headers())

    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])
    service.assert_not_awaited()


# ---------------------------------------------------------------------------
# Auth tests — no DB required (T-11-AC, ASVS V4)
# Each new path must return 401 when called with a wrong X-Admin-Token header.
# ---------------------------------------------------------------------------


_WRONG_TOKEN_HEADERS = {"X-Admin-Token": "invalid-token-value"}


@pytest.mark.asyncio
async def test_list_arguments_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/arguments with wrong X-Admin-Token must return 401."""
    response = await client_no_db.get("/api/admin/arguments", headers=_WRONG_TOKEN_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_argument_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/arguments/{id} with wrong X-Admin-Token must return 401."""
    response = await client_no_db.get(
        "/api/admin/arguments/1", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_argument_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """PATCH /api/admin/arguments/{id} with wrong X-Admin-Token must return 401."""
    response = await client_no_db.patch(
        "/api/admin/arguments/1",
        json={"case_name": "Test Case"},
        headers=_WRONG_TOKEN_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_publish_argument_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """POST /api/admin/arguments/{id}/publish with wrong X-Admin-Token must return 401."""
    response = await client_no_db.post(
        "/api/admin/arguments/1/publish", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_publish_argument_with_body_wrong_token_returns_401(
    client_no_db: AsyncClient,
) -> None:
    """POST /api/admin/arguments/{id}/publish with a JSON body and wrong
    X-Admin-Token must still return 401 (Phase 48 Task 2) — the new optional
    ``body: PublishRequest | None`` route parameter must not move the route
    outside the router-level verify_admin_token dependency."""
    response = await client_no_db.post(
        "/api/admin/arguments/1/publish",
        json={"override_reason": "trying to sneak past auth"},
        headers=_WRONG_TOKEN_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unpublish_argument_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """POST /api/admin/arguments/{id}/unpublish with wrong X-Admin-Token must return 401."""
    response = await client_no_db.post(
        "/api/admin/arguments/1/unpublish", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_arguments_status_param_route_resolution_returns_401_not_422(
    client_no_db: AsyncClient,
) -> None:
    """GET /api/admin/arguments?status=... must return 401 (not 422) regardless of
    whether the status value is recognized (DASH-02, D-05, Task 1).

    Proves the new `status` query param is accepted at the route-signature layer
    (no 422 unprocessable-entity at query-parsing) and that auth still fires
    before any DB access — mirroring the sibling wrong-token tests above, this
    uses client_no_db so no live database is required.
    """
    # A recognized value must not trip a 422 at the query-parsing layer.
    response = await client_no_db.get(
        "/api/admin/arguments?status=draft", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401

    # An unrecognized value must likewise never 422 — the route accepts any
    # string; the service-layer allow-list guard (Task 1) decides what to do
    # with it, never the route/query-parsing layer (D-05).
    response = await client_no_db.get(
        "/api/admin/arguments?status=bogus", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DB-guarded tests — skipped when DATABASE_URL is not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_argument_404_for_unknown_id(client: AsyncClient) -> None:
    """GET /api/admin/arguments/99999 with valid token should return 404 (T-11-IDOR)."""
    response = await client.get("/api/admin/arguments/99999", headers=_admin_headers())
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_patch_argument_404_for_unknown_id(client: AsyncClient) -> None:
    """PATCH /api/admin/arguments/99999 with valid token should return 404 (T-11-IDOR)."""
    response = await client.patch(
        "/api/admin/arguments/99999",
        json={"case_name": "Test"},
        headers=_admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_argument_404_for_unknown_id(client: AsyncClient) -> None:
    """POST /api/admin/arguments/99999/publish with valid token should return 404 (T-11-IDOR)."""
    response = await client.post(
        "/api/admin/arguments/99999/publish", headers=_admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublish_argument_404_for_unknown_id(client: AsyncClient) -> None:
    """POST /api/admin/arguments/99999/unpublish with valid token should return 404 (T-11-IDOR)."""
    response = await client.post(
        "/api/admin/arguments/99999/unpublish", headers=_admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_arguments_returns_list(client: AsyncClient) -> None:
    """GET /api/admin/arguments with valid token should return a list."""
    response = await client.get("/api/admin/arguments", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        item = body[0]
        assert "id" in item
        assert "argued_date" in item
        assert "case_name" in item
        assert "docket_number" in item


# ---------------------------------------------------------------------------
# DELETE /arguments/{id} — 409 for UNPUBLISHED (Phase 26 Plan 01, D-03/AEDIT-09)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_409_for_unpublished(client: AsyncClient) -> None:
    """DELETE /api/admin/arguments/{id} on an UNPUBLISHED argument must return 409
    with the updated copy ("Only drafts can be removed.").
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.UNPUBLISHED, resolved_at=None)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    try:
        response = await client.delete(
            f"/api/admin/arguments/{arg_id}", headers=_admin_headers()
        )
        assert response.status_code == 409
        body = response.json()
        assert "Only drafts can be removed." in body["detail"]
    finally:
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_409_for_pipeline(client: AsyncClient) -> None:
    """DELETE /api/admin/arguments/{id} on a PIPELINE-status argument must
    return 409 (T-26-13) — the server-side gate blocks a direct API call from
    stranding an active AdminJob mid-pipeline.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    try:
        response = await client.delete(
            f"/api/admin/arguments/{arg_id}", headers=_admin_headers()
        )
        assert response.status_code == 409
        body = response.json()
        assert "Only drafts can be removed." in body["detail"]
    finally:
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
                await db.commit()


# ---------------------------------------------------------------------------
# PATCH /arguments/{id}/participants/{id} — descriptor persistence (Phase 26 Plan 02,
# D-06, T-26-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_route_persists_descriptor_for_advocate(
    client: AsyncClient,
) -> None:
    """PATCH /arguments/{id}/participants/{id} with {side, descriptor} persists
    descriptor for an advocate participant and returns it in the response body (D-06).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        advocate = Person(full_name="Route Title Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MS. ROUTE ADVOCATE",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        advocate_id = advocate.id
        participant_id = participant.id

    try:
        response = await client.patch(
            f"/api/admin/arguments/{arg_id}/participants/{participant_id}",
            json={"side": "PETITIONER", "descriptor": "Counsel of Record"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["side"] == "PETITIONER"
        assert body["descriptor"] == "Counsel of Record"

        # BENCH is still rejected via the route (422).
        response = await client.patch(
            f"/api/admin/arguments/{arg_id}/participants/{participant_id}",
            json={"side": "BENCH"},
            headers=_admin_headers(),
        )
        assert response.status_code == 422
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person = await db.get(Person, advocate_id)
            if person is not None:
                await db.delete(person)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


# ---------------------------------------------------------------------------
# POST /arguments/{id}/publish — end-to-end override coverage (Phase 48
# Task 3, D-14/D-17/D-19/D-20)
# ---------------------------------------------------------------------------


async def _seed_uncertain_draft_with_lead_case():
    """Seed one DRAFT, resolved argument with a single unresolved-speaker
    utterance (source=corpus/method=direct, so the only thing dragging it
    to UNCERTAIN is the unresolved speaker — D-11) and a lead Case, so the
    argument reaches the publish route in a real UNCERTAIN state. Returns a
    dict of every id needed for teardown."""
    import datetime
    import uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ImportRun,
        SideEnum,
        Utterance,
    )

    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RT-OVR-{suffix}",
            docket_number_norm=f"rt-ovr-{suffix}",
            case_name="Route Override Fixture v. Test Harness",
            term_year=2026,
            slug=f"route-override-fixture-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        import_run = ImportRun(
            argument_id=arg.id, step="parse", source="corpus", method="direct"
        )
        db.add(import_run)
        await db.flush()

        utterance = Utterance(
            argument_id=arg.id,
            import_run_id=import_run.id,
            sequence=1,
            raw_speaker_label=None,
            text="Test utterance.",
            is_stage_direction=False,
            side=SideEnum.PETITIONER,
            person_id=None,  # unresolved speaker -> UNCERTAIN tier (D-11)
        )
        db.add(utterance)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "import_run_id": import_run.id,
            "utterance_id": utterance.id,
        }


async def _teardown_uncertain_draft_with_lead_case(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusLog,
        Case,
        CaseArgument,
        ImportRun,
        Utterance,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentStatusLog).where(
                ArgumentStatusLog.argument_id == ids["argument_id"]
            )
        )
        await db.execute(sa_delete(Utterance).where(Utterance.id == ids["utterance_id"]))
        await db.execute(sa_delete(ImportRun).where(ImportRun.id == ids["import_run_id"]))
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_route_with_override_reason_returns_200_and_trust_tier(
    client: AsyncClient,
) -> None:
    """POST /api/admin/arguments/{id}/publish with a valid override_reason
    succeeds for an UNCERTAIN-tier argument end to end, and the response
    body includes trust_tier (D-20)."""
    ids = await _seed_uncertain_draft_with_lead_case()
    try:
        response = await client.post(
            f"/api/admin/arguments/{ids['argument_id']}/publish",
            json={"override_reason": "operator override for route end-to-end test"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["trust_tier"] == "uncertain"
        assert body["status"] == "published"
        assert body["published_at"] is not None
    finally:
        await _teardown_uncertain_draft_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_route_ignores_extra_body_keys(client: AsyncClient) -> None:
    """POST /api/admin/arguments/{id}/publish with extra body keys alongside
    a valid override_reason ignores them — PublishRequest is an allow-list
    of exactly one field (T-48-MASS); status/trust_tier are never
    client-settable via this route."""
    ids = await _seed_uncertain_draft_with_lead_case()
    try:
        response = await client.post(
            f"/api/admin/arguments/{ids['argument_id']}/publish",
            json={
                "override_reason": "operator override, extra keys ignored",
                "status": "published",
                "trust_tier": "verified",
            },
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        # trust_tier reflects the SERVER's recomputed tier (uncertain), not
        # the client-supplied "verified" — proving the extra key had no effect.
        assert body["trust_tier"] == "uncertain"
    finally:
        await _teardown_uncertain_draft_with_lead_case(ids)
