---
phase: 19
plan: "03"
subsystem: api
tags:
  - fastapi
  - pydantic
  - schemas
  - services
  - router
  - admin
  - duplicate-prevention
  - metadata-prefill
dependency_graph:
  requires:
    - 19-01 (Argument.source_docket, Argument.cover_metadata, argued_date nullable)
  provides:
    - GET /api/admin/arguments/check-duplicate
    - PATCH /api/admin/arguments/{argument_id}/metadata
    - MetadataUpdate schema (mass-assignment guard)
    - ArgumentDetail.source_docket field
    - ArgumentDetail.cover_metadata field
    - check_duplicate_argument service function
    - update_argument_metadata service function
  affects:
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - api/routers/admin.py
    - Plan 04 SvelteKit UI (consumes both new endpoints)
tech_stack:
  added: []
  patterns:
    - MetadataUpdate mass-assignment guard (same pattern as ArgumentUpdate T-11-MASS)
    - .execution_options(synchronize_session=False) on all UPDATE statements (Pitfall 5)
    - Literal route registered before parameterized route (T-19-03-05 path conflict guard)
    - router-level X-Admin-Token auth inheritance (no per-route auth needed)
    - Returns False (not raises) for not-found; router translates to 404 (T-19-03-02)
key_files:
  created: []
  modified:
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - api/routers/admin.py
decisions:
  - "[19-03]: MetadataUpdate schema restricts writable fields to {case_name, source_docket, argued_date} — same mass-assignment guard pattern as ArgumentUpdate (T-19-03-01)"
  - "[19-03]: ArgumentListItem.argued_date and ArgumentDetail.argued_date changed to Optional[datetime.date] = None per D-08 / migration 0011"
  - "[19-03]: GET /arguments/check-duplicate registered BEFORE GET /arguments/{argument_id} so FastAPI resolves literal segment first (T-19-03-05)"
  - "[19-03]: check_duplicate_argument returns {exists: bool, argument_id: int|None} — no 404, absence of match is valid 200 (D-04)"
  - "[19-03]: update_argument_metadata returns False when argument not found; router raises HTTPException(404) — IDOR guard (T-19-03-02)"
  - "[19-03]: get_argument_detail return dict extended with source_docket and cover_metadata keys for job detail page (D-01, D-07)"
metrics:
  duration: 4
  completed: "2026-06-30"
status: complete
---

# Phase 19 Plan 03: FastAPI Layer — Schemas, Services, Router Summary

**One-liner:** FastAPI layer for Phase 19 — MetadataUpdate schema, two new service functions (check_duplicate_argument, update_argument_metadata), ArgumentDetail extended with source_docket/cover_metadata, and two new endpoints (GET check-duplicate, PATCH metadata) correctly ordered in the admin router.

## What Was Built

### Task 1: Schema Updates (api/schemas/admin_arguments.py)

Three changes:

**New MetadataUpdate class** — mass-assignment guard for the job detail metadata card (D-15, T-19-03-01). Only `case_name`, `source_docket`, and `argued_date` are writable. `argued_date` accepted as ISO 8601 string per project-wide V5 Input Validation pattern.

**ArgumentListItem.argued_date** changed from `datetime.date` (required) to `Optional[datetime.date] = None` per D-08 — job-driven ingest now leaves `argued_date` NULL instead of using today's date as a synthetic placeholder.

**ArgumentDetail** updated with:
- `argued_date` → `Optional[datetime.date] = None` (D-08)
- `source_docket: Optional[str] = None` (D-01 — new column from migration 0011)
- `cover_metadata: Optional[dict] = None` (D-07 — JSONB column from migration 0011)

### Task 2: Service Functions (api/services/admin_arguments.py)

**`check_duplicate_argument(db, docket, question) -> dict`** — parameterized query on `(Argument.source_docket, Argument.question_number)`. Returns `{"exists": bool, "argument_id": int | None}`. No 404 — absence of a match is a valid 200 response. SQLAlchemy bind parameters prevent SQL injection (T-19-03-03).

