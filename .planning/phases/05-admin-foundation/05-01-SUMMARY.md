---
phase: 05-admin-foundation
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, postgresql, pydantic-settings, admin, schema]

# Dependency graph
requires:
  - phase: 04-accessibility-hardening
    provides: stable v1.0 schema (migrations 0001, 0002) as the base
provides:
  - Alembic migration 0003 creating admin_jobs table with PG enum types
  - AdminJob ORM class with AdminJobStatus and AdminJobStep Python enums
  - admin_token required Settings field (ADMIN_TOKEN env var, fail-fast)
affects: [05-02-admin-router, 06-auth, 07-pipeline-runner, 08-people-editor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SAEnum with values_callable on AdminJob columns (matching existing PipelineRun pattern)
    - PG enum type creation via sa.Enum(...).create(checkfirst=True) before op.create_table
    - JSONB column via sqlalchemy.dialects.postgresql.JSONB (true JSONB, not generic JSON)
    - Required Settings field with no default (fail-fast startup posture)

key-files:
  created:
    - alembic/versions/0003_add_admin_jobs.py
    - tests/test_admin_schema.py
  modified:
    - api/models/models.py
    - api/core/config.py
    - tests/test_models_import.py

key-decisions:
  - "Migration 0003 lands the full admin_jobs schema (all 10 columns Phase 7 needs) — no migration 0004 required for this table"
  - "discrepancies is a nullable JSONB column (not a separate table) for batch fire-and-poll reads"
  - "argument_id is a nullable FK — NULL until ingest creates the argument row"
  - "admin_token has no default value — app refuses to start without ADMIN_TOKEN set"

patterns-established:
  - "Admin enum types (admin_job_status, admin_job_step) created before the table in upgrade(), dropped after the table in downgrade()"
  - "JSONB imported from sqlalchemy.dialects.postgresql for true JSONB (not generic JSON)"
  - "Required env var fields in Settings have no default value — same posture as database_url"

requirements-completed: [INFRA-A1]

# Metrics
duration: 10min
completed: 2026-06-15
---

# Phase 05, Plan 01: Admin Schema Summary

**Alembic migration 0003 with admin_jobs table, AdminJob SQLAlchemy ORM model, and ADMIN_TOKEN required Settings field — all 10 columns matching column-for-column**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-15T20:40:00Z
- **Completed:** 2026-06-15T20:50:27Z
- **Tasks:** 2 (TDD: test → feat for each)
- **Files modified:** 5

## Accomplishments
- Migration 0003 creates PG enum types `admin_job_status` and `admin_job_step` before the table (checkfirst=True), then `admin_jobs` with all 10 columns and a nullable FK to `arguments.id`
- AdminJob ORM model matches migration column-for-column: JSONB discrepancies, nullable `argument_id` FK, `func.now()` timestamps, SAEnum with values_callable
- `admin_token: str` added to Settings with no default — app refuses to start without ADMIN_TOKEN set (T-05-02 fail-fast posture)
- 13 static smoke tests in `tests/test_admin_schema.py` verify migration structure and ORM model without a DB connection

## Task Commits

Each task was committed atomically with TDD RED/GREEN discipline:

1. **Task 1 RED: Failing tests for migration** - `92415ef` (test)
2. **Task 1 GREEN: Alembic migration 0003** - `8188e75` (feat)
3. **Task 2 GREEN: AdminJob ORM + ADMIN_TOKEN config** - `0b575d4` (feat)

_Note: Task 2 tests were written as part of Task 1's test file (RED phase includes Task 2 assertions as they share the test file per plan spec). Task 2 had no separate RED commit._

## Files Created/Modified
- `alembic/versions/0003_add_admin_jobs.py` - Migration creating admin_job_status/admin_job_step PG enums and admin_jobs table with 10 columns
- `tests/test_admin_schema.py` - 13 static-analysis smoke tests (no DB required per D-15)
- `api/models/models.py` - Added AdminJobStatus, AdminJobStep enums and AdminJob ORM class; added JSONB import
- `api/core/config.py` - Added required `admin_token: str` field to Settings
- `tests/test_models_import.py` - Updated table count from 11 to 12 (admin_jobs added)

## Decisions Made
- Used `sa.Enum(...).create(op.get_bind(), checkfirst=True)` for enum creation per plan spec (PATTERNS.md pattern), consistent with plan action instructions
- Used `postgresql.JSONB()` (explicit) rather than `sa.JSON()` for the discrepancies column — true JSONB type as specified in plan action
- `func.now()` in ORM layer (project convention), `sa.text("now()")` in migration (Alembic convention) — matches existing PipelineRun pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_models_import.py table count from 11 to 12**
- **Found during:** Task 2 (running full test suite after adding AdminJob)
- **Issue:** `test_models_import.py` hard-coded `assert len(tables) == 11` and an exact set of 11 table names. Adding `admin_jobs` legitimately makes 12 tables, causing a false test failure.
- **Fix:** Updated count to 12 and added `"admin_jobs"` to the expected set in both `test_all_tables_count` and `test_expected_table_names`.
- **Files modified:** `tests/test_models_import.py`
- **Verification:** Full test suite passes (30/30) with `ADMIN_TOKEN=test`
- **Committed in:** `0b575d4` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in pre-existing test)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered
- pytest not installed in the venv (venv had no pytest.exe). Installed `pytest` and `pytest-asyncio` via `.venv/Scripts/pip install` as a Rule 3 blocking fix before the first test run.

## Threat Model Compliance
- `admin_token` has no default value — satisfies T-05-02 (fail-fast, prevents shipping unauthenticated admin router)
- `admin_token` is a plain str field not added to any `__repr__` or endpoint response — satisfies T-05-01 (no information disclosure)
- `argument_id` nullable FK accepted per T-05-03 — NULL is valid semantics (job exists before ingest creates the argument row)

## Next Phase Readiness
- Plan 02 (admin router) can import `AdminJob` from `api/models/models.py` and read `settings.admin_token`
- Phase 6 (auth) can add `SESSION_SECRET` alongside `admin_token` in `api/core/config.py`
- Phase 7 (pipeline runner) has the full `admin_jobs` schema it needs — no migration 0004 required for this table

---
*Phase: 05-admin-foundation*
*Completed: 2026-06-15*
