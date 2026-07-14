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
# PATCH /arguments/{id}/participants/{id} — title persistence (Phase 26 Plan 02,
# D-06, T-26-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_route_persists_title_for_advocate(
    client: AsyncClient,
) -> None:
    """PATCH /arguments/{id}/participants/{id} with {side, title} persists title
    for an advocate participant and returns it in the response body (D-06).
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
            json={"side": "PETITIONER", "title": "Counsel of Record"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["side"] == "PETITIONER"
        assert body["title"] == "Counsel of Record"

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
