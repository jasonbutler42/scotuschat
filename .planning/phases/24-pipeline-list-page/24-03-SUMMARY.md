---
phase: 24-pipeline-list-page
plan: 03
subsystem: ui
tags: [svelte5, sveltekit, forms, refactor, docket-pills]

# Dependency graph
requires:
  - phase: 24-pipeline-list-page
    provides: DocketPillInput shared component (Plan 02)
provides:
  - ArgumentDetailsCard consuming shared DocketPillInput component instead of inline pill logic
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyed block ({#key ...}) re-seeds a child component's internal $state from a parent-owned initial-value source on failed form submission"

key-files:
  created: []
  modified:
    - app/src/lib/components/ArgumentDetailsCard.svelte

key-decisions:
  - "effectiveDockets $state replaces the old direct pills $state as the parent-owned docket source of truth, keyed via effectiveDockets.join('\\u001f') to force DocketPillInput to re-seed from initialValues on failed-save restoration"

patterns-established:
  - "Shared pill-input sub-components re-seed via a keyed block driven by a parent $effect watching form action results, rather than syncing state top-down every render"

requirements-completed: [PLIST-02]

coverage:
  - id: D1
    description: "ArgumentDetailsCard renders docket pills via the shared DocketPillInput component, with identical add/remove/serialize behavior and failed-save restoration"
    requirement: "PLIST-02"
    verification:
      - kind: unit
        ref: "node -e source-assertion script (import/usage/reset:false/no dead addPill) — PASS"
        status: pass
      - kind: other
        ref: "npx svelte-check --tsconfig ./tsconfig.json --threshold error — 0 ERRORS 19 WARNINGS (pre-existing baseline)"
        status: pass
      - kind: manual_procedural
        ref: "Manual verification of add/remove docket pills, save, and failed-save restoration on the job detail page"
        status: unknown
    human_judgment: true
    rationale: "Automated checks confirm source structure and type-safety, but end-to-end browser behavior (pill add/remove UX, failed-save restoration visually) requires human verification on the running app."

duration: 10min
completed: 2026-07-07
status: complete
---

# Phase 24 Plan 03: ArgumentDetailsCard DocketPillInput Refactor Summary

**Refactored ArgumentDetailsCard.svelte to delegate docket pill add/remove/render logic to the shared DocketPillInput component, replacing ~90 lines of inline pill markup and state with a single keyed component instance.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-07T13:58:25Z
- **Completed:** 2026-07-07T14:04:43Z
- **Tasks:** 1 completed
- **Files modified:** 1

## Accomplishments

- `ArgumentDetailsCard.svelte` now imports and renders `DocketPillInput` for the docket field instead of maintaining its own `pills` state, `addPill()`, and `removePill()` functions
- Failed-save restoration behavior preserved: a new `effectiveDockets` state variable (renamed from `pills`) is still synchronized from `form.dockets` via `$effect`, and a `{#key effectiveDockets.join('')}` block forces `DocketPillInput` to re-seed its internal pill state from the updated `initialValues` on failed saves
- The `use:enhance` callback, including the mandatory `update({ reset: false })` on success and default `update()` on failure (Phase 23 state-preservation pattern), is completely unchanged
- The docket extracted-hints row (`hints.dockets` pills / "N/A") still renders directly below the pill input, unchanged
- Public component props interface (`savedValues`, `hints`, `action`, `readonly`, `form`) unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace inline pill logic in ArgumentDetailsCard with DocketPillInput (D-04, PLIST-02)** - `fcdbe43d` (refactor)

**Plan metadata:** (this commit, docs)

_Note: single-task plan; no TDD gates apply._

## Files Created/Modified

- `app/src/lib/components/ArgumentDetailsCard.svelte` - Removed inline `docketInput` state, `addPill()`, `removePill()`, and ~90 lines of inline pill markup; now imports and renders `<DocketPillInput initialValues={effectiveDockets} name="docket[]" id="docket-input" {readonly} />` inside a keyed block driven by `effectiveDockets`

## Decisions Made

- Renamed the parent's docket state variable from `pills` to `effectiveDockets` to clarify its new role as an initial-value source for the child component rather than the live editable pill array itself (the live array now lives inside `DocketPillInput`'s own `$state`)
- Used `effectiveDockets.join('')` (unit separator character) as the `{#key}` expression per the plan's explicit guidance, avoiding ambiguous joins that a plain `join('')` or `join(',')` could produce if docket values themselves contained commas

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`ArgumentDetailsCard` and the pipeline list page's docket editing UI (Plan 02) now share a single `DocketPillInput` implementation, satisfying D-04. No blockers for subsequent plans in Phase 24.

---
*Phase: 24-pipeline-list-page*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: app/src/lib/components/ArgumentDetailsCard.svelte
- FOUND: .planning/phases/24-pipeline-list-page/24-03-SUMMARY.md
- FOUND: fcdbe43d
- FOUND: bb17bd25
