# Phase 39: Bench popover — additional context data for Justices - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the public speaker popover (`SpeakerPopover.svelte`, served by `GET /arguments/{id}/speakers`) with richer persistent context for Justices: birthdate, death date, a full per-tenure list (office, dates, appointing president, that president's party, and reason the tenure ended), and a short bio excerpt — all presented identically for every Justice regardless of party, consistent with the apolitical-framing hard constraint. Historical data for all of this already exists in `data/corpus/supreme_court_justices_sections.csv` and should be wired in via the existing `import_justices_csv.py` importer rather than manually re-entered.

Two mockups (Rehnquist bench card, Bopp advocate card) surfaced elements beyond the original roadmap scope — bio text and an advocate descriptor/title line and an "Edit person" link. Per discussion: bio text is now in scope (shown on both bench and advocate popovers); the advocate descriptor is a placeholder-only UI element this phase (no real data pipeline yet); the "Edit person" link is explicitly deferred to backlog item `999.9`, not built here.

Case-specific presentation (age at argument, tenure length, case-heard count) remains out of scope per the roadmap.

</domain>

<decisions>
## Implementation Decisions

### Reason a tenure ended
- **D-01:** New `CourtTenure` field, a constrained enum with exactly three values: `retired`, `died`, `promoted` (nullable — null covers both "still in office" and the 2 unknown historical rows). No `resigned`/`other` catch-all: the source CSV's real vocabulary (`Retired` ×58, `Died` ×51, `Promoted to Chief Justice` ×3, `Still in Office` ×9, 2 blank) doesn't distinguish resignation from ordinary retirement — even Abe Fortas's 1969 scandal-resignation is classified `Retired` in the source data.
- **D-02:** Only applies to ended tenures (`end_date` not null). An open/active tenure never shows a reason.
- **D-03:** No auto-derivation/inference logic (no matching `end_date` against `death_date`, no detecting a same-day Associate→Chief transition). The reason is authoritative source data from the CSV's `Reason Left` column, imported directly — not computed.
- **D-15 (display):** Map canonical values to the mockup's exact display wording — `died` → "Died in office", `promoted` → "Promoted", `retired` → "Retired" (or equivalent phrasing planner/UI-phase locks in) — following the Phase 37 `office`/`office_title()` canonical-value → formal-display-title pattern.

### Historical data backfill
- **D-04:** `data/corpus/supreme_court_justices_sections.csv` already has `Birthdate`, `Death Date`, and `Reason Left` columns for all 126 rows — confirmed by direct inspection. `pipeline/commands/import_justices_csv.py` currently reads neither of these three columns. Extend it to read all three.
- **D-05:** Populate all three fields for newly-created `Person`/`CourtTenure` rows exactly as the other CSV-sourced fields already are.
- **D-06:** Backfill onto already-imported historical rows too — but only fill currently-null fields; never overwrite an existing non-null/operator-set value. Mirrors the established Phase 38 D-16 "prepopulate only blank saved fields" pattern. Applies to `Person.birthdate`, the new `Person.death_date`, and the new `CourtTenure.reason_left` (or planner's chosen name) alike.
- **D-07:** This is a straight CSV-to-DB backfill, not a new manual data-entry effort — the importer already dedupes people by exact `full_name` (D-02 in its own docstring) and tenures by `(person_id, office, start_date)`, and is documented idempotent/safe to re-run.

### Editor wiring
- **D-08:** Activate the two existing disabled "Coming soon" inputs in `app/src/routes/admin/people/[id]/+page.svelte`: the person-level Death Date input (currently `disabled`, `placeholder="Coming soon"`, `title="Tracked in a future update"`, around line 521–536) and the per-tenure "Reason Left" input (currently `disabled`, same placeholder pattern, around line 637–652, currently a free-text `<input type="text">`).
- **D-09:** Reason Left becomes a `<select>` dropdown once it's an enum (D-01), following the same pattern as the existing `appointing_president_party` dropdown immediately next to it in the same tenure sub-card.
- **D-10:** Both wire into the existing atomic Save flow exactly like `birthdate`/`office`/`appointed_by`/`appointing_president_party` already do (hidden-input serialization into the tenures JSON array, submitted with the main save-form) — no new save action.

### Party affiliation exposure (reverses a prior exclusion)
- **D-11:** `api/services/speakers.py` and `api/schemas/speakers.py` both currently carry an explicit comment excluding `appointing_president_party` from the public API "intentionally... apolitical framing constraint (T-14-02)". Phase 39 intentionally reverses this: the appointing president's party affiliation (not the Justice's own — Justices have no party) is now shown publicly, in plain neutral text, with identical visual treatment for every entry regardless of party (no color-coding, no aggregation, no differential framing) — consistent with the apolitical hard constraint because it's factual historical data about a president, presented uniformly, not editorial commentary or statistics about Justices.
- **D-12:** Update the T-14-02 comments/docstrings in `speakers.py` and `schemas/speakers.py` to reflect the reversal — don't leave stale "intentionally excluded" language pointing at code that now includes it.
- **D-13:** `api/services/speakers.py`'s `"appointing_president": None` hardcode (never wired since Phase 22, per its own comment "Phase 27 will wire this from court_tenures.appointed_by") must actually get wired now. Given the mockup shows appointing president per-tenure (not one person-level value), this moves from a single top-level `appointing_president` field to a per-`TenureEntry` field (`appointed_by` + `appointing_president_party` alongside `office`/`start_date`/`end_date` on each tenure row) rather than staying a separate top-level field.

