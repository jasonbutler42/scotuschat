# Phase 24: Pipeline List Page - Research

**Researched:** 2026-07-06
**Domain:** SvelteKit 5 Runes component extraction, FastAPI query param removal, compound badge logic
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Question Number Field (PLIST-01)**
- D-01: Replace `<select name="question_number">` with `<input type="text" name="question_number">`. No browser constraints (no `min`, `max`, `pattern`, or `type="number"`). FastAPI already coerces to `int`; it returns 422 if the value is unparseable.
- D-02: Placeholder and label stay the same. Default value behavior: the old select defaulted to "1" — the text input should pre-fill with "1" for the same UX.

**Docket Pill Input (PLIST-02)**
- D-03: Extract a shared `DocketPillInput.svelte` sub-component from `ArgumentDetailsCard.svelte`. It encapsulates: pill `$state`, Enter-key add handler, remove handler, hidden `<input type="hidden" name="docket[]" value="...">` per pill, and the pill display + remove button UI.
- D-04: `ArgumentDetailsCard.svelte` is refactored to import and use `DocketPillInput.svelte` instead of its current inline pill logic. Behavior must be identical post-refactor.
- D-05: The New Run form's `+page.svelte` imports and uses `DocketPillInput.svelte` for the docket field. The component renders inside the existing `<form method="POST" enctype="multipart/form-data">` — no nested form issues.
- D-06: `DocketPillInput.svelte` accepts at minimum an `initialValues: string[]` prop and a `name` prop (default `"docket[]"`). The New Run form passes `initialValues={[]}` (empty on load).

**Multi-Docket Submission for New Runs**
- D-07: When operator enters multiple docket pills and clicks "Start Run", the SvelteKit server action uses the **first pill** as `primary_docket` (sent to FastAPI `POST /api/admin/jobs`) and **immediately PATCHes** the new argument with all remaining pills after the run is created. This requires a second round-trip in the action before redirecting to `/admin/pipeline/{id}`.
- D-08: The duplicate preflight check fires for **every pill** before submit. If any `(docket, question_number)` pair matches an existing argument, the warning banner shows. The existing `check-duplicate` endpoint is called once per pill.
- D-09: The `duplicateWarning` state should show which specific docket triggered the warning.

**Runs Table (PLIST-03)**
- D-10: Remove the `limit` from `list_jobs` service call entirely (pass `limit=None` or remove the `.limit()` clause). API endpoint signature: `limit` param removed or made optional and defaulting to no limit.
- D-11: Section heading changes from "Recent Runs" to "All Runs".
- D-12: No pagination UI. Single query, all rows.

**Compound Status Badge (PLIST-05)**
- D-13: Status column badge becomes compound label combining `current_step` and `status`. Format: `"{Step} · {status_label}"` when step is active, or just `"{status_label}"` when Completed.
- D-14: The separate "Step" column is **removed** from the table.
- D-15: `badgeLabel()` updated to accept both `status` and `current_step`. `badgeStyle()` remains driven by `status` alone.
- D-16: When `current_step` is null (pending state before ingest starts), the badge shows just the status label ("Pending").

### Claude's Discretion
- Whether the `DocketPillInput.svelte` `name` prop defaults to `"docket[]"` or is required
- Exact props interface for `DocketPillInput.svelte` beyond `initialValues` and `name`
- How to PATCH additional dockets onto the new argument after run creation
- Whether preflight pill checks fire in parallel (Promise.all) or sequentially

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLIST-01 | Question number: free text field replacing 2-option dropdown | D-01/D-02: replace `<select>` with `<input type="text">`, default "1", no constraints. FastAPI `question_number: int = Form(1)` already coerces. |
| PLIST-02 | Docket input: pill/tag UI with multi-docket support | D-03–D-09: extract `DocketPillInput.svelte` from `ArgumentDetailsCard.svelte`; server action reads `docket[]` multi-value; first pill → primary_docket; remainder → PATCH via `MetadataUpdate.source_dockets` |
| PLIST-03 | Runs table shows all pipeline runs (not just recent 10) | D-10–D-12: remove `limit=10` from `list_jobs()` service call and `GET /api/admin/jobs` router call |
| PLIST-04 | "Show incomplete only" toggle retained | Already fully implemented — no changes needed |
| PLIST-05 | Status badges show stage + status (compound) | D-13–D-16: update `badgeLabel(status, currentStep)` in `+page.svelte`; remove Step column |
</phase_requirements>

