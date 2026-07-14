# Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace free-text `court_tenures.seat` with a constrained Chief/Associate office model, migrate existing tenure data without silent loss, and update every database, API, import, editor, and read-only display integration to use the new model. This phase does not add other tenure classifications or change argument-specific roles.

</domain>

<decisions>
## Implementation Decisions

### Office model
- **D-01:** The active tenure model is binary: every tenure is either Chief or Associate. Numbered-seat distinctions will not remain in the active model.
- **D-02:** A Justice elevated from Associate to Chief retains two tenure periods: an Associate row ending at elevation and a Chief row beginning at elevation.
- **D-03:** Every saved tenure row must have exactly one valid office. Blank, unset, and Unknown are not valid persisted values.
- **D-04:** The Chief/Associate restriction applies to every write path, including the editor, API, imports, scripts, and migrations.

### Existing-data migration
- **D-05:** Recognized numbered values such as `Associate Justice Seat 3` normalize to Associate.
- **D-06:** The dry-run and execution audit report records every changed row and its original value; numbered-seat removal must never be silent.
- **D-07:** A blank or unrecognized legacy value blocks migration until it receives an explicit Chief/Associate resolution. The migration must not infer or default a value.
- **D-08:** Migration requires a non-writing dry run before a separate explicit execution action.
- **D-09:** Execution is atomic. Any validation or update failure rolls back all changes.

### Editor behavior
- **D-10:** A new tenure row defaults to Associate.
- **D-11:** If invalid data reaches the editor, show the original invalid value with a clear error and block the entire profile save until the operator explicitly selects Chief or Associate. Never coerce it silently.
- **D-12:** Office changes remain local form state and persist through the existing profile Save action, atomically with dates and other tenure changes.
- **D-13:** The segmented control always has exactly one selected option; clicking the active segment cannot deselect it.

### Terminology and display
- **D-14:** The editor segments are labeled `Chief` and `Associate`.
- **D-15:** Read-only tenure summaries and Justice popovers display the formal titles `Chief Justice` and `Associate Justice`.
- **D-16:** The tenure field is called `Office`, not `Role`, because `Role` is reserved for argument-specific roles.
- **D-17:** Rename `seat` to `office` end to end across the database column, ORM, schemas, API payloads, imports, services, tests, UI state, form serialization, and read-only consumers. This is not a UI-only label change and does not require a compatibility alias.

### the agent's Discretion
- Exact enum/check-constraint mechanism and internal constant names, provided only the two locked offices are writable.
- Audit-report file format and command naming, provided the required dry-run, original-value traceability, explicit execution, and atomicity contracts are met.
- Exact visual styling details, provided the control reuses the established segmented-toggle idiom and satisfies the locked behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 37 goal, open design question, and success criteria, especially preservation or explicit migration of existing numbered-seat data.
- `.planning/REQUIREMENTS.md` — PEOPLE-08 requirement mapping for Phase 37.
- `.planning/PROJECT.md` — v1.6 Phase 37 milestone boundary and the intentionally deferred design decision now resolved here.

### Existing implementation
- `app/src/routes/admin/people/[id]/+page.svelte` — current tenure-row free-text seat editor and existing Bench/Advocate segmented-control idiom.
- `app/src/routes/admin/people/[id]/+page.server.ts` — current tenure JSON form parsing and API serialization using `seat`.
- `api/models/models.py` — current `CourtTenure.seat` database model.
- `api/schemas/admin_people.py` — current tenure request/response schemas using `seat`.
- `api/services/admin_people.py` — tenure replacement, serialization, and role lookup integration points.
- `pipeline/commands/import_justices_csv.py` — current importer emits `Chief Justice` and `Associate Justice` and deduplicates using seat.
- `app/src/lib/components/SpeakerPopover.svelte` — read-only public tenure-title display.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Bench/Advocate segmented controls in `app/src/routes/admin/people/[id]/+page.svelte` and `app/src/routes/admin/people/new/+page.svelte`: reuse their visual and accessible radiogroup/button idiom for Chief/Associate.
- Existing tenure-row form state and hidden JSON serialization in the edit page: replace `seat` with the locked `office` field while retaining atomic profile saving.
- `pipeline/commands/import_justices_csv.py` already maps source sections to the two formal titles, so its source classification can feed the constrained office model.

### Established Patterns
- Person edits submit tenures as one JSON array and the service replaces all tenure rows together; office changes must remain part of this existing atomic form flow.
- Bench/Advocate segmented controls keep one explicit selection and submit through hidden form state; the new office control should follow that interaction pattern.
- Bench role labels elsewhere are derived from the tenure covering an argument date; those consumers must switch from `seat` to `office` without changing date-window semantics.

### Integration Points
- Database/Alembic migration, `CourtTenure` ORM model, Pydantic schemas, admin people services/routes, SvelteKit server form types, editor state, import command, speaker/participant projections, popovers, and all tests/fixtures referring to `seat`.
- The migration utility needs dry-run and explicit execute modes, an original-to-new audit report, blocking detection for unresolved rows, and one transaction for execution.

</code_context>

<specifics>
## Specific Ideas

- “Office” deliberately avoids reusing “role,” which is reserved throughout the product for argument-specific roles.
- Compact editor wording (`Chief` / `Associate`) and formal read-only wording (`Chief Justice` / `Associate Justice`) are intentionally different.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Context gathered: 2026-07-14*
