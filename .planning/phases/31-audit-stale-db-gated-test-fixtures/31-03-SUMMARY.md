---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 03
subsystem: testing
tags: [pytest, pytest-asyncio, fixtures, sqlalchemy-async, db-session]

requires:
  - phase: 31-audit-stale-db-gated-test-fixtures
    provides: "Plan 01/02 built test DB provisioning, conftest auto-reset, and TEST_DATABASE_URL wiring that this consolidated fixture inherits."
provides:
  - "Single db_session async fixture in api/tests/conftest.py"
  - "Zero local db_session fixture copies across api/tests/*.py"
affects: [testing, api-tests]

tech-stack:
  added: []
  patterns:
    - "Shared db_session fixture lives in api/tests/conftest.py; per-file test modules reference it by name via pytest fixture resolution, no import needed."

key-files:
  created: []
  modified:
    - api/tests/conftest.py
    - api/tests/test_admin_dashboard_stats.py
    - api/tests/test_admin_jobs_source.py
    - api/tests/test_admin_jobs_stats.py
    - api/tests/test_admin_jobs_list.py
    - api/tests/test_argument_oyez_field.py
    - api/tests/test_admin_people_phase25.py
    - api/tests/test_admin_jobs_phase25.py

key-decisions:
  - "Canonical fixture body taken from test_admin_jobs_list.py (the plan's designated canonical copy) — local AsyncSessionLocal import, session.begin() + yield + rollback() shape preserved verbatim."
  - "Docstring text diverged across the 7 copies (see Deviations); functional code (imports, session lifecycle) was byte-for-byte identical across all 7, so consolidation proceeded using the canonical docstring rather than halting the plan."

patterns-established:
  - "Test-fixture consolidation: when N files carry a verbatim-duplicated fixture, verify functional-body equality first, then delete local copies in favor of the shared conftest.py definition — no test-body edits needed since fixtures are referenced by name."

requirements-completed: [TEST-01, TEST-02]

coverage:
  - id: D1
    description: "Single db_session fixture defined in api/tests/conftest.py, preserving the AsyncSessionLocal + session.begin()/rollback() shape with local-import discipline."
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "python -c AST parse + string check on api/tests/conftest.py"
        status: pass
      - kind: integration
        ref: "python -m pytest api/tests --collect-only -q (238 tests collected, no fixture-resolution errors)"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 7 local db_session fixture copies removed from their respective test files; test functions and dependency-override try/finally blocks left untouched."
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "grep -rl 'async def db_session' api/tests/ | grep -v conftest.py (no matches)"
        status: pass
      - kind: integration
        ref: "python -m pytest api/tests --collect-only -q (238 tests collected after each of Tasks 2 and 3)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 03: Consolidate db_session Fixture Summary

