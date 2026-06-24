---
phase: 12-people-admin-improvements
plan: "04"
subsystem: frontend-ui
tags: [people, photo, bio, merge, delete, sveltekit, svelte5, runes, form-actions]
status: complete

dependency_graph:
  requires:
    - photo/merge/delete named actions — Plan 03
    - merge-preview proxy +server.ts — Plan 03
    - can_delete + delete_block_count in load — Plan 03
    - photo_url_full in load — Plan 03
  provides:
    - bio + photo unified card with photo preview + Upload/URL tab widget (PADM-01)
    - merge section with eager count preview and confirm (PADM-03/PADM-04)
    - eligibility-gated delete section with tooltip (PADM-02)
    - merge transaction bug fix — drop nested db.begin() (12-01 regression)
  affects:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - api/services/admin_people.py

tech_stack:
  added: []
  patterns:
    - Svelte 5 Runes ($state only — no legacy stores)
    - photo form as sibling to save form (HTML disallows nested forms)
    - Bio & Photo as single standalone card — bio_text + photo widget in one form (post-verify fix)
    - photo action best-effort PATCHes bio_text before photo fetch (Pitfall 7 extended)
    - fetchMergePreview client-side fetch to same-origin /admin/people/[id]/merge-preview proxy (no ADMIN_TOKEN in client)
    - $state-driven tab toggle (photoTab upload | url) — no page reload
    - can_delete branching for delete button enabled/disabled state
    - aria-describedby + id="delete-tip" for accessible disabled tooltip
    - flat SQLAlchemy active-session commit pattern — no nested db.begin()

key_files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - api/services/admin_people.py

decisions:
  - "Post-verify fix: bio_text moved from save form into photo form. Bio & Photo is now a single card with a single form — bio textarea at top, photo widget below. photo action best-effort PATCHes bio_text before proceeding to photo save. Save action body drops bio_text (Pitfall 7 extended)."
  - "Post-verify fix: merge_people() dropped async with db.begin() block. SQLAlchemy 2.0 raises InvalidRequestError when db.begin() is called while a transaction is already in progress (started by the fetch-guard SELECTs). Fix: execute UPDATEs and DELETE flat on active session, call db.commit() once after all statements."
  - "Photo form placed as a sibling div/form adjacent to the save form (HTML nesting prohibition). Bio is in the same form as photo to avoid the visual split created by Court Tenure and Appointment sections sitting between them."
  - "fetchMergePreview fetches /admin/people/${data.person.id}/merge-preview (same-origin relative URL) — the +server.ts proxy injects ADMIN_TOKEN server-side so no token leaks to client (T-12-TOKENLEAK confirmed)"
  - "Delete button uses Svelte {#if data.can_delete} branching rather than disabled attribute + opacity; each branch renders its own button with appropriate styles"
  - "Merge confirm button conditioned on mergeTargetId && mergePreview — only appears after counts are loaded, preventing submission before the preview is visible"
  - "Count display preserves exact integers from the API — no rounding, no paraphrase (audit-relevant per T-12-COUNTFIDELITY)"

metrics:
  duration_minutes: 60
  completed_date: "2026-06-24"
  tasks_completed: 1
  files_changed: 3
---

# Phase 12 Plan 04: People Edit Page UI Restructure Summary

**One-liner:** Restructured people edit page with unified Bio & Photo card (bio + photo in one form), fixed SQLAlchemy nested-transaction crash in merge_people(), and wired photo action to best-effort save bio_text before photo.

## What Was Built

### Task 1 — Svelte UI (commit b89f6e3)

**app/src/routes/admin/people/[id]/+page.svelte restructured:**

- `photoTab = $state<'upload' | 'url'>('upload')` — drives tab toggle
- `photoSubmitting = $state(false)`, `mergeSubmitting = $state(false)`, `deleteSubmitting = $state(false)`
- `mergeTargetId = $state<string>('')`, `mergePreview = $state<{...} | null>(null)`, `mergeLoading`, `mergeError`
- `fetchMergePreview(targetId)` — async client-side fetch to same-origin merge-preview proxy

**Bio & Photo section (Task 1 approach — split across two adjacent cards):**
- Top card (inside save form): bio textarea only, with zero-corner CSS to visually connect to photo card below
- Bottom card (outside save form, separate `<form action="?/photo" enctype="multipart/form-data">`): photo preview + tab widget

**Merge section:** `<form action="?/merge">` with select picker, hidden target_id input, preview panel showing exact counts, confirm button conditioned on preview loaded.

**Delete section:** `<form action="?/delete">` with eligibility-gated button — enabled (red border) when `data.can_delete`, disabled (gray, cursor not-allowed) with `aria-describedby` tooltip when not.

## Post-Verify Fixes

Two bugs were identified during operator verification and fixed after the checkpoint.

### Fix 1 — Merge transaction crash (commit b11b754)

