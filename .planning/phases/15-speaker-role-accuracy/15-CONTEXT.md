# Phase 15: Speaker Role Accuracy - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 15 delivers three things:

1. **Justice role accuracy** — The public speaker popover shows the role a Justice held at `argued_date` via `CourtTenure` date-range lookup, not the person's static `Person.role_id`.
2. **Advocate role storage** — `argument_participants.side` is expanded to encode petitioner/respondent/amicus curiae per argument. Advocate roles are assigned during the resolve review and editable on the argument edit page.
3. **Argument lifecycle status** — `arguments` gets an explicit three-state `status` enum (`pipeline / draft / published`). The resolve step always requires manual operator approval; "Approve" transitions the argument from `pipeline` → `draft` and makes it editable on the argument edit page.

**Phase 15 is 4 plans** (expanded from roadmap's 3 due to the status/approval changes folded in):
- 15-01: Schema migration (SideEnum expansion + `arguments.status` column)
- 15-02: Service layer (tenure date-range lookup + advocate role label resolution)
- 15-03: Pipeline job detail approval UI (Approve button, read-only post-approve, Re-run button)
- 15-04: Argument edit page (advocate role editor, tenure gap warning, people directory filter)

**PIPE-14 is amended:** The resolve step no longer auto-advances when all speakers are auto-resolved. Every pipeline run requires manual operator approval before the argument is created (transitions to `draft`).

**Out of scope:** Advocate firm/organization affiliation (ADV-01, future), automated enrichment, multi-appointer tenure attribution per tenure row (deferred from Phase 14), full redesign of the pipeline job detail into a single submit form.

</domain>

<decisions>
## Implementation Decisions

### Argument Lifecycle Status

- **D-01:** Add `arguments.status` as an explicit enum column with three values: `pipeline` (prebirth — argument exists as DB scaffolding while the pipeline runs), `draft` (unpublished — pipeline done, argument editable on argument edit page, not publicly visible), `published` (publicly visible). This is an Alembic migration.
- **D-02:** Admin arguments list (`/admin/arguments`) shows only `draft` and `published` arguments. `pipeline`-state arguments are only accessible via the pipeline job detail page.
- **D-03:** The public `/cases` page continues to filter on `published_at IS NOT NULL` (unchanged). The new `status` column is admin-only.
- **D-04:** Mental model: the pipeline is a factory; the argument is the product. The argument "exists" (in the user's sense) when the operator approves the resolve step. Before that, the argument row is DB scaffolding.

### Advocate Role Storage (SideEnum Expansion)

- **D-05:** Expand `SideEnum` via `ALTER TYPE side ADD VALUE IF NOT EXISTS` for three new values: `PETITIONER`, `RESPONDENT`, `AMICUS`. `ADVOCATE` stays in the type permanently (Postgres cannot drop enum values) and is treated as legacy. `UNKNOWN` means "advocate, role not yet determined."
- **D-06:** The migration backfills all existing `argument_participants` rows where `side = 'ADVOCATE'` → `side = 'UNKNOWN'`. Clean slate for Phase 16 (parser) to assign `PETITIONER`/`RESPONDENT`/`AMICUS`.
- **D-07:** Advocate `role_name` in the popover comes from a hard-coded label map in the service layer — no join to the `roles` table needed:
  - `PETITIONER` → `"Petitioner's Counsel"`
  - `RESPONDENT` → `"Respondent's Counsel"`
  - `AMICUS` → `"Amicus Curiae"`
  - `UNKNOWN` or `ADVOCATE` (legacy) → `"Counsel"`

### Pipeline Job Detail (Resolve Review — Prebirth Only)

- **D-08:** The pipeline job detail page handles resolve-step editing only while the argument is in `pipeline` state. This includes: speaker alias confirmation/correction (existing) and advocate role assignment (new — `PETITIONER`/`RESPONDENT`/`AMICUS`/`UNKNOWN` dropdown for each non-BENCH participant).
- **D-09:** Every pipeline run ends with a manual "Approve" action. The operator clicks "Approve" on the pipeline job detail page regardless of whether there were any discrepancies. This triggers: `argument.status = 'draft'`, `argument.resolved_at = now()`, pipeline job transitions to read-only.
- **D-10:** After approval, the pipeline job detail is read-only but retains all stats (utterance count, speaker count, unresolved count, extracted metadata). A **"Re-run with same source"** button is visible; clicking it starts a new pipeline run using the same source PDF. The new run goes through `pipeline` state again; the existing `draft`/`published` argument is unaffected until the operator approves the new run.

### Argument Edit Page (Draft + Published)

- **D-11:** The argument edit page is the canonical home for all argument-level editing after approval. This includes: case metadata (Phase 11), and per-argument advocate roles (Phase 15 — new).
- **D-12:** Advocate role editor on the argument edit page: a dropdown for each resolved advocate participant showing `PETITIONER`/`RESPONDENT`/`AMICUS`/`UNKNOWN`. Saving updates `argument_participants.side` for that argument only — no effect on the person's record or their role in other arguments (ROLE-03 requirement).

### Justice Popover Role (Tenure Date-Range Lookup)

- **D-13:** In `get_argument_speakers`, the `role_name` for bench speakers (where `argument_participants.side = 'BENCH'`) is resolved by matching `argument.argued_date` against the person's `CourtTenure` rows. The matching row's `seat` field becomes `role_name` (e.g., `"Associate Justice"`, `"Chief Justice"`).
- **D-14:** **Fallback when `argued_date` falls outside all tenure rows:** use the tenure row with the highest `start_date` (most recent). This is the safest guess — usually means tenure data is incomplete for older arguments.
- **D-15:** **Surfacing tenure gaps to the operator:**
  - **Argument edit page:** Show an inline warning when any bench speaker's `argued_date` is outside all their tenure rows: `"[Name]'s role could not be resolved from tenure data — argued_date [date] falls outside all recorded tenures. Displaying most recent tenure as fallback. → Edit person"` (links to person edit page).
  - **People directory:** Add a new filter "Justices with tenure gaps" that shows people with `CourtTenure` rows where at least one of their arguments' `argued_date` is not covered by any tenure row.

### Claude's Discretion

- Exact label for the "Approve" button (e.g., "Create Argument", "Approve Run", "Accept")
- Whether the advocate role dropdown on the pipeline job detail and argument edit page are the same component or separate implementations
- Visual treatment of the inline tenure gap warning (inline banner, icon tooltip, etc.)
- Whether the Re-run button requires confirmation before starting

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §v1.3 Speaker Role Accuracy — ROLE-01, ROLE-02, ROLE-03 (3 requirements this phase closes)
- `.planning/REQUIREMENTS.md` §v1.2 Ingestion & Pipeline — PIPE-14 (amended: resolve step no longer auto-advances; manual approval required)
- `.planning/ROADMAP.md` §Phase 15 — Goal and 4 success criteria (must all be TRUE); note plan count is now 4, not 3

### Schema — Read Before Writing Migrations
- `api/models/models.py` — `SideEnum` (line 34: current values BENCH/ADVOCATE/UNKNOWN), `ArgumentParticipant` (line 205: `side` column), `Argument` model (no `status` column yet — add it), `CourtTenure` (line 113: `person_id`, `seat`, `start_date`, `end_date`)
- Alembic migration pattern: `api/alembic/versions/` — read existing migrations for `ALTER TYPE` enum expansion pattern; `statement_cache_size=0` must be in `connect_args` (CLAUDE.md constraint)

### Speaker Popover — Existing Implementation to Extend
- `api/services/speakers.py` — `get_argument_speakers()`: currently returns `role_name` from `Person.role_id`; Phase 15 changes this to tenure lookup for bench and side-label map for advocates; must also join `argument_participants.side` per person
- `api/schemas/speakers.py` — `SpeakerPopoverEntry`: `role_name` field stays; source changes
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` — speaker data pre-loaded here; no change needed unless `SpeakerPopoverEntry` shape changes

### Pipeline Job Detail — Existing Implementation to Extend
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — current resolve review UI; add advocate role dropdowns + Approve button + Re-run button
- `api/routers/admin_jobs.py` — add endpoint for approve action (sets `argument.status = 'draft'`, `resolved_at`) and re-run action
- `api/services/admin_jobs.py` — existing resolve/confirm service logic; extend for approval transition

### Argument Edit Page — Existing Implementation to Extend
- `app/src/routes/admin/arguments/[id]/+page.svelte` — argument edit form; add advocate role editor section and tenure gap warnings
- `api/routers/admin_arguments.py` (or equivalent) — PATCH endpoint for `argument_participants.side` per participant per argument
- `.planning/phases/11-argument-metadata-editing/11-CONTEXT.md` — D-05 (slug freeze on published), D-06 (published_at gate), mass-assignment allow-list pattern

### People Directory — Existing Implementation to Extend
- `app/src/routes/admin/people/+page.svelte` — existing filter UI; add "Justices with tenure gaps" filter
- `api/services/admin_people.py` — `list_people()` with filter support; extend for tenure gap query

### Prior Phase Decisions
- `.planning/phases/14-speaker-popover-card/14-CONTEXT.md` — D-01 through D-13: popover architecture, `SpeakerPopoverEntry` schema, `get_argument_speakers` pattern, `photo_url` reconstruction, `isBench` conditional rendering
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — D-01/D-02: migration 0006 pattern; `full_name` as resolution anchor
- `.planning/STATE.md` §Accumulated Context — prior phase decisions including `bits-ui ^2.18.1` for popover, fire-and-poll job state, `statement_cache_size=0`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/speakers.py` `get_argument_speakers()` — three-query pattern (person_ids → people+roles → tenures) is the base; Phase 15 adds a fourth query for `argument_participants.side` per person, and replaces the `role_name` assembly with tenure lookup (bench) vs. label map (advocates)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — existing resolve review table (speaker label, match, confidence, action); advocate role dropdown slots in as a new column for non-BENCH rows
- `app/src/routes/admin/people/+page.svelte` — existing filter toggle pattern (Phase 13: "incomplete" filter); "Justices with tenure gaps" filter follows the same pattern

### Established Patterns
- **Alembic DDL authority** — never `Base.metadata.create_all`; all DDL via `api/alembic/versions/`; `ALTER TYPE ... ADD VALUE IF NOT EXISTS` is valid Alembic `op.execute()`
- **No client-side fetch** — all data in `+page.server.ts`; `FASTAPI_BASE_URL` is `$env/static/private` never `PUBLIC_`
- **Svelte 5 Runes exclusively** — `$props()`, `$state()`, `$derived()`, `$effect()`; no `export let`, no `$:` blocks, no stores
- **Form actions + use:enhance** — admin edit pages use SvelteKit form actions; advocate role editor on argument edit page follows this pattern
- **Mass-assignment allow-list** — `ArgumentUpdate` Pydantic model controls what's PATCH-writable; `argument_participants.side` must be patched via a separate endpoint (it's a participant record, not an argument field)

### Integration Points
- `get_argument_speakers()` currently queries `distinct(Utterance.person_id)` to find speakers — it has no access to `argument_participants.side`. Phase 15 must add a join to `argument_participants` to get `side` per person for the advocate label map and bench tenure lookup
- `argument.status` column touches: ingest step (sets `pipeline`), approve action (sets `draft`), publish action (sets `published`), admin arguments list query filter, public cases list (unchanged — uses `published_at`)
- The Re-run button fires a new pipeline job using the existing ingest URL/path from the original `pipeline_runs` row — the `pdf_url` and `pdf_path` fields on `PipelineRun` already carry this

</code_context>

<specifics>
## Specific Ideas

- **"Approve" button placement**: At the bottom of the resolve review section on the pipeline job detail page, after the speaker table. Always visible — not gated on "no discrepancies remaining."
- **Argument status in admin list**: The arguments list should show a status badge (`Draft` / `Published`) to distinguish unpublished from published arguments at a glance.
- **Tenure gap warning**: Show the warning on the argument edit page for both `draft` and `published` arguments (a published argument with a tenure gap is arguably more urgent to fix).
- **People directory "Justices with tenure gaps" filter**: This requires a DB query that joins `argument_participants` → `arguments` (for `argued_date`) → `court_tenures` (for date ranges) and finds people where the join produces no matching tenure for at least one argument. This is a moderately complex query — researcher should validate the join strategy.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-appointer tenure attribution** — Justices with multiple tenures (e.g., Rehnquist: Associate Justice appointed by Nixon, Chief Justice appointed by Reagan) could show the correct appointing president per tenure row. Currently one `appointing_president` per person on the `people` table. Deferred from Phase 14; still deferred.
- **Full pipeline flow redesign as submit form** — User's mental model is "the pipeline fills out a form for me." The current approach implements the right conceptual model (prebirth/draft/published states, manual approval) without redesigning the pipeline job detail into a literal creation form. The form-first vision is noted for a potential future milestone.
- **Advocate firm/organization in popover** — REQUIREMENTS.md Future Requirements ADV-01. Not in scope for Phase 15.

</deferred>

---

*Phase: 15-speaker-role-accuracy*
*Context gathered: 2026-06-25*
