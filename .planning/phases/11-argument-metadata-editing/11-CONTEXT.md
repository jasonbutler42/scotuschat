# Phase 11: Argument Metadata Editing - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11 delivers:

1. **`/admin/arguments` list page** — all arguments with Pending / Resolved / Published status badges, sorted by argued date descending; publish/unpublish toggle per row
2. **`/admin/arguments/[id]` edit page** — per-argument form for case title (lead case), docket number (lead case), and argued date; always editable at any state; Publish / Unpublish button
3. **`published_at` column on `arguments` table** — new Alembic migration; replaces `resolved_at` as the public visibility gate
4. **Public `/cases/` query update** — filters on `published_at IS NOT NULL` instead of `resolved_at IS NOT NULL`
5. **Admin TopNav update** — "Arguments" link added to the admin variant in `TopNav.svelte`
6. **Job detail page update** — top-section argument metadata preview + "Edit argument metadata" link; "Ready to publish" CTA when job is COMPLETED and argument not yet published

Out of scope: unpublish workflow requiring re-resolve, bulk publish, post-resolve editing of utterances or speaker attributions, advocate firm/organization fields (ADV-01, v1.3).

</domain>

<decisions>
## Implementation Decisions

### Editor Location

- **D-01:** New `/admin/arguments` list page showing all arguments (pending, resolved, and published) with a status badge on each row, sorted by `argued_date DESC`. Each row includes a publish/unpublish toggle.
- **D-02:** New `/admin/arguments/[id]` per-argument edit page. Editable fields: lead case's `case_name`, lead case's `docket_number`, and `argument.argued_date`. Always editable regardless of state — no read-only lock at any stage.
- **D-03:** Job detail page (`/admin/pipeline/[job_id]`) gets a top-section argument metadata preview (case title, docket, argued date, current status) with an "Edit argument metadata" link to `/admin/arguments/[argument_id]`. Preview appears once `argument_id` is set on the job (i.e., after ingest creates the argument row).
- **D-04:** When job status = `COMPLETED` and `published_at IS NULL`, the job detail page displays a "Ready to publish" call-to-action section linking to `/admin/arguments/[argument_id]`. This guides the operator to the next step without requiring them to know to navigate there independently.

### Published State

- **D-05:** New `published_at` column (`TIMESTAMP WITH TIME ZONE`, nullable) added to the `arguments` table via a new Alembic migration. `resolved_at` is preserved and keeps its existing meaning: the pipeline resolve step stamped it when speaker resolution completed.
- **D-06:** Public visibility gate changes: `resolved_at IS NOT NULL` → `published_at IS NOT NULL` in `api/services/cases.py` `get_cases()` and any other service that filters public-facing arguments.
- **D-07:** Publish action is only available when `resolved_at IS NOT NULL AND published_at IS NULL`. Unpublish is always available when `published_at IS NOT NULL`. There is no gate preventing editing at any state.
- **D-08:** Publish / Unpublish control appears in two places: a toggle on each row of the `/admin/arguments` list, and a button on the `/admin/arguments/[id]` edit page.
- **D-09:** ARG-02 (read-only after `resolved_at` is set) is **dropped**. The argument editor is always editable. The publish model replaces the original read-only gate requirement.

### Consolidated Arguments

- **D-10:** The editor shows title and docket number for the **lead case only** (`is_lead = true` in `case_arguments`). Non-lead dockets from consolidated cases are shown as a read-only reference below the form fields but are not editable in this phase.

### Slug Behavior

- **D-11:** When `case_name` is edited and `published_at IS NULL`, the slug **re-derives** from the new `case_name` using the same logic as `pipeline/commands/ingest.py` `_derive_slug()`. When `published_at IS NOT NULL`, the slug is **frozen** — only `case_name` (the display title) updates. Because `cases.slug` has a unique constraint, a pre-publish slug collision with an existing case must surface as a user-facing validation error (not a DB constraint crash).

### Admin Navigation

- **D-12:** Admin TopNav (Phase 10 `TopNav.svelte`) gains an "Arguments" link in the admin variant: `SCOTUS CHAT | Pipeline Runner | Arguments | People Editor | [spacer] Log out`.

### Claude's Discretion

- Visual badge styling for Pending / Resolved / Published states — follow established admin dark theme tokens; pick distinct but not loud colors
- Label wording for publish/unpublish action ("Publish" / "Unpublish" is fine)
- Whether the list-row publish control is a button or a styled toggle — follow existing admin UI patterns
- Date display format on the arguments list (e.g., "Oct 6, 2014")
- Whether the argument edit page heading shows the case title or a generic "Edit Argument" label

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §Argument Metadata — ARG-01 (this phase closes it); ARG-02 is dropped and replaced by the publish model (D-09)
- `.planning/ROADMAP.md` §Phase 11 — Goal and success criteria (3 items that must be TRUE; note: SC-3 is superseded by D-09)
- `.planning/PROJECT.md` §Key Constraints — Alembic sole DDL authority; `Base.metadata.create_all` is forbidden; `resolved_at` visibility gate (now replaced by `published_at`)

