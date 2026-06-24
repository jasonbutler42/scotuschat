---
phase: 13-ingestion-flow-polish
plan: "01"
subsystem: api
tags: [pipeline, jobs, filter, cleanup, tdd, pipe-20]
dependency_graph:
  requires: []
  provides: [list_jobs-incomplete-filter, GET-admin-jobs-incomplete-param]
  affects: [api/routers/admin.py, api/services/admin_jobs.py]
tech_stack:
  added: []
  patterns: [SQLAlchemy .in_() enum filter, FastAPI bool query param, TDD RED-GREEN]
key_files:
  created:
    - api/tests/test_admin_jobs_list.py
  modified:
    - api/services/admin_jobs.py
    - api/routers/admin.py
    - app/src/routes/admin/arguments/+page.server.ts
    - pipeline/__main__.py
    - pipeline/commands/ingest.py
decisions:
  - "AdminJobStatus enum members (not string literals) used in .in_() clause (T-13-01)"
  - "Incomplete defined as PAUSED + FAILED per D-10; COMPLETED/RUNNING/PENDING excluded"
  - "Route param placed before db=Depends(get_db), matching list_people route shape"
metrics:
  duration: ~7 min
  completed: "2026-06-24"
  tasks: 2
  files: 5
status: complete
requirements: [PIPE-20]
---

# Phase 13 Plan 01: Pre-Phase-13 Cleanup + list_jobs Incomplete Filter Summary

**One-liner:** Pre-phase cleanup (T-11-PUBGATE restored) + `list_jobs` gains `incomplete` kwarg filtering `status IN ('paused','failed')` via SQLAlchemy enum `.in_()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pre-Phase-13 working-tree cleanup (D-14, D-15) | 33b4b4e | page.server.ts, __main__.py, ingest.py |
| 2 RED | list_jobs incomplete filter tests (PIPE-20) | b8ac097 | api/tests/test_admin_jobs_list.py |
| 2 GREEN | list_jobs incomplete filter implementation | e47ad87 | admin_jobs.py, admin.py |

## What Was Built

### Task 1: Pre-Phase-13 Cleanup
- Reverted `api/services/admin_arguments.py` and `app/src/routes/admin/arguments/+page.svelte` to HEAD — both files had accidentally removed the Phase 11 publish gate (T-11-PUBGATE)
- Committed 3 kept files (`+page.server.ts`, `__main__.py`, `ingest.py`) under exact message `fix: pre-phase-13 cleanup — publish logging + local-file ingest flag`
- T-11-PUBGATE verified intact: `publish_argument` enforces `resolved_at IS NOT NULL` at line 237 of `admin_arguments.py`

### Task 2: PIPE-20 Backend Filter (TDD)
- `list_jobs` in `api/services/admin_jobs.py` now accepts `incomplete: bool = False`
- When `incomplete=True`: adds `.where(AdminJob.status.in_([AdminJobStatus.PAUSED, AdminJobStatus.FAILED]))` before order/limit
- When `incomplete=False` (default): returns all jobs unchanged — same behavior as before
- `AdminJobStatus` enum was already imported; filter uses enum members (not string literals) — parameterized query, no SQL injection risk (T-13-01 mitigated)
- Route handler `GET /api/admin/jobs` in `api/routers/admin.py` accepts `incomplete: bool = False` query param (placed before `db=Depends(get_db)`, matching existing `list_people` route shape at line 321)
- Route passes param through: `await jobs_service.list_jobs(db, limit=10, incomplete=incomplete)`

### Tests (`api/tests/test_admin_jobs_list.py`)
- Auth tests (no DB): wrong token → 401 for both base route and `?incomplete=true`
- DB-guarded behavioral tests (4 behaviors):
  - `list_jobs(db, incomplete=False)` returns all seeded statuses (COMPLETED/RUNNING/PAUSED/FAILED/PENDING)
  - `list_jobs(db)` defaults to same as `incomplete=False`
  - `list_jobs(db, incomplete=True)` returns only PAUSED and FAILED
  - `list_jobs(db, incomplete=True)` excludes COMPLETED, RUNNING, PENDING
- HTTP endpoint integration tests: `?incomplete=false`, `?incomplete=true`, no param

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `git diff HEAD -- api/services/admin_arguments.py app/src/routes/admin/arguments/+page.svelte` is empty (both files match HEAD)
- `git log HEAD~2 --format=%s` = `fix: pre-phase-13 cleanup — publish logging + local-file ingest flag`
- Cleanup commit contains exactly 3 files (verified with `git show --stat HEAD~2`)
- `grep -n "incomplete" api/services/admin_jobs.py` shows kwarg and `.in_` filter
- `grep -n "incomplete: bool = False" api/routers/admin.py` matches both `list_jobs` (new) and `list_people` (existing)
- `python -m pytest api/tests/test_admin_jobs_list.py -x -q`: 2 passed, 6 skipped (DB-guarded tests skip without DATABASE_URL — expected)

## Known Stubs

None — implementation is complete. DB-guarded tests will exercise the full filter when DATABASE_URL is configured.

## Threat Flags

No new threat surface beyond what was in the plan's threat model. T-13-PUBGATE (publish gate) is confirmed intact.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | b8ac097 | PASS |
| GREEN (feat) | e47ad87 | PASS |

## Self-Check: PASSED

- `api/tests/test_admin_jobs_list.py` exists: FOUND
- `api/services/admin_jobs.py` has `incomplete` kwarg: FOUND (line 78)
- `api/routers/admin.py` has `incomplete: bool = False` on list_jobs route: FOUND (line 233)
- Commits 33b4b4e, b8ac097, e47ad87: all present in git log
