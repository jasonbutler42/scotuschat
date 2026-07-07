---
created: 2026-07-07T19:53:09.441Z
title: Add Archived pipeline run status
area: ui
files:
  - app/src/lib/components/RunStatusCard.svelte
  - api/services/admin_jobs.py
---

## Problem

Surfaced during Phase 25 UAT (`.planning/phases/25-pipeline-job-detail-page/25-UAT.md`). Once a pipeline run's argument has been created, `RunStatusCard` shows the `already_created` state, but there is no distinct status for "this run is now permanently read-only because its argument exists" versus a run that is merely `completed`. The user wants a new status — **Archived** — with a grey/neutral badge color, specifically for pipeline runs whose linked argument has been created (the run itself is read-only from that point on).

This is separate from `completed` (which likely still refers to the pipeline processing outcome, not the read-only/argument-created lifecycle state).

## Solution

TBD. Likely touches:
- `get_job_readiness` / `RunReadiness` (`api/services/admin_jobs.py`, `api/schemas/admin_jobs.py`) — may need a new state or a derived flag distinguishing "completed" from "archived (argument created)".
- `RunStatusCard.svelte`'s `already_created` branch — add the grey/neutral badge treatment.
- Confirm whether "Archived" replaces or supplements the existing `already_created` readiness state, and whether it affects the job's underlying `status` field or is purely a display-layer distinction.
