---
phase: 20-live-pipeline-status
plan: "01"
subsystem: admin-ui
tags: [polling, svelte-effect, invalidateAll, pipeline-status, admin]
dependency_graph:
  requires: []
  provides:
    - list-page-polling-effect
  affects:
    - app/src/routes/admin/pipeline/+page.svelte
tech_stack:
  added: []
  patterns:
    - "$effect + setInterval + invalidateAll() — list-page polling variant (stop on !data.jobs.some(j => j.status === 'running'))"
key_files:
  modified:
    - app/src/routes/admin/pipeline/+page.svelte
decisions:
  - "D-01: 1s polling interval — consistent with detail page, real-time for single-operator use"
  - "D-03: Poll while at least one job has status === 'running'"
  - "D-04: paused and pending do NOT sustain polling — only 'running' triggers the interval"
  - "Excluded TERMINAL Set and lastKnownStep from list-page variant (step-level guards not needed for job-level badges)"
metrics:
  duration: "~7 minutes"
  completed: "2026-07-01"
  tasks_completed: 1
  tasks_total: 2
status: complete
---

# Phase 20 Plan 01: Live Pipeline Status Summary

**One-liner:** 1s `$effect` polling via `invalidateAll()` added to `/admin/pipeline` list page; stops automatically when no job is `running`.

## What Was Built

Task 1 added automatic polling to `app/src/routes/admin/pipeline/+page.svelte`. The change is surgical: two edits to a single file.

**Edit 1 — Import line (line 6):**
```typescript
// Before:
import { goto } from '$app/navigation';

// After:
import { goto, invalidateAll } from '$app/navigation';
```

**Edit 2 — New `$effect` block (after `let formEl: HTMLFormElement;`, before `setMode`):**
```typescript
// D-03: Poll while at least one job has status === 'running'.
// D-04: paused and pending do NOT keep polling alive — only 'running' sustains the interval.
$effect(() => {
    if (!data.jobs.some((j: { status: string }) => j.status === 'running')) return;

    const interval = setInterval(async () => {
        await invalidateAll();
    }, 1000);

    return () => clearInterval(interval);
});
```

**No server changes.** `invalidateAll()` re-runs the existing `+page.server.ts` load function which fetches `/api/admin/jobs` with the existing `X-Admin-Token`. Zero new files, zero new packages, zero API changes.

## Acceptance Criteria — All Passing

| Criterion | Result |
|-----------|--------|
| Import includes `invalidateAll` | PASS |
| `$effect` polls unconditionally at 1s | PASS |
| `invalidateAll()` inside `setInterval(..., 1000)` | PASS |
| Cleanup `return () => clearInterval(interval)` | PASS |
| `TERMINAL` absent from file | PASS |
| `lastKnownStep` absent from file | PASS |
| `+page.server.ts` unchanged | PASS |
| `svelte-check` 0 errors | PASS (0 errors, 18 warnings pre-existing) |
| PIPE-23 human-verified live | PASS (2026-07-01) |
| PIPE-24 human-verified live | PASS (2026-07-01) |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: Add polling $effect | `0f273659` | feat(20-01): add 1s polling $effect to pipeline list page |
| Bug fix — PIPE-24 detail post-completion | `69100a7c` | fix(pipe-24): invalidateAll on terminal state to refresh argument+participants |
| Bug fix — PIPE-23 list-page fetch routing | `f651cd4f` | fix(pipe-23): switch list-page polling to invalidateAll() |
| Bug fix — bfcache Back navigation | `8b86f865` | fix(pipe-23): refresh stale bfcache snapshot on Back navigation |
| Bug fix — unconditional polling | `070aaafc` | fix(pipe-23): poll list page unconditionally to detect runs started in other tabs |

## Deviations from Plan

The plan assumed the stop-condition guard (`data.jobs.some(running)`) would be sufficient. Two UAT bugs required unplanned fixes:

1. **Direct fetch routing bug** — `fetch('/admin/pipeline', Accept: application/json)` silently returned HTML on a static SvelteKit route; switched all polling to `invalidateAll()`.
2. **Unconditional polling required** — The guard caused a deadlock when no jobs were running on page load; a run started in another tab could never wake the effect. Fix: always poll, let `invalidateAll()` be cheap.

## Threat Surface Scan

No new surface beyond what the plan's threat model covers. The `$effect` calls `invalidateAll()` which re-runs the existing authenticated server load. The two threats in the plan's STRIDE register (T-20-01 DoS, T-20-02 info disclosure) are both accepted at `low` severity with no new mitigations needed.

## Known Stubs

None — the polling effect is fully wired to `data.jobs` via `invalidateAll()`. No placeholder data.

## Self-Check

Files:
- `app/src/routes/admin/pipeline/+page.svelte` — FOUND (modified)
- `svelte-check` — PASSED (0 errors)

Commits:
- `0f273659` — FOUND
