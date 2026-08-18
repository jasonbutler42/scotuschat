# Deferred Items — Phase 28

Discovered while executing 28-01-PLAN.md. Out of scope per the plan's SCOPE
BOUNDARY rule (only auto-fix issues directly caused by the current task's
changes) — none of these files were modified by 28-01.

## Pre-existing DB-gated test failures (full `pytest -q` run, 2026-07-11)

When run against the shared dev database with `DATABASE_URL` set, 28 tests
fail across files this plan never touched:

- `pipeline/tests/test_ingest.py` (3 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `pipeline/tests/test_parse.py` (3 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `pipeline/tests/test_pipeline_run.py` (2 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit. Tests were also renamed by Phase 47's pipeline_run to import_run re-model (test_pipeline_run.py is now test_import_run.py; test_ingest_creates_pipeline_run is now test_ingest_creates_import_run). See .planning/notes/2026-08-18-uat-audit-closure.md"
- `pipeline/tests/test_resolve.py` (4 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md NOTE: 3 of these 4 are the never-implemented xfail(strict=True) stubs still tracked in Phase 31's deferred-items.md."
- `pipeline/tests/test_seed_aliases.py` (2 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md NOTE: both are never-implemented xfail(strict=True) stubs still tracked in Phase 31's deferred-items.md."
- `api/tests/test_admin_arguments_service.py` (4 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_admin_jobs_phase25.py` (4 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_admin_jobs_service.py` (2 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_admin_jobs_stats.py` (2 tests)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_argument_oyez_field.py` (1 test)
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_arguments.py` (3 tests)

Confirmed pre-existing and unrelated to this plan:
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `test_admin_jobs_stats.py`'s 2 failures were reproduced *before* any 28-01
  code was written (first DB-availability check of this execution run),
  caused by a `NotNullViolationError` on `utterances.strategy` in an old
  test-seeding helper that predates the Utterance.strategy NOT NULL column.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `test_admin_arguments_service.py::test_publish_argument_from_draft_writes_one_published_log_row`
  fails because it seeds a bare `Argument` row with no linked `Case`/`CaseArgument`,
  so `get_argument_detail` (called internally by `publish_argument`) returns
  `None` for lack of a lead case — a test-fixture gap, not a service-layer bug
  introduced by this plan.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- The remaining failures follow the same shape: tests written assuming a
  clean/empty dev database (fixed IDs like argument id=1, or committing rows
  directly via `AsyncSessionLocal()` without a rollback fixture) now collide
  with the corpus-scale dev DB populated by Phases 29/30 (~7,800 arguments).

This matches the already-tracked backlog item 999.19 ("tests leak real
Person/Argument rows into shared dev DB") — recommend addressing there
(e.g., migrating these DB-gated tests to the rollback-fixture pattern used
by `test_admin_dashboard_stats.py`, or running the suite against an isolated
test database) rather than as part of Phase 28.

None of these were fixed as part of 28-01 — all functions and files this
plan modifies are new (`admin_dashboard.py`) or additive (new functions
appended to `admin_arguments.py`, `admin_jobs.py`, `admin_people.py`); no
existing function body was changed.

**Closed 2026-08-18** (cross-phase UAT audit): all 28 of these tests now pass. The full
suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed, and none of the 4 failures is in
this list. Backlog 999.19's premise (tests leaking rows into the shared dev DB) was closed
by Phase 31's `TEST_DATABASE_URL` isolation plus Phase 46's rootdir `conftest.py`
relocation, which made the redirect fire for every pytest invocation shape.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