### Database & ORM
- `api/models/models.py` — `Argument` model (adds `published_at`); `Case` model (`case_name`, `docket_number`, `slug`); `CaseArgument` (`is_lead` flag for D-10)
- `alembic/versions/0006_add_structured_name_fields.py` — most recent migration; new migration chains from this

### API Layer
- `api/routers/admin.py` — existing admin job endpoints; new argument GET + PATCH endpoints go here
- `api/services/admin_jobs.py` — `resolve_job()` stamps `resolved_at`; job detail fetch needs argument metadata (case_name, docket_number, argued_date, resolved_at, published_at) for the preview section (D-03)
- `api/services/cases.py` — `get_cases()` uses `resolved_at IS NOT NULL` filter today; must change to `published_at IS NOT NULL` (D-06)
- `api/schemas/admin_jobs.py` — `AdminJobResponse` currently only has `argument_id`; extend to include argument metadata for the job detail preview

### Pipeline
- `pipeline/commands/ingest.py` `_derive_slug()` (line 82) — slug re-derivation on pre-publish edit reuses this function's logic (D-11)

### SvelteKit Admin UI
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — job detail page; gets top-section argument preview + publish CTA (D-03, D-04)
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load function; extend to fetch argument metadata
- `app/src/lib/components/TopNav.svelte` — Phase 10 component; add Arguments link to admin variant (D-12); check `10-CONTEXT.md` D-09 for the current admin link set

### Prior Phase Foundation (MUST READ)
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — admin form patterns: SvelteKit form actions, `use:enhance`, PersonEdit structure, dark theme tokens
- `.planning/phases/10-unified-navigation/10-CONTEXT.md` — `TopNav.svelte` variant system (D-03/D-04/D-09); current admin nav link set that D-12 extends
- `.planning/STATE.md` — accumulated context and any blockers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/admin_people.py` `update_person()` — the pattern for a PATCH service function (receive payload, validate, write, return dict); `update_argument()` follows the same shape
- Phase 8/9 admin form pattern: `+page.server.ts` with a load function + named form action + `use:enhance` on `+page.svelte` — `/admin/arguments/[id]` follows this exactly
- Admin dark theme tokens: `#0f1117` bg, `#1e293b` card, `#334155` border, `#94a3b8` body text, `#93c5fd` accent blue

### Established Patterns
- **SvelteKit form actions + `use:enhance`**: all admin form submissions use progressive enhancement (mandatory)
- **Server-only `FASTAPI_BASE_URL`**: from `$env/static/private`, never `PUBLIC_`; enforced by existing test suite
- **FastAPI router → service → schema layering**: router calls service, service returns dicts, router wraps with Pydantic — follow `api/routers/admin.py` pattern throughout
- **Alembic sole DDL authority**: `published_at` column added via migration only

### Integration Points
- `api/services/cases.py` `get_cases()` — change `Argument.resolved_at.isnot(None)` → `Argument.published_at.isnot(None)`
- `api/schemas/admin_jobs.py` `AdminJobResponse` — extend with argument metadata fields so the job detail page preview doesn't need a second fetch
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — extend load function to pass argument metadata (title, docket, argued_date, resolved_at, published_at) to the Svelte page
- `app/src/lib/components/TopNav.svelte` — add `{ label: 'Arguments', href: '/admin/arguments' }` to the admin link list

</code_context>

<specifics>
## Specific Ideas

- **"Ready to publish" CTA condition**: `job.status === 'completed' && argument.published_at === null` — show a highlighted section on the job detail page with a direct link to `/admin/arguments/[argument_id]`
- **Slug collision handling (D-11)**: before writing the new slug on a pre-publish edit, query for any existing `Case` with that slug (excluding the current case id). If a collision exists, return a 422 with a clear message like "This title generates a URL slug that conflicts with an existing case."
- **Slug re-derivation**: reuse the logic from `pipeline/commands/ingest.py` `_derive_slug()` — lowercase, spaces→hyphens, strip periods and commas — either import it directly or duplicate the 5-line function in the service layer
- **Non-lead docket display (D-10)**: show consolidated dockets below the editable fields as a small read-only list (docket number only), labeled something like "Consolidated dockets" — purely informational

</specifics>

<deferred>
## Deferred Ideas

- **Unpublish → re-resolve workflow** — operator corrections to speaker attributions after publish require an explicit unpublish + re-resolve flow; out of scope for v1.2
- **Bulk publish from the arguments list** — single-argument publish sufficient for v1.2; bulk toggle could come later
- **Post-resolve utterance or speaker editing** — not in scope; pipeline re-run is the correction mechanism
- **ADV-01 (advocate firm/organization in popover)** — deferred to v1.3 per REQUIREMENTS.md §Future Requirements

</deferred>

---

*Phase: 11-argument-metadata-editing*
*Context gathered: 2026-06-22*
