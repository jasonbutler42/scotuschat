---
phase: 08-people-editor
plan: "03"
subsystem: frontend
tags: [sveltekit, svelte5, people-editor, admin, table, toggle, navigation]
status: complete

dependency_graph:
  requires: [08-02]
  provides: [people-directory-page, incomplete-toggle, people-nav-link]
  affects: [08-04, 08-05]

tech_stack:
  added: []
  patterns:
    - SvelteKit PageServerLoad with private env imports (server-only FastAPI fetch)
    - Svelte 5 $derived for server-sync state (toggle pre-check from data.incomplete)
    - goto() from $app/navigation for URL-param toggle navigation (D-05)
    - CSS-only toggle switch via button role=switch with aria-checked

key_files:
  created:
    - app/src/routes/admin/people/+page.server.ts
    - app/src/routes/admin/people/+page.svelte
  modified:
    - app/src/routes/admin/+layout.svelte

decisions:
  - checked = $derived(data.incomplete ?? false) — derived instead of $state(data.incomplete) to stay in sync when load re-runs after goto() navigation
  - Toggle implemented as <button role="switch"> with aria-label (not a hidden input + label) — simpler Svelte 5 pattern with same semantics
  - goto() flips the URL which triggers load re-run; no manual state mutation needed
  - aria-label on toggle button handles svelte-check a11y warning for icon-only button

metrics:
  duration_minutes: 4
  completed_date: "2026-06-17"
  tasks_completed: 3
  files_changed: 3
---

# Phase 08 Plan 03: People Directory Page Summary

**One-liner:** `/admin/people` route with server-rendered PeopleTable (Name|Role|Missing fields|Edit columns), IncompleteToggle (`role="switch"`, `goto()` navigation, pre-checked from `?incomplete=1`), amber MissingFieldChip group, dual empty states per UI-SPEC, and People Editor nav link activated in `+layout.svelte`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | People directory load function | af05bb2 | app/src/routes/admin/people/+page.server.ts |
| 2 | People directory table + toggle + empty states | ab7bf4c | app/src/routes/admin/people/+page.svelte |
| 3 | Activate the People Editor nav link | 52f46e7 | app/src/routes/admin/+layout.svelte |

## What Was Built

### Load Function (`app/src/routes/admin/people/+page.server.ts`)

- Imports `ADMIN_TOKEN`, `FASTAPI_BASE_URL` from `$env/static/private` — server-only, never exposed to browser bundle (T-08-LEAK mitigated)
- Reads `incomplete` from `url.searchParams.get('incomplete') === '1'`
- Builds API URL: `${FASTAPI_BASE_URL}/api/admin/people${incomplete ? '?incomplete=1' : ''}`
- Fetches with `{ 'X-Admin-Token': ADMIN_TOKEN }` header
- Degrades to `[]` on non-OK (try/catch + `if (res.ok)` guard) — page renders even when FastAPI is down
- Returns `{ people, incomplete }`
- `PersonListItem` type declared inline: `{ id, full_name, role_id, role_name, missing: string[] }`

### Directory Page (`app/src/routes/admin/people/+page.svelte`)

**IncompleteToggle (D-05):**
- `<button role="switch" aria-checked={checked} aria-label="Show incomplete only">`
- `checked = $derived(data.incomplete ?? false)` — mirrors server state after load re-runs
- `handleToggle()`: if checked → `goto('/admin/people')`, else → `goto('/admin/people?incomplete=1')`
- CSS track: 44×24px, `#0f1117` off / `rgba(147,197,253,0.2)` on, border `#334155` off / `#93c5fd` on
- CSS thumb: 18×18px circle, `translateX(2px)` off / `translateX(22px)` on, `#94a3b8` off / `#93c5fd` on

**PeopleTable (D-06):**
- `<table>` with `<thead><tr>` and four `<th scope="col">` headers: Name / Role / Missing fields / (empty)
- Column widths: 40% / 25% / 20% / 15%
- Name: 16px `#e2e8f0`; Role: `role_name` or `—` in `#94a3b8`; Edit: right-aligned "Edit person" link in `#93c5fd`
- Missing fields: chip group `<span aria-label="Missing: bio, photo">` wrapping MissingFieldChip `<span>` elements
- MissingFieldChip: `rgba(245,158,11,0.15)` bg, `1px solid #f59e0b` border, `#f59e0b` text, `border-radius: 4px; padding: 4px 8px; font-size: 14px`
- XSS defense: all person data via `{...}` text interpolation — no `{@html}` anywhere (T-08-XSS mitigated)

