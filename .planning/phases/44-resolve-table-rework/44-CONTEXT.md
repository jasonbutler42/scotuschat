# Phase 44: Resolve Table Rework - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Rework `ResolveCard.svelte` (the admin pipeline job detail page's Resolve table) per SEED-001's mockup (`resolve-speakers-panel.png`) and locked requirements RESOLVE-01–06: five columns (Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor — no separate Action column), a two-button segmented Bench/Advocate toggle replacing the current `<select>`, a real writable Argument Role dropdown for advocate rows, an always-rendered Descriptor column (renamed from Title), and a consistent "hint" treatment across columns.

Confirmed via direct code trace (not assumed): for advocate rows, `side` and "Argument Role" are already the *same stored value* — `ArgumentParticipant.side` (SideEnum) is the only persisted field; `argument_role` is a read-time projection via `ADVOCATE_LABEL_MAP.get(side)` (`api/services/speakers.py:36-42`, consumed in `api/services/admin_people.py:1038` and `api/services/admin_arguments.py:311`). `ResolveRowUpdate` (`api/schemas/admin_jobs.py:190-207`) only accepts `participant_id`, `side`, `title` — splitting Bench/Advocate and Argument Role into two visual controls needs **no new backend field or write path** for that part of the rework. The Descriptor rename (see D-05 below) is the one place this phase does touch the backend.

</domain>

<decisions>
## Implementation Decisions

### Argument Role dropdown scope (RESOLVE-03)
- **D-01:** The Argument Role dropdown for advocate rows has **3 real selectable options** — Petitioner's Counsel / Respondent's Counsel / Amicus Curiae — not just the 2 shown literally in the mockup. Backend already fully supports `SideEnum.AMICUS` and its `ADVOCATE_LABEL_MAP` entry; amicus rows exist in real transcripts and must be reachable from this control.
- **D-02:** A row still at `UNKNOWN` (freshly toggled to Advocate, no role chosen) or legacy `ADVOCATE` (pre-Phase-15 data) shows an **unset placeholder** in the dropdown, not a selected "Counsel" value. Placeholder text is **"Select case role"** (not "Select role" — user's explicit wording, overriding the mockup's literal copy). Saving without a pick leaves `side=UNKNOWN`, same as today.

### Confirm/Select flow inside Resolved As (RESOLVE-01)
- **D-03:** The current two-button intervention flow (separate "Confirm" button for the auto-matched candidate, separate "Select" button to open search) **collapses into one entry point**: the person-search combobox opens pre-filled with the auto-matched candidate as the top suggestion. There is no separate "Confirm" button/action — picking the pre-filled suggestion or typing to override both go through the same interaction.
- **D-04:** If the operator never touches the pre-filled suggestion, it counts as **accepted** when "Continue Resolve" is submitted — matches today's `auto_resolved: true` fast-path behavior (these rows already skip the side-gate), just without a visible "Confirm" button doing that job.

### Descriptor rename scope (RESOLVE-04)
- **D-05 (scope-expanding — flagged for planner):** This is a **full-stack rename**, not UI-copy-only, despite ROADMAP.md's "expected to be a frontend rework... to be confirmed at plan time" framing. Rename `ArgumentParticipant.title` → `ArgumentParticipant.descriptor` and `title_hint` → `descriptor_hint` everywhere:
  - `api/models/models.py` — column rename + **new Alembic migration** (Alembic is sole DDL authority per CLAUDE.md)
  - Schemas: `api/schemas/admin_arguments.py`, `api/schemas/admin_jobs.py` (`ResolveRowUpdate.title` → `.descriptor`), `api/schemas/admin_people.py`
  - Services: `api/services/admin_arguments.py`, `api/services/admin_jobs.py` (`update_resolve_row_for_job`), `api/services/admin_people.py` (`list_resolve_rows_for_job`)
  - `api/routers/admin.py` (uses `participant.title` directly, ~line 601, 1358)
  - `pipeline/commands/parse.py` (~line 419-540 — TOC-subtitle writer sets `p.title`)
  - `app/src/lib/components/ResolveCard.svelte` (the actual UI rework)
  - **Reversibility: costly** — touches a DB column across a migration and every read/write call site; undoing means a second migration plus reverting every one of the files above.
- **D-06:** Operator explicitly chose to absorb this full rename into Phase 44 as one pass (not split into a separate phase) — avoids a confusing intermediate state where the UI says "Descriptor" but the API/DB still say "title". Phase 44's plan will have more tasks/waves than the roadmap's original frontend-only estimate assumed.

