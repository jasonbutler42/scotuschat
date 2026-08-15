---
phase: 42-corpus-import-fidelity-diff-fix
plan: 02
subsystem: pipeline
tags: [sqlalchemy, postgres, corpus-import, delete-cascade, pytest]

# Dependency graph
requires:
  - phase: 42-corpus-import-fidelity-diff-fix
    plan: 01
    provides: "--conversation-id scoped import path on import-convokit; conversation 15169 landed in the dev database as the phase's diff/fix target"
provides:
  - "scripts/delete_fixture_argument.py — operator-run offline routine that deletes one corpus-imported argument (any status, not just DRAFT) and its full FK-ordered dependent-row cascade in a single transaction, addressed by conversation id"
  - "A proven delete-then-reimport round trip for conversation 15169, with before/after per-table counts matching exactly"
affects: [42-03-corpus-import-fidelity-diff-fix, 42-04-corpus-import-fidelity-diff-fix, 42-05-corpus-import-fidelity-diff-fix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A new offline delete routine mirrors an existing admin service's FK-cascade order exactly, but is a wholly separate script rather than a wrapper/subclass, when the existing service's status gate cannot be safely reused or weakened for a different use case"
    - "Session.begin_nested() (SAVEPOINT) wraps a test's session-under-test when the test needs to assert a mid-operation exception rolled back writes already made earlier in the same operation, without losing the test's own already-flushed (uncommitted) seed data to that same rollback"

key-files:
  created:
    - scripts/delete_fixture_argument.py
    - pipeline/tests/test_delete_fixture_argument.py
    - .planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md
  modified: []

key-decisions:
  - "The routine is a standalone script, never importing api/services/admin_arguments.py::delete_argument, so its DRAFT-only gate is neither reused nor weakened for this dev/audit use case"
  - "--delete-case defaults off and, when set, only removes the case row when no OTHER argument's case_arguments row still links to it (checked after the fixture's own case_arguments row is deleted) — a defensive check beyond what the fixture's current state requires, per RESEARCH.md Assumptions Log A2"
  - "The whole resolve+report+cascade sequence lives inside exactly one get_session() block so a mid-cascade exception rolls back every prior step of the same cascade, not just the failing statement"

requirements-completed: [CORPUS-14]

coverage:
  - id: D1
    description: "scripts/delete_fixture_argument.py deletes one corpus-imported argument (status=pipeline, not DRAFT) and its full dependent-row cascade in one transaction, scoped strictly by a looked-up argument id"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_destructive_delete_clears_full_cascade_no_fk_violation"
        status: pass
      - kind: e2e
        ref: "real dev DB: delete_fixture_argument.py --conversation-id 15169 --delete-case --yes (argument, case, and all dependent rows confirmed gone; people/court_tenures unchanged)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The routine refuses on zero or multi Argument matches and deletes nothing in either case"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_zero_match_returns_nonzero_and_deletes_nothing"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_multi_match_returns_nonzero_and_deletes_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "Report-only mode (no --yes) prints the same per-table inventory as destructive mode and deletes nothing"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_report_only_default_deletes_nothing"
        status: pass
      - kind: e2e
        ref: "real dev DB: delete_fixture_argument.py --conversation-id 15169 (no --yes) — arguments count stayed at 166"
        status: pass
    human_judgment: false
  - id: D4
    description: "--delete-case retains a case still linked to another argument, and removes a case with no other link"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_delete_case_retains_case_when_another_argument_still_links_to_it"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_delete_case_removes_case_when_only_the_fixture_links_to_it"
        status: pass
    human_judgment: false
  - id: D5
    description: "Person rows are never deleted by the routine, regardless of flags"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_person_row_survives_delete"
        status: pass
      - kind: e2e
        ref: "real dev DB: people count unchanged at 343 across the destructive delete-and-reimport round trip"
        status: pass
    human_judgment: false
  - id: D6
    description: "A mid-cascade exception rolls back every step of that cascade, including ones already executed earlier in the same cascade — no partial deletion is ever left behind"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_delete_fixture_argument.py::test_single_transaction_rollback_on_mid_cascade_failure"
        status: pass
    human_judgment: false
  - id: D7
    description: "The delete-then-reimport round trip against the real conversation-15169 fixture reproduces every per-table count exactly (utterances, argument_participants, pipeline_runs, case_arguments, question_number), proving CORPUS-14's fix-then-reverify cycle works before any importer fix is written"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: "real dev DB round trip: snapshot -> delete --delete-case --yes -> re-import --conversation-id 15169 -> re-snapshot; all counts identical (see Round-Trip Evidence below)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Two concurrent scoped imports of the same conversation id never both create an Argument row"
    verification: []
    human_judgment: true
    rationale: "Flagged as `verification: backstop` in the plan's must_haves — no concurrency harness exists in this codebase to exercise two simultaneous imports against the same conversation id; the DB's own (source_docket, question_number) UNIQUE constraint is the actual backstop (an IntegrityError from a genuine race would surface as a docket_question_conflict counter increment, per Phase 29 CR-01), but this plan did not build or run a concurrency test to prove it. Left for a human to judge whether that existing DB-level constraint is sufficient assurance."

# Metrics
duration: 26min
completed: 2026-07-30
status: complete
---

# Phase 42 Plan 2: Fixture Delete-and-Reimport Routine Summary

**A purpose-built `scripts/delete_fixture_argument.py` deletes a `status=pipeline` corpus argument and its full FK-ordered dependent cascade in one transaction (bypassing the admin API's DRAFT-only gate without weakening it), and the delete-then-reimport round trip against the real conversation-15169 fixture reproduced every per-table count exactly.**

## Performance

- **Duration:** 26 min
- **Started:** 2026-07-30T16:23:15Z (per STATE.md `last_updated` after Plan 01)
- **Completed:** 2026-07-30T16:49:55Z
- **Tasks:** 3 completed
- **Files modified:** 2 created (1 script, 1 test file); 0 modified (Task 3 found no defect to fix)

## Accomplishments
- Built `scripts/delete_fixture_argument.py`: an operator-run, conversation-id-addressed delete routine that clears one corpus-imported argument and every dependent row (utterances, pipeline_runs, argument_participants, case_arguments, argument_status_log, admin_jobs.argument_id NULLed) in exactly one transaction — mirroring `api/services/admin_arguments.py::delete_argument`'s FK cascade order without reusing, subclassing, or weakening its DRAFT-only gate.
- Refuses to run on zero or multi conversation-id matches; report-only by default (prints the exact per-table inventory it would delete); `--yes` opts into destruction; `--delete-case` removes the linked case row only when no *other* argument still links to it.
- Added 9 automated tests (`pipeline/tests/test_delete_fixture_argument.py`) covering cascade completeness, argument-id scoping between two independent fixtures, zero/multi-match refusal, report-only default, the case-link retain/delete guard, person-row safety, and single-transaction rollback on an injected mid-cascade failure. Full `pipeline/tests/` suite green (207 passed, 5 xfailed).
- Proved the full delete-then-reimport round trip against the real dev database's conversation-15169 fixture: deleted the argument and its case, re-imported via Plan 01's `--conversation-id` flag, and every per-table count matched the pre-delete snapshot exactly — including `question_number` correctly returning to 1 and all 17 people matching (reused), not recreated.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fixture delete routine with FK-ordered, id-scoped, single-transaction cascade** - `ca216ef9` (feat)
2. **Task 2: Automated coverage for the delete routine** - `b77300d4` (test)
3. **Task 3: Prove the delete-and-reimport round trip against the real fixture** - no code change (round trip found no defect to fix); results recorded below and in this SUMMARY's frontmatter

_No `docs: complete plan` metadata commit exists yet — that follows this SUMMARY._

## Files Created/Modified
- `scripts/delete_fixture_argument.py` - New operator-run script. `--conversation-id` (required), `--delete-case` (opt-in), `--yes` (destructive opt-in). Resolves the Argument via `.all()` (not `scalar_one_or_none`) so multi-match is detectable rather than raising; reports an identical per-table inventory in both report-only and destructive modes; runs the whole cascade inside one `get_session()` block.
- `pipeline/tests/test_delete_fixture_argument.py` - 9 tests. Reuses the `isolated_session`/`_make_session_cm` pattern from `test_import_convokit_core.py`; adds a `_make_savepoint_session_cm` helper (wraps the session in a SAVEPOINT via `session.begin_nested()`) specifically for the single-transaction-rollback test, so an injected mid-cascade exception can be proven to undo earlier cascade steps without also discarding the test's own seed data.
- `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` - New. Logs one pre-existing, unrelated test failure found while running the full suite as a sanity check (see Issues Encountered) — not fixed here per the scope-boundary rule.

## Round-Trip Evidence (Task 3)

Pre-delete snapshot (conversation 15169, real dev DB):

| Metric | Value |
|---|---|
| Argument id | 1860 |
| question_number | 1 |
| status | pipeline |
| source_docket | 642 |
| Case id (docket 642, term 1966) | 700 |
| utterances | 480 |
| argument_participants | 17 |
| pipeline_runs | 1 |
| case_arguments | 1 |
| argument_status_log | 0 |
| admin_jobs | 1 |
| Global `arguments` | 166 |
| Global `people` | 343 |
| Global `court_tenures` | 123 |
| `cases` where term_year=1966 | 1 |

Destructive delete (`--conversation-id 15169 --delete-case --yes`): argument, case, and all dependent rows confirmed at 0 immediately afterward; `people` (343) and `court_tenures` (123) unchanged.

Re-import (`python -m pipeline import-convokit --conversation-id 15169`) printed: `1 arguments created, 0 arguments skipped (already imported), 1 cases created, 467 utterances created, 13 stage-direction utterances created, 0 people created, 17 people matched (reused), 0 speakers flagged, 0 conversations errored, 0 utterance rows errored, 0 docket/question conflicts, 1 unattributed speakers skipped.`

Post-re-import snapshot:

| Metric | Value | Matches pre-delete? |
|---|---|---|
| Argument id | 1861 (new row, expected) | n/a — new PK |
| question_number | 1 | ✓ identical |
| status | pipeline | ✓ identical |
| source_docket | 642 | ✓ identical |
| Case id | 701 (new row, expected) | n/a — new PK |
| utterances | 480 | ✓ identical |
| argument_participants | 17 | ✓ identical |
| pipeline_runs | 1 | ✓ identical |
| case_arguments | 1 | ✓ identical |
| argument_status_log | 0 | ✓ identical |
| admin_jobs | 1 | ✓ identical |
| Global `arguments` | 166 | ✓ identical |
| Global `people` | 343 | ✓ identical (0 created, 17 matched/reused) |
| Global `court_tenures` | 123 | ✓ identical |
| `cases` where term_year=1966 | 1 | ✓ identical |

**Explicit statement:** every per-table count matched exactly. The only differences are the new Argument/Case primary keys themselves (1860→1861, 700→701), which are expected since delete-then-reimport necessarily creates fresh rows. No importer-side discrepancy was surfaced by this round trip — nothing to hand off as an input to Plan 03's diff document from this task.

The closing report-only run (`--conversation-id 15169`, no `--yes`) printed an inventory identical in shape to the pre-delete inventory (same field names, same counts: utterances=480, pipeline_runs=1, argument_participants=17, case_arguments=1, argument_status_log=0), and the fixture remains present in the database at the end of this plan, as the plan's own overall `<verification>` requires for Plan 03 to diff.

## Decisions Made
- The routine is a wholly separate script from `api/services/admin_arguments.py::delete_argument` — never imported, subclassed, or patched — so that service's DRAFT-only gate stays intact for the admin UI while this offline routine targets `status=pipeline` corpus fixtures by design.
- `--delete-case`'s other-link check runs strictly after the fixture's own `case_arguments` row is deleted (matching the plan's literal instruction), so the count of "other" links correctly reflects only rows belonging to a different argument.
- Followed every other point in the plan's `<action>` sections as written (cascade order, `.all()` resolution style, single `get_session()` block, per-table reporting shape).

## Deviations from Plan

None - plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed. Task 3's round trip found no importer or delete-routine defect requiring a fix.

## Issues Encountered
- While running the full test suite (`pytest -q`, beyond the plan's own `pipeline/tests/ -q` gate) as a sanity check, 4 pre-existing, unrelated errors surfaced in `api/tests/test_phase38_people_ui_contract.py` — a Node.js-backed contract test failing on a mangled WSL/Windows path (`ENOENT` on a concatenated-not-joined path). This is unrelated to either of this plan's files and was not caused by this plan's changes; logged to `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` per the scope-boundary rule rather than fixed here. `pipeline/tests/ -q` — the plan's actual verification gate — is fully green (207 passed, 5 xfailed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Conversation 15169 is left present in the dev database (Argument id 1861, Case id 701) with counts matching Plan 01's originally recorded shape — ready for Plan 03's fidelity diff to read against.
- The delete-then-reimport mechanism this plan built is now available and proven for Plan 04's "fix, then re-verify" cycle (CORPUS-14): any importer fix can be applied, the fixture deleted via this routine, and re-imported cleanly to confirm the fix, exactly as this task just demonstrated with zero code changes.
- No blockers. `pipeline/tests/` is fully green (207 passed, 5 pre-existing xfailed, unrelated to this plan). One pre-existing, unrelated full-suite failure logged to `deferred-items.md` for a future session that owns the WSL/Windows Node.js test path issue.

---
*Phase: 42-corpus-import-fidelity-diff-fix*
*Completed: 2026-07-30*

## Self-Check: PASSED

- FOUND: scripts/delete_fixture_argument.py
- FOUND: pipeline/tests/test_delete_fixture_argument.py
- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/42-02-SUMMARY.md
- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md
- FOUND commit: ca216ef9 (Task 1)
- FOUND commit: b77300d4 (Task 2)
