---
phase: 12-people-admin-improvements
plan: "05"
subsystem: api
tags: [gap-fix, photo-upload, delete, aliases]
status: complete

dependency_graph:
  requires: []
  provides: [photo-url-fetch, alias-safe-delete]
  affects: [api/routers/admin.py, api/services/admin_people.py]

tech_stack:
  added: [httpx]
  patterns: [httpx-async-client, pillow-two-gate-validation, delete-before-orphan-check]

key_files:
  modified:
    - api/routers/admin.py
    - api/services/admin_people.py

decisions:
  - Photo URL path now fetches bytes via httpx and saves locally via upload_photo — no external references stored
  - Aliases deleted before orphan check — they are intrinsic name variants, not blocking FK rows
  - Two-gate Pillow validation (img.format before img.verify) applied identically to URL path and file-upload path

metrics:
  duration_minutes: 1
  completed_date: "2026-06-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 12 Plan 05: Gap Fix — Photo URL Fetch + Alias-Safe Delete Summary

**One-liner:** Fixes two UAT gaps — photo URL path now fetches and saves image bytes locally via httpx + Pillow, and alias-only persons can now be deleted by removing aliases before the orphan check.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Fix photo URL path: fetch, validate, save locally | b18ecb7 |
| 2 | Fix delete: delete aliases before orphan check | 1bfb7f7 |

## What Was Built

### Task 1 — Photo URL fetch and save (Gap A)

**File:** `api/routers/admin.py`

- Added `import httpx` at module level (line 40, alphabetically after `import hmac`)
- Replaced the `elif photo_url is not None:` branch (previously one line calling `update_photo_url`) with a full fetch-validate-save pipeline:
  1. `httpx.AsyncClient(timeout=10.0)` fetches bytes from the URL with redirect following
  2. Two-gate Pillow validation (same as file-upload path): `img.format` read before `img.verify()` (Pitfall 2)
  3. `people_service.upload_photo()` called with fetched bytes — uses existing dual-path local/Spaces logic

**Root cause closed:** External photo URLs were stored as strings in `photo_url` without fetching. Now all photos are self-contained regardless of input path.

### Task 2 — Alias-safe delete (Gap B)

**File:** `api/services/admin_people.py`

- Added `delete(SpeakerAlias)` step immediately after the `if person is None: return None` guard in `delete_person_if_orphan`
- Removed `(SpeakerAlias, SpeakerAlias.person_id)` from the orphan-check loop — only `Utterance`, `CaseAppearance`, and `ArgumentParticipant` block deletion
- `SpeakerAlias` and `delete` imports were already present — no new imports needed

**Root cause closed:** Any alias count > 0 was returning `False` (409 Conflict). Aliases are name variants intrinsic to the person and should be deleted with them.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched the plan's code snippets precisely.

## Verification

- `grep -n "httpx" api/routers/admin.py` shows `import httpx` at line 40 and `httpx.AsyncClient` inside `upload_person_photo`
- `grep -n "SpeakerAlias" api/services/admin_people.py` shows the new `delete(SpeakerAlias)` call at line 380 but NOT inside the orphan-check loop (which now has only 3 entries)
- `python -c "import ast; ast.parse(open('api/routers/admin.py').read()); ast.parse(open('api/services/admin_people.py').read()); print('syntax OK')"` passes

## Known Stubs

None.

## Threat Flags

None — no new network endpoints or auth paths introduced. The httpx fetch in the URL path is server-initiated (not user-controlled target for SSRF) within the existing admin-authenticated endpoint.

## Self-Check: PASSED

- `api/routers/admin.py` — confirmed modified, `import httpx` at line 40, URL fetch block present
- `api/services/admin_people.py` — confirmed modified, alias deletion step before orphan loop
- Commit `b18ecb7` — confirmed in git log
- Commit `1bfb7f7` — confirmed in git log
