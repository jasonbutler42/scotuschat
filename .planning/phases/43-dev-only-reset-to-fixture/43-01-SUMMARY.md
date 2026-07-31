---
phase: 43-dev-only-reset-to-fixture
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic-settings, admin, dev-tooling, truncate, import-convokit]

# Dependency graph
requires:
  - phase: 41-canonical-corpus-fixture-selection
    provides: FIXTURES.md's confirmed four-fixture set (conversation 15169 used by this plan)
  - phase: 42-corpus-import-fidelity-diff-fix
    provides: import-convokit importer fixes for conversation 15169, which this reset's reseed path now flows through automatically
provides:
  - Settings.environment required fail-fast field (D-02), mirroring admin_token
  - api/services/admin_dev.py::reset_to_fixture — TRUNCATE (D-01, 9 named tables, roles excluded) + in-process run_import_convokit reseed of one fixture, with a post-import existence check (never trusting silent success)
  - api/routers/admin_dev.py — separate, conditionally-mounted APIRouter proving D-07's structural absence pattern
  - api/schemas/admin_dev.py — the full ResetToFixtureResponse contract (locked now for Plan 43-03's parallel frontend work)
  - Two proven test techniques: synthetic-corpus end-to-end reset test, and module-re-import route-absence/presence test (with a FastAPI-0.139-compatible route-walking helper)
affects: [43-02-state-realization, 43-03-frontend-confirm-ui, 43-04-live-uat]

# Actuals (#2632)
actuals:
  tokens: 8430
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Separate APIRouter per conditionally-mounted feature (never bolt onto an always-mounted router) — the structural mechanism for D-07"
    - "In-process pipeline command invocation via SimpleNamespace (getattr-based args reading) instead of subprocess — avoids a new process boundary for a synchronous request"
    - "Post-write existence check instead of trusting exception-absence as success, when the callee swallows per-item errors internally"
    - "FastAPI route-tree walking must handle both a flat Route list and the newer _IncludedRouter(.original_router.routes) wrapper shape, depending on installed FastAPI minor version"

key-files:
  created:
    - api/schemas/admin_dev.py
    - api/services/admin_dev.py
    - api/routers/admin_dev.py
    - api/tests/test_admin_dev_routes.py
    - tests/test_admin_dev_router_gate.py
    - .planning/phases/43-dev-only-reset-to-fixture/deferred-items.md
  modified:
    - api/core/config.py
    - api/main.py

key-decisions:
  - "environment: str given no default, placed directly after admin_token in Settings, exactly mirroring that field's fail-fast shape (D-02)"
  - "TRUNCATE_SQL names D-01's 9 tables explicitly for auditability, ending in CASCADE; roles is deliberately excluded with an explanatory comment (it's a parent, not a child, of this table set)"
  - "corpus_dir stays a Python-only keyword argument on reset_to_fixture — the HTTP test reaches the synthetic corpus by patching admin_dev_service.reset_to_fixture with a thin corpus_dir-forwarding wrapper, never by adding a request parameter"
  - "Did NOT mark DEVTOOL-01/DEVTOOL-02 complete in REQUIREMENTS.md — both require the full 4-fixture set (Plan 43-02) and the frontend gate (Plan 43-03); flipping the checkbox after a 1-fixture backend-only slice would misstate phase status. Left for the phase's final plan (43-04) or a later state-sync step."

patterns-established:
  - "Pattern 1 (RESEARCH.md): separate router + conditional include_router for any capability that must be structurally absent, not just auth-refused, in some environment"
  - "Pattern 2 (RESEARCH.md): SimpleNamespace + getattr-based args reading to call a pipeline/commands/*.py entry point in-process from API code"

requirements-completed: []  # DEVTOOL-01/02 intentionally NOT marked — see key-decisions

coverage:
  - id: D1
    description: "Settings.environment is a required, defaultless str; full pytest suite still collects and passes with it in place"
    requirement: "DEVTOOL-02"
    verification:
      - kind: unit
        ref: "api/core/config.py — Settings.model_fields['environment'].is_required() check + full suite run"
        status: pass
    human_judgment: false
  - id: D2
    description: "One HTTP POST (with valid admin token) wipes the test DB and reseeds conversation 15169 through run_import_convokit, landing status=PIPELINE with a paired PAUSED/RESOLVE AdminJob, leaving roles untouched"
    requirement: "DEVTOOL-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_wipes_and_reseeds_fixtures"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_requires_admin_token"
        status: pass
    human_judgment: false
  - id: D3
    description: "The reset endpoint 404s (not 403s) outside development, including for allow-list near-miss values, while the four pre-existing routers stay mounted"
    requirement: "DEVTOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_admin_dev_router_gate.py#test_dev_router_absent_outside_development"
        status: pass
      - kind: unit
        ref: "tests/test_admin_dev_router_gate.py#test_dev_router_present_in_development"
        status: pass
      - kind: unit
        ref: "tests/test_admin_dev_router_gate.py#test_dev_router_absent_for_allowlist_near_misses"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-31
status: complete
---

# Phase 43 Plan 1: Dev-Only Reset to Fixture — Backend Vertical Slice Summary

**One `POST /api/admin/dev/reset-to-fixture` wipes the test DB (TRUNCATE across 9 named tables, CASCADE, `roles` excluded) and reseeds conversation 15169 through the real `run_import_convokit` importer in-process, behind a separately-mounted router that's genuinely absent (404, not 403) outside `settings.environment == "development"`.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed
- **Files modified:** 8 (2 modified, 6 created)

## Accomplishments
- `Settings.environment` — a new required, defaultless `str` field (D-02), fail-fast exactly like `admin_token`
- `api/services/admin_dev.py::reset_to_fixture` — pre-flight corpus check (before any destructive statement), one-statement `TRUNCATE ... CASCADE` over D-01's 9 named tables (`roles` deliberately excluded), then an in-process `run_import_convokit` reseed of conversation 15169 with a post-import `Argument` existence check (never inferring success from silence)
- `api/routers/admin_dev.py` — a brand-new, separate `APIRouter` at `/api/admin/dev`, reusing `verify_admin_token` from `api/routers/admin.py` unchanged; `api/main.py` mounts it only when `settings.environment == "development"` (D-07)
- `api/tests/test_admin_dev_routes.py` — end-to-end test over a synthetic corpus dir proving the full wipe+reseed+auth contract, including the Phase 30 `PIPELINE`/`PAUSED`-`RESOLVE` invariant
- `tests/test_admin_dev_router_gate.py` — module-re-import test proving the router is structurally absent (404, not 403) outside development, present inside it, and that the gate is an allow-list (near-miss values also yield absence)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the required `environment` setting (D-02)** - `dde83642` (feat)
2. **Task 2: End-to-end "reset one fixture" — TRUNCATE + real-importer reseed behind the conditional mount** - `bd107923` (feat, tracer)
3. **Task 3: Prove the route is absent, not refused, outside development (DEVTOOL-02)** - `e26b81b3` (test)

_No separate plan-metadata commit issued yet — this final documentation commit (SUMMARY/STATE/ROADMAP) follows below._

## Files Created/Modified
- `api/core/config.py` — added `environment: str`, no default, documented allow-list contract
- `api/schemas/admin_dev.py` — `ResetFixtureItem`, `ResetToFixtureResponse` (full 6-field contract locked for Plan 43-03)
- `api/services/admin_dev.py` — `FIXTURE_SET` (1 entry this plan), `TRUNCATE_SQL`, `CorpusUnavailableError`, `ResetIncompleteError`, `reset_to_fixture()`
- `api/routers/admin_dev.py` — separate `APIRouter`, `POST /reset-to-fixture` handler mapping service exceptions to 503/500
- `api/main.py` — conditional `app.include_router(admin_dev_router.router)` gated on `settings.environment`
- `api/tests/test_admin_dev_routes.py` — synthetic-corpus end-to-end test (2 tests)
- `tests/test_admin_dev_router_gate.py` — module-re-import absence/presence/allow-list test (5 tests, parametrized)
- `.planning/phases/43-dev-only-reset-to-fixture/deferred-items.md` — pre-existing, unrelated Node-path-join test failure logged and confirmed out of scope

## Decisions Made
- `environment: str` has no default and sits directly after `admin_token` in `Settings`, matching that field's exact fail-fast shape and voice (D-02).
- `TRUNCATE_SQL` names all 9 of D-01's tables explicitly (not just the CASCADE-sufficient root set) for auditability, per RESEARCH.md Open Question 1's resolution; a code comment documents the 3 tables reached transitively via CASCADE and why `roles` is excluded.
- `corpus_dir` is a Python-only keyword argument on `reset_to_fixture` — never a request body/query/header field. The HTTP-level test reaches the synthetic corpus by patching `api.routers.admin_dev.admin_dev_service.reset_to_fixture` (same module object as `api.services.admin_dev`) with a thin wrapper that forwards `corpus_dir`, keeping the prohibition intact while still exercising the real HTTP path.
- Did **not** mark DEVTOOL-01/DEVTOOL-02 complete in `REQUIREMENTS.md`. Both requirements explicitly require the full 4-fixture reseed (DEVTOOL-01: "reseeds exactly the CORPUS-12 fixture set (all 4 arguments)") and the frontend hard-gate (DEVTOOL-02, delivered in Plan 43-03) — this plan delivers only the backend, 1-fixture vertical slice. Flipping the checkbox now would misstate phase progress; left for a later plan/state-sync step in this phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/Test-technique fix] FastAPI route-tree walking broke under the installed FastAPI version**
- **Found during:** Task 2's own acceptance-criteria verification, then confirmed blocking for Task 3
- **Issue:** The plan's own verify command (`from api.main import app; assert any(r.path == ... for r in app.routes)`) and RESEARCH.md's module-re-import code example both assume `app.routes` yields flat objects with a `.path` attribute. The installed `fastapi` is `0.139.2` (requirements.txt pins `>=0.115`, so this is in-range but a large minor-version drift) — this version wraps every `include_router()` call in a private `fastapi.routing._IncludedRouter` object that has **no** `.path` attribute; the actual routes live on `.original_router.routes`. The literal command crashes with `AttributeError: '_IncludedRouter' object has no attribute 'path'` instead of returning a boolean.
- **Fix:** Wrote a small `_all_route_paths(app)` helper (in `tests/test_admin_dev_router_gate.py`) that walks both the legacy flat-route shape and the `_IncludedRouter.original_router.routes` shape, so route-presence/absence assertions work regardless of installed FastAPI minor version. Verified manually via direct introspection before committing.
- **Files modified:** `tests/test_admin_dev_router_gate.py` (new file — the helper lives here since Task 3 is the file that needs it)
- **Verification:** `./.venv/Scripts/python.exe -m pytest tests/test_admin_dev_router_gate.py -x -q` — 5 passed
- **Committed in:** `e26b81b3` (Task 3 commit)