### Bio text
- **D-14:** Show `Person.bio_text` in the popover for both bench (Justice) and advocate speakers, truncated with a clamp and a click-to-expand ("read more") affordance to reveal the full text inline. This field already exists in the DB; it has simply never been displayed in the popover before.

### Advocate descriptor/title (placeholder only)
- **D-16:** The mockup's advocate "Location" line is actually a general descriptor/title field — sometimes just a location, sometimes a full title+employer+location (e.g. "General Advocate, United States, Washington D.C.") — that follows an advocate's name in the transcript. No such field or extraction exists today. This mockup depicts a **future state**. Phase 39 may build the UI slot for it using placeholder/dummy text only; real data extraction and wiring is explicitly deferred to a future phase.

### Edit link (deferred, not built)
- **D-17:** Both mockups show an "Edit person" link at the bottom of the popover. This is explicitly deferred to backlog item `999.9` ("Edit affordance on utterances and speaker popover") — not built in Phase 39. A reference note pointing back to these mockups and this discussion has been added to `.planning/phases/999.9-edit-affordance-on-utterances-and-speaker-popover/NOTES.md`.

### the agent's Discretion
- Exact enum constant names/migration mechanics for the reason-left field, provided the three canonical values (retired/died/promoted) and nullability match D-01.
- Exact display wording for each reason value, provided it matches the mockup's tone ("Died in office", "Promoted", and an equivalent for "Retired").
- Exact bio-text clamp length/line-count and the click-to-expand interaction details (UI-phase may refine).
- Exact popover layout for fitting birthdate/death date + a multi-tenure list without overwhelming the card (UI hint is set on this phase; defer pixel-level layout to `/gsd-ui-phase`).
- Exact placeholder copy/positioning for the advocate descriptor slot (D-16).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §"Phase 39: Bench popover — additional context data for Justices" — goal, success criteria, explicit case-specific-presentation exclusion.
- `.planning/REQUIREMENTS.md` §"PUB-04" — requirement mapping for Phase 39.
- `.planning/PROJECT.md` §"Constraints" — apolitical framing hard constraint; §"Key Decisions" — T-14-02 origin (`appointing_president_party` originally excluded).

### Historical source data
- `data/corpus/supreme_court_justices_sections.csv` — authoritative source for `Birthdate`, `Death Date`, and `Reason Left` (126 rows, confirmed present); currently unused by the importer for these 3 columns.

### Existing implementation to modify
- `api/services/speakers.py` — `get_argument_speakers()`; currently hardcodes `"appointing_president": None` and explicitly excludes party (T-14-02 comment) — both must change.
- `api/schemas/speakers.py` — `SpeakerPopoverEntry`/`TenureEntry`; party is explicitly excluded by docstring — must change; `appointing_president` likely moves from top-level to per-`TenureEntry`.
- `app/src/lib/components/SpeakerPopover.svelte` — current rendering of tenure list and single top-level `appointing_president`; needs birthdate/death date, bio text with expand, per-tenure appointing-president/party/reason, and the new fields.
- `pipeline/commands/import_justices_csv.py` — `run_import_justices_csv()`; extend to read/backfill `Birthdate`, `Death Date`, `Reason Left` per D-04–D-07.
- `api/models/models.py` — `Person` (add `death_date`), `CourtTenure` (add reason-left field); follow the Phase 37 `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`/`office_title()` constant + CHECK-constraint pattern for the new enum.
- `app/src/routes/admin/people/[id]/+page.svelte` — the two disabled "Coming soon" inputs (Death Date ~line 521–536, Reason Left ~line 637–652) to activate per D-08–D-10.
- `.planning/phases/999.9-edit-affordance-on-utterances-and-speaker-popover/NOTES.md` — mockup reference note added during this discussion; read before any future 999.9 work.