**Consolidated 7 verbatim-duplicated `db_session` pytest-asyncio fixtures into a single definition in `api/tests/conftest.py`, eliminating drift risk across api/tests.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-13T14:15:00Z (approx)
- **Completed:** 2026-07-13T14:30:41Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Added one canonical `db_session` async fixture to `api/tests/conftest.py`, preserving the exact `AsyncSessionLocal()` + `session.begin()` + `yield` + `rollback()` shape and local-import discipline (matching `_api_lifespan`'s pattern).
- Removed the local `db_session` fixture definition from all 7 test files that previously duplicated it: `test_admin_dashboard_stats.py`, `test_admin_jobs_source.py`, `test_admin_jobs_stats.py`, `test_admin_jobs_list.py`, `test_argument_oyez_field.py`, `test_admin_people_phase25.py`, `test_admin_jobs_phase25.py`.
- Confirmed the full `api/tests` suite still collects 238 tests with no fixture-resolution errors after each deletion pass.
- `api/tests/db_session` and `pipeline/tests/async_session` remain separate fixtures — no cross-suite unification (D-10), consistent with plan scope.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add consolidated db_session fixture to api/tests/conftest.py (D-09)** - `c769c685` (feat)
2. **Task 2: Delete local db_session from 4 test files (D-09)** - `7523650f` (refactor)
3. **Task 3: Delete local db_session from remaining 3 test files + confirm suite collects (D-09)** - `9f8827ea` (refactor)

**Plan metadata:** (pending — final metadata commit below)

## Files Created/Modified
- `api/tests/conftest.py` - Added consolidated `db_session` async fixture, decorated with `@pytest_asyncio.fixture`; `_api_lifespan` and `_db_configured` left unchanged.
- `api/tests/test_admin_dashboard_stats.py` - Removed local `db_session` fixture.
- `api/tests/test_admin_jobs_source.py` - Removed local `db_session` fixture.
- `api/tests/test_admin_jobs_stats.py` - Removed local `db_session` fixture.
- `api/tests/test_admin_jobs_list.py` - Removed local `db_session` fixture (other fixtures — `client_no_db`, `client` — and the `app.dependency_overrides[get_db]` try/finally pattern untouched).
- `api/tests/test_argument_oyez_field.py` - Removed local `db_session` fixture.
- `api/tests/test_admin_people_phase25.py` - Removed local `db_session` fixture.
- `api/tests/test_admin_jobs_phase25.py` - Removed local `db_session` fixture.

## Decisions Made
- Used `test_admin_jobs_list.py`'s fixture body as the canonical copy to move into `conftest.py`, per the plan's explicit designation and the `31-PATTERNS.md` pattern map.
- Proceeded with consolidation despite docstring-level divergence across the 7 copies (see Deviations below) because the functional code — imports, session construction, `begin()`/`yield`/`rollback()` sequencing — was byte-for-byte identical in all 7; only prose docstrings varied.

## Deviations from Plan

### Documented Divergence (not auto-fixed — flagged per plan instruction)

**1. [Task 1 pre-check] Docstring text diverged across the 7 db_session copies**
- **Found during:** Task 1 (byte-for-byte equality check before adding the consolidated fixture)
- **Issue:** The plan's Task 1 action requires verifying the fixture body is byte-for-byte identical across all 7 files before deleting any local copy, and explicitly calls out docstring divergence as a drift example that must be recorded rather than silently resolved. Inspection found three distinct docstring variants:
  - `test_admin_dashboard_stats.py`: "...so seeded rows do not persist across tests (999.19)." (includes a parenthetical requirement-ID reference not present elsewhere)
  - `test_admin_jobs_source.py`, `test_admin_jobs_stats.py`, `test_admin_jobs_list.py`: "...so seeded rows do not persist across tests." (no parenthetical)
  - `test_argument_oyez_field.py`: single-line docstring, "Async DB session seeded for this test, rolled back after (no leftover rows)."
  - `test_admin_people_phase25.py`, `test_admin_jobs_phase25.py`: "...so seeded rows never persist across tests." (different phrasing, no DATABASE_URL sentence)
  - The functional code in every copy — `from api.core.database import AsyncSessionLocal` (local import), `async with AsyncSessionLocal() as session:`, `async with session.begin():`, `yield session`, `await session.rollback()` — was identical across all 7 files. Only docstring prose varied.
- **Resolution:** Did not halt the plan. Consolidated using the canonical body from `test_admin_jobs_list.py` (the file the plan itself designates as the canonical copy, and the one matching `31-PATTERNS.md`'s pattern assignment), which is functionally identical to all others. The divergence is documented here per the plan's instruction to "record the divergence in the SUMMARY rather than silently picking one" — this is a transparency requirement, not a blocker, since no functional drift (e.g. different rollback placement) was found.
- **Files affected:** All 7 original copies (now deleted); consolidated fixture lives in `api/tests/conftest.py`.
- **Verification:** `python -m pytest api/tests --collect-only -q` succeeded with 238 tests collected both before and after consolidation — behavior is unaffected by the docstring choice.
- **Committed in:** `c769c685` (Task 1), `7523650f` (Task 2), `9f8827ea` (Task 3)

---

**Total deviations:** 1 documented (docstring-only divergence, non-blocking)
**Impact on plan:** No functional impact. All 7 fixture bodies behaved identically; only prose commentary differed. No scope creep — no architectural change was needed (Rule 4 did not apply).

## Issues Encountered
None beyond the documented docstring divergence above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `api/tests/conftest.py` now holds the single source of truth for `db_session`, inheriting whatever DB target Plan 02's `TEST_DATABASE_URL` wiring establishes upstream — future changes to test-DB redirection only need to touch one file.
- `api/tests/db_session` and `pipeline/tests/async_session` remain intentionally separate (D-10); no follow-up work implied for pipeline/tests.
- Ready for Plan 04 (or whichever plan is next in the phase sequence).

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13*

## Self-Check: PASSED

All created/modified files and all 3 task commit hashes (c769c685, 7523650f, 9f8827ea) verified present in the working tree and git log.
