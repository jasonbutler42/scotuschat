---
phase: 07-pipeline-runner
plan: "02"
subsystem: api
tags: [fastapi, admin, pipeline-runner, job-routes, ssrf-mitigation, atomic-guards]
one_liner: "Five admin job routes wired to Plan 01 services: create-job (URL+upload), poll with step-advance, list, resolve-continue, and inline person creation"

dependency_graph:
  requires:
    - "07-01: admin_jobs service, pipeline_spawn, spaces, schemas"
    - "05-01: admin router with verify_admin_token dependency"
  provides:
    - "POST /api/admin/jobs — create job + spawn ingest (PIPE-12, PIPE-13)"
    - "GET /api/admin/jobs/{id} — poll + step-advance side effect (PIPE-14, PIPE-17)"
    - "GET /api/admin/jobs — history list"
    - "POST /api/admin/jobs/{id}/resolve — write confirmed aliases (PIPE-16)"
    - "POST /api/admin/jobs/{id}/people — inline person creation (D-13)"
  affects:
    - "api/routers/admin.py — extended with 5 new routes"

tech_stack:
  added: []
  patterns:
    - "SSRF mitigation: _validate_pdf_url enforces https + supremecourt.gov at route boundary (T-07-01)"
    - "File type guard: content_type == application/pdf rejected with 422 (T-07-04)"
    - "Atomic advance guards: try_advance_ingest_to_parse / try_advance_parse_to_resolve (rowcount check)"
    - "PIPE-17 resumable lookup: get_run_id_for_step re-derives run-id on every poll"
    - "Fire-and-forget spawn via spawn_pipeline_step after DB guard wins race"
    - "ValueError from resolve_job mapped to HTTPException 422 (Pitfall 5)"

key_files:
  modified:
    - path: "api/routers/admin.py"
      role: "HTTP surface for all admin job operations"
      symbols_added:
        - "_validate_pdf_url (SSRF guard)"
        - "create_job route (POST /jobs)"
        - "list_jobs route (GET /jobs)"
        - "get_job route (GET /jobs/{id}) with step-advance side effect"
        - "resolve_job route (POST /jobs/{id}/resolve)"
        - "create_person_for_job route (POST /jobs/{id}/people)"

decisions:
  - "Both tasks (Task 1: create+list, Task 2: poll+resolve+people) implemented in a single commit to api/routers/admin.py since they modify the same file"
  - "Inline sa_update import inside upload branch to avoid top-level circular concern — acceptable since it is a local update within the route handler"
  - "Re-read job after step-advance so response body reflects new current_step/status (not stale pre-advance state)"
  - "get_run_id_for_step called with 'ingest' before spawning parse, 'parse' before spawning resolve — run-id is input-step's run, as documented in PIPE-17"

metrics:
  duration_seconds: 133
  completed_date: "2026-06-16"
  tasks_completed: 2
  files_modified: 1
---

# Phase 07 Plan 02: Admin Job Routes Summary

Five FastAPI routes added to the existing admin router in `api/routers/admin.py`, wiring the Plan 01 service layer to the HTTP surface the SvelteKit pipeline pages will call.

## What Was Built

### Task 1: Create-job route and history list

`POST /api/admin/jobs` (202) accepts either a `pdf_url` form field or a `pdf_file` upload:

- **URL mode:** `_validate_pdf_url` enforces `https://...supremecourt.gov/...` before `create_job` or any subprocess spawn (T-07-01 SSRF mitigation, defense-in-depth before pipeline's own `_validate_url`). Calls `spawn_pipeline_step("ingest", job.id, ["--url", pdf_url])`.
- **Upload mode:** Rejects `content_type != application/pdf` with 422 (T-07-04). Creates the job to obtain its id, uploads bytes to Spaces as `uploads/{job.id}.pdf`, updates `spaces_key` on the job row, then calls `spawn_pipeline_step("ingest", job.id, ["--spaces-key", key])`.
- Both modes return 202 + `AdminJobResponse`.

`GET /api/admin/jobs` delegates to `jobs_service.list_jobs(db, limit=10)`.

### Task 2: Poll endpoint, resolve-continue, and inline person creation

`GET /api/admin/jobs/{job_id}` (poll endpoint, D-05/D-06):

1. Loads the job; returns 404 if absent.
2. **Step-advance side effect:** If `current_step=INGEST` and `status=COMPLETED`, calls `try_advance_ingest_to_parse(db, job_id)`. If the atomic guard wins (rowcount == 1), derives `run_id = get_run_id_for_step(db, job_id, "ingest")` and spawns parse. Analogously for PARSE→RESOLVE transition. Re-reads the job after a successful advance so the response reflects the new state.
3. PAUSED, FAILED, and COMPLETED jobs are not touched — no advance branch keys off those statuses.
4. The `get_run_id_for_step` call on every poll re-derives the run-id from `pipeline_runs` (PIPE-17) — no cached state, so a re-entrant poll after browser close/reopen works.

`POST /api/admin/jobs/{job_id}/resolve`: calls `jobs_service.resolve_job`. Catches `ValueError` (bad person_id, Pitfall 5 validate-first) and re-raises as `HTTPException(422)`, leaving the job paused for retry.

`POST /api/admin/jobs/{job_id}/people` (201): calls `jobs_service.create_person_for_job`; returns `PersonResponse`.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-07-01 | mitigated | `_validate_pdf_url` enforces https + supremecourt.gov before create_job and spawn |
| T-07-04 | mitigated | `content_type != application/pdf` rejected with 422 in upload branch |
| T-07-05 | mitigated | all routes inherit router-level `verify_admin_token` — no per-route auth needed |
| T-07-06 | mitigated | spawn only when atomic `try_advance_*` guard returns True (rowcount == 1) |

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries beyond those in the plan's threat model.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1 + Task 2 (same file) | 753aea9 | api/routers/admin.py |

## Self-Check: PASSED

- `api/routers/admin.py` exists and was modified: confirmed
- Commit 753aea9 exists: confirmed
- All 5 routes registered on admin router: `/api/admin/health`, `/api/admin/jobs`, `/api/admin/jobs/{job_id}`, `/api/admin/jobs/{job_id}/people`, `/api/admin/jobs/{job_id}/resolve` — verified via `python -c "from api.routers import admin..."` import check
- PIPE-17 resumable lookup present: `get_run_id_for_step(db, job_id, "ingest")` and `get_run_id_for_step(db, job_id, "parse")` both in source — verified
