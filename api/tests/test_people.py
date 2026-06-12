"""Tests for GET /people/{id} endpoint (API-03)."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """
    Async test client for the FastAPI app.

    Uses ASGITransport so tests run without a real network socket.
    The lifespan event will attempt a DB connection — tests that require
    the DB are guarded by the requires_db skipif marker below.
    """
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Test 1: GET /people/{id} — requires real DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_person(client: AsyncClient) -> None:
    """
    GET /people/{id} should return 200 with id, full_name, and role_name keys
    when the person exists in the database.

    Uses person_id=1 (a Justice seeded by seed-aliases) as the canonical
    test subject. Requires a running DB with at least one Person row.
    """
    response = await client.get("/people/1")
    assert response.status_code == 200

    body = response.json()
    assert "id" in body, "Response must have 'id' key"
    assert "full_name" in body, "Response must have 'full_name' key"
    assert "role_name" in body, "Response must have 'role_name' key"
    assert isinstance(body["id"], int), "id must be an integer"
    assert isinstance(body["full_name"], str), "full_name must be a string"
    assert len(body["full_name"]) > 0, "full_name must not be empty"


# ---------------------------------------------------------------------------
# Test 2: GET /people/99999 — 404 for unknown person
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_person_404(client: AsyncClient) -> None:
    """
    GET /people/99999 should return 404 with a 'detail' key when the person
    does not exist.
    """
    response = await client.get("/people/99999")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body, "404 response must have 'detail' key"
    assert body["detail"] == "Person not found"
