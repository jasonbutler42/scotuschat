---
phase: 07-pipeline-runner
plan: "05"
subsystem: app
tags: [sveltekit, svelte5-runes, polling, discrepancy-review, pipeline-runner, job-status]
one_liner: "Per-job status page with 2.5s live polling step cards, inline discrepancy confirm/correct/add-person review, Continue Resolve submit, and verbatim failed-state error panel"

dependency_graph:
  requires:
    - "07-02: GET /api/admin/jobs/{id}, POST /api/admin/jobs/{id}/resolve, POST /api/admin/jobs/{id}/people"
    - "07-04: /admin/pipeline start page (navigation anchor)"
    - "06-01: hooks.server.ts session guard protecting all /admin/* routes"
  provides:
    - "/admin/pipeline/[job_id] — per-job status page with live step advancement"
    - "SSR load renders correct state on reload (PIPE-17 resumability)"
    - "Inline discrepancy review flow (PIPE-15, PIPE-16)"
    - "Continue Resolve submit writes dispositioned matches (D-14)"
    - "Failed-state error panel verbatim with no retry (D-17)"
  affects:
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts — created"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte — created"

tech_stack:
  added: []
  patterns:
    - "Svelte 5 Runes polling: $effect + setInterval 2500ms calling invalidateAll(); cleanup via returned clearInterval"
    - "Terminal-set guard: polling stops immediately when status in {completed, failed, paused}"
    - "Per-row discrepancy state: $state<Record<string, RowState>> keyed by raw_speaker_label"
    - "Candidates-only dropdown: Correct dropdown options come solely from row.candidates (no extra fetch)"
    - "AddNewPersonForm uses fetch ?/addPerson directly (not SvelteKit enhance) to get returned person for dynamic dropdown"
    - "Named SvelteKit actions: resolve + addPerson (no default)"
    - "fail(422) on non-OK resolve keeps job paused for retry (Pitfall 5)"

key_files:
  created:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      role: "SSR load + named actions (resolve, addPerson)"
      symbols_added:
        - "load: fetch GET /api/admin/jobs/{id}; throws error(404) on missing"
        - "actions.resolve: POST JSON matches to /api/admin/jobs/{id}/resolve; fail(422) on non-OK"
        - "actions.addPerson: POST to /api/admin/jobs/{id}/people; returns created person"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      role: "Live status page UI — polling, StepCard x3, DiscrepancyTable, AddNewPersonForm, ContinueResolveButton, ErrorPanel"
      symbols_added:
        - "$effect polling loop with terminal-set guard"
        - "stepStatus() helper — derives per-card status from job.current_step + job.status"
        - "rowStates $state — per-row disposition tracking"
        - "allDispositioned $derived — controls Continue Resolve visibility"
        - "matchesJson $derived — builds hidden field JSON from rowStates"
        - "handleConfirm / handleCorrect / handleSelectPerson / handleAddPerson"
        - "getRowCandidates — merges row.candidates with extraCandidates from addPerson"

decisions:
  - "[07-05]: AddNewPersonForm uses raw fetch (?/addPerson) rather than SvelteKit use:enhance because the action result must dynamically update a specific row's candidate list — enhance's form result cannot target sub-component state"
  - "[07-05]: $effect initialises rowStates only for keys not already tracked — preserves in-progress operator work when invalidateAll() re-runs the effect"
  - "[07-05]: CSS @keyframes spin defined in <style> scoped block — only spinner in the file, no global pollution"
  - "[07-05]: error_message rendered in monospace pre-wrap for readability but never paraphrased — numbers/text preserved verbatim per CLAUDE.md constraint"

metrics:
  duration_seconds: 164
  completed_date: "2026-06-16"
  tasks_completed: 2
  files_modified: 2
---

# Phase 07 Plan 05: Job Status Page Summary

Per-job status page at `/admin/pipeline/[job_id]` — three live step cards driven by 2.5s polling, inline discrepancy review, Continue Resolve, and verbatim failed-state error panel.

## What Was Built

### Task 1: Status-page server load, resolve action, and add-person action

`app/src/routes/admin/pipeline/[job_id]/+page.server.ts`:

- **load**: fetches `GET /api/admin/jobs/{job_id}` with `X-Admin-Token`; throws `error(404, 'Run not found')` on 404; returns `{ job }`.
- **actions.resolve**: reads hidden `matches` field (JSON array of `{ raw_speaker_label, person_id }`); POSTs to `/api/admin/jobs/{id}/resolve` with `Content-Type: application/json`. Returns `fail(422, ...)` on non-OK so the job stays paused for operator retry (Pitfall 5).
- **actions.addPerson**: reads `full_name` + `role_name` from formData; POSTs to `/api/admin/jobs/{id}/people`; returns the created person (`{ id, full_name }`) on success.
- Named actions (`resolve` + `addPerson`) — no single default action.

