---
phase: 47-provenance-foundation
plan: 05
subsystem: testing
tags: [pytest, sqlalchemy, alembic, provenance, import_run, api-tests, schema-contract]

# Dependency graph
requires:
  - phase: 47-01
    provides: "import_run table + import_source/import_method PG enum types, ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes"
  - phase: 47-02
    provides: "ingest/parse/resolve write paths stamping source/method at row creation"
  - phase: 47-03
    provides: "API read layer converted to ImportRun, PIPELINE_RUN_STRATEGY deleted repo-wide"
  - phase: 47-04
    provides: "pipeline/tests suite (244 tests) converted to import_run, last-mile blocker narrowed to api/tests/test_admin_dev_routes.py only"
provides:
  - "api/tests (33-file corpus) and the two root tests/ schema-contract files collecting and passing in full against the import_run schema"
  - "Standing ImportSource/ImportMethod exhaustiveness assertions in tests/test_models_import.py"
  - "Live-schema absence assertion (pipeline_runs gone, utterances.import_run_id present, utterances.strategy gone) in tests/test_schema.py"
  - "Public utterance contract test proving strategy/source/method/external_id never leak (T-47-17)"
  - "Fix for test_migration_0022_person_name_authority.py's downgrade fixture, which previously assumed an empty database"
  - "Fix for a pre-existing test_no_create_all_in_codebase false positive (unrelated to Phase 47, exposed for the first time by this plan's full-suite collection fix)"
affects: [47-06]

# Actuals (#2632)
actuals:
  tokens: 15044
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test fixtures constructing ImportRun rows must declare both source= and method= explicitly (NOT NULL, no default) -- same D-02 invariant production writers and 47-04's pipeline/tests conversion follow"
    - "A migration-revision-pinned test (test_migration_0022, pinned to baseline 0021/target 0022) must keep the historical table name its pinned revision actually used, even after a later migration renames that table going forward -- renaming it would break the very revision the test exercises"

key-files:
  created: []
  modified:
    - api/tests/test_admin_jobs_source.py
    - api/tests/test_admin_jobs_stats.py
    - api/tests/test_admin_jobs_service.py
    - api/tests/test_admin_jobs_phase35.py
    - api/tests/test_admin_dev_routes.py
    - api/tests/test_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_speakers_service.py
    - api/tests/test_argument_oyez_field.py
    - api/tests/test_published_gate.py
    - api/tests/test_admin_dashboard_stats.py
    - api/tests/test_phase44_resolve_table_contract.py
    - api/tests/test_migration_0022_person_name_authority.py
    - tests/test_schema.py
    - tests/test_models_import.py
    - .planning/phases/47-provenance-foundation/deferred-items.md
    - .planning/WINDOWS.md

key-decisions:
  - "test_migration_0022_person_name_authority.py's TRUNCATE SQL keeps the literal table name pipeline_runs (not renamed to import_run) because that module is pinned to alembic revision 0021/0022, both of which predate migration 0026's rename -- at the schema state this module actually exercises, the table is genuinely still called pipeline_runs. Documented inline with an explanatory comment so a future reader does not 'fix' it into a broken test."
  - "Fixed two cross-file test interactions found only when the full suite collects and runs together for the first time (previously walled off by api/tests/test_admin_dev_routes.py's collection error): test_migration_0022's downgrade fixture now truncates utterances/import_run (scotus_test only) before downgrading past migration 0026, and test_no_create_all_in_codebase's search now skips nested tests/ subdirectories, matching its own docstring's stated intent."

patterns-established: []

requirements-completed: [PROV-01, PROV-03, PROV-04, PROV-06]

