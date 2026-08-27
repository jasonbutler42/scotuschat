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
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize("schema_name,field", [
    ("argument", "case_name"), ("argument", "docket_number"),
    ("metadata", "case_name"), ("metadata", "source_docket"),
])
@pytest.mark.parametrize("invalid", [None, "", " \t\n", "\u2003\u00a0"])
def test_required_patch_scalars_reject_explicit_empty_values(schema_name, field, invalid):
    from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate

    schema = ArgumentUpdate if schema_name == "argument" else MetadataUpdate
    with pytest.raises(ValidationError) as exc:
        schema(**{field: invalid})
    assert exc.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("schema_name,field", [
    ("argument", "case_name"), ("argument", "docket_number"),
    ("metadata", "case_name"), ("metadata", "source_docket"),
])
def test_required_patch_scalars_trim_outer_whitespace_only(schema_name, field):
    from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate

    schema = ArgumentUpdate if schema_name == "argument" else MetadataUpdate
    model = schema(**{field: "\u2003 Alpha  Beta \t"})
    assert getattr(model, field) == "Alpha  Beta"
    assert field in model.model_fields_set


def test_required_patch_fields_can_be_omitted():
    from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate

    assert ArgumentUpdate().model_fields_set == set()
    assert MetadataUpdate().model_fields_set == set()


@pytest.mark.parametrize("invalid", [None, [], [""], [" \t", "\u2003"]])
def test_source_dockets_rejects_empty_normalized_collection(invalid):
    from api.schemas.admin_arguments import MetadataUpdate

    with pytest.raises(ValidationError) as exc:
        MetadataUpdate(source_dockets=invalid)
    assert exc.value.errors()[0]["loc"] == ("source_dockets",)


def test_source_dockets_normalizes_once_in_first_seen_order_and_wins():
    from api.schemas.admin_arguments import MetadataUpdate

    body = MetadataUpdate(
        source_docket="legacy-1",
        source_dockets=[" ", " 24-1 ", "24-2", "24-1", "\t24-3\n"],
    )
    assert body.source_dockets == ["24-1", "24-2", "24-3"]
    assert body.source_docket == "legacy-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body_kwargs", "stored_docket", "stored_question"),
    [
        ({"source_docket": "24-1"}, "old", 2),
        ({"question_number": "2"}, "24-1", 1),
    ],
)
async def test_metadata_update_rejects_final_pair_collision(
    body_kwargs, stored_docket, stored_question
) -> None:
    from api.models.models import ArgumentStatusEnum
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import DuplicateArgumentError, update_argument_metadata

    db = AsyncMock()
    # status=DRAFT: D-35a's published guard (api/services/admin_arguments.py)
    # reads argument.status before this fixture's fixed side_effect list is
    # consulted — the attribute must exist, non-published, so the guard
    # passes through to the logic under test (49-11-PLAN.md Task 1 item 9).
    argument = SimpleNamespace(
        id=7, source_docket=stored_docket, question_number=stored_question,
        status=ArgumentStatusEnum.DRAFT,
    )
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: argument),
        MagicMock(scalar_one_or_none=lambda: 42),
    ]

    with pytest.raises(DuplicateArgumentError) as exc:
        await update_argument_metadata(db, 7, MetadataUpdate(**body_kwargs))
    assert exc.value.conflicting_argument_id == 42
    assert db.commit.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(("docket", "question"), [(None, 2), ("24-1", None)])
async def test_metadata_update_null_final_pair_does_not_collide(docket, question) -> None:
    from api.models.models import ArgumentStatusEnum
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    db = AsyncMock()
    # status=DRAFT: see the sibling test above — the guard reads this
    # attribute before anything else in the fixed side_effect list.
    argument = SimpleNamespace(
        id=7, source_docket=docket, question_number=question,
        status=ArgumentStatusEnum.DRAFT,
    )
    db.execute.side_effect = [MagicMock(scalar_one_or_none=lambda: argument), MagicMock()]
    assert await update_argument_metadata(db, 7, MetadataUpdate()) is True
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_metadata_array_writes_normalized_list_and_canonical_first_value() -> None:
    from api.models.models import ArgumentStatusEnum
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    db = AsyncMock()
    # status=DRAFT: see the published-guard fixtures above — the guard
    # reads this attribute before anything else in the fixed side_effect list.
    argument = SimpleNamespace(
        id=7, source_docket="old", question_number=None,
        status=ArgumentStatusEnum.DRAFT,
    )
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: argument),
        MagicMock(scalar_one_or_none=lambda: None),
        MagicMock(),
        MagicMock(),  # Phase 50 plan 50-03: _stamp_operator_provenance's own update(Argument)
    ]
    body = MetadataUpdate(
        source_docket="ignored",
        source_dockets=[" 24-2 ", "", "24-1", "24-2"],
    )

    assert await update_argument_metadata(db, 7, body) is True
    # -2, not -1: the LAST call is now _stamp_operator_provenance's own
    # update(Argument) (source_docket is in values_to_set, so Phase 50
    # plan 50-03's provenance stamp fires after this write).
    update_stmt = db.execute.await_args_list[-2].args[0]
    params = update_stmt.compile().params
    assert params["source_dockets"] == ["24-2", "24-1"]
    assert params["source_docket"] == "24-2"


def test_target_constraint_classifier_uses_structured_attributes_only() -> None:
    from api.services.argument_uniqueness import is_argument_pair_violation

    structured = SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_arguments_source_docket_question"))
    assert is_argument_pair_violation(structured)
    assert not is_argument_pair_violation(Exception("uq_arguments_source_docket_question"))


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


def test_delete_argument_utterances_before_import_run() -> None:
    """delete(Utterance) must appear before delete(ImportRun) in delete_argument
    (Pitfall 2 — utterances.import_run_id FK requires utterances deleted first).
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
    # Utterance delete must appear before ImportRun delete
    utterance_pos = func_body.find("delete(Utterance)")
    import_run_pos = func_body.find("delete(ImportRun)")
    assert utterance_pos != -1, "delete(Utterance) not found in delete_argument body"
    assert import_run_pos != -1, "delete(ImportRun) not found in delete_argument body"
    assert utterance_pos < import_run_pos, (
        "delete(Utterance) must appear before delete(ImportRun) "
        "(Pitfall 2: utterances.import_run_id FK order)"
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
    # We expect at least 5 delete() calls (Utterance, ImportRun, ArgumentParticipant,
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


def test_delete_argument_gate_keys_on_published() -> None:
    """delete_argument's status gate must be a single positive condition keyed
    on ArgumentStatusEnum.PUBLISHED — every OTHER status (CANDIDATE, DRAFT,
    UNPUBLISHED, and the retired PIPELINE value) returns True/deletes
    (D-25/PD-11, Phase 50).
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

    # The gate must key positively on PUBLISHED (not enumerate the other
    # three statuses, and not key on DRAFT the old way).
    assert "ArgumentStatusEnum.PUBLISHED" in func_body, (
        "delete_argument's gate must reference ArgumentStatusEnum.PUBLISHED"
    )
    gate_start = func_body.find("if argument.status")
    assert gate_start != -1, "delete_argument must have a status gate"
    gate_line_end = func_body.find("\n", gate_start)
    gate_line = func_body[gate_start:gate_line_end]
    assert "ArgumentStatusEnum.PUBLISHED" in gate_line, (
        f"Expected the status gate condition to key on PUBLISHED, found: {gate_line!r}"
    )
    assert "ArgumentStatusEnum.DRAFT" not in gate_line, (
        "delete_argument's gate must not key on DRAFT anymore — D-25/PD-11 "
        f"inverted it to a single published-only refusal, found: {gate_line!r}"
    )


