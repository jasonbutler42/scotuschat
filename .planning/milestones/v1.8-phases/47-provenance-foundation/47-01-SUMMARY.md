---
phase: 47-provenance-foundation
plan: 01
subsystem: database
tags: [postgresql, alembic, sqlalchemy, provenance, migration]

# Dependency graph
requires: []
provides:
  - "import_run table + import_source/import_method PG enum types (migration 0026), replacing pipeline_runs"
  - "ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes in api/models/models.py"
  - "utterances.import_run_id FK repoint; utterances.strategy dropped"
  - "Corpus write path (pipeline/commands/import_convokit.py) stamping source=CORPUS/method=DIRECT/external_id at row creation"
  - "pipeline/tests/test_import_run_provenance.py -- 7 passing tests proving the corpus/direct leg of D-06's guardrail end-to-end"
  - "Both DATABASE_URL (dev) and TEST_DATABASE_URL (scotus_test) at Alembic head 0026 with live-schema shape confirmed"
affects: [47-02, 47-03, 47-04, 47-05, 47-06]

# Actuals (#2632)
actuals:
  tokens: 11300
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native PostgreSQL enum types for closed-vocabulary columns (import_source/import_method), matching the existing SAEnum(..., values_callable=...) idiom used by SideEnum/ArgumentStatusEnum"
    - "DO-block-guarded CREATE TYPE (pg_type existence check) for brand-new enum types in a clean-rebuild migration"

key-files:
  created:
    - alembic/versions/0026_import_run_provenance.py
    - pipeline/tests/test_import_run_provenance.py
  modified:
    - api/models/models.py
    - pipeline/commands/import_convokit.py
    - conftest.py
    - pipeline/tests/conftest.py
    - api/services/admin_dev.py
    - pipeline/commands/ingest.py
    - pipeline/commands/resolve.py

key-decisions:
  - "Task 1 (operator-resolved via blocking checkpoint): native PostgreSQL enum types for import_source/import_method, not varchar+CHECK -- DB-level exhaustiveness rejects out-of-vocabulary writes at the storage boundary (T-47-06) and matches the dominant in-repo idiom (5 of 7 existing enum-shaped columns, including import_run.status on this same table). Accepted cost: values cannot be dropped later; adding one requires ALTER TYPE ... ADD VALUE outside a transaction."
  - "Rule 3 auto-fix: pipeline/commands/ingest.py and pipeline/commands/resolve.py received a minimal identifier-only rename (PipelineRun->ImportRun, PipelineRunStatus->ImportRunStatus, Utterance.pipeline_run_id->import_run_id) even though neither file is in this plan's files_modified list. Without it, import_convokit.py's own module-level imports (_derive_slug from ingest.py, normalize_label from resolve.py) raised ImportError at collection time, which is directly caused by this task's models.py rename and blocked this task's own required test file from running at all. No source=/method= stamping was added to either file -- that functional conversion remains plan 47-02's scoped work; both files still raise IntegrityError/AttributeError if actually invoked, matching the plan's own <intermediate_state_note> expectation."

patterns-established:
  - "Provenance columns (source/method) are NOT NULL with no ORM-level default -- every writer must declare them explicitly (D-02); the DB itself is the enforcement point, not application code."

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-04, PROV-06]

coverage:
  - id: D1
    description: "import_run table + import_source/import_method PG enums created by migration 0026, applied to both DATABASE_URL and TEST_DATABASE_URL"
    requirement: "PROV-01"
    verification:
      - kind: integration
        ref: "alembic current (both DATABASE_URL and TEST_DATABASE_URL) -- 0026 (head)"
        status: pass
      - kind: integration
        ref: "live-schema assertion script -- information_schema.tables/columns, pg_type/pg_enum checks against both databases"
        status: pass
    human_judgment: false
  - id: D2
    description: "Corpus importer stamps source=CORPUS/method=DIRECT/external_id at row creation; pdf_path/pdf_url stay NULL; Argument.oyez_transcript_id unchanged"
    requirement: "PROV-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_import_stamps_source_corpus_method_direct"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_import_populates_external_id"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_import_leaves_pdf_fields_null"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_import_preserves_argument_oyez_transcript_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "Corpus reimport is idempotent on Argument; empty-utterance corpus import still writes a provenance-carrying run row (PROV-05 empty/adjacency edges)"
    requirement: "PROV-05"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_reimport_is_idempotent_on_argument_and_stamps_provenance"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_corpus_import_writes_run_row_when_no_utterances"
        status: pass
    human_judgment: false
  - id: D4
    description: "import_run.source/method reject NULL at the storage boundary (T-47-06)"
    requirement: "PROV-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_import_run_rejects_missing_source_and_method"
        status: pass
    human_judgment: false
  - id: D5
    description: "tests/test_pytest_isolation_invocation_shapes.py regression test, listed in Task 3's <verify>"
    verification:
      - kind: integration
        ref: "tests/test_pytest_isolation_invocation_shapes.py (all 3 parametrized shapes)"
        status: fail
    human_judgment: true
    rationale: "Cannot pass until plans 47-02/47-03 land -- see Deviations. Not a defect in this plan's own deliverables; a human/verifier should confirm this is the expected, plan-acknowledged intermediate RED state before treating it as a regression."

