# Deferred Items — Phase 25

Out-of-scope discoveries logged during execution (Scope Boundary rule — not fixed here).

## Pre-existing test failures unrelated to Phase 25 Plan 01

Found while running the full `api/tests` suite as a sanity check after Plan 01 Task 1.
Both failures are unrelated to `admin_jobs.py`/`admin_arguments.py` and predate this plan's changes
(confirmed via `git stash` showing the same failures with Phase 25 Plan 01 changes removed).

- `api/tests/test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`
- `api/tests/test_people.py::test_get_person`
- `api/tests/test_people.py::test_get_person_404`

Root cause: `RuntimeError: Database session factory is not initialised — lifespan may not have
completed startup.` — these tests exercise a FastAPI route via a test client without the
app's `lifespan` context having run, so `AsyncSessionLocal` is `None` in `api/core/database.py`.
This is a pre-existing test-harness gap, not a Phase 25 regression.

Status: not fixed (out of scope for Plan 01 per Scope Boundary rule).
