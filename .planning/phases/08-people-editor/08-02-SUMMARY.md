---
phase: 08-people-editor
plan: "02"
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, admin, people-editor, crud]
status: complete

dependency_graph:
  requires: [08-01]
  provides: [admin-people-api, admin-roles-api, admin-participants-api]
  affects: [08-03, 08-04, 08-05]

tech_stack:
  added: []
  patterns:
    - FastAPI PATCH with Pydantic v2 optional fields and IDOR guard (return None → 404)
    - SQLAlchemy delete-and-reinsert tenure strategy (single transaction, execution_options)
    - FastAPI dependency override in pytest for auth-without-DB testing
    - find-or-create role pattern (select before insert, no IntegrityError risk)

key_files:
  created:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people.py
    - api/tests/test_admin_people_schemas_service.py
  modified:
    - api/routers/admin.py

decisions:
  - GET /api/admin/people upgraded to PersonListItem (superset of old PersonResponse — adds role_id + missing); Phase 7 typeahead consumers unaffected since they only read id/full_name/role_name
  - Auth tests use dependency_overrides[get_db] = async_generator to bypass DB lifespan; FastAPI resolves auth before DB when token is wrong, returning 401 without reaching get_db
  - Verification via app.openapi() spec rather than app.routes traversal — include_router stores _IncludedRouter objects not APIRoute; OpenAPI confirms all routes registered

metrics:
  duration_minutes: 8
  completed_date: "2026-06-17"
  tasks_completed: 3
  files_changed: 5
---

# Phase 08 Plan 02: Admin People API Summary

**One-liner:** FastAPI admin people backend — schemas (PersonListItem/PersonDetail/PersonUpdate/TenureRow/RoleCreate/RoleResponse/ParticipantItem), service (list_people with incomplete filter, get_person_detail, update_person with delete-and-reinsert tenure, create_role find-or-create, list_participants_for_job), and five new routes on the admin router.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD) | Create admin_people schemas + service module | b725ac9 (RED), 653e465 (GREEN) | api/schemas/admin_people.py, api/services/admin_people.py |
| 2 | Wire five routes into the admin router | 4b69847 | api/routers/admin.py |
| 3 (TDD) | Add backend tests for the new people endpoints | 1963f02 | api/tests/test_admin_people.py |

## What Was Built

### Schemas (`api/schemas/admin_people.py`)

- `TenureRow` — seat, start_date, end_date all `Optional[str] = None` (ISO date strings)
- `PersonListItem` — id, full_name, role_id, role_name, missing (list[str]); `from_attributes=True`
- `PersonDetail` — full edit form data including tenures list
- `PersonUpdate` — PATCH body with all optional fields; mass-assignment guard (T-08-MASS) — only full_name, role_id, bio_text, photo_url, tenures exposed
- `RoleCreate` — name (str, required)
- `RoleResponse` — id (int), name (str)
- `ParticipantItem` — person_id, full_name, role_name

### Service (`api/services/admin_people.py`)

- `_missing_fields(person)` — returns ["role","bio","photo"] ordered list per D-04/D-06; tenure absence is NOT missing
- `list_people(db, incomplete=False)` — outerjoin Person+Role, optional OR filter for IS NULL fields (D-04, PEOPLE-02)
- `get_person_detail(db, person_id)` — returns None for unknown id; loads all CourtTenure rows ordered by start_date ASC NULLS FIRST (D-08)
- `update_person(db, person_id, body)` — IDOR guard (return None → 404); empty-string normalization to None (Pitfall 5); calls `_replace_tenures` if tenures not None; single `await db.commit()`; returns refreshed detail dict
- `_replace_tenures(db, person_id, tenures)` — delete-and-reinsert strategy (D-09, Pattern 5); skips rows where both seat and start_date are falsy; parses dates with `datetime.date.fromisoformat()` (Pitfall 6); raises `ValueError` on malformed dates; does NOT commit (caller commits)
- `create_role(db, name)` — find-or-create on Role.name (D-10); avoids IntegrityError on unique constraint
- `list_participants_for_job(db, job_id)` — returns None if job not found or argument_id is None; joins ArgumentParticipant→Person→Role WHERE person_id IS NOT NULL (D-02)

Critical patterns verified:
- 2 `execution_options(synchronize_session=False)` calls (one on `delete(CourtTenure)` in `_replace_tenures`) — project-wide requirement
- No `Base.metadata.create_all` — Alembic is sole DDL authority

### Routes (`api/routers/admin.py`)

