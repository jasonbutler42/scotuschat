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
RESOLVE_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ResolveCard.svelte"
PARTICIPANT_SIDE_PATH = ROOT / "app" / "src" / "lib" / "participantSide.ts"

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
    # G-49-16 (2026-08-25): the declaration MUST be $derived-wrapped. It was a plain
    # `const` until an operator found the lock dead after an in-page publish — see
    # test_published_lock_flag_must_be_reactive below for the full reasoning. The
    # optional-$derived shape here keeps this test focused on "one named flag, page's
    # own comparison idiom"; reactivity is that test's job.
    assert re.search(
        rf"(const|let)\s+{LOCK_FLAG_NAME}\s*=\s*(?:\$derived\(\s*)?data\.argument\.status\s*===\s*'published'",
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

    # G-49-14 (2026-08-25): the row was split into five real <td>s, so each control
    # now also carries a `form="speaker-side-{id}"` association attribute AHEAD of its
    # other attributes. These locators match on attribute PRESENCE rather than a fixed
    # attribute ORDER — pinning order made the test fail on a markup change that left
    # every property it actually asserts intact.
    select_match = re.search(r"<select\s[^>]*name=\"side\"[^>]*>", region, re.DOTALL)
    assert select_match, "could not find the role <select name=\"side\"> in the Speakers card"
    assert LOCK_FLAG_NAME in select_match.group(0), (
        f"the role select must reference `{LOCK_FLAG_NAME}` in a disabled "
        f"condition. Actual tag:\n{select_match.group(0)}"
    )

    descriptor_match = re.search(r"<input\s[^>]*name=\"descriptor\"[^>]*/>", region, re.DOTALL)
    assert descriptor_match, "could not find the descriptor <input name=\"descriptor\"> in the Speakers card"
    assert LOCK_FLAG_NAME in descriptor_match.group(0), (
        f"the descriptor input must reference `{LOCK_FLAG_NAME}` in a disabled "
        f"condition. Actual tag:\n{descriptor_match.group(0)}"
    )

    save_button_match = re.search(r"<button\s[^>]*type=\"submit\"[^>]*disabled=\{([^}]*)\}", region)
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


def test_shared_module_exports_the_label_map_byte_identical_to_todays_advocate_labels() -> None:
    """The three advocate labels are operator-visible copy. The extraction
    (plan 49-10) must not silently reword them — Task 3 renders the
    Speakers card's advocate options from this map rather than from a
    second hardcoded list, so if the map ever drifted from today's strings
    the operator-visible copy would silently change with it."""
    source = _source(PARTICIPANT_SIDE_PATH)
    assert "SIDE_LABEL" in source, (
        "app/src/lib/participantSide.ts must export a SIDE_LABEL display map"
    )
    for label in ("Petitioner's Counsel", "Respondent's Counsel", "Amicus Curiae"):
        assert label in source, (
            f"SIDE_LABEL must carry the byte-identical advocate label {label!r} that "
            f"ResolveCard.svelte and the Speakers card render today"
        )


def test_shared_module_exports_the_specific_advocate_role_helper() -> None:
    """specificAdvocateRole is byte-equivalent to ResolveCard.svelte's own
    (pre-extraction) declaration — both cards import the same function
    rather than each declaring their own copy of the three-role check."""
    source = _source(PARTICIPANT_SIDE_PATH)
    assert "function specificAdvocateRole(" in source, (
        "app/src/lib/participantSide.ts must export specificAdvocateRole"
    )
    body = _plain_function_body(source, "specificAdvocateRole")
    for role in ("PETITIONER", "RESPONDENT", "AMICUS"):
        assert role in body, f"specificAdvocateRole must recognize {role!r}"


def test_shared_module_exports_a_boundary_crossing_predicate() -> None:
    """The one genuinely new export (planner_decisions): a pure predicate
    taking a previous bucket and a new side value and reporting whether the
    bucket changed, with the first-observation case (no previous bucket)
    reported as NOT a crossing — the rule clearPersonOnSideBucketChange
    already implements, so initial load/seeding is never mistaken for an
    operator-driven boundary crossing. Both cards will consume this."""
    source = _source(PARTICIPANT_SIDE_PATH)
    assert re.search(r"function\s+crossesSideBoundary\s*\(", source), (
        "app/src/lib/participantSide.ts must export a crossesSideBoundary(...) "
        "boundary-crossing predicate"
    )
    body = _plain_function_body(source, "crossesSideBoundary")
    assert "undefined" in body, (
        "the predicate must explicitly handle the no-previous-bucket case as NOT a crossing"
    )


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


def _speakers_script_region(source: str) -> str:
    """The script-level Speakers-card state (VALID_SIDES, the speakerSideById
    seed, sideConfirming, and the argument-id reset $effect) lives ABOVE the
    'Card 3: Speakers' markup comment _speakers_card_region scopes to — it is
    declared once in the <script> block, not per-row in the template. Scope
    assertions about that state to the whole <script> block instead."""
    match = re.search(r"<script[^>]*>(.*?)</script>", source, re.DOTALL)
    assert match, "could not find the <script> block in the page source"
    return match.group(1)


def test_speakers_row_has_no_per_class_branch() -> None:
    """STRUCTURAL-ONLY. CLAUDE.md's apolitical constraint made unfalsifiable-
    by-drift: with one row template there is no second branch that can
    diverge in affordance depth between bench and advocate."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)
    assert "speaker.is_bench" not in region, (
        "the Speakers card region must contain no reference to the row's stored bench "
        "flag — one row template must serve both bench and advocate rows"
    )


def test_speakers_side_control_offers_every_stored_value() -> None:
    """STRUCTURAL-ONLY. The unresolved placeholder text is pinned by 26-UAT
    Test 26, which 49-VERIFICATION.md human_verification item 3 still lists
    as never observed in a browser — rewording it would invalidate a check
    that has not yet been performed."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)
    select_match = re.search(r"<select\s[^>]*name=\"side\"[^>]*>(.*?)</select>", region, re.DOTALL)
    assert select_match, "could not find the side <select> in the Speakers card region"
    select_body = select_match.group(1)
    assert '<option value="UNKNOWN">Unresolved — choose a role</option>' in select_body, (
        "the unresolved sentinel's placeholder text must be byte-identical to today's"
    )
    assert '<option value="BENCH"' in select_body, (
        "the side control must offer the BENCH value — G-49-3's whole point"
    )
    for role in ("PETITIONER", "RESPONDENT", "AMICUS"):
        assert f'<option value="{role}"' in select_body, (
            f"the side control must still offer the specific advocate role {role!r}"
        )


def test_speakers_labels_come_from_the_shared_module() -> None:
    """STRUCTURAL-ONLY. Cites the open duplication todo
    (2026-08-12-speaker-popover-frontend-duplication-cleanup.md): the three
    advocate labels must be consumed from participantSide.ts's SIDE_LABEL
    map, not from a second hardcoded list on this page."""
    source = _source(ARGUMENT_DETAIL_PATH)
    assert re.search(r"from\s+['\"]\$lib/participantSide['\"]", source), (
        "the argument-detail page must import from '$lib/participantSide'"
    )
    import_match = re.search(r"import\s*\{([^}]*)\}\s*from\s*['\"]\$lib/participantSide['\"]", source)
    assert import_match, "could not find the named import from '$lib/participantSide'"
    assert "SIDE_LABEL" in import_match.group(1), (
        "the page must import SIDE_LABEL by name from the shared module"
    )

    region = _speakers_card_region(source)
    for hardcoded_label in ("Petitioner's Counsel", "Respondent's Counsel", "Amicus Curiae"):
        assert hardcoded_label not in region, (
            f"the Speakers card region must not hardcode the advocate label {hardcoded_label!r} — "
            f"it must render from SIDE_LABEL instead, so the two cards can never silently drift "
            f"in operator-visible copy"
        )
    assert "SIDE_LABEL" in region, (
        "the region must actually reference SIDE_LABEL to render its advocate option labels"
    )


def test_speakers_side_state_seeds_from_every_row() -> None:
    """Without this, a bench row would seed no side state at all and its
    control would render with no selection — this is a script-level
    (not per-row-markup) fact, so it is scoped to the whole <script> block
    rather than the markup region."""
    source = _source(ARGUMENT_DETAIL_PATH)
    script = _speakers_script_region(source)
    assert "VALID_SIDES" in script, "the page must still declare a VALID_SIDES set"
    valid_sides_match = re.search(r"VALID_SIDES\s*=\s*new Set\(\[([^\]]*)\]\)", script)
    assert valid_sides_match, "could not find the VALID_SIDES declaration"
    assert "'BENCH'" in valid_sides_match.group(1), (
        "VALID_SIDES must admit the BENCH value now that the control offers it"
    )

    seed_match = re.search(
        r"speakerSideById\s*=\s*\$state[^(]*\((.*?)\n\t\);", script, re.DOTALL
    )
    assert seed_match, "could not find the speakerSideById seed initializer"
    seed_body = seed_match.group(1)
    assert ".filter((s) => !s.is_bench)" not in seed_body, (
        "the seed must no longer filter out bench rows — every speaker row must seed its "
        "own side state, or a bench row's control would render with no selection"
    )


def test_boundary_crossing_requires_a_second_click() -> None:
    """STRUCTURAL-ONLY. Names the purpose being ported: the Resolve card's
    side gate (needsSideGate/confirmSide) forces an explicit decision before
    a consequential action; here the consequential action is the immediate
    write, so the same PURPOSE is served with a mechanism appropriate to a
    one-form-per-row POST rather than a copy of the Resolve card's own
    batch-form mechanism."""
    source = _source(ARGUMENT_DETAIL_PATH)
    script = _speakers_script_region(source)
    assert "sideConfirming" in script, (
        "the page must declare per-participant confirm state (sideConfirming)"
    )

    region = _speakers_card_region(source)
    assert re.search(r"crossesSideBoundary\s*\(\s*sideBucket\s*\(\s*speaker\.side\s*\)", region), (
        "the boundary check must be computed via the shared crossesSideBoundary predicate "
        "against the row's committed (stored) side, not an inline re-derivation"
    )
    assert "sideConfirming[speaker.participant_id]" in region, (
        "the confirm branch must be keyed per participant_id"
    )

    confirming_match = re.search(
        r"\{#if\s+sideConfirming\[speaker\.participant_id\]\}(.*?)\{:else\}(.*?)\{/if\}",
        region,
        re.DOTALL,
    )
    assert confirming_match, "could not find the sideConfirming if/else branch"
    confirming_branch, non_confirming_branch = confirming_match.groups()
    assert re.search(r'type="submit"', confirming_branch), (
        "the confirming branch must render a submit button"
    )
    assert re.search(r'type="button"[^>]*>\s*Cancel', confirming_branch, re.DOTALL) or "Cancel" in confirming_branch, (
        "the confirming branch must render a Cancel button"
    )
    assert 'type="button"' in non_confirming_branch, (
        "the non-confirming branch's button must NOT submit — it only sets the confirm flag"
    )
    assert 'type="submit"' not in non_confirming_branch, (
        "the non-confirming (not-yet-confirmed) branch must never itself submit the form"
    )

    assert "sideConfirming = {}" in script, (
        "the confirm state must be reset by the same argument-id $effect the Danger Zone "
        "uses (Pitfall 7) — otherwise a soft navigation to a different argument would carry "
        "stale confirm state across arguments"
    )


def test_bench_companion_distinguishes_three_states() -> None:
    """STRUCTURAL-ONLY. This is the one-way trap being closed: before this
    task, a bench row with NO person rendered a bare em-dash with no warning
    and no link — closed here by keying the third branch on person_id being
    absent rather than on missing_tenure, which the pre-existing bench-only
    render conflated."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)

    assert "speaker.bench_role" in region, "a tenure-derived role branch must still exist"
    assert "Missing tenure" in region, "the missing-tenure warning copy must still exist"
    assert "speaker.person_edit_href" in region, "the person-edit link must still be rendered"
    assert re.search(r"No person linked", region), (
        "a distinct no-person-linked state must exist, with copy that does not claim the "
        "tenure is missing (the real problem is that no person is linked at all)"
    )

    companion_match = re.search(
        r"\{#if\s+speaker\.person_id\s*==\s*null\}(.*?)\{:else if\s+speaker\.missing_tenure\}(.*?)\{:else\}(.*?)\{/if\}",
        region,
        re.DOTALL,
    )
    assert companion_match, (
        "the bench companion must be an if/else-if/else chain keyed FIRST on "
        "speaker.person_id being null (not on missing_tenure) — the third state must not "
        "be reachable only as a side effect of the missing_tenure check"
    )
    no_person_branch, missing_tenure_branch, role_branch = companion_match.groups()
    assert "No person linked" in no_person_branch
    assert "person_edit_href" not in no_person_branch, (
        "no Edit-person link on the no-person branch — there is no person to edit"
    )
    assert "Missing tenure" in missing_tenure_branch
    assert "person_edit_href" in missing_tenure_branch
    assert "bench_role" in role_branch


def test_descriptor_input_is_disabled_not_removed_on_bench() -> None:
    """STRUCTURAL-ONLY. Unmounting the descriptor input on a Bench selection
    would destroy a typed-but-unsaved value on a toggle — the defect
    ResolveCard.svelte's lastDescriptorValue (:155-165) exists to prevent,
    avoided here by construction (the input stays mounted) rather than by a
    second remembering mechanism."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)

    descriptor_match = re.search(r"<input\s[^>]*name=\"descriptor\"[^>]*/>", region, re.DOTALL)
    assert descriptor_match, "could not find the descriptor <input name=\"descriptor\"> in the region"
    descriptor_tag = descriptor_match.group(0)
    assert "'BENCH'" in descriptor_tag, (
        "the descriptor input's disabled position must consult the selected side"
    )

    preceding_window = region[max(0, descriptor_match.start() - 200) : descriptor_match.start()]
    assert not re.search(r"\{#if[^}]*\}\s*$", preceding_window.rstrip() + " "), (
        "the descriptor input must not be wrapped in a conditional that would unmount it "
        "on a Bench selection"
    )


def test_action_omits_descriptor_when_the_committed_side_was_bench() -> None:
    """RESOLVE-13 preserves a bench row's stored descriptor and the read
    path reports it null, so the page cannot see it; sending an empty
    string on the way back out would clobber exactly the value RESOLVE-13
    protected. This test is STRUCTURAL-ONLY for the markup half (the hidden
    input) and the action-body half; Task 2's
    test_bench_round_trip_does_not_lose_the_descriptor is what actually
    proves the outcome live."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)
    assert re.search(r'<input\s+type="hidden"\s+name="committed_side"\s+value=\{speaker\.side\}', region), (
        "the row must carry a hidden input naming the committed (stored) side"
    )

    server_source = _source(ARGUMENT_DETAIL_SERVER_PATH)
    body = _ts_action_body(server_source, "updateParticipantSide")
    assert "committed_side" in body, "the action must read the committed_side field"
    assert re.search(r"committedSide\s*!==\s*['\"]BENCH['\"]", body), (
        "the action must gate descriptor inclusion on the committed side NOT being BENCH"
    )
    assert re.search(r"formData\.has\(\s*['\"]descriptor['\"]\s*\)", body), (
        "the action must check whether the descriptor field was actually submitted before "
        "including it — a disabled input is omitted from FormData by the browser itself"
    )


def test_published_lock_and_unresolved_gate_both_survive_the_convergence() -> None:
    """A convergence that quietly dropped either the published lock (49-09)
    or the unresolved-side Save gate would un-verify shipped work."""
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)
    assert region.count(LOCK_FLAG_NAME) >= 3, (
        "the published lock flag must still gate the select, the descriptor input, and the "
        "action controls — a convergence must not quietly drop it"
    )
    assert "speakerSideById[speaker.participant_id] === 'UNKNOWN'" in region, (
        "the unresolved-side Save gate must still hold"
    )


def test_every_speakers_row_control_is_associated_with_its_own_row_form() -> None:
    """
    STRUCTURAL-ONLY. G-49-14 (operator, 2026-08-25) split the speaker row from one
    `<td colspan="3">` into five real `<td>`s so the row fills the five columns its
    header declares. `<form>` is not a permitted child of `<tr>`, so the form is
    declared once in the name cell and every control in the sibling cells associates
    with it by id via the HTML5 `form=` attribute.

    That association is now load-bearing and SILENT when broken: drop the `form=`
    attribute and the control simply stops being submitted — no error, no visual
    change, the row just quietly saves less than it should. This test exists because
    that failure mode is invisible to every other assertion in this module.

    Does NOT prove a browser actually submits the row (see the 48-10 false-green
    incident); it proves the association attribute is present on each control that
    must carry it, and that the form id is per-participant rather than shared.
    """
    source = _source(ARGUMENT_DETAIL_PATH)
    region = _speakers_card_region(source)

    form_ref = 'form="speaker-side-{speaker.participant_id}"'

    form_decl = re.search(r'<form\s[^>]*id="speaker-side-\{speaker\.participant_id\}"', region, re.DOTALL)
    assert form_decl, (
        "the per-row form must be declared with a participant-scoped id "
        '(id="speaker-side-{speaker.participant_id}"). A shared or static id would '
        "make every row submit the same participant's data."
    )

    select_match = re.search(r"<select\s[^>]*name=\"side\"[^>]*>", region, re.DOTALL)
    assert select_match and form_ref in select_match.group(0), (
        "the side <select> sits in a different <td> from its <form> and must carry "
        f"{form_ref} or it will not be submitted"
    )

    descriptor_match = re.search(r"<input\s[^>]*name=\"descriptor\"[^>]*/>", region, re.DOTALL)
    assert descriptor_match and form_ref in descriptor_match.group(0), (
        "the descriptor <input> sits in a different <td> from its <form> and must "
        f"carry {form_ref} or a typed descriptor will be silently dropped on save"
    )

    submit_buttons = re.findall(r"<button\s[^>]*type=\"submit\"[^>]*>", region, re.DOTALL)
    assert submit_buttons, "expected at least one submit button in the Speakers card region"
    for button in submit_buttons:
        assert form_ref in button, (
            "every submit button in the Speakers card sits in the Action <td>, outside "
            f"its <form>, and must carry {form_ref} to submit anything. Offending tag:\n{button}"
        )

    # The hidden inputs stay INSIDE the form element itself, so they need no attribute.
    assert 'name="participant_id"' in region and 'name="committed_side"' in region, (
        "both hidden inputs must survive the split — committed_side is RESOLVE-13's "
        "round-trip guard against clobbering a preserved bench descriptor"
    )

def test_published_lock_flag_must_be_reactive_not_const_captured() -> None:
    """
    G-49-16 (operator, 2026-08-25). The published lock MUST be `$derived`, never a plain
    `const` over `data`.

    `data` is a prop. In Svelte 5 runes mode a plain `const` evaluates ONCE at component
    initialisation and never recomputes. Publish and unpublish do NOT remount this
    component — both POST and invalidate, updating `data` in place — so a const-captured
    flag stays frozen at whatever the status was when the page first loaded. In the field
    that meant publishing with the page open left the entire card editable (the backend
    refused every write, so nothing corrupted, but the operator was offered controls that
    could not work), and unpublishing left it locked with no way back short of a reload.

    Why this test has to exist as its OWN assertion: every other source-contract test in
    this module asserts the MARKUP says `disabled={speakersLocked}` — and the markup was
    correct the entire time the bug was live. It was the FLAG that was dead. A grep cannot
    tell a live flag from a stale one, so the one greppable half of the invariant — the
    declaration must be $derived — is pinned here explicitly. Six plans verified this lock
    on a FRESH page load, which is the single case a const-captured flag gets right.

    Does NOT prove reactivity at runtime (that needs a mounted-component or browser test);
    it forecloses the specific regression that actually happened.
    """
    source = _source(ARGUMENT_DETAIL_PATH)

    declaration = re.search(
        rf"(const|let)\s+{LOCK_FLAG_NAME}\s*=\s*([^;]+);",
        source,
    )
    assert declaration, f"could not find the `{LOCK_FLAG_NAME}` declaration"

    keyword, initialiser = declaration.group(1), declaration.group(2)
    assert "$derived" in initialiser, (
        f"`{LOCK_FLAG_NAME}` must be declared with $derived so it recomputes when `data` "
        f"changes on publish/unpublish invalidation. A plain capture goes stale and the "
        f"lock silently stops tracking the argument's real status.\n"
        f"Actual: {keyword} {LOCK_FLAG_NAME} = {initialiser.strip()};"
    )
    assert keyword == "let", (
        f"a $derived declaration must use `let`, not `const` — Svelte reassigns it on "
        f"recompute. Actual keyword: {keyword!r}"
    )