### Task 2: Status-page UI

`app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Svelte 5 Runes only:

**Polling (D-15/D-16):**
- `$effect` checks `TERMINAL = new Set(['completed','failed','paused'])` before starting.
- If non-terminal: `setInterval(2500ms, () => invalidateAll())`. Returns `clearInterval` cleanup.
- Effect dependency on `data.job.status` causes it to re-run after Continue Resolve flips `paused → running`.

**Three StepCards (Ingest / Parse / Resolve):**
- `stepStatus()` helper derives per-card state from `job.current_step` + `job.status`.
- StatusBadge: colored border + text on `#1e293b` surface (never filled). Spinner glyph on running with `aria-label="Running"`.
- Step container carries `aria-live="polite"` for screen reader announcements.
- Border-left overrides: running → `#93c5fd`, paused → `#fbbf24`, failed → `#ef4444`.

**Discrepancy review (D-11–D-14):**
- `DiscrepancyTable` renders inside the Resolve card when `status = paused`.
- Per-row `$state` tracks `{ person_id, disposition, correcting, addingPerson, extraCandidates }`.
- **Confirm**: records `auto_match_id`, marks `disposition = 'confirmed'`.
- **Correct**: opens `<select>` whose options are **exactly `row.candidates`** (the per-row candidates the resolve step wrote into the job — no additional people endpoint, no extra fetch) plus `— Add new person —`.
- Selecting a person: marks `disposition = 'corrected'`.
- Selecting Add new person: reveals `AddNewPersonForm` (Full name + Role only, D-13). On save, posts to `?/addPerson` via raw `fetch`, adds returned person to `extraCandidates`, auto-selects.

**Continue Resolve (D-14):**
- `allDispositioned $derived`: true when every discrepancy row has a non-null disposition.
- Button only visible when `status = paused AND allDispositioned`.
- Full width, `min-height: 44px`, accent border (`#93c5fd`).
- Submits form to `?/resolve` with hidden `matches` field (JSON from `matchesJson $derived`).
- Sets `continueSubmitting = true` on click → button text becomes "Submitting…" + `disabled` attribute.

**Error panel (D-17):**
- Renders when `status = failed`.
- Heading: "This run failed."
- Body: `Error: {job.error_message}` in `monospace`, `white-space: pre-wrap` — verbatim, no paraphrase.
- "Start a new run" link to `/admin/pipeline`. No retry button.

**Accessibility:**
- `aria-live="polite"` on step card container.
- Spinner carries `aria-label="Running"` on badge element.
- Error messages use `role="alert"`.
- All primary buttons meet `min-height: 44px` (WCAG 2.5.5).
- `<table>` with `<thead>`, `<tbody>`, `<th scope="col">` for column headers.
- No legacy Svelte syntax.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Design Decisions

**1. [Rule 2 - Critical functionality] AddNewPersonForm uses raw fetch instead of SvelteKit enhance**
- **Found during:** Task 2 implementation
- **Issue:** SvelteKit `use:enhance` form action result cannot be targeted to a specific row's state in the discrepancy table. The `addPerson` action returns the created person object, which must be dynamically added to exactly one row's `extraCandidates` array.
- **Fix:** Used `fetch('?/addPerson', { method: 'POST', body: fd })` directly, then handled the JSON result to update the specific row state. This is a correctness requirement — enhance would work but could not route the returned person to the correct row without additional hacks.
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`

## Threat Mitigations Applied

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-07-15 | mitigated | FastAPI resolve_job validates every person_id exists before writing (Plan 01/02); bad id returns 422 and leaves job paused |
| T-07-16 | accepted | hooks.server.ts session guard (Phase 6) protects all /admin/* routes — no per-page auth check needed |
| T-07-17 | accepted | error_message is pipeline failure detail for the single trusted operator; rendered verbatim per CLAUDE.md constraint |
| T-07-18 | mitigated | polling stops on any terminal state including paused; no client retry loop on failed state |

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries beyond those in the plan's threat model.

## Known Stubs

None — all data comes from the SSR load function via `data.job`; discrepancy rows and candidates are real server data.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: server load + actions | 6232cc0 | app/src/routes/admin/pipeline/[job_id]/+page.server.ts |
| Task 2: status page UI | d24329a | app/src/routes/admin/pipeline/[job_id]/+page.svelte |

## Self-Check: PASSED
