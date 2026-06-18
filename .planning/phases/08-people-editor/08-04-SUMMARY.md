---
phase: 08-people-editor
plan: "04"
subsystem: frontend
tags: [sveltekit, svelte5, people-editor, admin, edit-form, tenure, role-select]
status: complete

dependency_graph:
  requires: [08-02, 08-03]
  provides: [person-edit-form, role-inline-create, tenure-row-management]
  affects: [08-05]

tech_stack:
  added: []
  patterns:
    - SvelteKit named actions (save + createRole) with use:enhance for both the main form and the inline role form
    - Svelte 5 $state<TenureRow[]> in-place mutation (push/splice) for dynamic tenure rows
    - Stable _key counter per tenure row in keyed {#each (row._key)} block (Pitfall 2 avoided)
    - Hidden name="tenures" JSON field strategy (Pattern 1 / Pitfall 3) to carry the full tenure array through form POST
    - use:enhance createRole callback that appends new role to localRoles $state and auto-selects it without page reload (Pattern 3 / Pitfall 4)
    - Sentinel string value in <select> to detect "add new role" selection without a separate boolean flag

key_files:
  created:
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte
  modified: []

decisions:
  - localRoles seeded from data.roles in $state so new roles appended by createRole use:enhance callback persist across renders without triggering a load re-run
  - selectedRoleId held in $state as string to allow binding to the <select> value; ADD_NEW_ROLE_SENTINEL constant keeps the sentinel isolated from real role ids
  - Bio & Photo section heading uses &amp; entity in Svelte template to avoid linter warning on bare ampersand in template text
  - Tenure row trash button uses onclick (Svelte 5 event attribute) not on:click (Svelte 4 event directive) — consistent with Svelte 5 Runes conventions
  - opacity set as an inline expression style="opacity: {saveSubmitting ? 0.7 : 1}" rather than a separate disabled visual class — matches UI-SPEC SaveChangesButton contract exactly

metrics:
  duration_minutes: 10
  completed_date: "2026-06-17"
  tasks_completed: 2
  files_changed: 2
---

# Phase 08 Plan 04: Person Edit Form Summary

**One-liner:** PersonEditForm at `/admin/people/[id]` — three section cards (Basic Info, Bio & Photo, Court Tenure), RoleSelect with inline AddRoleInlineForm posting to `?/createRole` via `use:enhance`, dynamic TenureRowList managed with `$state<TenureRow[]>` push/splice, hidden JSON tenure field, and a full-width SaveChangesButton that disables during submit.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Edit-form load + save + createRole actions | bfc2c5f | app/src/routes/admin/people/[id]/+page.server.ts |
| 2 | PersonEditForm with three sections, role select + inline create, dynamic tenure rows | 9779b9e | app/src/routes/admin/people/[id]/+page.svelte |

## What Was Built

### Server Module (`app/src/routes/admin/people/[id]/+page.server.ts`)

Built in the previous session (commit `bfc2c5f`):

- `load`: fetches `GET /api/admin/people/{id}` with X-Admin-Token; throws `error(404)` on not-found, `error(502)` on other non-OK; also fetches `GET /api/admin/people` to derive a de-duplicated roles list (`[{id, name}]`) sorted alphabetically; returns `{ person, roles }`
- `actions.save`: reads all form fields; converts empty `role_id` to null (Open Question 2); parses `tenures` hidden JSON field with try/catch (`fail(422)` on parse error); validates non-empty `full_name` (`fail(400)`); strips `_key` from each tenure before sending; PATCHes FastAPI with `Content-Type: application/json`; on success `throw redirect(303, '/admin/people/' + params.id)`
- `actions.createRole`: reads `role_name`; validates non-empty; POSTs to `/api/admin/roles`; returns `{ roleCreated: true, role }` on success so the `use:enhance` callback can update the dropdown; returns `fail(400, { roleError })` on error (kept separate from save errors — Pitfall 4)
- No `$env/static/public` / `PUBLIC_` imports; no client-side FastAPI calls

### Edit Form Component (`app/src/routes/admin/people/[id]/+page.svelte`)

**Page layout:**
- `<main>` with `background-color: #0f1117; min-height: 100vh;`
- `<header>` with breadcrumb `<a href="/admin/people">← People</a>` (`#94a3b8`, 14px) and `<h1>` = `{data.person.full_name}` (20px/600)
- Content container: `max-width: 640px; margin: 0 auto; padding: 48px 24px;`

**Section 1 — Basic Info:**
- Full name: `<label>` "Full name" + `<input name="full_name">` pre-filled with `data.person.full_name`
- Role: `<label>` "Role" + `<select name="role_id">` populated from `localRoles` (seeded from `data.roles` in `$state`) plus sentinel option "＋ Add new role"
- `handleRoleChange`: if sentinel selected → `showAddRoleForm = true`; otherwise set `selectedRoleId`
- `aria-expanded={showAddRoleForm}` on the select
- AddRoleInlineForm (shown when `showAddRoleForm`): inner `<form action="?/createRole" use:enhance>`; "Role name" label + input; "Create role" button; on success callback: `localRoles.push(data.role)`, `selectedRoleId = String(data.role.id)`, `showAddRoleForm = false`; on failure: sets `roleError`; inline `role="alert"` error paragraph

**Section 2 — Bio & Photo:**
- Bio: `<textarea name="bio_text">` (min-height 120px, resize vertical, font-family inherit) pre-filled with `data.person.bio_text ?? ''`
- Photo URL: `<input name="photo_url">` pre-filled with `data.person.photo_url ?? ''`, placeholder "https://…"

**Section 3 — Court Tenure (D-07/D-08/D-09):**
- `let tenureRows = $state<TenureRow[]>()` initialised from `data.person.tenures` mapped with stable incrementing `_key`
- `{#each tenureRows as row, i (row._key)}` — keyed by `_key` (Pitfall 2)
- Per row: Seat (`<input type="text" bind:value={row.seat}>`, 40% flex), Start date (`<input type="date" bind:value={row.start_date}>`, 25% flex), End date (`<input type="date" bind:value={row.end_date}>`, 25% flex), trash button (`aria-label="Remove tenure row"`, `#ef4444`, `onclick={() => removeTenureRow(i)}`)
- "Add tenure" full-width button (44px min-height) calls `addTenureRow()` which pushes `{ _key: nextKey++, seat: '', start_date: '', end_date: '' }`
- `removeTenureRow(i)` calls `tenureRows.splice(i, 1)` — in-place mutation
- `<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)} />` carries the array to the save action

**Form-level error and SaveChangesButton:**
- `{#if form?.error}` → `<p role="alert">` paragraph in `#ef4444`
- SaveChangesButton: `display: block; width: 100%; min-height: 44px; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0;`
- While submitting: text → "Saving…", `disabled`, `opacity: 0.7`
- `use:enhance` sets `saveSubmitting = true` on start, resets on result

## Verification Results

- `svelte-check --threshold error` → 0 errors, 10 warnings (pre-existing) ✓
- `grep -c 'action="?/save"' +page.svelte` → 1 ✓
- `grep -c 'name="tenures"' +page.svelte` → 1 ✓
- `grep -c 'aria-label="Remove tenure row"' +page.svelte` → 1 ✓
- `grep -c '@html' +page.svelte` → 0 ✓ (T-08-XSS mitigated)
- No `$env/static/public` or `PUBLIC_` in +page.server.ts ✓
- Three section headings present: "Basic Info", "Bio & Photo", "Court Tenure" ✓

## Deviations from Plan

None — plan executed exactly as written. The component implementation follows all UI-SPEC contracts, Runes patterns, and RESEARCH patterns without deviation.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what was planned.

| Threat | Status |
|--------|--------|
| T-08-XSS | Mitigated — no `{@html}` in +page.svelte; all person data via text interpolation or value bindings |
| T-08-LEAK | Mitigated — ADMIN_TOKEN/FASTAPI_BASE_URL server-only in +page.server.ts; no PUBLIC_ imports |
| T-08-IDOR | Mitigated — load throws 404 from FastAPI response; PATCH 404 handled server-side (Plan 02 enforces) |
| T-08-CSRF | Accepted — SvelteKit CSRF Origin check + hooks.server.ts auth guard cover admin form POSTs |
| T-08-SC | N/A — zero new npm packages (RESEARCH.md confirmed no new packages needed) |

## Known Stubs

None — form is fully wired to the Plan 01 server actions. Save POSTs to `?/save` which PATCHes FastAPI. CreateRole POSTs to `?/createRole` which POSTs to `/api/admin/roles`. Tenure rows are fully dynamic and serialized into the hidden field on each render.

## Self-Check: PASSED

- `app/src/routes/admin/people/[id]/+page.server.ts` — FOUND ✓
- `app/src/routes/admin/people/[id]/+page.svelte` — FOUND ✓
- Commit bfc2c5f (task 1 — prior session) — FOUND ✓
- Commit 9779b9e (task 2) — FOUND ✓
- svelte-check 0 errors — CONFIRMED ✓
- name="tenures" hidden field — CONFIRMED ✓
- aria-label="Remove tenure row" — CONFIRMED ✓
- No {@html} — CONFIRMED ✓
