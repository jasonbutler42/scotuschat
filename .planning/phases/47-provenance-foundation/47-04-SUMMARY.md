---
phase: 47-provenance-foundation
plan: 04
subsystem: testing
tags: [pytest, sqlalchemy, provenance, import_run, regression-suite]

# Dependency graph
requires:
  - phase: 47-01
    provides: "import_run table + import_source/import_method PG enum types, ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes"
  - phase: 47-02
    provides: "ingest/parse/resolve write paths stamping source/method at row creation"
  - phase: 47-03
    provides: "API read layer converted to ImportRun, PIPELINE_RUN_STRATEGY deleted repo-wide"
provides:
  - "pipeline/tests suite (244 tests, 239 passed + 5 pre-existing xfail) collecting and passing in full against the import_run schema"
  - "pipeline/tests/test_import_run.py -- renamed via git mv from test_pipeline_run.py, history preserved"
  - "pipeline/tests/test_parse.py::test_run_id_and_method -- renamed from test_run_id_strategy, per-utterance strategy assertion moved to the parent run's ImportMethod"
  - "scripts/delete_fixture_argument.py converted to ImportRun (Rule 3 blocking auto-fix, outside files_modified)"
  - "Standing assertion in test_import_convokit_core.py guarding Argument.oyez_transcript_id after corpus import"
affects: [47-05, 47-06]

# Actuals (#2632)
actuals:
  tokens: 9430
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test fixtures constructing ImportRun rows must declare both source= and method= explicitly (NOT NULL, no default) -- same D-02 invariant production writers follow"

key-files:
  created: []
  modified:
    - pipeline/tests/test_import_run.py
    - pipeline/tests/test_parse.py
    - pipeline/tests/test_ingest.py
    - pipeline/tests/test_resolve.py
    - pipeline/tests/test_import_convokit_core.py
    - pipeline/tests/test_import_convokit_utterances.py
    - pipeline/tests/test_delete_fixture_argument.py
    - pipeline/tests/test_diff_corpus_fixture.py
    - pipeline/tests/test_import_run_provenance.py
    - pipeline/tests/test_import_justices_csv.py
    - scripts/delete_fixture_argument.py

key-decisions: []

patterns-established: []

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-05]

coverage:
  - id: D1
    description: "The four PDF-lifecycle pipeline test files (test_import_run.py, test_parse.py, test_ingest.py, test_resolve.py) pass against the import_run schema; test_pipeline_run.py renamed to test_import_run.py with git history preserved"
    requirement: "PROV-01"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest pipeline/tests/test_import_run.py pipeline/tests/test_parse.py pipeline/tests/test_ingest.py pipeline/tests/test_resolve.py -q -- 40 passed, 3 xfailed"
        status: pass
      - kind: static
        ref: "git log --follow --oneline -- pipeline/tests/test_import_run.py shows history predating this phase"
        status: pass
    human_judgment: false
  - id: D2
    description: "test_run_id_strategy renamed to test_run_id_and_method; the per-utterance strategy assertion moved to the parent run's ImportMethod assertion, not deleted"
    requirement: "PROV-05"
    verification:
      - kind: static
        ref: "grep -c ImportMethod. pipeline/tests/test_parse.py returns 3 (>=2 required)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The entire pipeline/tests suite (244 tests) collects and passes against the import_run schema; no test was deleted to achieve this"
    requirement: "PROV-01"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest pipeline/tests -q -- 239 passed, 5 xfailed"
        status: pass
      - kind: static
        ref: "grep -rc PipelineRun\\|pipeline_run_id\\|pipeline_runs pipeline/tests/ -- 0 for every file"
        status: pass
      - kind: static
        ref: "grep -rc .strategy\\|strategy= pipeline/tests/ -- 0 for every file"
        status: pass
    human_judgment: false
  - id: D4
    description: "Standing assertion guards Argument.oyez_transcript_id after corpus import; _write_corpus_fixture/_args/_scoped_args helper names and signatures unchanged (test_import_run_provenance.py depends on them)"
    requirement: "PROV-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py::test_creates_case_argument_caseargument_importrun_entities"
        status: pass
      - kind: static
        ref: "grep -c 'def _write_corpus_fixture' pipeline/tests/test_import_convokit_core.py returns 1"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full-suite collection confirms exactly one remaining collection error (api/tests/test_admin_dev_routes.py, owned by 47-05) -- no new collection errors introduced by this plan's changes"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest -q -- 1 error in collection: api/tests/test_admin_dev_routes.py only"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-08-17
