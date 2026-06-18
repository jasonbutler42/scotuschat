# Phase 8: People Editor - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 delivers the operator's people management tools in the admin UI:

1. **People directory** (`/admin/people`) — paginated/scrollable table of all person records with name, role, and a per-row missing-fields badge; toggle switch to filter to incomplete records only
2. **Person edit form** (`/admin/people/[id]`) — sectioned form with Basic Info (name, role), Bio & Photo (bio text, photo URL), Court Tenure (all tenure rows with add/delete); single Save button
3. **Pipeline integration** — completed job detail page (`/admin/pipeline/[job_id]`) gains a read-only list of resolved participants and a "Review people →" link to `/admin/people?incomplete=1`
4. **Migration 0005** — adds `bio_text` (TEXT, nullable) and `photo_url` (VARCHAR, nullable) to the `people` table; this is a prerequisite for everything above

No argument/case metadata editing. No per-argument participant review page (PEOPLE-04 is satisfied by the incomplete filter alone).

</domain>

<decisions>
## Implementation Decisions

### Participant Review Integration (PEOPLE-04)

- **D-01:** No dedicated participants page. PEOPLE-04 is satisfied by the incomplete filter in `/admin/people`. After a pipeline run completes, the operator uses the filter to find newly created person stubs.
- **D-02:** The completed `/admin/pipeline/[job_id]` page gains a **read-only resolved participants section** at the bottom: a list of people resolved in that run (name + role), sourced by joining `argument_participants → people → roles` on `argument_participants.argument_id = admin_jobs.argument_id WHERE person_id IS NOT NULL`.
- **D-03:** Below the participant list, a **"Review people →" link** navigates to `/admin/people?incomplete=1`. The link is global — it shows all incomplete people, not just this argument's participants.

### Missing Field Definition & Directory UX (PEOPLE-01, PEOPLE-02)

- **D-04:** A person record is **incomplete** if `role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL`. Court tenure absence is NOT considered missing — most advocates never have a tenure row and that is correct, not missing.
- **D-05:** The filter is a **toggle switch** at the top of the `/admin/people` page. When active, the URL becomes `/admin/people?incomplete=1` and the `+page.server.ts` load function re-runs with the filter. The toggle is pre-activated when the page loads with `?incomplete=1` in the URL (i.e., when navigated from the "Review people" link).
- **D-06:** Directory table columns: **Name | Role | Missing fields badge | Edit link**. The missing-fields badge shows which specific fields are absent as small amber chips (e.g., chips labelled "bio", "photo", "role"). No bio snippet, no photo thumbnail in the table.

### Tenure Editing (PEOPLE-03)

- **D-07:** Tenure fields are **always visible** on the person edit form, even for advocates who have no existing `court_tenures` row. If the operator fills in dates and saves, a new `court_tenures` row is created for that person.
- **D-08:** Show **all tenure rows** for the person, not just the most recent. Each row renders seat / start_date / end_date as editable inputs.
- **D-09:** An **"Add tenure" button** appends a new empty tenure row to the form (client-side Svelte state). A **trash icon** per row removes it. All creates/deletes/edits are sent in the single Save submission — the backend replaces the person's tenure rows with whatever is submitted (delete-and-reinsert strategy for simplicity).

### Role Assignment (PEOPLE-03)

- **D-10:** Role is a **`<select>` dropdown** populated from the `roles` table. The dropdown includes an **"+ Add new role"** option at the bottom. Selecting it opens a small inline form to enter a role name; submitting creates a new `roles` row and immediately selects it in the dropdown. Requires a new `POST /api/admin/roles` endpoint.

### Edit Form Layout (PEOPLE-03)

- **D-11:** Single scrolling page with **three visual sections**, each with a header:
  - "Basic Info" — full_name (text input), role (dropdown + add-role inline)
  - "Bio & Photo" — bio_text (textarea), photo_url (text input)
  - "Court Tenure" — list of tenure rows (seat, start_date, end_date) + "Add tenure" button
  - One **"Save changes"** button at the bottom saves all sections together.

### Claude's Discretion

