---
phase: 11-argument-metadata-editing
plan: "02"
subsystem: api-backend
tags: [fastapi, pydantic, sqlalchemy, admin, arguments, publish]
dependency_graph:
  requires: ["11-01"]
  provides: ["11-03", "11-04"]
  affects: ["api/routers/admin.py", "api/schemas/admin_arguments.py", "api/services/admin_arguments.py"]
tech_stack:
  added: []
  patterns:
    - "Service-layer pattern mirroring admin_people.py (load → validate → write → return detail)"
    - "ArgumentUpdate mass-assignment allow-list (T-11-MASS)"
    - "Pre-write collision queries for slug and docket_number uniqueness"
    - "Slug freeze-on-publish with re-derivation only when published_at IS NULL (D-11)"
    - "_derive_slug imported from pipeline.commands.ingest (cross-layer precedent)"
    - "EVERY update() chained with .execution_options(synchronize_session=False) (Pitfall 5)"
key_files:
  created:
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
  modified:
    - api/routers/admin.py
decisions:
  - "[11-02]: ArgumentUpdate allow-list is exactly {case_name, docket_number, argued_date} — published_at is never PATCH-writable (T-11-MASS)"
  - "[11-02]: _derive_slug imported from pipeline.commands.ingest per A1 — no circular import; cross-layer precedent confirmed"
  - "[11-02]: slug freeze implemented — re-derive only when argument.published_at IS None; when published, only case_name display updates (D-11 / Pitfall 3)"
  - "[11-02]: Pre-write slug collision query raises ValueError('slug_collision'); docket collision raises ValueError('docket_collision') — both surface as 422 (T-11-SLUG, T-11-DOCKET)"
  - "[11-02]: publish_argument enforces resolved_at IS NOT NULL server-side (T-11-PUBGATE / Pitfall 1) — UI gate alone is insufficient"
  - "[11-02]: get_argument_detail returns None when argument exists but has no lead case (data integrity guard)"
  - "[11-02]: docket_number_norm set to stripped docket value on update (consistent with ingest — no separate norm function exported)"
metrics:
  duration: 3
  completed_date: "2026-06-22"
  tasks: 3
  files: 5
status: complete
---

# Phase 11 Plan 02: Argument Metadata Editing Backend Summary

**One-liner:** FastAPI admin backend for argument metadata editing — schemas, service with slug re-derivation + collision detection + publish guards, and five routed endpoints with inherited auth.

## What Was Built

### Task 1: Pydantic schemas (api/schemas/admin_arguments.py)

Four schema classes following `admin_people.py` conventions:

- `ConsolidatedDocket` — single `docket_number: str` field for non-lead dockets
- `ArgumentListItem` — id, argued_date, case_name, docket_number, resolved_at, published_at; `from_attributes=True`
- `ArgumentDetail` — extends ArgumentListItem with `slug` and `consolidated_dockets`; `from_attributes=True`
- `ArgumentUpdate` — PATCH body with exactly three writable fields: `case_name`, `docket_number`, `argued_date` (T-11-MASS); published_at, slug, and id are explicitly excluded

### Task 2: Service module (api/services/admin_arguments.py)

Five async service functions:

- `list_arguments(db)` — JOIN Argument + CaseArgument + Case WHERE is_lead, ORDER BY argued_date DESC
- `get_argument_detail(db, id)` — lead case + consolidated dockets; returns None on missing id (IDOR guard)
- `update_argument(db, id, body)` — argued_date via fromisoformat(); docket collision pre-check; case_name with slug re-derivation gate (published_at IS NULL only); all changes committed atomically
- `publish_argument(db, id)` — resolved_at IS NOT NULL guard; already-published guard; stamps published_at=now()
- `unpublish_argument(db, id)` — not-published guard; clears published_at=None

Helper `_derive_slug` imported from `pipeline.commands.ingest` (import confirmed non-circular; precedent from `admin_jobs.py` → `pipeline.commands.resolve`).

Every `update()` call uses `.execution_options(synchronize_session=False)` (Pitfall 5).

### Task 3: Routes (api/routers/admin.py + api/tests/test_admin_arguments_routes.py)

Five new routes added to the existing `router` (inherits `verify_admin_token` at construction):

| Method | Path | Handler |
|--------|------|---------|
| GET | /api/admin/arguments | `list_arguments` |
| GET | /api/admin/arguments/{id} | `get_argument` |
| PATCH | /api/admin/arguments/{id} | `update_argument` |
| POST | /api/admin/arguments/{id}/publish | `publish_argument` |
| POST | /api/admin/arguments/{id}/unpublish | `unpublish_argument` |

ValueError → HTTPException(422) with detail string; None result → HTTPException(404).

## Test Results

- `api/tests/test_admin_arguments_service.py`: 12 passed, 4 skipped (DB tests skipped — no DATABASE_URL)
- `api/tests/test_admin_arguments_routes.py`: 5 passed, 5 skipped (DB tests skipped — no DATABASE_URL)
- Pre-existing failure in `test_arguments.py::test_get_utterances_returns_404_for_unknown_argument` confirmed as pre-existing (fails on prior commit too); not caused by this plan.

## Threat Mitigations Implemented

| Threat | Mitigation | Where |
|--------|-----------|-------|
| T-11-MASS | ArgumentUpdate allow-list exactly {case_name, docket_number, argued_date} | schemas, verified by test |
| T-11-IDOR | Service returns None → router returns 404 for all five endpoints | service + router |
| T-11-AC | Routes inherit router-level Depends(verify_admin_token); test asserts 401 | router + test |
| T-11-PUBGATE | Backend checks resolved_at IS NOT NULL before publish; ValueError → 422 | service |
| T-11-SLUG | Pre-write collision query on Case.slug → ValueError("slug_collision") → 422 | service |
| T-11-DOCKET | Pre-write collision query on Case.docket_number → ValueError("docket_collision") → 422 | service |
| T-11-VALID | argued_date parsed with datetime.date.fromisoformat() → clean ValueError → 422 | service |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] docket_number_norm update on PATCH**

- **Found during:** Task 2 implementation
- **Issue:** PLAN.md action text notes to "keep docket_number_norm consistent with the existing ingest normalization". The `Case` model has a NOT NULL `docket_number_norm` column. When `docket_number` is updated, `docket_number_norm` must also be updated or the row will have a stale norm value.
- **Fix:** In `update_argument()`, when `docket_number` is changed, also set `lead_case.docket_number_norm = new_docket` (stripped). The pipeline does not export a separate `_normalize_docket_number` function; the norm is set to the stripped operator input, which is equivalent to what ingest writes for correctly-formatted dockets.
- **Files modified:** `api/services/admin_arguments.py`
- **Commit:** 3aa579f

## Known Stubs

None — all service functions are fully implemented. No hardcoded empty values or placeholder data.

## Threat Flags

None — all new surface is admin-gated and follows the established T-11-* threat register in the plan.

## Self-Check: PASSED
