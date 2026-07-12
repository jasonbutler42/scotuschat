---
phase: 28-dashboard
plan: 02
subsystem: api
tags: [fastapi, pydantic, pytest, route-ordering]

# Dependency graph
requires:
  - phase: 28-dashboard
    provides: "Plan 01's seven aggregation service functions (get_argument_stats, get_recent_drafts, get_utterance_count, get_pipeline_stats, get_people_stats, get_incomplete_people, get_tenure_gap_justices) and api/schemas/admin_dashboard.py response models"
provides:
  - "Seven new GET routes on api/routers/admin.py: /arguments/stats, /arguments/recent-drafts, /people/stats, /people/incomplete, /people/tenure-gaps, /jobs/stats, /utterances/count"
  - "api/tests/test_admin_dashboard_routes.py — DB-gated proof that each literal route resolves ahead of its {id}-parameterized sibling (200, not 422)"
affects: ["28-03 (frontend dashboard load() consumes these seven endpoints)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Literal-route-before-{id}-route registration order, mirroring the existing check-duplicate precedent, applied to three new resource groups (arguments, people, jobs)"
    - "Thin 2-3 line router delegation: call Plan 01 service function, wrap result in matching admin_dashboard Pydantic schema, return it"

key-files:
  created:
    - api/tests/test_admin_dashboard_routes.py
  modified:
    - api/routers/admin.py

key-decisions:
  - "GET /utterances/count placed adjacent to /arguments/stats and /arguments/recent-drafts (both delegate to admin_arguments service functions) rather than near /people or /jobs — no {id}-sibling route exists for /utterances so there was no ordering constraint forcing a specific location"
  - "Route test file uses only a DB-gated client fixture (no client_no_db/401 auth tests) since Task 2's scope per the plan is proving 200-not-422 resolution and response shape, not re-proving router-level auth inheritance already covered by the existing admin auth test suite"

patterns-established:
  - "Every new literal sub-route carries an explicit ordering-note docstring comment naming the specific {id} sibling it must precede, matching the check-duplicate precedent's comment style"

requirements-completed: [DASH-01, DASH-03]

coverage:
  - id: D1
    description: "GET /api/admin/arguments/stats returns ArgumentStats and resolves ahead of /arguments/{argument_id} (200, not 422)"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_arguments_stats_returns_200_not_422"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/admin/people/stats returns PeopleStats and resolves ahead of /people/{person_id}"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_people_stats_returns_200"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /api/admin/jobs/stats returns PipelineStats and resolves ahead of /jobs/{job_id}"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_jobs_stats_returns_200"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /api/admin/utterances/count returns UtteranceCount"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_utterances_count_returns_200"
        status: pass
    human_judgment: false
  - id: D5
    description: "GET /api/admin/arguments/recent-drafts returns up to 5 RecentDraft rows and resolves ahead of /arguments/{argument_id}"
    requirement: "DASH-03"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_arguments_recent_drafts_returns_200_capped_at_five"
        status: pass
    human_judgment: false
  - id: D6
    description: "GET /api/admin/people/incomplete and GET /api/admin/people/tenure-gaps each return up to 5 rows and resolve ahead of /people/{person_id}"
    requirement: "DASH-03"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_people_incomplete_returns_200_capped_at_five"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_dashboard_routes.py#test_people_tenure_gaps_returns_200_capped_at_five"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every new route inherits router-level verify_admin_token auth — no per-route auth code added; no /dashboard mega-endpoint added"
    verification:
      - kind: unit
        ref: "grep 'Depends(verify_admin_token)' api/routers/admin.py (single match at router construction)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-11
status: complete
---

# Phase 28 Plan 02: Dashboard Router Endpoints Summary

**Seven thin, resource-scoped GET routes on the existing `/api/admin` router exposing Plan 01's aggregation service functions, each literal route registered before its `{id}`-parameterized sibling and proven via a DB-gated test suite to resolve 200 (not 422).**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-11
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 new)

