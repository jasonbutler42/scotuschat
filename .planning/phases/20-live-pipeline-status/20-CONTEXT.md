# Phase 20: Live Pipeline Status - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add automatic polling to the pipeline list page (`/admin/pipeline`) so status badges update without manual reload while any job is running. The job detail page already satisfies PIPE-24 via its existing 1s polling — verification only. Primary deliverable is PIPE-23 (list page auto-refresh).

</domain>

<decisions>
## Implementation Decisions

### Poll Interval
- **D-01:** Both list page and detail page poll at **1s** — consistent cadence, effectively real-time for single-operator use. No differentiation between pages.
- **D-02:** 50ms or sub-second intervals are explicitly ruled out — `invalidateAll()` causes full re-renders and form state disruption at aggressive rates with no perceptible benefit (pipeline step transitions happen every 10–60 seconds minimum).

### List Page Poll Stop Conditions
- **D-03:** Poll while `at least one job has status === 'running'`. Stop when no job is running (all are `pending`, `paused`, `completed`, or `failed`).
- **D-04:** `paused` and `pending` do NOT keep polling alive — `paused` is stable state waiting for operator action; `pending` is a transient pre-start state (milliseconds). Only `running` triggers and sustains polling.

### Detail Page Scope
- **D-05:** The existing 1s `$effect` + `setInterval` + `invalidateAll()` on the job detail page already satisfies PIPE-24. No changes needed to the detail page implementation.
- **D-06:** Phase 20 scope = add list-page polling + verify detail-page behavior matches PIPE-24 acceptance criteria.

### Folded Todos
- **Todo: "Live polling for pipeline list page job cards"** — Captured problem: list page has no polling; status badges freeze on "Running" until manual reload. Solution approach confirmed: same `invalidateAll()` pattern as detail page. Interval changed from todo's suggested 2.5s to 1s (consistent with detail page, same rationale applies). Files: `app/src/routes/admin/pipeline/+page.svelte`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Polling Implementation
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` lines 56–78 — Canonical `$effect` + `setInterval` + `invalidateAll()` pattern. The list page implementation MUST follow this exact pattern.

### List Page (target file)
- `app/src/routes/admin/pipeline/+page.svelte` — Full list page component. The `data.jobs` array is the polling target. Polling condition: `data.jobs.some(j => j.status === 'running')`.
- `app/src/routes/admin/pipeline/+page.server.ts` — Server load function that fetches `/api/admin/jobs`. `invalidateAll()` re-runs this function.

### Requirements
- `.planning/REQUIREMENTS.md` — PIPE-23 (list page) and PIPE-24 (detail page) are the acceptance criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `$effect` + `setInterval` + `invalidateAll()` pattern: already implemented at `[job_id]/+page.svelte:63-78`. The list page implementation is a direct adaptation — change the `TERMINAL` condition from single-job status to `data.jobs.some(j => j.status === 'running')`.
- `lastKnownStep` fallback ($state): detail page pattern for preventing badge flicker during step transitions. Not needed on the list page (badges show job-level status, not step).

### Established Patterns
- `invalidateAll()` re-runs the server load function → new FastAPI call → reactive re-render. No client-side state management needed.
- `$effect` reactive dependency on `data.jobs` — the effect automatically restarts when `data` changes (e.g., after a new job is started from the form).
- Terminal state set on detail page: `{completed, failed, paused}`. List page uses a different condition: `data.jobs.some(j => j.status === 'running')`.

### Integration Points
- List page `+page.svelte`: add a `$effect` block parallel to the existing detail-page effect. No server-side changes needed.
- `aria-live="polite"` is already on the `<div>` wrapping the jobs table in the list page — screen reader announcements already wired.
- The list page form (New Run card) uses `$state` for mode/submitting/docket — `invalidateAll()` does not disrupt these because they are client-side `$state`, not derived from `data`.

</code_context>

<specifics>
## Specific Ideas

- The todo suggested 2.5s but user confirmed 1s for consistency with the detail page — simpler and still effectively real-time.
- No WebSocket or SSE consideration — polling is the validated pattern for this project.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **"Prevent duplicate argument creation during ingest"** — matched by keyword overlap but this was resolved in Phase 19 (PIPE-24/PIPE-25 complete). No action needed.

</deferred>

---

*Phase: 20-Live Pipeline Status*
*Context gathered: 2026-07-01*
