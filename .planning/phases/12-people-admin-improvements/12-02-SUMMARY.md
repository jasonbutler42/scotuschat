---
phase: 12-people-admin-improvements
plan: "02"
subsystem: backend-router
tags: [people, merge, delete, photo, staticfiles, http-endpoints]
status: complete

dependency_graph:
  requires:
    - upload_photo (api/services/admin_people.py) — Plan 01
    - merge_people (api/services/admin_people.py) — Plan 01
    - delete_person_if_orphan (api/services/admin_people.py) — Plan 01
    - get_merge_preview (api/services/admin_people.py) — Plan 01
    - update_photo_url (api/services/admin_people.py) — Plan 01
    - MergeRequest schema (api/schemas/admin_people.py) — Plan 01
    - MergePreview schema (api/schemas/admin_people.py) — Plan 01
  provides:
    - POST /api/admin/people/{person_id}/photo
    - GET /api/admin/people/{person_id}/merge-preview
    - POST /api/admin/people/{person_id}/merge
    - DELETE /api/admin/people/{person_id}
    - StaticFiles mount at /uploads serving data/uploads
  affects:
    - api/routers/admin.py
    - api/main.py

tech_stack:
  added: []
  patterns:
    - two-gate image validation (content_type first gate + Pillow second gate)
    - img.format read before img.verify() (Pitfall 2 avoidance)
    - ValueError→HTTPException(422) wrap (mirrors resolve_job pattern)
    - None→404 / False→409 / True→200 status mapping for delete_person
    - StaticFiles mount after router includes (API routes take precedence)
    - os.makedirs exist_ok=True for directory bootstrap on import

key_files:
  created: []
  modified:
    - api/routers/admin.py
    - api/main.py

decisions:
  - "img.format read before img.verify() — Pillow verify() exhausts the image object; format unreadable after (Pitfall 2)"
  - "target_id accepted as query param for merge-preview frontend contract but counts derive from source only (D-09)"
  - "StaticFiles mount placed after router includes — API routes take precedence; mount is harmless when Spaces is active"
  - "os.makedirs called at module import time — directory guaranteed to exist before any upload_photo local-path write"
  - "No per-route Depends(verify_admin_token) added — router-level dependency covers all four endpoints (T-12-AUTH)"

metrics:
  duration_minutes: 25
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_changed: 2
---

# Phase 12 Plan 02: People Admin HTTP Endpoints Summary

**One-liner:** Four people admin endpoints (photo upload with two-gate image validation, merge preview, atomic merge, orphan-only delete) wired to the Plan 01 service layer, plus a StaticFiles mount for local photo serving.

## What Was Built

This plan wires the five Plan 01 service functions to HTTP. No new service logic — the router is the sole place server-side image validation and HTTP status mapping happen.

### api/routers/admin.py — 4 new endpoints

**New imports added:** `from io import BytesIO`, `from PIL import Image, UnidentifiedImageError`, `MergePreview` and `MergeRequest` added to the existing `from api.schemas.admin_people import (...)` block. `spaces_service` was already imported.

**`POST /api/admin/people/{person_id}/photo`** (`upload_person_photo`):
- First gate: `content_type.startswith("image/")` — fast reject for obviously wrong types (client-supplied, spoofable)
- Second gate: `Image.open(BytesIO(file_bytes))` → read `img.format` **before** `img.verify()` (Pitfall 2 — verify() exhausts the object) → `UnidentifiedImageError | Exception` → 422
- Format→ext map: `{"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}` defaulting to "jpg"
- Dual path: file → `people_service.upload_photo()`, URL → `people_service.update_photo_url()`, neither → 422
- None result → 404; success → `PersonDetail(**result)`

**`GET /api/admin/people/{person_id}/merge-preview`** (`get_merge_preview`):
- Accepts `target_id` as query param (frontend contract); counts derive from source only (D-09)
- Calls `people_service.get_merge_preview(db, person_id)` → None→404, counts→`MergePreview(**counts)`

**`POST /api/admin/people/{person_id}/merge`** (`merge_person`):
- Wraps `people_service.merge_people(db, person_id, body.target_id)` in `try/except ValueError → HTTPException(422)`
- Self-merge raises ValueError in service → propagates to 422 (T-12-SELF)
- None result → 404; success → `PersonDetail(**result)`

**`DELETE /api/admin/people/{person_id}`** (`delete_person`):
- Maps service returns: `None → 404`, `False → 409`, `True → {"deleted": True}` (status 200)
- Server-side orphan COUNT is authoritative (T-12-ORPHAN); client disabled state is defense-in-depth only

All four endpoints inherit auth from router-level `dependencies=[Depends(verify_admin_token)]` — no per-route auth added (T-12-AUTH, verified: `grep -c verify_admin_token` still returns 4).

### api/main.py — StaticFiles mount

Added `import os` and `from fastapi.staticfiles import StaticFiles`. After all `app.include_router(...)` calls:
```python
os.makedirs("data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")
```
- `os.makedirs` at import time guarantees the directory exists before any local-path photo write
- Mount placed after all router includes so API routes take precedence over file serving
- Serves locally-stored photos at `/uploads/people/{file}` matching the relative path written by `upload_photo` (D-01 local fallback)
- Harmless when DO Spaces is active (directory stays empty)

## Deviations from Plan

None — plan executed exactly as written.

All threat mitigations implemented:
- T-12-UPLOAD: two-gate image validation (content_type first, Pillow second) with 422 on failure
- T-12-AUTH: router-level dependency covers all four endpoints; verify_admin_token count unchanged
- T-12-SELF: ValueError from service propagates to HTTPException(422)
- T-12-ORPHAN: server-side COUNT authoritative; router returns 409 on False return
- T-12-IDOR: None return → HTTPException(404) on all four endpoints
- T-12-PATHTRAVERSAL: filename derived server-side as `{person_id}.{ext}` from validated int + format-map ext

## Known Stubs

None. This plan is router + static-file config only — no data flow to UI rendering.

## Threat Flags

No new threat surface introduced beyond the threat model. The four HTTP endpoints and the StaticFiles mount are the planned surfaces. No new auth paths, schema changes, or trust boundary crossings beyond what was specified.

## Self-Check

- [x] `POST /api/admin/people/{person_id}/photo` present in OpenAPI schema
- [x] `GET /api/admin/people/{person_id}/merge-preview` present in OpenAPI schema
- [x] `POST /api/admin/people/{person_id}/merge` present in OpenAPI schema
- [x] `DELETE /api/admin/people/{person_id}` present in OpenAPI schema
- [x] `/uploads` StaticFiles mount present on `app.routes`
- [x] `data/uploads` directory exists after import
- [x] `verify_admin_token` count in admin.py = 4 (unchanged from pre-task baseline)
- [x] `img.format` read before `img.verify()` in upload_person_photo

## Self-Check: PASSED

All artifacts confirmed present. Both commits verified in git log.

Commits:
- 2138d47: feat(12-02): add photo, merge-preview, merge, delete people admin endpoints
- f5de634: feat(12-02): mount StaticFiles at /uploads for local photo serving
