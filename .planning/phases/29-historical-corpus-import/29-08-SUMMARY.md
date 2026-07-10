---
phase: 29-historical-corpus-import
plan: 08
subsystem: pipeline
tags: [pipeline-run, corpus-import, regression-test, data-contract]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import
    provides: import_convokit.py's single-run corpus import orchestrator (29-04/29-05)
provides:
  - "pipeline/commands/import_convokit.py's per-argument PipelineRun now writes step=\"parse\", matching api/services/arguments.py's established read-side contract"
  - "Regression assertions proving this contract cannot silently regress"
  - "End-to-end proof that corpus-imported utterances are retrievable via get_argument_with_utterances / GET /arguments/{id}/utterances"
affects: [29-verification, 29-review, admin-arguments, public-arguments]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A single combined pipeline run must be labeled by the read-side contract's expected value (step=\"parse\"), not by when in the import order it happens to run"

key-files:
  created: []
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py
    - pipeline/tests/test_import_convokit_utterances.py

key-decisions:
  - "Relabeled the write side (import_convokit.py's PipelineRun.step) rather than adding a second query branch to the shared read-side contract in api/services/arguments.py -- the corpus importer's single run IS the run that produced the Utterance rows, so it must carry the value that contract already expects everywhere else"
  - "No PipelineRun row was added or removed; no migration required (step is a free-text String(50) column, not an enum)"
  - "New end-to-end test calls get_argument_with_utterances directly (no HTTP client, no api.main import), avoiding the documented pre-existing FastAPI test lifespan/session-factory failure, consistent with 29-07's established pattern"

patterns-established:
  - "A pipeline stage that performs the combined work of multiple PDF-pipeline stages must be labeled by the semantic meaning consumers expect (step=\"parse\" = \"the run that owns this argument's utterances\"), not by its position in that pipeline's own internal ordering"

requirements-completed: [CORPUS-03, CORPUS-07]

coverage:
  - id: D1
    description: "pipeline/commands/import_convokit.py's PipelineRun creation writes step=\"parse\", not step=\"ingest\""
    requirement: "CORPUS-07"
    verification:
      - kind: unit
        ref: "grep -n 'step=\"parse\"' pipeline/commands/import_convokit.py -- exactly one match; 'step=\"ingest\"' -- zero matches"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_creates_case_argument_caseargument_pipelinerun_entities"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_every_utterance_has_pipeline_run_id_and_unique_sequence"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_argument_with_utterances (and therefore GET /arguments/{id}/utterances) returns the actual, non-empty, correctly-ordered, correctly-attributed Utterance rows for a corpus-imported Argument, and ArgumentUtterancesResponse(**result) constructs successfully"
    requirement: "CORPUS-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_utterances_readable_via_arguments_service_after_import"
        status: pass
    human_judgment: false
  - id: D3
    description: "The PDF-ingest pipeline's separate ingest/parse/resolve PipelineRun contract (ingest.py, parse.py, resolve.py) and admin_jobs.py's get_run_id_for_step/get_job/resolve_job are unaffected"
    requirement: "n/a (scope confirmation)"
    verification:
      - kind: other
        ref: "git diff --stat against api/services/arguments.py, api/services/admin_jobs.py, pipeline/commands/ingest.py, pipeline/commands/parse.py, pipeline/commands/resolve.py -- empty"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 08: Relabel corpus importer PipelineRun.step to "parse" Summary