---

## Summary

Phase 24 is a targeted four-change update to `/admin/pipeline/` (the pipeline list page). All changes are self-contained within the frontend and backend files that already exist; no new API endpoints, Alembic migrations, or database schema changes are required.

The largest structural change is extracting `DocketPillInput.svelte` from `ArgumentDetailsCard.svelte`. This is a pure extraction refactor — the exact pill state, Enter-key handler, hidden input pattern, and pill display markup move verbatim into a new shared component. `ArgumentDetailsCard.svelte` then imports and uses the component with `initialValues={savedValues.dockets}` and `readonly={readonly}`. Behavior must be identical post-extraction; the refactor is the most regression-prone part of the phase.

The multi-docket server action logic in `+page.server.ts` introduces a two-request pattern: the form action calls `POST /api/admin/jobs` with the first pill as `primary_docket`, then immediately calls `PATCH /api/admin/arguments/{id}/metadata` with a `MetadataUpdate` body containing `source_dockets: [all pills]` before redirecting. This is only needed when more than one pill was entered. The `MetadataUpdate` schema and `update_argument_metadata` service already support `source_dockets: list[str]` (added in Phase 23). The backend limit removal (`list_jobs(db, limit=10, ...)` → no limit) is a two-line change in the service and router.

**Primary recommendation:** Implement in five distinct tasks: (1) create `DocketPillInput.svelte`, (2) refactor `ArgumentDetailsCard.svelte` to use it, (3) update `+page.svelte` (pill input, question text field, compound badge, section rename, Step column removal), (4) update `+page.server.ts` (multi-docket action with PATCH round-trip, multi-pill preflight), (5) remove `limit=10` from backend service and router.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pill UI state (add/remove/display) | Browser / Client (Svelte component) | — | Pure client-side reactive state; serialized to form via hidden inputs at submit time |
| Hidden input serialization of pills | Browser / Client (form) | — | Standard HTML multi-value form fields; SvelteKit reads them server-side |
| Duplicate preflight check | Browser / Client (fetch before submit) | Frontend Server (proxy endpoint) | Client initiates; SK server `/admin/pipeline/check-duplicate` proxies to FastAPI with token |
| Multi-docket PATCH round-trip | Frontend Server (`+page.server.ts` action) | API / Backend (FastAPI) | Action owns orchestration: POST job → PATCH remaining dockets → redirect |
| Job listing (all rows) | API / Backend (FastAPI) | Database / Storage (Postgres) | Remove `.limit(10)` from SQLAlchemy query in `list_jobs()` |
| Compound badge logic | Browser / Client (`badgeLabel()` in `+page.svelte`) | — | Pure view-layer transform; `AdminJobResponse` already provides `status` and `current_step` |

---

## Standard Stack

### Core (all [VERIFIED: existing codebase — directly read])

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| SvelteKit 2.x / Svelte 5 Runes | project-locked | Frontend framework + SSR | Project mandate in CLAUDE.md; `$state`, `$derived`, `$effect` exclusively |
| FastAPI 0.115+ | project-locked | Backend API | Project mandate; provides `Form()` parameter coercion |
| SQLAlchemy 2.0 async | project-locked | ORM for Postgres queries | Project mandate; all DB writes use `.execution_options(synchronize_session=False)` |

### No New Dependencies

This phase introduces zero new npm or Python packages. All UI patterns and backend changes use existing project infrastructure.

---

## Package Legitimacy Audit

No external packages are installed in this phase. This section is not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
  │
  ├── [Pills state] ──→ $state array in DocketPillInput.svelte
  │                      └── hidden inputs (name="docket[]") serialize at submit
  │
  ├── [Form submit] ──→ handleSubmit() in +page.svelte
  │                      └── preflight: GET /admin/pipeline/check-duplicate?docket=X&question=Y
  │                          (one call per pill, sequential)
  │                          ├── match found → show duplicateWarning banner
  │                          └── all clear → formEl.requestSubmit()
  │
  ├── [Form POST] ──→ +page.server.ts actions.default
  │                   ├── reads: docket[] (FormData.getAll), question_number, mode
  │                   ├── sends: POST /api/admin/jobs { primary_docket: pills[0], question_number }
  │                   ├── if pills.length > 1:
  │                   │     PATCH /api/admin/arguments/{new_arg_id}/metadata
  │                   │     { source_dockets: [...all pills] }
  │                   └── redirect 303 → /admin/pipeline/{job.id}
  │
  └── [Page load] ──→ +page.server.ts load()
                       └── GET /api/admin/jobs  (no limit param)
                            └── list_jobs(db, incomplete=flag)  ← no .limit()
                                 └── SELECT AdminJob ORDER BY created_at DESC
