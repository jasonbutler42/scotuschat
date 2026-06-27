---
phase: 17-pipeline-ui-polish
plan: "01"
subsystem: api
status: complete
tags: [backend, schema, migration, admin-jobs, pdf-serving]
dependency_graph:
  requires: [phase-15 (PipelineRun.pdf_path), phase-16 (argument.argued_date), alembic-0008]
  provides: [AdminJobResponse.original_filename, AdminJobResponse.parse_stats, GET /api/admin/jobs/{job_id}/pdf]
  affects: [admin.py, admin_jobs.py, spaces.py, schemas/admin_jobs.py, models.py]
tech_stack:
  added: []
  patterns: [alembic-nullable-column, pydantic-from_attributes, run_in_executor-boto3, scalar_one-count, starlette-FileResponse-RedirectResponse]
key_files:
  created:
    - alembic/versions/0009_add_original_filename.py
    - api/tests/test_admin_jobs_stats.py
  modified:
    - api/models/models.py
    - api/schemas/admin_jobs.py
    - api/services/admin_jobs.py
    - api/services/spaces.py
    - api/routers/admin.py
decisions:
  - "ParseStats assembled from scalar COUNT results — no from_attributes config; AdminJobResponse retains from_attributes"
  - "parse_stats injected via job.__dict__ before model_validate reads ORM object"
  - "PDF endpoint branches spaces_key FIRST per Pitfall 2; disk fallback reads PipelineRun.pdf_path from ingest run"
  - "generate_pdf_presigned_url is synchronous boto3, wrapped in run_in_executor at call site"
  - "original_filename=pdf_file.filename passed through without assertion (Pitfall 3 — may be None for malformed uploads)"
metrics:
  duration_minutes: 25
  completed: "2026-06-27"
  tasks_completed: 3
  files_modified: 7
---

# Phase 17 Plan 01: Backend Support for Pipeline UI Polish Summary

Backend support for Phase 17 pipeline UI polish: store the original upload filename, compute parse stats at render time, and serve the source PDF through one unified admin endpoint.

## What Was Built

### Task 1: Migration 0009 + AdminJob ORM column + create_job capture

- Created `alembic/versions/0009_add_original_filename.py` — revision 0009, down_revision 0008; adds nullable TEXT column `original_filename` to `admin_jobs`; downgrade drops it. No backfill (existing rows get NULL).
- Added `AdminJob.original_filename = Column(Text, nullable=True)` to the ORM model.
- Extended `create_job()` with `original_filename: str | None = None` keyword param forwarded to the `AdminJob(...)` constructor.
- Updated the upload-mode `create_job` call in `admin.py` to pass `original_filename=pdf_file.filename`. URL-mode call left unchanged per D-03.

### Task 2: ParseStats schema + parse-stats query in get_job (TDD)

**RED:** Wrote `api/tests/test_admin_jobs_stats.py` — 8 tests covering:
- `ParseStats` model fields and absence of `from_attributes`
- `AdminJobResponse` has `original_filename` and `parse_stats` optional fields
- `AdminJobResponse` retains `from_attributes` config
- DB tests (skipped without DATABASE_URL): counts from latest parse run, None when no parse run, None when `argument_id` is None, latest-run-when-two-exist (D-09)

**GREEN:** Implemented:
- `ParseStats(BaseModel)` with `utterance_count: int` and `speaker_count: int` — no `from_attributes`; placed before `AdminJobResponse` in `admin_jobs.py`
- Added `original_filename: Optional[str] = None` and `parse_stats: Optional[ParseStats] = None` to `AdminJobResponse` (after `spaces_key`)
- Extended `get_job()`: reuses `get_run_id_for_step(db, job_id, "parse")` for recency; runs two COUNT queries with `scalar_one()`; injects result into `job.__dict__["parse_stats"]`; sets `None` when parse_run_id or argument_id is None

### Task 3: generate_pdf_presigned_url helper + GET /jobs/{job_id}/pdf endpoint

- Added `generate_pdf_presigned_url(key: str, expires_in: int = 900) -> str` to `spaces.py` — synchronous boto3, mirrors `upload_pdf_to_spaces` pattern.
- Added `GET /jobs/{job_id}/pdf` route to `admin.py`:
  - Return annotation `-> Response` with no `response_model` (Pitfall 6)
  - Branches on `job.spaces_key` FIRST (Pitfall 2 short-circuit)
  - Spaces branch: `run_in_executor` wraps presigned URL call → `RedirectResponse(302)`
  - Disk branch: `get_run_id_for_step(db, job_id, "ingest")` → PipelineRun row → `FileResponse(inline)`
  - 404 for: unknown job, missing ingest run, missing pdf_path
  - Auth inherited from router-level `verify_admin_token` (T-17-01 mitigated)
  - `original_filename` used as `Content-Disposition` filename; falls back to `argument-{job_id}.pdf`

## Decisions Made

- `ParseStats` has no `from_attributes` because it is assembled from plain dict scalars, not an ORM row. `AdminJobResponse` retains `from_attributes` for the main ORM-to-Pydantic conversion path.
- `parse_stats` is injected via `job.__dict__["parse_stats"]` so that `model_validate(job, from_attributes=True)` reads it as if it were an attribute — avoids constructing `AdminJobResponse` manually in every route.
- `generate_pdf_presigned_url` is synchronous (boto3 blocking IO) following the existing `upload_pdf_to_spaces` pattern; the route wraps it in `run_in_executor` consistent with the upload pattern already in the router.
- `original_filename=pdf_file.filename` passed through without assertion — `pdf_file.filename` may be `None` for malformed uploads (Pitfall 3); stored as-is; display-only field (T-17-04 accepted).

## Threat Surface Scan

All security-relevant surfaces were in the plan's `<threat_model>`:
- T-17-01: IDOR on `/jobs/{job_id}/pdf` — mitigated by router-level `verify_admin_token`
- T-17-02: Path traversal via FileResponse — mitigated by reading `pdf_path` from DB (not request params)
- T-17-03: Pre-signed URL in address bar — accepted (admin-only, 15-min TTL)
- T-17-04: `original_filename` spoofing — accepted (display-only, not used as file path)
- T-17-05: Parse stats disclosure — accepted (raw integers, no interpretation)

No new threat surface beyond what was modeled.

## Deviations from Plan

None — plan executed exactly as written. The alembic migrations directory was found at the project root (not inside `api/`) which matches the repo structure; the plan references were adjusted accordingly.

## Test Results

```
api/tests/test_admin_jobs_stats.py: 4 passed, 4 skipped
(DB tests skipped — DATABASE_URL not configured in CI; require live PostgreSQL)
```

## Self-Check

- [x] `alembic/versions/0009_add_original_filename.py` exists
- [x] `revision == "0009"`, `down_revision == "0008"`
- [x] `AdminJob.original_filename = Column(Text, nullable=True)` in models.py
- [x] `create_job` has `original_filename: str | None = None` param
- [x] Upload-mode call passes `original_filename=pdf_file.filename`
- [x] `ParseStats` exists with `utterance_count: int`, `speaker_count: int`, no `from_attributes`
- [x] `AdminJobResponse` has `original_filename` and `parse_stats` optional fields
- [x] `get_job` uses `get_run_id_for_step(db, job_id, "parse")` + two `scalar_one()` COUNT queries
- [x] `generate_pdf_presigned_url(key, expires_in=900)` in spaces.py
- [x] `GET /jobs/{job_id}/pdf` route registered; `-> Response` annotation, no `response_model`
- [x] No `Base.metadata.create_all` introduced
- [x] All task commits present: 58182602, 39192ee9, be61bb34, 91fbcb3c
