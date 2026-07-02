# Phase 21: Admin UI Surface - Research

**Researched:** 2026-07-01
**Domain:** SvelteKit admin UI, FastAPI delete endpoints, SQLAlchemy multi-table delete
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Delete Confirmation Flow**
- D-01: Both argument delete and job delete use an inline two-step reveal: first click changes the button to show "Confirm delete" + "Cancel"; second click submits the form action. No navigation, no modal, no `confirm()` dialog. Uses the existing `$state`-driven pattern (`deleteSubmitting`) from the people editor.
- D-02: The confirmation buttons replace the original delete button in-place — no layout shift or new elements stacking.

**Argument Delete (ADMIN-01)**
- D-03: Delete button lives on the argument edit page (`/admin/arguments/[id]`) only.
- D-04: Delete is blocked if `argument.status === 'published'` (i.e., `published_at IS NOT NULL`).
- D-05: `can_delete` flag computed in `+page.server.ts` and gates the delete button.
- D-06: After successful delete, redirect to `/admin/arguments`.
- D-07: Argument delete cascades: argument row + all linked `pipeline_runs` + all `utterances` from those runs + `argument_participants` + `case_arguments` join rows. The admin_job that birthed this argument either gets cascade-deleted or becomes an orphan reference — FK cascade behavior must be confirmed in the DB.
- D-08: Argument delete is independent of job state — only `argument.status` matters.

**Pipeline Run Delete (ADMIN-02)**
- D-09: Delete button lives on the job detail page (`/admin/pipeline/[job_id]`) only.
- D-10: CRITICAL mental model: Deleting a pipeline run MUST NOT delete or affect the linked argument, its pipeline_run step rows, or its utterances.
- D-11: Deleting an admin_job deletes ONLY the admin_job row. No cascade into pipeline_run step rows, utterances, or the argument.
- D-12: After successful delete, redirect to `/admin/pipeline`.
- D-13: If the argument produced by a bad run has bad utterances, operator uses ADMIN-01 (delete argument) to clean everything up.

**Admin Sub-Navigation (NAV-02)**
- D-14: When in any `/admin/*` route (except `/admin/login`), the layout renders two nav rows: Row 1 = `<TopNav variant="public" />`; Row 2 = new `<AdminSubNav />`.
- D-15: `TopNav.svelte` is NOT modified.
- D-16: `AdminSubNav` is a new component at `app/src/lib/components/AdminSubNav.svelte`.
- D-17: AdminSubNav background: `#1e293b`; `border-bottom: 1px solid #334155`; `padding: 12px 24px`.
- D-18: Logout button in AdminSubNav row, right-aligned.
- D-19: The `variant="admin"` prop and its associated branch in `TopNav.svelte` can be removed if it becomes dead code — confirm before removing.

### Claude's Discretion

None explicitly delegated; all major decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADMIN-01 | Operator can delete a mis-created argument from the admin UI (with confirmation; blocked if argument has published utterances) | FK cascade order confirmed; service function pattern identified from people delete |
| ADMIN-02 | Operator can delete a pipeline run from the admin UI (with confirmation) | AdminJob-only delete pattern confirmed; argument data is unaffected |
| NAV-02 | Admin header navigation unified with public navigation in style and component structure | TopNav.svelte dead-code analysis complete; AdminSubNav design contract from UI-SPEC |
</phase_requirements>

---

## Summary

Phase 21 delivers three targeted changes to the admin UI: argument delete (ADMIN-01), pipeline run delete (ADMIN-02), and admin sub-navigation unification (NAV-02). All three are pure UI + service-layer additions — no database schema changes, no Alembic migrations, no new external dependencies.

The codebase already has a complete, working delete pattern in the people editor (`admin/people/[id]/+page.svelte` and `+page.server.ts`). Phase 21 follows that pattern exactly for both delete flows, with one extension: the people editor submits on first click, but Phase 21 requires a two-step confirm (`deleteConfirming` state) before the form submits.