**File:** `api/services/admin_people.py` — `merge_people()`

**Root cause:** `merge_people()` called `async with db.begin():` after two `SELECT` queries had already started an implicit SQLAlchemy 2.0 transaction. SQLAlchemy 2.0 raises `InvalidRequestError: A transaction is already begun on this Session` when `db.begin()` is nested. The router's generic 500 handler surfaced this as "Merge failed. Please try again." in the UI.

**Fix:** Removed the `async with db.begin():` block. The four `UPDATE` statements and the `DELETE` now execute directly on the active session (part of the same implicit transaction started by the fetch-guard SELECTs), followed by a single `await db.commit()` after all statements complete.

### Fix 2 — Bio & Photo card placement (commit 61504f6)

**Files:** `app/src/routes/admin/people/[id]/+page.svelte` and `+page.server.ts`

**Root cause:** The bio textarea was inside the save form, which sits above Court Tenure and Appointment sections. The photo widget card was below Save Changes. The "connected card" zero-radius CSS did not work because the save form wrapped all those sections between the bio card and the photo card.

**Fix:**
- Removed bio_text div from inside the save form entirely
- Removed the zero-corner-radius connected-card hack on the photo widget
- Made the photo card a proper standalone card with `border-radius: 8px` and an H2 "Bio & Photo" heading
- Added bio_text textarea at the top of the photo card (above the photo preview)
- `photo` action now reads `bio_text` from formData and best-effort PATCHes it to `/api/admin/people/{id}` before the photo fetch
- `save` action body drops `bio_text` (Pitfall 7 extended — both bio and photo managed by photo action)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restructured photo widget placement to avoid nested form (Task 1)**
- **Found during:** Task 1 (svelte-check: "`<form>` cannot be a descendant of `<form>`")
- **Fix:** Split Bio & Photo section into two adjacent cards — bio in save form, photo widget as sibling form. Later superseded by post-verify Fix 2.
- **Commit:** b89f6e3

**2. [Rule 1 - Bug] SQLAlchemy nested transaction crash in merge_people() (post-verify Fix 1)**
- **Found during:** Human verify checkpoint — merge endpoint returning 500
- **Fix:** Dropped `async with db.begin():` block; execute flat on active session + `await db.commit()`
- **Files modified:** `api/services/admin_people.py`
- **Commit:** b11b754

**3. [Rule 2 - Missing functionality] Bio textarea placement renders bio below Save Changes button (post-verify Fix 2)**
- **Found during:** Human verify checkpoint — connected-card CSS not working
- **Fix:** Unified bio + photo into single standalone card outside save form; photo action saves bio best-effort
- **Files modified:** `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.server.ts`
- **Commit:** 61504f6

## Human Verify Checkpoint

- **Status:** Resolved — operator reviewed Task 1 output, identified two issues, provided fix instructions
- **Issues found:** (1) merge endpoint 500 on nested db.begin(); (2) bio textarea placement below Save Changes
- **Resolution:** Both fixes applied and committed after checkpoint

## Known Stubs

None. All data flows from live server load:
- `data.person.photo_url_full` — populated in load from FastAPI (Plan 03)
- `data.people` — populated in load as merge picker list (Plan 03)
- `data.can_delete` — derived in load from merge-preview counts (Plan 03)
- `mergePreview` — fetched client-side via same-origin proxy on picker change (Plan 03)
- `data.person.bio_text` — populated in load from FastAPI person detail (Plan 01)

## Threat Flags

No new threat surface beyond Plan 04's threat model. All five threat entries mitigated:
- T-12-CLIENTGATE: `data.can_delete` client gate is defense-in-depth; server enforces orphan check (Plan 02)
- T-12-SELFPICK: picker bound to `data.people` (load already excludes current person); server rejects self-merge with 422 (Plan 01/02)
- T-12-XSS-PHOTO: `photo_url_full` rendered in `<img src>` only — Svelte auto-escapes attribute values
- T-12-TOKENLEAK: client fetches same-origin `/admin/people/[id]/merge-preview` proxy; ADMIN_TOKEN never in client code (Plan 03)
- T-12-COUNTFIDELITY: counts rendered as exact integers from API — no rounding or paraphrase

## Self-Check

- [x] `app/src/routes/admin/people/[id]/+page.svelte` — FOUND
- [x] `app/src/routes/admin/people/[id]/+page.server.ts` — FOUND
- [x] `api/services/admin_people.py` — FOUND
- [x] Commit `b89f6e3` — FOUND (feat(12-04): restructure Bio & Photo + add Merge and Delete sections)
- [x] Commit `b11b754` — FOUND (fix(12-01): resolve merge transaction error)
- [x] Commit `61504f6` — FOUND (fix(12-04): move bio_text into photo form)
- [x] `tsc --noEmit` on people/[id] files — PASSED (tsc ok)

## Self-Check: PASSED