# ---------------------------------------------------------------------------
# DB-guarded delete_argument behavioral tests (Phase 21 Plan 01; gate
# inverted to published-only by D-25/PD-11, Phase 50)
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
async def test_delete_argument_returns_true_for_unpublished() -> None:
    """delete_argument() must return True for an UNPUBLISHED argument and
    actually remove it (D-25/PD-11, Phase 50) — the prior gate refused
    UNPUBLISHED; it is now deletable like every non-published state."""
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
    assert result is True

    async with AsyncSessionLocal() as db:
        assert await db.get(Argument, arg_id) is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_true_for_pipeline_legacy_status() -> None:
    """delete_argument() must return True for a PIPELINE-status argument and
    actually remove it (D-25/PD-11, Phase 50).

    PIPELINE is the retired (Phase 48 D-01) born-state enum value — dead but
    still valid because PostgreSQL cannot drop an enum value. This case is
    kept as the dead-value regression fixture — the published-only gate
    treats it like any other non-published status.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum
    from api.services.admin_arguments import delete_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, resolved_at=None)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        result = await delete_argument(db, arg_id)
    assert result is True

    async with AsyncSessionLocal() as db:
        assert await db.get(Argument, arg_id) is None


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_false_for_published() -> None:
    """delete_argument() must return False for a PUBLISHED argument (D-25)
    — the only refused status — and leave the row untouched."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            resolved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    try:
        async with AsyncSessionLocal() as db:
            from api.services.admin_arguments import delete_argument

            result = await delete_argument(db, arg_id)
        assert result is False

        async with AsyncSessionLocal() as db:
            assert await db.get(Argument, arg_id) is not None
    finally:
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
                await db.commit()