**Empty States:**
- Filtered-empty (`data.incomplete === true`, `people.length === 0`): heading "No incomplete records", body "All people have complete metadata. Turn off the filter to see everyone."
- No-people (`data.incomplete === false`, `people.length === 0`): heading "No people yet", body "People are added during pipeline resolve. Run a pipeline to populate this directory."

**Layout:** `<main>` with dark `#0f1117` bg; `<header>` with `#1e293b` bg; content `max-width: 860px; margin: 0 auto; padding: 48px 24px;`

### Admin Layout (`app/src/routes/admin/+layout.svelte`)

- Replaced `<span aria-disabled="true" aria-label="People Editor (coming soon)" style="... opacity: 0.5; cursor: default;">People Editor</span>`
- With `<a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">People Editor</a>`
- Styling identical to the Pipeline Runner `<a>` link — no visual change for sighted users; semantics change from disabled to active
- Logout form and Pipeline Runner link unchanged

## Verification Results

- `svelte-check --threshold error` → 0 errors ✓
- No issues in `routes/admin/people/*` per svelte-check ✓
- `grep -c 'href="/admin/people"' +layout.svelte` → 1 ✓
- No `$env/static/public` or `PUBLIC_` import in +page.server.ts ✓
- No `{@html}` in +page.svelte ✓

## Deviations from Plan

### [Rule 2 - Missing critical functionality] $derived instead of $state for toggle checked

**Found during:** Task 2
**Issue:** Plan specified `let checked = $state(data.incomplete ?? false)`. After `goto()` navigation, the SvelteKit load function re-runs and updates `data`, but `$state` only captures the initial value — checked would become stale. `svelte-check` surfaced this as a warning: "This reference only captures the initial value of `data`."
**Fix:** Changed to `let checked = $derived(data.incomplete ?? false)` — this re-derives from `data.incomplete` each time the load re-runs, keeping the toggle in sync with URL state.
**Files modified:** `app/src/routes/admin/people/+page.svelte`
**Commit:** ab7bf4c

### [Rule 2 - Missing critical functionality] aria-label on toggle button

**Found during:** Task 2
**Issue:** `svelte-check` surfaced a11y warning: "Buttons and links should either contain text or have an `aria-label`". The toggle button contains only a CSS thumb `<span>` — not readable text for screen readers.
**Fix:** Added `aria-label="Show incomplete only"` to the toggle button. The visible label text beside the toggle still reads "Show incomplete only" for sighted users.
**Files modified:** `app/src/routes/admin/people/+page.svelte`
**Commit:** ab7bf4c

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what was planned.

| Threat | Status |
|--------|--------|
| T-08-XSS | Mitigated — no `{@html}` in +page.svelte; all person data via `{...}` interpolation |
| T-08-LEAK | Mitigated — ADMIN_TOKEN/FASTAPI_BASE_URL server-only; no PUBLIC_ imports |
| T-08-AC | Accepted — hooks.server.ts route guard (Phase 6) covers /admin/people automatically |
| T-08-SC | N/A — zero new npm packages |

## Known Stubs

None — the page fetches real data from the Plan 02 FastAPI endpoint. Empty states render correctly when data is absent.

## Self-Check: PASSED

- `app/src/routes/admin/people/+page.server.ts` — FOUND ✓
- `app/src/routes/admin/people/+page.svelte` — FOUND ✓
- `app/src/routes/admin/+layout.svelte` contains `href="/admin/people"` — FOUND ✓
- Commit af05bb2 (task 1) — FOUND ✓
- Commit ab7bf4c (task 2) — FOUND ✓
- Commit 52f46e7 (task 3) — FOUND ✓
- svelte-check 0 errors — CONFIRMED ✓
- No PUBLIC_ or {@html} — CONFIRMED ✓
