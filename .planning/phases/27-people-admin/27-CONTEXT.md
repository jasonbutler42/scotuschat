# Phase 27: People Admin - Context

**Gathered:** 2026-07-08 (discussion paused, then resumed same day after operator mockups were reviewed)
**Status:** Ready for planning.

<domain>
## Phase Boundary

Split the people list at `/admin/people/` into Bench and Advocate tabs with tab-appropriate columns and filtering, add a "Create person" flow that works before any argument exists, and consolidate Justice-specific fields into a collapsible card (referred to in this doc as the **Bench Details card** — it has no visible on-screen title) at `/admin/people/[id]` — with appointment data read from the migrated per-tenure-row `court_tenures` columns (Phase 22). The create and edit flows share one page/template (D-07).

This phase does not touch the Dashboard (Phase 28) or any public-facing pages.

**Scope amendment from discussion (see Decisions):** The Role field (PEDIT-04/PEDIT-08) is dropped from this phase's Bench Details card — REQUIREMENTS.md should be updated to reflect this before/during planning. Two new fields (Death Date, and per-tenure "Reason Left") appear in the operator's mockups but are deferred — they get visual space in the layout, but stay disabled/non-functional until a future phase adds their schema.

**Mockups reviewed:** Three mockups were provided and copied into `.planning/phases/27-people-admin/mockups/` (see Canonical References). Per the operator: use them for **patterns and flow only** — layout structure, field grouping, what appears when — not for exact colors/spacing/fonts, which should continue to follow `.planning/codebase/DESIGN-SYSTEM.md`.

</domain>

<decisions>
## Implementation Decisions

### Tabs & Routing
- **D-01:** Bench/Advocate tabs are a query param on one page (`/admin/people?tab=bench` / `?tab=advocate`), same `+page.server.ts`, consistent with the existing `?incomplete=1` / `?tenure_gaps=1` pattern already on this page. Not separate routes, not a client-only toggle.
- **D-02:** Tab split is strictly `is_justice=true` → Bench, `is_justice=false` → Advocate. No new classification logic.
- **D-03:** Default tab (no `?tab=` param) is Bench.