# ---------------------------------------------------------------------------
# Phase 48 Plan 02 (D-22): delete_argument -> argument_status_log cascade
#
# D-03 makes every argument carry an argument_status_log row from birth,
# which makes the carried cascade defect (delete_argument's FK-ordered
# cascade never deletes argument_status_log rows, and that FK is NOT NULL
# with no ondelete clause, so PostgreSQL applies RESTRICT) reachable for
# every DRAFT argument. These tests prove the defect (pre-fix: red with a
# foreign-key violation) and then prove the fix (post-fix: green).
#
# Live repro captured before Task 2's fix landed (D-22 requires the actual
# failure output, not an asserted claim) — verbatim from the first run of
# `pytest api/tests/test_admin_arguments_service.py -q -k "cascade or
# refuses_candidate"` against the pre-fix service (2 failed, 1 passed):
#
#   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.IntegrityError)
#   <class 'asyncpg.exceptions.ForeignKeyViolationError'>: update or delete on
#   table "arguments" violates foreign key constraint
#   "argument_status_log_argument_id_fkey" on table "argument_status_log"
#   DETAIL:  Key (id)=(11402) is still referenced from table "argument_status_log".
#   [SQL: DELETE FROM arguments WHERE arguments.id = $1::INTEGER]
#   [parameters: (11402,)]
#
# Both cascade tests failed with this same error (only the argument id
# differed); test_delete_argument_still_refuses_candidate passed on this
# same pre-fix run, confirming D-05's gate is untouched by the defect.
# (SQLAlchemy wraps asyncpg's ForeignKeyViolationError in IntegrityError, exactly
# as 48-02-PLAN.md's Task 1 <behavior> predicted.)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_cascades_argument_status_log() -> None:
    """delete_argument() must delete argument_status_log rows for the
    argument before deleting the Argument row itself (D-22). A DRAFT
    argument carrying one status-log row must delete successfully — not
    raise ForeignKeyViolation — and leave zero argument_status_log rows
    behind.
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import delete_argument

    arg_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
            db.add(arg)
            await db.commit()
            arg_id = arg.id

        async with AsyncSessionLocal() as db:
            db.add(ArgumentStatusLog(argument_id=arg_id, status=ArgumentStatusEnum.DRAFT))
            await db.commit()

        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, arg_id)
        assert result is True

        async with AsyncSessionLocal() as db:
            assert await db.get(Argument, arg_id) is None
            remaining = await db.execute(
                select(func.count())
                .select_from(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == arg_id)
            )
            assert remaining.scalar_one() == 0
        arg_id = None  # deleted successfully — nothing left to clean up
    finally:
        if arg_id is not None:
            # Deletion failed or assertion tripped mid-way — clean up so the
            # rootdir conftest.py row-count tripwire still finds the dev DB
            # unchanged.
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
                )
                await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_cascades_multiple_status_log_rows() -> None:
    """delete_argument() must delete ALL argument_status_log rows for the
    argument, not just one — the post-D-03 reality is that every argument
    accumulates status-log history from birth (candidate, then draft).
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import delete_argument

    arg_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
            db.add(arg)
            await db.commit()
            arg_id = arg.id

        async with AsyncSessionLocal() as db:
            db.add(ArgumentStatusLog(argument_id=arg_id, status=ArgumentStatusEnum.CANDIDATE))
            db.add(ArgumentStatusLog(argument_id=arg_id, status=ArgumentStatusEnum.DRAFT))
            await db.commit()

        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, arg_id)
        assert result is True

        async with AsyncSessionLocal() as db:
            assert await db.get(Argument, arg_id) is None
            remaining = await db.execute(
                select(func.count())
                .select_from(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == arg_id)
            )
            assert remaining.scalar_one() == 0
        arg_id = None
    finally:
        if arg_id is not None:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
                )
                await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_returns_true_for_candidate() -> None:
    """delete_argument() must return True for a CANDIDATE-status argument
    and actually remove it, including its status-log row (D-25/PD-11,
    Phase 50) — the prior gate refused CANDIDATE on the theory that an
    active AdminJob might still reference it; corpus arguments carry no
    AdminJob at all as of this phase, so that reasoning no longer applies.
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import delete_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        db.add(ArgumentStatusLog(argument_id=arg_id, status=ArgumentStatusEnum.CANDIDATE))
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, arg_id)
        assert result is True

        async with AsyncSessionLocal() as db:
            assert await db.get(Argument, arg_id) is None
            remaining = await db.execute(
                select(func.count())
                .select_from(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == arg_id)
            )
            assert remaining.scalar_one() == 0
        arg_id = None
    finally:
        if arg_id is not None:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
                )
                await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
                await db.commit()


# ---------------------------------------------------------------------------
# D-26 (Phase 50 plan 50-03): delete_argument -> value_discrepancy cascade
#
# value_discrepancy.import_run_id is a hard FK to import_run.id (migration
# 0028), and delete_argument's cascade never touched value_discrepancy at
# all — so deleting an argument carrying any open discrepancy raised
# ForeignKeyViolation. Latent until now because almost nothing created
# discrepancies; D-01's always-reconcile (plan 50-05) makes it routine and
# D-25 makes candidates newly deletable. Each test below builds real
# value_discrepancy rows attributed to a real import_run row, so the
# ForeignKeyViolation this defect used to raise cannot be silently
# swallowed by a mock.
# ---------------------------------------------------------------------------


async def _seed_argument_with_lead_case_and_participant(*, status):
    """Seed one argument (given status) + lead Case + a real ImportRun +
    one ArgumentParticipant, returning every id a discrepancy test needs.
    Shared by the D-26 tests below — not exported, local to this module."""
    import uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        Case,
        CaseArgument,
        ImportRun,
        SideEnum,
    )

    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=status, resolved_at=None)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"D26-{suffix}",
            docket_number_norm=f"d26-{suffix}",
            case_name="D-26 Discrepancy Fixture v. Test Harness",
            term_year=2026,
            slug=f"d26-discrepancy-fixture-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        run = ImportRun(argument_id=arg.id, step="parse", source="corpus", method="direct")
        db.add(run)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            raw_speaker_label="MR. D26 SPEAKER",
            side=SideEnum.PETITIONER,
        )
        db.add(participant)
        await db.flush()

        await db.commit()
        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "import_run_id": run.id,
            "participant_id": participant.id,
        }


async def _teardown_argument_with_lead_case(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusLog,
        Case,
        CaseArgument,
        ImportRun,
        ValueDiscrepancy,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ValueDiscrepancy).where(
                ValueDiscrepancy.import_run_id == ids["import_run_id"]
            )
        )
        await db.execute(
            sa_delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == ids["argument_id"])
        )
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(ImportRun).where(ImportRun.id == ids["import_run_id"]))
        await db.execute(sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"]))
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_with_argument_scoped_discrepancy_succeeds_and_leaves_zero_rows() -> None:
    """Deleting an argument carrying an open value_discrepancy row with
    target_type="argument" targeting its own id succeeds (no
    ForeignKeyViolation) and leaves zero rows for that id (D-26)."""
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ValueDiscrepancy
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.CANDIDATE)
    async with AsyncSessionLocal() as db:
        db.add(
            ValueDiscrepancy(
                target_type="argument",
                target_id=ids["argument_id"],
                field="argued_date",
                import_run_id=ids["import_run_id"],
                incoming_value="2020-01-01",
                existing_value="2020-01-02",
            )
        )
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, ids["argument_id"])
        assert result is True

        async with AsyncSessionLocal() as db:
            remaining = await db.execute(
                select(func.count())
                .select_from(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "argument",
                    ValueDiscrepancy.target_id == ids["argument_id"],
                )
            )
            assert remaining.scalar_one() == 0
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_with_participant_scoped_discrepancy_succeeds_and_leaves_zero_rows() -> None:
    """Deleting an argument carrying an open value_discrepancy row with
    target_type="argument_participant" targeting its own participant
    succeeds and leaves zero rows for that id (D-26) — target_id is a SOFT
    reference with no FK, so this proves the participant leg is captured
    before step 4 deletes the participant row."""
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ValueDiscrepancy
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.DRAFT)
    async with AsyncSessionLocal() as db:
        db.add(
            ValueDiscrepancy(
                target_type="argument_participant",
                target_id=ids["participant_id"],
                field="person_id",
                import_run_id=ids["import_run_id"],
                incoming_value="42",
                existing_value=None,
            )
        )
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, ids["argument_id"])
        assert result is True

        async with AsyncSessionLocal() as db:
            remaining = await db.execute(
                select(func.count())
                .select_from(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id == ids["participant_id"],
                )
            )
            assert remaining.scalar_one() == 0
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_with_import_run_referencing_discrepancy_raises_no_fk_violation() -> None:
    """Deleting an argument that has value_discrepancy rows referencing its
    own import_run rows raises no ForeignKeyViolation (D-26's central
    claim — the pre-fix defect this whole test module documents)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ValueDiscrepancy
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.UNPUBLISHED)
    async with AsyncSessionLocal() as db:
        db.add(
            ValueDiscrepancy(
                target_type="argument",
                target_id=ids["argument_id"],
                field="question_number",
                import_run_id=ids["import_run_id"],
                incoming_value="2",
                existing_value="1",
            )
        )
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            # No try/except here on purpose — an un-caught ForeignKeyViolation
            # (wrapped in IntegrityError by SQLAlchemy) is exactly the pre-fix
            # failure this test must NOT reproduce.
            result = await delete_argument(db, ids["argument_id"])
        assert result is True
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_carrying_all_three_discrepancy_scopes_at_once_succeeds() -> None:
    """Deleting a CANDIDATE argument carrying argument-scoped, case-scoped
    (this argument the case's exclusive lead), and participant-scoped open
    discrepancies all at once — every one attributed to a real import_run
    row — succeeds with no ForeignKeyViolation and leaves zero
    value_discrepancy rows for any of the three targets (D-26's central
    multi-scope proof)."""
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ValueDiscrepancy
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.CANDIDATE)
    async with AsyncSessionLocal() as db:
        db.add(
            ValueDiscrepancy(
                target_type="argument",
                target_id=ids["argument_id"],
                field="argued_date",
                import_run_id=ids["import_run_id"],
                incoming_value="2020-01-01",
                existing_value="2020-01-02",
            )
        )
        db.add(
            ValueDiscrepancy(
                target_type="case",
                target_id=ids["case_id"],
                field="case_name",
                import_run_id=ids["import_run_id"],
                incoming_value="Renamed",
                existing_value="Original",
            )
        )
        db.add(
            ValueDiscrepancy(
                target_type="argument_participant",
                target_id=ids["participant_id"],
                field="person_id",
                import_run_id=ids["import_run_id"],
                incoming_value="42",
                existing_value=None,
            )
        )
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, ids["argument_id"])
        assert result is True

        async with AsyncSessionLocal() as db:
            for target_type, target_id in (
                ("argument", ids["argument_id"]),
                ("case", ids["case_id"]),
                ("argument_participant", ids["participant_id"]),
            ):
                remaining = await db.execute(
                    select(func.count())
                    .select_from(ValueDiscrepancy)
                    .where(
                        ValueDiscrepancy.target_type == target_type,
                        ValueDiscrepancy.target_id == target_id,
                    )
                )
                assert remaining.scalar_one() == 0, f"{target_type} discrepancy row must be gone"
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_does_not_delete_other_arguments_participant_or_person_discrepancies() -> None:
    """Deleting an argument does NOT delete a value_discrepancy row
    belonging to a DIFFERENT argument's participant, nor one whose
    target_type is "person" (D-26) — both must survive untouched."""
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, Person, ValueDiscrepancy
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.CANDIDATE)
    other_ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.CANDIDATE)

    async with AsyncSessionLocal() as db:
        person = Person(full_name="D-26 Survives Person")
        db.add(person)
        await db.flush()
        person_id = person.id

        db.add(
            ValueDiscrepancy(
                target_type="argument_participant",
                target_id=other_ids["participant_id"],
                field="person_id",
                import_run_id=other_ids["import_run_id"],
                incoming_value="7",
                existing_value=None,
            )
        )
        db.add(
            ValueDiscrepancy(
                target_type="person",
                target_id=person_id,
                field="first_name",
                import_run_id=ids["import_run_id"],
                incoming_value="Jane",
                existing_value="Jan",
            )
        )
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, ids["argument_id"])
        assert result is True

        async with AsyncSessionLocal() as db:
            other_remaining = await db.execute(
                select(func.count())
                .select_from(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id == other_ids["participant_id"],
                )
            )
            assert other_remaining.scalar_one() == 1

            person_remaining = await db.execute(
                select(func.count())
                .select_from(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "person",
                    ValueDiscrepancy.target_id == person_id,
                )
            )
            assert person_remaining.scalar_one() == 1
    finally:
        from sqlalchemy import delete as sa_delete_stmt

        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_delete_stmt(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id == other_ids["participant_id"],
                )
            )
            await db.execute(
                sa_delete_stmt(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "person",
                    ValueDiscrepancy.target_id == person_id,
                )
            )
            await db.execute(sa_delete_stmt(Person).where(Person.id == person_id))
            await db.commit()
        await _teardown_argument_with_lead_case(other_ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_argument_does_not_delete_shared_lead_case_discrepancy_of_another_argument() -> None:
    """Deleting an argument whose lead Case is ALSO lead for another
    argument does not delete that other argument's case-scoped
    discrepancy rows (D-26's NOT-EXISTS-equivalent scope guard) — Case is
    shared, so its discrepancy rows are not this argument's to delete
    unless this argument is the case's ONLY lead."""
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        CaseArgument,
        ImportRun,
        ValueDiscrepancy,
    )
    from api.services.admin_arguments import delete_argument

    ids = await _seed_argument_with_lead_case_and_participant(status=ArgumentStatusEnum.CANDIDATE)

    # A second argument that ALSO leads the same Case (shared lead case —
    # a real re-argument scenario, e.g. Obergefell Q1/Q2). The surviving
    # case-scoped discrepancy is attributed to THIS second argument's own
    # ImportRun, not the first argument's — the first argument's own
    # ImportRun is deleted as part of its own cascade (step 3), so a
    # discrepancy row that must SURVIVE cannot depend on it.
    async with AsyncSessionLocal() as db:
        second_arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
        db.add(second_arg)
        await db.flush()
        db.add(CaseArgument(case_id=ids["case_id"], argument_id=second_arg.id, is_lead=True))
        second_run = ImportRun(
            argument_id=second_arg.id, step="parse", source="corpus", method="direct"
        )
        db.add(second_run)
        await db.flush()
        db.add(
            ValueDiscrepancy(
                target_type="case",
                target_id=ids["case_id"],
                field="case_name",
                import_run_id=second_run.id,
                incoming_value="Renamed",
                existing_value="Original",
            )
        )
        await db.commit()
        second_arg_id = second_arg.id
        second_run_id = second_run.id

    try:
        async with AsyncSessionLocal() as db:
            result = await delete_argument(db, ids["argument_id"])
        assert result is True

        async with AsyncSessionLocal() as db:
            remaining = await db.execute(
                select(func.count())
                .select_from(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "case",
                    ValueDiscrepancy.target_id == ids["case_id"],
                )
            )
            assert remaining.scalar_one() == 1, (
                "the case-scoped discrepancy must survive — the second "
                "argument still leads this Case"
            )
    finally:
        from sqlalchemy import delete as sa_delete_stmt

        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_delete_stmt(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "case",
                    ValueDiscrepancy.target_id == ids["case_id"],
                )
            )
            await db.execute(
                sa_delete_stmt(CaseArgument).where(CaseArgument.argument_id == second_arg_id)
            )
            await db.execute(sa_delete_stmt(ImportRun).where(ImportRun.id == second_run_id))
            await db.execute(sa_delete_stmt(Argument).where(Argument.id == second_arg_id))
            await db.commit()
        # ids["argument_id"] was already deleted by delete_argument above;
        # its lead case row was NOT deleted by delete_argument (only
        # discrepancies/participants/import_run/status_log/CaseArgument for
        # THIS argument's own row are — the Case itself is never touched by
        # delete_argument), and it is still referenced by second_arg above,
        # so tear it down only after second_arg's own CaseArgument row is gone.
        async with AsyncSessionLocal() as db:
            from api.models.models import Case, ImportRun

            await db.execute(sa_delete_stmt(ImportRun).where(ImportRun.id == ids["import_run_id"]))
            await db.execute(sa_delete_stmt(Case).where(Case.id == ids["case_id"]))
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
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog, Case, CaseArgument
    from api.services.admin_arguments import publish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        # get_argument_detail (which publish_argument's return value delegates
        # to) requires a lead case to return non-None — without one it treats
        # the argument as a data-integrity issue and returns None.
        case = Case(
            docket_number="26-01-TEST-PUB",
            docket_number_norm="26-01-test-pub",
            case_name="Synthetic Test Case v. Publish",
            term_year=2026,
            slug="synthetic-test-case-v-publish-26-01",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id

    # Zero-constituent arguments floor to UNCERTAIN (Phase 48 D-13's
    # zero-constituent base case), which this pre-Phase-48 test's seeded
    # argument is — an override reason is required to reach the same
    # PUBLISHED outcome this test predates and is not itself testing (that
    # gate's own behavior is covered by api/tests/test_published_gate.py).
    async with AsyncSessionLocal() as db:
        result = await publish_argument(
            db, arg_id, override_reason="pre-existing test override"
        )

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

        # cleanup — no relationship() is configured between these models, so
        # the ORM unit-of-work cannot auto-derive FK-safe delete order; an
        # explicit flush() forces CaseArgument/log rows to delete before
        # Argument/Case (both of which they reference).
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        await db.delete(log_rows[0])
        await db.flush()
        case = await db.get(Case, case_id)
        await db.delete(case)
        arg = await db.get(Argument, arg_id)
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
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog, Case, CaseArgument
    from api.services.admin_arguments import publish_argument, unpublish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        # get_argument_detail (which publish_argument's return value delegates
        # to) requires a lead case to return non-None.
        case = Case(
            docket_number="26-01-TEST-REPUB",
            docket_number_norm="26-01-test-republ",
            case_name="Synthetic Test Case v. Republish",
            term_year=2026,
            slug="synthetic-test-case-v-republish-26-01",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
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
    # Zero-constituent arguments floor to UNCERTAIN (Phase 48 D-13's
    # zero-constituent base case), which this pre-Phase-48 test's seeded
    # argument is — an override reason is required here for the same reason
    # documented in test_publish_argument_from_draft_writes_one_published_log_row.
    async with AsyncSessionLocal() as db:
        result = await publish_argument(
            db, arg_id, override_reason="pre-existing test override"
        )

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

        # cleanup — explicit flush() forces FK-safe delete order (see comment
        # in test_publish_argument_from_draft_writes_one_published_log_row).
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        for row in log_rows:
            await db.delete(row)
        await db.flush()
        case = await db.get(Case, case_id)
        await db.delete(case)
        arg = await db.get(Argument, arg_id)
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


# ---------------------------------------------------------------------------
# PD-08 (Phase 50 plan 50-03): operator provenance stamping on the five
# Argument/Case compare-set columns via _stamp_operator_provenance, called
# from update_argument and update_argument_metadata.
# ---------------------------------------------------------------------------


async def _seed_draft_argument_with_lead_case_for_stamping():
    """Seed one DRAFT argument + lead Case with source/method left NULL
    (unstamped), returning the ids a stamping test needs."""
    import uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT, resolved_at=None)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"STAMP-{suffix}",
            docket_number_norm=f"stamp-{suffix}",
            case_name="Provenance Stamp Fixture v. Test Harness",
            term_year=2026,
            slug=f"provenance-stamp-fixture-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()
        return {"argument_id": arg.id, "case_id": case.id}


async def _teardown_draft_argument_with_lead_case(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        await db.execute(sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"]))
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_stamps_operator_provenance_on_argued_date_write() -> None:
    """After update_argument() writes argued_date, the argument row has
    source=OPERATOR and method=MANUAL (PD-08)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            result = await update_argument(
                db, ids["argument_id"], ArgumentUpdate(argued_date="2021-06-01")
            )
        assert result is not None

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.source == ImportSource.OPERATOR
            assert arg.method == ImportMethod.MANUAL
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_stamps_case_provenance_only_on_case_name_write() -> None:
    """After update_argument() writes the lead case's case_name, the lead
    Case row has source=OPERATOR/method=MANUAL, and the argument row's OWN
    provenance is untouched by a case-only edit (PD-08)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, Case, ImportMethod, ImportSource
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            result = await update_argument(
                db, ids["argument_id"], ArgumentUpdate(case_name="Renamed Stamp Fixture")
            )
        assert result is not None

        async with AsyncSessionLocal() as db:
            case = await db.get(Case, ids["case_id"])
            assert case.source == ImportSource.OPERATOR
            assert case.method == ImportMethod.MANUAL

            arg = await db.get(Argument, ids["argument_id"])
            assert arg.source is None, "a case-only edit must not stamp the argument row"
            assert arg.method is None
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_metadata_stamps_operator_provenance_on_question_number_write() -> None:
    """After update_argument_metadata() writes question_number, the
    argument row has source=OPERATOR and method=MANUAL (PD-08)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            ok = await update_argument_metadata(
                db, ids["argument_id"], MetadataUpdate(question_number="3")
            )
        assert ok is True

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.source == ImportSource.OPERATOR
            assert arg.method == ImportMethod.MANUAL
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_metadata_stamps_operator_provenance_on_source_docket_write() -> None:
    """After update_argument_metadata() writes source_docket, the argument
    row has source=OPERATOR and method=MANUAL (PD-08)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            ok = await update_argument_metadata(
                db, ids["argument_id"], MetadataUpdate(source_docket="26-STAMP-1")
            )
        assert ok is True

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.source == ImportSource.OPERATOR
            assert arg.method == ImportMethod.MANUAL
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_call_with_no_fields_leaves_provenance_unchanged() -> None:
    """A call that writes no field leaves both the argument's and the lead
    case's provenance unchanged (PD-08 <behavior>)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, Case
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            result = await update_argument(db, ids["argument_id"], ArgumentUpdate())
        assert result is not None

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            case = await db.get(Case, ids["case_id"])
            assert arg.source is None
            assert arg.method is None
            assert case.source is None
            assert case.method is None
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_operator_stamped_argument_value_rejects_disagreeing_corpus_write() -> None:
    """The round trip that proves the stamp is load-bearing, not decorative
    (PD-08 <behavior>): once update_argument() stamps an argument row's
    argued_date as OPERATOR-authored, a corpus apply_argument_value_change
    call with a DIFFERING incoming value returns REJECT_AND_RECORD and the
    stored value is byte-identical afterward."""
    from api.core.database import AsyncSessionLocal
    from api.domain.authority import WriteDecision
    from api.models.models import Argument
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument
    from api.services.admin_review import apply_argument_value_change

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            result = await update_argument(
                db, ids["argument_id"], ArgumentUpdate(argued_date="2021-06-01")
            )
        assert result is not None

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=arg,
                field="argued_date",
                incoming_value=__import__("datetime").date(2022, 1, 1),
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()
        assert decision == WriteDecision.REJECT_AND_RECORD

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.argued_date == __import__("datetime").date(2021, 6, 1), (
                "the operator-stamped value must survive the corpus write byte-identical"
            )
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


# ---------------------------------------------------------------------------
# list_argument_speakers — unified bench+advocate speakers list (Phase 26
# Plan 02, D-05, AEDIT-05/06/07)
# ---------------------------------------------------------------------------


def test_list_argument_speakers_importable() -> None:
    """list_argument_speakers must be importable from admin_arguments (no DB)."""
    from api.services.admin_arguments import list_argument_speakers  # noqa: F401


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_argument_speakers_returns_empty_for_missing_argument() -> None:
    """list_argument_speakers returns [] (not an exception) for a missing argument."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import list_argument_speakers

    async with AsyncSessionLocal() as db:
        rows = await list_argument_speakers(db, 999999)

    assert rows == []


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_argument_speakers_bench_advocate_and_utterance_counts() -> None:
    """One argument with a covered-tenure bench Justice, an uncovered-tenure
    bench Justice, and an advocate — asserts bench_role/missing_tenure,
    advocate descriptor/descriptor_hint, and a single-grouped-query utterance_count
    per participant (T-26-07).
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Person,
        SideEnum,
        Utterance,
    )
    from api.services.admin_arguments import list_argument_speakers

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            argued_date=datetime.date(2024, 1, 10),
        )
        db.add(arg)
        await db.flush()

        covered_justice = Person(full_name="Covered Justice", is_justice=True)
        uncovered_justice = Person(full_name="Uncovered Justice", is_justice=True)
        advocate = Person(full_name="Advocate Example")
        db.add_all([covered_justice, uncovered_justice, advocate])
        await db.flush()

        db.add(
            CourtTenure(
                person_id=covered_justice.id,
                office="associate",
                start_date=datetime.date(2010, 1, 1),
                end_date=None,
            )
        )
        await db.flush()

        bench_covered = ArgumentParticipant(
            argument_id=arg.id,
            person_id=covered_justice.id,
            raw_speaker_label="COVERED JUSTICE",
            side=SideEnum.BENCH,
        )
        bench_uncovered = ArgumentParticipant(
            argument_id=arg.id,
            person_id=uncovered_justice.id,
            raw_speaker_label="UNCOVERED JUSTICE",
            side=SideEnum.BENCH,
        )
        advocate_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MR. ADVOCATE",
            side=SideEnum.PETITIONER,
            descriptor="Counsel of Record",
        )
        db.add_all([bench_covered, bench_uncovered, advocate_participant])
        await db.flush()

        parse_run = ImportRun(
            argument_id=arg.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.RULE_BASED,
        )
        db.add(parse_run)
        await db.flush()

        # 3 utterances for the advocate, 1 for the covered justice, 0 for uncovered
        for i in range(3):
            db.add(
                Utterance(
                    argument_id=arg.id,
                    import_run_id=parse_run.id,
                    sequence=i,
                    raw_speaker_label="MR. ADVOCATE",
                    text=f"Advocate utterance {i}.",
                    person_id=advocate.id,
                )
            )
        db.add(
            Utterance(
                argument_id=arg.id,
                import_run_id=parse_run.id,
                sequence=3,
                raw_speaker_label="COVERED JUSTICE",
                text="Justice utterance.",
                person_id=covered_justice.id,
            )
        )
        await db.commit()

        arg_id = arg.id
        bench_covered_id = bench_covered.id
        bench_uncovered_id = bench_uncovered.id
        advocate_participant_id = advocate_participant.id
        covered_justice_id = covered_justice.id
        uncovered_justice_id = uncovered_justice.id
        advocate_id = advocate.id
        parse_run_id = parse_run.id

    async with AsyncSessionLocal() as db:
        rows = await list_argument_speakers(db, arg_id)

    assert len(rows) == 3
    by_id = {r["participant_id"]: r for r in rows}

    covered_row = by_id[bench_covered_id]
    assert covered_row["is_bench"] is True
    assert covered_row["bench_role"] == "Associate Justice"
    assert covered_row["argument_role"] == "Associate Justice"
    assert covered_row["missing_tenure"] is False
    assert covered_row["person_edit_href"] is None
    assert covered_row["descriptor"] is None
    assert covered_row["descriptor_hint"] is None
    assert covered_row["utterance_count"] == 1

    uncovered_row = by_id[bench_uncovered_id]
    assert uncovered_row["is_bench"] is True
    assert uncovered_row["bench_role"] is None
    assert uncovered_row["missing_tenure"] is True
    assert uncovered_row["person_edit_href"] == f"/admin/people/{uncovered_justice_id}"
    assert uncovered_row["utterance_count"] == 0

    advocate_row = by_id[advocate_participant_id]
    assert advocate_row["is_bench"] is False
    assert advocate_row["argument_role"] == "Petitioner's Counsel"
    assert advocate_row["descriptor"] == "Counsel of Record"
    assert advocate_row["descriptor_hint"] == "Counsel of Record"
    assert advocate_row["bench_role"] is None
    assert advocate_row["missing_tenure"] is False
    assert advocate_row["utterance_count"] == 3

    # Cleanup
    async with AsyncSessionLocal() as db:
        utt_result = await db.execute(
            select(Utterance).where(Utterance.argument_id == arg_id)
        )
        for u in utt_result.scalars().all():
            await db.delete(u)
        run = await db.get(ImportRun, parse_run_id)
        await db.delete(run)
        for pid in (bench_covered_id, bench_uncovered_id, advocate_participant_id):
            p = await db.get(ArgumentParticipant, pid)
            await db.delete(p)
        tenure_result = await db.execute(
            select(CourtTenure).where(CourtTenure.person_id == covered_justice_id)
        )
        for t in tenure_result.scalars().all():
            await db.delete(t)
        for person_id in (covered_justice_id, uncovered_justice_id, advocate_id):
            person = await db.get(Person, person_id)
            await db.delete(person)
        argument = await db.get(Argument, arg_id)
        await db.delete(argument)
        await db.commit()


# ---------------------------------------------------------------------------
# get_argument_detail status_log / speakers wiring (Phase 26 Plan 02, T-26-03,
# D-05) and update_participant_side descriptor persistence (D-06, T-26-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_argument_detail_includes_status_log_and_speakers() -> None:
    """get_argument_detail returns a non-empty status_log (oldest first) after a
    publish, and a speakers list covering every participant (T-26-03, D-05).
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        ArgumentStatusLog,
        Case,
        CaseArgument,
        Person,
        SideEnum,
    )
    from api.services.admin_arguments import get_argument_detail, publish_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        # get_argument_detail requires a lead case to return non-None.
        case = Case(
            docket_number="26-01-TEST-DETAIL",
            docket_number_norm="26-01-test-detail",
            case_name="Synthetic Test Case v. Detail",
            term_year=2026,
            slug="synthetic-test-case-v-detail-26-01",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        advocate = Person(full_name="Status Log Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MS. ADVOCATE",
            side=SideEnum.PETITIONER,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        advocate_id = advocate.id
        participant_id = participant.id

    # The single resolved ArgumentParticipant seeded above contributes no
    # tier (Phase 48 D-13 — a resolved participant has no source/method to
    # derive one from), and there are no utterances, so this argument floors
    # to UNCERTAIN (D-13's zero-constituent base case) — an override reason
    # is required, for the same reason documented in
    # test_publish_argument_from_draft_writes_one_published_log_row.
    async with AsyncSessionLocal() as db:
        await publish_argument(db, arg_id, override_reason="pre-existing test override")

    async with AsyncSessionLocal() as db:
        result = await get_argument_detail(db, arg_id)

    assert result is not None
    assert len(result["status_log"]) == 1
    assert result["status_log"][0]["status"] == ArgumentStatusEnum.PUBLISHED

    speaker_ids = {row["participant_id"] for row in result["speakers"]}
    assert participant_id in speaker_ids

    # Cleanup — explicit flush() forces FK-safe delete order (no relationship()
    # is configured between these models, so the ORM cannot auto-derive it):
    # log rows / participant / case_arguments (all reference Argument or
    # Case) must be gone before Person/Case/Argument themselves are deleted.
    async with AsyncSessionLocal() as db:
        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        for row in log_result.scalars().all():
            await db.delete(row)
        p = await db.get(ArgumentParticipant, participant_id)
        await db.delete(p)
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        await db.flush()

        person = await db.get(Person, advocate_id)
        await db.delete(person)
        case = await db.get(Case, case_id)
        await db.delete(case)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_argument_detail_status_log_orders_by_id_not_created_at() -> None:
    """get_argument_detail's status_log must return insertion order (by `id`)
    even when `created_at` disagrees with it (Phase 48-09 Finding 2,
    48-EVIDENCE.md).

    `ArgumentStatusLog.created_at` uses `server_default=func.now()`, and
    PostgreSQL's `now()` reflects the enclosing TRANSACTION's start time, not
    per-statement wall-clock time. A writer that opens a transaction earlier
    (e.g. for an unrelated read) and only later performs a status-log INSERT
    inside that same transaction can produce a `created_at` value that is
    *older* than a row inserted before it — exactly what was observed live
    against `reset_to_fixture`'s Draft fixture (argument 1785, oyez 13015):
    log_id=105 (candidate, created_at=17:05:09) inserted before
    log_id=108 (draft, created_at=17:04:20 — 49s EARLIER).

    This test constructs that exact skew explicitly (independent of reset
    timing) via a raw UPDATE on the second-inserted row's created_at, then
    asserts the returned order still matches insertion order (`id` ASC), not
    the corrupted `created_at` order.
    """
    import datetime

    from sqlalchemy import select, update

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        ArgumentStatusLog,
        Case,
        CaseArgument,
    )
    from api.services.admin_arguments import get_argument_detail

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="48-09-ORDER-TEST",
            docket_number_norm="48-09-order-test",
            case_name="Synthetic Test Case v. Ordering",
            term_year=2026,
            slug="synthetic-test-case-v-ordering-48-09",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.flush()

        # First inserted (lower id): the "candidate" birth row.
        candidate_log = ArgumentStatusLog(
            argument_id=arg.id, status=ArgumentStatusEnum.CANDIDATE
        )
        db.add(candidate_log)
        await db.flush()

        # Second inserted (higher id): the "draft" transition row.
        draft_log = ArgumentStatusLog(argument_id=arg.id, status=ArgumentStatusEnum.DRAFT)
        db.add(draft_log)
        await db.flush()

        arg_id = arg.id
        case_id = case.id
        candidate_log_id = candidate_log.id
        draft_log_id = draft_log.id
        assert candidate_log_id < draft_log_id  # sanity: true insertion order

        # Force the skew: give the SECOND-inserted (draft) row an EARLIER
        # created_at than the first-inserted (candidate) row, reproducing the
        # live anomaly without depending on any transaction/timing behavior.
        await db.execute(
            update(ArgumentStatusLog)
            .where(ArgumentStatusLog.id == draft_log_id)
            .values(
                created_at=datetime.datetime(
                    2026, 8, 20, 17, 4, 20, tzinfo=datetime.timezone.utc
                )
            )
        )
        await db.execute(
            update(ArgumentStatusLog)
            .where(ArgumentStatusLog.id == candidate_log_id)
            .values(
                created_at=datetime.datetime(
                    2026, 8, 20, 17, 5, 9, tzinfo=datetime.timezone.utc
                )
            )
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await get_argument_detail(db, arg_id)

    assert result is not None
    statuses = [row["status"] for row in result["status_log"]]
    # Insertion order (candidate first, draft second) must win despite
    # created_at reading the opposite. Before the fix (ORDER BY created_at
    # ASC, id ASC) this assertion fails: draft (stale created_at) sorts
    # first.
    assert statuses == [ArgumentStatusEnum.CANDIDATE, ArgumentStatusEnum.DRAFT]

    async with AsyncSessionLocal() as db:
        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        for row in log_result.scalars().all():
            await db.delete(row)
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        await db.flush()
        case_row = await db.get(Case, case_id)
        await db.delete(case_row)
        arg_row = await db.get(Argument, arg_id)
        await db.delete(arg_row)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_side_persists_descriptor_for_advocate() -> None:
    """update_participant_side writes descriptor when provided, leaves it unchanged
    when omitted (D-06, T-26-04). T-15-02-BENCH was retired as SATISFIED (not
    weakened) by D-35 in plan 49-10 — see update_participant_side's own
    docstring for the four compensating controls the retirement rests on —
    so the final block below no longer asserts a raise on side==BENCH; it
    asserts the new contract instead: the bench call succeeds, the stored
    descriptor is unchanged by it (RESOLVE-13), and a subsequent advocate
    call still returns the original descriptor.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.services.admin_arguments import update_participant_side

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        advocate = Person(full_name="Title Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MR. TITLE ADVOCATE",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        advocate_id = advocate.id
        participant_id = participant.id

    # Provide a descriptor alongside a side change — must persist.
    async with AsyncSessionLocal() as db:
        result = await update_participant_side(
            db, arg_id, participant_id, SideEnum.PETITIONER, "Counsel of Record"
        )
    assert result is not None
    assert result["side"] == SideEnum.PETITIONER.value
    assert result["descriptor"] == "Counsel of Record"

    # Omitting descriptor must leave the previously-persisted descriptor unchanged.
    async with AsyncSessionLocal() as db:
        result = await update_participant_side(
            db, arg_id, participant_id, SideEnum.RESPONDENT
        )
    assert result is not None
    assert result["side"] == SideEnum.RESPONDENT.value
    assert result["descriptor"] == "Counsel of Record"

    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        assert p.descriptor == "Counsel of Record"

    # T-15-02-BENCH retired (D-35, plan 49-10): a bench call now SUCCEEDS on a
    # non-published argument. A client-supplied descriptor on this call is
    # ignored (RESOLVE-13) — the stored descriptor stays "Counsel of Record".
    async with AsyncSessionLocal() as db:
        result = await update_participant_side(
            db, arg_id, participant_id, SideEnum.BENCH, "Should not persist"
        )
    assert result is not None
    assert result["side"] == SideEnum.BENCH.value
    assert result["descriptor"] == "Counsel of Record"

    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        assert p.side == SideEnum.BENCH
        assert p.descriptor == "Counsel of Record", (
            "RESOLVE-13: a bench write must never clobber the stored descriptor"
        )

    # A subsequent advocate call (descriptor omitted, as Task 3's committed-
    # side rule will do) must still report the original descriptor.
    async with AsyncSessionLocal() as db:
        result = await update_participant_side(db, arg_id, participant_id, SideEnum.RESPONDENT)
    assert result is not None
    assert result["descriptor"] == "Counsel of Record"

    # Cleanup
    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        await db.delete(p)
        person = await db.get(Person, advocate_id)
        await db.delete(person)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_side_second_operator_edit_persists() -> None:
    """Direct regression test for the authority-ceiling defect: TWO
    consecutive operator edits to the SAME participant through
    update_participant_side must BOTH actually persist.

    Before the fix: the first edit (existing rank UNKNOWN -> incoming
    OPERATOR) accepted and advanced review_state to OPERATOR_EDITED. The
    second edit (existing rank now OPERATOR -> incoming OPERATOR) hit
    decide_write's "equal authority rejects" rule and was silently
    REJECT_AND_RECORDed — the column never changed — and this function's
    own close_open_discrepancies call immediately closed the discrepancy
    the rejection had just recorded, leaving no trace anywhere. Critically,
    update_participant_side's return dict echoes back the REQUESTED side
    value regardless of whether the write was actually accepted (`"side":
    side.value`), so a test that only inspects the return value — like
    test_update_participant_side_persists_descriptor_for_advocate above —
    cannot detect this defect. This test re-fetches the row from the
    database after the second edit, which is the only way to prove the
    write genuinely took effect.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        ReviewState,
        SideEnum,
    )
    from api.services.admin_arguments import update_participant_side

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        advocate = Person(full_name="Second Edit Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MR. SECOND EDIT ADVOCATE",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        advocate_id = advocate.id
        participant_id = participant.id

    # First operator edit: UNKNOWN existing authority -> OPERATOR incoming
    # authority. Always accepted, even before the fix.
    async with AsyncSessionLocal() as db:
        result_1 = await update_participant_side(
            db, arg_id, participant_id, SideEnum.PETITIONER
        )
    assert result_1 is not None

    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        assert p.side == SideEnum.PETITIONER
        assert p.review_state == ReviewState.OPERATOR_EDITED

    # Second operator edit to the SAME participant: existing authority is
    # now OPERATOR (from the first edit) and the incoming write is also
    # OPERATOR — this is the defect's exact trigger.
    async with AsyncSessionLocal() as db:
        result_2 = await update_participant_side(
            db, arg_id, participant_id, SideEnum.RESPONDENT
        )
    assert result_2 is not None
    assert result_2["write_decision"] == "accept_and_record"

    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        # The genuine round-trip assertion: the second edit actually
        # persisted to the database, not just echoed back in the response.
        assert p.side == SideEnum.RESPONDENT
        assert p.review_state == ReviewState.OPERATOR_EDITED

    # Cleanup
    async with AsyncSessionLocal() as db:
        p = await db.get(ArgumentParticipant, participant_id)
        await db.delete(p)
        person = await db.get(Person, advocate_id)
        await db.delete(person)
        arg = await db.get(Argument, arg_id)
        await db.delete(arg)
        await db.commit()


@pytest.mark.asyncio
async def test_update_participant_side_rejects_unresolved_side() -> None:
    """update_participant_side must raise ValueError for both UNKNOWN and the
    legacy ADVOCATE side, before touching the database (T-26-14, CLAUDE.md
    no-silent-inference constraint) — an advocate's side must be authoritatively
    resolved to PETITIONER, RESPONDENT, or AMICUS.
    """
    from typing import Any

    from api.models.models import SideEnum
    from api.services.admin_arguments import update_participant_side

    # The guard raises before any session use, so a sentinel None session is safe.
    sentinel_session: Any = None

    with pytest.raises(ValueError):
        await update_participant_side(sentinel_session, 1, 1, SideEnum.UNKNOWN)

    with pytest.raises(ValueError):
        await update_participant_side(sentinel_session, 1, 1, SideEnum.ADVOCATE)


# ---------------------------------------------------------------------------
# G-50-2a: update_argument_metadata and update_argument are both
# operator-facing routes onto the SAME lead-Case column (case_name), so both
# must reach the same rung of the authority ladder. update_argument_metadata
# wrote the column without stamping, leaving the edit at CORPUS authority --
# found by the D-09 live walkthrough, 2026-08-26, not by these tests'
# predecessors (each route was only ever tested against itself).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_metadata_stamps_case_provenance_on_case_name_write() -> None:
    """The G-50-2a regression: after update_argument_metadata() writes the
    lead case's case_name, the lead Case row must reach OPERATOR authority.

    Case has no `review_state`, so `source` is the only carrier of the
    ladder's operator rung (api.domain.authority.authority_rank rule 2) --
    an unstamped edit is indistinguishable from a corpus value.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, Case, ImportMethod, ImportSource
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    ids = await _seed_draft_argument_with_lead_case_for_stamping()
    try:
        async with AsyncSessionLocal() as db:
            ok = await update_argument_metadata(
                db, ids["argument_id"], MetadataUpdate(case_name="Metadata Renamed Fixture")
            )
        assert ok is True

        async with AsyncSessionLocal() as db:
            case = await db.get(Case, ids["case_id"])
            assert case.case_name == "Metadata Renamed Fixture"
            assert case.source == ImportSource.OPERATOR
            assert case.method == ImportMethod.MANUAL

            # A case-only edit must not stamp the argument row -- the same
            # scoping update_argument observes (PD-08).
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.source is None, "a case-only edit must not stamp the argument row"
            assert arg.method is None
    finally:
        await _teardown_draft_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_both_operator_routes_onto_case_name_agree_on_authority() -> None:
    """Parity guard (G-50-2a): whichever operator route writes case_name,
    the lead Case must land on the same rung. This is the assertion whose
    absence let the two routes drift apart."""
    from api.core.database import AsyncSessionLocal
    from api.domain.authority import AuthorityRank, authority_rank
    from api.models.models import Case
    from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate
    from api.services.admin_arguments import update_argument, update_argument_metadata

    ranks = {}
    for label, apply in (
        ("update_argument", "argument"),
        ("update_argument_metadata", "metadata"),
    ):
        ids = await _seed_draft_argument_with_lead_case_for_stamping()
        try:
            async with AsyncSessionLocal() as db:
                if apply == "argument":
                    await update_argument(
                        db, ids["argument_id"], ArgumentUpdate(case_name=f"Renamed via {label}")
                    )
                else:
                    await update_argument_metadata(
                        db, ids["argument_id"], MetadataUpdate(case_name=f"Renamed via {label}")
                    )

            async with AsyncSessionLocal() as db:
                case = await db.get(Case, ids["case_id"])
                ranks[label] = authority_rank(
                    case.source.value if case.source else "",
                    case.method.value if case.method else "",
                    "",  # Case has no review_state
                )
        finally:
            await _teardown_draft_argument_with_lead_case(ids)

    assert ranks["update_argument"] == AuthorityRank.OPERATOR
    assert ranks["update_argument_metadata"] == AuthorityRank.OPERATOR
    assert ranks["update_argument"] == ranks["update_argument_metadata"], (
        f"the two operator routes onto case_name disagree on authority: {ranks}"
    )