**`pipeline/commands/import_convokit.py`'s single per-argument `PipelineRun` now writes `step="parse"` instead of `step="ingest"`, and a new end-to-end test proves `get_argument_with_utterances` now returns the actual, non-empty, correctly-attributed `Utterance` rows for a corpus-imported argument — closing the gap 29-07-PLAN.md's own regression test explicitly left open.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-10T08:10:00-05:00
- **Completed:** 2026-07-10T08:16:20-05:00
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `import_convokit.py`'s `_import_conversation` now creates its single `PipelineRun` with `step="parse"` (was `step="ingest"`), matching `api/services/arguments.py`'s established `step == "parse"` read-side filter.
- Rewrote the explanatory comment above the `PipelineRun(...)` construction to state the rationale (labeled by function — the run that writes this argument's `Utterance` rows — not by import order).
- Added regression assertions to the two existing pipeline tests that already query this row without checking `step`: `test_import_convokit_core.py::test_creates_case_argument_caseargument_pipelinerun_entities` and `test_import_convokit_utterances.py::test_every_utterance_has_pipeline_run_id_and_unique_sequence`.
- Added a new end-to-end test, `test_utterances_readable_via_arguments_service_after_import`, that runs the real `run_import_convokit` write path and the real `get_argument_with_utterances` read path against the same fixture, asserting `len(result["utterances"]) == 3`, correct ordering/attribution (raw_speaker_label, text, side, is_stage_direction) for all three rows, and a successful `ArgumentUtterancesResponse(**result)` round-trip.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relabel the corpus importer's PipelineRun.step to match the established "utterances-owning run" contract** - `b7467715` (fix)
2. **Task 2: End-to-end regression test proving corpus-imported utterances are actually retrievable** - `e8d7c285` (test)

**Plan metadata:** (pending — see final commit below)

## Files Created/Modified
- `pipeline/commands/import_convokit.py` — `PipelineRun(...)` construction in `_import_conversation` now writes `step="parse"`; comment rewritten to explain the rationale.
- `pipeline/tests/test_import_convokit_core.py` — added `assert run.step == "parse"` to `test_creates_case_argument_caseargument_pipelinerun_entities`.
- `pipeline/tests/test_import_convokit_utterances.py` — added `assert run.step == "parse"` to `test_every_utterance_has_pipeline_run_id_and_unique_sequence`; added new test `test_utterances_readable_via_arguments_service_after_import` (module-level imports for `ArgumentUtterancesResponse` and `get_argument_with_utterances` added).

## Decisions Made
- Fixed the write side (`import_convokit.py`), not the read side (`api/services/arguments.py`) — the corpus importer's single run genuinely IS the run that produced the `Utterance` rows for that argument, so the minimal-blast-radius fix is correcting what string it stamps, not adding a second query branch to a contract three other consumers already rely on (`get_argument_with_utterances`, `admin_jobs.get_run_id_for_step`, and the PDF pipeline's own `parse.py`).
- Confirmed by inspection (not assumption) that `api/services/admin_jobs.py`'s `get_run_id_for_step`/`get_job`/`resolve_job` are unaffected: every call site resolves `step` through an `AdminJob.argument_id` lookup, and `import_convokit.py` contains zero references to `AdminJob` anywhere in the file.
- New end-to-end test calls `get_argument_with_utterances` directly against the same `isolated_session` the import wrote to — no HTTP client, no `api.main` import — consistent with 29-07's established pattern for avoiding the documented pre-existing FastAPI test lifespan/session-factory failure.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their `<action>` blocks precisely; no Rule 1-4 auto-fixes were required beyond what the plan itself specified.

## Issues Encountered

- **Out-of-scope pre-existing test failures** (SCOPE BOUNDARY — logged to `deferred-items.md`, not fixed): running the plan's own verification step 3 (`pytest pipeline/tests/test_ingest.py pipeline/tests/test_parse.py pipeline/tests/test_pipeline_run.py -q`) surfaced 8 pre-existing failures unrelated to this plan's changes:
  - `test_ingest.py::test_ingest_creates_pipeline_run`, `test_consolidated_dockets`, `test_ingest_idempotent` and `test_parse.py::test_run_id_strategy`, `test_llm_failure_modes` — `AttributeError: 'Namespace' object has no attribute 'job_id'`, a test-fixture gap in files this plan never touches.
  - `test_parse.py::test_section_hint_not_cascade` — an unrelated assertion failure, not investigated further.
  - `test_pipeline_run.py::test_state_machine`, `test_rerun_creates_new_rows` — `sqlalchemy.exc.InterfaceError: cannot perform operation: another operation is in progress`, matching the project's documented pre-existing FastAPI/asyncpg test-session issue.
  - Confirmed via `git status --short` (only `import_convokit.py` and its two test files are modified) and `git diff --stat` against `api/services/arguments.py`, `api/services/admin_jobs.py`, `pipeline/commands/ingest.py`, `pipeline/commands/parse.py`, `pipeline/commands/resolve.py` (empty) that this plan's fix is confined to the corpus importer's write side and its own tests — these 8 failures pre-date this plan's execution and are logged in `.planning/phases/29-historical-corpus-import/deferred-items.md` for future gap-closure, not fixed here.
  - The plan's own tests (`pytest pipeline/tests/test_import_convokit_core.py pipeline/tests/test_import_convokit_utterances.py -q`) pass in full: 27/27.

## User Setup Required

None — no external service configuration required. No migration is required (`PipelineRun.step` is a free-text `String(50)` column). No backfill is required (zero corpus-imported `Argument` rows exist anywhere, per 29-VERIFICATION.md's Scope Note).

## Next Phase Readiness

- This closes the second independent gap discovered alongside 29-07's `argued_date` nullability fix — both gaps in Phase 29's verification/review cycle are now addressed.
- 29-07-PLAN.md's own regression test's deliberate abstention from asserting on `utterances` content is now superseded by this plan's `test_utterances_readable_via_arguments_service_after_import`.
- The pre-existing PDF-ingest pipeline test failures (`test_ingest.py`, `test_parse.py`, `test_pipeline_run.py` — 8 failures, `AttributeError: 'Namespace' object has no attribute 'job_id'` and a stale-session `InterfaceError`) are unrelated to this plan and are logged in `deferred-items.md` for a future gap-closure round.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*
