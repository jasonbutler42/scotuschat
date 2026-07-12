---
phase: 29-historical-corpus-import
plan: 09
subsystem: pipeline
tags: [sqlalchemy, integrityerror, corpus-import, dedup, asyncio]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import (plans 04/05)
    provides: import_convokit.py's _import_conversation entity-creation/dedup path this plan patches
provides:
  - "_next_question_number async helper deriving the next per-docket question_number"
  - "docket_question_conflict counter, distinct from conversations_errored, in per-batch summary"
  - "Explicit IntegrityError handling around the Argument flush (defense-in-depth safety net)"
  - "Regression tests proving reargued-case/PDF-overlap dockets no longer silently drop data"
affects: [29-historical-corpus-import verification, any future corpus-import gap-closure plan]

tech-stack:
  added: []
  patterns:
    - "Per-docket question_number derivation via select(func.max(...)).where(source_docket == ...) aligned to the DB's real UniqueConstraint"
    - "Explicit try/except IntegrityError around a flush, with session.rollback() + a distinct counter, as defense-in-depth alongside a proactive derivation"

key-files:
  created: []
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py

key-decisions:
  - "docket_question_conflict counted and printed distinctly from conversations_errored so an operator can tell a data-loss-prevented collision apart from an unrelated malformed-row error"
  - "IntegrityError handling kept as defense-in-depth only -- the primary fix is _next_question_number aligning the write path with the DB's real (source_docket, question_number) constraint before any flush is attempted"

patterns-established:
  - "When an app-level dedup check doesn't match a table's real UNIQUE constraint, derive the write value from the same columns the constraint covers, and add an explicit IntegrityError catch as a second layer -- never rely on a blanket except Exception to be the only safety net for a specific, anticipated collision"

requirements-completed: [CORPUS-03, CORPUS-08]

coverage:
  - id: D1
    description: "_next_question_number derives the next available question_number per source_docket (select max, +1, or 1 when none) so a reargued case or a PDF-ingested docket imports at question_number=2+ instead of colliding"
    requirement: "CORPUS-03"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py#test_docket_already_at_question_number_1_imports_at_question_number_2"
        status: pass
    human_judgment: false
  - id: D2
    description: "IntegrityError at the Argument flush is caught, rolled back, and counted in a distinct docket_question_conflict counter (never folded into conversations_errored), surfaced as its own labeled field in the per-batch summary"
    requirement: "CORPUS-08"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py#test_forced_collision_increments_docket_question_conflict_not_errored"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 09: Docket/Question Collision Gap Closure (CR-01) Summary

**Per-docket `question_number` derivation aligned with the DB's real `(source_docket, question_number)` UNIQUE constraint, plus a distinct `docket_question_conflict` counter and explicit `IntegrityError` safety net, so reargued cases and PDF-ingest-overlap dockets import instead of being silently dropped into `conversations_errored`.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-10T09:08Z (prior plan-metadata commit)
- **Completed:** 2026-07-10T09:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_next_question_number(session, source_docket)` queries `select(func.max(Argument.question_number)).where(Argument.source_docket == source_docket)` and returns `1` when no row exists, else `max + 1` -- this is exactly the `(source_docket, question_number)` pair `uq_arguments_source_docket_question` enforces, so the dedup logic and the DB's real uniqueness contract are now aligned.
- `_import_conversation`'s hardcoded `question_number=1` was replaced with the derived value, computed after the existing `oyez_transcript_id` idempotency short-circuit (so genuine re-runs still hit `skipped_existing` unchanged) and before the `Argument` is constructed.
- The `Argument` flush is now wrapped in `try/except IntegrityError` as a defense-in-depth safety net: on catch, `session.rollback()` clears the failed transaction, `counters["docket_question_conflict"]` increments, a distinct WARNING names the `conversation_id` and `source_docket`, and the function returns early -- `conversations_errored` is never touched by this path.
- `"docket_question_conflict"` was added to `_SUMMARY_COUNTER_KEYS` (auto-flows through `_new_counters`/`_accumulate_counters`) and rendered as its own `"N docket/question conflicts."` field in `_print_summary`, closing the CORPUS-08 visibility gap the verification flagged.
- Two new regression tests prove both documented CR-01 scenarios no longer silently drop data:
  - `test_docket_already_at_question_number_1_imports_at_question_number_2` pre-creates a PDF-ingested `Argument` at `question_number=1` for docket `55-71`, runs the corpus importer against a ConvoKit conversation for that same docket, and asserts the corpus record imports at `question_number=2` while the PDF row remains untouched.
  - `test_forced_collision_increments_docket_question_conflict_not_errored` monkeypatches `_next_question_number` to force a residual collision, and asserts (via `capsys`) the printed per-batch summary shows `1 docket/question conflicts` and `0 conversations errored`, with no corpus `Argument` row created.

## Task Commits

Each task was committed atomically:

1. **Task 1: Derive per-docket question_number + distinct docket_question_conflict counter with explicit IntegrityError handling** - `7bb1c5a2` (fix)
2. **Task 2: Regression tests for reargued/PDF-overlap docket collision** - `358a2357` (test)

**Plan metadata commit:** pending (this SUMMARY + STATE/ROADMAP update)

## Files Created/Modified

- `pipeline/commands/import_convokit.py` - Added `func`/`IntegrityError` imports, `_next_question_number` helper, replaced hardcoded `question_number=1`, wrapped the Argument flush in explicit `IntegrityError` handling, registered `docket_question_conflict` in the summary counter machinery and `_print_summary` output.
- `pipeline/tests/test_import_convokit_core.py` - Added 2 regression tests (`test_docket_already_at_question_number_1_imports_at_question_number_2`, `test_forced_collision_increments_docket_question_conflict_not_errored`) proving both CR-01 scenarios.

## Decisions Made

- Kept the blanket `except Exception` in `run_import_convokit` unchanged per the plan's explicit instruction -- it still guards genuinely unrelated malformed rows; the new `IntegrityError` handling intercepts the docket/question collision before it could ever reach that generic handler.
- Used `capsys` (not a `builtins.print` monkeypatch) to capture the per-batch summary text in Test B, matching the plan's suggested idiom and avoiding interference with pytest's own output capturing.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria (AST check for `_next_question_number`, grep counts for `docket_question_conflict`/`IntegrityError`/`func.max`, `py_compile`, and the full pytest run) were verified directly and passed without needing any Rule 1-4 deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01, the sole remaining BLOCKER gap from `29-VERIFICATION.md`, is closed: `_next_question_number` aligns the importer's dedup with the DB's real constraint, the `IntegrityError` safety net is in place, and `docket_question_conflict` is surfaced distinctly in the per-batch summary.
- `pipeline/tests/test_import_convokit_core.py` + `pipeline/tests/test_import_convokit_utterances.py` now show 29 passed (up from 27 at the prior verification pass) -- no regressions.
- `api/models/models.py`'s `uq_arguments_source_docket_question` constraint was read-only reference material for this plan and remains unmodified; Alembic remains the sole DDL authority.
- Ready for re-verification of Phase 29 (`/gsd:verify-work 29`) to confirm the CR-01 gap is formally closed and the phase can move to a `passed` verification status.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/tests/test_import_convokit_core.py
- FOUND: .planning/phases/29-historical-corpus-import/29-09-SUMMARY.md
- FOUND commit: 7bb1c5a2
- FOUND commit: 358a2357