```

### Recommended Project Structure

No structural changes — all files already exist. New file:

```
app/src/lib/components/
  DocketPillInput.svelte     ← NEW: extracted from ArgumentDetailsCard.svelte
  ArgumentDetailsCard.svelte ← MODIFIED: imports DocketPillInput

app/src/routes/admin/pipeline/
  +page.svelte               ← MODIFIED: DocketPillInput, text question, compound badge
  +page.server.ts            ← MODIFIED: multi-docket action, PATCH round-trip

api/routers/admin.py         ← MODIFIED: remove limit=10 from list_jobs call
api/services/admin_jobs.py   ← MODIFIED: remove limit param from list_jobs()
```

### Pattern 1: DocketPillInput.svelte Component Interface

**What:** A self-contained Svelte 5 Runes component that manages a list of docket pill strings. Serializes state to the parent form via hidden inputs.
**When to use:** Any form that needs multi-value docket input with pill UI.
**Example (extracted verbatim from ArgumentDetailsCard.svelte):** [VERIFIED: existing codebase]

```svelte
<script lang="ts">
  interface DocketPillInputProps {
    initialValues?: string[];  // default: []
    name?: string;             // default: "docket[]"
    readonly?: boolean;        // default: false
  }

  let {
    initialValues = [],
    name = 'docket[]',
    readonly = false
  }: DocketPillInputProps = $props();

  let pills = $state<string[]>(initialValues);
  let docketInput = $state('');

  function addPill() {
    const v = docketInput.trim();
    if (v && !pills.includes(v)) {
      pills = [...pills, v];
    }
    docketInput = '';
  }

  function removePill(value: string) {
    pills = pills.filter((p) => p !== value);
  }
</script>

