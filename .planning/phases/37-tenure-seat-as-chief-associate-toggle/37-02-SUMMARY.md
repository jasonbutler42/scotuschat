---
phase: 37-tenure-seat-as-chief-associate-toggle
plan: "02"
subsystem: database
tags: [postgresql, alembic, sqlalchemy, migration, audit]
requires:
  - phase: 37-01
    provides: migration safety regression harness
provides:
  - nullable seat-to-office rename revision
  - immutable reviewed-report normalization CLI
  - named binary office check and NOT NULL contraction
affects: [37-03, 37-04, 37-05, court-tenures]
tech-stack:
  added: []
  patterns: [expand-audit-contract migration, canonical JSON digest, transactional drift guard]
key-files:
  created:
    - alembic/versions/0020_rename_tenure_seat_to_office.py
    - scripts/migrate_tenure_offices.py
    - alembic/versions/0021_constrain_tenure_office.py
  modified: []
key-decisions:
  - "Execution consumes an immutable database-bound report as the sole audited row set."
  - "The database constraint is installed only after a preflight proves every office canonical."
patterns-established:
  - "Expand-audit-contract: preserve legacy readability, normalize explicitly, then constrain."
  - "Migration writes revalidate the complete reviewed row set under locks before the first update."
requirements-completed: [PEOPLE-08]
coverage:
  - id: D1
    description: Legacy tenure values survive the reversible seat-to-office rename unchanged.
    requirement: PEOPLE-08
    verification:
      - kind: integration
        ref: "tests/test_migrate_tenure_offices.py#test_rename_revision_only_renames_nullable_string_column"
        status: pass
    human_judgment: false
  - id: D2
    description: Reviewed reports drive explicit drift-safe all-or-none normalization.
    requirement: PEOPLE-08
    verification:
      - kind: integration
        ref: ".venv Python pytest tests/test_migrate_tenure_offices.py"
        status: pass
    human_judgment: false
  - id: D3
    description: Normalized storage is restricted to non-null chief or associate values.
    requirement: PEOPLE-08
    verification:
      - kind: integration
        ref: "tests/test_migrate_tenure_offices.py#test_final_revision_preflights_then_adds_named_check_and_not_null"
        status: pass
    human_judgment: false
duration: 18min
completed: 2026-07-15
status: complete
---

# Phase 37 Plan 02: Tenure Office Storage Migration Summary

**Reversible rename, integrity-protected audit normalization, and post-normalization binary Office constraint**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-15T19:00:00Z
- **Completed:** 2026-07-15T19:18:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added a rename-only Alembic expansion that preserves nullable arbitrary legacy values.
- Added a deterministic SHA-256-reviewed report workflow with explicit resolutions, database identity, complete-set drift detection, row locks, bound updates, and one transaction.
- Added a contraction revision that refuses unresolved data before installing a named two-value check and NOT NULL invariant.

## Task Commits

1. **Task 1: Add rename-only Alembic revision** - `d3221d1e` (feat)
2. **Task 2: Implement audited dry-run and atomic execution CLI** - `d37aac05` (feat)
3. **Task 3: Contract the schema only after normalization** - `8377b95f` (feat)

## Files Created/Modified

- `alembic/versions/0020_rename_tenure_seat_to_office.py` - Nullable string-compatible column rename and reversal.
- `scripts/migrate_tenure_offices.py` - Immutable audit report, explicit resolution, and atomic execution workflow.
- `alembic/versions/0021_constrain_tenure_office.py` - Preflight, named check constraint, and NOT NULL contraction.

## Decisions Made

- Database identity is represented as a one-way SHA-256 fingerprint of the PostgreSQL database name, excluding connection strings and credentials from reports.
- Resolution input must match the unresolved id set exactly; extra, missing, or noncanonical resolutions are rejected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected constant-time digest comparison module**
- **Found during:** Task 2 focused verification
- **Issue:** The initial implementation referenced `compare_digest` from `hashlib`, where it is unavailable.
- **Fix:** Imported `hmac` and used `hmac.compare_digest`.
- **Files modified:** `scripts/migrate_tenure_offices.py`
- **Verification:** Focused migration CLI tests and the complete 28-test module pass.
- **Committed in:** `d37aac05`

---

**Total deviations:** 1 auto-fixed bug
**Impact on plan:** Correctness fix only; no scope expansion.

## Issues Encountered

- Pytest temporary-directory creation and git index locking required approved execution outside the restricted Windows token sandbox.
- The normal patch wrapper briefly hit the split writable-root restriction; the two-line compatibility correction was applied as a scoped approved edit.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 37-03 can rename the ORM and strict API write contracts to `office` against the staged storage contract.
- No blockers remain for subsequent Phase 37 plans.

## Self-Check: PASSED

- All three production artifacts exist.
- Task commits `d3221d1e`, `d37aac05`, and `8377b95f` exist.
- `tests/test_migrate_tenure_offices.py`: 28 passed.

---
*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Completed: 2026-07-15*
