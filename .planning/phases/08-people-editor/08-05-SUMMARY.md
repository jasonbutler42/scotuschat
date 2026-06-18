---
phase: 08-people-editor
plan: "05"
subsystem: frontend
tags: [sveltekit, svelte5, admin, people-editor, pipeline, participants]
status: complete

dependency_graph:
  requires: [08-02]
  provides: [job-detail-participant-list]
  affects: []

tech_stack:
  added: []
  patterns:
    - SvelteKit load parallel fetch with graceful degrade (mirror of existing people-fetch pattern)
    - Svelte 5 {#if} guard on status + array length for conditional section render
    - {#each} with index for conditional last-item border-bottom removal

key_files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

decisions:
  - participants fetched only when status=completed AND argument_id non-null; otherwise [] (no fetch)
  - graceful degrade on fetch error — participants defaults to [] so existing page never breaks
  - role span omitted entirely when role_name is null (preferred over showing em dash placeholder)
  - last list item border removed via {#each} index comparison (i < length - 1) per UI-SPEC

metrics:
  duration_minutes: 4
  completed_date: "2026-06-17"
  tasks_completed: 2
  files_changed: 2
---

# Phase 08 Plan 05: ParticipantList on Job Detail Page Summary

**One-liner:** Extended job-detail load to fetch resolved participants from `GET /api/admin/jobs/{id}/participants` when completed, and appended a UI-SPEC-compliant ParticipantList section with pluralized heading, role-annotated `<ul>/<li>` list, and "Review people →" link to `/admin/people?incomplete=1`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend job-detail load to fetch participants when completed | 00d8c6c | app/src/routes/admin/pipeline/[job_id]/+page.server.ts |
| 2 | Append ParticipantList section to the job detail page | 051520c | app/src/routes/admin/pipeline/[job_id]/+page.svelte |

## What Was Built

### Load function extension (`+page.server.ts`)

- Added `ParticipantItem` interface: `{ person_id: number; full_name: string; role_name: string | null }`
- Conditional fetch: only when `job.status === 'completed'` and `job.argument_id != null`
- Calls `GET ${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/participants` with `X-Admin-Token` header
- On non-OK response: logs error, defaults `participants = []` — non-critical, page still renders
- On thrown error: same graceful degrade to `[]` with console.error
- Returns `participants` alongside existing `job`, `people`, `peopleLoadError` — all existing fields preserved

### ParticipantList section (`+page.svelte`)

- Guard: `{#if data.job.status === 'completed' && data.participants.length > 0}` — section absent for non-completed jobs and zero-participant completed jobs
- Container: `margin-top: 32px; background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;` — UI-SPEC exact values
- Heading `<h2>`: pluralized `{N} resolved participant` / `{N} resolved participants` per Copywriting Contract
- List: `<ul>` with `list-style: none` — not a `<table>` per Accessibility Contract
- Each `<li>`: 16px / `#e2e8f0`; `padding: 8px 0`; `border-bottom: 1px solid #334155` on all but last item
- Role annotation: `<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">({p.role_name})</span>` — span omitted when `role_name` is null
- "Review people →" link: `<a href="/admin/people?incomplete=1">` styled as button per UI-SPEC (D-03)
- All interpolation via `{...}` — no `{@html}` (T-08-XSS mitigated)
- Existing step cards, polling logic, discrepancy review, and failed-state panel are unchanged

## Verification Results

- `svelte-check --threshold error` → 0 errors (307 files checked) ✓
- `grep -c '/admin/people?incomplete=1' +page.svelte` → 1 ✓
- No `{@html}` in +page.svelte ✓
- Existing Phase 7 page behavior preserved (additive change only) ✓
- `$env/static/private` used for FASTAPI_BASE_URL and ADMIN_TOKEN — no PUBLIC_ env vars ✓

## Deviations from Plan

### [Rule 1 - Bug] Stale generated proxy caused svelte-check type errors

**Found during:** Task 2
**Issue:** After editing `+page.server.ts` to add `participants` to the return type, `svelte-check` reported 5 type errors on `+page.svelte` because the SvelteKit-generated proxy file (`proxy+page.server.ts`) still reflected the old return shape `{ job, people, peopleLoadError }` without `participants`. This is expected SvelteKit behavior — the proxy is regenerated on `svelte-kit sync`.
**Fix:** Ran `npx svelte-kit sync` to regenerate the proxy file, then re-ran `svelte-check` which reported 0 errors.
**Impact:** No code logic changed — the sync is part of the normal SvelteKit development workflow.

## Threat Surface Scan

All plan threat register mitigations implemented:

| Threat ID | Status |
|-----------|--------|
| T-08-XSS | Mitigated — participant names and roles rendered via `{p.full_name}` / `{p.role_name}` text interpolation; no `{@html}` |
| T-08-LEAK | Mitigated — ADMIN_TOKEN and FASTAPI_BASE_URL from `$env/static/private`; fetch in load (server-side only) |
| T-08-REG | Mitigated — additive change only; existing step cards/polling/resolve/failed-panel untouched; svelte-check confirms 0 type errors |
| T-08-SC | N/A — no new npm packages installed |

No new threat surface introduced beyond the plan's register.

## Known Stubs

None — participants are fetched from the live `GET /api/admin/jobs/{id}/participants` endpoint implemented in Plan 08-02. No hardcoded empty values or placeholder text.

## Self-Check: PASSED

- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — FOUND ✓ (participants fetch added)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — FOUND ✓ (ParticipantList section added)
- Commit 00d8c6c (feat load extension) — FOUND ✓
- Commit 051520c (feat ParticipantList) — FOUND ✓
- svelte-check 0 errors ✓
- /admin/people?incomplete=1 link present ✓
- No @html ✓