<!-- Hidden inputs — one per pill, serialized into parent form -->
{#each pills as pill}
  <input type="hidden" {name} value={pill} />
{/each}

<!-- Pill list -->
{#if pills.length > 0}
  <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
    {#each pills as pill}
      <span style="display: inline-flex; align-items: center; gap: 6px; background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 14px; color: #e2e8f0;">
        {pill}
        {#if !readonly}
          <button
            type="button"
            aria-label="Remove docket {pill}"
            onclick={() => removePill(pill)}
            style="min-width: 28px; min-height: 28px; background: transparent; border: none; cursor: pointer; font-size: 14px; color: #94a3b8;"
          >×</button>
        {/if}
      </span>
    {/each}
  </div>
{/if}

<!-- Text input -->
<input
  type="text"
  bind:value={docketInput}
  disabled={readonly}
  onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (!readonly) addPill(); } }}
  style="width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box; font-family: inherit;"
/>
```

**Critical note:** The component does NOT include a `<label>` — labels are rendered by the parent (either `ArgumentDetailsCard` or `+page.svelte`) because the label's `for` attribute must match an `id` on the input, and the parent controls the surrounding form layout. The planner must account for this: the `DocketPillInput` text input should expose an `id` prop or use a deterministic id so the parent's `<label for="...">` can target it. The current `ArgumentDetailsCard` uses `for="docket-input"` on its label and `id="docket-input"` on the input — either carry that id as a prop or embed a default in the component.

### Pattern 2: Multi-Pill Preflight in handleSubmit()

**What:** Sequential per-pill duplicate check before form submit. Current code checks a single `docketInput` text value; new code reads the serialized pill values from the form's hidden inputs.
**When to use:** When `pills.length > 0` and `preflightCleared === false`.

**Critical change:** The current `handleSubmit()` reads `docketInput` (the bound text box value). After the pill refactor, the text box is inside `DocketPillInput.svelte` and is no longer directly accessible from `+page.svelte`. The planner must decide how `handleSubmit()` reads the current pill list:

**Option A (recommended):** `DocketPillInput.svelte` exposes a `getPills(): string[]` method via Svelte 5 `$bindable` or a module export, and `+page.svelte` calls it. **Actually simpler:** read the hidden inputs directly from `formEl` at submit time:

```typescript
// In handleSubmit(), after pills exist:
const pillValues = [...(formEl.querySelectorAll('input[name="docket[]"]') as NodeListOf<HTMLInputElement>)]
  .map(i => i.value);
```

**Option B:** Lift pill state up into `+page.svelte` and pass it down as a prop. This makes the parent stateful again, which partially defeats the extraction purpose.

**Option C:** Expose the pills array from `DocketPillInput.svelte` via a `bind:pills` pattern (Svelte 5 `$bindable`).

**Recommendation:** Option A (read hidden inputs from formEl at submit time) — zero prop-drilling, works with the self-contained component model declared in D-03/D-05. [ASSUMED — designer discretion, no single canonical answer]

**Sequential preflight loop:**
```typescript
async function handleSubmit(e: SubmitEvent) {
  const pillValues = [...(formEl.querySelectorAll('input[name="docket[]"]') as NodeListOf<HTMLInputElement>)]
    .map(i => i.value);

  if (pillValues.length === 0 || preflightCleared) {
    submitting = true;
    return;
  }

  e.preventDefault();

  for (const docket of pillValues) {
    try {
      const res = await fetch(
        `/admin/pipeline/check-duplicate?docket=${encodeURIComponent(docket)}&question=${encodeURIComponent(questionInput)}`
      );
      if (!res.ok) { preflightCleared = true; (e.target as HTMLFormElement).requestSubmit(); return; }
      const data = await res.json();
      if (data.exists) {
        duplicateWarning = { argumentId: data.argument_id, docket, question: questionInput };
        return;  // stop on first match
      }
    } catch {
      preflightCleared = true;
      (e.target as HTMLFormElement).requestSubmit();
      return;
    }
  }
  preflightCleared = true;
  (e.target as HTMLFormElement).requestSubmit();
}
```

Note: `questionInput` is still needed as a reactive `$state` variable bound to the new text input for question number (replacing the select). The variable name and binding pattern stay the same; only the HTML element changes.

### Pattern 3: Multi-Docket Server Action with PATCH Round-Trip

**What:** After creating the job, if more than one docket pill was submitted, PATCH the new argument to persist all dockets via `MetadataUpdate.source_dockets`.
**When to use:** `dockets.length > 1` in the server action.

**Key facts from codebase audit:** [VERIFIED: existing codebase]

The `PATCH /api/admin/arguments/{argument_id}/metadata` endpoint already exists at `api/routers/admin.py` line 754. It accepts a `MetadataUpdate` body (JSON) with `source_dockets: list[str] | None`. The `update_argument_metadata` service already handles the full normalization and writes both `source_dockets` and `source_docket` (first element). The `AdminJobResponse` schema includes `argument_id: Optional[int]`.

**Landmine — timing:** After `POST /api/admin/jobs`, the response includes `id` (job id) but `argument_id` is `None` at this point. The argument is created by the ingest subprocess, not by the POST. This means the PATCH round-trip in the server action **cannot use `job.argument_id`** — it is null immediately after job creation.

**Resolution:** The additional dockets CANNOT be PATCHed immediately after job creation because the argument doesn't exist yet. The planner must recognize this constraint and choose one of:

1. **Store the extra dockets on the AdminJob itself** (requires schema change — out of scope for this phase)
2. **Pass all dockets as CLI args to the ingest subprocess** — already passes `--primary-docket`; could pass `--additional-dockets` (requires pipeline change — out of scope)
3. **Redirect to job detail page immediately** with the additional pill values as URL params, then have the job detail page PATCH when the argument is ready (complex coordination)
4. **Accept that multi-docket entry on the New Run form only sends the first docket at run creation time**; the operator adds additional dockets on the job detail page's ArgumentDetailsCard (which already supports multi-docket via Phase 23) once the argument exists.

**Conclusion:** D-07 as stated (PATCH remaining pills immediately after run creation) is **not implementable** because `argument_id` is null at job creation time — the argument doesn't exist yet. The CONTEXT.md decision D-07 must be flagged to the user. The planner should implement: first pill → `primary_docket` only; redirect to job detail. The job detail's `ArgumentDetailsCard` (Phase 23, already complete) handles adding remaining dockets after the argument is created. This is a constraint the planner must surface as a `checkpoint:human-verify` before proceeding with D-07 implementation. [VERIFIED: existing codebase — AdminJobResponse.argument_id = None after creation]

### Pattern 4: Compound Badge — badgeLabel() Update

**What:** `badgeLabel(status, currentStep)` produces a compound label.
**Current code:** [VERIFIED: existing codebase]

```typescript
function badgeLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: 'Pending', running: 'Running', completed: 'Completed',
    paused: 'Needs review', failed: 'Failed',
  };
  return labels[status] ?? status;
}
```

**New signature and logic:**
```typescript
function badgeLabel(status: string, currentStep: string | null | undefined): string {
  const statusLabels: Record<string, string> = {
    pending: 'Pending', running: 'Running', completed: 'Completed',
    paused: 'Needs Review', failed: 'Failed',
  };
  const stepLabels: Record<string, string> = {
    ingest: 'Ingest', parse: 'Parse', resolve: 'Resolve',
  };
  const statusLabel = statusLabels[status] ?? status;
  if (status === 'completed' || !currentStep) {
    return statusLabel;
  }
  const stepLabel = stepLabels[currentStep] ?? currentStep;
  return `${stepLabel} · ${statusLabel}`;
}
```

**Usage in template:** `badgeLabel(job.status, job.current_step)`

Note: "Needs review" in current code vs. "Needs Review" in CONTEXT.md D-15 — the UI-SPEC badge table shows "Resolve · Needs Review" (capital R). This is a minor inconsistency; the planner should pick one and be consistent. UI-SPEC is authoritative for display text.

### Pattern 5: Removing the limit from list_jobs

**Current service signature:** [VERIFIED: existing codebase]
```python
async def list_jobs(
    db: AsyncSession, limit: int = 10, incomplete: bool = False
) -> list[AdminJob]:
    ...
    query = query.order_by(AdminJob.created_at.desc()).limit(limit)