**2. [Rule 1 - Bug] Test-file prefix assumptions corrected to match actual router mount points**
- **Found during:** Task 3, writing the regression guard that pre-existing routers stay mounted
- **Issue:** The plan's acceptance criteria describe the pre-existing routers as living under `/api/arguments`, `/api/cases`, `/api/people` — but `api/routers/{arguments,cases,people}.py` actually mount at bare `/arguments`, `/cases`, `/people` (no `/api` prefix; only `admin`/`admin_dev` use `/api/admin*`). Asserting the plan's literal (incorrect) prefixes would have produced a false-negative regression alarm even though the routers are genuinely still mounted.
- **Fix:** Wrote the regression-guard assertions against the actual mount prefixes, with a comment documenting the discrepancy so a future reader isn't confused.
- **Files modified:** `tests/test_admin_dev_router_gate.py`
- **Verification:** Same test run as above — the regression guard correctly passes against real route data.
- **Committed in:** `e26b81b3` (Task 3 commit)

**3. [Rule 1 - Bug/Test design] `db_session` fixture unusable for this destructive test; added a local `db` fixture**
- **Found during:** Task 2, first test run
- **Issue:** `api/tests/conftest.py`'s `db_session` fixture wraps the whole test in one `session.begin()` block, rolled back at the end. This test needs its seeded rows and post-reset assertions to see genuinely COMMITTED state — the reset endpoint's TRUNCATE and reseed run on a completely separate connection/session. Calling `db_session.commit()` inside the fixture's own `begin()` block raised `sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager` on the very next query.
- **Fix:** Added a local `db` fixture in `api/tests/test_admin_dev_routes.py` with its own dedicated engine/session (no wrapping transaction, no auto-rollback) — matching `pipeline/tests/test_import_convokit_adminjob.py`'s `isolated_session` fixture precedent for the same reason.
- **Files modified:** `api/tests/test_admin_dev_routes.py`
- **Verification:** Both tests pass; full suite green afterward with no fixture-name collisions.
- **Committed in:** `bd107923` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed, all Rule 1 (test-technique/assumption bugs discovered while writing verification, not implementation defects). No scope creep — all three were necessary to make the plan's own verification actually work as intended.