**`update_argument_metadata(db, argument_id, body: MetadataUpdate) -> bool`** — updates `Argument.argued_date`, `Argument.source_docket`, and (when `body.case_name` is not None) the lead `Case.case_name`. Returns `False` when the argument is not found; the router translates this to a 404 (T-19-03-02 IDOR guard). All UPDATE statements use `.execution_options(synchronize_session=False)` (Pitfall 5). Lead case lookup uses `CaseArgument.is_lead == True` — same pattern as `get_argument_detail`.

**`get_argument_detail` return dict** extended with two new keys:
- `"source_docket": argument.source_docket` (new column, may be None)
- `"cover_metadata": argument.cover_metadata` (new JSONB column, may be None)

### Task 3: Router Endpoints (api/routers/admin.py)

**`MetadataUpdate` import** added to the existing `from api.schemas.admin_arguments import ...` block.

**`GET /arguments/check-duplicate`** registered at route index 15, immediately BEFORE `GET /arguments/{argument_id}` at index 16 (T-19-03-05). FastAPI resolves literal path segments before parameterized ones — this ordering ensures "check-duplicate" is never consumed as an `argument_id` integer.

**`PATCH /arguments/{argument_id}/metadata`** registered after the unpublish route. Calls `arguments_service.update_argument_metadata(db, argument_id, body)`; raises `HTTPException(404)` when service returns `False`; returns `{"success": True}` on success.

Both new endpoints inherit X-Admin-Token auth from the router-level dependency (T-19-03-04) — no per-route auth annotation needed.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All new service functions have real logic. No hardcoded values, placeholders, or TODO markers in the modified files.

## Threat Surface Scan

No new network surface beyond what the plan's threat model documents. The two new endpoints were explicitly planned:

| Threat ID | Mitigation Verified |
|-----------|---------------------|
| T-19-03-01 | MetadataUpdate schema limits writes to {case_name, source_docket, argued_date} only |
| T-19-03-02 | update_argument_metadata returns False on not-found; router translates to 404 |
| T-19-03-03 | check_duplicate_argument uses SQLAlchemy bind params — no string interpolation |
| T-19-03-04 | Both new routes inherit router-level Depends(verify_admin_token) |
| T-19-03-05 | check-duplicate registered at index 15, argument_id at index 16 — confirmed via router inspection |

## Self-Check

| Artifact | Status |
|----------|--------|
| api/schemas/admin_arguments.py — MetadataUpdate class | FOUND — committed at 553eb27f |
| api/schemas/admin_arguments.py — ArgumentListItem.argued_date Optional | FOUND — committed at 553eb27f |
| api/schemas/admin_arguments.py — ArgumentDetail.source_docket, cover_metadata | FOUND — committed at 553eb27f |
| api/services/admin_arguments.py — check_duplicate_argument | FOUND — committed at a9cbf218 |
| api/services/admin_arguments.py — update_argument_metadata | FOUND — committed at a9cbf218 |
| api/services/admin_arguments.py — get_argument_detail extended | FOUND — committed at a9cbf218 |
| api/routers/admin.py — MetadataUpdate import | FOUND — committed at 8589fbdb |
| api/routers/admin.py — GET /arguments/check-duplicate | FOUND — committed at 8589fbdb |
| api/routers/admin.py — PATCH /arguments/{argument_id}/metadata | FOUND — committed at 8589fbdb |
| Route order: check-duplicate (idx 15) before {argument_id} (idx 16) | VERIFIED — python router inspection confirms |
| All imports resolve | VERIFIED — python -c "from api.schemas... from api.services... from api.routers..." exits 0 |

## Self-Check: PASSED

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1: Schema updates | 553eb27f | feat(19-03): update admin_arguments schemas — MetadataUpdate, Optional argued_date, source_docket/cover_metadata on ArgumentDetail |
| Task 2: Service functions | a9cbf218 | feat(19-03): add check_duplicate_argument and update_argument_metadata service functions |
| Task 3: Router endpoints | 8589fbdb | feat(19-03): register check-duplicate and metadata PATCH endpoints in admin router |
