---
phase: 05-admin-foundation
plan: 02
subsystem: api
tags: [fastapi, auth, admin, dependency-injection, router, python]

# Dependency graph
requires:
  - phase: 05-01
    provides: settings.admin_token field (ADMIN_TOKEN env var) in api/core/config.py
provides:
  - api/routers/admin.py with verify_admin_token dependency and GET /api/admin/health route
  - Admin router mounted in api/main.py at prefix /api/admin
  - Router-level X-Admin-Token auth dependency (single swap point for Phase 6 HMAC cookies)
  - 11 static-analysis smoke tests in tests/test_admin_router.py
affects: [06-auth, 07-pipeline-runner, 08-people-editor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Router-level dependency injection via APIRouter(dependencies=[Depends(verify_admin_token)]) for surgical Phase 6 replacement
    - Full prefix /api/admin (not bare /admin) to avoid SvelteKit /admin/* page route collision
    - verify_admin_token as async function returning None — FastAPI dependency protocol for auth guards
    - Smoke import test uses os.environ.setdefault to supply required env var without polluting process env

key-files:
  created:
    - api/routers/admin.py
    - tests/test_admin_router.py
  modified:
    - api/main.py

key-decisions:
  - "Admin router prefix is /api/admin (D-09): full prefix avoids naming collision with SvelteKit's /admin/* page routes"
  - "verify_admin_token dependency placed at APIRouter construction level (D-12): Phase 6 swaps it in one place without touching route signatures"
  - "GET /api/admin/health is the only Phase 5 route (D-11): exists solely so the 401 dependency can be smoke-tested before Phase 7 adds real routes"
  - "get_db imported in admin.py even though health route does not use it: Phase 7 can add DB routes without structural imports change"
  - "Smoke import test sets ADMIN_TOKEN via os.environ.setdefault: keeps test self-contained without requiring conftest changes"

patterns-established:
  - "Router-level auth dependency: place in APIRouter(dependencies=[...]) not per-route; allows wholesale replacement in one location"
  - "Full route prefix for admin: /api/admin not /admin — prevents ambiguity with SvelteKit page routes on the same domain"
  - "Token never echoed: verify_admin_token compares and discards; 401 detail is constant 'Unauthorized' (T-05-05)"

requirements-completed: [INFRA-A1]

# Metrics
duration: 2min
completed: 2026-06-15
---

# Phase 05, Plan 02: Admin Router Summary

**FastAPI admin router at /api/admin with router-level X-Admin-Token auth dependency, GET /health smoke-test route, and two-line mount in api/main.py — Phase 6 swaps the auth in one place**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-06-15T20:54:09Z
- **Completed:** 2026-06-15T20:56:17Z
- **Tasks:** 2 (TDD: test → feat for each)
- **Files modified:** 3

## Accomplishments
- `api/routers/admin.py` defines `verify_admin_token` (raises HTTPException 401 on mismatch) and mounts it at the `APIRouter` level so Phase 6 replaces it in one place
- Router prefix `/api/admin` (full path per D-09) avoids collision with SvelteKit's `/admin/*` pages
- `GET /api/admin/health` returns `{"status": "ok"}` — smoke-test target for verifying the 401 dependency before Phase 7 routes land
- `api/main.py` updated with two lines: import and `app.include_router(admin_router.router)` after existing routers — zero changes to arguments/cases/people routers or the public `/health` probe
- 11 static-analysis smoke tests verify router structure, 401 behavior, no `create_all`, main.py mounting, and existing-router regression guard

## Task Commits

Each task was committed atomically with TDD RED/GREEN discipline:

1. **Task 1 RED: Failing tests for admin router** - `53268dd` (test)
2. **Task 1 GREEN: Create admin router** - `5f352bf` (feat)
3. **Task 2 RED: Failing tests for main.py mount** - `8bf2706` (test)
4. **Task 2 GREEN: Mount admin router in main.py** - `01faf02` (feat)

## Files Created/Modified
- `api/routers/admin.py` - verify_admin_token dependency, router at prefix /api/admin, GET /health route, get_db imported for Phase 7
- `tests/test_admin_router.py` - 11 static-analysis smoke tests (no DB, no ASGI client per D-15)
- `api/main.py` - Added admin_router import and include_router call; existing routers unchanged

## Decisions Made
- Placed `os.environ.setdefault("ADMIN_TOKEN", "test-smoke-import")` inside the smoke import test rather than adding ADMIN_TOKEN to conftest — keeps the test self-contained and avoids leaking env state to other tests
- Used `os.environ.setdefault` (not `os.environ["ADMIN_TOKEN"] = ...`) so a pre-set ADMIN_TOKEN from the shell (e.g., `ADMIN_TOKEN=test pytest`) takes precedence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed smoke import test to set ADMIN_TOKEN before import**
- **Found during:** Task 2 GREEN verification (running tests without ADMIN_TOKEN env prefix)
- **Issue:** The test comment stated "The pytest environment sets ADMIN_TOKEN=test via conftest.py" but conftest.py only calls `load_dotenv()` — .env does not contain ADMIN_TOKEN. Without the env var, pydantic-settings raises ValidationError when `settings = Settings()` is called at config import time, causing the smoke import to fail.
- **Fix:** Added `os.environ.setdefault("ADMIN_TOKEN", "test-smoke-import")` inside the test function body, before the module cache flush and import attempt.
- **Files modified:** `tests/test_admin_router.py`
- **Verification:** `python -m pytest tests/test_admin_router.py tests/test_cases_api.py -x -q` passes 17/17 without pre-set env var
- **Committed in:** `01faf02` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in smoke import test setup)
**Impact on plan:** Necessary correctness fix. Test now works standalone without requiring the shell caller to set ADMIN_TOKEN.

## Issues Encountered
None beyond the deviation documented above.

## Threat Model Compliance
- T-05-04 (Spoofing): `dependencies=[Depends(verify_admin_token)]` at router level enforces the check on every route; missing/wrong header → 401 before handler runs
- T-05-05 (Information Disclosure): `verify_admin_token` compares and discards; token value never logged or echoed; 401 detail is constant "Unauthorized"
- T-05-06 (Elevation of Privilege): Throwaway token accepted per plan; router-level placement keeps Phase 6 swap surgical
- T-05-07 (Tampering): Zero `app/` files touched (D-14); no SvelteKit attack surface introduced

## Next Phase Readiness
- Phase 6 (auth) can replace `verify_admin_token` with HMAC session-cookie auth in one location: the `dependencies=[...]` argument in `api/routers/admin.py`
- Phase 7 (pipeline runner) can add routes to `api/routers/admin.py` without structural changes — `get_db` is already imported
- Full test suite passes: 41/41 with no regressions

## Self-Check: PASSED

- api/routers/admin.py: FOUND
- api/main.py (contains admin_router): FOUND
- tests/test_admin_router.py: FOUND
- .planning/phases/05-admin-foundation/05-02-SUMMARY.md: FOUND
- Commit 53268dd (test RED Task 1): FOUND
- Commit 5f352bf (feat GREEN Task 1): FOUND
- Commit 8bf2706 (test RED Task 2): FOUND
- Commit 01faf02 (feat GREEN Task 2): FOUND

---
*Phase: 05-admin-foundation*
*Completed: 2026-06-15*
