"""
Tests for the Phase 52 (D-09, D-10) read-only identity fields on the admin
People API: display_name and oyez_speaker_id.

Both fields are returned by GET/PATCH's response body (PersonDetail) but
must never be accepted as PATCH input — they are absent from PersonUpdate's
field set, which carries `extra="forbid"`, so a posted display_name or
oyez_speaker_id is a 422, not a silently-ignored write. This mirrors the
existing full_name precedent proven in
test_admin_people.py::test_update_person_rejects_full_name_field.

These tests assert the 422 through the real request path (a live PATCH
against the ASGI app), not by inspecting `model_fields` alone, so they prove
the refusal rather than the declaration.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.fixture
async def client():
    """
    Async test client for the FastAPI app (requires a live DB via DATABASE_URL).

    Uses ASGITransport so tests run without a real network socket, matching
    the fixture pattern in test_admin_people.py.
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
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_rejects_display_name_field(client: AsyncClient) -> None:
    """PATCH /api/admin/people/{id} rejects a client-supplied display_name
    with 422 (D-09) — display_name is returned by PersonDetail but is not a
    field on PersonUpdate, which carries extra="forbid"."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "DisplayNameRejectTest"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"display_name": "Should Be Rejected"},
        )
        assert response.status_code == 422
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_rejects_oyez_speaker_id_field(client: AsyncClient) -> None:
    """PATCH /api/admin/people/{id} rejects a client-supplied
    oyez_speaker_id with 422 (D-10) — oyez_speaker_id is the load-bearing
    corpus join key and is returned by PersonDetail but is not a field on
    PersonUpdate, which carries extra="forbid"."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "OyezSpeakerIdRejectTest"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"oyez_speaker_id": "j__should_be_rejected"},
        )
        assert response.status_code == 422
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_writable_field_still_succeeds(client: AsyncClient) -> None:
    """PATCH /api/admin/people/{id} with an unrelated, genuinely writable
    field (bio_text) still succeeds — proving the 422s above are a targeted
    refusal of display_name/oyez_speaker_id specifically, not a broken write
    path."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "WritableFieldStillWorksTest"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"bio_text": "A test biography."},
        )
        assert response.status_code == 200
        assert response.json()["bio_text"] == "A test biography."
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_person_returns_display_name_and_oyez_speaker_id(
    client: AsyncClient,
) -> None:
    """GET /api/admin/people/{id} returns display_name and oyez_speaker_id,
    both nullable, on the PersonDetail response body."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "ReadPathReturnsFieldsTest"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.get(
            f"/api/admin/people/{person_id}", headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert "display_name" in body
        assert "oyez_speaker_id" in body
        # Freshly created via the admin create form, with no corpus join —
        # both fields are null.
        assert body["display_name"] is None
        assert body["oyez_speaker_id"] is None
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)
