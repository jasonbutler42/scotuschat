# Deferred Items — Phase 29 (historical-corpus-import)

## From Plan 29-08

### Pre-existing PDF-pipeline test failures, unrelated to this plan's changes

**Found during:** Task 1/2 verification (`pytest pipeline/tests/test_ingest.py pipeline/tests/test_parse.py pipeline/tests/test_pipeline_run.py -q`)

**Observation:** 8 of 17 tests across `test_ingest.py`, `test_parse.py`, and `test_pipeline_run.py` fail:
- `test_ingest.py::test_ingest_creates_pipeline_run`, `test_consolidated_dockets`, `test_ingest_idempotent` — `AttributeError: 'Namespace' object has no attribute 'job_id'` inside `pipeline/commands/ingest.py` (the test's own `argparse.Namespace(...)` fixture omits `job_id`, which `_run_ingest_inner` now reads unconditionally).
- `test_parse.py::test_run_id_strategy`, `test_llm_failure_modes` — same `AttributeError` pattern; `test_section_hint_not_cascade` — assertion failure (not investigated further, out of scope).
- `test_pipeline_run.py::test_state_machine`, `test_rerun_creates_new_rows` — `sqlalchemy.exc.InterfaceError: cannot perform operation: another operation is in progress` (looks like the documented pre-existing Windows/asyncpg concurrent-session issue referenced in project memory).

**Why out of scope:** This plan (29-08) modifies only `pipeline/commands/import_convokit.py`, `pipeline/tests/test_import_convokit_core.py`, and `pipeline/tests/test_import_convokit_utterances.py` (confirmed via `git status --short`). `git diff --stat` against `pipeline/commands/ingest.py`, `pipeline/commands/parse.py`, `pipeline/commands/resolve.py`, `api/services/arguments.py`, and `api/services/admin_jobs.py` is empty — none of these files were touched by this plan. These failures pre-date this plan's execution and are unrelated to the `PipelineRun.step` relabel; per the executor's SCOPE BOUNDARY rule, they are logged here rather than fixed.

**Status:** Not fixed. Needs its own investigation/gap-closure plan — likely a missing `job_id=None` default somewhere in `ingest.py`/`parse.py`'s Namespace-consuming code path, or a stale test fixture that predates a `job_id`-aware code change in an earlier phase.
