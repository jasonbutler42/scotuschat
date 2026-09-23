---
phase: 49-review-model
plan: 09
subsystem: api
tags: [fastapi, sveltekit, svelte5, admin, authority-gate, review-model]

requires:
  - phase: 49-review-model plan 04
    provides: "The single authority-gated writer (apply_participant_value_change) that every ArgumentParticipant value write must route through (D-31/D-31a) — this plan's guard sits in front of it, not beside it."
provides:
  - "A published lock on api/services/admin_arguments.py::update_participant_side, mirroring update_resolve_row_for_job's existing guard predicate, error shape, and folded-todo citation — D-35's FIRST half"
  - "The lock made visible on the Speakers card (role select, descriptor input, Save all disabled under a single speakersLocked flag, with a reason line), plus honest published-rejection copy in the updateParticipantSide SvelteKit action"
  - "WR-01 closed: CreatePersonPopover's Bench/Advocate radio resyncs to the row's current side on the OPEN transition, not only on close"
  - "The full D-35 published-write inventory in deferred-items.md, with the one NEW question (does the lock extend to the Case/Argument-Details cards?) stated for the operator"
affects: [49-10, phase-50]

actuals:
  tokens: 11200
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Published-status guard placed BEFORE the authority-gate call, after pure-input validation guards that must remain DB-free — ordering matters for both correctness (no discrepancy residue on a refused write) and for a pre-existing sentinel-session unit test that requires the BENCH/unresolved-side checks to raise before any db.execute()"
    - "A single named boolean flag (speakersLocked) derived once from data.argument.status, consulted by every control in a card, instead of repeating the raw status comparison at each control"

key-files:
  created:
    - api/tests/test_phase49_participant_side_contract.py
  modified:
    - app/src/lib/components/CreatePersonPopover.svelte
    - api/services/admin_arguments.py
    - api/routers/admin.py
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - .planning/phases/49-review-model/deferred-items.md

key-decisions:
  - "Published guard placed AFTER the existing BENCH/unresolved-side input-validation raises, not literally first in the function body. test_admin_arguments_service.py::test_update_participant_side_rejects_unresolved_side calls the function with a sentinel `None` session specifically to prove those two guards never touch the database — inserting the Argument-status guard ahead of them would have broken that pre-existing, untouched test. The published guard still runs before the participant SELECT and before either apply_participant_value_change call, which is the property the plan's Task 2 assertions and D-16 reasoning actually require."
  - "test_update_participant_side_still_accepts_unpublished_and_draft and test_popover_does_not_resync_side_on_every_prop_change were GREEN from the start of the red phase, not red-then-green. Both are documented explicitly below as negative-space/continuity checks rather than presented as a false red-then-green narrative, matching 49-08's precedent for the same situation."
  - "Chose the predicate `detail.includes('is published')` (matching the exact phrase in the new ValueError string, `f\"Argument {argument.id} is published (current status: ...\"`) as the SvelteKit action's branch condition, rather than a bespoke error code, to avoid adding a new response contract for a single 422 case — the router already maps every ValueError to a 422 with str(exc) as detail."

patterns-established:
  - "Card-level lock flags (one named boolean, declared once, consulted everywhere) rather than repeating a raw status comparison at each disabled control — reduces the chance of one control silently drifting out of sync with the others."

requirements-completed: [REVIEW-01, REVIEW-04]

