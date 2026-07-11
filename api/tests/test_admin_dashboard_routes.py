"""
Tests for the admin dashboard stats/needs-attention routes (Phase 28 Plan 02).

DB-guarded tests (skipped when DATABASE_URL is not configured):
  - Each of the seven new endpoints returns 200 (not 422 — a 422 is the exact
    route-shadowing signature from Pitfall 1, where a literal route registered
    after its {id}-parameterized sibling is silently swallowed) with the
    documented response shape.
  - GET /api/admin/arguments/stats gets an explicit regression assertion
    documenting the ordering-hazard intent (T-28-05 / Pitfall 1).

These routes are read-only (pure aggregation reads) — no seed/commit calls
happen in this file, so no row-leakage concern (backlog 999.19) applies here.
"""

import os

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
async def client():
    """
    Async test client for the FastAPI app (requires a live DB via DATABASE_URL).

    Uses ASGITransport so tests run without a real network socket. The
    autouse _api_lifespan fixture in conftest.py fires ASGI lifespan so
    AsyncSessionLocal is bound before any route handler runs.
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
# DB-guarded tests — skipped when DATABASE_URL is not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_arguments_stats_returns_200_not_422(client: AsyncClient) -> None:
    """
    GET /api/admin/arguments/stats must resolve to the stats route and return
    200 with the ArgumentStats shape — NOT a 422, which would be the exact
    route-shadowing signature if /arguments/{argument_id} swallowed this
    literal path segment (T-28-05, Pitfall 1 regression guard).
    """
    response = await client.get("/api/admin/arguments/stats", headers=_admin_headers())
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text} — "
        "a 422 here means /arguments/{argument_id} is shadowing /arguments/stats"
    )
    body = response.json()
    assert "total" in body
    assert "published" in body
    assert "draft" in body
    assert "unpublished" in body


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_arguments_recent_drafts_returns_200_capped_at_five(client: AsyncClient) -> None:
    """GET /api/admin/arguments/recent-drafts returns an array of length <= 5."""
    response = await client.get(
        "/api/admin/arguments/recent-drafts", headers=_admin_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 5
    if body:
        item = body[0]
        assert "id" in item
        assert "case_name" in item
        assert "docket_number" in item


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_people_stats_returns_200(client: AsyncClient) -> None:
    """GET /api/admin/people/stats returns 200 with the PeopleStats shape."""
    response = await client.get("/api/admin/people/stats", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "incomplete" in body


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_people_incomplete_returns_200_capped_at_five(client: AsyncClient) -> None:
    """GET /api/admin/people/incomplete returns an array of length <= 5."""
    response = await client.get("/api/admin/people/incomplete", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 5
    if body:
        item = body[0]
        assert "id" in item
        assert "full_name" in item
        assert "missing" in item


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_people_tenure_gaps_returns_200_capped_at_five(client: AsyncClient) -> None:
    """GET /api/admin/people/tenure-gaps returns an array of length <= 5."""
    response = await client.get("/api/admin/people/tenure-gaps", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 5
    if body:
        item = body[0]
        assert "id" in item
        assert "full_name" in item


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_jobs_stats_returns_200(client: AsyncClient) -> None:
    """GET /api/admin/jobs/stats returns 200 with the PipelineStats shape."""
    response = await client.get("/api/admin/jobs/stats", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert "recent_count" in body
    assert "last_activity_at" in body


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_utterances_count_returns_200(client: AsyncClient) -> None:
    """GET /api/admin/utterances/count returns 200 with the UtteranceCount shape."""
    response = await client.get("/api/admin/utterances/count", headers=_admin_headers())
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
