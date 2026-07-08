"""
Pure-logic and import tests for admin_arguments service (Phase 11 Plan 02 / Phase 21 Plan 01).

Scope:
  - Verify all public service functions and the _derive_slug helper import correctly.
  - Verify _derive_slug output matches the canonical pipeline transform.
  - Verify ArgumentUpdate schema has exactly the correct allow-list (mass-assignment guard).
  - Verify delete_argument structural guards (FK order, synchronize_session=False).
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
    """All public service functions must be importable from admin_arguments."""
    from api.services.admin_arguments import (  # noqa: F401
        delete_argument,
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
    """Every update() and delete() call in admin_arguments.py must be guarded with
    .execution_options(synchronize_session=False) (Pitfall 5).
    """
    import inspect
    import re

    from api.services import admin_arguments

    source = inspect.getsource(admin_arguments)
    # Count all update() and delete() SQLAlchemy Core calls — not just update(Argument)
    stmt_count = len(re.findall(r'\b(update|delete)\(', source))
    sync_false_count = source.count("synchronize_session=False")
    assert stmt_count > 0, "No update() or delete() calls found — service may not be implemented"
    assert sync_false_count >= stmt_count, (
        f"Found {stmt_count} update()/delete() calls but only {sync_false_count} "
        "synchronize_session=False guards. Every update()/delete() needs the guard (Pitfall 5)."
    )


# ---------------------------------------------------------------------------
# delete_argument structural guards (Phase 21 Plan 01)
# ---------------------------------------------------------------------------


def test_delete_argument_importable() -> None:
    """delete_argument must be importable from admin_arguments (Phase 21)."""
    from api.services.admin_arguments import delete_argument  # noqa: F401


def test_delete_argument_utterances_before_pipeline_runs() -> None:
    """delete(Utterance) must appear before delete(PipelineRun) in delete_argument
    (Pitfall 2 — utterances.pipeline_run_id FK requires utterances deleted first).
    """
    import inspect

    from api.services import admin_arguments

    source = inspect.getsource(admin_arguments)
    # Find the delete_argument function body
    func_start = source.find("def delete_argument(")
    assert func_start != -1, "delete_argument not found in source"
    # Find the next top-level function after delete_argument
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]
    # Utterance delete must appear before PipelineRun delete
    utterance_pos = func_body.find("delete(Utterance)")
    pipeline_run_pos = func_body.find("delete(PipelineRun)")
    assert utterance_pos != -1, "delete(Utterance) not found in delete_argument body"
    assert pipeline_run_pos != -1, "delete(PipelineRun) not found in delete_argument body"
    assert utterance_pos < pipeline_run_pos, (
        "delete(Utterance) must appear before delete(PipelineRun) "
        "(Pitfall 2: utterances.pipeline_run_id FK order)"
    )


def test_delete_argument_admin_job_nulled_before_argument_deleted() -> None:
    """update(AdminJob) setting argument_id=None must appear before delete(Argument)
    in delete_argument body (Pitfall 1 — AdminJob FK would violate RESTRICT).
    """
    import inspect

    from api.services import admin_arguments

    source = inspect.getsource(admin_arguments)
    func_start = source.find("def delete_argument(")
    assert func_start != -1, "delete_argument not found in source"
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]
    admin_job_update_pos = func_body.find("update(AdminJob)")
    argument_delete_pos = func_body.find("delete(Argument)")
    assert admin_job_update_pos != -1, "update(AdminJob) not found in delete_argument body (Pitfall 1)"
    assert argument_delete_pos != -1, "delete(Argument) not found in delete_argument body"
    assert admin_job_update_pos < argument_delete_pos, (
        "update(AdminJob) must appear before delete(Argument) "
        "(Pitfall 1: AdminJob.argument_id FK has no ondelete)"
    )


def test_delete_argument_all_deletes_have_synchronize_session_false() -> None:
    """Every delete() call inside delete_argument must include
    .execution_options(synchronize_session=False) (Pitfall 3).
    """
    import inspect

    from api.services import admin_arguments

    source = inspect.getsource(admin_arguments)
    func_start = source.find("def delete_argument(")
    assert func_start != -1, "delete_argument not found in source"
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]
    # Count db.execute(delete(...)) calls — each needs synchronize_session=False
    delete_call_count = func_body.count("delete(")
    # We expect at least 5 delete() calls (Utterance, PipelineRun, ArgumentParticipant,
    # CaseArgument, Argument) and at least 1 update() call (AdminJob).
    # Every delete() and update() must have execution_options guard.
    exec_opts_count = func_body.count("synchronize_session=False")
    assert delete_call_count >= 5, (
        f"Expected at least 5 delete() calls in delete_argument, found {delete_call_count}"
    )
    assert exec_opts_count >= delete_call_count, (
        f"Found {delete_call_count} delete() calls but only {exec_opts_count} "
        "synchronize_session=False guards in delete_argument (Pitfall 3)."
    )


# ---------------------------------------------------------------------------
# DB-guarded delete_argument behavioral tests (Phase 21 Plan 01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_none_for_missing() -> None:
    """delete_argument() must return None for a non-existent argument id."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import delete_argument

    async with AsyncSessionLocal() as db:
        result = await delete_argument(db, 999999)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_false_for_unpublished() -> None:
    """delete_argument() must return False for an UNPUBLISHED argument (D-03/AEDIT-09)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum
    from api.services.admin_arguments import delete_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.UNPUBLISHED, resolved_at=None)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        result = await delete_argument(db, arg_id)
    assert result is False

    async with AsyncSessionLocal() as db:
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


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


# ---------------------------------------------------------------------------
# Three-state lifecycle + ArgumentStatusLog audit trail (Phase 26 Plan 01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_argument_from_draft_writes_one_published_log_row() -> None:
    """publish_argument on a DRAFT (resolved) argument sets status=PUBLISHED,
    stamps published_at, and writes exactly one PUBLISHED log row (T-26-03).
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        result = await publish_argument(db, arg_id)

    assert result is not None
    assert result["status"] == ArgumentStatusEnum.PUBLISHED
    assert result["published_at"] is not None

    async with AsyncSessionLocal() as db:
        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        log_rows = log_result.scalars().all()
        assert len(log_rows) == 1
        assert log_rows[0].status == ArgumentStatusEnum.PUBLISHED

        # cleanup
        arg = await db.get(Argument, arg_id)
        await db.delete(log_rows[0])
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublish_then_republish_succeeds_and_preserves_published_at() -> None:
    """unpublish_argument sets status=UNPUBLISHED and leaves published_at intact;
    a subsequent publish_argument call succeeds (re-publish, D-02/AEDIT-08) and
    re-stamps published_at. Each transition writes exactly one matching log row.
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument, unpublish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.commit()
        arg_id = arg.id
        original_published_at = arg.published_at

    # --- unpublish ---
    async with AsyncSessionLocal() as db:
        result = await unpublish_argument(db, arg_id)

    assert result is not None
    assert result["status"] == ArgumentStatusEnum.UNPUBLISHED
    assert result["published_at"] is not None
    assert result["published_at"] == original_published_at

    # unpublishing a DRAFT/UNPUBLISHED argument raises (guard keys on status)
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError):
            await unpublish_argument(db, arg_id)

    # --- re-publish from UNPUBLISHED must succeed (not "Already published") ---
    async with AsyncSessionLocal() as db:
        result = await publish_argument(db, arg_id)

    assert result is not None
    assert result["status"] == ArgumentStatusEnum.PUBLISHED
    assert result["published_at"] is not None

    async with AsyncSessionLocal() as db:
        log_result = await db.execute(
            select(ArgumentStatusLog)
            .where(ArgumentStatusLog.argument_id == arg_id)
            .order_by(ArgumentStatusLog.id)
        )
        log_rows = log_result.scalars().all()
        assert len(log_rows) == 2
        assert log_rows[0].status == ArgumentStatusEnum.UNPUBLISHED
        assert log_rows[1].status == ArgumentStatusEnum.PUBLISHED

        # cleanup
        arg = await db.get(Argument, arg_id)
        for row in log_rows:
            await db.delete(row)
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_publish_argument_already_published_raises() -> None:
    """publish_argument on a PUBLISHED argument must raise ValueError."""
    import datetime

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum
    from api.services.admin_arguments import publish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError):
            await publish_argument(db, arg_id)

    async with AsyncSessionLocal() as db:
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


# ---------------------------------------------------------------------------
# list_arguments / update_argument slug-freeze — three-state status keying
# (Phase 26 Plan 01, ALIST-01, ALIST-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_arguments_includes_unpublished_row() -> None:
    """list_arguments() must include a row whose Argument.status is UNPUBLISHED
    (ALIST-02) — only PIPELINE-status arguments are excluded.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
    from api.services.admin_arguments import list_arguments

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.UNPUBLISHED, resolved_at=None)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="26-01-TEST-UNPUB",
            docket_number_norm="26-01-test-unpub",
            case_name="Synthetic Test Case v. UNPUBLISHED",
            term_year=2026,
            slug="synthetic-test-case-v-unpublished-26-01",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id

    async with AsyncSessionLocal() as db:
        rows = await list_arguments(db)

    matching = [r for r in rows if r["id"] == arg_id]
    assert len(matching) == 1
    assert matching[0]["status"] == ArgumentStatusEnum.UNPUBLISHED

    async with AsyncSessionLocal() as db:
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        case = await db.get(Case, case_id)
        await db.delete(case)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_slug_frozen_for_unpublished() -> None:
    """update_argument() must NOT re-derive the slug when the argument's
    status is UNPUBLISHED — only case_name updates; slug stays unchanged
    (ALIST-01, slug-freeze keys on status not published_at).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.UNPUBLISHED, resolved_at=None)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="26-01-TEST-SLUG",
            docket_number_norm="26-01-test-slug",
            case_name="Original Case Name",
            term_year=2026,
            slug="original-case-name-slug-frozen",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        original_slug = case.slug

    async with AsyncSessionLocal() as db:
        result = await update_argument(
            db, arg_id, ArgumentUpdate(case_name="Renamed Case Name")
        )

    assert result is not None
    assert result["case_name"] == "Renamed Case Name"
    assert result["slug"] == original_slug

    async with AsyncSessionLocal() as db:
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        case = await db.get(Case, case_id)
        await db.delete(case)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()
