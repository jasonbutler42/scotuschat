# Phase 18: People Schema + Editor - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an `is_justice` boolean column to the `people` table via Alembic migration (`0010`), backfill `True` for any person with existing `court_tenures` rows (all others default `False`), expose a toggle in the people editor, and conditionally show/hide bench-only sections (Role, Court Tenure, Appointment) based on the flag. Add a Justice indicator to the people directory listing. Operator can correct the classification on any record.

</domain>

<decisions>
## Implementation Decisions

### Migration & Backfill
- **D-01:** New migration `0010_add_is_justice.py` adds `is_justice BOOLEAN NOT NULL DEFAULT FALSE` to `people`. Backfills `is_justice = TRUE` for every `person_id` that appears in `court_tenures`. Alembic hand-written (not autogenerate); standard pattern from prior migrations.
- **D-02:** Backfill source is `court_tenures` only — no inference from `argument_participants.side = BENCH`. If a person has no tenure rows, they default `False` regardless of how they appeared in arguments.

### Toggle Placement & Label
- **D-03:** The `is_justice` toggle lives at the **top of the Basic Info card**, before the name fields — a single labeled checkbox: `☐ Is Justice`.
- **D-04:** The toggle is part of the main `?/save` form action (not a separate dedicated action). `is_justice` is added to `PersonUpdate` allow-list and submitted with all other fields on Save.

### Role Field Conditionality
- **D-05:** Role select stays inside Basic Info but is wrapped in `{#if isJustice}` — hidden for non-justice people. No form restructuring.
- **D-06:** When `is_justice = False` and the Role select is hidden, any existing `role_id` is **preserved in the DB**. The save action does not clear role_id when is_justice = False.
- **D-07:** When `is_justice = False` and Court Tenure rows exist in the DB, they are **preserved**. Hiding the section doesn't delete data. Operator must re-enable `is_justice` to manage tenure rows.
- **D-08:** When `{#if isJustice}` hides sections, those inputs are absent from the DOM and are not submitted. The save action treats absent optional fields as "leave unchanged" — consistent with existing `PersonUpdate` pattern.

### Editor Reactivity
- **D-09:** Sections appear/disappear in **real-time** as the operator toggles the checkbox, before saving — same pattern as `showAddRoleForm` today. `isJustice` bound to `$state`, initialized from `data.person.is_justice`. Sections wrapped in `{#if isJustice}`.

### Directory Listing
- **D-10:** Add a Justice indicator (small badge or text tag) to people directory rows where `is_justice = True`. The `PersonListItem` schema needs `is_justice` added; the list page renders the indicator alongside name/role.

### Schemas & API
- **D-11:** `PersonDetail` schema gains `is_justice: bool` field. `PersonUpdate` allow-list gains `is_justice: Optional[bool]`. The people admin service reads and writes `is_justice` via the existing PATCH endpoint.

### Folded Todos
- **Live polling for pipeline list page job cards** (Phase 20) — folded at user request; this todo belongs to Phase 20's live-polling work. Captured here for awareness; not in Phase 18 scope.
- **Prevent duplicate argument creation during ingest** (Phase 19) — folded at user request; this todo belongs to Phase 19's pipeline reliability work. Captured here for awareness; not in Phase 18 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — PEOPLE-05, PEOPLE-06, PEOPLE-07 are the three requirements for this phase; success criteria defined here
- `.planning/ROADMAP.md` — Phase 18 goal, success criteria, and phase boundary

### Existing Schema & Migrations
- `api/models/models.py` — `Person` model (no `is_justice` yet); `CourtTenure` model (links via `person_id`) — read before writing migration
- `alembic/versions/0009_add_original_filename.py` — most recent migration; new migration is `0010`
- `alembic/versions/0008_side_enum_and_argument_status.py` — reference for the `op.execute("COMMIT")` pattern required before ALTER TYPE ADD VALUE in PG

### Existing API Schemas
- `api/schemas/admin_people.py` — `PersonDetail`, `PersonUpdate`, `PersonListItem` all need `is_justice` added
- `api/services/admin_people.py` — service layer for people CRUD; where `is_justice` write logic goes

### Frontend Editor
- `app/src/routes/admin/people/[id]/+page.svelte` — current people editor; `showAddRoleForm` is the exact precedent for `$state`-driven conditional section visibility
- `app/src/routes/admin/people/[id]/+page.server.ts` — save action; needs `is_justice` in FormData parsing and PATCH body
- `app/src/routes/admin/people/+page.svelte` — directory listing page; needs Justice indicator
- `app/src/routes/admin/people/+page.server.ts` — directory load function; `PersonListItem` → needs `is_justice`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `showAddRoleForm` (`$state<boolean>`) in `+page.svelte` — exact pattern for `isJustice` reactive toggle; `{#if isJustice}` wraps bench sections the same way `{#if showAddRoleForm}` wraps the inline role form
- `PersonUpdate` allow-list in `admin_people.py` — established mass-assignment guard; `is_justice` added as `Optional[bool]`

### Established Patterns
- Alembic hand-written migrations with explicit FK ordering (not autogenerate) — D-01 follows this
- `op.execute("COMMIT")` before ALTER TYPE ADD VALUE — not needed for boolean column, but note the pattern exists (0008)
- `use:enhance` + form actions for all admin CRUD — D-04 consistent with this
- DOM-absent inputs = "leave unchanged" in save action — D-08 leverages this existing behavior
- `$state` reactivity for conditional UI (no stores) — D-09 follows Svelte 5 Runes pattern throughout

### Integration Points
- `PersonDetail.is_justice` → frontend `data.person.is_justice` → seeds `isJustice` `$state`
- `?/save` FormData → `is_justice` checkbox value → `PersonUpdate.is_justice` → DB write
- Directory listing: `PersonListItem.is_justice` → `+page.svelte` renders indicator badge

</code_context>

<specifics>
## Specific Ideas

- The Justice indicator on directory rows should be a small visual element (badge or text tag) alongside the name/role, not a filter — the existing "missing fields" filter handles filtering; this is a visual at-a-glance indicator
- The inline checkbox at the top of Basic Info should be a simple `<input type="checkbox">` with `name="is_justice"` and `bind:checked` to `isJustice` state — consistent with the existing form element style (no third-party toggle widget)

</specifics>

<deferred>
## Deferred Ideas

None from discussion — stayed within phase scope.

### Reviewed Todos (not folded)
*(Both matched todos were folded at user request — see Folded Todos in decisions above)*

</deferred>

---

*Phase: 18-People Schema + Editor*
*Context gathered: 2026-06-29*