coverage:
  - id: D1
    description: "The five admin-jobs and dev-reset API test files (test_admin_jobs_source.py, test_admin_jobs_stats.py, test_admin_jobs_service.py, test_admin_jobs_phase35.py, test_admin_dev_routes.py) pass against the import_run schema, with corpus-vs-pdf fixtures established via the declared ImportRun.source enum rather than a strategy string"
    requirement: "PROV-03"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest api/tests/test_admin_jobs_source.py api/tests/test_admin_jobs_stats.py api/tests/test_admin_jobs_service.py api/tests/test_admin_jobs_phase35.py api/tests/test_admin_dev_routes.py -q -- 33 passed"
        status: pass
      - kind: static
        ref: "grep -c ImportSource.CORPUS / ImportSource.PDF_PIPELINE in api/tests/test_admin_jobs_source.py (3 / 2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The remaining eight API test files and the two root schema-contract test files pass against the import_run schema; schema-contract files name import_run with unchanged table counts and gain standing ImportSource/ImportMethod exhaustiveness assertions; the public utterance contract test proves no provenance field is exposed"
    requirement: "PROV-04"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest api/tests tests -q -- 800 passed, 10 skipped, 0 failed"
        status: pass
      - kind: static
        ref: "grep -c import_run_id / strategy-not-in / source-not-in / method-not-in / external_id-not-in assertions in api/tests/test_arguments.py"
        status: pass
      - kind: static
        ref: "grep -c 'assert len(tables) == 13' tests/test_models_import.py (1); grep -c ImportSource/ImportMethod (3 each)"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_pytest_isolation_invocation_shapes.py (D-03 regression, CLAUDE.md-named) -- all 3 parametrized invocation shapes now pass, closing the gap 47-01/47-03 left open"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest tests/test_pytest_isolation_invocation_shapes.py -q -- 3 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bare full-suite pytest -q (the phase's integration checkpoint) reports an accurate count; 4 pre-existing, unrelated failures identified and explained rather than hidden or hand-waved"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest -q -- 1054 collected: 1035 passed, 10 skipped, 5 xfailed, 4 failed"
        status: fail
    human_judgment: true
    rationale: "The 4 failures (api/tests/test_phase44_argument_role_roundtrip.py) are a pre-existing SideEnum module-identity bug from Phase 5/44, fully reproducible in isolation without any file this plan touched, and only surfaces under pytest.ini's testpaths order (tests before api/tests) which the explicit-path api/tests+tests invocation this plan's own acceptance criteria uses does not hit. A human should confirm this is out of 47-05's scope before treating it as a phase-blocking regression -- see deferred-items.md and WINDOWS.md entry #5."

duration: ~50min
completed: 2026-08-17
status: complete
---

# Phase 47 Plan 05: Test Suite Conversion (API + Schema Contracts) Summary

**Converted the thirteen `api/tests` files and two root `tests/` schema-contract files still referencing the retired `PipelineRun`/`pipeline_run_id`/`pipeline_runs`/`strategy` names to the `import_run` schema, closing out Phase 47's test-suite conversion — `api/tests tests` now collects and passes in full (800 passed, 10 skipped, 0 failed), and along the way fixed two genuine cross-file test interactions that only became visible once the full suite could finally collect and run together for the first time.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-08-17T22:22Z
- **Tasks:** 2/2
- **Files modified:** 17 (15 test files, 2 planning docs)

## Accomplishments

