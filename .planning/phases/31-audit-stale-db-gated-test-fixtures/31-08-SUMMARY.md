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
  - "No deletion performed in Task 1 -- dry-run only, per D-04 and the blocking-human checkpoint (T-31-18)"
  - "Operator reviewed the Task 1 dry-run report and typed 'approved'; fresh re-detection immediately before --execute matched the authorized set exactly (6 groups / 25 Person rows / 56 Argument rows / 81 total), so no drift-abort was needed"

patterns-established: []

requirements-completed: [TEST-01]

coverage: []

# Metrics
duration: 25min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 08: Cleanup dry-run + operator-authorized destructive cleanup Summary

**Operator-authorized `scripts/cleanup_leaked_test_rows.py --execute` removed the 81 leaked rows (25 duplicate Person rows across 6 name groups including 6 Ketanji Brown Jackson rows, 56 orphaned Argument rows) from the shared dev DB; `python -m pipeline import-justices` and a full `pytest -q` run both completed cleanly afterward, confirming success criterion 4.**

## Performance

- **Duration:** ~25 min total (Task 1 ~10 min dry-run + Task 2 ~15 min operator-authorized execute + smoke checks)
- **Started:** 2026-07-13T00:00:00Z (approx, see git log for exact commit timestamps)
- **Tasks:** 2 of 2 completed
- **Files modified:** 0 source files (this SUMMARY.md is the only file either task produces; all mutation was data-only against the shared dev DB, not source code)

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

## Task 2: Operator-Authorized Destructive Cleanup + Criterion-4 Smoke

**Operator response: "approved"** (received after reviewing the Task 1 dry-run report above).

### Pre-execute re-verification

Before running `--execute`, a fresh dry-run was run to confirm the candidate set had not drifted since the operator reviewed the report. Result matched exactly: 6 duplicate Person groups, 25 Person delete candidates, 56 orphaned Argument candidates, 81 total. No drift -- proceeded to execute with the authorized count.

### Execute run

Command: `python scripts/cleanup_leaked_test_rows.py --execute` (confirmation prompt supplied with `81`, matching the total candidate count).

The script re-ran detection inside the delete transaction (its built-in TOCTOU guard) and confirmed the in-transaction candidate set still matched the pre-execute set before deleting. All 25 duplicate Person rows were deleted (dependent `court_tenures`/`case_appearances`/`argument_participants`/`utterances`/`speaker_alias` rows reassigned to each group's survivor first, per D-06/T-31-11) and all 56 orphaned Argument rows were deleted (with their dependent `utterances`/`pipeline_runs`/`argument_participants`/`argument_status_log`/`case_arguments` rows and any now-orphaned `cases` rows).

Output tail:

```
Deleted Person ids [1066, 1173, 1254, 1358] (dependents reassigned to survivor 928).
... (54 more "Deleted Argument id ..." lines omitted for brevity, full list matches
the 56 orphan ids in the Task 1 dry-run report above) ...

Deletion committed. Final counts -- people: 333, arguments: 163.
Compare against the pre-cleanup baseline noted in 31-CONTEXT.md (352 people, 211 arguments).
```

**Post-cleanup row counts:** people=333 (358 - 25 = 333), arguments=163 (219 - 56 = 163). Both deltas match the authorized candidate counts exactly.

### Criterion-4 smoke: `import-justices`

Command: `python -m pipeline import-justices`

```
Done — 0 people created, 0 people upgraded to is_justice=True, 0 court_tenures created (0 rows skipped).
```

Completed cleanly with **no `MultipleResultsFound` and no other leaked-data-caused error** — success criterion 4 confirmed. (0/0/0 is expected: the surviving Ketanji Brown Jackson row, id 116, already carries the linked `court_tenures` row that made it the D-06 survivor, so there was nothing left to create/upgrade.)

### Optional full-suite re-run

Command: `python -m pytest -q`

```
429 passed, 5 xfailed in 62.56s (0:01:02)
```

Full suite green, no leak-guard failures raised by the `pytest_sessionstart`/`pytest_sessionfinish` hooks (Plan 07). A follow-up read-only COUNT query confirmed `people`/`arguments` counts held stable at 333/163 after the full test run, i.e. the leak-guard hooks correctly prevented any new leakage during this run.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run the cleanup dry-run against the shared dev DB and capture candidates** - 321f4995 (this SUMMARY.md; no source files modified -- dry-run only)
2. **Task 2: Operator-authorized destructive cleanup + import-justices criterion-4 smoke** - checkpoint task; data-only mutation against the shared dev DB (no source files modified); recorded in the final metadata commit for this plan

## Files Created/Modified

- `.planning/phases/31-audit-stale-db-gated-test-fixtures/31-08-SUMMARY.md` - this report (dry-run findings + operator-authorized execution results)

## Decisions Made

- None beyond D-04 (dry-run by default), D-05 (broad-sweep detection), D-06 (survivor selection), and T-31-02 (execute-path re-detection guards against a stale candidate set) -- all already locked in 31-CONTEXT.md and implemented in Plan 04's script. This plan only ran the existing script (dry-run, then operator-authorized execute) and recorded its output; no script changes were needed.

## Deviations from Plan

None - both tasks executed exactly as written. The fresh pre-execute re-verification (required by this plan's `<critical_constraint>`) found the candidate set unchanged from the Task 1 dry-run, so no divergence report was needed and execution proceeded as authorized.

## Issues Encountered

**Live leakage had grown beyond the 31-CONTEXT.md baseline** (documented in Task 1): the dry-run found 81 total candidate rows across 6 duplicate Person name groups plus 56 orphaned Argument rows, not just the originally-documented 5 KBJ duplicates, and row counts (358/219) were higher than the 352/211 baseline. This was expected given the leak was "confirmed currently active" and pytest runs during Plans 31-05/06/07 occurred before the leak-guard hooks (Plan 07) became fully effective. The operator reviewed this expanded scope and authorized cleanup of the full 81-row set — no rows outside the reported set were touched, and no real/production Person row was misidentified as a deletion candidate (every survivor was verified in the Task 1 report to be the row with linked `court_tenures`/bio data, or the documented lowest-id fallback for the four clearly-synthetic test-fixture name groups).

## Next Phase Readiness

TEST-01 is complete. The shared dev DB is clean (333 people / 163 arguments, no duplicate `full_name` groups, no orphaned Argument rows matching the detection sweep), `import-justices` runs clean, and a full pytest run confirms no new leakage. `scripts/cleanup_leaked_test_rows.py` remains available as a standalone, re-runnable tool (per D-07) if leakage is ever detected again in the future — it is not registered as a pipeline CLI subcommand since it is a one-time/as-needed maintenance script, not part of the production ingest pipeline.

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13 -- both tasks complete, operator-authorized destructive cleanup executed and verified*

## Self-Check: PASSED

- FOUND: `.planning/phases/31-audit-stale-db-gated-test-fixtures/31-08-SUMMARY.md`
- FOUND: commit `321f4995` (Task 1 dry-run capture)
