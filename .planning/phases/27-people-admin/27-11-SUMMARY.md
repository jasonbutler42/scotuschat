---
phase: 27-people-admin
plan: 11
subsystem: ui
tags: [svelte5, runes, effect, bugfix, admin]

# Dependency graph
requires:
  - phase: 27-people-admin (plan 10)
    provides: CR-01 (always-present hidden birthdate/tenures inputs) and CR-02 (tenureRows/nextKey re-derivation on person-id change) data-preservation fixes
provides:
  - Fixed effect_update_depth_exceeded infinite-loop regression on /admin/people/[id]
affects: [27-people-admin verification/UAT]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Write-only $state reset inside $effect: use a plain local (non-reactive) counter for intermediate reads inside a .map() callback, and write the $state variable exactly once after the loop completes, so the effect never reads back a $state var it wrote in the same run"

key-files:
  created: []
  modified:
    - "app/src/routes/admin/people/[id]/+page.svelte"

key-decisions:
  - "Used a plain local `let resetKey = 1` counter (not $state) inside the person-id-change reset $effect, writing `nextKey` exactly once after the .map() completes, matching the established write-only reset-effect convention already used elsewhere in the codebase (e.g. admin/pipeline/[job_id]/+page.svelte:78)"

patterns-established:
  - "Reset $effects that recompute a keyed list must never read back a $state variable they're also writing during the same effect run — use a local plain-variable counter for the intermediate reads/increments, then a single write-only assignment to the $state variable at the end"

requirements-completed: [PEDIT-07]

coverage:
  - id: D1
    description: "Break the nextKey self-referential read+write inside the person-id-change reset $effect, eliminating the effect_update_depth_exceeded infinite-loop regression"
    requirement: "PEDIT-07"
    verification:
      - kind: automated_ui
        ref: "cd app && npm run check (0 errors / 16 warnings, unchanged baseline)"
        status: pass
      - kind: other
        ref: "grep counts: 'nextKey = 1;' = 0, 'nextKey = resetKey;' = 1, 'let resetKey = 1;' = 1, 'resetKey++' = 1, 'nextKey++' = 2"
        status: pass
    human_judgment: true
    rationale: "The actual browser behavior (no console effect-rerun spam, no effect_update_depth_exceeded throw, responsive navigation) and the CR-01/CR-02 data-preservation round-trips can only be confirmed by a live click-through in a browser, per the established 27-07/08/09/10 gap-closure pattern — this is deferred to the next /gsd-verify-work 27 UAT retest, which this fix unblocks."

duration: 8min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 11: Fix person-detail effect_update_depth_exceeded loop Summary

**Replaced a self-referential `nextKey` $state read+write inside the person-id-change reset `$effect` with a write-only pattern using a local non-reactive counter, eliminating the infinite-loop regression introduced by the 27-10 CR-02 fix.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-09T18:00:00Z
- **Completed:** 2026-07-09T18:08:00Z
- **Tasks:** 1 completed
- **Files modified:** 1

## Accomplishments
- Fixed the `effect_update_depth_exceeded` infinite-loop bug on `/admin/people/[id]` for any person with >=1 tenure row, caused by the person-id-change reset `$effect` reading and writing the `$state` variable `nextKey` synchronously within the same effect run (`nextKey = 1;` followed by `_key: nextKey++` inside a `.map()` callback)
- Restored the codebase's established write-only reset-effect convention: the `$state` variable `nextKey` is now written exactly once (`nextKey = resetKey;`), after a local plain-variable counter (`resetKey`) computes all intermediate `_key` values during the `.map()`
- Preserved the CR-01 (always-present hidden inputs) and CR-02 (tenureRows/nextKey re-derivation on person-id change) data-preservation behavior from Plan 27-10 verbatim — every other statement in the effect (merge state resets, `isJustice`, `birthdate`) and the top-of-script initializer/`addTenureRow`/`removeTenureRow` are byte-for-byte unchanged
- `svelte-check` remains at the pre-existing baseline of 0 errors / 16 warnings

## Task Commits

Each task was committed atomically:

1. **Task 1: Break the nextKey self-referential read+write inside the person-id-change reset $effect** - `9651e27c` (fix)

**Plan metadata:** (final commit, see below)

## Files Created/Modified
- `app/src/routes/admin/people/[id]/+page.svelte` - Replaced `nextKey = 1;` + `_key: nextKey++` inside the person-id-change reset `$effect` with `let resetKey = 1;` + `_key: resetKey++`, then a single trailing `nextKey = resetKey;` write

## Decisions Made
- Used a plain local `let resetKey = 1` counter (not `$state`) scoped to this single effect run, mirroring the safe pattern already used by the top-of-script `tenureRows`/`nextKey` initializer (which runs at component init, outside `$effect`) and the codebase-wide write-only reset-effect convention (e.g. `admin/pipeline/[job_id]/+page.svelte:78`)

## Deviations from Plan

None - plan executed exactly as written. The task's `<action>` steps were followed precisely: `nextKey = 1;` inside the effect replaced with `let resetKey = 1;`, `_key: nextKey++` changed to `_key: resetKey++`, and a single trailing `nextKey = resetKey;` added immediately after the `.map()` assignment completes. All other statements in the effect (merge state resets, `isJustice`, `birthdate`) and the top-of-script initializer/`addTenureRow`/`removeTenureRow` were left untouched, as instructed.

## Issues Encountered
None. The file's current state matched the debug session's diagnosis exactly (person-id-change reset effect at lines 125-150, `nextKey = 1;` at line 133, `_key: nextKey++` at line 142), so no line-number reconciliation was needed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 27's 4th UAT retest (`27-UAT.md`) is unblocked: opening `/admin/people/[id]` for a Justice with tenure rows should no longer throw `effect_update_depth_exceeded` or spam console effect reruns, and the page should no longer feel "crazy slow"
- Functional confirmation (live click-through) of this fix, plus re-testing CR-01 (Test 1), CR-02 (Test 2), and the 4 other previously-blocked tests (Tests 3-6: slide-reveal animation, column spacing, President's Party dropdown, create-person name-parts), is deferred to the next `/gsd-verify-work 27` pass, per the established 27-07/08/09/10 gap-closure pattern
- No blockers or concerns beyond the standard human UAT retest that follows every Phase 27 gap-closure plan

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: `app/src/routes/admin/people/[id]/+page.svelte`
- FOUND: `.planning/phases/27-people-admin/27-11-SUMMARY.md`
- FOUND commit: `9651e27c`
- FOUND commit: `bbd792fc`
