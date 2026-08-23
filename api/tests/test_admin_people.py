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
    item contains the PersonListItem keys: id, full_name, missing, is_justice
    (Phase 27 / D-10 dropped role_id/role_name — role no longer lives on Person).
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
        assert "is_justice" in item, "PersonListItem must have 'is_justice'"
        assert "missing" in item, "PersonListItem must have 'missing'"
        assert "role_id" not in item, "role_id was removed from PersonListItem (D-10)"
        assert "role_name" not in item, "role_name was removed from PersonListItem (D-10)"
        assert isinstance(item["id"], int), "id must be an integer"
        assert isinstance(item["full_name"], str), "full_name must be a string"
        assert isinstance(item["missing"], list), "missing must be a list"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_people_missing_filter(client: AsyncClient) -> None:
    """
    GET /api/admin/people?missing=bio should return only people missing bio
    (D-04 click-to-filter; supersedes the removed ?incomplete=true toggle).
    """
    response = await client.get(
        "/api/admin/people?missing=bio", headers=_admin_headers()
    )
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    # Every returned item must be missing the filtered-on field
    for item in body:
        assert "bio" in item["missing"], (
            f"Person {item['id']} ({item['full_name']}) returned by "
            "?missing=bio but 'bio' not in its own missing list"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_partial_patch_does_not_wipe_other_fields(
    client: AsyncClient,
) -> None:
    """
    CR-01 regression: PATCH /api/admin/people/{id} must only write fields the
    request body explicitly includes. The real editor splits edits across two
    separate forms — Save Person (full_name/first_name/last_name/middle_name/
    name_suffix/is_justice/birthdate/tenures/bio_text, Phase 39 gap closure —
    39-UAT.md gap 1/test 10 moved bio_text here) and Photo (photo_url only) —
    each omitting the other's fields. update_person previously wrote every
    field unconditionally, so submitting one form silently wiped whatever the
    other form owns. This test still exercises that contract directly at the
    API layer regardless of which SvelteKit form currently owns each field.
    """
    headers = _admin_headers()
    # Phase 38 (D-01, D-04, T-38-07): PersonCreateRequest has no full_name
    # field — the "identity" the Identity form now establishes is structured
    # parts; full_name is always derived server-side.
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={
            "is_justice": False,
            "first_name": "CR-01",
            "last_name": "RegressionTestPerson",
        },
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        # Simulate an earlier Save Person submit that only touched name
        # fields and birthdate at that point, omitting bio_text/photo_url.
        identity_res = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={
                "first_name": "Regression",
                "last_name": "Testperson",
                "birthdate": "1950-01-01",
            },
        )
        assert identity_res.status_code == 200

        # Simulate a PATCH that sends only bio_text (Phase 39 gap closure:
        # this is now what a Save Person submit sends when only the Biography
        # card changed), omitting first_name/last_name/birthdate/tenures.
        bio_res = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"bio_text": "A test biography."},
        )
        assert bio_res.status_code == 200

        detail = bio_res.json()
        assert detail["bio_text"] == "A test biography."
        assert detail["first_name"] == "Regression", (
            "first_name was wiped by a PATCH that never included it (CR-01)"
        )
        assert detail["last_name"] == "Testperson", (
            "last_name was wiped by a PATCH that never included it (CR-01)"
        )
        assert detail["birthdate"] == "1950-01-01", (
            "birthdate was wiped by a PATCH that never included it (CR-01)"
        )

        # And the reverse direction: a subsequent Identity-form-only PATCH
        # (no bio_text key) must not wipe the bio_text just set above.
        identity_res_2 = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={
                "first_name": "Regression",
                "last_name": "Testperson",
                "birthdate": "1950-01-01",
            },
        )
        assert identity_res_2.status_code == 200
        assert identity_res_2.json()["bio_text"] == "A test biography.", (
            "bio_text was wiped by a PATCH that never included it (CR-01)"
        )
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_rejects_full_name_field(client: AsyncClient) -> None:
    """POST /api/admin/people rejects a client-supplied full_name with 422
    (D-01, D-04, T-38-07) — Full Name is always server-derived from parts."""
    headers = _admin_headers()
    response = await client.post(
        "/api/admin/people",
        headers=headers,
        json={
            "full_name": "Should Be Rejected",
            "is_justice": False,
            "last_name": "Rejected",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_rejects_missing_first_and_last(client: AsyncClient) -> None:
    """POST /api/admin/people with neither first_name nor last_name is a 422
    (D-09 minimum-data invariant, enforced by prepare_person_name)."""
    headers = _admin_headers()
    response = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_rejects_full_name_field(client: AsyncClient) -> None:
    """PATCH /api/admin/people/{id} rejects a client-supplied full_name with
    422 (D-01, D-04, T-38-07) — mirrors the create-side guard above."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "FullNameRejectTest"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"full_name": "Should Be Rejected"},
        )
        assert response.status_code == 422
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_partial_name_patch_merges_with_stored_parts(
    client: AsyncClient,
) -> None:
    """PATCH with only ONE name-part field (e.g. middle_name) merges against
    the person's already-stored first/last rather than clearing them and
    re-derives full_name from the merged result (D-01, D-03, D-04)."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={
            "is_justice": False,
            "first_name": "Merge",
            "last_name": "Testperson",
        },
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]
    assert create_res.json()["full_name"] == "Merge Testperson"

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"middle_name": "Middle"},
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["first_name"] == "Merge", "omitted first_name was wiped, not merged"
        assert detail["last_name"] == "Testperson", "omitted last_name was wiped, not merged"
        assert detail["middle_name"] == "Middle"
        assert detail["full_name"] == "Merge Middle Testperson"
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_explicit_null_clears_name_part(client: AsyncClient) -> None:
    """An explicit null/blank name-part field is a deliberate CLEAR, merged
    with the person's other stored parts — distinct from omitting the field
    entirely (D-04 omitted-vs-cleared contract, model_fields_set)."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={
            "is_justice": False,
            "first_name": "Clear",
            "middle_name": "MiddleToClear",
            "last_name": "Testperson",
        },
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"middle_name": None},
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["middle_name"] is None
        assert detail["first_name"] == "Clear", "unrelated stored part was wiped"
        assert detail["last_name"] == "Testperson", "unrelated stored part was wiped"
        assert detail["full_name"] == "Clear Testperson"
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_name_edit_rejects_clearing_both_first_and_last(
    client: AsyncClient,
) -> None:
    """A PATCH that would leave the merged result with neither first_name
    nor last_name is a 422 (D-09) — nothing is written."""
    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "OnlyLastName"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"last_name": None},
        )
        assert response.status_code == 422

        # Confirm nothing was actually written — the row is untouched.
        detail_res = await client.get(
            f"/api/admin/people/{person_id}", headers=headers
        )
        assert detail_res.json()["last_name"] == "OnlyLastName"
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_person_authoritative_name_edit_sets_operator_edited(
    client: AsyncClient,
) -> None:
    """An authoritative name-part edit sets review_state = operator_edited
    (Phase 49 D-11 — an edit always means *edited*) but leaves
    provenance_metadata untouched (D-12, carrying Phase 38 D-15 forward
    unchanged — independent audit trail, never erased by an edit). Directly
    flips the DB review_state/metadata (mirroring migration 0022's legacy
    review state, now folded into the unified record) since create_person
    always creates an unambiguous, never-reviewed row."""
    import json

    from sqlalchemy import text

    from api.core.database import AsyncSessionLocal

    headers = _admin_headers()
    create_res = await client.post(
        "/api/admin/people",
        headers=headers,
        json={"is_justice": False, "last_name": "Ambiguous Legacy Name"},
    )
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    try:
        metadata = {
            "source": "legacy_migration_0022",
            "raw": "Ambiguous Legacy Name",
            "confidence": "Low",
            "reason": "more than three name tokens is ambiguous",
            "auto_applied": False,
        }
        async with AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "UPDATE people SET review_state = 'needs_review', "
                    "provenance_metadata = CAST(:metadata AS JSONB) "
                    "WHERE id = :id"
                ),
                {"metadata": json.dumps(metadata), "id": person_id},
            )
            await db.commit()

        pre_res = await client.get(f"/api/admin/people/{person_id}", headers=headers)
        assert pre_res.json()["review_state"] == "needs_review"
        assert pre_res.json()["provenance_metadata"] == metadata

        response = await client.patch(
            f"/api/admin/people/{person_id}",
            headers=headers,
            json={"first_name": "Resolved", "last_name": "Person"},
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["review_state"] == "operator_edited", (
            "authoritative name edit did not set review_state=operator_edited (D-11)"
        )
        assert detail["provenance_metadata"] == metadata, (
            "provenance_metadata was erased/rewritten by an operator edit (D-12) — "
            "expected the envelope to be byte-identical to what was seeded"
        )
    finally:
        await client.delete(f"/api/admin/people/{person_id}", headers=headers)


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
