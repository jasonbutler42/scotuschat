---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 02
subsystem: testing
tags: [pytest, asyncpg, postgres, test-isolation, leak-detection]

# Dependency graph
requires:
  - "scripts/provision_test_db.py — scotus_test provisioning (31-01)"
  - "pipeline/tests/conftest.py::_reset_test_db — TEST_DATABASE_URL-gated auto-reset (31-01)"
provides:
  - "tests/conftest.py::_REAL_DATABASE_URL — captured pre-override shared dev-DB URL"
  - "tests/conftest.py DATABASE_URL -> TEST_DATABASE_URL redirect for the whole suite (api + pipeline)"
  - "tests/conftest.py::pytest_sessionstart / pytest_sessionfinish — automated people/arguments row-count leak guard on the real dev DB"
affects: [31-03, 31-04, 31-05, 31-06, 31-07, 31-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capture-before-override: read a real env var into a module constant before mutating it, so later guards can always inspect the pre-override value"
    - "Silent no-op (not pytest.skip) inside pytest_sessionstart/pytest_sessionfinish — these hooks have no test context to skip against"

key-files:
  created: []
  modified:
    - tests/conftest.py

key-decisions:
  - "_REAL_DATABASE_URL is captured as the very first statement after load_dotenv(), before the TEST_DATABASE_URL override — this is what the leak-detection hooks check, never the (possibly redirected) os.environ['DATABASE_URL'], so the guard keeps watching the real dev DB even when isolation is active (T-31-05)."
  - "The leak-detection hooks check only people and arguments (D-12), matching the success criterion and the tables confirmed leaked in the actual incident — not the full clean_db table list."
  - "Both hooks reuse the exact _db_configured placeholder guard shape from api/tests/conftest.py ('sk-ant' not in url and url != the literal placeholder DSN), replicated locally since a bare bool(url) check would let .env.example placeholder values leak into CI."

requirements-completed: [TEST-01]

coverage:
  - id: D1
    description: "tests/conftest.py redirects DATABASE_URL to TEST_DATABASE_URL for the whole suite when configured, without touching any production module"
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "ast.parse(tests/conftest.py) — parse-ok"
        status: pass
      - kind: integration
        ref: "pytest tests/ --collect-only -q — 42 tests collected, no errors"
        status: pass
      - kind: integration
        ref: "pytest tests/ -q with TEST_DATABASE_URL unset (this environment) — 42 passed, DATABASE_URL left pointed at the real dev DB"
        status: pass
    human_judgment: true
    rationale: "The redirect branch (TEST_DATABASE_URL set) cannot be exercised live in this execution environment because TEST_DATABASE_URL is not yet configured in .env (operator user_setup step from 31-01 not yet performed). Static verification (parse + guard-branch review) passed; the no-op branch (TEST_DATABASE_URL unset, DATABASE_URL untouched) was exercised live and passed."
  - id: D2
    description: "pytest_sessionstart/pytest_sessionfinish snapshot and re-assert people/arguments counts on the real dev DB, raising an unambiguous message on mismatch, and no-op silently when unconfigured"
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "ast.parse + string checks confirming both hooks defined, both query FROM people and FROM arguments — ok"
        status: pass
      - kind: integration
        ref: "pytest tests/ -q with the real DATABASE_URL configured (this environment) — 42 passed; sessionstart/sessionfinish both executed the live query path (DATABASE_URL was confirmed configured and non-placeholder) with zero row-count drift"
        status: pass
      - kind: integration
        ref: "pytest api/tests -q — 133 passed, 105 skipped; no regressions from the new root conftest hooks"
        status: pass
    human_judgment: false
    rationale: "Both the no-op guard and the live query-and-compare path were exercised directly in this execution environment (DATABASE_URL was already configured to a real, non-placeholder DSN), giving full behavioral coverage without needing an injected-leak test, which is out of scope for this plan."

# Metrics
duration: 20min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 02: Wire Whole Suite to Test DB + Add Row-Count Leak Guard Summary

**Root `tests/conftest.py` now redirects `DATABASE_URL` onto `TEST_DATABASE_URL` for the whole suite when configured, and enforces an automated `pytest_sessionstart`/`pytest_sessionfinish` guard that fails loudly if any session changes `people`/`arguments` row counts on the real shared dev DB.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-13T14:14:28Z (approx., per STATE.md)
- **Completed:** 2026-07-13 (same day)
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `tests/conftest.py` captures `_REAL_DATABASE_URL` from `os.environ.get("DATABASE_URL")` immediately after `load_dotenv()`, before any override — this is the value every downstream guard in this file inspects.
- When `TEST_DATABASE_URL` is set, `os.environ["DATABASE_URL"]` is reassigned to it at conftest module load, before `api.core.config.settings` or `api.core.database` are imported anywhere in the suite — redirecting the whole test run (api + pipeline) onto `scotus_test` with zero changes to production modules. When unset, `DATABASE_URL` is left exactly as-is.
- `pytest_sessionstart` opens a one-shot `asyncpg`-backed connection (via `create_async_engine` + `statement_cache_size=0`) to `_REAL_DATABASE_URL`, counts `people` and `arguments`, and stashes the counts on `session.config._scotus_pre_counts`.
- `pytest_sessionfinish` re-queries the same two counts and raises an `AssertionError` naming the table and before/after counts on any mismatch. Both hooks return immediately (no assertion, no error) when `_REAL_DATABASE_URL` is unset or matches the `sk-ant` / placeholder-DSN guard already used elsewhere in the suite.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DATABASE_URL preservation + TEST_DATABASE_URL override wiring in tests/conftest.py (D-01)** - `b0df5a24` (feat)
2. **Task 2: Add pytest_sessionstart/pytest_sessionfinish leak-detection hook (D-11, D-12, D-13)** - `bc66eb22` (feat)

**Plan metadata:** _(pending — final docs commit follows this SUMMARY)_

## Files Created/Modified

- `tests/conftest.py` - Added `_REAL_DATABASE_URL` capture + `TEST_DATABASE_URL` override wiring (Task 1), and `_db_configured`, `pytest_sessionstart`, `pytest_sessionfinish` (Task 2). No `api.*` imports at module level; all SQLAlchemy imports are local to the hook functions.

## Decisions Made

- `_REAL_DATABASE_URL` is a module constant captured before the override so it never reflects a redirected `TEST_DATABASE_URL` value — this is the specific mechanism that satisfies T-31-05 (the leak guard must always watch the real dev DB, never the possibly-overridden `DATABASE_URL`).
- The leak-detection hooks use `asyncio.run(...)` around a small async helper rather than a sync driver, since the project's only Postgres driver dependency is `asyncpg`/SQLAlchemy async — avoids adding a new sync driver dependency for a one-shot query.
- The hooks check only `people` and `arguments` (D-12) — not the full `clean_db` table list from `pipeline/tests/conftest.py` — per the plan's explicit scope-narrowing instruction, keeping the failure message unambiguous and matching the confirmed incident tables.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria were verified: `_REAL_DATABASE_URL` capture precedes the override, no `api.*` module-level imports were introduced, both hooks are defined and query only `people`/`arguments`, and both hooks no-op silently under the same placeholder guard used elsewhere in the suite.

## Issues Encountered

None. Live verification in this execution environment was more complete than plan 31-01's, because `DATABASE_URL` (the real dev DB) is already configured here — the guard's live query-and-compare path (not just its no-op path) executed successfully across three separate pytest invocations (`tests/`, `api/tests`) with zero row-count drift observed.

## User Setup Required

No new setup beyond what 31-01 already documented (`TEST_DATABASE_URL` in `.env`, `python scripts/provision_test_db.py`). Once that is done, the `TEST_DATABASE_URL` redirect branch added in this plan's Task 1 will take effect automatically on the next `pytest` invocation — no additional operator action needed for this plan specifically.

## Next Phase Readiness

- The whole suite is now wired to redirect onto `scotus_test` whenever `TEST_DATABASE_URL` is configured, and every future full-suite run is self-checked against accidental writes to the shared dev DB via the new session hooks — this is the automated enforcement mechanism success criterion 1 required.
- Later plans in this phase (fixing the ~28 stale DB-gated fixtures, consolidating the duplicated `db_session` fixture, cleaning up already-leaked rows) can now proceed with this guard active as a safety net: any fixture fix that accidentally still writes to the dev DB will fail the session loudly instead of leaking silently.

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: tests/conftest.py
- FOUND commit: b0df5a24
- FOUND commit: bc66eb22
