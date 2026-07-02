# Phase 20: Live Pipeline Status - Research

**Researched:** 2026-07-01
**Domain:** SvelteKit 2 / Svelte 5 Runes — client-side polling with `$effect` + `invalidateAll()`
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Both list page and detail page poll at **1s** — consistent cadence, effectively real-time for single-operator use.
- **D-02:** 50ms or sub-second intervals are explicitly ruled out — `invalidateAll()` causes full re-renders and form state disruption at aggressive rates.
- **D-03:** Poll while `at least one job has status === 'running'`. Stop when no job is running.
- **D-04:** `paused` and `pending` do NOT keep polling alive. Only `running` triggers and sustains polling.
- **D-05:** The existing 1s `$effect` + `setInterval` + `invalidateAll()` on the job detail page already satisfies PIPE-24. No changes needed to the detail page implementation.
- **D-06:** Phase 20 scope = add list-page polling + verify detail-page behavior matches PIPE-24 acceptance criteria.

### Claude's Discretion
None — all implementation decisions are locked.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-23 | Pipeline list page updates job status badges automatically while any run is active — no manual reload needed | Add `$effect` + `setInterval` + `invalidateAll()` to `+page.svelte`; stop condition: `!data.jobs.some(j => j.status === 'running')` |
| PIPE-24 | Pipeline job detail page updates step cards live while the run is active — operator can watch step progression in real time | Already implemented at `[job_id]/+page.svelte:63-78`; verification only |
</phase_requirements>

---

## Summary

Phase 20 adds automatic 1s polling to the pipeline list page (`/admin/pipeline`) so job status badges refresh without a manual reload while any run is active. The implementation is a narrow Svelte 5 Runes change: one `$effect` block added to `app/src/routes/admin/pipeline/+page.svelte`. No server-side changes, no new dependencies, no new API endpoints.

The canonical pattern already exists verbatim in `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (lines 63–78). The list-page adaptation differs in exactly one place: the terminal-state guard. The detail page stops on `TERMINAL = {completed, failed, paused}` for a single job. The list page stops when `!data.jobs.some(j => j.status === 'running')` — i.e., no job anywhere is currently running.

PIPE-24 (detail page) is already satisfied by the existing implementation and requires only a UAT verification pass, not code changes.

**Primary recommendation:** Copy the `$effect` block from `[job_id]/+page.svelte:63-78` into `+page.svelte`, replace the single-job terminal check with the multi-job `some()` condition, and verify the detail page against PIPE-24 acceptance criteria.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auto-refresh polling logic | Browser / Client (`$effect`) | — | Client-side timer drives `invalidateAll()` calls; no server timer or push needed |
| Job status data fetch | Frontend Server (SSR load function) | — | `+page.server.ts` fetches `/api/admin/jobs` on each `invalidateAll()` call |
| Job status persistence | API / Backend (FastAPI) | Database (PostgreSQL) | FastAPI reads `pipeline_runs.status` from Postgres; no caching layer |
| Screen reader announcement | Browser / Client (`aria-live`) | — | `aria-live="polite"` already on the jobs table wrapper; no changes needed |

---

## Standard Stack

No new packages. This phase uses only what is already installed.

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `$app/navigation` (SvelteKit) | 2.x | `invalidateAll()` — re-runs all server load functions | Project-standard; already imported in `[job_id]/+page.svelte` |
| Svelte 5 Runes (`$effect`, `$state`) | 5.x | Reactive lifecycle hooks for setting/clearing intervals | Project-mandated (CLAUDE.md: "no legacy stores") |

### No Package Legitimacy Audit Needed

This phase installs zero external packages. The audit section is omitted.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser tab (/admin/pipeline)
│
│  $effect fires when data.jobs changes (including on first render)
│  ↓
│  [has any job with status='running'?]
│      No  → return (no interval created; any prior interval already cleared by cleanup)
│      Yes → setInterval(1000ms)
│              │
│              └── await invalidateAll()
│                      │
│                      └── SvelteKit re-runs +page.server.ts load()
│                              │
│                              └── fetch FASTAPI_BASE_URL/api/admin/jobs
│                                      │
│                                      └── FastAPI reads pipeline_runs from PostgreSQL
│                                              │
│                                              └── JSON response → reactive re-render
│
│  $effect cleanup fn: clearInterval(interval)
│    — called when: effect re-runs (data.jobs changed), component unmounts
```

