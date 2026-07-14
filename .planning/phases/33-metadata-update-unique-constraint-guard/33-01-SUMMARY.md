---
phase: 33-metadata-update-unique-constraint-guard
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, uniqueness]
requires:
  - phase: 23
    provides: argument source docket and question metadata
provides:
  - Race-safe final-pair uniqueness guard for metadata updates
  - Stable duplicate_argument HTTP conflict contract
  - Sanitized handling for unrelated database constraints
affects: [admin-arguments, metadata-editing]
tech-stack:
  added: []
  patterns: [shared uniqueness predicate, structured constraint classification]
key-files:
  created: [api/services/argument_uniqueness.py]
  modified: [api/services/admin_arguments.py, api/routers/admin.py, api/tests/test_admin_arguments_service.py, api/tests/test_admin_arguments_routes.py]
key-decisions:
  - "Only concrete docket/question pairs participate in the pre-check, matching PostgreSQL NULL uniqueness semantics."
  - "The raced final pair is attached structurally to IntegrityError before rollback so winner lookup uses submitted values."
patterns-established:
  - "Named database constraints are classified from structured driver attributes and cause chains, never message text."
requirements-completed: [PIPE-27]
coverage:
  - id: D1
    description: "Final concrete-pair collisions are detected with partial-save combination and self exclusion."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pre-check and raced constraint violations return the stable duplicate_argument contract while other constraints remain sanitized."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_routes.py"
        status: pass
    human_judgment: false
duration: 12min
completed: 2026-07-14
status: complete
---

# Phase 33 Plan 01: Metadata Update Unique Constraint Guard Summary

**Metadata saves now combine the final docket/question pair, reject known duplicates before update, and recover named PostgreSQL races through an exact sanitized 409 contract.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-14T12:34:00Z
- **Completed:** 2026-07-14T12:46:31Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added one shared parameterized pair lookup with self exclusion and PostgreSQL-compatible NULL behavior.
- Added a cycle-safe structured classifier for `uq_arguments_source_docket_question`.
- Locked normal, raced, and unrelated-constraint HTTP behavior with service and route tests.

## Task Commits

1. **RED: behavioral uniqueness contract tests** - `3247098c`
2. **Task 1: shared uniqueness primitives and service guard** - `09d7c528`
3. **Task 2: exact HTTP conflict mapping** - `f9afebdd`
4. **Race correction: preserve final pair across rollback** - `5503dc0e`

## Files Created/Modified

- `api/services/argument_uniqueness.py` - canonical pair lookup and constraint classifier.
- `api/services/admin_arguments.py` - combined final-pair pre-check and duplicate result.
- `api/routers/admin.py` - rollback-first target-race recovery and stable error payloads.
- `api/tests/test_admin_arguments_service.py` - partial, NULL, and classifier behavior.
- `api/tests/test_admin_arguments_routes.py` - exact conflict, rollback, race, and sanitization behavior.

## Decisions Made

- Retained PostgreSQL as the race authority; the service pre-check improves precision but does not replace the named constraint fallback.
- Preserved the submitted final pair on the structured exception because rollback restores stored values before winner lookup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved the submitted pair across rollback**
- **Found during:** Task 2
- **Issue:** Re-reading the argument after rollback would recover the old pair, not the pair that lost the race.
- **Fix:** Attached the final pair to the caught `IntegrityError` in the service and consumed it after router rollback.
- **Files modified:** `api/services/admin_arguments.py`, `api/routers/admin.py`, `api/tests/test_admin_arguments_routes.py`
- **Verification:** Target-race test asserts rollback occurs before winner lookup with the submitted pair.

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required for correct D-07 race recovery; no scope expansion.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

Phase complete and ready for verification or Phase 34 planning.

---
*Phase: 33-metadata-update-unique-constraint-guard*
*Completed: 2026-07-14*
