---
phase: 48-trust-lifecycle
plan: 02
subsystem: database
tags: [sqlalchemy, postgresql, pytest, fk-cascade, admin-arguments]

requires:
  - phase: 48-trust-lifecycle
    plan: 01
    provides: "D-03's candidate-birth-logging design (every argument gets an argument_status_log row from birth), which makes this carried defect reachable for every argument"
provides:
  - "delete_argument's FK-ordered cascade now deletes argument_status_log rows before deleting the Argument row (D-22 fix)"
  - "A permanent CI regression test proving the defect was real and the fix works (test_delete_argument_cascades_argument_status_log, test_delete_argument_cascades_multiple_status_log_rows)"
  - "test_delete_argument_still_refuses_candidate locking D-05 (delete gate stays DRAFT-only)"
  - "Corrected docstrings in api/services/admin_arguments.py and scripts/delete_fixture_argument.py that no longer claim a DRAFT argument cannot carry a status-log row, or reference the retired PIPELINE status"
affects: ["48-03 and later plans in this phase that land TRUST-03's candidate-birth status-log write — the delete path they now make reachable is proven safe"]

actuals:
  tokens: 3974
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Failing-then-passing regression test written and run BEFORE the fix (D-22) — the test's first run is the live repro, captured verbatim in the test file as a comment block, not asserted from reading the code"

key-files:
  created: []
  modified:
    - api/tests/test_admin_arguments_service.py
    - api/services/admin_arguments.py
    - scripts/delete_fixture_argument.py

key-decisions:
  - "The two new cascade tests use a try/finally cleanup pattern so a failed assertion mid-test still removes any leftover Argument/ArgumentStatusLog rows, keeping the rootdir conftest.py shared-dev-DB row-count tripwire green even on a red run."
  - "test_delete_argument_still_refuses_candidate was added as a new, explicit CANDIDATE-status case rather than repurposing the existing test_delete_argument_returns_false_for_pipeline test — the plan explicitly required keeping the PIPELINE case as the dead-value regression fixture rather than deleting it."

requirements-completed: [TRUST-03]

coverage:
  - id: D1
    description: "delete_argument deletes every argument_status_log row for the argument before deleting the Argument row, so a DRAFT argument carrying status-log history deletes successfully instead of raising ForeignKeyViolation."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_multiple_status_log_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "A regression test exists that fails against the pre-fix cascade and passes against the fixed one — the defect is proven by execution, not asserted by reading."
    requirement: "TRUST-03"
    verification:
      - kind: other
        ref: "pytest run captured verbatim in api/tests/test_admin_arguments_service.py's comment block above the cascade tests: 2 failed with sqlalchemy.exc.IntegrityError / ForeignKeyViolationError on argument_status_log_argument_id_fkey, pre-fix; 2 passed, post-fix"
        status: pass
    human_judgment: false
  - id: D3
    description: "The DRAFT-only delete gate is unchanged (D-05): a candidate argument still returns False from delete_argument."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_still_refuses_candidate"
        status: pass
    human_judgment: false
  - id: D4
    description: "The false comment at scripts/delete_fixture_argument.py claiming a DRAFT argument can never carry a status-log row is corrected, and the stale status == pipeline reference is updated to status == candidate."
    requirement: "TRUST-03"
    verification:
      - kind: other
        ref: "python -c AST check: ast.get_docstring(...) does not contain 'can never have one' and does contain 'candidate'"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 02: Close the delete_argument -> argument_status_log Cascade Defect Summary

**A one-line fix (`delete(ArgumentStatusLog)` before the final `Argument` delete) closing a carried FK-cascade defect that D-03's candidate-birth-logging design was about to make reachable for every argument, proven by a failing-then-passing regression test that captured the live `ForeignKeyViolationError` verbatim before the fix landed.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 complete
- **Files modified:** 3

