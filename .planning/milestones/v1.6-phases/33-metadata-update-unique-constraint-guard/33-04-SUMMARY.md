---
phase: 33-metadata-update-unique-constraint-guard
plan: 04
subsystem: api
tags: [fastapi, svelte, duplicate-recovery, regression]
requires:
  - phase: 33-01
    provides: Stable duplicate_argument HTTP conflict contract
  - phase: 33-03
    provides: Shared accessible conflict alert and recovery link
provides:
  - Factual duplicate API copy shared by pre-check and race paths
  - Single-owner recovery-link wording with a cross-layer regression
affects: [admin-pipeline, admin-arguments, metadata-editing]
tech-stack:
  added: []
  patterns: [api-facts-component-actions, cross-layer-source-regression]
key-files:
  created: []
  modified: [api/routers/admin.py, api/tests/test_admin_arguments_routes.py, api/tests/test_question_number_nullable.py]
key-decisions:
  - "The API owns only factual duplicate pair copy; ArgumentDetailsCard owns the actionable recovery-link label."
patterns-established:
  - "Cross-layer copy composition tests assert each visible recovery phrase has exactly one owner."
requirements-completed: [PIPE-27]
coverage:
  - id: D1
    description: "Pre-check and named-constraint race responses return identical factual pair-identifying duplicate payloads."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_routes.py#test_metadata_duplicate_contract_from_service"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_routes.py#test_metadata_target_race_rolls_back_then_returns_winner"
        status: pass
    human_judgment: false
  - id: D2
    description: "The factual API message and shared component compose Open conflicting argument exactly once while safe recovery checks remain intact."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_question_number_nullable.py#test_duplicate_message_and_component_compose_one_recovery_phrase"
        status: pass
      - kind: unit
        ref: "api/tests/test_question_number_nullable.py#test_argument_details_card_restores_values_and_focuses_one_safe_alert"
        status: pass
      - kind: other
        ref: "npm --prefix app run check"
        status: pass
    human_judgment: false
duration: 4min
completed: 2026-07-14
status: complete
---

# Phase 33 Plan 04: Deduplicated Conflict Recovery Copy Summary

**Duplicate conflict responses now state only the colliding pair, leaving the shared component to render the actionable recovery link exactly once.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-14T15:47:00Z
- **Completed:** 2026-07-14T15:51:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Aligned service pre-check and named-constraint race payloads on identical factual duplicate copy.
- Preserved rollback ordering, winner lookup, structured conflict id, and unrelated-constraint sanitization.
- Added exact route assertions and a cross-layer regression proving the recovery-link phrase is rendered once.

## Task Commits

1. **Task 1: Give the component sole ownership of duplicate recovery link copy** - `ce6eb651`

## Files Created/Modified

- `api/routers/admin.py` - removes component-owned link wording from both duplicate payload builders.
- `api/tests/test_admin_arguments_routes.py` - asserts identical exact payloads for pre-check and race collisions.
- `api/tests/test_question_number_nullable.py` - proves API and component copy compose one recovery phrase while retaining safe alert assertions.

## Decisions Made

- Kept the backend message factual and pair-identifying; the existing shared component remains the sole owner of actionable link copy.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Existing Svelte warnings remain unchanged and `svelte-check` reports zero errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 33 gap closure is complete and ready for resumed UAT verification.

---
*Phase: 33-metadata-update-unique-constraint-guard*
*Completed: 2026-07-14*
