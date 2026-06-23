---
phase: 12-people-admin-improvements
plan: "04"
subsystem: frontend-ui
tags: [people, photo, merge, delete, sveltekit, svelte5, runes, form-actions]
status: complete

dependency_graph:
  requires:
    - photo/merge/delete named actions — Plan 03
    - merge-preview proxy +server.ts — Plan 03
    - can_delete + delete_block_count in load — Plan 03
    - photo_url_full in load — Plan 03
  provides:
    - photo preview + Upload/URL tab widget (PADM-01)
    - merge section with eager count preview and confirm (PADM-03/PADM-04)
    - eligibility-gated delete section with tooltip (PADM-02)
  affects:
    - app/src/routes/admin/people/[id]/+page.svelte

tech_stack:
  added: []
  patterns:
    - Svelte 5 Runes ($state only — no legacy stores)
    - photo form as sibling to save form (HTML disallows nested forms)
    - Bio & Photo card split across two adjacent divs — top half in save form, photo widget as standalone form below
    - fetchMergePreview client-side fetch to same-origin /admin/people/[id]/merge-preview proxy (no ADMIN_TOKEN in client)
    - $state-driven tab toggle (photoTab upload | url) — no page reload
    - can_delete branching for delete button enabled/disabled state
    - aria-describedby + id="delete-tip" for accessible disabled tooltip

key_files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.svelte

decisions:
  - "Photo form placed as a sibling div/form adjacent to the save form (HTML nesting prohibition). Bio & Photo card is visually split — bio textarea stays inside the save form's card, photo widget is a continuation card outside the save form. This avoids enctype on the save form (Pitfall 1) and keeps the visual grouping intact."
  - "fetchMergePreview fetches /admin/people/${data.person.id}/merge-preview (same-origin relative URL) — the +server.ts proxy injects ADMIN_TOKEN server-side so no token leaks to client (T-12-TOKENLEAK confirmed)"
  - "Delete button uses Svelte {#if data.can_delete} branching rather than disabled attribute + opacity; each branch renders its own button with appropriate styles — avoids dynamic style strings for the disabled state"
  - "Merge confirm button conditioned on mergeTargetId && mergePreview — only appears after counts are loaded, preventing submission before the preview is visible"
  - "Count display preserves exact integers from the API — no rounding, no paraphrase (audit-relevant per T-12-COUNTFIDELITY)"

metrics:
  duration_minutes: 30
  completed_date: "2026-06-23"
  tasks_completed: 1
  files_changed: 1
---

# Phase 12 Plan 04: People Edit Page UI Restructure Summary

**One-liner:** Replaced standalone photo_url input with a photo preview + Upload/URL tab widget (separate multipart form), and appended Merge (eager count preview) and Delete (eligibility-gated) sections below the save form in +page.svelte.

## What Was Built

One file restructured — no new packages, no new routes.

### app/src/routes/admin/people/[id]/+page.svelte

**Script block additions (Svelte 5 Runes):**
- `photoTab = $state<'upload' | 'url'>('upload')` — drives tab toggle
- `photoSubmitting = $state(false)` — drives photo submit button state
- `mergeTargetId = $state<string>('')` — bound to merge picker select
- `mergePreview = $state<{...} | null>(null)` — populated by fetchMergePreview
- `mergeLoading = $state(false)`, `mergeError = $state<string | null>(null)` — fetch state
- `mergeSubmitting = $state(false)`, `deleteSubmitting = $state(false)` — submit states
- `fetchMergePreview(targetId)` — async function fetching `/admin/people/${id}/merge-preview?target_id=${targetId}`; sets mergePreview on ok, mergeError on failure, mergeLoading during fetch

**Bio & Photo section restructure:**
- The main save form's Bio & Photo card now contains only the bio textarea (bio is still saved via `?/save`)
- A second adjacent card (outside the save form) contains the photo widget in its own `<form action="?/photo" enctype="multipart/form-data" use:enhance>`
- Photo preview: 80×80 circle — `<img>` with `object-fit: cover` if `data.person.photo_url_full` is set; else styled initials div (`aria-hidden="true"`)
- Tab bar: two `type="button"` buttons toggling `photoTab`; active tab has `border-bottom: 2px solid #93c5fd; color: #e2e8f0`, inactive has `border-bottom: 2px solid transparent; color: #94a3b8`
- Upload panel: `<input type="file" name="photo_file" accept="image/*">` (min-height 44px)
- URL panel: `<input type="text" name="photo_url" placeholder="https://…">` (matches existing input style)
- `{#if form?.photoError}` alert paragraph below tabs
- "Save photo" / "Saving photo…" submit button (accent border `#93c5fd`)

