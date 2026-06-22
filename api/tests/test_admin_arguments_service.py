"""
Pure-logic and import tests for admin_arguments service (Phase 11 Plan 02).

Scope:
  - Verify all five public service functions and the _derive_slug helper import correctly.
  - Verify _derive_slug output matches the canonical pipeline transform.
  - Verify ArgumentUpdate schema has exactly the correct allow-list (mass-assignment guard).
  - DB-touching tests are guarded behind DATABASE_URL skip marker.

These tests do NOT require a live database for the import and schema assertions.
"""

import os

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


def test_service_functions_import() -> None:
    """All five public service functions must be importable from admin_arguments."""
    from api.services.admin_arguments import (  # noqa: F401
        get_argument_detail,
        list_arguments,
        publish_argument,
        unpublish_argument,
        update_argument,
    )


def test_derive_slug_importable_from_service() -> None:
    """_derive_slug must be importable from admin_arguments (re-exported from pipeline)."""
    from api.services.admin_arguments import _derive_slug  # noqa: F401


# ---------------------------------------------------------------------------
# _derive_slug unit tests (canonical pipeline transform)
# ---------------------------------------------------------------------------


def test_derive_slug_basic() -> None:
    """Standard case: lowercase + spaces to hyphens."""
    from api.services.admin_arguments import _derive_slug

    assert _derive_slug("Obergefell v. Hodges") == "obergefell-v-hodges"


def test_derive_slug_strips_periods() -> None:
    """Periods must be stripped (not converted to hyphens)."""
    from api.services.admin_arguments import _derive_slug

    result = _derive_slug("Brown v. Board of Education")
    assert "." not in result


def test_derive_slug_strips_commas() -> None:
    """Commas must be stripped (not converted to hyphens)."""
    from api.services.admin_arguments import _derive_slug

    result = _derive_slug("Roe, Jr. v. Wade, Sr.")
    assert "," not in result


def test_derive_slug_periods_not_converted_to_hyphens() -> None:
    """Ensure 'v.' does not produce double-hyphens — periods disappear entirely."""
    from api.services.admin_arguments import _derive_slug

    # "Obergefell v. Hodges" → spaces become hyphens, period disappears
    # should be "obergefell-v-hodges" not "obergefell-v--hodges"
    result = _derive_slug("Obergefell v. Hodges")
    assert "--" not in result
    assert result == "obergefell-v-hodges"


def test_derive_slug_all_lowercase() -> None:
    """Result must be fully lowercase."""
    from api.services.admin_arguments import _derive_slug

    result = _derive_slug("MIRANDA v. ARIZONA")
    assert result == result.lower()


# ---------------------------------------------------------------------------
# ArgumentUpdate mass-assignment guard tests (T-11-MASS)
# ---------------------------------------------------------------------------


def test_argument_update_allow_list() -> None:
    """ArgumentUpdate must expose exactly {case_name, docket_number, argued_date}."""
    from api.schemas.admin_arguments import ArgumentUpdate

    assert set(ArgumentUpdate.model_fields) == {"case_name", "docket_number", "argued_date"}


def test_argument_update_no_published_at() -> None:
    """published_at must NOT be in ArgumentUpdate (T-11-MASS)."""
    from api.schemas.admin_arguments import ArgumentUpdate

    assert "published_at" not in ArgumentUpdate.model_fields


def test_argument_update_no_slug() -> None:
    """slug must NOT be in ArgumentUpdate — it is derived server-side."""
    from api.schemas.admin_arguments import ArgumentUpdate

    assert "slug" not in ArgumentUpdate.model_fields


def test_argument_update_no_id() -> None:
    """id must NOT be in ArgumentUpdate — it is a path parameter."""
    from api.schemas.admin_arguments import ArgumentUpdate

    assert "id" not in ArgumentUpdate.model_fields


# ---------------------------------------------------------------------------
# Service file structural guards (update + synchronize_session=False)
# ---------------------------------------------------------------------------


def test_service_file_has_synchronize_session_false() -> None:
    """Every update() call in admin_arguments.py must be guarded with
    .execution_options(synchronize_session=False) (Pitfall 5).
    """
    import inspect

    from api.services import admin_arguments

    source = inspect.getsource(admin_arguments)
    # Count update() calls (both sqlalchemy core update() and any usage)
    update_count = source.count("update(Argument)")
    sync_false_count = source.count("synchronize_session=False")
    assert update_count > 0, "No update() calls found — service may not be implemented"
    assert sync_false_count >= update_count, (
        f"Found {update_count} update() calls but only {sync_false_count} "
        "synchronize_session=False guards. Every update() needs the guard (Pitfall 5)."
    )


# ---------------------------------------------------------------------------
# DB-guarded tests — skipped when DATABASE_URL is not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_arguments_returns_list() -> None:
    """list_arguments() must return a list (possibly empty) of dicts."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import list_arguments

    async with AsyncSessionLocal() as db:
        result = await list_arguments(db)
    assert isinstance(result, list)
    for item in result:
        assert "id" in item
        assert "argued_date" in item
        assert "case_name" in item
        assert "docket_number" in item


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_argument_detail_returns_none_for_missing() -> None:
    """get_argument_detail() must return None for a non-existent argument id."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import get_argument_detail

    async with AsyncSessionLocal() as db:
        result = await get_argument_detail(db, 999999)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_argument_returns_none_for_missing() -> None:
    """publish_argument() must return None for a non-existent argument id."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import publish_argument

    async with AsyncSessionLocal() as db:
        result = await publish_argument(db, 999999)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublish_argument_returns_none_for_missing() -> None:
    """unpublish_argument() must return None for a non-existent argument id."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import unpublish_argument

    async with AsyncSessionLocal() as db:
        result = await unpublish_argument(db, 999999)
    assert result is None