### Per-Tab Incomplete Filtering
- **D-04:** The existing "Incomplete only" toggle is **removed entirely** on both tabs. In its place: missing-field pills render inline in the list (extending today's pill pattern), and **clicking a pill filters the table** to people with that specific gap (click again / a visible "Clear filter" control resets). No separate toggle or dropdown control.
- **D-05:** Advocate tab missing-field pills: first name, last name, photo, bio. Role is **not** checked (role_id is structurally never set for advocates going forward per PEDIT-04's original intent — see Role removal below, this is now moot for advocates but the underlying reasoning holds for why role was never counted for them).
- **D-06:** Bench tab missing-field pills: first name, last name, photo, bio, birthdate, **no tenures** (zero `CourtTenure` rows for that person). Role is explicitly **excluded** from the Bench incomplete check — see Role removal decision below (role is being dropped from the UI entirely, not just from the incomplete check).
- **Note:** "No tenures" (zero tenure rows) is distinct from the existing "Justices with tenure gaps" filter (PDIR-06, a Justice **has** tenures but one doesn't cover a specific argued_date). Both concepts stay separate; "Justices with tenure gaps" filter is retained as-is.

### Create-Person Flow
- **D-07:** "Create person" is a full page navigation, not a popover/modal. Button on the list page → `/admin/people/new`, which renders the same person-editor template used for editing, just with no existing data (reuses PDIR-07's originally-specified navigation model; the popover idea was considered and explicitly rejected in favor of unifying create/edit into one page pattern).
- **D-08:** Minimum required to save a new person: full name **and** a Bench/Advocate choice (sets `is_justice`) upfront. Everything else (tenure, bio, photo, birthdate) is optional and filled in later on the same page.
- **D-09:** On save, the new-person form POSTs to a new (not-yet-existing) general create-person endpoint, then redirects to `/admin/people/{id}` — identical redirect behavior to every other save action on this page. This is a **new backend endpoint**; it is not a reuse of Phase 25's job-scoped `create_person_for_job` (that one validates the participant belongs to a specific job — not applicable here).

### Bench Details Card (formerly discussed as "Justice Details")
- **D-10 (Role field removed — REQUIREMENTS AMENDMENT):** The Role field (Chief Justice / Associate Justice) is dropped from this card entirely, overriding PEDIT-04 and PEDIT-08 as written in REQUIREMENTS.md. Rationale from discussion: role is argument-dependent (already covered per-argument via Phase 15/26's title/side work on `argument_participants`), so a person-level Role field is dead weight. **REQUIREMENTS.md needs to be updated to reflect this before/during planning** — PEDIT-04 and PEDIT-08 as currently written are no longer accurate for this phase.
- **D-11:** Expand/collapse animation uses a height/slide transition (e.g. Svelte's built-in `slide` transition) when Bench is selected — the card container stays visible and its content grows/shrinks, not a fade-in-place.
- **D-12 (deferred, but reserve layout space):** A "Reason Left" field per tenure row (e.g. died / retired / promoted / still in office, free text per the mockup) was proposed. This requires a new `court_tenures` column and a new Alembic migration, out of scope for this phase (Phase 22, schema foundations, already shipped and is closed). **Decision: defer the schema/functionality to a future phase, but render the field now, disabled/greyed out** (D-19), so the layout doesn't need to be reworked later.
- **D-13 (card structure, from mockup):** Adopt the mockup's consolidated single-card model: one card (no visible title — internally "Bench Details") containing a Bench/Advocate segmented toggle (replaces the old "Is Justice" checkbox), which sets `is_justice`. When Bench is selected, Birth Date, Death Date, and the repeatable Tenure Periods list appear inline in the same card (animated per D-11). When Advocate is selected, none of those fields render. This replaces the previous two-part model (checkbox in Basic Info + separate always-conditional "Court Tenure" card below it).
- **D-14 (new field, deferred like D-12):** The mockup also introduces a person-level **Death Date** field next to Birth Date, which isn't in REQUIREMENTS.md (PEDIT-02 only specifies Birthdate). Same treatment as Reason Left: render the field now (disabled/greyed out, per D-19), wire it up (new nullable column + migration) in a future phase.
- **D-15:** Birth Date, Death Date, and Tenure Periods are Bench-only, per the mockup — they do not appear when Advocate is selected. (This narrows PEDIT-02's literal wording, which didn't scope Birthdate to Bench-only; the mockup is treated as authoritative here.)
- **D-16 — Tenure appointment field input types (previously blocked, now settled by mockup):** Both **Appointed by** (e.g. "Richard Nixon") and **Appointing president's party** (e.g. "Republican") are plain free-text `<input>` fields, matching every other text field's styling — not dropdowns, not a curated president lookup.
- **D-17 (Claude's discretion, resolved):** The mockup's Photo card button reads "Save photo," conflicting with the locked requirement PEDIT-05 ("Upload photo"). Per the operator's explicit delegation of this kind of wording conflict, resolved in favor of the existing locked requirement: **the button stays "Upload photo."**
- **D-18:** Each Tenure Period row is its own bordered sub-card (Start Date, End Date, Appointing President, President's Party, Reason Left [disabled per D-19], a "Remove" button) inside the Bench Details card, with a "+ Add Tenure Period" action below the list — matches the mockup's nested-card treatment, not today's flatter inline-row layout.
- **D-19:** Reserved-but-not-yet-functional fields (Death Date, Reason Left) render as **disabled/greyed-out inputs** — not fully interactive inputs whose values are silently dropped on save. This avoids an operator typing a value that appears to save but doesn't persist.

### Claude's Discretion
- Exact visual treatment of the click-to-filter pill interaction (D-04) — how the active filter and its "clear" affordance are presented — is left to the planner/implementer, as long as clicking a pill filters and there's a way to clear it.
- Advocate argument count (PDIR-04) computation (distinct arguments vs. total participations) is left to the planner — no explicit user preference surfaced.
- Exact wording/styling of the disabled Reason Left / Death Date fields (D-19) — e.g. whether a "Coming soon" tooltip or label accompanies the disabled state.
- Whether the Merge and Delete sections (unchanged from today, PEDIT-11/PEDIT-12) render on `/admin/people/new` — they logically should be hidden there (nothing to merge/delete before a person is saved) and only appear once editing an existing person; the mockups only show the Create flow so this wasn't explicitly discussed, but it follows directly from D-07's shared-template model.
- The mockup's breadcrumb-style page header ("People > Create Person") is a new pattern not used elsewhere in admin (existing pages use a plain "← People" back-link). Recommended: adopt it consistently on both create and edit pages, styled per `.planning/codebase/DESIGN-SYSTEM.md` tokens (not the mockup's exact colors) — left to the planner/ui-researcher to confirm.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 27 goal and success criteria (§ "Phase 27: People Admin").
- `.planning/REQUIREMENTS.md` — PDIR-01 through PDIR-07, PEDIT-01 through PEDIT-12. **PEDIT-04 and PEDIT-08 are superseded by D-10 above (Role field dropped) — REQUIREMENTS.md text has not yet been edited to reflect this; treat D-10 as authoritative for this phase.**
- `.planning/codebase/DESIGN-SYSTEM.md` — Colors/typography/spacing reference. The mockups below are for **layout/flow patterns only**; visual styling (colors, fonts, radii) should follow this doc, not the mockups' literal appearance (operator's explicit instruction).

### Mockups (operator-provided, reviewed 2026-07-08)
- `.planning/phases/27-people-admin/mockups/create-person-bench-filled.png` — Create Person page, Bench selected, filled with a realistic example (William Rehnquist) showing two Tenure Period rows including the deferred Reason Left field ("Promoted", "Died").
- `.planning/phases/27-people-admin/mockups/create-person-bench-blank.png` — Same page, blank, Bench selected, one empty Tenure Period row with placeholder text.
- `.planning/phases/27-people-admin/mockups/create-person-advocate.png` — Same page, blank, Advocate selected — no Birth/Death Date, no Tenure Periods section.

### Prior Decisions
- `.planning/phases/22-schema-foundations/22-CONTEXT.md` — Defines the `court_tenures.appointed_by` / `appointing_president_party` migration (move-by-rename from `people`, no backfill) that this phase's tenure rows read from.
- `.planning/phases/25-pipeline-job-detail-page/25-CONTEXT.md` — D-12/D-13: the job-scoped mini create-person popover deliberately stayed minimal (name + side only) and explicitly deferred the full create-person editor to this phase. `create_person_for_job` (job-scoped, validates participant ownership) is NOT the pattern to reuse for D-09's new general create endpoint.
- `.planning/phases/26-arguments-admin/26-CONTEXT.md` — Established the per-argument advocate title/role pattern (role dropdown + title on `ArgumentParticipant`) that D-10's rationale for dropping the person-level Role field rests on.

### Existing People Admin UI (this phase's main edit targets)
- `app/src/routes/admin/people/+page.svelte` — List page; currently a single table with two independent toggle filters (`incomplete`, `tenure_gaps`) and a "Missing fields" pill column. D-01 through D-06 restructure this into tabs with click-to-filter pills.
- `app/src/routes/admin/people/+page.server.ts` — List page load; currently reads `incomplete`/`tenure_gaps` query params only — needs a `tab` param per D-01.
- `app/src/routes/admin/people/[id]/+page.svelte` — Edit page; currently has "Is Justice" checkbox + conditionally-shown Role select in the Basic Info card, and a separate always-shown-when-justice "Court Tenure" card below it with Seat/Start/End per row (no appointment fields yet, no animation). D-07 through D-19 restructure this into the new create+edit page: Identity card (renamed from "Basic Info," drops the is_justice checkbox), Photo card, Biography card, and the consolidated Bench Details card (D-13) — reused unchanged at `/admin/people/new` (D-07).
- `app/src/routes/admin/people/[id]/+page.server.ts` — Edit page load/actions; `save` action currently sends `tenures: [{seat, start_date, end_date}]` with no appointment fields — needs `appointed_by`/`appointing_president_party` per row (both free text per D-16), plus the new create-person action (D-09).

### Backend/API
- `api/services/admin_people.py` — `list_people()` (tab/pill filtering targets, D-01–D-06), `_missing_fields()` (per-tab pill logic, D-05/D-06), `get_person_detail()` / `update_person()` / `_replace_tenures()` (tenure row read/write — needs `appointed_by`/`appointing_president_party` per row), no existing general create-person function (D-09's new work).
- `api/schemas/admin_people.py` — `PersonUpdate`, `TenureRow` schemas — `TenureRow` needs `appointed_by`/`appointing_president_party` fields added (both `str | None`, free text, D-16). Do NOT add `reason_ended` — that's deferred (D-12, D-19) and stays UI-only (disabled) with no schema/API changes this phase.
- `api/models/models.py` — `Person` (`is_justice`, no `birthdate` column yet — needs migration for PEDIT-02; no `death_date` column — deferred per D-14, UI-only disabled field, no migration this phase), `CourtTenure` (`seat`, `start_date`, `end_date`, `appointed_by`, `appointing_president_party` — all present from Phase 22; no `reason_ended` column — deferred per D-12).
- `api/routers/admin.py` — People routes: `/people`, `/people/{id}`, `/people/{id}/photo`, `/people/{id}/merge`, `/people/{id}/merge-preview` — needs a new `POST /people` (or similar) for D-09.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The existing "Missing fields" pill rendering in `+page.svelte` (lines ~193–215) is the direct template for D-04/D-05/D-06's expanded pill set — same chip styling, just driven by a different field list per tab and made clickable.
- The existing `?incomplete=1` / `?tenure_gaps=1` query-param toggle pattern in `+page.server.ts`/`+page.svelte` (D-05/D-15 style) is the direct template for D-01's `?tab=` param — same `goto()` + `$derived` pattern, one more param.
- The existing tenure-rows `$state<TenureRow[]>` array + hidden JSON field pattern (Pattern 1) in `[id]/+page.svelte` (lines ~76–96, ~489) is the base to extend with `appointed_by`/`appointing_president_party` per row.
- The existing `{#if isJustice}` conditional block wrapping Role + Court Tenure sections is the direct target to merge into one Justice Details card with a slide transition (D-11).
- `update_person`'s existing full-name-only validation (no role/tenure required) is the direct template for D-08's create-person minimum-required validation.

### Established Patterns
- Svelte 5 Runes only: `$props`, `$state`, `$derived`, `$effect`; no legacy `export let` or `$:` blocks.
- Admin UI uses inline dark-theme CSS with card backgrounds `#1e293b`, borders `#334155`, primary text `#e2e8f0`, muted text `#94a3b8`.
- SvelteKit form actions + `use:enhance` is the established save/submit pattern; delete-and-reinsert (Pattern 5) is the established tenure-row write strategy in `update_person`.
- Every SQLAlchemy `update()`/`delete()` statement uses `.execution_options(synchronize_session=False)` (project-wide critical guard).
- Dates parsed with `datetime.date.fromisoformat()`; malformed input raises `ValueError` → router maps to 422.

### Integration Points — Gaps Found During Scouting (not user decisions — planner must address)
- No `birthdate` column exists on `Person` yet — PEDIT-02 requires a new nullable column + migration (small addition, likely bundled into this phase's planning since Phase 22 already closed).
- No general (non-job-scoped) create-person backend endpoint exists — D-09 requires a new one; the only precedent is job-scoped and IDOR-guarded to a specific job's participants (not reusable as-is).
- `_missing_fields()` currently applies the same three-field check (role/bio/photo) to every person regardless of `is_justice` — D-05/D-06 require it to branch per tab/is_justice and add birthdate + no-tenures for Bench.

</code_context>

<specifics>
## Specific Ideas

- The operator explicitly prefers unifying "create" and "edit" into the same page/template rather than a separate lightweight creation surface — a stated general preference, not just a one-off for this phase ("I like the idea of the 'create' and 'edit' pages being the same more").
- The operator initially favored a popover for creation (reasoning: "popups are transient by nature and well suited to things that only exist for a moment") but reversed this after weighing it against the create/edit-unification preference above — the reversal is the locked decision (D-07), not the popover.
- Reserve visual space in the layout for both deferred fields (Reason Left per tenure row, Death Date on the person) so a future phase can wire them up without a re-layout (D-12, D-14, D-19).
- **Mockups are patterns/flow references only, not visual specs** — the operator was explicit: "don't freak out and try to match the styles exactly... use your existing design system and just use these mockups for patterns and flow." Card structure, field grouping, and conditional reveal behavior come from the mockups; colors/spacing/typography come from `.planning/codebase/DESIGN-SYSTEM.md`.
- Minor copy/label conflicts between a mockup and existing locked requirements should be resolved silently in favor of the existing language, not re-asked (see D-17 and the general preference behind it).

</specifics>

<deferred>
## Deferred Ideas

- **Reason Left field** (e.g. died / retired / promoted / still in office, free text) per tenure row — needs a new `court_tenures` column + Alembic migration. Deferred to a future phase (D-12); this phase renders it disabled (D-19).
- **Death Date field** on the person record — needs a new nullable column + Alembic migration. Deferred to a future phase (D-14); this phase renders it disabled (D-19).

</deferred>

---

*Phase: 27-People Admin*
*Context gathered: 2026-07-08*
*Discussion was paused mid-flow pending operator mockups, then resumed and completed the same day after mockups were reviewed. All previously-blocked items (Bench Details card layout, tenure appointment field input types) are now settled — see D-13 through D-19.*