**Merge section (new card after photo widget):**
- Card tokens: bg `#1e293b`, border `#334155`, radius 8px, padding 24px
- Heading "Merge into another person" (20px, 600, `#e2e8f0`)
- `<form action="?/merge" use:enhance>` with `<select>` bound to `mergeTargetId` + `onchange={() => fetchMergePreview(mergeTargetId)}`
- Options: blank placeholder "— Select a person —" then `data.people` items (server already excludes current person), sorted as provided by load; option label `{last_name}, {first_name}` or `full_name` fallback
- Hidden `<input name="target_id">` carries value to action
- Preview panel (shown when `mergeTargetId` truthy): bg `#0f1117`, border `#334155`; shows "Loading…", error, or count summary
- Count line format: `N utterance(s) · N alias(es) · N appearance(s) · N argument participant(s)` — exact integers
- Zero-count variant: "No records to transfer. This person has no associated data."
- Confirm button (shown when `mergeTargetId && mergePreview`): label "Merge [source] into [target]" / "Merging…"; accent border `#93c5fd`
- `{#if form?.mergeError}` alert paragraph

**Delete section (new card at bottom):**
- Card tokens identical to merge card; no heading
- `<form action="?/delete" use:enhance>`
- When `data.can_delete`: enabled button with `border: 1px solid #ef4444; color: #ef4444; cursor: pointer`; label "Delete person" / "Deleting…"
- When `!data.can_delete`: `disabled` button with `border: 1px solid #334155; color: #94a3b8; cursor: not-allowed; opacity: 0.7`; plus `<p id="delete-tip">Cannot delete — this person has associated records and cannot be removed.</p>` with `aria-describedby="delete-tip"` on the button
- `{#if form?.deleteError}` alert paragraph

**Save form unchanged:**
- Opening tag: `<form method="POST" action="?/save" use:enhance>` — no `enctype` attribute
- No `name="photo_url"` input in the save form body

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restructured photo widget placement to avoid nested form**
- **Found during:** Task 1 (svelte-check: "`<form>` cannot be a descendant of `<form>`")
- **Issue:** Placing the photo `<form>` inside the Bio & Photo card which was itself inside the save `<form>` created a nested form — HTML-invalid and flagged as a Svelte error.
- **Fix:** Split the Bio & Photo section into two adjacent cards. The top half (bio textarea) stays inside the save form. The bottom half (photo widget) is a standalone `<form>` sibling outside the save form with visual CSS continuity (rounded corners adjusted to join the two parts).
- **Files modified:** `app/src/routes/admin/people/[id]/+page.svelte`
- **Commit:** b89f6e3

## Known Stubs

None. All data flows from live server load:
- `data.person.photo_url_full` — populated in load from FastAPI (Plan 03)
- `data.people` — populated in load as merge picker list (Plan 03)
- `data.can_delete` — derived in load from merge-preview counts (Plan 03)
- `mergePreview` — fetched client-side via same-origin proxy on picker change (Plan 03)

## Threat Flags

No new threat surface beyond Plan 04's threat model. All five threat entries mitigated:
- T-12-CLIENTGATE: `data.can_delete` client gate is defense-in-depth; server enforces orphan check (Plan 02)
- T-12-SELFPICK: picker bound to `data.people` (load already excludes current person); server rejects self-merge with 422 (Plan 01/02)
- T-12-XSS-PHOTO: `photo_url_full` rendered in `<img src>` only — Svelte auto-escapes attribute values; not executable
- T-12-TOKENLEAK: client fetches same-origin `/admin/people/[id]/merge-preview` proxy; ADMIN_TOKEN never in client code (Plan 03)
- T-12-COUNTFIDELITY: counts rendered as exact integers from API — no rounding or paraphrase

## Self-Check

- [x] `app/src/routes/admin/people/[id]/+page.svelte` — FOUND
- [x] Commit `b89f6e3` — FOUND (feat(12-04): restructure Bio & Photo + add Merge and Delete sections)
- [x] `name="photo_url"` count = 1 — VERIFIED (grep returns 1)
- [x] All three actions `?/photo`, `?/merge`, `?/delete` referenced — VERIFIED
- [x] Save form has no `enctype` attribute — VERIFIED
- [x] `svelte-check --threshold error` returns 0 errors — VERIFIED

## Self-Check: PASSED

All artifacts confirmed present and verified.

Commits:
- b89f6e3: feat(12-04): restructure Bio & Photo + add Merge and Delete sections

## Human Verify Pending

Task 2 (checkpoint:human-verify) is pending operator approval. See checkpoint details in the executor's return message.
