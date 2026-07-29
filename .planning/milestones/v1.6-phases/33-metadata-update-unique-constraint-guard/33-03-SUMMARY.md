---
phase: 33-metadata-update-unique-constraint-guard
plan: 03
subsystem: ui
tags: [sveltekit, svelte, accessibility, duplicate-recovery]
requires:
  - phase: 33-01
    provides: Stable duplicate_argument HTTP conflict contract
provides:
  - Identical value-preserving duplicate recovery on both admin metadata actions
  - Shared focused conflict alert with safe navigation to the winning argument
affects: [admin-pipeline, admin-arguments, metadata-editing]
tech-stack:
  added: []
  patterns: [defensive action-boundary parsing, update-tick-focus recovery]
key-files:
  created: []
  modified: [app/src/routes/admin/pipeline/[job_id]/+page.server.ts, app/src/routes/admin/arguments/[id]/+page.server.ts, app/src/lib/components/ArgumentDetailsCard.svelte, api/tests/test_question_number_nullable.py]
key-decisions:
  - "Only a non-empty duplicate_argument message with a positive integer conflict id crosses the FastAPI-to-SvelteKit boundary."
  - "A returned argued_date field is detected by property presence so an attempted blank date overrides loaded data."
patterns-established:
  - "Failed enhanced forms update state, await Svelte tick, then focus the single inline alert."
requirements-completed: [PIPE-27]
coverage:
  - id: D1
    description: "Both admin actions preserve dockets, question number, and argued date while accepting only the structured duplicate contract."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_question_number_nullable.py#test_metadata_actions_validate_duplicate_contract_and_preserve_attempted_values"
        status: pass
    human_judgment: false
  - id: D2
    description: "The shared card restores attempted values and focuses one safe conflict alert linking to the winning argument."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_question_number_nullable.py#test_argument_details_card_restores_values_and_focuses_one_safe_alert"
        status: pass
      - kind: other
        ref: "npm --prefix app run check"
        status: pass
    human_judgment: true
    rationale: "Keyboard focus landing and new-tab behavior still require the planned two-route browser check."
duration: 3min
completed: 2026-07-14
status: complete
---

# Phase 33 Plan 03: Accessible Duplicate Recovery Summary

**Both admin metadata editors now preserve attempted values and guide keyboard users from a sanitized duplicate response to the conflicting argument.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-14T12:49:59Z
- **Completed:** 2026-07-14T12:52:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Aligned both SvelteKit actions on one defensive 409 contract while preserving every submitted metadata value on all failures.
- Restored returned docket, question, and blank-or-concrete date values in the shared card.
- Added update-then-tick focus recovery and a positive-integer-derived, noopener/noreferrer conflict link.

## Task Commits

1. **RED: focused duplicate recovery contracts** - `83d9c789`
2. **Task 1: preserve metadata duplicate recovery state** - `b09be342`
3. **Task 2: focus shared duplicate conflict alert** - `de3084fd`

## Files Created/Modified

- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - validates duplicate responses and echoes attempted values.
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - mirrors the pipeline action contract for direct editing.
- `app/src/lib/components/ArgumentDetailsCard.svelte` - restores values and focuses the shared safe conflict alert.
- `api/tests/test_question_number_nullable.py` - focused source-contract regression for both actions and the shared component.

## Decisions Made

- Required the conflict id to be a positive integer before constructing a local navigation path.
- Used property-presence testing for `argued_date`, because null is a meaningful attempted blank rather than absence of returned state.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Existing Svelte warnings remain unchanged and `svelte-check` reports zero errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 33 is ready for final phase verification after the remaining plan summary is present. The planned two-route keyboard/value browser check remains human UAT.

---
*Phase: 33-metadata-update-unique-constraint-guard*
*Completed: 2026-07-14*
