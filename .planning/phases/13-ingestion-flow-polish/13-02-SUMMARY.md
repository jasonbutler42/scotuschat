---
phase: 13-ingestion-flow-polish
plan: "02"
subsystem: frontend
tags: [pipeline, jobs, filter, incomplete, toggle, pipe-20, svelte5]
dependency_graph:
  requires: [13-01]
  provides: [pipeline-list-incomplete-toggle, pipeline-list-incomplete-empty-state]
  affects:
    - app/src/routes/admin/pipeline/+page.server.ts
    - app/src/routes/admin/pipeline/+page.svelte
tech_stack:
  added: []
  patterns: [SvelteKit url.searchParams, goto navigation, role=switch toggle, $derived reactive state]
key_files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/+page.server.ts
    - app/src/routes/admin/pipeline/+page.svelte
decisions:
  - "incomplete = url.searchParams.get('incomplete') === '1' strict comparison — T-13-03 (any other value → off)"
  - "apiUrl built conditionally: ?incomplete=true appended to FastAPI fetch only when param active"
  - "incomplete returned on all three load paths (success, non-OK, catch) — no missing-field edge case"
  - "incomplete = $derived(data.incomplete ?? false) — reactive to server reload on navigation"
  - "Section header flex row: h2 left, toggle group right — mirrors /admin/people layout"
  - "Toggle pill: 44×24px, border-radius 12px, knob translateX(2px/22px) — exact /admin/people pattern"
  - "filter-on empty state branches on incomplete && jobs.length===0 before non-filter empty state"
metrics:
  duration: ~15 min
  completed: "2026-06-24"
  tasks: 2
  files: 2
status: complete
requirements: [PIPE-20]
---

# Phase 13 Plan 02: Pipeline List Incomplete Toggle Summary

**One-liner:** Pipeline list load forwards `?incomplete=1` to FastAPI as `?incomplete=true`; a `role="switch"` toggle pill above Recent Runs navigates between full list and filtered (paused+failed) view with a distinct empty state.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Forward incomplete param in pipeline list load | 1ccc408 | +page.server.ts |
| 2 | Incomplete toggle switch + filter-on empty state | a5be595 | +page.svelte |

## What Was Built

### Task 1: Forward incomplete param in pipeline list load (`+page.server.ts`)

- `load` signature changed from `async ()` to `async ({ url })` to access URL params
- `const incomplete = url.searchParams.get('incomplete') === '1'` — strict comparison per T-13-03; any value other than `'1'` treats the filter as off
- `apiUrl` built conditionally: `${FASTAPI_BASE_URL}/api/admin/jobs${incomplete ? '?incomplete=true' : ''}` — no injection risk (param re-emitted as literal string)
- `incomplete` returned on all three paths: success (`{ jobs, incomplete }`), non-OK (`{ jobs: [], incomplete }`), catch (`{ jobs: [], incomplete }`)
- X-Admin-Token header unchanged

### Task 2: Incomplete toggle switch + filter-on empty state (`+page.svelte`)

- `import { goto } from '$app/navigation'` added to script block
- `let incomplete = $derived(data.incomplete ?? false)` — reactive to server reload after navigation
- `handleToggle()` navigates to `/admin/pipeline?incomplete=1` when off, `/admin/pipeline` when on (D-13)
- `<h2>Recent Runs</h2>` replaced with flex row header (`justify-content: space-between`) — h2 left, toggle group right
- Toggle button: `role="switch"`, `aria-checked={incomplete}`, `aria-label="Show incomplete only"`, `min-height: 44px` (WCAG 2.5.5)
- Toggle pill: 44px wide × 24px tall, `border-radius: 12px`, off state `#334155` border / `#0f1117` bg, on state `#93c5fd` border / `rgba(147,197,253,0.2)` bg
- Knob: 18px circle, off `#94a3b8` at `translateX(2px)`, on `#93c5fd` at `translateX(22px)`
- Label `<span>`: 14px, off color `#94a3b8`, on color `#e2e8f0`
- Filter-on empty state (when `incomplete && jobs.length === 0`): heading "No jobs need attention", body "All recent runs completed or are running. Toggle off to see the full history."
- Non-filter empty state ("No runs yet") preserved as the `{:else if}` branch

## Deviations from Plan

None — plan executed exactly as written.

## Checkpoint Verification

Task 3 (`checkpoint:human-verify`) cleared — approved 2026-06-25. Operator confirmed:
- Toggle renders in off state above Recent Runs
- Clicking toggle: URL becomes /admin/pipeline?incomplete=1, knob slides right (blue), table shows only paused/failed jobs
- Filter-on empty state ("No jobs need attention") renders correctly when no paused/failed jobs
- Clicking toggle again: URL returns to /admin/pipeline, full list restored
- Keyboard access verified (Tab focus ring, Enter/Space to flip)

## Known Stubs

None.

## Threat Flags

No new threat surface beyond the plan's threat model.
- T-13-03 mitigated: strict `=== '1'` comparison; any other param value → filter off
- T-13-04 mitigated: `FASTAPI_BASE_URL` and `ADMIN_TOKEN` remain server-only in `$env/static/private`

## Self-Check: PASSED

- `app/src/routes/admin/pipeline/+page.server.ts` modified with `incomplete` param: FOUND
- `app/src/routes/admin/pipeline/+page.svelte` has `role="switch"`: FOUND (line 312)
- Commit 1ccc408 (Task 1): present in git log
- Commit a5be595 (Task 2): present in git log
- `npx svelte-check` — 0 errors after both tasks
