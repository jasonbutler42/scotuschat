"""
Tests for the admin people, roles, and participants endpoints.

Auth tests (no DB required):
  - Assert each new admin people/roles/participants path returns 401 without
    an X-Admin-Token header (proves router-level auth dependency covers new routes,
    Access Control V4 / T-08-AC).
  - Uses a DB-override fixture so these tests run without a live database:
    `get_db` is overridden to yield None — auth is checked before any DB call,
    so a 401 response is returned before the None session is used.

DB-guarded tests (skipped when DATABASE_URL is not configured):
  - GET /api/admin/people returns list where each item has the PersonListItem keys.
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

    This allows auth tests to run without a live DB. The auth dependency
    (verify_admin_token) is resolved first and raises 401 before any
    database call is made, so the mock session is never actually used.
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
    The lifespan event will attempt a DB connection — tests that require
    the DB are guarded by the _db_configured skipif marker.
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
# Auth tests — no DB required (T-08-AC, ASVS V4)
# Uses client_no_db which overrides get_db so these tests run without a live DB.
#
# FastAPI behaviour for verify_admin_token (Header(...)):
#   - Wrong/invalid token: 401 Unauthorized (hmac.compare_digest fails)
#   - Missing header: 422 Unprocessable Entity (required header validation)
# Both responses mean the request is rejected before reaching any handler.
# These tests use a wrong token (value "invalid") to assert 401 for each route.
# ---------------------------------------------------------------------------


_WRONG_TOKEN_HEADERS = {"X-Admin-Token": "invalid-token-value"}


@pytest.mark.asyncio
async def test_list_people_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/people with wrong X-Admin-Token must return 401 (auth inherited)."""
    response = await client_no_db.get("/api/admin/people", headers=_WRONG_TOKEN_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_person_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/people/{id} with wrong X-Admin-Token must return 401 (auth inherited)."""
    response = await client_no_db.get("/api/admin/people/1", headers=_WRONG_TOKEN_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_person_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """PATCH /api/admin/people/{id} with wrong X-Admin-Token must return 401 (auth inherited)."""
    response = await client_no_db.patch(
        "/api/admin/people/1",
        json={"full_name": "Test"},
        headers=_WRONG_TOKEN_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_role_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """POST /api/admin/roles with wrong X-Admin-Token must return 401 (auth inherited)."""
    response = await client_no_db.post(
        "/api/admin/roles",
        json={"name": "Test Role"},
        headers=_WRONG_TOKEN_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_participants_wrong_token_returns_401(client_no_db: AsyncClient) -> None:
    """GET /api/admin/jobs/{id}/participants with wrong X-Admin-Token must return 401 (auth inherited)."""
    response = await client_no_db.get(
        "/api/admin/jobs/1/participants", headers=_WRONG_TOKEN_HEADERS
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DB-guarded tests — skipped when DATABASE_URL is not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_people_returns_person_list_item_shape(client: AsyncClient) -> None:
    """
    GET /api/admin/people with a valid token should return a list where each
    item contains the PersonListItem keys: id, full_name, role_id, role_name, missing.
    """
    response = await client.get("/api/admin/people", headers=_admin_headers())
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list), "Response must be a list"

    # If there are any people, verify the shape of the first item
    if body:
        item = body[0]
        assert "id" in item, "PersonListItem must have 'id'"
        assert "full_name" in item, "PersonListItem must have 'full_name'"
        assert "role_id" in item, "PersonListItem must have 'role_id'"
        assert "role_name" in item, "PersonListItem must have 'role_name'"
        assert "missing" in item, "PersonListItem must have 'missing'"
        assert isinstance(item["id"], int), "id must be an integer"
        assert isinstance(item["full_name"], str), "full_name must be a string"
        assert isinstance(item["missing"], list), "missing must be a list"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_people_incomplete_filter(client: AsyncClient) -> None:
    """
    GET /api/admin/people?incomplete=true should return only people with
    missing fields (role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL).
    """
    response = await client.get(
        "/api/admin/people?incomplete=true", headers=_admin_headers()
    )
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    # Every returned item must have at least one missing field
    for item in body:
        assert len(item["missing"]) > 0, (
            f"Person {item['id']} ({item['full_name']}) in incomplete list "
            "but has no missing fields"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_person_404_for_unknown_id(client: AsyncClient) -> None:
    """GET /api/admin/people/99999 with valid token should return 404."""
    response = await client.get("/api/admin/people/99999", headers=_admin_headers())
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_participants_404_for_unknown_job(client: AsyncClient) -> None:
    """GET /api/admin/jobs/99999/participants with valid token should return 404."""
    response = await client.get(
        "/api/admin/jobs/99999/participants", headers=_admin_headers()
    )
    assert response.status_code == 404