## Accomplishments
- Wrote three new DB-gated tests FIRST, confirmed two of them fail with a live `ForeignKeyViolationError`-derived `IntegrityError` against the pre-fix service (the actual, previously-missing live repro — captured verbatim as a comment block in the test file), and confirmed the third (`test_delete_argument_still_refuses_candidate`) passes both before and after the fix.
- Added the missing cascade step to `delete_argument` — `delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id).execution_options(synchronize_session=False)` — placed as the new step 5, between `CaseArgument` deletion and the `AdminJob` NULL-out, renumbering the two steps that follow (6 and 7) and updating the docstring's ordered cascade list and gate description to match.
- Corrected the docstring in `scripts/delete_fixture_argument.py` that falsely claimed "a DRAFT argument can never have [an argument_status_log row]" — the exact false claim that let this defect survive three milestones per the ROADMAP write-up — and updated its stale "status == pipeline" reference to the now-correct "status == candidate" (Phase 48 D-01).
- Full suite green afterward: 1117 passed, 5 xfailed, 0 failed — no new failures, and the shared dev-DB row-count tripwire was unaffected throughout (both the pre-fix red run and the post-fix green run).

## Task Commits

Each task was committed atomically:

1. **Task 1: Prove the defect — failing regression test for the missing cascade step** - `fe34cb19c` (test)
2. **Task 2: Land the cascade step and correct the false comment** - `a94723c7f` (fix)

**Plan metadata:** (this commit) — `docs(48-02): complete plan`

## Files Created/Modified
- `api/tests/test_admin_arguments_service.py` - Added `test_delete_argument_cascades_argument_status_log`, `test_delete_argument_cascades_multiple_status_log_rows`, and `test_delete_argument_still_refuses_candidate`, plus a comment block recording the pre-fix live repro output (Task 1)
- `api/services/admin_arguments.py` - `delete_argument` gains the `delete(ArgumentStatusLog)` cascade step (new step 5) and an updated docstring naming `CANDIDATE` as the born state and `argument_status_log` as a required (not defensive) cascade step (Task 2)
- `scripts/delete_fixture_argument.py` - Corrected the false "can never have one" claim and the stale "status == pipeline" reference in the module docstring (Task 2)

## Decisions Made
- Cleanup in the two new cascade tests uses `try`/`finally` rather than relying on the test's own success path, so a failed assertion mid-test (e.g., if a future regression reintroduces the defect) still leaves the shared `scotus_test` database in a clean state for the rootdir `conftest.py` row-count tripwire.
- Kept `test_delete_argument_returns_false_for_pipeline` unchanged and added a distinct `test_delete_argument_still_refuses_candidate` test rather than repurposing the pipeline test, per the plan's explicit instruction to preserve the retired-enum-value regression fixture.

## Deviations from Plan

None - plan executed exactly as written. The flagged assumption in `<flagged_assumptions>` (that the pre-fix run might come back green, indicating the defect doesn't reproduce as described) did not occur — the defect reproduced exactly as the ROADMAP's static analysis predicted, with the exact `ForeignKeyViolationError` on `argument_status_log_argument_id_fkey` named in the plan's `<behavior>` block.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The cascade defect that D-03 (Phase 48 Plan 01) deliberately made reachable for every argument is now closed and permanently regression-tested. Any later plan in this phase that lands candidate-birth status-log writes (making `delete_argument` reachable on freshly-born arguments once they become DRAFT) inherits a proven-safe delete path.
- The DRAFT-only delete gate (D-05) is explicitly locked and unaffected — later plans widening deletion to candidates are out of scope for this phase (deferred to Phase 50) and this plan's tests will catch any accidental gate-widening regression.
- Full suite baseline for subsequent plans in this phase: 1117 passed, 5 xfailed, 0 failed, 0 skipped.

## Self-Check: PASSED

- FOUND: api/tests/test_admin_arguments_service.py
- FOUND: api/services/admin_arguments.py
- FOUND: scripts/delete_fixture_argument.py
- FOUND commit: fe34cb19c
- FOUND commit: a94723c7f

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
