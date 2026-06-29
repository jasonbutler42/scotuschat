# Phase 9: People Data Model Migration - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 delivers:

1. **Alembic migration 0006** — adds `first_name`, `last_name`, `middle_name`, `name_suffix`, `appointing_president`, and `appointing_president_party` columns to the `people` table; all nullable, no defaults, no backfill
2. **ORM model update** — `Person` model gains the six new columns
3. **Schema update** — `PersonDetail` and `PersonUpdate` schemas gain the six new fields
4. **Edit form extension** — the Phase 8 people edit form (`/admin/people/[id]`) gains name-parts inputs in the expanded Basic Info section and a new Appointment section; `full_name` auto-derives from parts server-side when `first_name` is non-empty
5. **Admin directory sort** — `/admin/people` directory query sorts by `last_name NULLS LAST` (replacing or supplementing current sort order)

Out of scope: backfilling structured name parts from existing `full_name` values; any public-facing display of these fields (Phase 14 consumes them); image upload or merge (Phase 12).

</domain>

<decisions>
## Implementation Decisions

### Name Parts — Schema & Storage (PEOP-01)

- **D-01:** Six new nullable columns added to `people` via migration 0006: `first_name VARCHAR(150)`, `last_name VARCHAR(150)`, `middle_name VARCHAR(150)`, `name_suffix VARCHAR(50)`, `appointing_president VARCHAR(200)`, `appointing_president_party VARCHAR(50)`. All nullable, no default, no NOT NULL constraint.
- **D-02:** `full_name` remains the resolution anchor and is NOT removed or made optional. Name parts are supplemental — downstream features (Phase 12 merge, Phase 14 popover) read structured parts; the pipeline resolver continues to use `full_name`.
- **D-03:** Migration 0006 leaves all new columns NULL on existing rows — no backfill, no parsing attempt. Operators fill in fields for records that matter (Justices first).

### Name Parts — Derivation Logic (PEOP-01)

- **D-04:** When the PATCH handler receives a `PersonUpdate` payload where `first_name` is non-empty, the service **auto-derives `full_name`** from parts using the format `{first} [{middle}] {last}[ {suffix}]` (middle and suffix omitted when blank). Example: first="Amy", middle="Coney", last="Barrett" → `full_name = "Amy Coney Barrett"`.
- **D-05:** If `first_name` is null or empty in the PATCH payload, `full_name` is left unchanged (server does not overwrite it). This preserves existing resolved records that only have `full_name` set.
- **D-06:** `full_name` remains an **editable text input** on the form alongside the name parts. The operator can edit either. Server derivation fires server-side on save — no client-side live preview needed.

### Admin Directory Sort (PEOP-01)

- **D-07:** The `/admin/people` directory query orders by `last_name NULLS LAST` as the primary sort. Records where `last_name IS NULL` appear at the bottom of the list.

### Appointing President Fields — Storage (PEOP-02)

- **D-08:** `appointing_president` is a **free-text VARCHAR(200)**. Operator types the president's name (e.g., "Ronald Reagan"). No constrained list — fewer than 50 values, operator-entered.
- **D-09:** `appointing_president_party` is a **VARCHAR(50)** stored as plain text. The frontend renders a `<select>` dropdown with a fixed option list (constraint lives in the UI, not the DB). Valid options: `Democratic`, `Republican`, `Whig`, `Federalist`, `Democratic-Republican`, `Independent`. An empty/null value is valid (advocates have no appointing president).
- **D-10:** No party field is stored directly on the person (e.g., no "Justice's own party"). The party field always refers to the appointing president's party affiliation.

### Edit Form Layout

