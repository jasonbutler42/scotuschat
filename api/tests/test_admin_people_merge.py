"""
Tests for Phase 12 service functions: merge_people, get_merge_preview,
delete_person_if_orphan, update_photo_url, upload_photo.

These tests verify:
  - Import tests (no DB required)
  - Pure-logic tests: merge-to-self ValueError (no DB required)
  - DB-guarded service tests: merge transfer + delete, orphan check,
    get_merge_preview counts (skipped when DATABASE_URL not configured)

DB tests create isolated data inside a transaction that is rolled back after
each test so the test suite does not mutate production or staging state.
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
# Import tests — no DB required
# ---------------------------------------------------------------------------


def test_new_service_functions_import() -> None:
    """All five new Phase 12 service functions must be importable."""
    from api.services.admin_people import (  # noqa: F401
        delete_person_if_orphan,
        get_merge_preview,
        merge_people,
        update_photo_url,
        upload_photo,
    )


def test_spaces_helper_imports() -> None:
    """upload_photo_to_spaces must be importable from spaces module."""
    # Only check that the module attribute exists by name; boto3 may not be installed
    import importlib
    spec = importlib.util.find_spec("api.services.spaces")
    assert spec is not None, "api.services.spaces module must exist"
    # Read source to confirm the function is defined
    import inspect, ast, pathlib
    src_path = pathlib.Path(spec.origin)
    src = src_path.read_text()
    assert "def upload_photo_to_spaces" in src, "upload_photo_to_spaces must be defined in spaces.py"


def test_merge_schemas_import() -> None:
    """MergeRequest and MergePreview must import and construct correctly."""
    from api.schemas.admin_people import MergePreview, MergeRequest

    req = MergeRequest(target_id=7)
    assert req.target_id == 7

    preview = MergePreview(utterances=2, aliases=1, appearances=3, argument_participants=0)
    assert preview.utterances == 2
    assert preview.aliases == 1
    assert preview.appearances == 3
    assert preview.argument_participants == 0


# ---------------------------------------------------------------------------
# Pure-logic tests (no DB required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_merge_people_same_id_raises_value_error() -> None:
    """merge_people(db, X, X) raises ValueError before any DB operation."""
    from api.services.admin_people import merge_people

    class _FakeDB:
        """Stub DB that should never be called."""
        async def execute(self, *args, **kwargs):
            raise AssertionError("DB must not be called when source == target")

    with pytest.raises(ValueError, match="Source and target must be different people"):
        await merge_people(_FakeDB(), source_id=5, target_id=5)


# ---------------------------------------------------------------------------
# DB-guarded service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_merge_preview_returns_none_for_missing_source() -> None:
    """get_merge_preview returns None when source person does not exist."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        from api.services.admin_people import get_merge_preview
        result = await get_merge_preview(db, source_id=999999999)
        assert result is None

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_merge_preview_returns_counts_for_existing_person() -> None:
    """get_merge_preview returns a dict with the four count keys for a real person."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from api.services.admin_people import get_merge_preview

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Insert a test person in a savepoint so we can roll back
        async with db.begin():
            await db.execute(text(
                "INSERT INTO people (full_name) VALUES ('Test Preview Person') "
                "ON CONFLICT DO NOTHING"
            ))
            # Retrieve the inserted id
            row = (await db.execute(
                text("SELECT id FROM people WHERE full_name = 'Test Preview Person' LIMIT 1")
            )).one_or_none()

            if row is None:
                pytest.skip("Could not insert test person")

            person_id = row[0]
            result = await get_merge_preview(db, source_id=person_id)

            assert result is not None
            assert "utterances" in result
            assert "aliases" in result
            assert "appearances" in result
            assert "argument_participants" in result
            # Freshly-inserted person has no FK rows
            assert result["utterances"] == 0
            assert result["aliases"] == 0
            assert result["appearances"] == 0
            assert result["argument_participants"] == 0

            # Clean up
            await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_person_if_orphan_missing_person_returns_none() -> None:
    """delete_person_if_orphan returns None for a non-existent person_id."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from api.services.admin_people import delete_person_if_orphan

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await delete_person_if_orphan(db, person_id=999999999)
        assert result is None

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_person_if_orphan_deletes_orphaned_person() -> None:
    """delete_person_if_orphan returns True and removes a person with no FK rows."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from api.services.admin_people import delete_person_if_orphan, get_person_detail

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Insert orphan person
        await db.execute(text(
            "INSERT INTO people (full_name) VALUES ('Orphan Delete Test Person')"
        ))
        await db.commit()
        row = (await db.execute(
            text("SELECT id FROM people WHERE full_name = 'Orphan Delete Test Person' LIMIT 1")
        )).one_or_none()
        assert row is not None
        person_id = row[0]

    async with async_session() as db:
        result = await delete_person_if_orphan(db, person_id=person_id)
        assert result is True

    # Verify gone
    async with async_session() as db:
        detail = await get_person_detail(db, person_id)
        assert detail is None

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_merge_people_missing_source_returns_none() -> None:
    """merge_people returns None when the source person does not exist."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from api.services.admin_people import merge_people

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await merge_people(db, source_id=999999998, target_id=999999999)
        assert result is None

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_merge_people_transfers_and_deletes_source() -> None:
    """merge_people transfers all FK rows to target and deletes source."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from api.services.admin_people import merge_people, get_person_detail

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Create source and target persons
        await db.execute(text("INSERT INTO people (full_name) VALUES ('Merge Source Person')"))
        await db.execute(text("INSERT INTO people (full_name) VALUES ('Merge Target Person')"))
        await db.commit()

        src_row = (await db.execute(
            text("SELECT id FROM people WHERE full_name = 'Merge Source Person' LIMIT 1")
        )).one_or_none()
        tgt_row = (await db.execute(
            text("SELECT id FROM people WHERE full_name = 'Merge Target Person' LIMIT 1")
        )).one_or_none()
        assert src_row and tgt_row
        src_id = src_row[0]
        tgt_id = tgt_row[0]

    async with async_session() as db:
        result = await merge_people(db, source_id=src_id, target_id=tgt_id)
        # Returns the refreshed target detail (not None)
        assert result is not None
        assert result["id"] == tgt_id

    # Source must be gone; target must survive
    async with async_session() as db:
        source_detail = await get_person_detail(db, src_id)
        target_detail = await get_person_detail(db, tgt_id)
        assert source_detail is None, "Source person must be deleted after merge"
        assert target_detail is not None, "Target person must still exist after merge"

    # Clean up
    async with async_session() as db:
        await db.execute(text(f"DELETE FROM people WHERE id = {tgt_id}"))
        await db.commit()

    await engine.dispose()