duration: ~55min (continuation session)
completed: 2026-08-17
status: complete
---

# Phase 47 Plan 01: Provenance Foundation Summary

**Landed the `import_run` table, `ImportSource`/`ImportMethod` native PG enums, and the corpus write path stamping declared provenance at row creation, proven end-to-end by 7 new tests reading provenance directly off freshly written rows.**

## Performance

- **Duration:** ~55 min (continuation session; original checkpoint agent made zero commits)
- **Completed:** 2026-08-17T21:03Z
- **Tasks:** 3 (Task 1 checkpoint resolved by operator before this continuation; Tasks 2-3 executed here)
- **Files modified:** 9 (2 created, 7 modified)

## Accomplishments
- Migration `0026` creates `import_source`/`import_method` PG enum types (DO-block guarded), renames `pipeline_run_status` -> `import_run_status` in place, truncates+drops `pipeline_runs` (D-01 clean rebuild), creates `import_run` fresh with `source`/`method` NOT NULL + nullable `external_id`, and repoints `utterances.import_run_id` -> `import_run.id` while dropping `utterances.strategy` (D-05)
- `api/models/models.py`: `PipelineRun` -> `ImportRun`, `PipelineRunStatus` -> `ImportRunStatus`, new `ImportSource`/`ImportMethod` enum classes; `Utterance.pipeline_run_id` -> `import_run_id`, `Utterance.strategy` dropped
- `pipeline/commands/import_convokit.py`'s corpus writer stamps `source=ImportSource.CORPUS`, `method=ImportMethod.DIRECT`, `external_id=conversation_id` at row creation; `Argument.oyez_transcript_id` and its idempotency-key query are untouched (dual-write, not a relocation)
- All three hardcoded `"pipeline_runs"` table-name sites (`conftest.py` `_WATCHED_TABLES`, `pipeline/tests/conftest.py`'s two TRUNCATE lists, `api/services/admin_dev.py`'s `TRUNCATE_SQL`) updated to `import_run` in this same commit (T-47-02/T-47-03)
- New `pipeline/tests/test_import_run_provenance.py`: 7 tests covering PROV-01/02/04/05/06's corpus/direct leg -- source/method stamped, external_id dual-write, pdf fields NULL, oyez_transcript_id preserved, reimport idempotency, empty-utterance edge, NOT NULL rejection
- Migration `0026` applied to and verified against **both** `DATABASE_URL` (dev, database `scotus`) and `TEST_DATABASE_URL` (`scotus_test`) -- both report `0026 (head)`; a full downgrade/re-upgrade cycle was exercised against `scotus_test` to prove migration reversibility before touching the dev database
- Live-schema assertions (table presence, column nullability, `udt_name`, `pg_enum` label ordering) confirmed identical on both databases

## Task Commits

Each task was committed atomically:

