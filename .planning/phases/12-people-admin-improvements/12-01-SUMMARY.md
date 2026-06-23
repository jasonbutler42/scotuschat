---
phase: 12-people-admin-improvements
plan: "01"
subsystem: backend-services
tags: [people, merge, delete, photo, spaces, service-layer]
status: complete

dependency_graph:
  requires: []
  provides:
    - upload_photo_to_spaces (api/services/spaces.py)
    - get_merge_preview (api/services/admin_people.py)
    - merge_people (api/services/admin_people.py)
    - delete_person_if_orphan (api/services/admin_people.py)
    - update_photo_url (api/services/admin_people.py)
    - upload_photo (api/services/admin_people.py)
    - MergeRequest schema (api/schemas/admin_people.py)
    - MergePreview schema (api/schemas/admin_people.py)
  affects:
    - api/services/admin_people.py
    - api/services/spaces.py
    - api/schemas/admin_people.py

tech_stack:
  added: []
  patterns:
    - async with db.begin() atomic transaction (T-12-ATOMIC)
    - fetch-guard → None return → router 404 (T-12-IDOR)
    - execution_options(synchronize_session=False) on every UPDATE/DELETE (T-12-SYNC)
    - server-side orphan COUNT before delete (T-12-ORPHAN)
    - ValueError("Source and target must be different people.") on self-merge (T-12-SELF)
    - asyncio.get_running_loop().run_in_executor for sync Spaces call

key_files:
  created:
    - api/tests/test_admin_people_merge.py
  modified:
    - api/services/spaces.py
    - api/services/admin_people.py
    - api/schemas/admin_people.py

decisions:
  - "upload_photo_to_spaces mirrors upload_pdf_to_spaces with caller-supplied content_type; no ACL arg (deferred)"
  - "merge_people uses single async with db.begin() — context manager commits; no inner db.commit() (D-10)"
  - "delete_person_if_orphan returns False (not raises) when FK rows exist — router translates to 409"
  - "upload_photo imports spaces lazily inside function body to avoid any circular import risk"
  - "MergePreview has model_config from_attributes=True; MergeRequest does not (request-only body)"
  - "get_merge_preview takes only source_id — target_id not needed for counts (D-09 confirmed)"

metrics:
  duration_minutes: 35
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_changed: 4
---

# Phase 12 Plan 01: People Admin Service Layer Summary

**One-liner:** Five new service functions (photo upload dual-path, atomic merge, merge preview counts, orphan-only delete, URL update) and one Spaces helper backed by TDD tests.

## What Was Built

This plan builds the pure service + schema layer for all four Phase 12 requirements. No HTTP routing or frontend work — the router (Plan 02) and frontend (Plans 03–04) will build against this stable contract.

### api/services/spaces.py

Added `upload_photo_to_spaces(file_bytes: bytes, key: str, content_type: str) -> str` that mirrors `upload_pdf_to_spaces` exactly: same `get_spaces_client()` call, same `upload_fileobj` pattern, same return-the-key contract — only difference is the `ContentType` ExtraArg uses the caller-supplied `content_type` parameter instead of the hardcoded `"application/pdf"`. No ACL ExtraArg added (DO Spaces ACL setup is deferred per CONTEXT.md).

### api/schemas/admin_people.py

Added two Pydantic v2 schemas:
- `MergeRequest(target_id: int)` — POST body for `/api/admin/people/{id}/merge`; no `model_config` (request-only)
- `MergePreview(utterances, aliases, appearances, argument_participants: int)` — GET merge-preview response; `model_config = {"from_attributes": True}` per response-model convention

### api/services/admin_people.py

Added five Phase 12 service functions:

**`get_merge_preview(db, source_id)`** — Fetch-guard (None if missing), then one `COUNT()` per FK table (Utterance/SpeakerAlias/CaseAppearance/ArgumentParticipant). Returns `{"utterances": N, "aliases": N, "appearances": N, "argument_participants": N}`.