### Prior-phase precedent this phase follows
- `.planning/phases/37-tenure-seat-as-chief-associate-toggle/37-CONTEXT.md` — established pattern for constraining a `CourtTenure` field to an enum with CHECK constraint + canonical-value-to-display-title mapping; this phase's Reason Left field follows the same shape.
- `.planning/phases/38-full-name-vs-name-parts-rethink/38-CONTEXT.md` — D-16's "prepopulate only blank fields, never overwrite an operator value" backfill pattern, reused here for D-06.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/routes/admin/people/[id]/+page.svelte`'s existing `appointing_president_party` `<select>` dropdown (with the escape-hatch "unknown value" `<option>` for legacy data) is the direct pattern to copy for the new Reason Left dropdown.
- `office_title()` / `OFFICE_TITLES` in `api/models/models.py` / `SpeakerPopover.svelte` is the direct precedent for a reason-left canonical-value → display-title helper.
- `pipeline/commands/import_justices_csv.py`'s existing idempotent dedup-by-`full_name` / dedup-tenure-by-`(person_id, office, start_date)` loop is where the 3 new column reads and null-only backfill writes get added.

### Established Patterns
- Tenure data flows through one atomic JSON-serialized array in the person edit form (`tenures` hidden input), submitted together with person-level fields (`birthdate`, `is_justice`) via the single save-form — the new fields follow this exactly, no new form action.
- `CourtTenure` fields use a `CheckConstraint` + `nullable=False` + a small canonical-constant module pattern (Phase 37) for constrained values — Reason Left should follow the same DDL shape via a new Alembic migration (Alembic is sole DDL authority).
- The public API layer (`speakers.py`/`schemas/speakers.py`) has historically been deliberately minimal/apolitical by omission — this phase is the first to knowingly widen that surface, so the T-14-02 comments must be updated in place, not just silently contradicted.

### Integration Points
- New Alembic migration(s) for `Person.death_date` and `CourtTenure`'s reason-left column + CHECK constraint.
- `import_justices_csv.py` read/backfill extension.
- `api/schemas/speakers.py` (`TenureEntry` gains `appointed_by`, `appointing_president_party`, reason field; `SpeakerPopoverEntry` gains `birthdate`, `death_date`, `bio_text`, loses/keeps top-level `appointing_president` per D-13).
- `api/services/speakers.py` assembly logic (Step 5) — wire real per-tenure appointing-president/party/reason instead of the `None` hardcode.
- `SpeakerPopover.svelte` rendering — birthdate/death date line, bio text with expand, per-tenure block with office/dates/appointing-president/party/reason, advocate descriptor placeholder slot.
- `app/src/routes/admin/people/[id]/+page.svelte` — activate the two disabled inputs; `+page.server.ts` for the same route may need its form-parsing type updated to include the new fields.

</code_context>

<specifics>
## Specific Ideas

- Two mockups reviewed live during discussion (not saved as files — described here): a bench/Justice card (William H. Rehnquist) showing avatar, name, current-title pill ("Chief Justice"), a "b. Oct 1, 1924 · d. Sep 3, 2005" line, a truncated bio paragraph, and two tenure rows each with office+date-range on one line and "{President} · {Party}" / "{Reason}" on the next — e.g. "Chief Justice — Sep 1986 – Sep 2005" / "Reagan · Republican" / "Died in office", and "Associate Justice — Jan 1972 – Sep 1986" / "Nixon · Republican" / "Promoted"; and an advocate card (James Bopp Jr.) showing avatar, name, role pill ("Petitioner's Counsel"), and a descriptor line ("Dallas, Texas").
- Both cards show an "Edit person" link bottom-right — explicitly deferred (D-17), not built here.
- User's stated general approach for future mockups in this project: they may depict future state beyond a phase's actual scope; flag anything that looks out-of-scope rather than assuming it's all in-bounds, and where a mockup implies data or capability that doesn't exist yet, build the UI with placeholder/dummy content and defer the real wiring rather than skipping the visual element entirely.

</specifics>

<deferred>
## Deferred Ideas

- Advocate descriptor/title real data + extraction pipeline (D-16) — placeholder only this phase; future phase wires actual parsed/entered descriptor text.
- "Edit person" link on the popover (D-17) — belongs to backlog item `999.9`, which now has a note referencing these mockups.

</deferred>

---

*Phase: 39-bench-popover-additional-context-data*
*Context gathered: 2026-07-21*
