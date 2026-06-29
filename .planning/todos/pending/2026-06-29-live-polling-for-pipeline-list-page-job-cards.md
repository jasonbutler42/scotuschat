---
created: 2026-06-29T16:19:39.209Z
title: Live polling for pipeline list page job cards
area: ui
files:
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
---

## Problem

The pipeline list page (`/admin/pipeline`) has no real-time polling. When a job is running,
its status badge stays frozen at "Running" on the list page until the operator manually
refreshes. The operator can't trust what they're seeing — they don't know if ingest is
still running, completed, or failed without a hard reload.

The job detail page (`/admin/pipeline/[job_id]`) already has 1s polling via `setInterval`
inside a `$effect` (line 66), but only while `status === 'running'`. The list page has no
equivalent mechanism at all.

## Solution

Add `setInterval`-based polling to the pipeline list page using the same `invalidateAll()`
pattern already used on the detail page. Poll only when at least one job in the list has
`status === 'running'` or `status === 'paused'` (paused needs review — also relevant). Stop
polling once all jobs are in terminal states (`completed`, `failed`).

The 1s interval on the detail page may be more aggressive than needed for the list view;
2.5s is probably fine here since the list doesn't need step-level granularity.