## Accomplishments
- Added seven new GET routes to `api/routers/admin.py`: `/arguments/stats`, `/arguments/recent-drafts`, `/people/stats`, `/people/incomplete`, `/people/tenure-gaps`, `/jobs/stats`, `/utterances/count` — each a 2-3 line delegation to the matching Plan 01 service function, wrapped in the matching `admin_dashboard` Pydantic schema
- Every literal route registered strictly before its `{id}`-parameterized sibling (`/arguments/stats` and `/arguments/recent-drafts` before `/arguments/{argument_id}`; `/people/stats`, `/people/incomplete`, `/people/tenure-gaps` before `/people/{person_id}`; `/jobs/stats` before `/jobs/{job_id}`) — verified both by a live `router.routes` index-order assertion and by the DB-gated route test
- New `api/tests/test_admin_dashboard_routes.py`: 7 DB-gated tests, one per endpoint, each asserting `status_code == 200` (never 422) plus the documented response-body keys; the `/arguments/stats` test carries an explicit regression-intent comment tying it back to the Pitfall 1 route-shadowing hazard
- No new auth code added anywhere — all seven routes inherit `verify_admin_token` from the router-level dependency; no `/dashboard` mega-aggregate endpoint was created

## Task Commits

Each task was committed atomically:

1. **Task 1: Register seven dashboard routes with literal-before-{id} ordering** - `0cae423c` (feat)
2. **Task 2: DB-gated route test proving 200 (not 422) resolution and response shape** - `c14b1365` (test)

**Plan metadata:** commit pending (see below)

## Files Created/Modified
- `api/routers/admin.py` - added seven GET routes (`get_argument_stats_route`, `get_recent_drafts_route`, `get_utterance_count_route`, `get_people_stats_route`, `get_incomplete_people_route`, `get_tenure_gap_justices_route`, `get_pipeline_stats_route`) and the corresponding `api.schemas.admin_dashboard` import block
- `api/tests/test_admin_dashboard_routes.py` - new: 7 DB-gated tests, one per new endpoint, proving 200-not-422 resolution and response shape

## Decisions Made
- `GET /utterances/count` was placed next to the two new `/arguments/*` routes (both delegate to `admin_arguments` service functions) since no `{id}`-sibling route exists for `/utterances` and the plan left exact placement to executor discretion for discoverability
- The new test file omits `client_no_db`/401 auth-gate tests (present in the sibling `test_admin_arguments_routes.py` file) because Task 2's stated scope is proving 200-not-422 route resolution and response shape — router-level auth inheritance for this prefix is already covered by the existing test suite, and Task 1's acceptance criteria confirm via source assertion that no per-route auth was added

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verify commands (route-ordering import assertion; DB-gated pytest run) passed on the first attempt with no auto-fixes required.

## Issues Encountered

None. The DB-gated test suite required loading `tests/conftest.py`'s root-level `load_dotenv()` in addition to `api/tests/conftest.py`'s lifespan fixture to pick up `DATABASE_URL` for a targeted single-file pytest invocation (`pytest tests/conftest.py api/tests/test_admin_dashboard_routes.py`) — this mirrors the same test-infrastructure quirk documented in 28-01-SUMMARY.md and is not a defect in this plan's own code; all 7/7 tests pass against the live corpus-scale dev DB, and all 7/7 skip cleanly when `DATABASE_URL` is unset.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 28-03 (frontend) can now build `+page.server.ts`'s sequential-fetch `load()` against all seven live endpoints: `GET /api/admin/arguments/stats`, `/arguments/recent-drafts`, `/people/stats`, `/people/incomplete`, `/people/tenure-gaps`, `/jobs/stats`, `/utterances/count`.
- No blockers.

---
*Phase: 28-dashboard*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: api/routers/admin.py
- FOUND: api/tests/test_admin_dashboard_routes.py
- FOUND: .planning/phases/28-dashboard/28-02-SUMMARY.md
- FOUND commit: 0cae423c
- FOUND commit: c14b1365
