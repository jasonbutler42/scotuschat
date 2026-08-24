"""
Phase 49 Plan 09 — participant-side contract module.

D-35's FIRST half (the published lock) and WR-01 (the create-person
popover's open-time side resync) both land here. This module is a sibling
of the popover assertions in `test_phase49_cleanup_contract.py` and
deliberately does not modify that module — it defines its own local
`_source` / `_plain_function_body` helpers rather than importing across
test modules, matching this codebase's established pattern (see
test_phase38_people_ui_contract.py, test_phase48_publish_override_ui_
contract.py).

Scope across the two gap-closure plans that touch participant-side
handling: this module (49-09) covers WR-01's open-time resync and the
published lock on `update_participant_side`; plan 49-10 covers the
converged side/pool control. This module does not anticipate 49-10's
work.

Every `.svelte`-source assertion in this module is STRUCTURAL-ONLY: it
proves a string/pattern is present in source, never that the control
renders or behaves correctly in a browser. A `$state` proxy trap already
let 28 green source-contract tests pass against a fully broken button in
Phase 48 (plan 48-10) — see the project memory note on this exact failure
mode. Each structural test's docstring says so explicitly. The `<human-
check>` browser walkthroughs in 49-09-PLAN.md are the actual behavioral
evidence, not the tests below.

Task 2's central claims (the published lock) are LIVE database
assertions — not source greps — because the whole point is to prove
non-persistence, not merely that an exception was raised.
"""

import ast
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]

CREATE_PERSON_POPOVER_PATH = ROOT / "app" / "src" / "lib" / "components" / "CreatePersonPopover.svelte"
ADMIN_ARGUMENTS_SERVICE_PATH = ROOT / "api" / "services" / "admin_arguments.py"
ADMIN_JOBS_SERVICE_PATH = ROOT / "api" / "services" / "admin_jobs.py"
ARGUMENT_DETAIL_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.svelte"
ARGUMENT_DETAIL_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.server.ts"

FOLDED_TODO_SLUG = "2026-08-21-widen-participant-editability-to-all-unpublished-states"


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plain_function_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of a plain `function {name}(...) { ... }`
    declaration (not an arrow function or object property). Local copy of the
    helper in test_phase49_cleanup_contract.py — deliberately not imported
    across test modules."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*", source)
    assert match, f"could not find `function {name}(...)` in source"
    brace_start = source.index("{", match.end())
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : i + 1]
    raise AssertionError(f"unbalanced braces while extracting {name}")


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


def test_popover_resyncs_side_on_open_not_only_on_close() -> None:
    """
    WR-01 (49-REVIEW.md:297): `let side = $state<'BENCH'|'ADVOCATE'>(initialSide)`
    is a Svelte 5 state initializer, which reads `initialSide` exactly once at
    mount and is NOT reactive to later prop changes. `ResolveCard.svelte` passes
    `initialSide` to an always-rendered (never conditionally mounted) instance,
    so the only fix is an explicit resync on the open transition of
    `onOpenChange`, alongside the existing close-transition `resetForm()` call.

    STRUCTURAL-ONLY: this proves the open-transition branch exists in source,
    never that the popover renders correctly in a browser.
    """
    source = _source(CREATE_PERSON_POPOVER_PATH)
    match = re.search(r"onOpenChange=\{\(next\)\s*=>\s*\{(.*?)\}\}", source, re.DOTALL)
    assert match, "could not find the onOpenChange handler body"
    body = match.group(1)

    assert re.search(r"if\s*\(next\)\s*side\s*=\s*initialSide\s*;", body), (
        f"onOpenChange must reassign `side` from `initialSide` on the OPEN "
        f"transition (WR-01). Actual handler body:\n{body}"
    )
    assert re.search(r"else\s*resetForm\(\)\s*;", body), (
        f"onOpenChange must still call resetForm() on the CLOSE transition — "
        f"the fix complements the existing close-time reset, it does not "
        f"replace it. Actual handler body:\n{body}"
    )


