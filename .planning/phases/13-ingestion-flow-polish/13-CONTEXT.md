# Phase 13: Ingestion Flow Polish - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 fixes three known issues in the existing admin pipeline runner UI:

1. **Progress badges (PIPE-18)** — Step status cards on the job detail page show stale or incorrect state during transitions. The `stepStatus()` function in `[job_id]/+page.svelte` has edge cases when `current_step` is null mid-transition (e.g., while the DB write between steps is in-flight). Fix is frontend-only; server-side auto-advancement logic is not in scope.

2. **Typeahead (PIPE-19)** — The native `<datalist>` + `<input>` combobox used for speaker alias correction has browser-inconsistent filtering (especially Safari). Replace with a custom combobox: plain `<input>` + filtered `<ul>` rendered in Svelte. No new dependencies.

3. **Incomplete filter (PIPE-20)** — The pipeline list (`/admin/pipeline`) has no way to show only jobs requiring operator action. Add a toggle using `?incomplete=1` URL query param (matching the existing `/admin/people?incomplete=1` pattern). Filter applied server-side at the API level (GET /api/admin/jobs?incomplete=true). Incomplete = `paused` + `failed` statuses.

**Pre-Phase-13 cleanup required (before execution begins):**

There are 5 uncommitted files in the working tree from earlier work:
- `api/services/admin_arguments.py` — accidental removal of `resolved_at IS NOT NULL` publish gate (Phase 11 guard T-11-PUBGATE). **REVERT this file.**
- `app/src/routes/admin/arguments/+page.svelte` — relaxed publish button condition `{#if !arg.published_at}`. **REVERT this file.**
- `app/src/routes/admin/arguments/+page.server.ts` — added error logging for publish action. **KEEP and commit.**
- `pipeline/__main__.py` — added `--local-file` argument for dev workflow. **KEEP and commit.**
- `pipeline/commands/ingest.py` — handles `--local-file` path in ingest. **KEEP and commit.**

Commit the 3 kept files as a single pre-Phase-13 cleanup commit before any Phase 13 work runs. Do not include the 2 reverted argument files.

Out of scope: server-side auto-advancement logic in `GET /api/admin/jobs/{job_id}`, any new pipeline steps, any public-facing changes, any changes to the argument editor (Phase 11 work complete).

</domain>

<decisions>
## Implementation Decisions

### Progress Badges (PIPE-18)

- **D-01:** Fix is frontend-only. The server-side auto-advancement logic in `GET /api/admin/jobs/{job_id}` was validated in Phase 7 and is not in scope.
- **D-02:** Diagnose before fixing. The first plan step adds `console.log(job.status, job.current_step)` inside the `$effect` poll loop to capture what values arrive during live transitions. The fix is written against what the diagnostic reveals.
- **D-03:** When `current_step` is `null` and `job.status === 'running'` (transition window between steps), the UI must preserve the last known step as 'running' rather than flashing all badges to 'pending'. Implement by tracking the last non-null `current_step` in a `$state` variable and falling back to it when the poll returns null.
- **D-04:** Reduce poll interval from 2.5s to 1s during `running` state. The `$effect` already has terminal-state short-circuit; just change the `setInterval` delay for running jobs.

### Typeahead Combobox (PIPE-19)

- **D-05:** Replace the native `<datalist>` + `<input>` with a custom combobox: a plain text `<input>` that filters `data.people` (the full people roster already loaded server-side) on every keystroke, and renders matching candidates in a styled `<ul>` below the input. No third-party library — vanilla Svelte 5 Runes.
- **D-06:** Filter candidates client-side using `$derived` — match on `full_name` and `role_name` fields using a case-insensitive contains check against the typed value.
- **D-07:** Keep the "Add new person" option at the bottom of the candidate dropdown. Selecting it hides the dropdown and shows the existing inline AddNewPersonForm below the input. Same flow as before; just works correctly now.
- **D-08:** Combobox closes (dropdown hidden, selection committed) when the operator clicks a candidate from the list. Clicking outside the combobox with no selection made cancels without changing the row's disposition.
- **D-09:** The combobox replaces the `<input list>` + `<datalist>` block inside the `{:else if s?.correcting}` branch in `[job_id]/+page.svelte`. All other parts of the discrepancy review flow (Confirm, Change buttons, AddNewPersonForm, `handleSelectPerson`, `getRowCandidates`) remain unchanged.

### Incomplete Filter (PIPE-20)

- **D-10:** Incomplete is defined as `paused` + `failed` statuses. Both require operator action before the argument can proceed.
- **D-11:** Filter toggle uses URL query param `?incomplete=1` (matches `/admin/people?incomplete=1` pattern). The SvelteKit load function in `+page.server.ts` reads the URL param and passes `incomplete=true` to the FastAPI jobs endpoint.
- **D-12:** Filter applied server-side: `GET /api/admin/jobs?incomplete=true` (new optional query param on the existing endpoint). The API service layer filters the query to `WHERE status IN ('paused', 'failed')`.
- **D-13:** The toggle lives on the pipeline list page (`/admin/pipeline/+page.svelte`) as a button that navigates to `?incomplete=1` (or back to the page without the param). It sits above the Recent Runs table, visually consistent with the admin dark theme.

### Pre-Phase-13 Cleanup

- **D-14:** Revert `api/services/admin_arguments.py` and `app/src/routes/admin/arguments/+page.svelte` to HEAD before committing anything. The resolved_at publish gate (T-11-PUBGATE) must remain intact.
- **D-15:** Commit the remaining 3 files (`app/src/routes/admin/arguments/+page.server.ts`, `pipeline/__main__.py`, `pipeline/commands/ingest.py`) as a single pre-Phase-13 cleanup commit with message: `fix: pre-phase-13 cleanup — publish logging + local-file ingest flag`.

