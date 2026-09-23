---
phase: 50-unified-import-path
plan: 04
subsystem: ui
tags: [admin-review, discrepancy-render, argument-approve, svelte-form-action]

requires:
  - phase: 50-unified-import-path
    plan: "02"
    provides: "ReviewQueueArgumentItem.argument_discrepancies — the argument-level/lead-case-level discrepancy detail this plan renders"
  - phase: 50-unified-import-path
    plan: "03"
    provides: "POST /api/admin/arguments/{id}/approve — the argument-scoped approve route this plan's form posts to"
provides:
  - "Argument-level and lead-case-level discrepancy render on /admin/review — a Discrepancy badge on the collapsed row's case name plus a full stored/incoming detail block at the top of the expanded panel"
  - "The Approve action on a CANDIDATE argument's review row, rendered once per argument regardless of constituent state, posting to the argument-scoped approve route"
affects: [50-05, 50-06, 50-07]

actuals:
  tokens: 2644
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Argument-scoped action rendered OUTSIDE the per-constituent {#each} loop and its constituents-vs-blockers branch, so a per-argument action is guaranteed to render exactly once regardless of whether the argument has any flagged constituent — the per-constituent action row precedent (Confirm/Confirm-as-unattributable/Re-flag) cannot be reused verbatim for an argument-scoped action without producing either zero or N duplicate buttons"
    - "Reused discrepancyBadgeStyle()/discrepancyValueDisplay() and the stored-then-incoming two-line layout verbatim for the new argument-level block, so an argument/case-level disagreement reads identically to a participant-level one (D-07's visibility claim)"

key-files:
  created: []
  modified:
    - app/src/routes/admin/review/+page.svelte
    - app/src/routes/admin/review/+page.server.ts
    - api/tests/test_phase49_review_ui_contract.py

key-decisions:
  - "The Approve form action was placed OUTSIDE the {#each item.constituents} loop, not inside the per-constituent action row the plan's read_first pointer named — a literal per-constituent placement would either duplicate the button once per flagged constituent, or (worse) never render at all for a CANDIDATE argument queued solely via a degraded-tier or argument/case-discrepancy leg with zero flagged constituents, which is the primary use case D-14 exists to unblock. Rule 1 (bug prevention) — documented under Deviations."
  - "The local ReviewQueueArgumentItem TypeScript type Task 1 asked to extend lives in +page.server.ts, not in +page.svelte's module script (the .svelte file declares no local types; it infers PageData). Edited +page.server.ts instead — already listed in the plan's own frontmatter files_modified for the whole plan, and required for svelte-check's zero-errors acceptance criterion."

requirements-completed: [IMPORT-03, IMPORT-05]

coverage:
  - id: D1
    description: "An argument whose own value or whose lead case's value disagrees shows a Discrepancy badge on its /admin/review row and the stored/incoming pair in its expanded panel, rendered identically to a participant-level discrepancy"
    requirement: IMPORT-05
    verification:
      - kind: other
        ref: "api/tests/test_phase49_review_ui_contract.py::test_argument_discrepancies_referenced_at_least_three_times, ::test_argument_discrepancies_iterated_with_keyed_each_on_id, ::test_argument_discrepancies_render_both_existing_and_incoming_through_display_helper, ::test_argument_level_discrepancy_row_badge_conditioned_on_non_empty_list"
        status: pass
    human_judgment: true
    rationale: "Source-contract tests prove the render structure exists and is wired to the right field, but per the project's own documented $state-proxy-vs-grep-contract-test trap, they cannot prove the badge/detail block actually appears correctly in a browser against a live discrepancy row. WINDOWS.md #30 records the unrun browser walkthrough."
  - id: D2
    description: "A CANDIDATE argument's review row carries an Approve action that posts to the argument-scoped approve route, and after it succeeds the row's status reads Draft; the action is absent for every other status; it is the only new per-argument action (no argument-scoped resolve or create-person)"
    requirement: IMPORT-03
    verification:
      - kind: other
        ref: "api/tests/test_phase49_review_ui_contract.py::test_approve_form_posts_to_the_approve_action, ::test_approve_form_guarded_by_candidate_status_condition, ::test_approve_action_present_in_server_module_posting_to_argument_scoped_route"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py -k approve (6 tests, re-run this session against the argument-scoped approve route this form calls)"
        status: pass
    human_judgment: true
    rationale: "The form-action wiring and its backing route are both tested, but the end-to-end click-Approve-see-Draft-then-publish walkthrough (Task 2's <human-check>) was never observed in a browser — no browser tool or .env admin credential access available to this executor. WINDOWS.md #30."
  - id: D3
    description: "No new class attribute, style block, media query, or truncation is introduced on the page; the full regression suite stays green"
    requirement: IMPORT-05
    verification:
      - kind: other
        ref: "grep -c 'class=' / 'text-overflow' / '@media' == 0 (test_no_class_attribute_anywhere_inline_styles_only, test_no_truncation_or_media_query_introduced_on_the_review_page); npx svelte-check --threshold error == 0 errors; ./.venv/bin/python -m pytest -q == 1561 passed, 5 xfailed, 0 failed (was 1554/5/0; +7 is exactly the new contract-test assertions, zero regressions)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 04: Argument-Level Discrepancy Render + Argument-Scoped Approve on /admin/review Summary

**Two additions to `/admin/review`: an argument/lead-case-level Discrepancy badge and detail block reusing the existing participant-level styling verbatim, and an Approve form (posting to plan 50-03's argument-scoped route) that renders once per CANDIDATE argument regardless of constituent state — not nested inside the per-constituent action row, which would have either duplicated it or hidden it entirely for the primary zero-constituent use case.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `argument_discrepancies` is rendered at the top of the expanded panel — a bordered block reusing `discrepancyBadgeStyle()`/`discrepancyValueDisplay()` and the stored-then-incoming two-line layout verbatim (keyed `{#each ... as d (d.id)}`), plus the same Discrepancy badge next to the case name on the collapsed row when the list is non-empty.
- A candidate argument's expanded panel now carries an "Approve — move to Draft" button, posting to a new `?/approve` form action in `+page.server.ts` that calls `POST /api/admin/arguments/{id}/approve` with the admin token, preserves the tab/filter query string on redirect, and surfaces a non-OK response as an operator-readable `fail(422, ...)` message rather than swallowing it.
- 7 new source-contract assertions added to `api/tests/test_phase49_review_ui_contract.py` (4 for Task 1, 3 for Task 2).
- Full suite: 1561 passed, 5 xfailed, 0 failed (was 1554/5/0 — the +7 delta is exactly the new contract-test assertions, zero regressions).

## Task Commits

1. **Task 1: Render argument-level and lead-case-level discrepancies** — `c1eed5854` (feat)
2. **Task 2: The Approve action on a candidate argument's review row** — `adf54dad5` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `app/src/routes/admin/review/+page.svelte` — argument-level discrepancy badge (collapsed row) + detail block (expanded panel, top); argument-scoped Approve form (expanded panel, rendered once per argument, gated on `item.status === 'candidate'`)
- `app/src/routes/admin/review/+page.server.ts` — `argument_discrepancies` field added to the local `ReviewQueueArgumentItem` type; `approveArgument()` helper + `approve` form action
- `api/tests/test_phase49_review_ui_contract.py` — 4 new assertions for the discrepancy render, 3 new assertions for the Approve form/action

## Decisions Made

- See key-decisions in frontmatter: the Approve action's placement (outside the per-constituent loop) and the type-declaration file correction are both documented there and expanded on below under Deviations.
- Heading text for the argument-level discrepancy block reads "This argument's own values and its lead case's" — names the scope as distinct from a participant's, per the plan's action text, without inventing new UI-SPEC vocabulary.
- Approve button label reads "Approve — move to Draft" — states the destination in operator vocabulary per the plan's explicit instruction, not an internal transition name.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Approve form placed outside the per-constituent action row, not inside it**
- **Found during:** Task 2, reading the actual current structure of the expanded panel before editing.
- **Issue:** The plan's read_first pointer named `app/src/routes/admin/review/+page.svelte:538-572` — "the expanded panel's action row, containing the three existing action forms; the new form goes in the same row" — as the insertion site. That row (Confirm / Confirm-as-unattributable / Edit / Re-flag) is nested INSIDE `{#each item.constituents as constituent}`, scoped per-participant. Approve is argument-scoped (D-14), not participant-scoped. Placing it there verbatim would have either rendered one Approve button per flagged constituent (visually wrong, and arguably a footgun — clicking any one of N duplicate buttons submits the same argument-level action), or — critically — never rendered at all for a CANDIDATE argument with zero flagged constituents, since that state renders the sibling `{:else}` blockers-list branch instead of the `{#each}` loop. A candidate argument queued solely via a degraded-tier leg or an argument/case-level discrepancy (this same plan's Task 1 deliverable) is exactly the kind of row that can have zero flagged constituents — meaning the literal placement would have silently broken D-14's stated purpose ("without it a jobless corpus argument is permanently unpublishable") for its own primary case.
- **Fix:** Added a new, argument-scoped block immediately after the `{#if item.constituents.length > 0}...{:else}...{/if}` pair, still inside the same `<td colspan="6">`, gated only on `item.status === 'candidate'`. It renders exactly once per argument row regardless of constituent state.
- **Files modified:** `app/src/routes/admin/review/+page.svelte`
- **Verification:** `grep -c "?/approve"` == 1 (not N); the acceptance criterion "the approve form is rendered only under a candidate-status condition" is met by a dedicated contract test; svelte-check 0 errors; full suite green.
- **Committed in:** `adf54dad5` (Task 2 commit)

**2. [Rule 3 - Blocking] `ReviewQueueArgumentItem`'s local type declaration edited in `+page.server.ts`, not `+page.svelte`**
- **Found during:** Task 1, locating the type declaration the plan's action text named.
- **Issue:** `+page.svelte`'s module script (`<script lang="ts">`) declares no local types at all — `let { data, form } = $props();` is untyped, inferring via SvelteKit's generated `PageData`. The actual `ReviewQueueArgumentItem` type lives in `+page.server.ts`. Without adding `argument_discrepancies` there, `item.argument_discrepancies` in the `.svelte` template would have no type backing it, and `svelte-check --threshold error` (a hard acceptance criterion for both tasks) would either fail or silently widen to `any`.
- **Fix:** Added `argument_discrepancies: DiscrepancyDetail[]` to the `ReviewQueueArgumentItem` type in `+page.server.ts` instead. This file was already in the plan's own frontmatter `files_modified` list for the whole plan (though not Task 1's own narrower `<files>` sub-list) — required for Task 2 anyway.
- **Files modified:** `app/src/routes/admin/review/+page.server.ts`
- **Verification:** `npx svelte-check --threshold error` reports 0 errors after this change.
- **Committed in:** `c1eed5854` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug prevention — the plan's literal placement would have broken its own D-14 purpose for the primary use case; 1 Rule 3 blocking-issue correction — the named file had no type to extend). **Impact:** Both were necessary for correctness; neither changed the plan's stated behavior or added scope beyond what Task 1/Task 2 already specified.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The argument-level/lead-case-level discrepancy render and the argument-scoped Approve action are both live on `/admin/review`, structurally verified by source-contract tests and (for Approve) by the underlying route's own integration tests re-run this session.
- **Not observed in a browser this session** — same constraint as every prior Phase 49/50 UI plan in this project (no browser tool, no `.env` admin credential access): the Task 2 `<human-check>` walkthrough (click Approve on a candidate corpus argument; confirm status flips to Draft, the tab/filter selection survives the redirect, the Approve button disappears from that row; publish the same argument afterward; confirm a discrepancy value is fully readable with no truncation at 1280px and at a narrow viewport). Recorded as `WINDOWS.md` entry #30 and as `human_judgment: true` in this SUMMARY's coverage block for D1/D2. A human should complete this walkthrough before UAT sign-off, alongside the other outstanding Phase 49 browser items already tracked in `49-EVIDENCE.md` §9.
- No blockers for plan 50-05 (the reconcile compare-and-write body) or plan 50-06 (D-22 delegation sweep) — neither depends on this plan's UI surface.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All modified files verified present on disk with the expected content; both task commit hashes (`c1eed5854`, `adf54dad5`) verified present in git log; full suite re-run in foreground: 1561 passed, 5 xfailed, 0 failed (up from 1554/5/0 baseline).