### Segmented toggle reuse for side-gate (RESOLVE-02)
- **D-07:** The existing pre-resolution side-gate (D-11/PJOB-18 in Phase 25 — two plain buttons, "Select Bench or Advocate to continue", used only for intervention rows before the person-search typeahead activates) reuses the **same segmented-toggle component** as the resolved/editable Bench|Advocate state, not a visually distinct control. The gate state is just this same toggle with neither option pre-selected/active yet.

### "Extracted"/hint treatment across all 4 columns (RESOLVE-05)
- **D-08:** Checked whether a genuine "originally extracted" `side` value exists separate from the current committed value (the way `title_hint` today just re-reads `participant.title` per `api/services/admin_people.py:946-950` — "there is no separate stored 'originally extracted' value... the same column the operator edits"). **It does not** — `ArgumentParticipant.side` has no shadow/history column, and `ArgumentParticipant` has no `pipeline_run_id` to reconstruct a prior value from. Any hint on Bench/Advocate or Argument Role would necessarily just redisplay the row's own current value.
- **D-09 (locked, supersedes an earlier draft that would have omitted these hints — do not build the omit version):** All four columns (Resolved As, Bench/Advocate, Argument Role, Descriptor) **do show a hint**, matching the mockup and RESOLVE-05's literal wording. But the hint **wording changes from "Extracted:" to "Imported:"** across all four columns in this table specifically — honest framing for data that in this milestone's fixtures came from `import-convokit` (corpus passthrough), not a genuine per-field LLM/PDF extraction event. This is a uniform copy choice for now, not per-row provenance detection (no per-row PDF-vs-corpus field exists on `ArgumentParticipant` today — checked `models.py`, confirmed absent).
  - **Component change required:** `CopyableExtractedValue.svelte` hardcodes the `"Extracted:"` prefix (line 111, no prop for it today). Add a new **optional prefix-label prop** (e.g. `prefixLabel`, default `"Extracted"`) so every other call site in the app (pipeline run pages, argument editor) is unaffected; `ResolveCard.svelte` passes `prefixLabel="Imported"` for all four of its own hint usages.
  - **Deferred (see below):** building real per-row provenance detection so hint wording/values can differ correctly once PDF ingest (vs. corpus import) is exercised again.

### Claude's Discretion
- Exact internal implementation of the pre-filled-combobox pattern for D-03/D-04 (component structure, how "top suggestion" is visually distinguished from other candidates) — user locked the behavior, not the pixel-level mechanics.
- Whether the Alembic migration for D-05 is a simple column rename (`op.alter_column`) or requires additional handling — implementation detail for planning, not a user decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/ROADMAP.md` §"Phase 44: Resolve Table Rework" — goal, 5 success criteria, RESOLVE-01–06
- `.planning/REQUIREMENTS.md` — RESOLVE-01 through RESOLVE-06 full text
- `.planning/seeds/SEED-001-rework-resolve-table-requirements.md` — the original seed with full mockup-delta writeup (6 numbered deltas); this phase's real source of truth alongside the mockup image itself
- `resolve-speakers-panel.png` (outside repo at `C:\workspace\scotuschat\resolve-speakers-panel.png` — confirmed present and read directly during this discussion) — the visual acceptance reference: 5 sample rows (resolved Bench w/ valid tenure, resolved Advocate, unresolved intervention row, fully-unresolved row, resolved Bench w/ tenure gap)

### Architecture constraints
- `CLAUDE.md` §"Key Constraints" — Alembic is sole DDL authority (governs D-05's migration); §"Architecture Rules" #4 — `CopyableExtractedValue` is the default component for operator-editable extracted-value destinations (governs D-09's prefix-prop approach, not a hand-rolled 5th hint variant)

### Code under rework
- `app/src/lib/components/ResolveCard.svelte` (742 lines) — the file being reworked; current column order Raw label/Resolved as/Bench-Advocate/Argument Role/Title/Action (script-level comment ~line 6-20 documents the two merged data sources: `resolveRows` + `discrepancies`)
- `app/src/lib/components/CopyableExtractedValue.svelte` — shared hint component; line 111 hardcodes `"Extracted:"` prefix, needs the new prop per D-09

### Backend contract (confirmed unchanged for Bench/Advocate + Argument Role split)
- `api/schemas/admin_jobs.py:190-207` — `ResolveRowUpdate` (participant_id, side, title)
- `api/services/admin_jobs.py:765` — `update_resolve_row_for_job`
- `api/services/admin_people.py:885` — `_bench_role_and_missing_tenure` (tenure date-window lookup, unaffected)
- `api/services/admin_people.py:921` — `list_resolve_rows_for_job` (GET projection consumed by ResolveCard)
- `api/services/speakers.py:36-42` — `ADVOCATE_LABEL_MAP`

### Descriptor rename call sites (D-05)
- `api/models/models.py` — `ArgumentParticipant` (~lines 365-376)
- `api/schemas/admin_arguments.py`, `api/schemas/admin_jobs.py`, `api/schemas/admin_people.py`
- `api/services/admin_arguments.py`, `api/services/admin_jobs.py`, `api/services/admin_people.py`
- `api/routers/admin.py` (~lines 601, 1358)
- `pipeline/commands/parse.py` (~lines 419-540)

### Prior-phase invariants this phase must not break
- `.planning/STATE.md` §"Accumulated Context > Decisions" — Phase 27 Plan 11: use the write-only `$state` reassignment pattern for any effect-driven reset (an effect that reads+writes the same `$state` inside its own body triggers `effect_update_depth_exceeded`); Phase 27 CR-01/CR-02: keep data-carrying form inputs always present in the DOM, not conditionally rendered — conditionally-rendered inputs silently don't submit and wipe data on save

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CopyableExtractedValue.svelte` — already used for the current Title/Descriptor hint (Phase 38 added stacked-provenance mode); extend with a prefix-label prop (D-09) rather than building a new component
- `CreatePersonPopover.svelte` — already wired into the intervention-row correction flow; the D-03 collapsed combobox pattern still uses this for the "create new person" path