def test_popover_does_not_resync_side_on_every_prop_change() -> None:
    """
    Resyncing `side` on every `initialSide` prop change (e.g. via a Svelte 5
    `$effect` tracking the prop) would discard a radio choice the operator
    deliberately made while the popover is open — a WORSE defect than WR-01
    describes. The fix must be a one-shot branch on the open transition, not
    an effect that tracks the prop continuously.

    STRUCTURAL-ONLY. If there are zero `$effect(` occurrences in this
    component today, this assertion holds trivially — recorded here rather
    than left to look like it caught something it didn't.
    """
    source = _source(CREATE_PERSON_POPOVER_PATH)
    effect_starts = [m.start() for m in re.finditer(r"\$effect\s*\(", source)]
    if not effect_starts:
        # No $effect at all in this component — the assertion is trivially
        # satisfied. Documented rather than silently passing on absence.
        return

    for start in effect_starts:
        brace_start = source.index("{", start)
        depth = 0
        end = None
        for i in range(brace_start, len(source)):
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        assert end is not None, "unbalanced braces while extracting $effect block"
        block = source[start:end]
        assert "initialSide" not in block, (
            f"found an $effect tracking `initialSide` — this would clobber a "
            f"deliberate mid-session radio choice. Block:\n{block}"
        )


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


LOCK_FLAG_NAME = "speakersLocked"


def _speakers_card_region(source: str) -> str:
    """Locate the Speakers card region by its heading comment through the
    close of its table/section, so pre-existing status comparisons elsewhere
    on the page (Status card, Danger Zone) cannot make a scoped assertion
    self-satisfying or self-invalidating."""
    start_match = re.search(r"Card 3: Speakers", source)
    assert start_match, "could not locate the Speakers card heading comment in the page source"
    end_match = re.search(r"Danger Zone", source[start_match.end():])
    assert end_match, "could not locate the end-of-Speakers-card boundary (Danger Zone) in the page source"
    return source[start_match.start() : start_match.end() + end_match.start()]


def _ts_action_body(source: str, action_name: str) -> str:
    """Extract the brace-balanced body of a SvelteKit form action property,
    e.g. `updateParticipantSide: async ({ ... }) => { ... }`."""
    match = re.search(rf"{re.escape(action_name)}\s*:\s*async\s*\([^)]*\)\s*=>\s*", source)
    assert match, f"could not find `{action_name}: async (...) => ...` action in source"
    brace_start = source.index("{", match.end())
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : i + 1]
    raise AssertionError(f"unbalanced braces while extracting action {action_name}")


def test_argument_page_derives_one_published_lock_flag() -> None:
    """
    STRUCTURAL-ONLY: proves a single named flag (`speakersLocked`) is
    declared, using the same `data.argument.status === 'published'` idiom
    the page already uses at its unpublish-button branch, and that the
    Speakers card region does not repeat that comparison inline a second
    time (it must reference the flag instead). Does not prove the flag is
    wired correctly at runtime.
    """
    source = _source(ARGUMENT_DETAIL_PATH)
    assert re.search(
        rf"(const|let)\s+{LOCK_FLAG_NAME}\s*=\s*data\.argument\.status\s*===\s*'published'\s*;",
        source,
    ), (
        f"expected a single named published-lock flag `{LOCK_FLAG_NAME}` derived "
        f"from `data.argument.status === 'published'`, matching the page's own "
        f"comparison idiom used at its unpublish-button branch"
    )

    region = _speakers_card_region(source)
    assert "data.argument.status === 'published'" not in region, (
        "the Speakers card region must consult the derived flag, not repeat "
        "the raw status comparison inline a second time"
    )