coverage:
  - id: D1
    description: "WR-01: CreatePersonPopover's Bench/Advocate radio resyncs to the row's current side on the popover's OPEN transition, not only on close, without clobbering a mid-session radio choice via a reactive effect"
    requirement: REVIEW-04
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_popover_resyncs_side_on_open_not_only_on_close"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_popover_does_not_resync_side_on_every_prop_change"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py (all five pre-existing popover assertions, unmodified)"
        status: pass
    human_judgment: true
    rationale: "Source-contract tests prove the open-transition branch and the absence of a prop-tracking $effect exist in source text only. The actual browser walkthrough (toggle row, open popover, verify pre-selection; keep popover open, change radio, toggle row again, verify choice survives) could not be run in this sandbox — denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET, unchanged all phase. Recorded NOT OBSERVED in 49-VERIFICATION.md, not as a pass."
  - id: D2
    description: "update_participant_side refuses a write against a PUBLISHED argument, proven by non-persistence (side/descriptor/review_state unchanged, no open value_discrepancy row), while UNPUBLISHED and DRAFT arguments remain fully writable; the guard runs before the authority gate; both participant-value writers share one predicate and folded-todo citation"
    requirement: REVIEW-01
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_update_participant_side_refuses_a_published_argument"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_update_participant_side_still_accepts_unpublished_and_draft"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_published_guard_precedes_the_authority_gate"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_both_participant_writers_share_one_published_predicate"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_update_participant_side_rejects_unresolved_side (pre-existing, confirmed unaffected)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Speakers card visibly discloses the lock (role select, descriptor input, Save all disabled under speakersLocked, with a reason line naming publish/unpublish), identically for bench and advocate rows; the updateParticipantSide action returns copy naming unpublishing as the remedy instead of the generic retry message on a published rejection"
    requirement: REVIEW-01
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_argument_page_derives_one_published_lock_flag"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_speakers_card_controls_consult_the_published_lock"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_speakers_card_explains_the_lock"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py#test_participant_side_action_reports_a_published_rejection_accurately"
        status: pass
    human_judgment: true
    rationale: "Every assertion here is STRUCTURAL-ONLY per its own docstring — it proves a string/attribute exists in the .svelte or .server.ts source, never that a browser actually renders the controls disabled or that the reason line is legible. This project has a documented false-green incident (plan 48-10: 28 green source-contract tests against a fully broken button) that is the explicit reason this cannot self-close. The browser human-check could not be run in this sandbox for the same credential reason as D1 and is recorded NOT OBSERVED."

duration: 1h 5m
completed: 2026-08-24
status: complete
---

# Phase 49 Plan 09: Published Lock + WR-01 Summary