**`merge_people(db, source_id, target_id)`** — Self-merge guard raises `ValueError("Source and target must be different people.")` before any DB access. Fetch-guards both persons (None if either missing). Runs 4x `update(model).where(col == source_id).values(...)` + `delete(Person)` inside a single `async with db.begin()` block — no `db.commit()` inside the block (context manager commits on clean exit). Returns `get_person_detail(target_id)` after commit.

**`delete_person_if_orphan(db, person_id)`** — Fetch-guard (None if missing). COUNTs across all 4 FK tables; returns `False` on any positive count (caller → 409). On zero counts, executes `delete(Person)`, `await db.commit()`, returns `True`.

**`update_photo_url(db, person_id, photo_url)`** — URL-only path (D-03). Normalizes empty/whitespace to None (Pitfall 5 convention). Commits, returns refreshed detail.

**`upload_photo(db, person_id, file_bytes, ext, content_type)`** — Dual-path (D-01): if `settings.do_spaces_bucket` is set, uploads via `run_in_executor` calling `spaces_service.upload_photo_to_spaces`, sets full public URL. Otherwise writes to `data/uploads/people/{person_id}.{ext}` (mkdir parents=True), sets relative path `/uploads/people/{person_id}.{ext}`.

### api/tests/test_admin_people_merge.py

New test file covering the full behavior block:
- Import tests for all 5 functions, schemas, and spaces helper (no DB required)
- `merge_people` self-merge `ValueError` (no DB required — fake DB stub asserts never-called)
- `get_merge_preview` returns None for missing source (DB-guarded)
- `get_merge_preview` returns correct zero-counts for fresh person (DB-guarded)
- `delete_person_if_orphan` returns None for missing person (DB-guarded)
- `delete_person_if_orphan` returns True and removes orphaned person (DB-guarded)
- `merge_people` returns None for missing source/target (DB-guarded)
- `merge_people` transfers rows and deletes source (DB-guarded)

All 4 no-DB tests pass; 6 DB-guarded tests skip when `DATABASE_URL` is not configured. Pre-existing `test_arguments.py::test_get_utterances_returns_404_for_unknown_argument` failure is unrelated and pre-dates this plan (confirmed by stash test).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 73eca12 | test(12-01): add failing tests — confirmed ImportError on first run |
| GREEN (feat) | 7595dad | feat(12-01): implement service functions — 4 passed, 6 skipped |
| REFACTOR | — | No refactor needed — implementation is clean |

## Deviations from Plan

None — plan executed exactly as written.

All threat mitigations in the plan's threat register are implemented:
- T-12-SELF: `if source_id == target_id: raise ValueError(...)` at top of `merge_people`
- T-12-ATOMIC: all operations inside single `async with db.begin()`
- T-12-ORPHAN: server-side COUNT before delete; returns False on any positive count
- T-12-IDOR: fetch-guard returns None for unknown person_id on every function
- T-12-SYNC: `.execution_options(synchronize_session=False)` on every `update()` / `delete()`
- T-12-SC: zero new packages installed (Pillow/boto3 already in requirements.txt)

## Known Stubs

None. This plan is service+schema only — no data flow to UI rendering.

## Threat Flags

No new threat surface introduced beyond what was planned. All five service functions operate on the `people` table and 4 FK child tables as documented in the threat model. No new network endpoints, auth paths, or schema changes.

## Self-Check

- [x] api/services/spaces.py — upload_photo_to_spaces present
- [x] api/services/admin_people.py — all 5 new functions present
- [x] api/schemas/admin_people.py — MergeRequest and MergePreview present
- [x] api/tests/test_admin_people_merge.py — created and passing

Commits:
- fbe0e4c: feat(12-01): add upload_photo_to_spaces and MergeRequest/MergePreview schemas
- 73eca12: test(12-01): add failing tests (RED)
- 7595dad: feat(12-01): add merge/preview/orphan-delete/upload service functions (GREEN)
