---
phase: 49-review-model
plan: 10
subsystem: ui
tags: [svelte, sveltekit, fastapi, sqlalchemy, pydantic, admin-editing]

requires:
  - phase: 49-review-model (plan 09)
    provides: "The published lock on update_participant_side (D-35's first half) and the Speakers-card lock-notice/copy this plan builds on"
provides:
  - "app/src/lib/participantSide.ts — the single source of truth for the bench/advocate bucket rule, the operator-visible role labels, and the boundary-crossing predicate, imported by both ResolveCard.svelte and the argument-detail Speakers card"
  - "A converged Speakers card reaching all five stored side values (BENCH + 3 advocate roles + unresolved) on a non-published argument, gated by a two-step boundary-crossing confirm"
  - "update_participant_side accepting BENCH under RESOLVE-13's descriptor-preservation rule; T-15-02-BENCH retired as satisfied (not weakened) by D-35"
  - "G-49-3 closed; D-35 recorded in 49-CONTEXT.md as the second (final) half of the operator's convergence decision"
affects: [49-11]

actuals:
  tokens: 24515
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Shared $lib/*.ts module consumed by both a component and a route (matching docketValues.ts/personNames.ts precedent) for cross-surface pure logic extraction"
    - "Purpose-port instead of mechanism-copy: a UI safety gate (confirm-before-consequential-action) reimplemented per-surface in the idiom that surface already has (per-row POST vs. batch form), rather than sharing the gate's stateful mechanism"
    - "Read-path field re-purposed for a client-selection-driven render (bench companion keyed on speakerSideById, not stored is_bench) instead of adding a new preview endpoint"

key-files:
  created:
    - app/src/lib/participantSide.ts
  modified:
    - app/src/lib/components/ResolveCard.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/schemas/admin_arguments.py
    - api/routers/admin.py
    - api/tests/test_phase44_resolve_table_contract.py
    - api/tests/test_phase49_participant_side_contract.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
    - api/tests/test_admin_jobs_phase25.py
    - .planning/phases/49-review-model/49-UAT.md
    - .planning/phases/49-review-model/49-CONTEXT.md
    - .planning/phases/49-review-model/deferred-items.md

key-decisions:
  - "T-15-02-BENCH retired as SATISFIED, not weakened — its reconciliation concern is now met by the boundary confirm, the no-fallback tenure derivation, the Missing-tenure/no-person affordance, and 49-09's published lock, per D-35."
  - "The extraction is a shared module, not a shared component — only sideBucket/SIDE_LABEL/specificAdvocateRole are pure; clearPersonOnSideBucketChange and the toggle handlers stay in ResolveCard because they depend on component state."
  - "The bench companion follows the operator's CURRENT selection (speakerSideById), not the stored is_bench flag, so it appears the instant Bench is picked rather than only after save."
  - "The descriptor round trip is fixed at both ends: the service skips the descriptor column entirely on a BENCH write (RESOLVE-13), and the form action omits the descriptor key when the row's committed side was BENCH."
  - "The public chat page's independently derived bench flag is NOT reconciled (outside Phase 49's boundary) — recorded as MORE reachable by this plan, not silently accepted."

patterns-established:
  - "A future cross-surface pure-logic extraction in this codebase should land in $lib/*.ts with named exports and no framework imports, following docketValues.ts/personNames.ts/participantSide.ts."

requirements-completed: [REVIEW-01, REVIEW-04]

coverage:
  - id: D1
    description: "Shared participantSide.ts module: bucket rule, label map, specific-advocate-role helper, and boundary-crossing predicate, consumed by both ResolveCard.svelte and the Speakers card"
    requirement: "REVIEW-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py::test_side_bucket_helper_treats_all_advocate_roles_as_one_bucket"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py::test_resolve_card_imports_side_bucket_from_shared_module_not_a_local_declaration"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_shared_module_exports_the_label_map_byte_identical_to_todays_advocate_labels"
        status: pass
    human_judgment: true
    rationale: "The Resolve card's browser behavior (toggle highlight, person-clear on real boundary crossing, unchanged labels) is not provable by source assertions alone — see 48-10's false-green incident. A human-check walk was specified for this task; not observed in this session (no browser tool available to the executor)."
  - id: D2
    description: "Backend accepts BENCH under RESOLVE-13; T-15-02-BENCH retired as satisfied with descriptor preservation, review_state advance, discrepancy closure, and the published lock all proved live"
    requirement: "REVIEW-01"
    verification:
      - kind: integration
        ref: "api/tests/test_phase49_participant_side_contract.py::test_bench_side_write_succeeds_and_preserves_the_stored_descriptor"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase49_participant_side_contract.py::test_bench_round_trip_does_not_lose_the_descriptor"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase49_participant_side_contract.py::test_bench_write_advances_review_state_and_closes_discrepancies"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase49_participant_side_contract.py::test_bench_write_still_refused_on_a_published_argument"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_one_authority_gated_call_handles_side"
        status: pass
    human_judgment: false
  - id: D3
    description: "One converged Speakers row: five reachable side values, boundary-crossing confirm, three-state bench companion (role/missing-tenure/no-person), descriptor round trip, published lock and unresolved gate intact — closes G-49-3"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_speakers_row_has_no_per_class_branch"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_boundary_crossing_requires_a_second_click"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_bench_companion_distinguishes_three_states"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_participant_side_contract.py::test_action_omits_descriptor_when_the_committed_side_was_bench"
        status: pass
    human_judgment: true
    rationale: "Every .svelte assertion above is STRUCTURAL-ONLY — proves a string/pattern is present in source, never that the control renders or behaves in a browser (the 48-10 false-green precedent). The plan's six-item human-check (side control reaches every value, confirm gate on a real crossing, no confirm among advocate roles, live descriptor round trip, no-person/missing-tenure affordances, published lock) was not observed in this session; a browser tool is available to the orchestrator but not to this executor."

duration: 90min
completed: 2026-08-24
status: complete
---

# Phase 49 Plan 10: Converge the Speakers Card onto the Resolve Card's Full Side Vocabulary Summary

**Shared `participantSide.ts` bucket/label module, backend BENCH acceptance under RESOLVE-13, and one converged Speakers row template with a boundary-crossing confirm — closing G-49-3 and the second half of D-35.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-08-24 (session start)
- **Completed:** 2026-08-24T22:47:40Z
- **Tasks:** 3 (all completed)
- **Files modified:** 16 (1 created)

## Accomplishments

- Extracted the bench/advocate bucket rule, the operator-visible role labels (`SIDE_LABEL`), and `specificAdvocateRole` out of `ResolveCard.svelte` into `app/src/lib/participantSide.ts`, plus one genuinely new export, `crossesSideBoundary` — the single source of truth both cards now import from.
- `update_participant_side` now accepts `BENCH`. `T-15-02-BENCH` is retired **as satisfied**, not weakened: its reconciliation concern is met by four compensating controls (the boundary confirm, the no-fallback tenure derivation, the Missing-tenure/no-person affordance, and 49-09's published lock), all recorded in the function's own docstring, the schema docstring, and both router docstrings.
- RESOLVE-13 is enforced on this path exactly as it already was on the resolve path: a BENCH write never touches the descriptor column, and the round trip (advocate → bench → advocate, descriptor omitted both times) still reports the original descriptor — proved live.
- The Speakers card is now ONE row template: bench and advocate rows are structurally indistinguishable in affordance depth. The side control reaches all five stored values. A boundary-crossing selection requires an explicit second click (purpose-port of the Resolve card's side gate); a change among advocate roles does not. The bench companion is a three-state affordance (tenure role / missing-tenure warning + edit link / no-person-linked) keyed on `person_id` first, closing the one-way trap where a bench row with no person rendered a bare em-dash.
- G-49-3 is marked `status: resolved` in `49-UAT.md`; D-35 (both halves, this plan's half and 49-09's) is recorded in `49-CONTEXT.md`.

## Task Commits

1. **Task 1: One shared side module** — `574903cb5` (feat)
2. **Task 2: Backend accepts BENCH under RESOLVE-13; T-15-02-BENCH retired** — `49dbd082d` (fix)
3. **Task 3: One converged Speakers row (closes G-49-3)** — `5ec8d1fde` (feat)

_Note: this plan's `tdd="true"` tasks did not follow the strict RED-commit/GREEN-commit/REFACTOR-commit three-commit cycle — each task's tests and source landed in a single commit per task, matching plans 49-07/49-08/49-09's precedent on this phase. RED-phase failures were observed and are quoted below before any commit was made._

**Plan metadata:** (this commit, made by the orchestrator after this SUMMARY)

## Files Created/Modified

- `app/src/lib/participantSide.ts` — shared bucket rule, label map, specific-advocate-role helper, boundary-crossing predicate
- `app/src/lib/components/ResolveCard.svelte` — imports the four from the shared module; declares none locally; `clearPersonOnSideBucketChange` delegates its comparison to `crossesSideBoundary` while keeping its own `previousBucket !== undefined` guard visible
- `app/src/routes/admin/arguments/[id]/+page.svelte` — one converged Speakers row template; `VALID_SIDES` admits `BENCH`; seed no longer filters bench rows; `sideConfirming` state + its Pitfall-7 reset; boundary-crossing confirm UI; three-state bench companion; hidden `committed_side` input
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — `updateParticipantSide` action reads `committed_side`; PATCH body omits `descriptor` unless the field was submitted (browser omits disabled inputs) AND the committed side was not BENCH
- `api/services/admin_arguments.py` — `update_participant_side` no longer raises on `side == BENCH`; descriptor gate skipped entirely when `side == BENCH`; `persisted_descriptor` reports the existing value on a bench write; docstring carries the full retirement paragraph
- `api/services/admin_jobs.py` — `update_resolve_row_for_job`'s own docstring corrected (it referenced the now-retired "rejects BENCH by design" rationale for why the two writers don't delegate)
- `api/schemas/admin_arguments.py`, `api/routers/admin.py` (two docstrings) — the remaining three of the plan's four named citation sites updated
- `api/tests/test_phase44_resolve_table_contract.py` — re-pointed `test_side_bucket_helper_treats_all_advocate_roles_as_one_bucket` at the shared module; added the opposite-direction companion assertion; widened `_function_body`'s closing-brace regex to accept both the component's one-tab-nested convention and a top-level module's zero-indent convention
- `api/tests/test_phase49_participant_side_contract.py` — all three tasks' new assertions (17 new tests across Tasks 1–3)
- `api/tests/test_admin_arguments_service.py`, `api/tests/test_admin_arguments_routes.py`, `api/tests/test_admin_jobs_phase25.py` — rewrote the tests/docstrings that asserted the now-retired BENCH rejection
- `.planning/phases/49-review-model/49-CONTEXT.md`, `49-UAT.md`, `deferred-items.md` — D-35 recorded; G-49-3 resolved; two out-of-scope items recorded with explicit dispositions

## Decisions Made

See `key-decisions` in frontmatter. The single most consequential one: **T-15-02-BENCH is retired as satisfied, not weakened.** A future reader must not read this as a relaxed security posture — the guard's actual concern (no reconciliation-free bench classification) is met at the new call site by four independent controls, three of them pre-existing (the tenure no-fallback rule, the Missing-tenure affordance, 49-09's published lock) and one new (the boundary confirm). Nothing about IDOR scoping, the mass-assignment boundary, the unresolved-side rejection, or the single authority-gated writer changed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_admin_arguments_routes.py`'s route-level descriptor test asserted the retired BENCH rejection**
- **Found during:** Task 2 regression run (`test_admin_arguments_routes.py` is not in this plan's `files_modified` list, but the plan's own action text names it as a module to run)
- **Issue:** `test_update_participant_route_persists_descriptor_for_advocate` had its own final block asserting `PATCH .../participants/{id}` with `side=BENCH` returns 422 — this is the exact same class of stale assertion Task 2 rewrote at the service level, just one layer up, and the plan's read_first did not name this specific test.
- **Fix:** Rewrote the final block to assert the new contract (BENCH succeeds, descriptor unchanged) — same pattern as the service-level rewrite, docstring updated, nothing deleted.
- **Files modified:** `api/tests/test_admin_arguments_routes.py`
- **Verification:** `test_update_participant_route_persists_descriptor_for_advocate` passes; full suite green.
- **Committed in:** `49dbd082d` (Task 2 commit)

**2. [Rule 1 - Bug] `api/services/admin_jobs.py`'s own docstring cited the now-retired rationale**
- **Found during:** Task 2, while grepping for other "rejects BENCH by design" references after fixing the two explicitly-named test docstrings
- **Issue:** `update_resolve_row_for_job`'s docstring stated it "does NOT route through admin_arguments.update_participant_side, which rejects BENCH by design" — a fifth citation site beyond the plan's four named ones, now inaccurate.
- **Fix:** Corrected to state both writers accept BENCH and that they remain separate due to differing trust-boundary derivation (job_id vs. argument id), not a since-retired rejection.
- **Files modified:** `api/services/admin_jobs.py`
- **Verification:** Full suite green; no assertion changed, docstring-only edit.
- **Committed in:** `49dbd082d` (Task 2 commit)

**3. [commit-boundary note, not a functional deviation] `api/tests/test_phase49_participant_side_contract.py`'s Task 1 and Task 2 test additions landed in their respective task commits correctly, but Task 1's three new assertions and the constants they use were appended contiguously with no intervening commit before Task 2's additions began** — both tasks' test-file diffs are cleanly separated in the actual commits (Task 1's commit touches only the path-constant addition; Task 2's and Task 3's each touch their own appended sections), verified by `git show --stat` on each commit. No test content is misattributed to the wrong task's commit.

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — stale test/docstring assertions of the retired BENCH rejection, found beyond the plan's four explicitly named citation sites)
**Impact on plan:** Both fixes are direct, necessary consequences of retiring T-15-02-BENCH consistently everywhere it was asserted — no scope creep, no architectural change.

## Issues Encountered

- `_function_body`'s tab-indented-closing-brace convention (in `test_phase44_resolve_table_contract.py`) assumed every extracted function is nested one level inside a `<script>` block (ResolveCard.svelte's convention). `participantSide.ts` is a top-level `$lib` module (docketValues.ts's convention), whose functions close at column zero. Widened the regex from `\n\t\}` to `\n\t?\}` — verified safe because a more deeply nested closing brace (two-plus tabs) still cannot match, so the first true end-of-function is still what is found; confirmed no existing test in that module regressed.
- `get_argument_detail` requires a `Case`/`CaseArgument` lead link to return non-`None` — the round-trip test originally called it and got `None` back. Switched to `list_argument_speakers`, the lower-level function that only needs the `Argument` row, matching what the page's own read path (`_speaker_rows`) actually calls.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

G-49-3 is closed. `deferred-items.md` records two open items for future consideration, both explicitly NOT part of this plan's scope: (1) the public chat page's independently-derived bench flag, now MORE reachable by operator action than before this plan — tracked by the existing todo `2026-08-12-speakers-bench-classification-silent-fallback.md`; (2) person-to-participant reassignment remains uneditable on the Speakers card (remedy: the Resolve card) — a genuinely separate gap the operator has not raised.

Plan 49-11 (whole-argument published lock, D-35a) depends on nothing this plan changed structurally — it explicitly does not touch `update_participant_side`, the Speakers card, or the participant-side module, and its own plan text already anticipates that 49-10 appended `D-35` to `49-CONTEXT.md` first (it appends `D-35a` after it).

**Human-check items NOT observed in this session** (browser tooling is available to the orchestrator, not to this executor):
1. Task 1: Resolve-card regression walk — toggle behavior, person-clear on real boundary crossing, unchanged advocate labels.
2. Task 3: the six-item Speakers-card convergence walk (every row reaches every value; confirm gate fires only on a real crossing; the live descriptor round trip; the no-person/missing-tenure bench-companion states; the published lock disabling everything).
3. 49-09's published-lock walk (not re-run here; unaffected by this plan's changes per the regression suite).

Recommend running these three walks in the browser before considering G-49-3 fully closed from a UX standpoint, using arguments 1809 (unresolved-speaker case), 1810 (draft, to exercise the boundary confirm and round trip), and 1811 (published, to confirm the lock still holds).

---
*Phase: 49-review-model*
*Completed: 2026-08-24*

## Self-Check: PASSED

- FOUND: `app/src/lib/participantSide.ts`
- FOUND: `api/tests/test_phase49_participant_side_contract.py`
- FOUND: `app/src/routes/admin/arguments/[id]/+page.svelte`
- FOUND: `app/src/routes/admin/arguments/[id]/+page.server.ts`
- FOUND: `574903cb5` (Task 1 commit)
- FOUND: `49dbd082d` (Task 2 commit)
- FOUND: `5ec8d1fde` (Task 3 commit)