### Recommended Project Structure

No structural changes. The change is a single `$effect` block added to the existing file:

```
app/src/routes/admin/pipeline/
├── +page.svelte        ← ADD $effect block here (only change)
└── +page.server.ts     ← No changes
```

### Pattern 1: `$effect` + `setInterval` + `invalidateAll()` — list-page variant

**What:** A reactive effect that creates a 1s polling interval when any job is running, and tears it down automatically when the condition is no longer true or the component unmounts.

**When to use:** When a SvelteKit page needs periodic data refresh without WebSocket/SSE, and the page already uses server load functions as the data source.

**Canonical source in codebase:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte` lines 63–78

**List-page adaptation (the only difference is the stop condition):**

```typescript
// Source: adapted from [job_id]/+page.svelte:63-78
import { invalidateAll } from '$app/navigation';

$effect(() => {
    // Stop polling when no job is currently running.
    // data.jobs is the reactive prop — $effect re-runs when it changes,
    // so a new job starting will automatically restart polling.
    if (!data.jobs.some((j: { status: string }) => j.status === 'running')) return;

    const interval = setInterval(async () => {
        await invalidateAll();
    }, 1000);

    return () => clearInterval(interval);
});
```

**Key properties of this pattern:**
- The `$effect` cleanup function (`return () => clearInterval(interval)`) runs before each re-execution AND on component unmount. No manual teardown needed.
- `$effect` takes a reactive dependency on `data.jobs` implicitly — when `invalidateAll()` delivers new `data`, the effect re-evaluates the stop condition.
- The `return` (early exit when no job is running) means no interval is created in that case, so calling `clearInterval(undefined)` never occurs.
- `submitting`, `mode`, `docketInput`, and other `$state` variables in the list page are client-side state and are NOT reset by `invalidateAll()`. The CONTEXT.md confirms this explicitly (D-06 code context).

**Detail-page terminal set for reference (do NOT use on list page):**

```typescript
// Source: [job_id]/+page.svelte:64
const TERMINAL = new Set(['completed', 'failed', 'paused']);
if (!data?.job?.status || TERMINAL.has(data.job.status)) return;
```

The list page must NOT use this set. It would fail to stop polling when the last `running` job flips to `paused` (needs review) — a job that is paused is not terminal from the list perspective, but it is also not `running`, so the `some()` check correctly stops polling.

### Anti-Patterns to Avoid

- **Using the detail-page TERMINAL set verbatim on the list page:** The detail page has one job with known terminal states. The list page must check whether *any* job is `running`. A `paused` job on the list page is stable — polling should stop, not continue.
- **Storing `lastKnownStep` on the list page:** The list page shows job-level status badges, not step cards. The `lastKnownStep` flicker guard is only needed on the detail page (PIPE-18). Do not add it to the list page.
- **Adding `data-sveltekit-reload` to the polling mechanism:** This is for navigation links, not the polling pattern. `invalidateAll()` already triggers a server-side refetch without a full page navigation.
- **Modifying `+page.server.ts`:** No server changes are needed. `invalidateAll()` already re-runs the existing load function.
- **Polling in a `onMount` with no cleanup:** Svelte 5 `$effect` is the correct hook; it guarantees cleanup. `onMount` from `svelte` is legacy-adjacent and does not participate in Runes reactivity.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Re-fetching data on an interval | Custom fetch loop with manual state management | `invalidateAll()` inside `setInterval` inside `$effect` | `invalidateAll()` is the SvelteKit-idiomatic way to re-run load functions; it participates in SvelteKit's deduplication and error handling |
| Stopping the poll on terminal state | Boolean `$state` flag + manual clearInterval call | Early `return` from `$effect` | The early return prevents the interval from being created; the cleanup fn (`return () => clearInterval`) handles teardown automatically |
| Detecting new jobs starting mid-session | Watching `data.jobs.length` explicitly | `$effect` reactive dependency on `data.jobs` | `$effect` automatically re-runs when `data.jobs` changes (because `invalidateAll()` updates `data`), so a new job appearing will restart polling without extra code |

**Key insight:** The `$effect` + `setInterval` + `invalidateAll()` pattern is already battle-tested in this codebase. Do not introduce a parallel pattern.

---

## Common Pitfalls

### Pitfall 1: Effect runs before `data.jobs` is populated (empty array edge case)
**What goes wrong:** On first load with no jobs, `data.jobs` is `[]`. `[].some(...)` returns `false`, so the effect returns early — correct. No issue.
**Why it happens:** The `some()` short-circuit handles the empty case correctly.
**How to avoid:** No special handling needed. The pattern works.

### Pitfall 2: Polling continues after navigating away
**What goes wrong:** If the operator navigates to a detail page via the "View" link and the list page `$effect` interval is still ticking, `invalidateAll()` calls could fire on the wrong page.
**Why it happens:** SvelteKit destroys the component on navigation, which triggers `$effect` cleanup. `clearInterval` is called automatically.
**How to avoid:** No special handling needed. SvelteKit lifecycle guarantees cleanup.

### Pitfall 3: `invalidateAll()` resets form state
**What goes wrong:** The New Run card has `$state` fields (`mode`, `submitting`, `docketInput`, `questionInput`, `duplicateWarning`). If `invalidateAll()` reset these, the operator's in-progress form would be wiped on every poll tick.
**Why it happens:** This would happen if form state were derived from `data`. It is not — all form state is client-side `$state` and is unaffected by `invalidateAll()`.
**How to avoid:** No action needed. The existing `$state` fields are safe. Confirmed by CONTEXT.md code context section.
**Warning signs:** If the form clears every second during a run — check that no form field binds to `data.*` instead of a `$state` variable.

### Pitfall 4: `$effect` placement — must be in `<script>`, not template
**What goes wrong:** Placing the `$effect` block inside the `{#each}` or elsewhere in the template compiles but does not behave as expected.
**Why it happens:** `$effect` is a Runes primitive that belongs in the `<script lang="ts">` block.
**How to avoid:** Add the `$effect` block after the existing `$state` and `$derived` declarations in the `<script lang="ts">` block.

### Pitfall 5: `import { invalidateAll }` missing from list page
**What goes wrong:** `invalidateAll is not a function` runtime error.
**Why it happens:** The list page currently imports only `{ goto }` from `$app/navigation`. `invalidateAll` must be added to the import.
**How to avoid:** Change the import line: `import { goto, invalidateAll } from '$app/navigation';`

---

## Runtime State Inventory

Step 2.5 SKIPPED — this is a greenfield addition to the list page, not a rename/refactor/migration phase. No runtime state affected.

---

## Environment Availability

Step 2.6 SKIPPED — no external dependencies beyond the already-running SvelteKit dev server and FastAPI backend. Both are required by the existing codebase and are presumed available.

---

## Validation Architecture

`nyquist_validation` is explicitly `false` in `.planning/config.json`. This section is omitted per config.

---

## Security Domain

This phase adds no new data access, no new endpoints, no new authentication surface, and no new form inputs. The polling mechanism calls `invalidateAll()` which re-runs the existing server load function with the existing `X-Admin-Token` header and `FASTAPI_BASE_URL` — both already reviewed in prior phases. No new ASVS controls apply.

---

## Code Examples

### Complete `$effect` block for list page

```typescript
// File: app/src/routes/admin/pipeline/+page.svelte
// Add to <script lang="ts"> after existing $state declarations

$effect(() => {
    // D-03: Poll while at least one job has status === 'running'.
    // D-04: paused and pending do NOT keep polling alive.
    if (!data.jobs.some((j: { status: string }) => j.status === 'running')) return;

    const interval = setInterval(async () => {
        await invalidateAll();
    }, 1000);

    return () => clearInterval(interval);
});
```

### Import line change

```typescript
// Before:
import { goto } from '$app/navigation';

// After:
import { goto, invalidateAll } from '$app/navigation';
```

### Existing detail-page polling (for reference — DO NOT CHANGE)

```typescript
// Source: app/src/routes/admin/pipeline/[job_id]/+page.svelte lines 63-78
$effect(() => {
    const TERMINAL = new Set(['completed', 'failed', 'paused']);
    if (!data?.job?.status || TERMINAL.has(data.job.status)) return;

    const interval = setInterval(async () => {
        await invalidateAll();
        console.debug('[poll]', { status: data.job.status, current_step: data.job.current_step });
        if (data.job.current_step !== null && data.job.current_step !== undefined) {
            lastKnownStep = data.job.current_step;
        }
    }, 1000);

    return () => clearInterval(interval);
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `onMount` + `setInterval` (Svelte 4 legacy stores) | `$effect` + `setInterval` (Svelte 5 Runes) | Svelte 5.0 | `$effect` participates in the Runes reactive graph and guarantees cleanup; `onMount` does not |
| Manual `fetch` on interval | `invalidateAll()` on interval | SvelteKit 2.x | `invalidateAll()` re-runs server load functions, keeping data flow through the established SSR path |

**Deprecated/outdated:**
- `onMount` + `setInterval` for polling: Not wrong, but non-idiomatic in Svelte 5. CLAUDE.md mandates Runes — use `$effect`.
- Direct `PUBLIC_FASTAPI_BASE_URL` client-side fetch: Forbidden by CLAUDE.md architecture rule. All FastAPI calls go through `+page.server.ts`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `$effect` cleanup is called on SvelteKit component unmount during navigation | Common Pitfalls / Pitfall 2 | If cleanup is not called, a stale interval continues firing `invalidateAll()` on the wrong page. In practice this would surface as console errors or unexpected data refreshes. | 

*All other claims in this research are VERIFIED against the codebase (direct code reads) or CITED from the existing implementation.*

---

## Open Questions

None. CONTEXT.md has locked all implementation decisions. The pattern is fully specified and the canonical implementation exists in the codebase.

---

## Sources

### Primary (HIGH confidence — codebase reads)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` lines 63–78 — canonical `$effect` + `setInterval` + `invalidateAll()` polling pattern
- `app/src/routes/admin/pipeline/+page.svelte` — full list page; confirms `$state` variables are client-side only (safe from `invalidateAll()` reset); confirms `aria-live="polite"` is already wired
- `app/src/routes/admin/pipeline/+page.server.ts` — server load function; confirms `invalidateAll()` will re-run the `/api/admin/jobs` fetch with no server-side changes needed
- `.planning/phases/20-live-pipeline-status/20-CONTEXT.md` — all implementation decisions locked (D-01 through D-06)
- `.planning/REQUIREMENTS.md` — PIPE-23, PIPE-24 acceptance criteria
- `.planning/config.json` — `nyquist_validation: false` (validation section omitted)

### Secondary (MEDIUM confidence)
- None needed — codebase provides ground truth for all claims.

### Tertiary (LOW confidence)
- A1 (Pitfall 2) — `$effect` cleanup on navigation: based on Svelte 5 training knowledge. If the project's existing detail-page polling has never caused stale-interval bugs during navigation, this is implicitly validated in production.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — read directly from codebase; no new packages
- Architecture: HIGH — pattern exists verbatim in `[job_id]/+page.svelte`; adaptation is mechanically clear
- Pitfalls: HIGH — derived from direct code inspection of the target files; one LOW assumption noted

**Research date:** 2026-07-01
**Valid until:** Stable — Svelte 5 Runes and SvelteKit 2 are mature; no time-sensitivity

## Project Constraints (from CLAUDE.md)

| Directive | Impact on This Phase |
|-----------|---------------------|
| Svelte 5 Runes — no legacy stores | Use `$effect`, not `onMount` + writable stores |
| All FastAPI calls from SvelteKit go through `+page.server.ts` | Polling must call `invalidateAll()` to re-run the load function — never fetch `FASTAPI_BASE_URL` from client code |
| `FASTAPI_BASE_URL` is server-only — never `PUBLIC_` | Confirmed: no client-side URL needed; `invalidateAll()` triggers the server load |
| Alembic is the sole DDL authority | Not applicable — no schema changes |
| Pipeline is offline only — no HTTP pipeline endpoints | Not applicable — polling reads status, does not trigger pipeline steps |
| Apolitical framing | Not applicable — this phase is UI infrastructure only |