```

**New service signature (two approaches):**

*Approach A — remove limit entirely:*
```python
async def list_jobs(
    db: AsyncSession, incomplete: bool = False
) -> list[AdminJob]:
    ...
    query = query.order_by(AdminJob.created_at.desc())  # no .limit()
```

*Approach B — make limit optional with None:*
```python
async def list_jobs(
    db: AsyncSession, limit: int | None = None, incomplete: bool = False
) -> list[AdminJob]:
    ...
    if limit is not None:
        query = query.limit(limit)
    query = query.order_by(AdminJob.created_at.desc())
```

**Router change (either approach):** [VERIFIED: existing codebase, admin.py line 266]
```python
# Before:
return await jobs_service.list_jobs(db, limit=10, incomplete=incomplete)

# After (Approach A):
return await jobs_service.list_jobs(db, incomplete=incomplete)
```

Approach A is cleaner; Approach B preserves flexibility for future pagination. D-10 says "remove the limit entirely" — Approach A aligns with that.

**Router docstring update:** The docstring on `GET /api/admin/jobs` still says "Return the 10 most recent pipeline jobs" — update to "Return all pipeline jobs, newest first."

### Anti-Patterns to Avoid

- **Nested forms:** Do not put `<DocketPillInput>` inside the `ArgumentDetailsCard`'s own `<form>` if that causes double-form nesting in the New Run page. The component is placed inside the already-existing `<form>` in `+page.svelte`; `ArgumentDetailsCard` has its own `use:enhance` form which is correct for the job detail page. No nesting issue exists in the list page.
- **Resetting pill state on form enhance:** `ArgumentDetailsCard`'s `enhance` callback uses `update({ reset: false })` on success to preserve pill state (Phase 23 T-23 pattern). This MUST remain after the refactor — if the pill state moves to `DocketPillInput.svelte`, the `reset: false` in `ArgumentDetailsCard` still applies at the form level.
- **Assuming argument_id exists immediately after job creation:** As documented in Pattern 3, `argument_id` is null on the `AdminJobResponse` returned by `POST /api/admin/jobs`. Any logic that reads `job.argument_id` immediately after creation will get null.
- **Reading pills via docketInput binding in handleSubmit:** After extraction, `docketInput` in `+page.svelte` will be gone (it moves into `DocketPillInput.svelte`). The handleSubmit function must read pills from the form's hidden inputs instead.
- **Paused → "Needs review" vs "Needs Review" case inconsistency:** Current code has lowercase "r" in "Needs review". UI-SPEC uses "Needs Review" (capital R) in badge examples. Pick one; UI-SPEC is authoritative.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duplicate check endpoint | Custom fetch logic | Existing `/admin/pipeline/check-duplicate` SvelteKit server route | Already proxies to FastAPI with token injection; same-origin, no CORS |
| Multi-docket PATCH | New endpoint | Existing `PATCH /api/admin/arguments/{id}/metadata` with `source_dockets` field | `MetadataUpdate.source_dockets` fully implemented in Phase 23; service handles normalize + dedup |
| Pill UI | Custom tag input library | Extract from `ArgumentDetailsCard.svelte` | The exact implementation already exists and matches the design system |

---

## Runtime State Inventory

Not applicable — this is a UI/API update phase, not a rename or migration phase. No stored data, live service config, OS-registered state, secrets, or build artifacts need updating.

---

## Common Pitfalls

### Pitfall 1: argument_id is null after POST /api/admin/jobs

**What goes wrong:** D-07 says to PATCH remaining dockets immediately after creating the job. The `AdminJobResponse.argument_id` is `Optional[int]` and is `None` at creation time — the argument is created by the ingest subprocess, not the API POST.
**Why it happens:** The architecture deliberately separates job creation (instant) from argument creation (subprocess). `argument_id` is only set after ingest completes.
**How to avoid:** Do not attempt D-07 as literally stated. Redirect immediately after job creation; the operator uses `ArgumentDetailsCard` on the job detail page to add remaining dockets once the argument exists. Flag this to the user before planning.
**Warning signs:** Any server action code that reads `job.argument_id` and uses it immediately after `POST /api/admin/jobs` will get `None` and the subsequent PATCH will 404.

### Pitfall 2: pill $state lost on form submission / page navigation

**What goes wrong:** If `DocketPillInput.svelte` is used inside a form with `use:enhance` and the enhance callback calls `update()` (without `reset: false`), SvelteKit resets the form element, which destroys the Svelte component state.
**Why it happens:** SvelteKit's `enhance` helper resets the form DOM on success unless `reset: false` is passed.
**How to avoid:** `ArgumentDetailsCard`'s enhance callback already passes `update({ reset: false })` on success — this is a Phase 23 decision (T-23 pattern). The refactored version must not change this. For the New Run form in `+page.svelte`, the action redirects on success (303 redirect), so the form is never "reset" in place — not an issue there.
**Warning signs:** Pills disappear after a failed save attempt on the job detail page.

### Pitfall 3: Enter key submitting the form from the pill input

**What goes wrong:** The pill input's Enter key handler calls `addPill()`, but if `e.preventDefault()` is not called first, the keydown event bubbles and the form submits.
**Why it happens:** Enter in a text field inside a form triggers form submit by default.
**How to avoid:** `e.preventDefault()` must be called before `addPill()` in the `onkeydown` handler. This is already the pattern in `ArgumentDetailsCard.svelte` — carry it verbatim into `DocketPillInput.svelte`.
**Warning signs:** Form submits on Enter instead of adding a pill.

### Pitfall 4: Preflight checks the text input value instead of the pill values

**What goes wrong:** Current `handleSubmit()` reads `docketInput` (bound to the text box). After refactor, `docketInput` is internal to `DocketPillInput.svelte` and is no longer in `+page.svelte` scope.
**Why it happens:** The bind is moved into the child component during extraction.
**How to avoid:** Read pills from `formEl.querySelectorAll('input[name="docket[]"]')` instead of from a bound variable.
**Warning signs:** Preflight always runs zero checks because `docketInput` is always empty; or TypeScript compile error because `docketInput` is undefined.

### Pitfall 5: Step column removal leaves misaligned table headers

**What goes wrong:** The Step `<th>` and Step `<td>` cells are removed but the fourth column (View link) still exists — the table has three columns after removal: Status | Created | (View). If only the Step `<th>` is removed but Step `<td>` is left, columns desync.
**Why it happens:** Two separate edits required: remove the `<th>` in `<thead>` AND remove the `<td>` in `{#each data.jobs as job}`.
**How to avoid:** Remove both the `<th scope="col">Step</th>` and the corresponding `<td>` that renders `{job.current_step ?? '—'}`. Verify column count matches after change.
**Warning signs:** Table headers don't align with data columns.

### Pitfall 6: "Needs review" vs "Needs Review" case inconsistency

**What goes wrong:** Current `badgeLabel()` returns "Needs review" (lowercase r). The UI-SPEC and CONTEXT.md show "Needs Review" (capital R) in the compound badge example "Resolve · Needs Review".
**Why it happens:** Inconsistency between the current implementation and the new spec.
**How to avoid:** Update to "Needs Review" (capital R) consistently in `badgeLabel()` when implementing D-15. The `badgeStyle()` function uses the status key `paused` (not the label), so no change needed there.

---

## Code Examples

### Current list_jobs service call (to remove limit): [VERIFIED: existing codebase]

`api/routers/admin.py` line 266:
```python
return await jobs_service.list_jobs(db, limit=10, incomplete=incomplete)
```

`api/services/admin_jobs.py` line 198–222:
```python
async def list_jobs(
    db: AsyncSession, limit: int = 10, incomplete: bool = False
) -> list[AdminJob]:
    query = select(AdminJob)
    if incomplete:
        query = query.where(...)
    query = query.order_by(AdminJob.created_at.desc()).limit(limit)
    result = await db.execute(query)
    ...
```

### check-duplicate endpoint signature (confirmed): [VERIFIED: existing codebase]

SvelteKit proxy: `GET /admin/pipeline/check-duplicate?docket=X&question=Y`
FastAPI backend: `GET /api/admin/arguments/check-duplicate?docket=X&question=Y` (int coercion on `question`)

Returns: `{ "exists": boolean, "argument_id": number | null }`

The SvelteKit proxy is at `app/src/routes/admin/pipeline/check-duplicate/+server.ts`. The `question` param is forwarded as a string; FastAPI coerces to `int` via the `question: int` query param declaration. One call per pill needed.

### MetadataUpdate schema for multi-docket PATCH: [VERIFIED: existing codebase]

```python
class MetadataUpdate(BaseModel):
    case_name: Optional[str] = None
    source_docket: Optional[str] = None
    source_dockets: Optional[list[str]] = None  # Phase 23 D-MULTI-DOCKET
    argued_date: Optional[str] = None
    question_number: Optional[str] = None
```

Send as JSON `Content-Type: application/json` with `source_dockets: [...all pills]`. Service writes both `source_dockets` and `source_docket` (first element). But see Pitfall 1 — this PATCH can only happen when `argument_id` is known (not null).

### AdminJobResponse fields relevant to Phase 24: [VERIFIED: existing codebase]

```python
class AdminJobResponse(BaseModel):
    id: int
    status: AdminJobStatus          # "pending"|"running"|"paused"|"completed"|"failed"
    current_step: Optional[AdminJobStep] = None  # "ingest"|"parse"|"resolve"|null
    argument_id: Optional[int] = None            # null at creation time
    created_at: datetime.datetime
    updated_at: datetime.datetime
    # ... other fields not used on list page
```

Both `status` and `current_step` are already returned by `GET /api/admin/jobs` — no API schema changes needed for the compound badge.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single docket text input | Multi-docket pill input | Phase 24 (this phase) | Consolidated arguments need multiple dockets; Phase 23 added the same UI to the job detail page |
| "Recent Runs" (limit 10) | "All Runs" (no limit) | Phase 24 (this phase) | Operators need full history visibility |
| Separate Status + Step columns | Compound badge, Step column removed | Phase 24 (this phase) | One column carries complete step+status context |
| `<select>` question number | Free-text question number | Phase 23 (job detail) → Phase 24 (list page) | Allows Q3, Q4, etc. without code changes; FastAPI validates as int |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reading pills via `formEl.querySelectorAll('input[name="docket[]"]')` in `handleSubmit()` is the cleanest approach for keeping `DocketPillInput.svelte` self-contained | Pattern 2 | If wrong, alternative is `$bindable` or lifting state — more prop-drilling but still implementable |
| A2 | D-07 (PATCH remaining dockets immediately after job creation) is not implementable as stated because `argument_id` is null at creation time | Pattern 3 / Pitfall 1 | If wrong (e.g. FastAPI creates the argument synchronously now), the PATCH would work — but the code audit shows `argument_id` starts null |

---

## Open Questions

1. **D-07 conflict with null argument_id**
   - What we know: `argument_id` is `None` on `AdminJobResponse` immediately after `POST /api/admin/jobs`. The argument is created by the async ingest subprocess.
   - What's unclear: Does the CONTEXT.md decision D-07 intend for the PATCH to happen on the server action (impossible with current architecture) or was this an oversight?
   - Recommendation: Flag to user before planning. The safe fallback is: New Run form submits first pill only; operator adds remaining dockets via `ArgumentDetailsCard` on the job detail page after the argument is created. This is already fully supported by Phase 23 infrastructure.

2. **DocketPillInput label/id pattern**
   - What we know: The component should not include a `<label>` (parent owns layout), but the parent needs to associate a `<label for="...">` with the component's text input.
   - What's unclear: Whether to expose an `id` prop on `DocketPillInput.svelte` or hardcode a default.
   - Recommendation: Add an `id` prop with a default value (e.g., `"docket-input"`) so the parent's `<label for="docket-input">` works. The list page can use a different id if needed to avoid conflicts.

---

## Environment Availability

Step 2.6: SKIPPED — this phase makes changes to existing SvelteKit and FastAPI files. No new external tools, services, CLIs, or runtimes are required.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | FastAPI `question_number: int = Form(1)` coerces and validates; `docket` strings stored as-is (operator-entered, no injection surface) |
| V4 Access Control | Yes (unchanged) | All `/api/admin/*` routes protected by `verify_admin_token` dependency; SvelteKit proxy injects token server-side (no client exposure) |
| V2 Authentication | No (unchanged) | Token check already in place; this phase does not change auth |

No new attack surface introduced. The multi-pill preflight calls the existing same-origin SvelteKit proxy endpoint — no new client-to-FastAPI paths, no new form fields that bypass existing validation.

---

## Sources

### Primary (HIGH confidence)
- `app/src/routes/admin/pipeline/+page.svelte` — full file read; current select, docket input, badgeLabel/badgeStyle, table columns documented
- `app/src/routes/admin/pipeline/+page.server.ts` — full file read; form action, primary_docket single-value read, load function documented
- `app/src/lib/components/ArgumentDetailsCard.svelte` — full file read; pill state, addPill, removePill, hidden inputs, enhance callback documented
- `api/routers/admin.py` — full file read; list_jobs call with limit=10, check-duplicate signature, metadata PATCH endpoint confirmed
- `api/services/admin_jobs.py` — full file read; list_jobs(limit=10) signature, AdminJob creation, argument_id=None at creation confirmed
- `api/schemas/admin_jobs.py` — full file read; AdminJobResponse.status and current_step types confirmed
- `api/services/admin_arguments.py` — full file read; update_argument_metadata with source_dockets support confirmed
- `api/schemas/admin_arguments.py` — full file read; MetadataUpdate.source_dockets field confirmed
- `app/src/routes/admin/pipeline/check-duplicate/+server.ts` — full file read; endpoint signature, query params, proxy pattern confirmed
- `api/models/models.py` — AdminJobStatus and AdminJobStep enum values confirmed

### Secondary (MEDIUM confidence)
- `.planning/phases/24-pipeline-list-page/24-CONTEXT.md` — phase decisions and constraints
- `.planning/phases/24-pipeline-list-page/24-UI-SPEC.md` — visual contract and interaction spec

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all files read directly from codebase
- Architecture: HIGH — all integration points verified against actual code
- Pitfalls: HIGH — Pitfall 1 (null argument_id) verified against AdminJobResponse schema and job creation flow; all others from direct code reading
- D-07 implementability: HIGH (verified impossible as stated) — the open question is flagged for user decision

**Research date:** 2026-07-06
**Valid until:** 2026-08-06 (stable codebase; no fast-moving external dependencies)
