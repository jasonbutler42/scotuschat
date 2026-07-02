# Phase 21: Admin UI Surface - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Three deliverables:

1. **Argument delete (ADMIN-01)**: Operator can delete a mis-created argument from the argument edit page, after an inline two-step confirmation. Blocked if the argument is published.

2. **Pipeline run delete (ADMIN-02)**: Operator can delete a bad pipeline run (admin_job) from the job detail page, after an inline two-step confirmation. Only the admin_job row is deleted — the linked argument and its utterances are unaffected.

3. **Admin sub-navigation (NAV-02)**: When in the admin area, a second nav row appears immediately below the public TopNav. The public TopNav (Cases + Admin link) is always visible. A new `AdminSubNav` component renders below it with Pipeline Runner, Arguments, People Editor, and Logout.

</domain>

<decisions>
## Implementation Decisions

### Delete Confirmation Flow
- **D-01:** Both argument delete and job delete use an **inline two-step reveal**: first click changes the button to show "Confirm delete" + "Cancel"; second click submits the form action. No navigation, no modal, no `confirm()` dialog. Uses the existing `$state`-driven pattern (`deleteSubmitting`) from the people editor.
- **D-02:** The confirmation buttons ("Confirm delete" + "Cancel") replace the original delete button in-place — no layout shift or new elements stacking.

### Argument Delete (ADMIN-01)
- **D-03:** Argument delete button lives **on the argument edit page** (`/admin/arguments/[id]`) only — not on the list page. Consistent with the people editor pattern where delete lives on the entity's own page.
- **D-04:** Delete is **blocked if `argument.status === 'published'`** (i.e., `published_at IS NOT NULL`). Arguments in `pipeline` or `draft` status can be deleted.
- **D-05:** The `can_delete` flag is computed in `+page.server.ts` and gates the delete button visibility — same pattern as `can_delete` in the people editor.
- **D-06:** After successful delete, redirect to `/admin/arguments` (the arguments list).
- **D-07:** Argument delete cascades: deletes the argument row, all linked `pipeline_runs`, all `utterances` from those runs, `argument_participants`, and `case_arguments` join rows. The admin_job that birthed this argument either gets cascade-deleted or becomes an orphan reference — planning/research should confirm FK cascade behavior in the DB.
- **D-08:** Argument delete is **independent of job state** — no check against admin_job status. Only `argument.status` matters.

### Pipeline Run Delete (ADMIN-02)
- **D-09:** Pipeline run (admin_job) delete button lives **on the job detail page** (`/admin/pipeline/[job_id]`) only — not on the pipeline list page.
- **D-10:** **Mental model (CRITICAL):** Pipeline runs are disposable scaffolding whose sole purpose is to produce an `Argument`. Once the argument exists, it is the permanent record. Deleting a pipeline run MUST NOT delete or affect the linked argument, its pipeline_run step rows, or its utterances.
- **D-11:** Deleting an admin_job deletes **only the admin_job row**. No cascade into pipeline_run step rows, utterances, or the argument. The argument retains all its data.
- **D-12:** After successful delete, redirect to `/admin/pipeline` (the pipeline list).
- **D-13:** If the argument produced by a bad run has bad utterances, operator uses ADMIN-01 (delete argument) to clean everything up — that is the appropriate path for data cleanup.

### Admin Sub-Navigation (NAV-02)
- **D-14:** When in any `/admin/*` route (except `/admin/login`), the layout renders **two nav rows**: Row 1 = `<TopNav variant="public" />` (the existing public nav, unchanged); Row 2 = new `<AdminSubNav />` component.
- **D-15:** `TopNav.svelte` is **not modified**. The admin layout (`admin/+layout.svelte`) switches from `<TopNav variant="admin" />` to `<TopNav variant="public" /><AdminSubNav />`.
- **D-16:** `AdminSubNav` is a new component at `app/src/lib/components/AdminSubNav.svelte`. It renders: Pipeline Runner link, Arguments link, People Editor link, Logout button (right-aligned).
- **D-17:** AdminSubNav background: `#1e293b` (the current admin nav color) — provides subtle visual separation from the public TopNav's `#0f1117`. Same `border-bottom: 1px solid #334155` and `padding: 12px 24px` as the existing nav.
- **D-18:** Logout button lives in the AdminSubNav row, right-aligned — consistent with current positioning.
- **D-19:** The `variant="admin"` prop and its associated branch in `TopNav.svelte` can be removed if it becomes dead code after this change — researcher/planner should confirm no other references remain.

