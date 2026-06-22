---
phase: 11-argument-metadata-editing
plan: "03"
subsystem: sveltekit-admin-ui
tags: [sveltekit, svelte5, admin, arguments, publish, use-enhance]
dependency_graph:
  requires: ["11-02"]
  provides: ["11-04"]
  affects:
    - app/src/routes/admin/arguments/+page.server.ts
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/lib/components/TopNav.svelte
tech_stack:
  added: []
  patterns:
    - "SvelteKit named form actions + use:enhance (per-row hidden argument_id — Pitfall 6)"
    - "Svelte 5 runes — $props(), $state(), $derived() for submitting flags"
    - "FASTAPI_BASE_URL + ADMIN_TOKEN from $env/static/private only (T-11-ENV)"
    - "redirect(303) on action success to re-run load with fresh data"
    - "fail(422) with UI-SPEC error copy on slug_collision / docket_collision"
    - "Status badge helper functions (badgeStyle/badgeLabel) mirroring pipeline/+page.svelte"
    - "toDateInputValue() helper converts ISO timestamp to YYYY-MM-DD for <input type=date>"
key_files:
  created:
    - app/src/routes/admin/arguments/+page.server.ts
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte
  modified:
    - app/src/lib/components/TopNav.svelte
decisions:
  - "[11-03]: Arguments list load degrades to [] on non-OK (console.error, no throw) — matches people list pattern"
  - "[11-03]: List publish/unpublish actions redirect(303) unconditionally — best-effort; backend enforces guards"
  - "[11-03]: Edit page save parses response body JSON to extract detail string for slug_collision / docket_collision discrimination"
  - "[11-03]: toDateInputValue() helper slices first 10 chars of ISO string for date input compatibility"
  - "[11-03]: Consolidated dockets rendered only when consolidated_dockets.length > 0 (D-10)"
metrics:
  duration: 10
  completed_date: "2026-06-22"
  tasks: 3
  files: 5
status: complete
---

# Phase 11 Plan 03: Argument Metadata Editing Admin UI Summary

**One-liner:** SvelteKit admin UI for argument metadata editing — list page with status badges and per-row publish toggles, edit page with two-card form and slug-collision error display, and TopNav Arguments link.

## What Was Built

### Task 1: Arguments list page (d48c964)

Two new files: `app/src/routes/admin/arguments/+page.server.ts` and `+page.svelte`.

**Server (`+page.server.ts`):**
- `load`: GET `/api/admin/arguments` with `X-Admin-Token`; degrades to `[]` on non-OK (console.error, no throw)
- `publish` action: reads `argument_id` from formData, POSTs to `/api/admin/arguments/{id}/publish`, redirects 303
- `unpublish` action: same pattern for `/unpublish`
- Both env vars imported from `$env/static/private` (T-11-ENV)

**Page (`+page.svelte`):**
- Svelte 5 runes; `let { data } = $props()`
- `<table>` with `<th scope="col">` for Status, Case Title, Docket, Argued, Publish (WCAG 1.3.1)
- Status badge logic: published_at → Published (#4ade80 green); resolved_at only → Resolved (#a78bfa violet); else → Pending (#94a3b8)
- Per-row forms with hidden `argument_id` input and `use:enhance` (Pitfall 6)
- Publish button (accent border #93c5fd) when resolved+unpublished; Unpublish (muted #334155) when published; no control when pending
- Edit `<a>` link per row (#93c5fd)
- Empty state with UI-SPEC copy: "No arguments yet" / "No arguments have been ingested…"
- `formatDate` helper: `toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })`

### Task 2: Argument edit page (b938ad6)

Two new files: `app/src/routes/admin/arguments/[id]/+page.server.ts` and `+page.svelte`.

**Server (`+page.server.ts`):**
- `load`: GET with 404 → `error(404)`, non-OK → `error(502)`
- `save`: PATCH `{case_name, docket_number, argued_date}`; parses 422 response body for `slug_collision` → UI-SPEC copy; `docket_collision` → docket-specific message; redirect(303) on success
- `publish`: POST to `/publish`; fail(422) on non-OK; redirect(303)
- `unpublish`: POST to `/unpublish`; fail(422) on non-OK; redirect(303)

**Page (`+page.svelte`):**
- Svelte 5 runes; `let { data, form } = $props()`
- Header: back link "← Arguments" (#94a3b8) + h1 = `data.argument.case_name`
- Container max-width 640px
- Card 1 "Argument Details": `<form action="?/save" use:enhance>` with three labeled inputs — case title (type=text), docket number (type=text — NOT date), argued date (type=date)
- Consolidated dockets: read-only `<ul>` below fields, only when `consolidated_dockets.length > 0` (D-10)
- `form?.error` in `role="alert"` slot
- "Save changes" button: full-width, accent border #93c5fd, min-height 44px, shows "Saving…" + disabled when submitting
- Card 2 "Status": current badge + "Resolved MMM D, YYYY" / "Published MMM D, YYYY" + slug preview
- Publish form: only when `resolved_at && !published_at`; shows "Publishing…" submitting state
- Unpublish form: only when `published_at`; shows "Unpublishing…" submitting state; muted border #334155

### Task 3: TopNav Arguments link (1b4b728)

Modified `app/src/lib/components/TopNav.svelte` admin variant: added `<a href="/admin/arguments">Arguments</a>` between "Pipeline Runner" and "People Editor" anchors. Inline style matches sibling links exactly (`font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;`). Public variant unchanged. Nav order: SCOTUS CHAT | Pipeline Runner | Arguments | People Editor | [spacer] Log out (D-12).

## Threat Mitigations Implemented

| Threat | Mitigation | Where |
|--------|-----------|-------|
| T-11-ENV | FASTAPI_BASE_URL / ADMIN_TOKEN from `$env/static/private` only — never PUBLIC_ | All +page.server.ts files |
| T-11-PUBUI | UI only renders Publish when state allows (defense-in-depth; backend is authoritative) | [id]/+page.svelte + list +page.svelte |
| T-11-XSS | No `{@html}` used for argument fields; Svelte escapes all interpolated text | Both +page.svelte files |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components render live API data. No hardcoded empty values or placeholder text.

## Threat Flags

None — all new surface is admin-gated and follows the T-11-* threat register in the plan.

## Self-Check: PASSED