**Environment note (not a deviation, logged separately):** A pre-existing, unrelated Node-subprocess path-join failure in `api/tests/test_phase38_people_ui_contract.py` (4 errors) was found during Task 1's full-suite run. Confirmed pre-existing via `git stash` (reproduces identically without any of this plan's changes). Logged to `.planning/phases/43-dev-only-reset-to-fixture/deferred-items.md`, not fixed (out of scope per SCOPE BOUNDARY).

## Issues Encountered
- **WSL/Windows env-var propagation:** Shell-exported environment variables in the WSL bash session do not propagate into the Windows `.venv/Scripts/python.exe` process (a WSL interop limitation, not a project defect). This meant `pytest api/tests/test_admin_dev_routes.py` run in isolation always skips its two DB-dependent tests (no conftest.py in that narrow collection path calls `load_dotenv()`). Resolved by verifying via a wider invocation (e.g. `pytest tests/test_admin_router.py::test_api_main_imports_without_error api/tests/test_admin_dev_routes.py`) that triggers `tests/conftest.py`'s `load_dotenv()` + `DATABASE_URL` redirect for the same process — this matches how every other `api/tests/test_admin_*_routes.py` file already behaves when run standalone vs. as part of the full suite. Not a new problem introduced by this plan.

## User Setup Required