status: complete
---

# Phase 47 Plan 04: Pipeline Test Suite Conversion Summary

**Converted all eight `pipeline/tests` files referencing the retired `PipelineRun`/`pipeline_run_id`/`strategy` names to the `import_run` schema (`ImportRun`/`ImportSource`/`ImportMethod`), renamed `test_pipeline_run.py` to `test_import_run.py` with git history preserved, and translated every per-utterance strategy assertion into a parent-run `ImportMethod` assertion rather than deleting coverage — the full 244-test `pipeline/tests` suite now collects and passes (239 passed, 5 pre-existing xfailed).**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-08-17T21:46Z
- **Tasks:** 2/2
- **Files modified:** 11 (10 test files, 1 script)

## Accomplishments

- `pipeline/tests/test_pipeline_run.py` renamed to `test_import_run.py` via `git mv` (history follows); both tests (`test_state_machine`, `test_rerun_creates_new_rows`) converted to construct `ImportRun` rows with declared `source=`/`method=`
- `pipeline/tests/test_parse.py`: `test_run_id_strategy` renamed to `test_run_id_and_method` — the per-utterance `row.strategy in (...)` assertion moved up to `assert new_run.method in (ImportMethod.RULE_BASED, ImportMethod.LLM_CORRECTIVE)` on the parent run, keeping the `row.import_run_id == new_run.id` check; the second test in the file (`test_parse_preserves_operator_docket_when_extracted_pair_conflicts`) converted its fixture `ImportRun` construction to declare `source=PDF_PIPELINE`/`method=NORMALIZED`
- `pipeline/tests/test_ingest.py`: `test_ingest_creates_pipeline_run` renamed to `test_ingest_creates_import_run`; assertions extended to check `source=PDF_PIPELINE`/`method=NORMALIZED` alongside the existing status/step checks
- `pipeline/tests/test_resolve.py`: `test_resolve_interrupt_sets_needs_review`'s mocked-session unit test converted to reference `resolve_module.ImportRun`/`ImportRunStatus` (via the module's own namespace, preserving the identity-map safety note already documented in the file)
- `pipeline/tests/test_import_convokit_core.py`: all `PipelineRun`/`strategy="convokit_import"` fixture reads converted to `ImportRun`/`source=CORPUS`/`method=DIRECT`; added a standing assertion (`test_creates_case_argument_caseargument_importrun_entities`, renamed from `..._pipelinerun_entities`) that `Argument.oyez_transcript_id` still equals the conversation id post-import — the cheapest possible guard against the single highest-risk mistake this phase could make
- `pipeline/tests/test_import_convokit_utterances.py`: `pipeline_run_id` → `import_run_id` throughout; `test_every_utterance_has_pipeline_run_id_and_unique_sequence` renamed to `test_every_utterance_has_import_run_id_and_unique_sequence`
- `pipeline/tests/test_delete_fixture_argument.py`: fixture helper `_seed_full_fixture` now constructs `ImportRun(source=PDF_PIPELINE, method=RULE_BASED)`; the FK-ordered cascade-count assertions (`"pipeline_runs"` → `"import_run"`, matching the model's real `__tablename__`) preserved intact, including the injected mid-cascade-failure test's table-name interception string
- `pipeline/tests/test_diff_corpus_fixture.py`: removed the unused `PipelineRun`/`PipelineRunStatus` import (dead references — the underlying `scripts/diff_corpus_fixture.py` never used them)
- `pipeline/tests/test_import_justices_csv.py`: updated a stale prose pointer from `test_pipeline_run.py::test_rerun_creates_new_rows` to the renamed `test_import_run.py::test_rerun_creates_new_rows`
- `pipeline/tests/test_import_run_provenance.py`: reworded a stale module comment that named the retired run-model symbol directly (tripping this plan's own file-wide negative-grep acceptance criterion) — no behavior change, prose only

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert the PDF-lifecycle pipeline tests and rename test_pipeline_run.py** — `b74ae85c0` (test)
2. **Task 2: Convert the corpus-import and fixture-management pipeline tests** — `8938da48f` (test)

## Files Created/Modified

- `pipeline/tests/test_import_run.py` — renamed via `git mv` from `test_pipeline_run.py`; both tests converted to `ImportRun`
- `pipeline/tests/test_parse.py` — `test_run_id_strategy` renamed to `test_run_id_and_method`; strategy assertion moved to parent-run `ImportMethod`
- `pipeline/tests/test_ingest.py` — `test_ingest_creates_pipeline_run` renamed to `test_ingest_creates_import_run`
- `pipeline/tests/test_resolve.py` — mocked-session unit test converted to `ImportRun`/`ImportRunStatus`
- `pipeline/tests/test_import_convokit_core.py` — fixtures/assertions converted to `ImportRun`/`ImportSource.CORPUS`/`ImportMethod.DIRECT`; standing `oyez_transcript_id` guard added
- `pipeline/tests/test_import_convokit_utterances.py` — `pipeline_run_id` → `import_run_id`
- `pipeline/tests/test_delete_fixture_argument.py` — fixture + cascade-count assertions converted to `ImportRun`/`import_run`
- `pipeline/tests/test_diff_corpus_fixture.py` — removed unused `PipelineRun`/`PipelineRunStatus` import
- `pipeline/tests/test_import_run_provenance.py` — stale comment reworded (Rule 1/3 fix, see Deviations)
- `pipeline/tests/test_import_justices_csv.py` — stale cross-reference comment updated to renamed file
- `scripts/delete_fixture_argument.py` — Rule 3 blocking auto-fix, minimal identifier rename (see Deviations)

## Decisions Made

None — this plan executes 47-01/47-02/47-03's already-decided schema; no new architectural decisions were needed. Two test functions were renamed beyond the plan's explicit list (`test_ingest_creates_pipeline_run` → `test_ingest_creates_import_run`, `test_creates_case_argument_caseargument_pipelinerun_entities` → `..._importrun_entities`) for naming consistency with the schema they now exercise — not required by the plan's `<artifacts_this_phase_produces>` list, but harmless and consistent with the one rename the plan did require (`test_run_id_strategy` → `test_run_id_and_method`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Minimal identifier rename in `scripts/delete_fixture_argument.py`**
- **Found during:** Task 2 (converting `test_delete_fixture_argument.py`)
- **Issue:** `scripts/delete_fixture_argument.py` (not in this plan's `files_modified` list) has a module-level `from api.models.models import (..., PipelineRun, ...)`. Since `PipelineRun` no longer exists (removed in 47-01), the script raised `ImportError` at module load — blocking `test_delete_fixture_argument.py`, this plan's own scoped test file, from importing at all (`from scripts.delete_fixture_argument import _run` failed collection).
- **Fix:** Renamed `PipelineRun` → `ImportRun` and the `"pipeline_runs"` table-name label → `"import_run"` (matching the model's real `__tablename__`) throughout the script's docstring, imports, `DEPENDENT_MODELS` list, and both `delete(...)`/`select(...)` call sites. Did **not** add any `source=`/`method=` stamping logic — this script only ever `delete()`s `ImportRun` rows by `argument_id`, it never constructs one, so there is no provenance-declaration gap to fill. This mirrors the identical pattern 47-01 used for `pipeline/commands/ingest.py`/`resolve.py`.
- **Files modified:** `scripts/delete_fixture_argument.py`
- **Verification:** `./.venv/bin/python -c "import scripts.delete_fixture_argument"` exits 0; `python3 -m compileall -q scripts/delete_fixture_argument.py` clean; full `test_delete_fixture_argument.py` suite (9 tests) passes.
- **Committed in:** `8938da48f` (Task 2 commit)

**2. [Rule 1 - Bug] Stale retired-symbol prose in `test_import_run_provenance.py` tripped this plan's own acceptance criterion**
- **Found during:** Task 2 final verification (`grep -rc "PipelineRun\|pipeline_run_id\|pipeline_runs" pipeline/tests/`)
- **Issue:** `test_import_run_provenance.py` (owned by 47-01/47-02, not this plan's `files_modified`) has a module comment literally spelling out `PipelineRun, PipelineRunStatus` to explain why its fixture helpers were copied rather than imported from `test_import_convokit_core.py`. That comment's factual premise (the import was broken) is still historically true, but the plan's own file-wide negative-grep acceptance criterion (`grep -rc "PipelineRun\|..." pipeline/tests/` returning 0 for every file) does not distinguish prose from code — and the retired-name-hygiene note in `<conversion_rules>` explicitly says to restate old-vocabulary explanations "never annotate it with the old name."
- **Fix:** Reworded the comment to describe the historical breakage without naming the retired symbol directly (referring to "the pre-Phase-47 run model name" instead of spelling it out).
- **Files modified:** `pipeline/tests/test_import_run_provenance.py`
- **Verification:** `grep -rc "PipelineRun\|pipeline_run_id\|pipeline_runs" pipeline/tests/` returns 0 for every file; `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -q` still passes (12 passed, unchanged).
- **Committed in:** `8938da48f` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes were necessary to unblock this plan's own scoped deliverable (a fully green `pipeline/tests` suite) and to satisfy this plan's own stated acceptance criteria. No functional/provenance-stamping work was pulled forward from another plan — `scripts/delete_fixture_argument.py` only deletes rows by id, so there was no `source=`/`method=` gap to fill.

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `pipeline/tests` (244 tests) collects and passes in full against the `import_run` schema. `test_import_run.py`, `test_parse.py`, `test_ingest.py`, `test_resolve.py`, `test_import_convokit_core.py`, `test_import_convokit_utterances.py`, `test_delete_fixture_argument.py`, and `test_diff_corpus_fixture.py` are all green.
- A full bare-invocation `pytest -q` run now shows **exactly one** remaining collection error: `api/tests/test_admin_dev_routes.py` (`ImportError: cannot import name 'PipelineRun'`, line 40, direct construction in its own test body) — this is 47-05's scoped conversion work, unaffected by anything in this plan's `files_modified`. No new collection errors were introduced by this plan.
- `api/tests/test_docket_arg_safety.py` and `pipeline/tests/test_ingest_startup_guard.py` (named in `<upstream_state>` as already collecting cleanly with no edits needed) remain unaffected — confirmed via the full `pipeline/tests` and full-suite runs above.
- 47-05 can proceed against `api/tests/test_admin_dev_routes.py` without any further schema, fixture-helper, or test-suite dependency from this plan. 47-06's full-suite gate now inherits a RED surface of exactly one file.

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `pipeline/tests/test_import_run.py`
- CONFIRMED ABSENT: `pipeline/tests/test_pipeline_run.py`
- FOUND: `.planning/phases/47-provenance-foundation/47-04-SUMMARY.md`
- FOUND commit: `b74ae85c0`
- FOUND commit: `8938da48f`
- FOUND commit: `b6e9b8968`
