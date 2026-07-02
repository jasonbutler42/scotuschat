# Phase 23: Shared Argument Details Component - Context

**Gathered:** 2026-07-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a single reusable `ArgumentDetailsCard` Svelte component that renders the docket pill/tag input, free-text question number field, argued date, and extracted hints from `cover_metadata` — and wire it up on the pipeline job detail page as its first consumer.

Also in scope:
- Update the parse stat card on pipeline job detail: add Bench/Advocate/Total speaker counts, case name, argued date, docket(s), question number(s); unextracted fields show "N/A" rather than being hidden
- Remove source file display from the ingest card (PJOB-09 — it moves to the run status card in Phase 25)

The component is designed for Phase 26 reuse on `/admin/arguments/[id]` — same component, different save action target.

</domain>

<decisions>
## Implementation Decisions

### Component Architecture
- **D-01:** `ArgumentDetailsCard` owns its own `<form method="POST" use:enhance>` element. It takes an `action` prop for the save target (e.g., `?/saveJobMetadata` on pipeline job detail, `?/save` on argument edit). Phase 26 reuse is plug-in: same component, different `action` prop.
- **D-02:** The component replaces the existing Argument Metadata save form on `pipeline/[id]` entirely — no coexistence with the old form.
- **D-03:** Data flows to the component as props from the parent page: `<ArgumentDetailsCard savedValues={...} hints={...} action="..." />`. No data fetching inside the component — consistent with the architecture rule that all data fetching lives in `+page.server.ts`.

### Docket Pill/Tag Interaction
- **D-04:** Operator adds a docket pill by typing a docket number and pressing **Enter**. The input field clears and the docket appears as a removable pill. Keyboard-first; no visible "Add" button needed.
- **D-05:** Each pill serializes as a separate `<input type="hidden" name="docket[]" value="...">` in the form. Server reads `FormData.getAll('docket[]')`. No JSON serialization or comma-splitting needed.
- **D-06:** On failed save (server returns a form error), the component restores pill state from the submitted dockets in the `form` prop — not from `savedValues`. Operator does not lose unsaved pill changes.

### Hints Display
- **D-07:** Extracted hints appear **below each editable input** as small muted text. Linear layout, no second column, works on narrow screens.
- **D-08:** Hint prefix is `"Extracted: [value]"` — e.g., `"Extracted: October 12, 2024"` or `"Extracted: N/A"`. Clear provenance signal — operator knows the value came from the pipeline.
- **D-09:** For the docket hint (potentially multiple extracted dockets): each extracted docket displays as its own **small read-only pill/tag** in the hint area below the docket input. Not comma-joined — individual pills are clearer for multiple dockets.

### Claude's Discretion
- Component and prop naming (`ArgumentDetailsCard`, prop shapes) — follow PascalCase component convention, camelCase props
- Whether `savedValues` and `hints` are separate props or a single merged prop — researcher can determine cleanest shape given existing `cover_metadata` JSONB structure
- Parse stat card data sourcing (new API response fields vs. reading from existing argument/job fields) — researcher audits what's available; Phase 23 may need backend additions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Admin Pages (both consumers of the new component)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — current pipeline job detail; the Argument Metadata save form here is replaced by the new component
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — server load; must be updated to pass `savedValues` and `hints` props, and handle the new `saveJobMetadata` form action
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Phase 26 will wire the component here; researcher should read current structure to understand integration point
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — argument edit server load; Phase 26 consumer (reference only in Phase 23)

### Existing Components (patterns to follow)
- `app/src/lib/components/AdminSubNav.svelte` — most recent admin component; establishes Svelte 5 Runes + inline CSS pattern
- `app/src/lib/components/SpeakerPopover.svelte` — uses `bits-ui 2.18.1`; reference for headless UI integration if needed

### Schema and Data
- `api/models/models.py` — `ArgumentParticipant` (has `side` field: PETITIONER/RESPONDENT/AMICUS/BENCH/ADVOCATE/UNKNOWN), `Argument` (has `cover_metadata` JSONB, `argued_date`, `source_docket`), `AdminJob` — understand what fields exist for both save targets
- `api/routers/admin/` — admin job detail endpoint; check what `parse_stats` currently returns and what needs adding for PJOB-10 (Bench/Advocate/Total speaker counts, case name, argued date, dockets, question numbers)

### Requirements
- `.planning/REQUIREMENTS.md` — Phase 23 requirements: AEDIT-03, AEDIT-04, PJOB-03, PJOB-04, PJOB-05, PJOB-06, PJOB-07, PJOB-09, PJOB-10, PJOB-11, PJOB-12

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/lib/components/AdminSubNav.svelte` — establishes the Svelte 5 Runes + inline CSS pattern for admin components; `ArgumentDetailsCard` should follow the same structure
- `use:enhance` pattern from `$app/forms` — already used in both `pipeline/[job_id]/+page.svelte` and `arguments/[id]/+page.svelte`; the component's `<form>` should use it the same way
- `formatDate()` helper — appears in multiple admin pages (both consumers); could be extracted to `$lib/utils.ts` or duplicated minimally in the component

### Established Patterns
- **Svelte 5 Runes exclusively**: `$props()`, `$state()`, `$derived()`, `$effect()` — no `export let`, no `$:` reactive blocks, no legacy stores
- **Inline CSS dark design system**: `#0f1117` page bg, `#1e293b` card bg, `#334155` borders, `#e2e8f0` primary text, `#94a3b8` muted text — hints use muted text color
- **Form actions with `use:enhance`**: SvelteKit form actions for all saves; `form` prop carries server response (errors, echoed values)
- **No data fetching in components**: All data via `+page.server.ts` load → props into component
- **ParseStats currently has `utterance_count` and `speaker_count`**: Expanding to Bench/Advocate/Total + cover_metadata fields requires either backend additions or reading from the argument record already in the page data

### Integration Points
- `pipeline/[job_id]/+page.svelte`: Replace Argument Metadata `<form>` block with `<ArgumentDetailsCard>` import; update +page.server.ts to expose `savedValues`/`hints` shape and add `saveJobMetadata` form action
- `api/routers/admin/` (admin job detail endpoint): Likely needs updated `ParseStats` response type to include Bench/Advocate speaker count breakdown and cover_metadata-derived fields for PJOB-10
- `app/src/lib/components/` — new file `ArgumentDetailsCard.svelte` goes here

</code_context>

<specifics>
## Specific Ideas

- Docket pills in the hint area are read-only visual indicators — they should look visually distinct from the editable pill UI (e.g., smaller, no X button, slightly different styling) so the operator understands they can't interact with the hint pills
- The "Extracted: N/A" state should be visually distinct from "Extracted: [real value]" — perhaps even more muted or italic — so the operator can quickly see which fields had successful extraction
- PJOB-12 enforcement: the parse stat card must show the same extracted values as the hints in the Argument Details card — both read from `cover_metadata` JSONB on the same record; researcher should confirm they share a source

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-Shared Argument Details Component*
*Context gathered: 2026-07-02*
