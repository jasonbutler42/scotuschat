"""
Published-lock enforcement on the participant-side write path (Phase 49, D-35).

`update_participant_side` and its bench sibling must refuse a PUBLISHED
argument and must still accept draft/unpublished ones. These are LIVE
database assertions — the claim is NON-PERSISTENCE, not merely that an
exception was raised.

Also covers, at the Python layer: the guard ordering (published check
precedes the authority gate), that both participant writers share one
published predicate, that unresolved sides are still rejected, and that
exactly one authority-gated call handles `side`.

Trimmed 2026-08-27 (debridement pass): 20 static `.svelte`-source
assertions removed. They proved strings were present in source and proved
nothing about the rendered page — the failure mode that let 28 green tests
pass against a fully broken button in plan 48-10. Frontend behavior here is
verified by eye. See CLAUDE.md -> Testing Policy.
"""

import ast
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]

ADMIN_ARGUMENTS_SERVICE_PATH = ROOT / "api" / "services" / "admin_arguments.py"
ADMIN_JOBS_SERVICE_PATH = ROOT / "api" / "services" / "admin_jobs.py"
FOLDED_TODO_SLUG = "2026-08-21-widen-participant-editability-to-all-unpublished-states"


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _service_function_source_lines(module_path: Path, function_name: str) -> list[str]:
    """
    Read a Python service module and return non-comment, non-blank lines from
    the named async function's body. Local copy of the helper in
    test_published_gate.py (`_service_function_source_lines`), generalized to
    take a Path directly rather than a filename relative to api/services/ —
    deliberately not imported across test modules.
    """
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            start = node.lineno
            end = node.end_lineno
            lines = source.splitlines()[start - 1 : end]
            non_comment = [
                line for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            return non_comment
    return []


# ─────────────────────────────────────────────────────────────────────────
# Task 1 (WR-01): the create-person popover resyncs its side on OPEN, not
# only on close.
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# Task 2: the published lock on `update_participant_side` (D-35 half one).
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_side_refuses_a_published_argument() -> None:
    """
    D-35: "If an argument is currently published, the data for that argument
    is locked." A live proof (rolled back in this session) showed a side
    write on PUBLISHED argument 1803 / participant 3684 previously returned
    `{'write_decision': 'accept'}` — this test proves that hole is closed.

    This asserts NON-PERSISTENCE, not merely that an exception was raised:
    side, descriptor, and review_state are all re-read from a fresh session
    after the raise and asserted unchanged, and no new value_discrepancy row
    is left behind for this participant.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        ReviewState,
        SideEnum,
        ValueDiscrepancy,
    )
    from api.services.admin_arguments import update_participant_side
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED)
        db.add(arg)
        await db.flush()

        advocate = Person(full_name="Published Lock Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MR. PUBLISHED LOCK ADVOCATE",
            side=SideEnum.PETITIONER,
            descriptor="Original Descriptor",
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        advocate_id = advocate.id
        participant_id = participant.id

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await update_participant_side(
                    db, arg_id, participant_id, SideEnum.RESPONDENT, "Should not persist"
                )

        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            assert p.side == SideEnum.PETITIONER
            assert p.descriptor == "Original Descriptor"
            assert p.review_state == ReviewState.UNREVIEWED

            disc_result = await db.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id == participant_id,
                    ValueDiscrepancy.resolved_at.is_(None),
                )
            )
            assert disc_result.scalar_one_or_none() is None, (
                "a refused write on a PUBLISHED argument must leave no open "
                "value_discrepancy row behind"
            )
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person = await db.get(Person, advocate_id)
            if person is not None:
                await db.delete(person)
            argument = await db.get(Argument, arg_id)
            if argument is not None:
                await db.delete(argument)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_participant_side_still_accepts_unpublished_and_draft() -> None:
    """
    The folded todo `2026-08-21-widen-participant-editability-to-all-unpublished-states`
    exists because the resolve writer's ORIGINAL guard was CANDIDATE-only and
    had to be widened. The new guard here must key on PUBLISHED alone — a
    CANDIDATE-only or DRAFT-only predicate would re-introduce that exact bug
    on a second path.
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

    for status in (ArgumentStatusEnum.UNPUBLISHED, ArgumentStatusEnum.DRAFT):
        async with AsyncSessionLocal() as db:
            arg = Argument(status=status)
            db.add(arg)
            await db.flush()

            advocate = Person(full_name=f"Still Editable Advocate {status.value}")
            db.add(advocate)
            await db.flush()

            participant = ArgumentParticipant(
                argument_id=arg.id,
                person_id=advocate.id,
                raw_speaker_label="MR. STILL EDITABLE ADVOCATE",
                side=SideEnum.UNKNOWN,
            )
            db.add(participant)
            await db.commit()

            arg_id = arg.id
            advocate_id = advocate.id
            participant_id = participant.id

        try:
            async with AsyncSessionLocal() as db:
                result = await update_participant_side(
                    db, arg_id, participant_id, SideEnum.PETITIONER
                )
            assert result is not None
            assert result["side"] == SideEnum.PETITIONER.value

            async with AsyncSessionLocal() as db:
                p = await db.get(ArgumentParticipant, participant_id)
                assert p.side == SideEnum.PETITIONER
        finally:
            async with AsyncSessionLocal() as db:
                p = await db.get(ArgumentParticipant, participant_id)
                if p is not None:
                    await db.delete(p)
                person = await db.get(Person, advocate_id)
                if person is not None:
                    await db.delete(person)
                argument = await db.get(Argument, arg_id)
                if argument is not None:
                    await db.delete(argument)
                await db.commit()


def test_published_guard_precedes_the_authority_gate() -> None:
    """
    `apply_participant_value_change` records a value_discrepancy as part of
    DECIDING a write (D-16). If the published check ran after it, a refused
    edit would still leave a discrepancy row and a review_state advance
    behind — a rejected write with side effects. The guard must run BEFORE
    the first authority-gate call in source order.
    """
    lines = _service_function_source_lines(ADMIN_ARGUMENTS_SERVICE_PATH, "update_participant_side")
    assert lines, "could not extract update_participant_side() body"

    published_idx = next(
        (i for i, line in enumerate(lines) if "ArgumentStatusEnum.PUBLISHED" in line),
        None,
    )
    gate_idx = next(
        (i for i, line in enumerate(lines) if "apply_participant_value_change(" in line),
        None,
    )
    assert published_idx is not None, (
        f"update_participant_side() must compare status to "
        f"ArgumentStatusEnum.PUBLISHED. Actual body:\n{chr(10).join(lines)}"
    )
    assert gate_idx is not None, (
        f"update_participant_side() must call apply_participant_value_change(). "
        f"Actual body:\n{chr(10).join(lines)}"
    )
    assert published_idx < gate_idx, (
        "the published-status check must precede the first authority-gate "
        "call: apply_participant_value_change records a value_discrepancy as "
        "part of deciding a write, so a refusal placed after it would leave "
        f"a discrepancy row and a review_state advance behind. Actual body:\n{chr(10).join(lines)}"
    )


def test_both_participant_writers_share_one_published_predicate() -> None:
    """
    D-35's whole point is that the two participant-value writers behave
    identically on the published question. This assertion is what stops
    them drifting apart a third time.
    """
    side_lines = _service_function_source_lines(ADMIN_ARGUMENTS_SERVICE_PATH, "update_participant_side")
    resolve_lines = _service_function_source_lines(ADMIN_JOBS_SERVICE_PATH, "update_resolve_row_for_job")

    assert side_lines, "could not extract update_participant_side() body"
    assert resolve_lines, "could not extract update_resolve_row_for_job() body"

    side_text = "\n".join(side_lines)
    resolve_text = "\n".join(resolve_lines)

    assert "ArgumentStatusEnum.PUBLISHED" in side_text, (
        f"update_participant_side() must compare status to ArgumentStatusEnum.PUBLISHED. "
        f"Actual body:\n{side_text}"
    )
    assert "ArgumentStatusEnum.PUBLISHED" in resolve_text, (
        f"update_resolve_row_for_job() must compare status to ArgumentStatusEnum.PUBLISHED. "
        f"Actual body:\n{resolve_text}"
    )
    assert FOLDED_TODO_SLUG in side_text, (
        f"update_participant_side()'s published-guard error must cite the folded "
        f"todo {FOLDED_TODO_SLUG!r}. Actual body:\n{side_text}"
    )
    assert FOLDED_TODO_SLUG in resolve_text, (
        f"update_resolve_row_for_job()'s published-guard error must cite the folded "
        f"todo {FOLDED_TODO_SLUG!r}. Actual body:\n{resolve_text}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Task 3: the lock made visible on the Speakers card, and honest rejection
# copy in the server action.
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# Plan 49-10, Task 1 (G-49-3/D-35): the shared side/bucket module — the
# bucket rule, the operator-visible role labels, and the specific-advocate-
# role helper exist in exactly ONE place, consumed by both the Resolve card
# and the Speakers card. `test_side_bucket_helper_treats_all_advocate_
# roles_as_one_bucket` in test_phase44_resolve_table_contract.py is the
# re-pointed declaration assertion for the bucket rule itself; the
# assertions below cover the label map and the specific-advocate-role
# helper, which that module does not otherwise touch.
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# Plan 49-10, Task 2 (G-49-3/D-35): the backend accepts BENCH under
# RESOLVE-13, and T-15-02-BENCH is retired as SATISFIED (not weakened) — its
# reconciliation concern is met at the new call site by four compensating
# controls (Task 3's boundary confirm, the no-fallback tenure derivation,
# the Missing-tenure/no-person affordance, and 49-09's published lock).
# ─────────────────────────────────────────────────────────────────────────

BENCH_REJECTION_STRING = "BENCH cannot be set via participant side update"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_side_write_succeeds_and_preserves_the_stored_descriptor() -> None:
    """RESOLVE-13: a bench write must skip the descriptor column entirely —
    the stored descriptor is preserved, and a client-supplied bench
    descriptor is deliberately ignored (passed here on purpose) rather than
    written. T-15-02-BENCH's retirement (D-35) means this call must now
    SUCCEED on a non-published argument rather than raise.
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

        person = Person(full_name="Bench Retirement Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. BENCH RETIREMENT ADVOCATE",
            side=SideEnum.PETITIONER,
            descriptor="Original Descriptor",
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        person_id = person.id
        participant_id = participant.id

    try:
        async with AsyncSessionLocal() as db:
            result = await update_participant_side(
                db, arg_id, participant_id, SideEnum.BENCH, "Should not persist"
            )
        assert result is not None
        assert result["side"] == SideEnum.BENCH.value
        assert result["descriptor"] == "Original Descriptor", (
            "the returned descriptor must report the row's EXISTING descriptor, not the "
            "ignored incoming one — the return value must not claim a write that did not "
            "happen"
        )

        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            assert p.side == SideEnum.BENCH
            assert p.descriptor == "Original Descriptor", (
                "RESOLVE-13: a bench write must never clobber the stored descriptor, even "
                "when a client supplies one in the same call"
            )
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person_row = await db.get(Person, person_id)
            if person_row is not None:
                await db.delete(person_row)
            argument = await db.get(Argument, arg_id)
            if argument is not None:
                await db.delete(argument)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_round_trip_does_not_lose_the_descriptor() -> None:
    """The sharpest defect in this convergence (planner_decisions): RESOLVE-13
    preserves a bench row's descriptor but the read path reports it null, so
    a naive bench->advocate move would submit an empty string and clobber
    the very value RESOLVE-13 protected. This mirrors
    test_phase44_argument_role_roundtrip.py's equivalent proof on the
    resolve path — advocate(descriptor) -> bench -> advocate, with the
    descriptor OMITTED on the return leg (which is what Task 3's form action
    will do), must still report the ORIGINAL descriptor.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.services.admin_arguments import list_argument_speakers, update_participant_side

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        person = Person(full_name="Round Trip Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MS. ROUND TRIP ADVOCATE",
            side=SideEnum.RESPONDENT,
            descriptor="Counsel for Respondent",
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        person_id = person.id
        participant_id = participant.id

    try:
        # advocate -> bench (descriptor omitted, mirroring the round-trip's first leg)
        async with AsyncSessionLocal() as db:
            await update_participant_side(db, arg_id, participant_id, SideEnum.BENCH)

        # bench -> advocate (descriptor OMITTED — Task 3's committed-side rule)
        async with AsyncSessionLocal() as db:
            await update_participant_side(db, arg_id, participant_id, SideEnum.PETITIONER)

        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            assert p.descriptor == "Counsel for Respondent", (
                "the descriptor must survive the full advocate -> bench -> advocate round "
                "trip even though it is omitted on both legs of the call"
            )

        async with AsyncSessionLocal() as db:
            speakers = await list_argument_speakers(db, arg_id)
        speaker = next(s for s in speakers if s["participant_id"] == participant_id)
        assert speaker["descriptor"] == "Counsel for Respondent", (
            "the read path must report the original descriptor once the row is an "
            "advocate row again — proving the round trip live, not by source grep"
        )
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person_row = await db.get(Person, person_id)
            if person_row is not None:
                await db.delete(person_row)
            argument = await db.get(Argument, arg_id)
            if argument is not None:
                await db.delete(argument)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_write_advances_review_state_and_closes_discrepancies() -> None:
    """The bench path must not be a quieter path than the advocate path: it
    advances review_state to OPERATOR_EDITED and closes this participant's
    open value_discrepancy rows, exactly as an advocate write does."""
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        ReviewState,
        SideEnum,
        ValueDiscrepancy,
    )
    from api.services.admin_arguments import update_participant_side

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        person = Person(full_name="Discrepancy Bench Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. DISCREPANCY BENCH ADVOCATE",
            side=SideEnum.PETITIONER,
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        person_id = person.id
        participant_id = participant.id

    try:
        async with AsyncSessionLocal() as db:
            await update_participant_side(db, arg_id, participant_id, SideEnum.BENCH)

        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            assert p.review_state == ReviewState.OPERATOR_EDITED

            disc_result = await db.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id == participant_id,
                    ValueDiscrepancy.resolved_at.is_(None),
                )
            )
            assert disc_result.scalar_one_or_none() is None, (
                "a bench write must close any open value_discrepancy row for this "
                "participant, same as the advocate path"
            )
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person_row = await db.get(Person, person_id)
            if person_row is not None:
                await db.delete(person_row)
            argument = await db.get(Argument, arg_id)
            if argument is not None:
                await db.delete(argument)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_bench_write_still_refused_on_a_published_argument() -> None:
    """Proves the retirement did not reopen 49-09's hole: 49-09's published
    lock is the compensating control the retirement rests on, and it must
    still refuse a bench write exactly as it refuses any other side write.
    This assertion is expected to ALREADY PASS before this task's source
    edit — today's bench raise fires unconditionally before the published
    check is ever reached, so the write is refused either way. Recorded
    here explicitly (not merely inferred) so the retirement's compensating
    control is proved directly rather than assumed.
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
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED)
        db.add(arg)
        await db.flush()

        person = Person(full_name="Published Bench Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. PUBLISHED BENCH ADVOCATE",
            side=SideEnum.PETITIONER,
            descriptor="Should Not Change",
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        person_id = person.id
        participant_id = participant.id

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await update_participant_side(db, arg_id, participant_id, SideEnum.BENCH)

        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            assert p.side == SideEnum.PETITIONER
            assert p.descriptor == "Should Not Change"
    finally:
        async with AsyncSessionLocal() as db:
            p = await db.get(ArgumentParticipant, participant_id)
            if p is not None:
                await db.delete(p)
            person_row = await db.get(Person, person_id)
            if person_row is not None:
                await db.delete(person_row)
            argument = await db.get(Argument, arg_id)
            if argument is not None:
                await db.delete(argument)
            await db.commit()


def test_unresolved_sides_are_still_rejected() -> None:
    """T-15-02-BENCH's retirement is scoped to BENCH alone — the unresolved-
    side rejection (T-26-14) is untouched by this plan. Expected to ALREADY
    PASS: today's guard already raises for both UNKNOWN and the legacy
    ADVOCATE literal, and this task does not touch that guard.
    """
    from typing import Any

    from api.models.models import SideEnum
    from api.services.admin_arguments import update_participant_side

    sentinel_session: Any = None

    import asyncio

    async def _run() -> None:
        with pytest.raises(ValueError):
            await update_participant_side(sentinel_session, 1, 1, SideEnum.UNKNOWN)
        with pytest.raises(ValueError):
            await update_participant_side(sentinel_session, 1, 1, SideEnum.ADVOCATE)

    asyncio.run(_run())


def test_one_authority_gated_call_handles_side() -> None:
    """49-04 D2/D-31a: every value write to argument_participants routes
    through the ONE authority-gated writer. This asserts exactly one
    authority-gate call passes the side field, and that the bench-rejection
    error string no longer exists anywhere in the service module — the
    retirement removes a refusal, it does not add a writer.
    """
    lines = _service_function_source_lines(ADMIN_ARGUMENTS_SERVICE_PATH, "update_participant_side")
    assert lines, "could not extract update_participant_side() body"

    side_gate_calls = [
        i
        for i, line in enumerate(lines)
        if "apply_participant_value_change(" in line
    ]
    # There may be two apply_participant_value_change(...) call sites in this
    # function (side and, conditionally, descriptor) — exactly one of them
    # must carry field="side".
    full_body = "\n".join(lines)
    side_field_occurrences = full_body.count('field="side"')
    assert side_field_occurrences == 1, (
        f"expected exactly one authority-gate call handling the side field, found "
        f"{side_field_occurrences}. Actual body:\n{full_body}"
    )

    module_source = _source(ADMIN_ARGUMENTS_SERVICE_PATH)
    assert BENCH_REJECTION_STRING not in module_source, (
        f"the retired bench-rejection string {BENCH_REJECTION_STRING!r} must no longer "
        f"exist anywhere in api/services/admin_arguments.py"
    )


# ─────────────────────────────────────────────────────────────────────────
# Plan 49-10, Task 3 (G-49-3/D-35): one converged Speakers row — five
# reachable side values, a boundary confirm, and equal affordance for bench
# and advocate. Every assertion in this section is STRUCTURAL-ONLY: it
# proves a string/pattern is present in source, never that the control
# renders or behaves correctly in a browser (the 48-10 false-green
# incident — 28 green source-contract tests against a fully broken button
# — is exactly the failure mode this label guards against). The six-item
# human-check in 49-10-PLAN.md's Task 3 is the actual behavioral evidence.
# ─────────────────────────────────────────────────────────────────────────


