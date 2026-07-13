---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 08
subsystem: database
tags: [postgresql, sqlalchemy, data-cleanup, dev-db]

# Dependency graph
requires:
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 04)
    provides: scripts/cleanup_leaked_test_rows.py (dry-run + --execute cleanup script)
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 07)
    provides: leak-guard hooks and DB-gated fixture fixes that stopped new leakage
provides:
  - Verbatim dry-run report of every leaked-row deletion candidate in the shared dev DB, for operator review at the Task 2 checkpoint
affects: [31-audit-stale-db-gated-test-fixtures]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "No deletion performed in this task -- dry-run only, per D-04 and the blocking-human checkpoint (T-31-18)"

patterns-established: []

requirements-completed: []  # TEST-01 not yet complete -- destructive execution (Task 2) is still pending operator authorization

coverage: []

# Metrics
duration: 10min
completed: 2026-07-13
status: checkpoint
---

# Phase 31 Plan 08: Cleanup dry-run + blocking checkpoint Summary

**Dry-run of `scripts/cleanup_leaked_test_rows.py` against the shared dev DB found 81 leaked rows (25 duplicate Person rows across 6 name groups, 56 orphaned Argument rows) -- larger than the 5-row KBJ baseline recorded in 31-CONTEXT.md; execution is paused at the Task 2 blocking-human checkpoint pending operator authorization.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-13T00:00:00Z (approx, see git log for exact commit timestamp)
- **Tasks:** 1 of 2 completed (Task 2 is a blocking-human checkpoint, intentionally not executed)
- **Files modified:** 0 source files (dry-run only; this SUMMARY.md is the only file this task produces)

## Accomplishments

- Confirmed `DATABASE_URL` points at the shared dev DB (`scotus` on `localhost:5432`), not `scotus_test` or `TEST_DATABASE_URL`.
- Ran `python scripts/cleanup_leaked_test_rows.py` (no flags -- dry-run, zero deletes) and captured the full verbatim report below.
- Confirmed current row counts: **358 people, 219 arguments** -- grown from the 352/211 baseline recorded in 31-CONTEXT.md on 2026-07-13, consistent with ongoing test leakage during Plans 31-05/06/07 execution before the leak-guard hooks (Plan 07) were fully effective.
- Confirmed the 5 originally-known KBJ duplicate ids (116, 959, 1097, 1204, 1285) all appear in the `Ketanji Brown Jackson` group, plus **one additional leaked KBJ row (id 1389)** not in the original discussion baseline -- exactly one survivor (id 116, chosen for its linked `court_tenures` row) is selected per D-06.

## Verbatim Dry-Run Output

Command: `python scripts/cleanup_leaked_test_rows.py` (run from repo root, `DATABASE_URL` pointed at the shared dev DB, no flags -- dry-run is the default, zero deletes)