- `api/tests/test_admin_jobs_source.py`: every corpus-vs-pdf fixture now writes an `ImportRun` row declaring `source=ImportSource.CORPUS|PDF_PIPELINE` + a matching `method=`, instead of a `PipelineRun` row carrying a `strategy=` string — the observable assertions (`source` reads `"corpus"`/`"pdf"`) are unchanged; only how the fixture establishes the precondition changed. Two test function names containing the retired vocabulary (`..._for_convokit_import_run`, `..._mixed_pipeline_runs`) were renamed to name the new vocabulary instead, per the retired-name-hygiene rule.
- `api/tests/test_admin_jobs_stats.py`: `parse_stats` fixtures construct `ImportRun` with declared `source=`/`method=`, keeping the `step="parse"`/`step="ingest"` per-step grain intact (D-04, deliberately preserved by this phase).
- `api/tests/test_admin_jobs_service.py`, `test_admin_jobs_phase35.py`, `test_admin_dev_routes.py`: structural guards, delete-cascade tests, and the dev-reset throwaway-row fixture all converted to `ImportRun`/`import_run_id`; `test_admin_dev_routes.py`'s `reset_to_fixture` patching safety harness was left byte-for-byte untouched (only the table-name string and one throwaway `PipelineRun` fixture were renamed).
- `api/tests/test_arguments.py`: the public `GET /arguments/{id}/utterances` contract test now asserts `import_run_id` is present and that `strategy`, `source`, `method`, and `external_id` are all absent from a serialized utterance (T-47-17) — the negative assertion was added, not silently dropped.
- `api/tests/test_admin_arguments_service.py`, `test_speakers_service.py`, `test_admin_dashboard_stats.py`, `test_published_gate.py`, `test_argument_oyez_field.py`, `test_phase44_resolve_table_contract.py`: remaining `PipelineRun`/`pipeline_run_id`/`strategy=` references converted; the delete-cascade ordering test now asserts `delete(Utterance)` precedes `delete(ImportRun)` (matching the real FK order in `admin_arguments.py`); the frontend client-side leak guard now checks for `ImportRun` (the current internal identifier) instead of the retired `PipelineRun`.
- `tests/test_schema.py`: `EXPECTED_TABLES` names `import_run`; `test_all_tables_exist` gained two new assertions on the same live-schema fixture — `pipeline_runs` is absent from `information_schema.tables`, and `utterances` carries `import_run_id` with no `strategy` column. `test_no_create_all_in_codebase` was left alone functionally but its pre-existing search-path bug (see Deviations) was fixed.
- `tests/test_models_import.py`: expected table-name set names `import_run` (13-table count unchanged); `test_pipeline_run_status_values` renamed to `test_import_run_status_values`; two new standing exhaustiveness tests (`test_import_source_values`, `test_import_method_values`) guard both closed vocabularies at exactly 4 and 5 values respectively; the utterance index assertion renamed to `ix_utterances_import_run_id`.
- `api/tests/test_migration_0022_person_name_authority.py`: **left the historical `pipeline_runs` table name in place** in its `_CLEAN_TABLES_SQL` — that module is pinned to alembic revision 0021/0022, both of which predate migration 0026's rename, so at the schema state this module actually exercises, the table is genuinely still called `pipeline_runs`. Documented this inline with an explanatory comment. Separately **fixed a real bug**: its `_baseline_at_0021` fixture assumed the database was empty before downgrading past migration 0026, which recreates `pipeline_runs` empty and re-adds `utterances.pipeline_run_id`'s FK against it — any real rows left behind by another test module (e.g. `test_admin_dev_routes.py`'s corpus-reset tests, which deliberately leave 4 fixture arguments behind) broke the downgrade with a `ForeignKeyViolationError`. The fixture now truncates `utterances, import_run CASCADE` (scotus_test only, never `DATABASE_URL`, never touching migration 0026 itself) immediately before downgrading, whenever `import_run` currently exists.

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert the admin-jobs and dev-reset API tests** — `9ef87502d` (test)
2. **Task 2: Convert the remaining API tests and the two schema-contract tests** — `e628d2011` (test)

**Deferred-items/ledger docs commit:** `bad35a159` (docs)

## Files Created/Modified

- `api/tests/test_admin_jobs_source.py` — corpus-vs-pdf fixtures converted to `ImportRun`/declared `source=`/`method=`
- `api/tests/test_admin_jobs_stats.py` — `parse_stats` fixtures converted, `step=` grain preserved
- `api/tests/test_admin_jobs_service.py` — structural guards + behavioral delete_job test converted
- `api/tests/test_admin_jobs_phase35.py` — disk-backed PDF fixture and cleanup converted
- `api/tests/test_admin_dev_routes.py` — throwaway-row seed converted; safety harness untouched
- `api/tests/test_arguments.py` — seeded_argument fixture converted; public contract test gains negative provenance-leak assertions
- `api/tests/test_admin_arguments_service.py` — delete-cascade ordering test + list_argument_speakers fixture converted
- `api/tests/test_speakers_service.py` — two ImportRun/Utterance fixture blocks converted
- `api/tests/test_argument_oyez_field.py` — stale prose reference updated
- `api/tests/test_published_gate.py` — ordering-preservation assertion checks `func.max(ImportRun.id)`
- `api/tests/test_admin_dashboard_stats.py` — utterance-count fixture converted
- `api/tests/test_phase44_resolve_table_contract.py` — client-side leak guard checks `ImportRun`
- `api/tests/test_migration_0022_person_name_authority.py` — historical `pipeline_runs` reference preserved with explanatory comment; downgrade fixture now truncates leftover data before downgrading past migration 0026
- `tests/test_schema.py` — `EXPECTED_TABLES` names `import_run`; live-schema absence/presence assertions added; `test_no_create_all_in_codebase`'s nested-`tests/`-directory bug fixed
- `tests/test_models_import.py` — expected table set, renamed status test, two new exhaustiveness tests, renamed index assertion
- `.planning/phases/47-provenance-foundation/deferred-items.md` — documents both cross-file issues found during full-suite verification
- `.planning/WINDOWS.md` — entry #4 marked fixed, new entry #5 recorded for the pre-existing SideEnum bug

## Decisions Made

- **`test_migration_0022_person_name_authority.py` keeps `pipeline_runs` literally.** This module is pinned to alembic revision 0021/0022 (predating migration 0026's rename). Renaming this reference to `import_run` would TRUNCATE a table that does not exist yet at that revision, breaking the test. Documented inline.
- **Two cross-file test-suite bugs, found only once the full suite could finally collect and run together, were fixed rather than deferred**, because both blocked this plan's own explicit acceptance criteria (`api/tests tests -q` exiting 0). Both fixes are minimal, narrowly scoped, and restore each function's own already-documented intent — neither is an architectural change:
  - `test_no_create_all_in_codebase` (Rule 1 — bug): its docstring already promised "excludes test files," but the `rglob` walk over `api/`/`pipeline/` did not actually skip nested `tests/` subdirectories, so a file at `api/tests/test_phase44_descriptor_rename.py` (Phase 44, untouched by this plan) tripped it by containing the literal string `"Base.metadata.create_all"` inside its OWN assertion text.
  - `test_migration_0022_person_name_authority.py`'s `_baseline_at_0021` fixture (Rule 3 — blocking): assumed an empty database before downgrading past migration 0026; fixed by truncating `utterances, import_run` first (scotus_test only).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `test_no_create_all_in_codebase`'s nested-`tests/`-directory false positive**
- **Found during:** Task 2, final full-suite verification run
- **Issue:** The function's `search_dirs` walk (`api/`, `alembic/`, `pipeline/`) does not exclude each directory's own `tests/` subdirectory, contrary to its own docstring's claim ("excludes test files"). `api/tests/test_phase44_descriptor_rename.py` (Phase 44, unrelated to this plan) contains the literal string `"Base.metadata.create_all"` inside its own assertion message, tripping the check the first time `api/tests` and `tests/` were ever collected together in one process (previously walled off by `test_admin_dev_routes.py`'s collection error).
- **Fix:** Skip any path segment named `tests` (excluding the file's own basename) during the `rglob` walk.
- **Files modified:** `tests/test_schema.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_schema.py::test_no_create_all_in_codebase -q` — 1 passed.
- **Committed in:** `e628d2011` (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed `test_migration_0022_person_name_authority.py`'s downgrade-assumes-empty-database bug**
- **Found during:** Task 2, final full-suite verification run
- **Issue:** `_baseline_at_0021`'s `command.downgrade(alembic_config, BASELINE_REVISION)` call passes through migration 0026's `downgrade()`, which recreates `pipeline_runs` empty and re-adds `utterances.pipeline_run_id`'s FK against it. `api/tests/test_admin_dev_routes.py`'s corpus-reset tests deliberately leave 4 fixture arguments (and their `import_run`/`utterances` rows) behind — that endpoint's whole purpose is to seed a database, not clean up after itself — so once that file's collection error was fixed (this plan's own Task 1), its tests ran for the first time ever alongside `test_migration_0022`'s downgrade tests, and the leftover rows broke the downgrade with `ForeignKeyViolationError: ... utterances_pipeline_run_id_fkey`. Reproduced in isolation via `pytest api/tests/test_migration_0022_person_name_authority.py -q` against a `scotus_test` database carrying leftover rows.
- **Fix:** `_baseline_at_0021` now checks whether `import_run` currently exists and, if so, truncates `utterances, import_run CASCADE` (scotus_test only, never `DATABASE_URL`, never touching migration 0026 itself) immediately before the downgrade call.
- **Files modified:** `api/tests/test_migration_0022_person_name_authority.py`
- **Verification:** `./.venv/bin/python -m pytest api/tests/test_migration_0022_person_name_authority.py -q` — all 7 tests pass (previously 7 errors); full `api/tests tests -q` — 800 passed, 0 failed.
- **Committed in:** `e628d2011` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were necessary to satisfy this plan's own `api/tests tests -q` exits-0 acceptance criterion, are narrowly scoped, and restore each function's own already-documented intent rather than introducing new behavior. Neither is an architectural change.

## Issues Encountered

- **A bare full-suite `./.venv/bin/python -m pytest -q` (1054 collected) shows 4 failures, all in `api/tests/test_phase44_argument_role_roundtrip.py`.** This is a pre-existing bug from Phases 5/44 (both files predate Phase 47 by a wide margin), fully reproducible in isolation with no file this plan touched: `./.venv/bin/python -m pytest tests/test_admin_router.py api/tests/test_phase44_argument_role_roundtrip.py -q` reproduces the same 4 failures. Root cause: `tests/test_admin_router.py` intentionally `del sys.modules[...]`s and reimports every `api.*` module mid-suite (a documented pattern per `api/tests/conftest.py`'s own docstring); `pytest.ini`'s `testpaths = tests pipeline/tests api/tests` collects `tests/` (and this reimport) before `api/tests/`, so `ResolveRowUpdate` (imported at module level in the affected test file, before the reimport) is bound to a stale `SideEnum` class object, while the test body's own function-local `SideEnum` import resolves to the new one — an `isinstance()` check across two distinct-but-equal-valued class objects fails. This does NOT reproduce under this plan's own acceptance-criteria invocation (`pytest api/tests tests -q`, explicit-path order, no reimport-before-collection issue). Documented in full in `.planning/phases/47-provenance-foundation/deferred-items.md` and logged as WINDOWS.md entry #5 (open, out of scope for 47-05 — neither file is in this plan's `files_modified`, and the fix is either changing `test_admin_router.py`'s reimport strategy or making `ResolveRowUpdate`'s import function-local in the affected file, unrelated to the provenance/import_run conversion this phase is about).
- No other issues. All items resolved as described in Deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `api/tests` (33 test files including the 5 converted in Task 1 and the 8 in Task 2) and both root schema-contract test files now collect and pass in full against the `import_run` schema — 800 passed, 10 skipped, 0 failed on `./.venv/bin/python -m pytest api/tests tests -q`.
- All 3 parametrized shapes of `tests/test_pytest_isolation_invocation_shapes.py` (the CLAUDE.md-named D-03 regression test) now pass, closing the gap that 47-01/47-03 tracked as open.
- `PipelineRun`/`PipelineRunStatus`/`pipeline_run_id`/`pipeline_runs`/`PIPELINE_RUN_STRATEGY` no longer appear anywhere in `api/tests/` or `tests/` except two deliberately-preserved, documented exceptions: `test_migration_0022_person_name_authority.py`'s revision-0021-pinned TRUNCATE (historically accurate for that migration's baseline) and `tests/test_schema.py`'s own new absence-assertion (which must name the retired string to assert it is gone).
- **47-06 (full-suite gate) inherits:** a clean `api/tests tests -q` run, plus one known, pre-existing, unrelated-to-Phase-47 gap surfaced only by the bare full-suite `pytest -q` invocation — `api/tests/test_phase44_argument_role_roundtrip.py`'s 4 failures under `testpaths` collection order (see Issues Encountered above and `deferred-items.md`). 47-06 should decide whether this gap needs a fix before Phase 47 ships, since it is the first plan to actually be able to run the true bare `pytest -q` end to end.
- **Known gap for a follow-up plan or `/gsd-review-backlog`:** the `test_admin_router.py` reimport-vs-module-level-import ordering fragility this plan exposed and diagnosed but did not fix (out of scope — pre-existing, unrelated files).

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `.planning/phases/47-provenance-foundation/47-05-SUMMARY.md`
- FOUND: `.planning/phases/47-provenance-foundation/deferred-items.md`
- FOUND commit: `9ef87502d`
- FOUND commit: `e628d2011`
- FOUND commit: `bad35a159`
- FOUND commit: `ca01f47a7`