### Reviewed Todos (not folded)
- **"Live polling for pipeline list page job cards"** — already shipped in Phase 20 (PIPE-23 complete). No action needed.
- **"Prevent duplicate argument creation during ingest"** — already shipped in Phase 19 (PIPE-24/PIPE-25 complete). No action needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — ADMIN-01 (argument delete), ADMIN-02 (pipeline run delete), NAV-02 (admin sub-nav); success criteria defined here
- `.planning/ROADMAP.md` — Phase 21 goal, success criteria, and phase boundary

### Existing Delete Pattern (people editor — primary analog)
- `app/src/routes/admin/people/[id]/+page.svelte` — `can_delete` conditional button, `deleteSubmitting` $state, `?/delete` form action, inline tooltip for blocked state. This is the direct pattern to follow for argument and job delete.
- `app/src/routes/admin/people/[id]/+page.server.ts` — `can_delete` computed in load function, `delete` action calls FastAPI DELETE endpoint, handles 409 response.
- `api/routers/admin.py` lines ~607–629 — `@router.delete("/people/{person_id}")` endpoint pattern: returns 200 + `{"deleted": True}` on success, 409 on FK block.

### Target Pages for New Delete Buttons
- `app/src/routes/admin/arguments/[id]/+page.svelte` — argument edit page; delete button + two-step confirm go here
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — add `?/delete` form action here
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — job detail page; job delete button + two-step confirm go here
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — add `?/delete` form action here

### Navigation Components
- `app/src/lib/components/TopNav.svelte` — existing shared nav component; `variant="public"` stays unchanged. The `variant="admin"` branch will become dead code — confirm before removing.
- `app/src/routes/admin/+layout.svelte` — admin layout; switches from `<TopNav variant="admin" />` to `<TopNav variant="public" /><AdminSubNav />`

### Data Models
- `api/models/models.py` — `AdminJob` (lines ~345+), `Argument` (lines ~161+), `PipelineRun` (lines ~263+), `Utterance` (lines ~292+). Read FK relationships before writing delete service logic — confirm whether SQLAlchemy cascade is configured or manual deletion is required.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **People delete pattern** (`admin/people/[id]/+page.svelte`): `let deleteSubmitting = $state(false)` + `action="?/delete"` form + `{#if data.can_delete}` conditional. Direct template for argument and job delete.
- **`use:enhance`** throughout all admin form actions — delete actions follow the same pattern.
- **`X-Admin-Token` header** on all FastAPI admin fetch calls — new DELETE endpoints use the same auth header.
- **Redirect after action**: `throw redirect(303, '/admin/arguments')` pattern used consistently across all admin form actions.

### Established Patterns
- `can_delete` boolean computed in `+page.server.ts` load function; gates delete button in `.svelte` — keeps guard logic server-side.
- FastAPI DELETE endpoint returns `{"deleted": True}` on 200; 409 with `detail` string when blocked by FK or status check.
- Svelte 5 Runes ($state) for all local UI state — no legacy stores.
- `{#if data.can_delete}` / `{:else}` for conditional delete/tooltip rendering (see people editor).

### Integration Points
- New FastAPI endpoint `DELETE /api/admin/arguments/{id}` — checks `argument.status !== 'published'` before deleting; cascades argument + pipeline_runs + utterances + participants + case_arguments.
- New FastAPI endpoint `DELETE /api/admin/jobs/{job_id}` — deletes only the `admin_job` row; argument and downstream data unaffected.
- `admin/+layout.svelte` renders `<AdminSubNav />` below `<TopNav variant="public" />` — no change to the public layout or `TopNav.svelte` itself.

</code_context>

<specifics>
## Specific Ideas

- The admin sub-nav appears as a second strip directly below the public TopNav — operator always sees the Cases link and can click back to the public site from any admin page.
- AdminSubNav inherits the existing admin nav link style: `font-size: 14px; font-weight: 400; color: #94a3b8` for inactive links, same Logout button styling as today.
- The two-step confirm should show "Confirm delete" as a danger-red button (matching the initial delete button style) and "Cancel" as a muted/secondary button — visually consistent with the blocked-state tooltip pattern in the people editor.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 21-Admin UI Surface*
*Context gathered: 2026-07-01*