```
======================================================================
DUPLICATE PERSON GROUPS
======================================================================

full_name='Advocate Example' ids=[962, 1100, 1207, 1288, 1392]
  SURVIVOR: id=962 (no distinguishing tenure/bio data on any row in group -- fell back to lowest id)
  DELETE CANDIDATES: [1100, 1207, 1288, 1392]

full_name='Bench Example' ids=[963, 1101, 1208, 1289, 1393]
  SURVIVOR: id=963 (no distinguishing tenure/bio data on any row in group -- fell back to lowest id)
  DELETE CANDIDATES: [1101, 1208, 1289, 1393]

full_name='John Smith' ids=[960, 1098, 1205, 1286, 1390]
  SURVIVOR: id=960 (no distinguishing tenure/bio data on any row in group -- fell back to lowest id)
  DELETE CANDIDATES: [1098, 1205, 1286, 1390]

full_name='Justice Example' ids=[961, 1099, 1206, 1287, 1391]
  SURVIVOR: id=961 (no distinguishing tenure/bio data on any row in group -- fell back to lowest id)
  DELETE CANDIDATES: [1099, 1206, 1287, 1391]

full_name='Ketanji Brown Jackson' ids=[116, 959, 1097, 1204, 1285, 1389]
  SURVIVOR: id=116 (has 1 linked court_tenures row(s))
  DELETE CANDIDATES: [959, 1097, 1204, 1285, 1389]

full_name='Status Log Advocate' ids=[928, 1066, 1173, 1254, 1358]
  SURVIVOR: id=928 (no distinguishing tenure/bio data on any row in group -- fell back to lowest id)
  DELETE CANDIDATES: [1066, 1173, 1254, 1358]

======================================================================
ORPHANED / TEST-FIXTURE ARGUMENT CANDIDATES
======================================================================

argument id=358 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=359 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=384 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=438 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=439 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=464 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=518 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=519 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=544 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=761 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=762 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=787 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=841 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=842 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=867 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=972 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=973 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=978 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1018 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1019 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1023 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1024 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1029 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1046 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1146 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1147 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1152 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1192 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1193 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1197 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1198 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1203 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1288 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1289 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1294 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1334 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1335 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1339 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1340 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1345 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1405 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1406 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1411 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1451 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1452 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1456 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1457 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1462 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1548 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1549 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1554 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1594 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1595 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1599 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1600 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

argument id=1605 case_name=None docket_number=None
  REASON: orphan: no linked utterances and no linked pipeline_runs

======================================================================
SUMMARY
======================================================================
  Duplicate Person groups found: 6
  Person rows marked for deletion: 25
  Orphaned/test-fixture Argument candidates: 56
  Total rows marked for deletion: 81

Dry-run complete -- no rows deleted. Pass --execute to delete the candidates above.
```

**Pre-cleanup row counts (captured separately via a read-only COUNT query, same DATABASE_URL):** people=358, arguments=219.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run the cleanup dry-run against the shared dev DB and capture candidates** - (this SUMMARY.md; no source files modified -- dry-run only, see commit hash in final metadata commit)

**Task 2 (blocking-human checkpoint) has NOT been executed.** No destructive `--execute` run and no `import-justices` smoke run have occurred. This SUMMARY reflects only the Task 1 dry-run.

## Files Created/Modified

- `.planning/phases/31-audit-stale-db-gated-test-fixtures/31-08-SUMMARY.md` - this dry-run report, for operator review at the Task 2 checkpoint

## Decisions Made

- None beyond D-04 (dry-run by default) and D-06 (survivor selection), both already locked in 31-CONTEXT.md and implemented in Plan 04's script -- this task only ran the existing script and recorded its output.

## Deviations from Plan

None - Task 1 executed exactly as written (dry-run only, zero deletes, verbatim output captured).

## Issues Encountered

**Live leakage has grown beyond the 31-CONTEXT.md baseline.** The dry-run found 81 total candidate rows (25 duplicate Person rows across 6 name groups: "Advocate Example", "Bench Example", "John Smith", "Justice Example", "Ketanji Brown Jackson", "Status Log Advocate" -- plus 56 orphaned Argument rows), not just the originally-documented 5 KBJ duplicates. Current row counts (358 people / 219 arguments) are also higher than the 352/211 baseline recorded on 2026-07-13. This is consistent with the CONTEXT's own note that the leak was "confirmed currently active" and with ongoing pytest runs during Plans 31-05/06/07 execution before the leak-guard hooks (Plan 07) became fully effective. This is not a bug in the detection script -- it is expected given the timeline, and is exactly what the broad-sweep detection (D-05) was designed to catch. Flagged clearly for the operator at the Task 2 checkpoint; no action taken beyond reporting.

## Next Phase Readiness

Blocked on the Task 2 blocking-human checkpoint (T-31-18): the operator must review the dry-run report above, confirm no real Person row (i.e., no survivor) is misidentified as a deletion candidate, then explicitly authorize the destructive `--execute` run. Task 2 also requires running `python -m pipeline import-justices` immediately after to confirm success criterion 4 (no `MultipleResultsFound`). Until "approved" is received, no further action will be taken against the shared dev DB.

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: Task 1 only, 2026-07-13 -- Task 2 pending operator authorization*