The FK cascade order for argument delete is the most technically significant detail. SQLAlchemy ORM models have no `cascade=` relationship declarations — all FK rows must be deleted manually in dependency order via explicit `delete()` statements in the new service function. The correct deletion sequence is: `utterances` (references `pipeline_runs` AND `arguments`) → `pipeline_runs` (references `arguments`) → `argument_participants` (references `arguments`) → `case_arguments` (references `arguments`) → `arguments`. The `admin_jobs.argument_id` FK is nullable and points TO `arguments`, so deleting the argument leaves admin_job rows with a NULL argument_id reference — this is acceptable because admin_job is the child, not the parent.

For nav unification (NAV-02): `variant="admin"` appears in exactly one file (`admin/+layout.svelte` line 9). After replacing it with `<TopNav variant="public" /><AdminSubNav />`, the `variant="admin"` code path in `TopNav.svelte` becomes completely dead. D-19 permits removing it, but the planner should include it as a cleanup task at the end.

**Primary recommendation:** Implement in three plans — (1) argument delete service + endpoint + UI, (2) job delete endpoint + UI, (3) AdminSubNav component + layout change + TopNav cleanup. Plans 1 and 2 can be parallelized; plan 3 is independent.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Argument delete guard (`can_delete`) | API / Backend | Frontend Server (SvelteKit load) | Status check belongs server-side; load function reads from FastAPI and passes flag to component |
| Argument cascade delete | API / Backend | — | SQLAlchemy multi-table delete in service function; router exposes DELETE endpoint |
| Job delete (admin_job only) | API / Backend | — | Single-row delete; no cascade needed |
| Two-step confirm UI state | Browser / Client | — | `$state` in `.svelte` component; no server round-trip until second click |
| Post-delete redirect | Frontend Server (SvelteKit action) | — | `throw redirect(303, ...)` in `+page.server.ts` form action |
| AdminSubNav rendering | Frontend Server (SSR layout) | — | Layout-level decision; `page.url.pathname` check already in `admin/+layout.svelte` |

---

## Standard Stack

### Core

No new packages required. All implementation uses existing stack.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit 2.x / Svelte 5 | already installed | Form actions, `$state`, `use:enhance` | Project constraint |
| FastAPI 0.115+ | already installed | DELETE endpoints | Project constraint |
| SQLAlchemy 2.0 async | already installed | Multi-table cascade delete | Project constraint |

### Supporting

None — this phase uses only existing capabilities.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual FK delete sequence | SQLAlchemy `cascade="all, delete-orphan"` on relationships | Relationships are not declared in models.py — adding them now would require testing all existing code paths; manual delete is safer and follows the pattern established in `delete_person_if_orphan` |
| Two `$state` variables (`deleteConfirming` + `deleteSubmitting`) | Single state machine | Two booleans is the simplest approach and matches the existing codebase idiom |

**Installation:** No new packages.

---

## Package Legitimacy Audit

Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
      │
      │ (1) GET /admin/arguments/[id]
      ▼
SvelteKit +page.server.ts (load)
      │ FASTAPI_BASE_URL/api/admin/arguments/{id}
      ▼
FastAPI GET /api/admin/arguments/{id}
      │ → ArgumentDetail (includes argument.status)
      ▼
+page.server.ts assembles can_delete = (status !== 'published')
      │ → data.can_delete, data.argument passed to component
      ▼
+page.svelte renders delete card
      │ (2a) First click → deleteConfirming = true (no fetch)
      │ (2b) Second click → form POST ?/delete (use:enhance)
      ▼
SvelteKit +page.server.ts (delete action)
      │ FASTAPI_BASE_URL DELETE /api/admin/arguments/{id}
      ▼
FastAPI DELETE /api/admin/arguments/{id}
      │ → arguments_service.delete_argument(db, id)
      ▼
PostgreSQL: DELETE utterances → DELETE pipeline_runs
           → DELETE argument_participants → DELETE case_arguments
           → DELETE arguments
      │ → {"deleted": True}
      ▼
throw redirect(303, '/admin/arguments')
```

For job delete:
```
Operator → POST ?/delete → FastAPI DELETE /api/admin/jobs/{id}
         → admin_jobs_service.delete_job(db, id)
         → DELETE admin_jobs WHERE id = {id}   (single row)
         → {"deleted": True}
         → redirect to /admin/pipeline
