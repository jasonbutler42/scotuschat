---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 04
subsystem: database
tags: [postgres, sqlalchemy, asyncpg, data-cleanup, cli-script]

requires:
  - phase: 31-audit-stale-db-gated-test-fixtures (plan 01-03)
    provides: dedicated scotus_test DB isolation, session-scoped auto-reset, consolidated db_session fixture -- the root-cause fix that stops future leakage
provides:
  - "scripts/cleanup_leaked_test_rows.py -- standalone, dry-run-by-default remediation script for the already-leaked rows sitting in the shared dev DB"
affects: [31-audit-stale-db-gated-test-fixtures plan 08 (gated live execution of this script)]

tech-stack:
  added: []
  patterns:
    - "GROUP BY/HAVING COUNT(*) > 1 broad-sweep duplicate detection instead of a hardcoded id list"
    - "Survivor selection scored by (court_tenures linkage, non-null bio field count, -id) tuple comparison, lowest-id only as last-resort tie-break"
    - "Re-run detection immediately before a gated destructive action and abort if the candidate set drifted since the report was printed"
    - "FK-safe delete cascade for Argument rows extended from api/services/admin_arguments.py::delete_argument's documented order, plus argument_status_log"

key-files:
  created:
    - scripts/cleanup_leaked_test_rows.py
    - .planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md
  modified: []

key-decisions:
  - "Person duplicate survivor selection scores court_tenures linkage first, then non-null bio field count, then lowest id as a documented last resort -- never blindly keep-lowest-id (D-06)"
  - "Orphan-Argument detection combines two independent signals (no linked utterances+pipeline_runs, and synthetic case_name/docket_number pattern match) rather than only one, per D-05's broad-sweep requirement"
  - "Deliberately excluded job-{id} source_docket values from the orphan/pattern match -- that is a legitimate production placeholder for in-progress admin-job arguments, not test leakage"
  - "Non-survivor Person deletes reassign dependent FKs (court_tenures, case_appearances, argument_participants, utterances, speaker_alias) to the survivor rather than deleting or cascading through them, so real dependent data is never destroyed (T-31-11)"
  - "Execute path re-runs detection inside the same transaction as the deletes and aborts if the candidate set changed since the dry-run report, closing the TOCTOU gap between reporting and deleting (T-31-02)"

patterns-established:
  - "Standalone scripts/*.py remediation tools follow the same DATABASE_URL placeholder guard as api/tests/conftest.py::_db_configured -- copy verbatim, do not simplify to bool(url)"

requirements-completed: [TEST-01]

coverage:
  - id: D1
    description: "Dry-run (no flag) prints the full survivor/candidate breakdown for every duplicate Person group and every orphaned/test-fixture Argument, and deletes nothing"
    requirement: "TEST-01"
    verification:
      - kind: manual_procedural
        ref: "python scripts/cleanup_leaked_test_rows.py (run live against the shared dev DB during this session) -- printed 6 duplicate Person groups (19 delete candidates) and 48 orphaned Argument candidates; people/arguments counts unchanged at 352/211 before and after"
        status: pass
    human_judgment: false
  - id: D2
    description: "Detection is a broad sweep (GROUP BY/HAVING on people.full_name, LEFT JOIN-based orphan detection on arguments), not a hardcoded list of the 5 known KBJ ids"
    requirement: "TEST-01"
    verification:
      - kind: manual_procedural
        ref: "Live dry-run found 6 duplicate groups (not just the 1 KBJ group) totaling 19 candidates, and 48 orphaned Argument rows, against the real dev DB"
        status: pass
    human_judgment: false
  - id: D3
    description: "Survivor selection for each duplicate Person group is chosen by real tenure/bio data, not blindly by lowest id"
    requirement: "TEST-01"
    verification:
      - kind: manual_procedural
        ref: "Live dry-run output: Ketanji Brown Jackson group (ids 116, 959, 1097, 1204, 1285) selected id=116 as survivor with reason 'has 1 linked court_tenures row(s)'; other groups with no distinguishing data fell back to lowest id with an explicit documented reason string"
        status: pass
    human_judgment: false
  - id: D4
    description: "Deletion only occurs when an explicit --execute flag is passed, and even then requires an interactive confirmation token (or --yes/--force) plus a fresh re-detection check before any DELETE runs"
    requirement: "TEST-01"
    verification:
      - kind: manual_procedural
        ref: "python scripts/cleanup_leaked_test_rows.py --execute with a deliberately mismatched confirmation ('abort' typed against expected '67') -- printed 'Confirmation did not match -- aborting. No rows deleted.'; people/arguments counts unchanged at 352/211 after"
        status: pass
      - kind: unit
        ref: "python -c ast.parse(...) static check: '--execute' present, TRUNCATE/DROP TABLE/DROP DATABASE absent from the file"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live deletion against the shared dev DB is deliberately NOT executed in this plan -- deferred to Plan 08's operator-authorization checkpoint"
    verification: []
    human_judgment: true
    rationale: "This plan's critical constraint explicitly forbids running a live deletion here; confirming the actual cleanup lands correctly requires the human-gated --execute run in Plan 08, which this plan does not perform."

duration: 20min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 04: Cleanup Script for Leaked Test Rows Summary

**Standalone `scripts/cleanup_leaked_test_rows.py` — dry-run-by-default script that broadly detects duplicate `Person` rows and orphaned/test-fixture `Argument` rows in the shared dev DB, picks survivors by real tenure/bio data, and gates all deletion behind `--execute` plus an interactive confirmation.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-13
- **Tasks:** 2 completed
- **Files modified:** 1 created (`scripts/cleanup_leaked_test_rows.py`), 1 deferred-items note created

