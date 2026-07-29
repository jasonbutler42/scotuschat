# Phase 38: Rethink Full Name vs. name-part fields in the people editor - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Make structured name parts the authoritative operator-editable representation of a person, generate and synchronize the existing `full_name` compatibility value from those parts, migrate existing full-name-only records without silent corruption, and carry extracted name-part provenance through pipeline/import paths into the people editor. This phase also evolves the shared extracted-value presentation globally so every operator-editable extracted field can show the interpreted value, confidence, and exact raw source text in one consistent stacked pattern.

The phase does not restore the removed job-rerun control and does not add a general-purpose Admin Dashboard attention queue. Ambiguous-name cleanup is surfaced through the existing People directory attention/filter pattern.

</domain>

<decisions>
## Implementation Decisions

### Name authority and storage
- **D-01:** Structured name parts are authoritative. Full Name is generated and is not independently operator-editable.
- **D-02:** People create/edit surfaces show a live, read-only Full Name preview labeled as generated from name parts.
- **D-03:** One shared derivation rule applies everywhere a person is created or updated, including the main people editor, standalone create page, pipeline mini-create, API writes, CSV/corpus imports, and seeds.
- **D-04:** Keep the existing `full_name` database field as a synchronized compatibility value so current display, sorting, alias, deduplication, and API consumers continue to work.

### Canonical formatting
- **D-05:** Canonical Full Name format is `First Middle Last, Suffix`; omit blank Middle and Suffix components without leaving extra spaces or punctuation.
- **D-06:** Normalize whitespace only: trim components and collapse repeated spaces. Preserve authored capitalization and punctuation.
- **D-07:** Treat each component as authored text. Preserve initials, hyphens, apostrophes, particles, compound surnames, and suffix spelling; do not synthesize periods, title-case text, or otherwise rewrite content.
- **D-08:** Display the canonical Full Name everywhere. Lists may continue sorting by Last Name without changing displayed ordering.

### Minimum data and legacy migration
- **D-09:** A new person requires at least First Name or Last Name. This supports incomplete pipeline knowledge and legitimate single-part names while guaranteeing a non-empty derived Full Name.
- **D-10:** Automatically split existing Full Names into component fields rather than requiring immediate manual cleanup or leaving all legacy rows unconverted.
- **D-11:** Auto-apply only confident splits. When a Full Name cannot be split confidently, preserve the original Full Name unchanged and flag the record for name review; do not silently replace it with a guess.
- **D-12:** Surface ambiguous legacy records through a specific `Name review` attention indicator/filter in the People directory, following the existing missing-data cleanup pattern.
- **D-13:** Do not add or defer a generic cross-feature Admin Dashboard queue unless the focused People directory solution later proves insufficient.

### Extracted name-part provenance
- **D-14:** Pipeline parsing and import paths extract First, Middle, Last, and Suffix as persistent reference metadata rather than producing only a Full Name.
- **D-15:** Show the extracted reference beneath each corresponding editable saved field. Extracted metadata persists independently when an operator edits the saved value.
- **D-16:** When extraction first becomes available, prepopulate only blank saved fields. Never overwrite an existing operator value.
- **D-17:** If extraction/reprocessing occurs later, replace the extracted reference with the latest result while leaving saved fields untouched. This consistency rule does not restore the removed job-rerun UI.
- **D-18:** Retain the extractor's best-effort interpretation for every name part, including uncertain guesses, so the operator can see what the system thought it saw and correct the editable value.

### Shared extracted-value presentation
- **D-19:** Evolve the shared extracted-value component globally, not only for name fields. Extracted fields with an editable destination use the same stacked treatment.
- **D-20:** The stacked treatment exposes three distinct facts per field: the interpreted extracted value, a confidence rating, and the exact raw source text.
- **D-21:** First line: `Extracted: {interpreted value}` with the Phase 36 copy affordance attached to the interpreted displayed value. Second line: `{confidence band} confidence · Raw: {exact source text}`.
- **D-22:** Confidence is presented as `High`, `Medium`, or `Low`, not a percentage. Avoid implying calibrated statistical precision; research/planning may define a consistent confidence contract and thresholds.
- **D-23:** The stacked layout must remain usable beneath both narrow fields such as Suffix and wider fields such as Last Name.

### Agent's Discretion
- Exact shared formatter/module boundary and enforcement mechanism, provided every write path uses the same canonical rule.
- Exact migration splitting algorithm, confidence contract, and thresholds, provided ambiguous legacy values remain intact and reviewable.
- Exact storage schema for extracted value, raw text, and confidence, provided provenance persists independently of operator edits and all relevant paths behave consistently.
- Exact responsive spacing and accessible markup for the stacked extracted-value component, constrained by the Phase 36 copy/accessibility contract and the canonical mockup.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements and boundaries
- `.planning/ROADMAP.md` §"Phase 38: Rethink Full Name vs. name-part fields in the people editor" — authoritative goal, success criteria, and pipeline-consistency boundary.
- `.planning/REQUIREMENTS.md` §"PEOPLE-09" — requires a locked Full Name behavior decision.
- `.planning/PROJECT.md` §"Current Milestone: v1.6 Backlog Cleanup" and §"Constraints" — milestone scope and project-wide constraints.