- **D-11:** The **Basic Info** section expands to include name parts below `full_name`:
  - Row 1: `full_name` (full-width text input, editable)
  - Row 2: `first_name` | `middle_name` | `last_name` | `name_suffix` (4-column grid or 2+2 layout — Claude's discretion on responsive breakpoints)
- **D-12:** A new **"Appointment"** section is added as the **4th section** after Court Tenure:
  - `appointing_president` — text input labeled "Appointed by"
  - `appointing_president_party` — `<select>` dropdown labeled "Appointing president's party" with the six party options from D-09 plus a blank/empty option at the top
- **D-13:** The form's **page title / header** displays the person's `full_name` (e.g., "Edit: Amy Coney Barrett") rather than a generic "Edit Person" label. This is a Phase 8 edit — the `<h1>` or page title already renders the name; update it to use `full_name`.
- **D-14:** Final form section order: **Basic Info** → **Bio & Photo** → **Court Tenure** → **Appointment**. Single "Save changes" button at the bottom sends all sections together (Phase 8 pattern, unchanged).

### Claude's Discretion

- Exact column widths for the 4-input name parts row (responsive layout is Claude's call — 4-column on desktop, 2-column on tablet/mobile is reasonable)
- Whether `name_suffix` uses a small `<input>` (e.g., width ~80px) or a `<select>` with common suffixes (Jr., Sr., II, III, IV) — free text input is fine
- Exact label wording for the Appointment section header ("Appointment", "Appointing President", etc.)
- Whether the Appointment section shows a note ("Leave blank for advocates") or just renders silently empty — silence is fine
- Amber chip colors and form styling follow the Phase 8 admin dark theme tokens established

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` — PEOP-01, PEOP-02 (Phase 9 scope); confirm no other requirements are being addressed
- `.planning/ROADMAP.md` §Phase 9 — Success criteria (4 items that must be TRUE)
- `.planning/PROJECT.md` §Key Constraints — Alembic-is-sole-DDL-authority; `Base.metadata.create_all` is forbidden

### Prior Phase Foundation (MUST READ)
- `.planning/milestones/v1.1-phases/08-people-editor/08-CONTEXT.md` — Full Phase 8 decisions: edit form layout (D-11 section structure), PersonUpdate PATCH pattern (D-09 delete-and-reinsert tenure), admin dark theme tokens, SvelteKit patterns (`$state`, `$derived`, `use:enhance`, server-only `FASTAPI_BASE_URL`)
- `.planning/STATE.md` — accumulated context; check for any blockers or notes carried from Phases 6–8

### Database & ORM
- `api/models/models.py` — `Person` model (current columns: `id`, `full_name`, `role_id`, `bio_text`, `photo_url`); migration 0006 adds six new columns here
- `alembic/versions/0005_add_person_metadata.py` — most recent migration; 0006 chains from this

### Admin Backend
- `api/schemas/admin_people.py` — `PersonDetail` (edit form response), `PersonUpdate` (PATCH body); Phase 9 adds six new optional fields to both
- `api/services/admin_people.py` — `get_person_detail()` (extend to return new fields), `update_person()` (add derivation logic per D-04/D-05)
- `api/routers/admin.py` — `PATCH /api/admin/people/{id}` and `GET /api/admin/people/{id}` routes; `GET /api/admin/people` list route (update sort order per D-07)

### SvelteKit Admin UI
- `app/src/routes/admin/people/[id]/+page.svelte` — Phase 8 edit form; Phase 9 extends Basic Info section and adds Appointment section (D-11, D-12)
- `app/src/routes/admin/people/[id]/+page.server.ts` — load function (returns PersonDetail) and PATCH action; extend both for new fields
- `app/src/routes/admin/people/+page.server.ts` — directory load function; update `ORDER BY` to `last_name NULLS LAST` (D-07)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/admin_people.py` `update_person()` — Phase 8 PATCH handler; extend it with name-derivation logic (D-04/D-05). The delete-and-reinsert tenure pattern already in place provides the structural model for the full save.
- `api/schemas/admin_people.py` `PersonUpdate` — mass-assignment guard already documented (T-08-MASS); Phase 9 adds six new `Optional` fields to the allow-list
- Phase 8 admin dark theme token set: `#0f1117` bg, `#1e293b` card, `#334155` border, `#94a3b8` body text, `#93c5fd` accent — all new form inputs must match

### Established Patterns
- **Svelte 5 Runes**: `$state` for form field values, `$derived` for computed display; continue Phase 8 pattern — no legacy stores
- **SvelteKit form actions**: `export const actions = { default: async ({ request }) => ... }` in `+page.server.ts` — identical pattern to Phase 8 save
- **`use:enhance`**: all form submissions use progressive enhancement — mandatory continuation
- **Server-only env vars**: `FASTAPI_BASE_URL` from `$env/static/private`; never expose to client
- **FastAPI service/router/schema layering**: router calls service, service returns dicts, router wraps with Pydantic — follow `api/routers/admin.py` pattern

### Integration Points
- `api/models/models.py` `Person` — add six `Column(...)` entries, all `nullable=True`
- `api/schemas/admin_people.py` `PersonDetail` / `PersonUpdate` — add six `Optional[str] = None` fields
- `api/services/admin_people.py` `update_person()` — inject derivation block: `if payload.first_name: person.full_name = _derive_full_name(payload)`
- `api/services/admin_people.py` `list_people()` — change `ORDER BY` clause to `last_name NULLS LAST`
- `app/src/routes/admin/people/[id]/+page.svelte` — extend Basic Info section with 4-input name row; add Appointment section below Court Tenure
- `alembic/versions/0006_add_structured_name_fields.py` — new migration; adds six nullable columns to `people`

</code_context>

<specifics>
## Specific Ideas

- **Derivation helper**: a small private Python helper `_derive_full_name(first, middle, last, suffix) -> str` that joins non-blank parts with spaces is cleaner than inline string concatenation in `update_person()`. Example: `" ".join(p for p in [first, middle, last, suffix] if p)`.
- **Party select order**: blank/empty option first, then alphabetical: `(blank)`, Democratic, Democratic-Republican, Federalist, Independent, Republican, Whig. Alphabetical keeps the list predictable.
- **Directory sort**: `ORDER BY people.last_name NULLS LAST, people.full_name ASC` — secondary sort by `full_name` ensures stable ordering among records that share a last name or have no last name.

</specifics>

<deferred>
## Deferred Ideas

- **Public display of name parts and appointing president** — Phase 14 (Speaker Popover Card) consumes `first_name`, `last_name`, `appointing_president`, and `appointing_president_party` for the bench speaker popover. Phase 9 makes the data available; Phase 14 surfaces it.
- **Advocate-specific party or affiliation fields** (e.g., firm, organization) — explicitly out of scope per REQUIREMENTS Future section (ADV-01 deferred to v1.3+).
- **Backfilling name parts from existing full_name values** — intentionally deferred. If the operator wants bulk-fill, that's a one-off data task outside the phase scope.

</deferred>

---

*Phase: 9-people-data-model-migration*
*Context gathered: 2026-06-19*