## Accomplishments
- Broad-sweep detection for duplicate `Person.full_name` groups via `GROUP BY`/`HAVING COUNT(*) > 1` — not a hardcoded list of the 5 known Ketanji Brown Jackson ids (D-05)
- Survivor selection per group scored by linked `court_tenures` count, then non-null bio field count, falling back to lowest id only when a group is genuinely indistinguishable, with the chosen reason printed for operator review (D-06)
- Orphan-Argument detection combining two signals: no linked `utterances`/`pipeline_runs`, and synthetic case_name/docket_number pattern matching (`Synthetic...`, `...TEST...`) drawn from the actual test-fixture conventions in `api/tests/*.py` — deliberately excludes the legitimate `job-{id}` production placeholder
- Gated `--execute` deletion path: refuses to run without `DATABASE_URL` (or against a placeholder value), re-runs detection immediately before deleting and aborts on any drift from the dry-run set, requires an explicit confirmation token (or `--yes`/`--force`), reassigns dependent FKs to the survivor before deleting non-survivor Person rows, and deletes orphan Arguments via the same FK-ordered cascade as `admin_arguments.py::delete_argument` (extended to also cover `argument_status_log`, which that function's cascade omits) plus now-orphaned `Case` rows
- Verified end-to-end against the live shared dev DB in dry-run mode (Task 1 `done` criterion) and confirmed the `--execute` confirmation gate aborts safely with zero deletions on a mismatched token (Task 2 `done` criterion) — row counts stayed at the documented baseline (352 people, 211 arguments) throughout

## Task Commits

Each task was committed atomically:

1. **Task 1: Build detection + dry-run reporting (D-04, D-05, D-06)** - `fbc68ca3` (feat)
2. **Task 2: Add gated deletion path with safety guards (D-04, D-08)** - `60b72c27` (feat)

**Plan metadata:** committed in this final SUMMARY/STATE/ROADMAP commit

## Files Created/Modified
- `scripts/cleanup_leaked_test_rows.py` - standalone remediation script: detection, survivor selection, dry-run reporting, and gated deletion for leaked test rows in the shared dev DB
- `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md` - logs an out-of-scope discovery (see Issues Encountered)

## Decisions Made
- Person duplicate survivor selection uses a `(tenure_count, bio_field_count, -id)` comparison tuple rather than a simple if/else chain, so ties fall through cleanly to the documented lowest-id fallback
- Orphan-Argument detection is OR-combined (orphan signal OR pattern match) rather than AND-combined, matching D-05's literal "AND/OR" phrasing, since the two signals catch different classes of leaked rows (pipeline-committed-then-abandoned vs. directly-inserted-by-test)
- The execute path's stale-set check compares candidate id sets (not full row content) between the dry-run pass and the transaction-scoped re-detection pass — sufficient to catch drift (new leaks appearing, or the operator's approved set becoming outdated) without over-engineering a full row diff
- Cleanup of now-orphaned `Case` rows is scoped narrowly to cases exclusively linked to a just-deleted candidate Argument (checked via a `case_arguments` remaining-count query after the join-row delete), not a fresh independent sweep for orphaned Cases in general — kept the script's blast radius tied to what D-05 explicitly asked for (Person duplicates + orphaned Arguments)

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria and `done` conditions were met without requiring any Rule 1-4 deviation to the plan's own scope.

## Issues Encountered

**Out-of-scope discovery (logged, not fixed):** While designing the FK-safe delete cascade for orphan Arguments (Task 2), found that `api/services/admin_arguments.py::delete_argument` — the existing production delete path — does not delete `argument_status_log` rows before deleting the `arguments` row, even though `argument_status_log.argument_id` is a `NOT NULL` FK with no `ondelete` clause (defaults to `RESTRICT` in Postgres), and every DRAFT argument approved through the normal job flow gets at least one status log row at creation. This looks like a latent `ForeignKeyViolation` bug in unrelated production code, not something caused by this plan's changes. `api/services/admin_arguments.py` is not in this plan's `files_modified`, so per the executor's scope-boundary rule it was not fixed here — logged to `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md` instead, with a suggested one-line fix. `scripts/cleanup_leaked_test_rows.py` itself correctly deletes `argument_status_log` rows in its own cascade, so this script is unaffected by the gap.

## User Setup Required

None — no external service configuration required. The script reads the existing `DATABASE_URL` env var already configured in `.env` for this project; no new setup needed.

## Next Phase Readiness

- `scripts/cleanup_leaked_test_rows.py` is built, verified against the live shared dev DB in dry-run mode, and its `--execute` confirmation/abort path is verified safe — ready for Plan 08's gated, operator-authorized live execution.
- Plan 08 should be aware the live dry-run in this session found 6 duplicate Person groups (19 delete candidates, not just the 5 KBJ rows) and 48 orphaned/test-fixture Argument candidates — larger than the 5+"some" estimate in 31-CONTEXT.md's "Specific Ideas". No action needed now; just context for whoever runs `--execute` in Plan 08.
- The `admin_arguments.py::delete_argument` FK gap noted above is unrelated to this plan's deliverable and does not block Plan 08, but is available in `deferred-items.md` for a future fix/regression test.

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: scripts/cleanup_leaked_test_rows.py
- FOUND: .planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md
- FOUND: fbc68ca3 (Task 1 commit)
- FOUND: 60b72c27 (Task 2 commit)