### Extracted-value interaction contract
- `.planning/phases/36-click-to-copy-extracted-values-design-pattern/36-CONTEXT.md` — existing global rule for extracted fields with editable destinations and exact copy behavior.
- `.planning/phases/36-click-to-copy-extracted-values-design-pattern/36-UI-SPEC.md` — approved reusable component, accessibility, states, spacing, and copy-feedback contract.
- `.planning/phases/36-click-to-copy-extracted-values-design-pattern/36-PATTERNS.md` — exact component and consumer integration seams.

### Canonical visual reference
- `.planning/phases/38-full-name-vs-name-parts-rethink/mockups/extracted-fields-stacked.png` — user-supplied canonical stacked layout for small and large fields. Replace its example percentage with the locked `High`/`Medium`/`Low` confidence band while preserving the two-line structure and raw-text treatment.
- `.planning/phases/38-full-name-vs-name-parts-rethink/38-FIGMA.md` — approved Figma manifest for the Docket Pill component, including canonical file/node links, covered states, implementation targets, and the durable fallback snapshot.
- `.planning/phases/38-full-name-vs-name-parts-rethink/mockups/docket-pill-provenance-approved.png` — approved offline snapshot of the Docket Pill review sheet. The editable Figma component linked from `38-FIGMA.md` remains authoritative.

### Existing name behavior and ingestion
- `api/services/admin_people.py` — existing `_derive_full_name`, partial edit-time derivation, create-time Full Name requirement, directory missing-field logic, and people mutations.
- `api/schemas/admin_people.py` — current create/update contracts and structured name fields.
- `api/models/models.py` — current non-null `Person.full_name`, nullable structured parts, and JSONB metadata patterns.
- `app/src/routes/admin/people/new/+page.server.ts` — standalone create validation currently requires Full Name.
- `app/src/routes/admin/people/[id]/+page.server.ts` — edit action currently requires Full Name and forwards both representations.
- `app/src/routes/admin/people/new/+page.svelte` — standalone name form to convert to generated preview plus extracted hints.
- `app/src/routes/admin/people/[id]/+page.svelte` — main people editor and existing attention/field layout integration point.
- `pipeline/commands/import_justices_csv.py` — existing `First Middle Last, Suffix` reconstruction rule and manual-override escape hatch.
- `pipeline/commands/seed_aliases.py` — existing Full Name-based seed and dedup consumer.
- `pipeline/commands/import_convokit.py` — corpus person creation/import path that must follow the shared authority contract.
- `api/services/admin_jobs.py` — pipeline mini-create path that currently accepts Full Name only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/lib/components/CopyableExtractedValue.svelte`: the Phase 36 shared copy component should evolve to render interpreted value, confidence, and raw text rather than introducing a separate name-only component.
- `api/services/admin_people.py::_derive_full_name`: existing formatter seam, but it currently renders suffix without the locked comma and only derives during certain edit requests.
- `pipeline/commands/import_justices_csv.py::reconstruct_full_name`: already implements the locked `First Middle Last, Suffix` rule and documents exception handling.
- People directory `missing` indicators/filters: established operator cleanup surface for the new `Name review` state.

### Established Patterns
- `full_name` remains a widely consumed non-null display/dedup anchor, so synchronized compatibility storage is safer than a read-time removal migration.
- Existing extraction provenance uses persistent source metadata (for example `Argument.cover_metadata`) separately from operator-editable values; name-part provenance should follow that separation.
- Phase 36 established that displayed extracted values with editable destinations use one shared copy interaction, including local feedback and disabled `N/A` behavior.
- People create/edit fields are split across Svelte forms and Pydantic allow-lists; derivation must be enforced server-side so no client or import path can bypass it.

### Integration Points
- Main and standalone people editor fields, headings, preview, and server actions.
- FastAPI people create/update schemas and service mutations.
- Job-scoped mini-create and resolve workflows.
- Justice CSV, corpus, seed, and any other person creation/import path.
- Migration/backfill plus persistent People directory review status.
- Every current `CopyableExtractedValue` consumer and future extracted field with an editable destination.

</code_context>

<specifics>
## Specific Ideas

- Canonical examples: `Amy Coney Barrett` and `John G. Roberts, Jr.`.
- The generated preview should update live while name parts are edited and make its non-editable/generated status explicit.
- The attached mockup's stacked structure is intentional because it scales cleanly beneath both narrow and wide inputs.
- Example revised hint: first line `Extracted: William` with copy affordance; second line `High confidence · Raw: WILLIAM`.
- The operator values transparency: best-effort extracted interpretations should remain visible even when uncertain, while ambiguous legacy migration must preserve the original Full Name rather than silently corrupt it.

</specifics>

<deferred>
## Deferred Ideas

None. A general Admin Dashboard attention queue was considered, but the user decided the focused People directory `Name review` filter may fully satisfy the need and should be tried first rather than captured as a new capability.

</deferred>

---

*Phase: 38-full-name-vs-name-parts-rethink*
*Context gathered: 2026-07-15*
