---
phase: 30-corpus-import-resolve-workflow
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, admin-jobs, provenance]

# Dependency graph
requires:
  - phase: 30-corpus-import-resolve-workflow (Plan 01)
    provides: AdminJob rows paired with corpus-imported arguments via PipelineRun.strategy == "convokit_import"
provides:
  - "AdminJobResponse.source: Literal['pdf','corpus'] derived field"
  - "exists()-based source derivation in list_jobs() and get_job()"
affects: [30-corpus-import-resolve-workflow (Plan 03 — list-page Source tag)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived-field-via-exists()-subquery: never add a schema/DDL column when a signal is already computable from an existing relationship (PipelineRun.strategy), per CLAUDE.md's Alembic-is-sole-DDL-authority constraint"

key-files:
  created:
    - api/tests/test_admin_jobs_source.py
  modified:
    - api/schemas/admin_jobs.py
    - api/services/admin_jobs.py

key-decisions:
  - "get_job()'s exists() correlates on the already-loaded job.argument_id Python value (not a second AdminJob-correlated subquery), since a single-row lookup has no need to join back to AdminJob and this avoids an under-specified FROM clause"
  - "PIPELINE_RUN_STRATEGY imported from pipeline.commands.import_convokit into api/services/admin_jobs.py, following the established cross-layer import precedent (normalize_label from pipeline.commands.resolve)"

patterns-established:
  - "Derived-field-via-exists(): source (and prior is_archived) never require new columns — computed at read time from existing relationships"

requirements-completed: [PJOB-01]

coverage:
  - id: D1
    description: "AdminJobResponse exposes source: Literal['pdf','corpus'] = 'pdf'"
    requirement: "PJOB-01"
    verification:
      - kind: unit
        ref: "python -c \"AdminJobResponse.model_fields['source'].default\" -> 'pdf'"
        status: pass
    human_judgment: false
  - id: D2
    description: "list_jobs() and get_job() derive source via a duplication-safe exists() subquery on PipelineRun.strategy == 'convokit_import', including the mixed-runs guard case (no row duplication)"
    requirement: "PJOB-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_source.py (5 tests: corpus, pdf/non-corpus-run, pdf/no-run, pdf/no-argument, mixed-runs duplication guard)"
        status: unknown
    human_judgment: true
    rationale: "DB-gated tests are skipped in this environment because DATABASE_URL is not exported as a process env var (only loaded from .env by pydantic-settings for the app itself) — matches the project's pre-existing, documented FastAPI test lifespan/session-factory failure (async_session_factory does not exist in api/core/database.py). This is an existing, open, unrelated infrastructure gap, not something this plan introduced or should fix. Tests were written correctly against the established test_admin_jobs_list.py fixture pattern and will exercise real DB behavior once that infra gap is resolved."

duration: 15min
completed: 2026-07-10
status: complete
---

# Phase 30 Plan 02: AdminJobResponse Source Field Summary

**Derived `source: Literal["pdf","corpus"]` field on `AdminJobResponse`, computed at read time in both `list_jobs()` and `get_job()` via a duplication-safe `exists()` subquery on `PipelineRun.strategy == "convokit_import"` — no schema change.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified:** 2 (+1 created)

## Accomplishments
- `AdminJobResponse.source` field added, mirroring the `is_archived` field's shape/comment style, defaulting to `"pdf"`
- `list_jobs()` now selects an `is_corpus_subq.label("is_corpus")` column alongside the existing `Argument.status` projection and sets `job.__dict__["source"]` per row — no duplicate `AdminJob` rows even when an argument has multiple `PipelineRun` rows (one corpus, one not)
- `get_job()` derives the real per-job `source` value (not a hardcoded default, unlike `is_archived`'s detail-page default) via a single-row `exists()` query correlated on the already-loaded `job.argument_id`
- New `api/tests/test_admin_jobs_source.py` with 5 tests covering: convokit_import run -> "corpus" (list + detail parity), non-corpus run -> "pdf", no `PipelineRun` at all -> "pdf", no linked argument -> "pdf", and the duplication guard (mixed corpus + non-corpus runs on one argument -> exactly one row, classified "corpus")

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the source field to AdminJobResponse** - `cd83c288` (feat)
2. **Task 2: Derive source in list_jobs() and get_job() via an exists() subquery** - `6cd13962` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `api/schemas/admin_jobs.py` - Added `source: Literal["pdf", "corpus"] = "pdf"` field to `AdminJobResponse`, same comment style as `is_archived`
- `api/services/admin_jobs.py` - Imported `exists` from sqlalchemy and `PIPELINE_RUN_STRATEGY` from `pipeline.commands.import_convokit`; added `is_corpus_subq` to `list_jobs()`'s query/row-unpacking; added an equivalent single-row `exists()` derivation to `get_job()`
- `api/tests/test_admin_jobs_source.py` - New DB-gated test file (5 tests) asserting corpus vs pdf classification and the no-duplication guard

## Decisions Made
- `get_job()`'s `exists()` query correlates on `job.argument_id` (a plain Python value, already loaded from the earlier `select(AdminJob)` call) rather than re-joining back to the `AdminJob` table — simpler and avoids an ambiguous/under-specified FROM clause that a naive port of the `list_jobs()` pattern would have introduced for a single-row lookup. `job.argument_id is None` correctly yields no `PipelineRun` match (the column is `NOT NULL`), giving `"pdf"` for jobs with no linked argument, same as `list_jobs()`.
- `PIPELINE_RUN_STRATEGY` imported directly from `pipeline.commands.import_convokit` (not re-declared as a local literal) — confirmed this imports cleanly with no circular-import issue (`import_convokit.py` does not import from `api.services.admin_jobs`), following the same established precedent as the existing `normalize_label` import from `pipeline.commands.resolve`.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched 30-PATTERNS.md's prescribed code shape precisely, including the exact `is_corpus_subq` variable name and `exists()` approach documented there.

## Issues Encountered

The DB-gated tests (this plan's new `test_admin_jobs_source.py`, and pre-existing sibling files `test_admin_jobs_list.py` / `test_admin_jobs_service.py`) could not be exercised against a live database in this environment: setting `DATABASE_URL` as a process env var and running the test suite surfaces `ImportError: cannot import name 'async_session_factory' from 'api.core.database'` — that name does not exist in `api/core/database.py` (which only exports `engine`, `AsyncSessionLocal`, `get_db`, and `lifespan`). This reproduces identically on the pre-existing `test_admin_jobs_list.py`'s own `db_session` fixture, confirming it is a pre-existing, already-documented infrastructure gap (project memory: "FastAPI test lifespan/session-factory failure (open, pre-existing, ~57 tests)"), not a regression introduced by this plan. In the standard run configuration (no `DATABASE_URL` process env var — the normal state for this repo, since `.env` is loaded by pydantic-settings for the app but not exported to the shell), all `@pytest.mark.skipif(not _db_configured())`-gated tests correctly skip and the suite passes:
- `python -m pytest api/tests/test_admin_jobs_source.py -x -q` -> 5 skipped
- `python -m pytest api/tests/test_admin_jobs_list.py api/tests/test_admin_jobs_service.py -q` -> 5 passed, 12 skipped

Static verification confirmed instead:
- `AdminJobResponse.model_fields['source'].default == 'pdf'`
- `import api.services.admin_jobs` succeeds (no circular import from the new `PIPELINE_RUN_STRATEGY` import)
- `py_compile` clean on all three modified/created files
- No new Alembic migration file was added (`git status` on `alembic/versions/` shows no new file for this plan)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `AdminJobResponse.source` is ready for 30-03's list-page Source tag to consume via `data.jobs[].source` passthrough in `+page.server.ts`
- The pre-existing `async_session_factory` test infrastructure gap remains open and blocks live-DB verification of this plan's (and several prior plans') DB-gated tests; it is unrelated to this plan's scope and should be tracked/fixed separately

---
*Phase: 30-corpus-import-resolve-workflow*
*Completed: 2026-07-10*

## Self-Check: PASSED
All created files and commit hashes verified present.
