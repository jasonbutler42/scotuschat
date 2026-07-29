---
phase: 37-tenure-seat-as-chief-associate-toggle
plan: "01"
subsystem: testing
tags: [pytest, node-test, migration-safety, accessibility, tdd]

requires:
  - phase: 37-tenure-seat-as-chief-associate-toggle
    provides: D-01 through D-17 context, research, validation, patterns, and UI contract
provides:
  - Collectable RED contract for reviewed, integrity-protected, atomic tenure-office migration
  - Parseable Office radio, invalid-state, focus, serialization, and recovery contract
affects: [37-02, 37-03, 37-04, 37-05, tenure-office-migration, people-editor]

tech-stack:
  added: []
  patterns: [Wave 0 collectable RED harnesses, static source contracts, canonical report digest assertions]

key-files:
  created:
    - tests/test_migrate_tenure_offices.py
    - app/tests/tenure-office.browser.test.mjs
  modified: []

key-decisions:
  - "Wave 0 tests fail at execution rather than collection when Phase 37 production artifacts are absent."
  - "Native same-name radio semantics are the executable accessibility baseline for Office selection."

patterns-established:
  - "Migration safety: a reviewed canonical report is immutable input to an explicit drift-checked transaction."
  - "Editor recovery: invalid Office state remains unselected, associated, focusable, and rehydrated with all edits."

requirements-completed: [PEOPLE-08]

coverage:
  - id: D1
    description: Migration safety and audit behavior are specified before production changes.
    requirement: PEOPLE-08
    verification:
      - kind: integration
        ref: ".venv Python pytest tests/test_migrate_tenure_offices.py --collect-only -q"
        status: pass
    human_judgment: false
  - id: D2
    description: Office selection, invalid-state focus, serialization, and failed-save recovery are specified.
    requirement: PEOPLE-08
    verification:
      - kind: automated_ui
        ref: "node --check app/tests/tenure-office.browser.test.mjs"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-15
status: complete
---

# Phase 37 Plan 01: Wave 0 Regression Harnesses Summary

**Collectable migration-integrity and Office-control RED contracts covering irreversible normalization, accessibility, and failed-save recovery**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-15T18:30:00Z
- **Completed:** 2026-07-15T18:50:58Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added 28 collectable pytest cases covering canonical mapping, unresolved blockers, immutable reviewed-report integrity, explicit resolution, drift detection, atomic rollback, staged constraints, and downgrade ordering.
- Added a dependency-free Node contract for native Office radios, keyboard semantics, 44px styling, invalid legacy state, first-invalid focus, hidden JSON, and failed-save rehydration.
- Kept missing Phase 37 production artifacts as intentional RED execution failures without breaking collection or syntax validation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Specify staged migration and atomic audit behavior** - `eb61f719` (test)
2. **Task 2: Specify Office control and failed-save recovery behavior** - `a090daa4` (test)

## Files Created/Modified

- `tests/test_migrate_tenure_offices.py` - Migration utility, report integrity, transaction, and Alembic staging contract.
- `app/tests/tenure-office.browser.test.mjs` - Accessible Office interaction and form recovery contract.

## Decisions Made

- Used runtime artifact assertions instead of module-level imports so missing Wave 2 production files produce named RED failures rather than collection errors.
- Required native same-name radios as the preferred keyboard/idempotence contract while retaining radiogroup fallback recognition for the container.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced stale browser-test analog with the current repository harness**
- **Found during:** Task 2
- **Issue:** `app/tests/required-metadata.browser.test.mjs` no longer exists in the checkout.
- **Fix:** Followed the active `app/tests/case-required-recovery.browser.test.mjs` and dependency-free Node test conventions while preserving every 37-UI-SPEC assertion.
- **Files modified:** `app/tests/tenure-office.browser.test.mjs`
- **Verification:** `node --check app/tests/tenure-office.browser.test.mjs`
- **Committed in:** `a090daa4`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test coverage and scope are unchanged; only the obsolete analog was replaced.

## Issues Encountered

- The first task commit hit Windows `.git/index.lock` permission friction; retrying the same scoped stage/commit with approved permissions succeeded.
- The plan's `api/tests/test_cleanup_leaked_test_rows.py` analog was absent; the production safety script and Phase 37 pattern map supplied the intended contract.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 37-02 can implement the two Alembic revisions and migration utility directly against the named RED contract.
- Later editor plans can make the Node contract executable against the completed Svelte implementation without adding a UI dependency.

## Self-Check: PASSED

- Both created files exist.
- Task commits `eb61f719` and `a090daa4` exist.
- Migration tests collect 28 cases; the Node harness passes syntax validation.

---
*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Completed: 2026-07-15*