**Locks `update_participant_side` on PUBLISHED arguments (mirroring the resolve writer's existing guard), surfaces that lock on the Speakers card with honest rejection copy, fixes the create-person popover's open-time side resync, and inventories every remaining write path that can still mutate published argument data — the FIRST half of D-35, landed ahead of 49-10's convergence work.**

## Performance

- **Duration:** ~1h 5m
- **Tasks:** 3/3 completed
- **Files modified:** 6 (1 created: the new contract module)
- **Full suite:** 1104 passed, 0 failed (baseline 1094 — a clean +10, exactly the 10 new assertions in this plan's new module)

## Accomplishments

- **WR-01 closed.** `CreatePersonPopover.svelte`'s `onOpenChange` now reassigns `side = initialSide` on the OPEN transition, alongside the pre-existing `resetForm()` call on CLOSE. A radio choice made while the popover is open is never clobbered — the fix is a one-shot branch, not a reactive effect tracking the prop.
- **The published lock on `update_participant_side`.** Loads the owning `Argument` and raises `ValueError` when `status == ArgumentStatusEnum.PUBLISHED`, using the same error shape (argument id, current status, folded-todo citation) as the sibling `update_resolve_row_for_job`. The guard runs before the participant SELECT and before either `apply_participant_value_change` call, so a refused write leaves no `value_discrepancy` row and no `review_state` advance. UNPUBLISHED and DRAFT arguments remain fully editable — proved live, not merely asserted.
- **The lock made visible.** A single `speakersLocked` flag (`data.argument.status === 'published'`) disables the Speakers card's role select, descriptor input, and Save button, with a reason line naming publish as the cause and unpublish as the remedy — applied identically to bench and advocate rows. The `updateParticipantSide` SvelteKit action now returns `"...Unpublish it first..."` on a published rejection instead of the generic `"Try again."`, without echoing the raw server detail.
- **The write-path inventory.** `deferred-items.md` now carries a full table of every admin write path that can reach an `Argument`/`Case`/`ArgumentParticipant`/`Person`, with an explicit disposition for each, plus the one NEW question for the operator: does D-35 extend to the Case/Argument-Details cards on the same page?

## Task Commits

1. **Task 1: WR-01 — popover resyncs side on open, not only on close** — `f824dbe5f` (fix)
2. **Task 2: Published lock on `update_participant_side`** — `b64fa06fb` (fix)
3. **Task 3: Lock visible on the Speakers card + write-path inventory** — `b00ea59c3` (feat)

**Plan metadata:** (this commit, made by the orchestrator after this SUMMARY)

## Files Created/Modified

- `api/tests/test_phase49_participant_side_contract.py` — new contract module (created in Task 1 per plan instruction); 10 assertions spanning WR-01, the published lock, and the Speakers-card/action visibility, plus local `_source`/`_plain_function_body`/`_service_function_source_lines`/`_ts_action_body` helpers (deliberately not imported from `test_phase49_cleanup_contract.py` or `test_published_gate.py`)
- `app/src/lib/components/CreatePersonPopover.svelte` — `onOpenChange` now branches on the open transition to resync `side` from `initialSide`
- `api/services/admin_arguments.py` — `update_participant_side` gains the published-status guard (after the pre-existing BENCH/unresolved-side input checks, before the participant SELECT and both authority-gate calls) plus an expanded docstring
- `api/routers/admin.py` — participant-PATCH endpoint docstring documents the new 422 case; resolve-row endpoint docstring's two stale statements (pre-widening candidate-only rule; pre-RESOLVE-13 "descriptor forced to null" claim) corrected to match current behavior
- `app/src/routes/admin/arguments/[id]/+page.svelte` — new `speakersLocked` flag; role select, descriptor input, and Save button each gain it in their disabled condition (existing conditions preserved); a card-level reason line renders under the flag
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — `updateParticipantSide` action reads the 422 body's `detail` and returns distinct copy on a published rejection; generic copy preserved for every other failure
- `.planning/phases/49-review-model/deferred-items.md` — new section: the full D-35 published-write inventory and the one NEW question for the operator

## Decisions Made

- **Guard ordering: published check AFTER the pure-input BENCH/unresolved-side raises, not literally first.** The plan's Task 2 text said "insert the guard as the FIRST thing the function does after entry." A pre-existing test (`test_admin_arguments_service.py::test_update_participant_side_rejects_unresolved_side`) calls `update_participant_side` with a sentinel `None` session specifically to prove the BENCH and unresolved-side guards raise before touching the database at all. Placing the Argument-status guard ahead of those two would have made the function call `db.execute()` before reaching them, breaking that untouched pre-existing test. Verified by running the guard-ordering assertion (`test_published_guard_precedes_the_authority_gate`, which only requires the published check precede the first `apply_participant_value_change` call) — it still passes with this ordering, and it is the ordering the plan's own D-16 reasoning actually needs (no discrepancy residue on a refused write). Discovered this during the RED-phase-confirmed-green loop: the guard was first written literally first, which broke the sentinel-session test; reordered and reverified.
- **`detail.includes('is published')` as the branch predicate in the SvelteKit action**, keyed off the literal phrase in the new `ValueError` string, rather than inventing a machine-readable error code. The router already maps every `ValueError` to a 422 with `str(exc)` as `detail`; adding a new response contract for one case would be a larger change than the plan's frontier warranted.
- **Two assertions were GREEN from the start of the RED phase** — documented explicitly rather than presented as red-then-green (see below).

## Deviations from Plan

None beyond the guard-ordering adjustment described above, which is a correctness fix required to keep an untouched pre-existing test passing (Rule 1 — auto-fixed bug in the plan's literal "first thing" instruction, not a scope change) and is fully covered by the plan's own executable guard-ordering assertion.

## RED-Phase Evidence

Every assertion below was authored first, run, and confirmed to fail before its corresponding source edit. Full captured output is in the scratchpad at `/tmp/claude-1000/-home-jason-scotuschat-project/f1b6f4a8-478c-4569-a8ac-b9162bcb219c/scratchpad/red_phase_full.txt` (Task 3's four assertions and Tasks 1/2's source-based assertions); the two live-DB assertions requiring an honest re-run are noted separately below.

**Task 1 — WR-01:**

- `test_popover_resyncs_side_on_open_not_only_on_close` — RED:
  ```
  AssertionError: onOpenChange must reassign `side` from `initialSide` on the OPEN transition (WR-01). Actual handler body:

  		if (!next) resetForm();

  assert None
  ```
- `test_popover_does_not_resync_side_on_every_prop_change` — **GREEN from the start.** There is no `$effect(` in `CreatePersonPopover.svelte` today (the component uses only `$state`), so the "no effect tracks the prop" assertion is trivially satisfied both before and after the fix. This is a negative-space continuity check, not a red-then-green gate — documented here explicitly per the non-negotiable instruction, matching 49-08's precedent for the same situation (its `test_no_truncation_or_media_query_introduced_on_the_review_page` and `test_dashboard_grid_uses_no_media_query_and_no_class_attribute`).

**Task 2 — the published lock:**

- `test_update_participant_side_refuses_a_published_argument` — the FIRST attempt to capture this RED hit a bug in my own test (a nonexistent `ReviewState.PIPELINE_RESOLVED` enum member), so that failure message (`AttributeError`) was not a genuine proof the guard was absent. After fixing the enum reference (`ReviewState.UNREVIEWED`), I re-ran RED honestly by temporarily reverting the guard implementation (`git stash` on `api/services/admin_arguments.py` alone) and captured the real failure:
  ```
  Failed: DID NOT RAISE ValueError
  ```
  Then restored the guard (`git stash pop`) and reconfirmed the assertion passes. This is the honest RED for this assertion; the earlier `AttributeError` capture is disclosed here rather than silently discarded.
- `test_update_participant_side_still_accepts_unpublished_and_draft` — **GREEN from the start.** Before the guard existed, a write against an UNPUBLISHED or DRAFT argument already succeeded (there was no guard of any kind), so this assertion — which exists to prove the guard's predicate doesn't over-narrow — passed both before and after the fix. Documented explicitly as a negative-space/continuity check rather than a red-then-green gate, per the non-negotiable instruction and matching the plan's own anticipation elsewhere in this project (49-08 precedent).
- `test_published_guard_precedes_the_authority_gate` — RED:
  ```
  AssertionError: update_participant_side() must compare status to ArgumentStatusEnum.PUBLISHED. Actual body:
  async def update_participant_side(
      ...
  [full pre-fix function body, no ArgumentStatusEnum.PUBLISHED anywhere]
  assert None is not None
  ```
- `test_both_participant_writers_share_one_published_predicate` — RED:
  ```
  AssertionError: update_participant_side() must compare status to ArgumentStatusEnum.PUBLISHED. Actual body:
  async def update_participant_side(
      ...
  [full pre-fix function body]
  ```

**Task 3 — visibility + inventory (all four confirmed RED together, `8 failed, 2 passed in 13.70s` — the 2 passes were the two Task 1/2 green-from-start cases above):**

- `test_argument_page_derives_one_published_lock_flag` — RED:
  ```
  AssertionError: expected a single named published-lock flag `speakersLocked` derived from `data.argument.status === 'published'`, matching the page's own comparison idiom used at its unpublish-button branch
  assert None
  ```
- `test_speakers_card_controls_consult_the_published_lock` — RED:
  ```
  AssertionError: the role select must reference `speakersLocked` in a disabled condition. Actual tag:
  <select
  	name="side"
  	bind:value={speakerSideById[speaker.participant_id]}
  	...
  >
  assert 'speakersLocked' in '<select\n...(no disabled attribute at all)...>'
  ```
- `test_speakers_card_explains_the_lock` — RED:
  ```
  AssertionError: expected a `{#if speakersLocked}...{/if}` reason block in the Speakers card region
  assert None
  ```
- `test_participant_side_action_reports_a_published_rejection_accurately` — RED:
  ```
  AssertionError: expected the action to branch on the published case by inspecting the response body's `detail`. Actual action body:
  {
  	const formData = await request.formData();
  	...
  	if (!res.ok) {
  		return fail(422, { roleError: 'Could not save role. Try again.' });
  	}
  	throw redirect(303, '/admin/arguments/' + params.id);
  }
  assert None
  ```

Note on the initial (superseded) attempt: my first pass at Task 3's four assertions was too weak — it checked for the mere presence of the words "disabled", "published", and "unpublish" anywhere in a large window, which were already true elsewhere on the page (other cards' status branches, the Danger Zone) and passed on the very first run against unmodified source, before any implementation. I recognized this was not gating anything, rewrote all four to target the specific `speakersLocked` flag name and its exact wiring points, reran, and confirmed all four then failed for the right reason (the flag and its wiring genuinely did not exist yet). The RED messages quoted above are from that corrected version.

## Pre-existing Tests Confirmed Unaffected

Per the plan's requirement, the three pre-existing live `update_participant_side` tests in `api/tests/test_admin_arguments_service.py` were read and confirmed to seed `status=ArgumentStatusEnum.DRAFT`:
- `test_update_participant_side_persists_descriptor_for_advocate`
- `test_update_participant_side_second_operator_edit_persists`
- `test_update_participant_side_rejects_unresolved_side` (seeds no argument at all — uses a sentinel session; see the guard-ordering decision above)

The route-level test `test_admin_arguments_routes.py::test_update_participant_route_persists_descriptor_for_advocate` was also confirmed to seed `ArgumentStatusEnum.DRAFT`. None of the four is invalidated by this plan's guard. All four passed in the full-suite run below.

## Human-Checks: Observed vs Not Observed

Both `<human-check>` items in this plan's tasks were **NOT OBSERVED**. This sandbox is denied `.env` read access for `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SESSION_SECRET`, unchanged for the entire duration of Phase 49 (consistent with 49-EVIDENCE.md §9 item 4 and every other Phase 49 plan's human-check disposition). No admin-authenticated browser session could be established, so:

- **Task 1's human-check** (toggle a row's side with the popover closed, then open; deliberately choose a radio while the popover is open and confirm an underlying row-side change does not clobber it) — NOT OBSERVED. `49-VERIFICATION.md` `human_verification` item 1 stays open with this reason; it is NOT ticked on the strength of the structural assertions above, per the plan's own explicit instruction.
- **Task 3's human-check** (visually confirm the Speakers card's disabled controls and reason line on a published argument, unchanged behavior on DRAFT/UNPUBLISHED, and the operator copy on an actual published-rejection round-trip) — NOT OBSERVED, same reason.

**Structural vs behavioural closure are recorded as two separate claims throughout this SUMMARY and in the `coverage:` block above — no `.svelte`/`.server.ts` source-text assertion is presented as proof of runtime behavior.**

## Issues Encountered

None beyond the guard-ordering adjustment (documented above under Decisions Made) and the two RED-phase test-authoring corrections (the `ReviewState` enum typo, corrected before capturing an honest RED for that assertion; and the initial too-weak Task 3 assertions, corrected before any source implementation began).

## Scope Boundary Honored

Per the plan's prohibitions: no second write path to `argument_participants` was introduced (`grep -c 'ArgumentStatusEnum.PUBLISHED' api/services/admin_arguments.py` → 9; `grep -v '^\s*<!--' ... | grep -c 'name="side"'` → 1, unchanged); the `side == SideEnum.BENCH` raise was not touched (49-10's territory); `update_argument`/`update_argument_metadata` were not touched (the NEW question recorded, not silently resolved); `app/src/routes/admin/+page.svelte`, `app/src/routes/admin/review/+page.svelte`, and `api/tests/test_phase49_review_ui_contract.py` (49-08's files) were not touched; `api/tests/test_phase49_cleanup_contract.py` was not edited and its five pre-existing popover assertions still pass unmodified. No Alembic migration was written or needed — the guard reads an existing column.

## Verification

- `./.venv/bin/python -m pytest api/tests/test_phase49_participant_side_contract.py -q` → 10 passed
- `./.venv/bin/python -m pytest api/tests/test_published_gate.py api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_admin_jobs_phase25.py api/tests/test_authority_matrix.py -q` → 238 passed
- `./.venv/bin/python -m pytest api/tests -q` → **1104 passed, 0 failed** (baseline: 1094 passed, independently re-run after 49-08 landed — this plan's diff is a clean +10, exactly the size of the new module, no regressions)
- `npm --prefix app run check` → 0 errors, 38 warnings (all pre-existing `state_referenced_locally` / a11y warnings already present in the codebase before this plan; none newly introduced by `speakersLocked`, a plain `const`, or any other change here)
- `python3 -m compileall -q pipeline api scripts tests alembic` → clean
- `git diff --stat` (across this plan's three commits) lists exactly this plan's `files_modified` — no file from 49-08's set appears

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

This plan closes the FIRST half of D-35 (the published lock) and WR-01. **It does NOT close G-49-3** — `gap_ids` is deliberately empty in this plan's frontmatter so `/gsd-verify-work`'s reconciliation attributes G-49-3 entirely to plan 49-10, which implements D-35's second half (the converged side/pool control) and retires `T-15-02-BENCH`. Do not treat this plan's published lock as a substitute for 49-10's convergence work — they are two independent halves of the same operator rule, and this plan deliberately does not pull any of 49-10's territory forward (the BENCH raise, `resolve_participant_review`'s scope, the shared side/pool module, or the converged row template all remain untouched).

The one NEW question recorded in `deferred-items.md` (does D-35 extend to the Case/Argument-Details cards on `/admin/arguments/{id}`, reversing their "readonly is always false here" comment?) is open and awaiting the operator — it is a candidate for its own small follow-up plan regardless of which way it resolves.

---
*Phase: 49-review-model*
*Completed: 2026-08-24*

## Self-Check: PASSED

All files listed in `files_modified` (plus the new SUMMARY itself) verified present on disk; all three task commit hashes (`f824dbe5f`, `b64fa06fb`, `b00ea59c3`) verified present in `git log --oneline --all`.
