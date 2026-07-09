---
phase: 27-people-admin
plan: 10
subsystem: ui
tags: [svelte, sveltekit, forms, data-integrity]

# Dependency graph
requires:
  - phase: 27-people-admin (27-09)
    provides: Person Type card (Bench/Advocate segmented toggle), curated President's Party dropdown, tenure sub-cards
provides:
  - "Always-present hidden birthdate/tenures inputs in the [id] person editor's save-form, decoupled from the Bench/Advocate toggle's mount state"
  - "Complete person-id-change reset $effect that re-derives tenureRows/nextKey alongside its existing merge/isJustice/birthdate resets"
affects: [27-people-admin verification, any future person-editor gap-closure plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Data-carrying hidden form inputs must live outside any `{#if}` block whose condition an operator can toggle before submit — conditional *rendering* must never gate what data reaches FormData"
    - "SvelteKit soft-navigation reset effects (component reuse across `data.person.id` changes) must reset every piece of per-entity $state, not just the fields that were reset when the effect was first introduced"

key-files:
  created: []
  modified:
    - "app/src/routes/admin/people/[id]/+page.svelte"

key-decisions:
  - "Relocated the hidden birthdate and tenures inputs to sit alongside the existing always-present is_justice hidden input (immediately before {#if isJustice}), rather than creating a new markup location — reuses the established form=\"save-form\" cross-form-association idiom already used throughout this file"
  - "Removed name/form attributes from the visible Birth Date <input> (kept id + bind:value) rather than keeping a duplicate name=\"birthdate\" input, per the plan's explicit exactly-one-input-per-name requirement"
  - "Reset effect's tenureRows re-derivation mirrors the top-of-script initializer's map callback verbatim (same field list, same ?? '' fallbacks) rather than extracting a shared helper — plan explicitly instructed keeping the initializer unchanged and not creating a second effect"

patterns-established:
  - "Toggle-hidden UI sections that carry persisted state must expose that state to the submitted form via always-mounted hidden inputs bound to the same $state variables the visible UI edits, not via inputs nested inside the toggled section itself"

requirements-completed: [PEDIT-07]

coverage:
  - id: D1
    description: "Toggling an existing Justice's Person Type card to Advocate and clicking Save Person preserves tenure history and birthdate (no more PATCH with tenures:[] / birthdate:null just because the Bench-only UI was unmounted)"
    requirement: "PEDIT-07"
    verification:
      - kind: unit
        ref: "grep structural gates: name=\"birthdate\"/name=\"tenures\" both precede {#if isJustice}; exactly one of each; svelte-check 0 errors / 16 warnings (baseline unchanged)"
        status: pass
      - kind: manual_procedural
        ref: "Open an existing Justice with tenure rows + birthdate, click Advocate, click Save Person, reload — tenure rows and birthdate unchanged (deferred to Phase 27 UAT retest per plan's explicit instruction)"
        status: unknown
    human_judgment: true
    rationale: "Plan explicitly defers the full click-through Save/reload round-trip to the Phase 27 UAT retest (consistent with the 27-07/08/09 gap-closure pattern); automated checks here only prove the structural precondition (input position/uniqueness), not the live PATCH round-trip against a running FastAPI + Postgres stack."
  - id: D2
    description: "After a merge redirect to /admin/people/{target_id} (soft navigation, reused component instance), the editor's tenureRows state re-derives from the target person's real tenures instead of retaining the stale pre-merge source person's rows"
    requirement: "PEDIT-07"
    verification:
      - kind: unit
        ref: "grep structural gates: tenureRows = (data.person.tenures re-derivation present exactly once in the reset effect (distinct from the $state initializer); nextKey = 1 reset present exactly once; svelte-check 0 errors / 16 warnings"
        status: pass
      - kind: manual_procedural
        ref: "Merge person A into person B, on the resulting /admin/people/{B} page click Save Person, reload — B's tenure rows are B's own, not A's (deferred to Phase 27 UAT retest)"
        status: unknown
    human_judgment: true
    rationale: "Plan explicitly defers this behavioral round-trip (merge → soft nav → Save → reload) to the Phase 27 UAT retest; it requires a live browser session against real merge data, which is outside the scope of static/structural checks."

duration: 5min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 10: Gap Closure (CR-01/CR-02) Summary

**Relocated the hidden birthdate/tenures save-form inputs outside the Bench/Advocate toggle's conditional, and completed the person-id-change reset effect to also re-derive tenureRows/nextKey — closing the two BLOCKER data-loss defects (CR-01, CR-02) that failed Phase 27's third verification pass.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-09T15:47:53Z
- **Completed:** 2026-07-09T15:49:47Z
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments
- Toggling an existing Justice to "Advocate" and clicking Save Person no longer deletes tenure history/birthdate — the hidden `birthdate`/`tenures` inputs are now always part of `save-form`, bound to the same `$state` the visible Bench UI edits, regardless of the toggle's current position (CR-01 closed).
- Saving on a post-merge `/admin/people/{target_id}` page no longer risks overwriting the target person's real tenures with a stale pre-merge source-person array — the person-id-change reset `$effect` now re-derives `tenureRows`/`nextKey` from `data.person.tenures` on every navigation, mirroring the existing `isJustice`/`birthdate` resets (CR-02 closed).
- The Bench-only slide-reveal (D-11) and Bench/Advocate segmented toggle (D-13) are unchanged and confirmed intact (`transition:slide` count still 1; visible Birth Date/Tenure Period UI still gated behind `{#if isJustice}`).

## Task Commits

Each task was committed atomically:

1. **Task 1: CR-01 — make the birthdate and tenures save-form inputs always present (outside the Bench-only conditional)** - `bbc135b9` (fix)
2. **Task 2: CR-02 — reset tenureRows/nextKey in the person-id-change $effect** - `b02a2681` (fix)

**Plan metadata:** committed separately as part of this summary/state update.

## Files Created/Modified
- `app/src/routes/admin/people/[id]/+page.svelte` — relocated hidden `birthdate`/`tenures` inputs outside `{#if isJustice}` (alongside the existing always-present `is_justice` hidden input); stripped `name`/`form` from the visible Birth Date input so it's a pure bind-only UI control; removed the now-redundant in-block hidden `tenures` input; extended the person-id-change reset `$effect` to reset `nextKey` and re-derive `tenureRows` from `data.person.tenures`.

## Decisions Made
- Placed the two relocated hidden inputs directly alongside the existing always-present `is_justice` hidden input (immediately before `{#if isJustice}`), per the plan's explicit instruction, rather than elsewhere in the card.
- Kept exactly one `name="birthdate"` input (the always-present hidden one) by stripping `name`/`form` from the visible date-picker rather than keeping both — matches the plan's exact-one-input acceptance gate.
- Mirrored the top-of-script `tenureRows` initializer's map callback verbatim inside the reset effect (same fields, same `?? ''` fallbacks, inline type annotation) rather than extracting a shared helper function, per the plan's explicit "do not create a second effect / do not change the initializer" constraint.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>` specs precisely; all automated `<verify>` gates passed on the first attempt with no additional fixes required.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both BLOCKER defects (CR-01, CR-02) from `27-REVIEW.md` are fixed; svelte-check passes with the unchanged baseline (0 errors, 16 warnings); the Bench-only slide-reveal and Bench/Advocate toggle remain intact.
- ROADMAP Success Criterion 4 / REQUIREMENTS.md PEDIT-07's "unchecking hides fields but does not delete tenure or appointment data" clause is now structurally satisfied — the remaining three behavioral round-trips (CR-01 toggle+save, CR-02 merge+save, and a fresh look at the slide-reveal animation now that its DOM contents changed slightly) are deferred to the Phase 27 UAT retest, per the plan's explicit scope and consistent with the 27-07/08/09 gap-closure pattern.
- Phase 27 should proceed to `/gsd-verify-work 27` (a 4th verification pass) to confirm Truth 4 / PEDIT-07 now passes and to close out the phase.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*
