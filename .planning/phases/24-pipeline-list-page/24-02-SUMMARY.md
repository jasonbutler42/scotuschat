---
phase: 24-pipeline-list-page
plan: 02
subsystem: ui
tags: [svelte5, runes, component-extraction, form-serialization]

# Dependency graph
requires:
  - phase: 24-pipeline-list-page (plan 01)
    provides: pipeline jobs list backend cap removal (no direct coupling, same phase)
provides:
  - Shared DocketPillInput.svelte component encapsulating docket pill state/UI
affects: [24-pipeline-list-page plan 03 (ArgumentDetailsCard refactor), 24-pipeline-list-page plan 04 (New Run form wiring)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Self-contained pill/tag input component: no change event emitted, parent reads serialized values via FormData.getAll(name) on submit"
    - "Component omits its own <label>; exposes an id prop so the parent's <label for=id> can target the internal text input"

key-files:
  created: [app/src/lib/components/DocketPillInput.svelte]
  modified: []

key-decisions:
  - "id prop defaults to 'docket-input' to preserve ArgumentDetailsCard's existing label/for wiring; list page can override to avoid duplicate-id conflicts"

patterns-established:
  - "Docket pill extraction pattern: $state array + addPill()/removePill() + one hidden input per pill, rendered even when readonly"

requirements-completed: [PLIST-02]

coverage:
  - id: D1
    description: "DocketPillInput.svelte component exists with initialValues, name, readonly, and id props, reproducing ArgumentDetailsCard's pill add/remove/serialize behavior"
    requirement: "PLIST-02"
    verification:
      - kind: unit
        ref: "node content-assertion script (initialValues/name/readonly/$props/addPill/removePill/type=\"hidden\"/preventDefault all present)"
        status: pass
      - kind: unit
        ref: "npx svelte-check --tsconfig ./tsconfig.json --threshold error"
        status: pass
    human_judgment: false

# Metrics
duration: 2min
completed: 2026-07-07
status: complete
---

# Phase 24 Plan 02: Shared DocketPillInput Component Summary

**Extracted a standalone `DocketPillInput.svelte` Svelte 5 Runes component from `ArgumentDetailsCard.svelte`'s inline pill logic, ready for reuse on both the job detail page (Plan 03) and the New Run form (Plan 04).**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-07T13:55:48Z
- **Completed:** 2026-07-07T13:56:59Z
- **Tasks:** 1 completed
- **Files modified:** 1

## Accomplishments
- Created `app/src/lib/components/DocketPillInput.svelte` — self-contained pill/tag input with `initialValues`, `name`, `readonly`, and `id` props
- Carried pill add/remove/serialize behavior verbatim from `ArgumentDetailsCard.svelte`: `addPill()` trims and silently rejects empty/duplicate values; `removePill(value)` filters the array; one hidden `<input type="hidden" {name} value={pill}>` per pill
- Component renders no internal `<label>` — parent owns the label via `for`/`id` per D-03/D-06 and RESEARCH Pattern 1
- `readonly` mode disables the text input and hides remove buttons while still rendering hidden inputs for existing pills

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DocketPillInput.svelte extracted from ArgumentDetailsCard pill logic** - `6659687d` (feat)

**Plan metadata:** _pending final commit_

## Files Created/Modified
- `app/src/lib/components/DocketPillInput.svelte` - New shared pill/tag docket input component (props: `initialValues`, `name`, `readonly`, `id`)

## Decisions Made
- `id` prop defaults to `'docket-input'`, matching the id `ArgumentDetailsCard.svelte` already uses for its `<label for="docket-input">`, so Plan 03's refactor requires no label changes. The New Run form (Plan 04) can pass a distinct `id` if both pill inputs ever render on the same page simultaneously.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `svelte-check` reported a pre-existing warning class (`state_referenced_locally` on `let pills = $state<string[]>(initialValues);`) that also exists in the source component (`ArgumentDetailsCard.svelte` has the identical pattern with `savedValues.dockets`) — this is expected per the plan's instruction to carry the state initialization verbatim, is a warning (not an error), and does not affect behavior since `initialValues` is only read once at mount by design (props are not intended to update pills reactively after mount, matching existing behavior).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `DocketPillInput.svelte` is ready to be imported by `ArgumentDetailsCard.svelte` (Plan 03) and `+page.svelte` (Plan 04)
- No blockers for Plan 03 or Plan 04

---
*Phase: 24-pipeline-list-page*
*Completed: 2026-07-07*