```

For AdminSubNav:
```
admin/+layout.svelte
  ├── {#if page.url.pathname !== '/admin/login'}
  │     <TopNav variant="public" />    ← unchanged
  │     <AdminSubNav />                ← new
  └── {/if}
  {@render children()}
```

### Recommended Project Structure

No new directories required. New files:

```
app/src/lib/components/
└── AdminSubNav.svelte       ← new component (D-16)

api/services/
└── admin_arguments.py       ← add delete_argument() function
└── admin_jobs.py            ← add delete_job() function

api/routers/
└── admin.py                 ← add DELETE /arguments/{id}, DELETE /jobs/{id}

app/src/routes/admin/
└── +layout.svelte           ← switch to TopNav public + AdminSubNav
└── arguments/[id]/+page.svelte       ← add delete section
└── arguments/[id]/+page.server.ts   ← add delete action + can_delete in load
└── pipeline/[job_id]/+page.svelte   ← add delete section
└── pipeline/[job_id]/+page.server.ts ← add delete action
```

### Pattern 1: Two-Step Inline Delete Confirm (Svelte 5 Runes)

**What:** First click on delete button toggles `deleteConfirming = true`; second click submits the form action. Cancel resets to initial state.

**When to use:** Both ADMIN-01 and ADMIN-02 delete sections.

**Example — component Svelte state and template structure:**
```typescript
// Source: inferred from admin/people/[id]/+page.svelte delete section + UI-SPEC D-01/D-02
let deleteConfirming = $state(false);
let deleteSubmitting = $state(false);
```

```html
<!-- Source: UI-SPEC Interaction Contract + CONTEXT.md D-01/D-02 -->
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
  <h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
    Danger Zone
  </h2>

  {#if data.can_delete}
    {#if deleteConfirming}
      <!-- Two-button row replacing the delete button in-place (D-02) -->
      <div style="display: flex; gap: 8px;">
        <form method="POST" action="?/delete" style="flex: 1;"
          use:enhance={() => {
            deleteSubmitting = true;
            return async ({ update }) => { deleteSubmitting = false; await update(); };
          }}
        >
          <button type="submit" disabled={deleteSubmitting}
            style="display: block; width: 100%; min-height: 44px; background: transparent;
                   border: 1px solid #ef4444; border-radius: 6px; font-size: 16px;
                   font-weight: 600; color: #ef4444; cursor: pointer;
                   opacity: {deleteSubmitting ? 0.7 : 1};">
            {deleteSubmitting ? 'Deleting…' : 'Confirm delete'}
          </button>
        </form>
        <button type="button" onclick={() => { deleteConfirming = false; }}
          style="flex: 1; min-height: 44px; background: transparent;
                 border: 1px solid #334155; border-radius: 6px; font-size: 16px;
                 font-weight: 400; color: #94a3b8; cursor: pointer;">
          Cancel
        </button>
      </div>
    {:else}
      <button type="button" onclick={() => { deleteConfirming = true; }}
        style="display: block; width: 100%; min-height: 44px; background: transparent;
               border: 1px solid #ef4444; border-radius: 6px; font-size: 16px;
               font-weight: 600; color: #ef4444; cursor: pointer;">
        Delete argument
      </button>
    {/if}
  {:else}
    <!-- Blocked state (argument only) -->
    <button disabled aria-describedby="delete-tip"
      style="display: block; width: 100%; min-height: 44px; background: transparent;
             border: 1px solid #334155; border-radius: 6px; font-size: 16px;
             font-weight: 600; color: #94a3b8; cursor: not-allowed; opacity: 0.7;">
      Delete argument
    </button>
    <p id="delete-tip" style="font-size: 14px; color: #94a3b8; margin-top: 8px; text-align: center;">
      Published arguments cannot be deleted. Unpublish first.
    </p>
  {/if}
</div>
```

**Key difference from people editor:** People editor uses a single submit-on-first-click form. This phase adds `deleteConfirming` as a gate before the form is submitted.

### Pattern 2: FastAPI DELETE Endpoint (following people delete pattern)

**What:** DELETE endpoint returns 200 + `{"deleted": True}` on success, 404 on not found, 409 on blocked.

**When to use:** Both argument delete and job delete endpoints.

**Example — argument delete endpoint:**
```python
# Source: api/routers/admin.py lines 607-629 (people delete pattern)
@router.delete("/arguments/{argument_id}", status_code=200)
async def delete_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an argument only if it is not published (ADMIN-01).

    Returns 200 + {"deleted": True} on success.
    Returns 404 if the argument does not exist.
    Returns 409 if argument.status == 'published'.
    Auth inherited from router-level dependency.
    """
    result = await arguments_service.delete_argument(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    if result is False:
        raise HTTPException(
            status_code=409,
            detail="Published arguments cannot be deleted. Unpublish first.",
        )
    return {"deleted": True}
```

### Pattern 3: Multi-Table Cascade Delete (SQLAlchemy, no ORM relationships)

**What:** Manual DELETE sequence respecting FK constraint order.

**When to use:** Argument delete service function only. Job delete is a single-row delete.

**FK dependency order for argument delete:**
```
utterances.argument_id → arguments.id         (must delete first)
utterances.pipeline_run_id → pipeline_runs.id  (pipeline_runs cannot be deleted while utterances reference them)
pipeline_runs.argument_id → arguments.id       (after utterances deleted)
argument_participants.argument_id → arguments.id
case_arguments.argument_id → arguments.id
arguments.id                                   (last)
```

**admin_jobs.argument_id is a nullable FK pointing TO arguments.** After deleting the argument, admin_job rows whose argument_id referenced it will violate FK if PostgreSQL enforces it. Check: the FK is nullable (`nullable=True`) and the ORM model has no `ondelete=` clause — this means the default PostgreSQL FK behavior (RESTRICT/NO ACTION) applies. The FK must be NULLed before or the admin_job row deleted before the argument is deleted.

**Critical finding (D-07 confirmation):** `AdminJob.argument_id` is a nullable FK to `arguments.id` with NO `ondelete="CASCADE"` or `ondelete="SET NULL"` on the SQLAlchemy column definition. PostgreSQL will raise a FK constraint violation if the argument is deleted while any admin_job row still references it. The service function must either:
- SET argument_id = NULL on all admin_job rows referencing this argument before deleting, OR
- DELETE those admin_job rows before deleting the argument.

The CONTEXT.md D-07 says "The admin_job that birthed this argument either gets cascade-deleted or becomes an orphan reference — planning/research should confirm FK cascade behavior." The FK is NOT cascade-configured at the DB level. The service function must explicitly NULL the argument_id column on any admin_job rows referencing this argument before deleting the argument row.

**Service function example:**
```python
# Source: SQLAlchemy patterns from api/services/admin_people.py + models.py FK analysis
async def delete_argument(db: AsyncSession, argument_id: int) -> bool | None:
    """Delete an argument and all dependent data (ADMIN-01).

    Returns True on success, False if argument is published (409), None if not found (404).
    Deletion order (FK dependency):
      1. Utterances (references both pipeline_runs AND arguments)
      2. PipelineRuns (references arguments)
      3. ArgumentParticipants (references arguments)
      4. CaseArguments (references arguments)
      5. NULL out AdminJob.argument_id for any jobs referencing this argument
      6. Argument
    All delete() calls use .execution_options(synchronize_session=False).
    """
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        return False

    # Step 1: Delete utterances referencing this argument's pipeline runs
    await db.execute(
        delete(Utterance)
        .where(Utterance.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 2: Delete pipeline_run step rows for this argument
    await db.execute(
        delete(PipelineRun)
        .where(PipelineRun.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 3: Delete argument_participants
    await db.execute(
        delete(ArgumentParticipant)
        .where(ArgumentParticipant.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 4: Delete case_arguments join rows
    await db.execute(
        delete(CaseArgument)
        .where(CaseArgument.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 5: NULL out AdminJob.argument_id (FK not cascade-configured)
    await db.execute(
        update(AdminJob)
        .where(AdminJob.argument_id == argument_id)
        .values(argument_id=None)
        .execution_options(synchronize_session=False)
    )
    # Step 6: Delete the argument itself
    await db.execute(
        delete(Argument)
        .where(Argument.id == argument_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return True
```

### Pattern 4: AdminSubNav Component

**What:** New Svelte component mirroring the admin-variant nav links from TopNav.svelte.

**When to use:** Rendered in `admin/+layout.svelte` for all `/admin/*` routes except `/admin/login`.

**Example:**
```html
<!-- Source: TopNav.svelte lines 38-90 (admin variant branch), UI-SPEC Component Inventory -->
<!-- app/src/lib/components/AdminSubNav.svelte -->
<script lang="ts">
  // No props needed — links are hardcoded (same as TopNav admin variant)
</script>

<nav
  aria-label="Admin navigation"
  style="
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  "
>
  <a href="/admin/pipeline" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    Pipeline Runner
  </a>
  <a href="/admin/arguments" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    Arguments
  </a>
  <a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    People Editor
  </a>

  <form method="POST" action="/admin?/logout" style="margin-left: auto;">
    <button
      type="submit"
      style="min-height: 44px; font-size: 14px; font-weight: 400; color: #94a3b8;
             background: transparent; border: 1px solid #334155; border-radius: 6px;
             padding: 8px 16px; cursor: pointer;"
      onmouseenter={(e) => { const b = e.currentTarget as HTMLButtonElement; b.style.color = '#e2e8f0'; b.style.borderColor = '#e2e8f0'; }}
      onmouseleave={(e) => { const b = e.currentTarget as HTMLButtonElement; b.style.color = '#94a3b8'; b.style.borderColor = '#334155'; }}
    >
      Log out
    </button>
  </form>
</nav>
```

### Pattern 5: `can_delete` in Load Function (argument edit page)

**What:** Compute `can_delete` from the already-loaded argument data — no extra API call needed.

**When to use:** `admin/arguments/[id]/+page.server.ts` load function.

```typescript
// Source: admin/people/[id]/+page.server.ts can_delete pattern, adapted for argument
// argument.status is already in the ArgumentDetail response
const can_delete = argument.status !== 'published';
return { argument, can_delete };
```

Note: The people editor derives `can_delete` from a separate merge-preview API call to count FK rows. For argument delete, the guard is simpler: `status !== 'published'`. No additional API call is needed.

### Anti-Patterns to Avoid

- **Deleting in wrong FK order:** Attempting to DELETE arguments before utterances or pipeline_runs will raise PostgreSQL FK constraint violations. Always delete child rows before parent rows.
- **Omitting `execution_options(synchronize_session=False)`:** Every `update()` and `delete()` statement in this codebase MUST include this option. Omitting it causes SQLAlchemy to attempt session synchronization, which conflicts with async usage.
- **Calling `Base.metadata.create_all`:** Project constraint (CLAUDE.md). Never call this. Alembic is the sole DDL authority.
- **Putting `FASTAPI_BASE_URL` in client code:** All API calls go through `+page.server.ts`. The env var is `$env/static/private` only.
- **Modifying `TopNav.svelte`:** D-15 locks this. `TopNav.svelte` is not modified.
- **Navigating to confirm delete:** D-01 locks the inline two-step reveal. No separate confirmation page or modal.
- **Deleting the argument inside the job delete endpoint:** D-10/D-11 are critical. Job delete touches only the admin_job row.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form submission with JS enhancement | Custom fetch | `use:enhance` from `$app/forms` | Already used throughout; handles optimistic UI, deserialization, redirect following |
| Admin token auth on new endpoints | Custom middleware | Router-level `verify_admin_token` dependency (already on the admin router) | All endpoints on the admin router inherit it automatically |
| Delete cascade logic | Custom ORM relationship cascade | Manual `delete()` sequence following the established pattern | ORM relationships are not declared; manual is the project pattern |

---

## Runtime State Inventory

Not applicable — this is a greenfield addition phase. No renames, refactors, or migrations.

---

## Common Pitfalls

### Pitfall 1: AdminJob FK violation when deleting argument
**What goes wrong:** `DELETE FROM arguments WHERE id = X` raises `ForeignKeyViolation` because `admin_jobs.argument_id` references the argument row.
**Why it happens:** The FK exists (`AdminJob.argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=True)`) but has no `ondelete="CASCADE"` or `ondelete="SET NULL"`. PostgreSQL default is RESTRICT.
**How to avoid:** Execute `UPDATE admin_jobs SET argument_id = NULL WHERE argument_id = X` BEFORE deleting the argument row.
**Warning signs:** `asyncpg.exceptions.ForeignKeyViolationError` during argument delete tests.

### Pitfall 2: Wrong FK delete order (utterances vs pipeline_runs)
**What goes wrong:** Deleting `pipeline_runs` before `utterances` fails because `utterances.pipeline_run_id` references pipeline_runs.
**Why it happens:** Utterance has TWO FKs into this data: `argument_id` AND `pipeline_run_id`.
**How to avoid:** Delete utterances FIRST (they depend on pipeline_runs), then delete pipeline_runs.
**Warning signs:** `ForeignKeyViolationError` on the pipeline_runs DELETE.

### Pitfall 3: Missing `execution_options(synchronize_session=False)` on delete statements
**What goes wrong:** SQLAlchemy async session raises errors or behaves unpredictably when `synchronize_session` is not disabled.
**Why it happens:** The project's async SQLAlchemy pattern requires this on every `update()` and `delete()`.
**How to avoid:** Add `.execution_options(synchronize_session=False)` to every `db.execute(delete(...))` and `db.execute(update(...))` call.
**Warning signs:** SQLAlchemy `InvalidRequestError` or silent stale-cache bugs.

### Pitfall 4: `can_delete` for arguments is simpler than for people
**What goes wrong:** Developer copies the people-editor `can_delete` logic (which calls the merge-preview endpoint to count FK rows) instead of the simpler status check.
**Why it happens:** People delete is FK-based; argument delete is status-based (`published` vs not).
**How to avoid:** `can_delete = argument.status !== 'published'` — computed from already-loaded data. No extra API call.
**Warning signs:** Unnecessary `merge-preview` API call in the arguments load function.

### Pitfall 5: TopNav `variant="admin"` dead code removal
**What goes wrong:** Developer removes the `variant="admin"` branch from TopNav.svelte before confirming it is fully dead — if any route still passes `variant="admin"`, the nav renders as the public variant.
**Why it happens:** `variant="admin"` only appears in `admin/+layout.svelte`. After Phase 21, the layout no longer passes that variant.
**How to avoid:** Grep for `variant="admin"` after updating the layout before removing the TopNav branch.
**Warning signs:** Admin nav links disappear from any page.

### Pitfall 6: Job delete must not cascade into argument
**What goes wrong:** Developer accidentally deletes the argument row when deleting the admin_job.
**Why it happens:** The job detail page shows argument data prominently; it is easy to confuse job-delete with argument-delete scope.
**How to avoid:** The job delete service function contains exactly one DELETE statement: `DELETE FROM admin_jobs WHERE id = X`. No other table is touched.
**Warning signs:** Argument data disappears from the database after a job delete.

### Pitfall 7: `deleteConfirming` state persists across SvelteKit soft navigation
**What goes wrong:** Operator navigates to argument A (confirm showing), then navigates to argument B — the confirm state is still `true` from argument A.
**Why it happens:** SvelteKit soft navigation reuses the component instance. `$state` variables survive navigation unless explicitly reset.
**How to avoid:** Add a `$effect(() => { data.argument.id; deleteConfirming = false; deleteSubmitting = false; })` that resets state whenever the argument id changes. (The people editor has the same pattern for `mergeTargetId`, `isJustice`, etc.)
**Warning signs:** Confirm state shows when navigating between arguments without having clicked Delete.

---

## Code Examples

### +page.server.ts delete action (argument)
```typescript
// Source: admin/people/[id]/+page.server.ts delete action (lines 374-396) — adapted
delete: async ({ params, fetch }) => {
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
            method: 'DELETE',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch {
        return fail(502, { deleteError: 'Could not delete argument. Try again.' });
    }

    if (!res.ok) {
        if (res.status === 409) {
            return fail(409, {
                deleteError: 'Published arguments cannot be deleted. Unpublish first.',
            });
        }
        return fail(502, { deleteError: 'Could not delete argument. Try again.' });
    }

    throw redirect(303, '/admin/arguments');
},
```

### +page.server.ts load function addition for can_delete (argument)
```typescript
// Source: derived from people load function pattern + CONTEXT.md D-05
// argument is already loaded from FastAPI — no extra fetch needed
const can_delete = argument.status !== 'published';
return { argument, can_delete };
```

### admin/+layout.svelte after change
```html
<!-- Source: existing admin/+layout.svelte + CONTEXT.md D-14/D-15/D-16 -->
<script lang="ts">
    import '../../app.css';
    import { page } from '$app/state';
    import TopNav from '$lib/components/TopNav.svelte';
    import AdminSubNav from '$lib/components/AdminSubNav.svelte';
    let { children } = $props();
</script>

{#if page.url.pathname !== '/admin/login'}
<TopNav variant="public" />
<AdminSubNav />
{/if}

{@render children()}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-step delete (people editor) | Two-step inline confirm (Phase 21) | Phase 21 | Reduces accidental deletes; no modal dependency |
| Admin nav in TopNav variant | Dedicated AdminSubNav component | Phase 21 | Cleaner component boundary; TopNav stays URL-unaware |

**Deprecated/outdated after this phase:**
- `variant="admin"` in `TopNav.svelte`: becomes dead code after layout change (D-19 permits removal).

---

## FK Cascade Analysis (ADMIN-01 D-07 Resolution)

The models.py file was read directly. Key FK relationships for argument delete:

| Table | FK column | References | ondelete | Action required |
|-------|-----------|-----------|---------|-----------------|
| `utterances` | `argument_id` | `arguments.id` | none (RESTRICT) | DELETE utterances WHERE argument_id = X |
| `utterances` | `pipeline_run_id` | `pipeline_runs.id` | none (RESTRICT) | Must delete utterances BEFORE pipeline_runs |
| `pipeline_runs` | `argument_id` | `arguments.id` | none (RESTRICT) | DELETE pipeline_runs WHERE argument_id = X |
| `argument_participants` | `argument_id` | `arguments.id` | none (RESTRICT) | DELETE argument_participants WHERE argument_id = X |
| `case_arguments` | `argument_id` | `arguments.id` | none (RESTRICT) | DELETE case_arguments WHERE argument_id = X |
| `admin_jobs` | `argument_id` | `arguments.id` (nullable) | none (RESTRICT) | UPDATE admin_jobs SET argument_id = NULL WHERE argument_id = X |
| `arguments` | `id` | — | — | DELETE LAST |

No ORM `relationship()` declarations exist in models.py — all cascades are manual.

[VERIFIED: direct codebase read — api/models/models.py]

---

## TopNav `variant="admin"` Dead Code Analysis (D-19)

Grep result: `variant="admin"` appears in exactly ONE file in the entire codebase:
- `app/src/routes/admin/+layout.svelte` line 9

After Phase 21 changes that file to use `variant="public"`, the `{:else}` branch in `TopNav.svelte` (lines 38-90) becomes unreachable. The `variant` prop type can be narrowed or the branch removed entirely. The planner should include this as an optional cleanup task after the nav change is verified working.

[VERIFIED: direct codebase grep — app/src/routes/admin/+layout.svelte]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `case_appearances` does NOT need to be deleted as part of argument delete (it references `cases.id` and `people.id`, not `arguments.id`) | FK Cascade Analysis | If case_appearances has an argument_id FK not visible in models.py, the delete will fail |
| A2 | No other tables in the schema reference `arguments.id` beyond those listed in the FK table above | FK Cascade Analysis | Additional FK violations at delete time |

**Mitigation for A1 and A2:** `case_appearances` was read from models.py directly — it has `case_id` and `person_id` FKs, not `argument_id`. The full models.py was read and all 12 tables were reviewed. No additional FKs referencing `arguments.id` were found beyond the 6 listed.

[VERIFIED: direct codebase read — api/models/models.py]

---

## Open Questions

1. **Should `variant="admin"` branch be removed from `TopNav.svelte` in this phase?**
   - What we know: D-19 says "can be removed if it becomes dead code — confirm before removing"
   - What's unclear: Whether there is value in keeping it for future use
   - Recommendation: Include removal as a task in the nav plan. It is clean dead code elimination and aligns with D-19.

2. **Should `speaker_alias` table be deleted for argument delete?**
   - What we know: `speaker_alias.person_id` references `people.id`, NOT `arguments.id`. It is not in the FK chain for argument delete.
   - What's unclear: Nothing — it does NOT need to be touched.
   - Recommendation: Exclude from argument delete service function.

---

## Environment Availability

Step 2.6 SKIPPED — this phase makes no changes that require external tools beyond the already-running dev server. No new CLI tools, services, or runtimes are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (api/tests/) |
| Config file | not checked — no test config file was found in a quick glob |
| Quick run command | `pytest api/tests/ -x -q` |
| Full suite command | `pytest api/tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | argument delete: unpublished argument deletes all child rows | unit | `pytest api/tests/test_admin_arguments_service.py -x -q` | Partial — file exists but delete function not yet implemented |
| ADMIN-01 | argument delete: published argument returns 409 | unit | same | same |
| ADMIN-01 | FK order: utterances deleted before pipeline_runs | unit | same | same |
| ADMIN-01 | AdminJob.argument_id NULLed before argument delete | unit | same | same |
| ADMIN-02 | job delete: only admin_job row deleted | unit | `pytest api/tests/ -x -q -k "delete_job"` | No — new test needed |
| NAV-02 | AdminSubNav renders correct links | manual visual | n/a | n/a |

### Sampling Rate

- Per task commit: `pytest api/tests/test_admin_arguments_service.py -x -q`
- Per wave merge: `pytest api/tests/ -x -q`
- Phase gate: Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `api/tests/test_admin_arguments_service.py` — add `test_delete_argument_*` test cases covering: (a) unpublished argument full cascade, (b) published argument returns False, (c) not found returns None, (d) FK order verified via mock or real DB
- [ ] `api/tests/` — add `test_delete_job` case covering single-row delete

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes — admin-only endpoints | `verify_admin_token` dependency on all admin router endpoints (already in place) |
| V3 Session Management | no | no session changes |
| V4 Access Control | yes — delete operations are irreversible | Server-side status check (can_delete) is authoritative; client disabled state is defense-in-depth |
| V5 Input Validation | yes | `argument_id` and `job_id` are typed `int` in FastAPI path params — validated automatically |
| V6 Cryptography | no | no crypto changes |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR — delete another operator's argument | Tampering | FastAPI 404 if argument not found; no user-scoping needed (single operator) |
| Double-delete race on argument | Tampering | First delete commits; second returns None → 404 |
| CSRF on delete form | Tampering | SvelteKit CSRF protection is active (ORIGIN env var set); form actions use POST |
| Deleting published argument via direct API call | Tampering | Server-side status check in service function; 409 returned regardless of UI state |

---

## Sources

### Primary (HIGH confidence)

- Direct codebase read — `api/models/models.py` — FK relationships for all 12 tables
- Direct codebase read — `api/routers/admin.py` — existing DELETE endpoint pattern (people delete, lines 607-629)
- Direct codebase read — `api/services/admin_people.py` — `delete_person_if_orphan` function (lines 411-450)
- Direct codebase read — `api/services/admin_arguments.py` — service layer conventions
- Direct codebase read — `app/src/routes/admin/people/[id]/+page.svelte` — delete section, `$state` pattern
- Direct codebase read — `app/src/routes/admin/people/[id]/+page.server.ts` — delete action pattern
- Direct codebase read — `app/src/routes/admin/arguments/[id]/+page.svelte` — target page structure
- Direct codebase read — `app/src/routes/admin/arguments/[id]/+page.server.ts` — target action file
- Direct codebase read — `app/src/lib/components/TopNav.svelte` — variant="admin" branch, logout button style
- Direct codebase read — `app/src/routes/admin/+layout.svelte` — single location of variant="admin"
- Direct codebase read — `.planning/phases/21-admin-ui-surface/21-UI-SPEC.md` — approved visual design contract

### Secondary (MEDIUM confidence)

None — all findings are from direct codebase reads.

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- FK cascade order: HIGH — read directly from models.py; all 12 tables verified
- Delete service pattern: HIGH — directly modeled on existing `delete_person_if_orphan`
- AdminSubNav design: HIGH — UI-SPEC already approved; exact styles extracted from TopNav.svelte
- Two-step confirm pattern: HIGH — pattern derived from existing people editor + UI-SPEC contract
- `can_delete` logic: HIGH — argument.status already in ArgumentDetail response; no additional fetch needed

**Research date:** 2026-07-01
**Valid until:** 2026-07-31 (stable codebase; no external dependencies to expire)