1. **Task 1: Decide the closed-vocabulary representation for source and method** - resolved by operator via blocking checkpoint (native-pg-enum) -- no code commit of its own; the decision is implemented in Task 2's commit.
2. **Task 2: End-to-end corpus provenance -- schema, model, corpus writer, read-back** - `c73e4442d` (feat)
3. **Task 3: Apply migration 0026 to the dev database and assert the live schema** - no source files changed (per this task's own `<files>` spec -- it only changes/asserts live database state); no commit.

**Plan metadata:** (this commit)

## Files Created/Modified
- `alembic/versions/0026_import_run_provenance.py` - Clean-rebuild migration: `import_source`/`import_method` types, `import_run` table, utterance FK repoint, `strategy` drop
- `pipeline/tests/test_import_run_provenance.py` - 7 end-to-end provenance tests (corpus/direct leg of D-06)
- `api/models/models.py` - `ImportRun`/`ImportSource`/`ImportMethod`/`ImportRunStatus` ORM shapes
- `pipeline/commands/import_convokit.py` - Corpus writer stamps declared provenance at row creation
- `conftest.py` - `_WATCHED_TABLES` renamed entry
- `pipeline/tests/conftest.py` - Both TRUNCATE lists renamed
- `api/services/admin_dev.py` - `TRUNCATE_SQL` renamed
- `pipeline/commands/ingest.py` - Minimal identifier-only rename (Rule 3, see Deviations)
- `pipeline/commands/resolve.py` - Minimal identifier-only rename (Rule 3, see Deviations)

## Decisions Made
- **Task 1 (operator, via blocking checkpoint):** native PostgreSQL enum types for `source`/`method`, not `varchar`+CHECK. Rationale: DB-level exhaustiveness at the storage boundary (T-47-06) and consistency with 5 of 7 existing enum-shaped columns in this codebase, including `import_run.status` on this very table. Accepted cost: PG cannot drop enum values later.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Minimal identifier rename in `pipeline/commands/ingest.py` and `pipeline/commands/resolve.py`**
- **Found during:** Task 2 (running `pipeline/tests/test_import_run_provenance.py` for the first time)
- **Issue:** `pipeline/commands/import_convokit.py` (in this plan's scope) imports `_derive_slug` from `ingest.py` and `normalize_label` from `resolve.py` at module level. Both files still had top-level `from api.models.models import (..., PipelineRun, PipelineRunStatus, ...)`, which raised `ImportError` the instant `api/models/models.py` was renamed (this task's own Task 2a change) -- blocking `import_convokit.py` from importing at all, and with it this task's own required test file. The plan's `<intermediate_state_note>` claimed `import_convokit.py` "imports only `api.domain.person_names`, `api.services.argument_uniqueness`, and `api.models.models`" -- this was incomplete; it also transitively imports `ingest.py` and `resolve.py`.
- **Fix:** Renamed `PipelineRun`->`ImportRun`, `PipelineRunStatus`->`ImportRunStatus`, and `Utterance.pipeline_run_id`->`Utterance.import_run_id` in both files' import statements and the class-name usages that participate in that same rename (construction sites, `session.get(...)` calls, status assignments, one query filter each). Did **not** add `source=`/`method=` stamping to either file's `ImportRun`/run construction -- that is plan 47-02's scoped functional work per RESEARCH.md's writer-mapping table. Both files will still raise `IntegrityError` (NOT NULL) or otherwise fail if actually invoked before 47-02 lands, matching the plan's own `<intermediate_state_note>` ("pipeline/commands/{ingest,parse,resolve}.py ... are RED").
- **Files modified:** `pipeline/commands/ingest.py`, `pipeline/commands/resolve.py`
- **Verification:** `pipeline/tests/test_import_run_provenance.py` now imports and runs cleanly (7/7 pass); `python3 -m compileall` clean on both files.
- **Committed in:** `c73e4442d` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to unblock this task's own deliverable (the corpus provenance test file). No functional work was pulled forward from plan 47-02 -- only the identifier rename needed to keep the module chain importable.

## Issues Encountered

- **`tests/test_pytest_isolation_invocation_shapes.py` (Task 3's `<verify>`) cannot currently pass.** All three of its parametrized invocation shapes run `api/tests/test_db_isolation_probe.py` (directly or via the bare/testpaths-driven shape's full collection), and that file's `autouse=True` `_api_lifespan` fixture (`api/tests/conftest.py`) does `from api.main import app`, which transitively imports `api.routers.admin`, which still does `from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, PipelineRun` -- and `PipelineRun` no longer exists. `api/routers/admin.py` (plus `api/services/arguments.py`, `admin_arguments.py`, `admin_jobs.py`, `api/schemas/admin_jobs.py`/`utterance.py`) are explicitly `47-03-PLAN.md`'s `files_modified` list, not this plan's. Fixing this test now would mean pulling forward the bulk of plan 47-03's scoped work, which risks conflicting with that plan's own detailed task breakdown.
  - **Resolution:** Left unfixed, as the plan's own `<intermediate_state_note>` explicitly anticipates the wider test suite being RED until waves 2/3 land ("api/routers/admin.py ... and most of the existing test suite are RED. That is expected and planned -- plans 47-02 and 47-03 convert them (wave 2)"). Task 3's acceptance-criteria list including this specific regression test appears to be a planning oversight -- the note didn't anticipate that this test's own subprocess invocations would hit the same collection-time breakage. Logged to `.planning/WINDOWS.md` (kind: `unrun-verify`, phase 47) so it stays visible at ship time. All 6 of Task 3's other acceptance criteria (both databases at `0026 (head)`, full live-schema shape match, `pipeline/tests/test_import_run_provenance.py` green) passed cleanly.
  - This is expected to resolve naturally once plan 47-03 lands (`api/routers/admin.py` converted) and plans 47-04/47-05 convert the remaining test-suite consumers.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `import_run` schema, ORM shapes, and the corpus write path are in place and proven end-to-end on both databases -- plan 47-02 (PDF-path writers: `ingest.py`/`parse.py`/`resolve.py`) and plan 47-03 (API/service layer re-point) can now build directly on `ImportRun`/`ImportSource`/`ImportMethod` without any further schema changes.
- **Known gap for the next wave to inherit:** `pipeline/commands/ingest.py` and `resolve.py` are import-safe but functionally incomplete (no `source`/`method` stamped) -- plan 47-02 must add the actual stamping, not just rely on this plan's identifier rename.
- **Blocker for 47-06 (full-suite gate):** the full suite remains collection-broken until 47-03 converts `api/routers/admin.py` and the other API-layer files that `api/tests/conftest.py`'s autouse app-lifespan fixture pulls in. This is expected per the plan's own wave sequencing, not a new blocker introduced here.

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `alembic/versions/0026_import_run_provenance.py`
- FOUND: `pipeline/tests/test_import_run_provenance.py`
- FOUND: `.planning/phases/47-provenance-foundation/47-01-SUMMARY.md`
- FOUND commit: `c73e4442d`