### Claude's Discretion

- Exact visual treatment of the combobox dropdown (width matching input, border, max-height for scroll) — match admin dark theme tokens
- Whether the combobox input clears on Escape or restores to the last confirmed value
- Exact wording of the toggle button ("Show incomplete only" / "Show all")
- Combobox item hover/focus highlight color (suggest `#1e293b` → `#334155` hover within the dark theme)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §Ingestion & Pipeline — PIPE-18, PIPE-19, PIPE-20 (3 requirements this phase closes)
- `.planning/ROADMAP.md` §Phase 13 — Goal and 3 success criteria (must all be TRUE)

### Existing Implementation to Fix
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — `stepStatus()` function (lines 143–161), `$effect` poll loop (lines 40–48), discrepancy review typeahead block (`{:else if s?.correcting}` branch ~lines 515–551); these are the exact sections being changed for PIPE-18 and PIPE-19
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — server load function; `data.people` (lines 39–55) already fetches the full people roster for typeahead
- `app/src/routes/admin/pipeline/+page.svelte` — pipeline list page; Recent Runs table and new filter toggle go here
- `app/src/routes/admin/pipeline/+page.server.ts` — `load` function (lines 5–22); needs to forward `incomplete` URL param to API

### API Endpoints to Extend
- `api/routers/admin.py` — `GET /api/admin/jobs` handler; add optional `incomplete: bool = False` query param (following the existing pattern on `GET /api/admin/people` at line 315)
- `api/services/admin_jobs.py` (or wherever `list_jobs` lives) — add `incomplete` filter to the DB query

### Prior Phase Context
- `.planning/phases/11-argument-metadata-editing/11-CONTEXT.md` — T-11-PUBGATE: `publish_argument` MUST enforce `resolved_at IS NOT NULL` server-side; revert of accidental removal is required before Phase 13 begins
- `.planning/STATE.md` §Accumulated Context — Phase 7 decisions about fire-and-poll architecture, job state machine

### Design System
- Admin dark theme tokens: `#0f1117` bg, `#1e293b` card surface, `#334155` border, `#94a3b8` body text, `#93c5fd` accent blue — all new UI must use these exact values

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` `getRowCandidates()` (lines 240–253) — already merges `data.people` + `row.candidates` + `extraCandidates` into a deduplicated list; the custom combobox reads from this same merged list
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` `handleSelectPerson()` (lines 221–238) — already handles person selection and the `__add_new__` sentinel; custom combobox calls this unchanged
- `$effect` poll loop with `TERMINAL` set check (lines 40–48) — already has the right terminal-state short-circuit; just change the `setInterval` ms value for D-04

### Established Patterns
- **SvelteKit form actions + `use:enhance`**: all admin form submissions use progressive enhancement — mandatory; AddNewPersonForm already uses it
- **Server-only env vars**: `FASTAPI_BASE_URL` from `$env/static/private` — never `PUBLIC_`; load function fetches to API, not the client
- **`invalidateAll()` for poll updates**: already used in the `$effect` loop; custom combobox does not change this
- **URL query param filter**: `?incomplete=1` mirrors the `/admin/people?incomplete=1` pattern; the load function reads `url.searchParams.get('incomplete')` and passes a boolean to the API
- **API optional bool param**: `GET /api/admin/people?incomplete=false` is the existing reference pattern (admin.py line 315); `GET /api/admin/jobs?incomplete=false` follows the same shape

### Integration Points
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — `{:else if s?.correcting}` branch: swap `<input list> + <datalist>` block for the new custom combobox component/inline block
- `app/src/routes/admin/pipeline/+page.server.ts` — `load` function: add `const incomplete = url.searchParams.get('incomplete') === '1';` and pass to API fetch
- `api/routers/admin.py` — `GET /api/admin/jobs` route: add `incomplete: bool = False` query param, pass to service
- `api/services/admin_jobs.py` (find the list_jobs function) — add `.where(AdminJob.status.in_(['paused', 'failed']))` clause when `incomplete=True`

</code_context>

<specifics>
## Specific Ideas

- **Diagnostic logging pattern**: Inside the `$effect` poll loop, before `setInterval`, add:
  ```typescript
  console.debug('[poll]', { status: data.job.status, current_step: data.job.current_step });
  ```
  This appears in the browser console during a live run and reveals exactly when null current_step arrives.

- **Last-known-step tracking**: Add `let lastKnownStep = $state<string | null>(data.job.current_step ?? null);` outside the effect. Inside the poll effect (after `invalidateAll()`), update it when non-null: `if (data.job.current_step) lastKnownStep = data.job.current_step;`. Pass `lastKnownStep` to `stepStatus()` as a fallback.

- **Combobox dropdown behavior**: The custom `<ul>` should only be visible when the input is focused AND `query.length > 0` (or always when focused, your call). Clicking outside should close it via a `document.addEventListener('click', ...)` inside a `$effect` cleanup.

- **Filter toggle button placement**: Above the "Recent Runs" heading, right-aligned. e.g., `<button onclick="goto('/admin/pipeline?incomplete=1')">Show incomplete only</button>`. When `?incomplete=1` is active, button text reads "Show all" and navigates to `/admin/pipeline`.

</specifics>

<deferred>
## Deferred Ideas

- Server-side auto-advancement logic audit — the GET endpoint's inline step-advancement is working correctly per Phase 7 validation; a future audit is possible but not warranted by PIPE-18
- Animated step transition (e.g., brief pulse when a badge flips state) — cosmetic enhancement, not in PIPE-18 scope
- Reducing Recent Runs history beyond 10 items, pagination of jobs list — not in PIPE-20 scope

</deferred>

---

*Phase: 13-ingestion-flow-polish*
*Context gathered: 2026-06-24*