None — the required `ENVIRONMENT=development` env var (project-root `.env`) was already present (confirmed via `dotenv_values('.env')` before Task 1 began, satisfying this task's `<precondition>`). `app/.env`'s independent `ENVIRONMENT` value (needed by Plan 43-03, not this plan) was confirmed absent — flagged for the Plan 43-03 executor, not actioned here per this plan's Task 1 scope note ("Do not touch ... app/.env ... in this task").

## Next Phase Readiness
- The backend vertical slice is proven end-to-end on the riskiest integration (calling `run_import_convokit` in-process from a FastAPI request) — Plan 43-02 can now safely expand `FIXTURE_SET` to all 4 fixtures and add the DRAFT/PUBLISHED/Mid-pipeline state realization calls without re-deriving this plumbing.
- `ResetToFixtureResponse`'s full 6-field shape is locked, so Plan 43-03 (frontend) can code against it in parallel with Plan 43-02.
- **Blocker/concern for Plan 43-03:** `app/.env` does not yet have `ENVIRONMENT=development` set (confirmed via `dotenv_values('app/.env')`) — Plan 43-03's frontend gate needs this added before its own verification can pass (RESEARCH.md Pitfall 4).
- **Environment-drift note for future plans/phases:** the installed `fastapi` (`0.139.2`) has moved well past this project's `>=0.115` floor pin and changed its `app.routes` internal shape (see Deviation 1 above). Any future code that walks `app.routes` directly should use (or extend) the `_all_route_paths()` helper in `tests/test_admin_dev_router_gate.py` rather than assuming a flat `.path`-bearing list.

## Self-Check: PASSED

All created files confirmed present on disk (`api/schemas/admin_dev.py`, `api/services/admin_dev.py`, `api/routers/admin_dev.py`, `api/tests/test_admin_dev_routes.py`, `tests/test_admin_dev_router_gate.py`, `deferred-items.md`, this SUMMARY). All three task commit hashes (`dde83642`, `bd107923`, `e26b81b3`) confirmed present in `git log --oneline --all`.

---
*Phase: 43-dev-only-reset-to-fixture*
*Completed: 2026-07-31*
