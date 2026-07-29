# Phase 34: Blank case_name/docket_number validation - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Prevent the argument editor and pipeline metadata PATCH paths from clearing required case-name or canonical docket values. Blank, whitespace-only, explicit-null, and empty-collection submissions must not corrupt `Case.slug`, `Case.docket_number`, `Case.docket_number_norm`, or `Argument.source_docket`. The phase adds authoritative Pydantic validation, equivalent required behavior in the native and pill-based controls, and actionable feedback through the existing admin forms. It does not change docket formatting rules, dedup semantics, question-number optionality, or repair historical data.

</domain>

<decisions>
## Implementation Decisions

### Docket collection and canonical value
- **D-01:** When `source_dockets` contains valid and blank entries, trim entries, drop blanks, de-duplicate valid values in first-seen order, and accept the result when the applicable minimum rule is satisfied.
- **D-02:** Normalize the collection before selecting the canonical docket. The first remaining valid entry becomes `source_docket`, even when blank entries preceded it.
- **D-03:** Explicit `null` for a required case-name or docket field is invalid. Field omission retains PATCH semantics and means “leave unchanged.”
- **D-04:** When an operator submits no docket pills, preserve the visibly empty attempted state after failure; do not silently restore the saved docket.
- **D-05:** The pill-based docket control must provide an equivalent client-side required check. Backend schema validation remains authoritative.

### Whitespace normalization
- **D-06:** Schema validators strip leading and trailing whitespace and return the normalized value. Otherwise-valid trimmed values are accepted; values empty after trimming are rejected.
- **D-07:** Preserve internal whitespace exactly. Do not collapse repeated internal spaces or otherwise rewrite case titles or docket text.
- **D-08:** Blank detection follows Python `str.strip()` semantics, including tabs, newlines, and recognized Unicode whitespace.

### Operator feedback and recovery
- **D-09:** Render required-value failures in each form's existing inline `role="alert"` region rather than adding a new error component or page-level banner.
- **D-10:** Use field-specific operator copy: **“Case name is required.”** and **“Add at least one docket.”**
- **D-11:** When multiple required fields fail, show every field-specific error together and move keyboard focus to the first invalid field.
- **D-12:** Preserve the full attempted submission after failure, including blank invalid values and all other submitted values, so the operator corrects only what failed.

### API validation contract
- **D-13:** Keep FastAPI/Pydantic's standard structured `422` validation-error envelope; do not introduce application-specific blank-field codes.
- **D-14:** Explicit null, empty strings, whitespace-only strings, and empty docket collections share the same missing-required-value classification.
- **D-15:** SvelteKit actions identify required-field failures from structured Pydantic error `loc` values, never by matching human-readable validation messages. Other `422` conditions retain their existing distinct handling.

### Agent's Discretion
- Choose whether explicitly supplied `source_dockets` must contain at least one nonblank docket at schema validation time or whether an equally strict PIPE-28-compatible enforcement point is more appropriate. The result must still make it impossible for either save path to clear the canonical docket.
- Choose whether a request that supplies disagreeing `source_docket` and `source_dockets` is rejected or uses the array as authoritative. The choice must be deterministic, tested, and preserve D-01 through D-05.
- Exact validator/helper placement, error parsing helper structure, focus implementation, and test organization are left to research and planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and prior contract
- `.planning/ROADMAP.md` §"Phase 34: Blank case_name/docket_number validation" — authoritative phase goal, fixed implementation direction, success criteria, and UI hint.
- `.planning/REQUIREMENTS.md` §"PIPE-28" — clearing case name or docket must produce validation rather than slug/dedup corruption.
- `.planning/phases/33-metadata-update-unique-constraint-guard/33-CONTEXT.md` — immediately preceding metadata contract, submitted-value preservation, structured error handling, and shared-form decisions that Phase 34 must preserve.

### Backend validation and writes
- `api/schemas/admin_arguments.py` — `ArgumentUpdate` and `MetadataUpdate` are the Pydantic v2 request schemas that require nonblank normalization and validation.
- `api/services/admin_arguments.py` — `update_argument` writes `Case.case_name`, slug, docket, and normalized docket; `update_argument_metadata` normalizes docket arrays, derives canonical `source_docket`, and updates lead-case metadata.
- `api/services/argument_uniqueness.py` — defines the canonical `(source_docket, question_number)` lookup whose semantics depend on preserving a concrete docket value.

### Operator surfaces
- `app/src/lib/components/ArgumentDetailsCard.svelte` — shared metadata form, existing inline alert, attempted-value restoration, and focus behavior for docket failures.
- `app/src/lib/components/DocketPillInput.svelte` — custom docket collection control that needs required-state behavior equivalent to a native required input.
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — owns the Case card `case_name`/`docket_number` save and the shared argument-details metadata save.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — sends normalized `source_dockets` to the metadata endpoint and must map structured validation locations into preserved form failures.

No external specs or ADRs — requirements are fully captured by the roadmap, PIPE-28, the Phase 33 contract, and the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Pydantic v2 `field_validator` on `ArgumentUpdate` and `MetadataUpdate` provides the roadmap-prescribed authoritative boundary and can return stripped values.
- `ArgumentDetailsCard.svelte` already centralizes docket submission for both the argument editor and pipeline job detail page and already has a focusable inline alert plus attempted-value restoration.
- Phase 33 already established structured failure parsing and preservation of docket, question-number, and date attempts across both SvelteKit actions.

### Established Patterns
- PATCH omission is distinct from explicit clearing through Pydantic `model_fields_set`; Phase 34 preserves omission while rejecting explicit null/blank for required fields.
- Metadata forms submit a full `source_dockets` array, not merely legacy `source_docket`; validating only the singular field would leave the live UI path unprotected.
- Docket arrays currently trim entries, discard blanks, de-duplicate in insertion order, and use the first normalized entry as `source_docket`; D-01/D-02 retain that normalization for mixed valid input while closing the all-empty case.
- SvelteKit form actions use `fail(...)` payloads and `use:enhance` without resetting failed form values.

### Integration Points
- `ArgumentUpdate.case_name` and `.docket_number` protect `update_argument` before `_derive_slug` or docket normalization can receive an empty string.
- `MetadataUpdate.case_name`, `.source_docket`, and `.source_dockets` protect `update_argument_metadata`; collection validation must align with its canonical-first-docket behavior.
- The Case card and `ArgumentDetailsCard` have separate action owners on `/admin/arguments/[id]`; both must map standard Pydantic `422` locations to the selected field-focused feedback.
- The custom pill control cannot rely solely on a native text input's `required` attribute, so its empty-state check must participate in submission while remaining backed by server validation.

</code_context>

<specifics>
## Specific Ideas

- Required-error copy is exactly **“Case name is required.”** and **“Add at least one docket.”**
- Multiple required errors appear together in the existing alert, while focus moves to the first invalid control rather than to the alert.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 34-blank-case-name-docket-validation*
*Context gathered: 2026-07-14*