- Exact styling of the toggle switch (CSS or Tailwind, no JS library required)
- Whether the missing-fields badge chips are `<span>` tags or another element
- Whether tenure date inputs are `<input type="date">` or text fields (prefer `type="date"` for browser-native date pickers)
- Whether the "Add new role" inline form appears below the dropdown or as a small modal
- Exact wording of the "Review people" link on the completed job page
- Whether the participant list on the job page shows a count header ("3 resolved participants") before the list
- Exact amber color value for the missing-fields badge chips (use `#f59e0b` or similar — stay consistent with admin theme)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` — PEOPLE-01 through PEOPLE-04 (Phase 8 scope); DEPLOY-01/03 deferred to v1.2
- `.planning/ROADMAP.md` §Phase 8 — Success criteria (4 items that must be TRUE)
- `.planning/PROJECT.md` §Constraints — Alembic-is-sole-DDL-authority; apolitical framing (identical treatment for all speakers); no `Base.metadata.create_all`

### Prior Phase Foundation
- `.planning/phases/07-pipeline-runner/07-CONTEXT.md` — D-13 (person create during discrepancy = name+role only; bio/photo/tenure is Phase 8); `argument_id` on `admin_jobs` is the FK Phase 8 reads for participant list; dark admin theme color values
- `.planning/STATE.md` §Accumulated Context — `GET /api/admin/people` already exists (Plan 07-07); `BODY_SIZE_LIMIT=10M` and `ORIGIN` env var blockers for DO deployment

### Database & ORM
- `api/models/models.py` — `Person` (full_name, role_id — bio_text/photo_url NOT YET in schema; migration 0005 adds them), `Role` (id, name), `CourtTenure` (person_id, seat, start_date, end_date), `ArgumentParticipant` (argument_id, person_id, raw_speaker_label, side), `AdminJob` (argument_id FK used for participant read)
- `alembic/versions/` — most recent migration determines the next number; migration 0005 adds bio_text + photo_url to people

### Existing Admin Backend
- `api/routers/admin.py` — `GET /api/admin/people` (returns list of PersonResponse — needs bio_text/photo_url added); `POST /api/admin/jobs/{job_id}/people` (inline person create from discrepancy — Phase 7 pattern); `verify_admin_token` dependency stays in place
- `api/services/admin_jobs.py` — `list_people()` (current implementation, returns name+role only — Phase 8 extends or replaces); `create_person_for_job()` (minimal Phase 7 create — name+role only)
- `api/services/people.py` — `get_person_by_id()` (returns id, full_name, role_name — no bio/photo/tenure yet)
- `api/schemas/people.py` — `PersonResponse` (id, full_name, role_name — needs bio_text, photo_url, tenures added for Phase 8 edit form response)
- `api/schemas/admin_jobs.py` — `PersonCreate` (name+role only — Phase 7 minimal create; Phase 8 does NOT change this schema, add/update metadata is separate)

### SvelteKit Admin UI
- `app/src/routes/admin/+layout.svelte` — "People Editor" is currently a disabled `<span>` at line ~36; Phase 8 activates it as `<a href="/admin/people">`
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Phase 7 job detail page; Phase 8 adds participant read-only list + "Review people →" link at bottom when job status = completed
- `app/src/routes/admin/pipeline/+page.server.ts` — SvelteKit server load + form action pattern to follow for new people pages

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/routers/admin.py` `verify_admin_token` dependency — stays in place; all new people routes use the same dependency
- `GET /api/admin/people` — already exists; upgrade it to include `bio_text`, `photo_url`, and `incomplete` flag for filtering
- `api/services/people.py` `get_person_by_id()` — extend with bio_text, photo_url, and tenure rows for the edit form load
- Admin dark theme token set: `#0f1117` bg, `#1e293b` card, `#334155` border, `#94a3b8` body text, `#93c5fd` accent — established in Phases 6-7; all Phase 8 UI must match

### Established Patterns
- **Svelte 5 Runes**: `$state` for dynamic tenure row array (add/delete rows before submit), `$derived` for "any fields missing" computed values, `$effect` if needed for toggle-on-load
- **SvelteKit form actions**: `export const actions = { default: async ({ request, fetch }) => ... }` in `+page.server.ts` — same pattern as Phase 6 login and Phase 7 start-run form
- **`use:enhance`**: All form submissions use `use:enhance` for progressive enhancement — established in Phase 7; continue here
- **Server-only env vars**: `FASTAPI_BASE_URL` from `$env/static/private` — all FastAPI calls from `+page.server.ts` load functions; never client-side fetch for admin data
- **FastAPI service/router/schema layering**: New routes follow the pattern in `api/routers/cases.py` — router calls service, service returns dicts, router wraps with Pydantic schema

### Integration Points
- `app/src/routes/admin/people/` — new route directory; `+page.server.ts` (load + ?incomplete filter), `+page.svelte` (table + toggle)
- `app/src/routes/admin/people/[id]/` — new route; `+page.server.ts` (load person + roles + tenures; PATCH action), `+page.svelte` (sectioned form with dynamic tenure rows)
- `api/routers/admin.py` — new routes to add: `GET /api/admin/people/{id}` (person detail with tenure array), `PATCH /api/admin/people/{id}` (update person + replace tenures), `POST /api/admin/roles` (create new role)
- `api/services/admin_people.py` — new service file for Phase 8 people management (separate from admin_jobs.py to maintain clear separation of concerns)
- `api/schemas/admin_people.py` — new schemas: `PersonDetail` (full edit form data including tenure array), `PersonUpdate` (PATCH body), `TenureRow` (seat, start_date, end_date)
- `alembic/versions/0005_add_person_metadata.py` — adds `bio_text TEXT` and `photo_url VARCHAR(500)` to `people` table; nullable, no default

</code_context>

<specifics>
## Specific Ideas

- The participant list on the completed job page reads `argument_participants WHERE argument_id = {job.argument_id} AND person_id IS NOT NULL`, joined to `people` and `roles` for display — avoids a new endpoint by including participants in the existing `GET /api/admin/jobs/{id}` response payload (or a lightweight separate `GET /api/admin/jobs/{id}/participants` endpoint)
- The "Review people →" link uses a standard `<a>` tag styled as a button (consistent with Phase 7 "Continue Resolve" button pattern)
- The missing-fields badge chips: derive on the server side so the API response includes a `missing: string[]` field per person; client renders chips from that array
- The tenure delete-and-reinsert strategy: PATCH endpoint receives the full current tenure array; service deletes all existing `court_tenures` rows for that person and inserts the submitted rows in one transaction — simpler than tracking individual add/delete/update operations
- Photo URL is stored as-is; no upload. Operator pastes a URL (e.g., from Oyez). No validation beyond non-empty string.

</specifics>

<deferred>
## Deferred Ideas

- **Argument/case metadata editing** (title, docket_number, argued_date, case_name) — the synthetic docket created by Phase 7's job-driven ingest (`job-{id}`) needs real values. This was explicitly deferred as "out of scope for Phase 8 but needed in the next batch of work." Schedule for Phase 9 or a follow-on patch. Affects: `cases` table (case_name, docket_number) and `arguments` table (title, argued_date).

</deferred>

---

*Phase: 8-people-editor*
*Context gathered: 2026-06-17*