- `GET /api/admin/people?incomplete=bool` — replaces old route returning PersonResponse; upgraded to PersonListItem with incomplete filter; Phase 7 typeahead unaffected (PersonListItem is a superset)
- `GET /api/admin/people/{person_id}` — PersonDetail, 404 if None (T-08-IDOR)
- `PATCH /api/admin/people/{person_id}` — PersonUpdate body, 404/422 guards, ValueError→422 for malformed dates, mass-assignment bounded
- `POST /api/admin/roles` (201) — RoleResponse, find-or-create semantics
- `GET /api/admin/jobs/{job_id}/participants` — list[ParticipantItem], 404 if no argument
- No per-route `Depends(verify_admin_token)` — all five routes inherit from router-level dependency (T-08-AC)

### Tests (`api/tests/test_admin_people.py`)

- 5 auth tests (no DB): wrong-token returns 401 for all four new admin paths + upgraded list path; use `dependency_overrides[get_db]` so tests run without live DB
- 4 DB-guarded tests (skip when no DATABASE_URL): list_people returns PersonListItem shape, incomplete filter correctness, 404 for unknown person, 404 for unknown job participants
- Result: `5 passed, 4 skipped` — exits 0

## Verification Results

- `from api.main import app` imports cleanly ✓
- All 5 routes verified via `app.openapi()` spec ✓
- `python -m pytest api/tests/test_admin_people.py -x -q` → `5 passed, 4 skipped` ✓
- `grep -c 'execution_options(synchronize_session=False)'` → 2 ✓
- No `Base.metadata.create_all` in changed files ✓
- Pre-existing `test_arguments.py` failure confirmed not introduced by this plan ✓

## Deviations from Plan

### [Rule 1 - Bug] Plan verification script uses app.routes traversal that doesn't flatten include_router

**Found during:** Task 2
**Issue:** Plan's verify command `paths={(r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r,'methods')}` returns only 1 route (`/health`) because FastAPI's `include_router()` stores routers as `_IncludedRouter` objects in `app.routes` — these lack `.path`/`.methods` as direct attributes.
**Fix:** Verified all 5 routes using `app.openapi()` spec traversal instead — this is the correct approach for FastAPI's nested router structure.
**Impact:** Routes ARE correctly registered; the verification approach was changed, not the implementation.

### [Rule 2 - Missing critical functionality] TDD test: FastAPI returns 422 (not 401) for missing required header

**Found during:** Task 3
**Issue:** `verify_admin_token` uses `Header(...)` (required header). FastAPI returns 422 when the header is absent entirely. Plan specified "no token → 401" but the actual behavior is 422 for missing headers, 401 for wrong tokens.
**Fix:** Auth tests use wrong-token approach (value "invalid-token-value") which correctly returns 401, proving the auth dependency is inherited. Added documentation in test docstrings explaining the 422 vs 401 distinction.
**Security impact:** None — both 401 (wrong token) and 422 (missing header) reject the request before any handler logic runs. Auth is correctly enforced either way.

## Threat Surface Scan

All mitigations from the plan's threat register are implemented:

| Threat ID | Status |
|-----------|--------|
| T-08-AC | Mitigated — router-level auth inherited; test_admin_people.py asserts 401 on all new routes |
| T-08-IDOR | Mitigated — get_person_detail/update_person return None for unknown id → 404 |
| T-08-MASS | Mitigated — PersonUpdate exposes ONLY full_name, role_id, bio_text, photo_url, tenures |
| T-08-SQLI | Mitigated — all queries use SQLAlchemy ORM parameterized queries |
| T-08-DATE | Mitigated — datetime.date.fromisoformat() validates ISO; ValueError → 422 before DB write |
| T-08-NULL | Mitigated — empty-string bio/photo normalized to None on write in update_person() |
| T-08-SC | N/A — zero new packages |

## Known Stubs

None — all service functions are fully implemented. No hardcoded empty values, placeholder text, or unconnected data sources.

## Self-Check: PASSED

- `api/schemas/admin_people.py` — FOUND ✓
- `api/services/admin_people.py` — FOUND ✓
- `api/routers/admin.py` (5 routes including upgraded list) — FOUND ✓
- `api/tests/test_admin_people.py` — FOUND ✓
- `api/tests/test_admin_people_schemas_service.py` — FOUND ✓
- Commit b725ac9 (test RED) — FOUND ✓
- Commit 653e465 (feat GREEN) — FOUND ✓
- Commit 4b69847 (feat routes) — FOUND ✓
- Commit 1963f02 (feat tests) — FOUND ✓
- execution_options count = 2 ✓
- No Base.metadata.create_all ✓
- pytest exits 0 ✓
