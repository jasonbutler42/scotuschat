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

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


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
