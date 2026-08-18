# Deferred Items — Phase 25

Out-of-scope discoveries logged during execution (Scope Boundary rule — not fixed here).

## Pre-existing test failures unrelated to Phase 25 Plan 01

Found while running the full `api/tests` suite as a sanity check after Plan 01 Task 1.
Both failures are unrelated to `admin_jobs.py`/`admin_arguments.py` and predate this plan's changes
(confirmed via `git stash` showing the same failures with Phase 25 Plan 01 changes removed).

- `api/tests/test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_people.py::test_get_person`
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
- `api/tests/test_people.py::test_get_person_404`

Root cause: `RuntimeError: Database session factory is not initialised — lifespan may not have
completed startup.` — these tests exercise a FastAPI route via a test client without the
app's `lifespan` context having run, so `AsyncSessionLocal` is `None` in `api/core/database.py`.
This is a pre-existing test-harness gap, not a Phase 25 regression.

Original disposition at Plan 01: not fixed (out of scope per the Scope Boundary rule).
Closed by the 2026-08-18 cross-phase UAT audit — see the resolution fields below.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
