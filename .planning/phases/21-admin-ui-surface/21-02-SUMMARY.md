---
phase: 21-admin-ui-surface
plan: 02
subsystem: api, ui
tags: [fastapi, svelte5, sqlalchemy, delete, admin-job, pipeline-run]

# Dependency graph
requires:
  - phase: 21-01 (argument delete)
    provides: api/routers/admin.py target file (Wave 2 sequencing)
  - phase: 15 (approve/rerun)
    provides: existing /jobs/{job_id}/* route structure in admin.py
provides:
  - delete_job service function (admin_job row only)
  - DELETE /api/admin/jobs/{job_id} FastAPI endpoint
  - Two-step inline confirm delete UI on job detail page
  - Redirect to /admin/pipeline after delete
affects:
  - 21-03-PLAN (AdminSubNav — layout around same job detail page)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-row delete: delete(AdminJob).where(id==job_id).execution_options(synchronize_session=False)"
    - "Job delete does NOT cascade — argument/pipeline_runs/utterances survive (D-10/D-11)"
    - "Two-step inline confirm: deleteConfirming + deleteSubmitting $state; $effect resets on soft nav (Pitfall 7)"

key-files:
  created:
    - api/tests/test_admin_jobs_service.py
  modified:
    - api/services/admin_jobs.py
    - api/routers/admin.py
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

key-decisions:
  - "delete_job returns bool: True=deleted (rowcount==1), False=not found (rowcount==0) — simpler than delete_argument (no blocked state for jobs)"
  - "No can_delete gate on job delete — D-08 published guard applies to arguments only, not jobs"
  - "DELETE endpoint placed after all /jobs/{job_id}/* sub-routes (pdf, resolve, people, approve, rerun) to avoid shadowing"
  - "$effect references data.job.id to reset deleteConfirming/deleteSubmitting on SvelteKit soft nav (Pitfall 7)"
  - "delete action uses global fetch (no event.fetch) — consistent with all other actions in this file"

requirements-completed: [ADMIN-02]

coverage:
  - id: D1
    description: "delete_job service function: single admin_job row delete, argument/run/utterances survive"
    requirement: ADMIN-02
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py::test_delete_job_importable"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py::test_delete_job_only_deletes_admin_jobs"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py::test_delete_job_has_synchronize_session_false"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py::test_delete_job_returns_false_for_missing_id"
        status: skipped (no DATABASE_URL)
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py::test_delete_job_removes_only_admin_job_row"
        status: skipped (no DATABASE_URL)
    human_judgment: false
  - id: D2
    description: "DELETE /api/admin/jobs/{job_id} endpoint: 200 deleted, 404 not found"
    requirement: ADMIN-02
    verification:
      - kind: unit
        ref: "python -m pytest api/tests/ -x -q -k job"
        status: pass (10 passed, 13 skipped)
    human_judgment: false
  - id: D3
    description: "Job detail page: two-step Danger Zone delete, redirect to /admin/pipeline"
    requirement: ADMIN-02
    verification:
      - kind: unit
        ref: "app svelte-check --threshold error: 0 errors"
        status: pass
    human_judgment: true
    rationale: "UI interaction state (deleteConfirming toggle, redirect, no blocked state) requires visual verification in a running browser"

duration: ~20min
completed: 2026-07-01
status: complete
---

# Phase 21 Plan 02: Pipeline Run Delete (ADMIN-02) Summary

**Single-row admin_job delete with two-step inline confirm; argument and downstream data survive (D-10/D-11)**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-01
- **Completed:** 2026-07-01
- **Tasks:** 3 (TDD: RED commit + GREEN commit for Task 1)
- **Files modified:** 4 (+ 1 created)

## Accomplishments

- `delete_job(db, job_id) -> bool` added to admin_jobs.py: single DELETE against admin_jobs only; `rowcount==1` → True, `rowcount==0` → False (no cascade into argument or its data)
- `DELETE /api/admin/jobs/{job_id}` endpoint added to admin.py after all /jobs/{job_id}/* sub-routes; returns 200 `{"deleted": True}` or 404
- Job detail page `+page.server.ts` gains `delete` form action: DELETE call with X-Admin-Token, `redirect(303, '/admin/pipeline')` on success, `fail(502)` on error (D-12)
- Job detail page `+page.svelte` gains Danger Zone card with `deleteConfirming`/`deleteSubmitting` `$state`, `$effect` for Pitfall 7 reset, two-step confirm (no blocked state — D-08 applies to arguments only)
- New test file `api/tests/test_admin_jobs_service.py` with 3 structural + 2 DB-guarded behavioral tests

## Task Commits

1. **Task 1 RED: Failing tests for delete_job** — `33e1f06b` (test)
2. **Task 1 GREEN: delete_job service implementation** — `db9b8059` (feat)
3. **Task 2: DELETE /jobs/{job_id} endpoint** — `4fd45dac` (feat)
4. **Task 3: Danger Zone UI + delete action** — `2931ef14` (feat)

## Files Created/Modified

- `api/tests/test_admin_jobs_service.py` — Created: 3 structural tests + 2 DB-guarded behavioral tests for delete_job
- `api/services/admin_jobs.py` — Added `delete` import + `delete_job` function
- `api/routers/admin.py` — Added `DELETE /jobs/{job_id}` handler
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — Added `delete` form action
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Added `deleteConfirming`/`deleteSubmitting` `$state`, `$effect` reset, Danger Zone card

## Decisions Made

- `delete_job` returns `bool` (not `bool | None`) — jobs have no blocked state (no published guard); False = not found is sufficient (simpler than delete_argument's three-way return)
- No `can_delete` gate: `D-08` published guard applies to arguments; jobs are always deletable
- DELETE endpoint placed after all `/jobs/{job_id}/*` sub-routes to avoid shadowing
- `$effect` references `data.job.id` to reset confirm state on SvelteKit soft navigation (Pitfall 7)
- `delete` action uses bare global `fetch` (no `event.fetch`) — consistent with existing actions in this file

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `test(21-02)` commit `33e1f06b` — failing import test confirmed before implementation
- GREEN gate: `feat(21-02)` commit `db9b8059` — all 3 structural tests pass after implementation

## Threat Surface Scan

No new threat surface beyond the plan's threat model. All four STRIDE threats mitigated:
- T-21-02-SCOPE: delete_job contains exactly one DELETE against AdminJob; structural test + source assertion proves no other table is touched
- T-21-02-IDOR: path param typed `int`; delete_job returns False for missing id → 404
- T-21-02-CSRF: SvelteKit CSRF active; form action POST only
- T-21-02-AUTH: router-level `verify_admin_token` inherited

## Known Stubs

None — delete is fully wired end-to-end.

## Next Phase Readiness

- Plan 03 (AdminSubNav) can proceed immediately — does not depend on this plan's outputs