def test_speakers_card_controls_consult_the_published_lock() -> None:
    """
    STRUCTURAL-ONLY: proves the role select, descriptor input, and Save
    button each reference `speakersLocked` in a disabled position, and that
    the Save button's pre-existing unresolved-side and in-flight conditions
    survive (the lock is added to the existing gate, not substituted for
    it). Does not prove a control actually renders disabled in a browser —
    see the 48-10 false-green incident (28 green source-contract tests
    against a fully broken button) for why this cannot close the visual
    claim.
    """
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)

    select_match = re.search(r"<select\s+name=\"side\"[^>]*>", region, re.DOTALL)
    assert select_match, "could not find the role <select name=\"side\"> in the Speakers card"
    assert LOCK_FLAG_NAME in select_match.group(0), (
        f"the role select must reference `{LOCK_FLAG_NAME}` in a disabled "
        f"condition. Actual tag:\n{select_match.group(0)}"
    )

    descriptor_match = re.search(r"<input\s+type=\"text\"\s+name=\"descriptor\"[^/]*/>", region, re.DOTALL)
    assert descriptor_match, "could not find the descriptor <input name=\"descriptor\"> in the Speakers card"
    assert LOCK_FLAG_NAME in descriptor_match.group(0), (
        f"the descriptor input must reference `{LOCK_FLAG_NAME}` in a disabled "
        f"condition. Actual tag:\n{descriptor_match.group(0)}"
    )

    save_button_match = re.search(r"<button\s+type=\"submit\"\s+disabled=\{([^}]*)\}", region)
    assert save_button_match, "could not find the Save <button type=\"submit\" disabled={...}> in the Speakers card"
    disabled_expr = save_button_match.group(1)
    assert LOCK_FLAG_NAME in disabled_expr, (
        f"the Save button's disabled condition must include `{LOCK_FLAG_NAME}`. "
        f"Actual condition:\n{disabled_expr}"
    )
    assert "savingSpeakerId === speaker.participant_id" in disabled_expr, (
        "the Save button's pre-existing in-flight condition must survive"
    )
    assert "speakerSideById[speaker.participant_id] === 'UNKNOWN'" in disabled_expr, (
        "the Save button's pre-existing unresolved-side condition must survive"
    )


def test_speakers_card_explains_the_lock() -> None:
    """
    STRUCTURAL-ONLY: proves a reason line, conditioned on `speakersLocked`,
    exists in the Speakers card region and names publishing as the cause and
    unpublishing as the remedy. A disabled control with no explanation is
    the apolitical-constraint failure mode in miniature — the operator
    cannot tell a lock from a bug.
    """
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)

    match = re.search(rf"\{{#if\s+{LOCK_FLAG_NAME}\}}(.*?)\{{/if\}}", region, re.DOTALL)
    assert match, (
        f"expected a `{{#if {LOCK_FLAG_NAME}}}...{{/if}}` reason block in the "
        f"Speakers card region"
    )
    reason_text = match.group(1)
    assert "published" in reason_text.lower(), (
        f"the reason line must name publishing as the cause. Actual block:\n{reason_text}"
    )
    assert "unpublish" in reason_text.lower(), (
        f"the reason line must name unpublishing as the remedy. Actual block:\n{reason_text}"
    )


def test_participant_side_action_reports_a_published_rejection_accurately() -> None:
    """
    STRUCTURAL-ONLY: proves the `updateParticipantSide` server action reads
    the 422 body's `detail`, branches on a published-specific case, and
    returns copy naming unpublishing as the remedy rather than inviting a
    retry — while the generic retry copy remains reachable on every other
    failure. The current single generic message ("Could not save role. Try
    again.") invites a retry that can never succeed against a published
    argument.
    """
    source = _source(ARGUMENT_DETAIL_SERVER_PATH)
    body = _ts_action_body(source, "updateParticipantSide")

    assert "Could not save role. Try again." in body, (
        "the generic retry copy must still be reachable for non-published failures"
    )
    assert re.search(r"detail\.includes\(['\"]is published['\"]\)", body), (
        f"expected the action to branch on the published case by inspecting the "
        f"response body's `detail`. Actual action body:\n{body}"
    )
    assert "unpublish" in body.lower(), (
        f"the published-branch copy must name unpublishing as the remedy. "
        f"Actual action body:\n{body}"
    )
    published_copy_match = re.search(r"roleError:\s*'([^']*unpublish[^']*)'", body, re.IGNORECASE)
    assert published_copy_match, "could not find distinct published-rejection roleError copy"
    assert published_copy_match.group(1) != "Could not save role. Try again.", (
        "the published-rejection copy must be distinct from the generic retry copy"
    )
