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

    Creates its own durable Person row via a committed AsyncSessionLocal()
    session rather than assuming a hardcoded person_id=1 row exists (Phase
    31, T-31-19: the previous hardcoded-id=1 assumption relied on
    pipeline/tests/test_seed_aliases.py seeding real justices first — those
    tests are pre-existing pytest.fail("not implemented") stubs marked
    xfail, so run_seed_aliases() never actually executes in the current
    suite and no such row exists; this version is self-contained). Uses a
    plain committed session (not the shared db_session rollback fixture)
    because the HTTP client's request handler opens its own separate DB
    session via the app's get_db dependency — an uncommitted row in a
    different session/connection would not be visible to it.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Person

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Test Get Person Regression", is_justice=False)
        db.add(person)
        await db.commit()
        person_id = person.id

    try:
        response = await client.get(f"/people/{person_id}")
        assert response.status_code == 200

        body = response.json()
        assert "id" in body, "Response must have 'id' key"
        assert "full_name" in body, "Response must have 'full_name' key"
        assert "role_name" in body, "Response must have 'role_name' key"
        assert isinstance(body["id"], int), "id must be an integer"
        assert isinstance(body["full_name"], str), "full_name must be a string"
        assert len(body["full_name"]) > 0, "full_name must not be empty"
    finally:
        # Cleanup — the row above was committed, not protected by any rollback.
        async with AsyncSessionLocal() as db:
            person = await db.get(Person, person_id)
            if person is not None:
                await db.delete(person)
                await db.commit()


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