### Established Patterns
- Per-row hidden `<form>` + `requestSubmit()` pattern (script ~lines 92-109, 344-369) — side/title/descriptor edits submit immediately per-row via `?/saveResolveRow`; this pattern is unaffected by the rework and should be reused, not replaced
- `pendingSideOverrides` / `sideGateConfirmed` `$state` records (lines 100-101) — existing state shape for in-flight side edits; the segmented-toggle rework (D-07) should extend these, not introduce a parallel state model
- `SIDE_LABEL` map (lines 137-144) already has the advocate role display strings; D-01's dropdown options should reuse/align with this rather than duplicating labels

### Integration Points
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — composes `ResolveCard` as a sibling after the pipeline step-status cards (per Phase 25 D-05/D-20, unchanged by this phase)
- `api/routers/admin.py` (~lines 601, 1358) — the two call sites reading/writing `participant.title` directly that D-05's rename must update

</code_context>

<specifics>
## Specific Ideas

- Mockup (`resolve-speakers-panel.png`) is the literal visual reference — 5 columns, dark theme consistent with the rest of the admin UI (`#1e293b` card background, `#334155` borders — matches existing `ResolveCard.svelte` inline styles)
- Placeholder copy: "Select case role" (Argument Role, unset advocate state) — user's exact wording, not the mockup's "Select role"
- Hint prefix: "Imported:" (all 4 columns in this table, replacing "Extracted:") — user's exact wording, framing the value as import-sourced rather than freshly extracted

</specifics>

<deferred>
## Deferred Ideas

- **Real per-row extraction provenance:** Build a genuine way to distinguish PDF-parsed rows from corpus-imported rows (no such field exists on `ArgumentParticipant` today), so hint wording/values can correctly say "Extracted:" for genuine PDF/LLM extraction vs. "Imported:" for corpus passthrough, rather than the uniform "Imported:" label this phase applies everywhere in `ResolveCard`. Flagged for a future phase — not built now.
- **Capturing genuinely distinct raw/extracted values for `side` and argument role at parse time:** today `side` is a single mutable column with no shadow/history copy (unlike `Utterance.pipeline_run_id` versioning); a future phase could add this if per-field "before vs. after operator edit" hints become a real requirement.

### Reviewed Todos (not folded)
- `2026-07-28-unpublished-argument-visible-in-cases-list.md` — publish-visibility bug, already assigned to Phase 45 (BUG-01) per STATE.md. Not folded here.
- `2026-07-29-popover-scrollbar-outside-card.md` — popover styling bug, already assigned to Phase 45 (BUG-02) per STATE.md. Not folded here.

</deferred>

---

*Phase: 44-Resolve Table Rework*
*Context gathered: 2026-08-01*
