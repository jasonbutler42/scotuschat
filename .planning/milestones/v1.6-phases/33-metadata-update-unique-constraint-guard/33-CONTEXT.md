# Phase 33: `update_argument_metadata` unique-constraint guard - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Prevent every write path that can create or change the `arguments(source_docket, question_number)` pair from surfacing an unhandled database error. The operator-facing metadata PATCH must detect a collision, return a precise `409 Conflict`, and render actionable feedback on both admin surfaces that use the shared Argument Details card. Existing ingest/import behavior remains channel-appropriate but must be audited against the same uniqueness predicate. Blank-value validation belongs to Phase 34 and is not part of this phase.

</domain>

<decisions>
## Implementation Decisions

### HTTP conflict contract
- **D-01:** A docket/question collision returns **`409 Conflict`**, not `422`.
- **D-02:** The response uses FastAPI's structured `detail` object with a stable `code` of `duplicate_argument`, a clear human-readable `message`, and `conflicting_argument_id`.
- **D-03:** The message identifies the submitted pair: **“An argument already uses docket {docket}, question {number}. Open conflicting argument.”** The final phrase is rendered as a link to `/admin/arguments/{conflicting_argument_id}` that opens in a new tab.

### Operator feedback and recovery
- **D-04:** Render the collision in the existing inline `role="alert"` area inside `ArgumentDetailsCard.svelte`; do not add a separate page-level banner. Because both admin routes reuse this component, both surfaces must behave identically.
- **D-05:** Preserve every submitted value after the failed save — docket pills, question number, and argued date — so the operator can compare or correct the attempted values.
- **D-06:** Move keyboard focus to the collision alert after the failed save. The conflicting-record link must remain keyboard accessible and open in a new tab using the safe external-tab attributes appropriate for the component.

### Guard consistency
- **D-07:** Use a pre-write existence check for precise conflict data **plus** an `IntegrityError` fallback for race safety. A pre-check alone is insufficient.
- **D-08:** Evaluate the **final combined pair** on partial PATCHes: combine submitted values with the argument's stored values and exclude the current argument row from the collision query. An unchanged save must not conflict with itself.
- **D-09:** Audit every code path that writes `source_docket` and/or `question_number` against the same uniqueness predicate. HTTP metadata saves use the new `409` contract; offline ingest/import paths retain their existing channel-specific duplicate handling rather than being forced into HTTP wording.
- **D-10:** In the fallback, rollback first and map only the named `uq_arguments_source_docket_question` violation to `duplicate_argument`. Other constraint failures must remain sanitized and separately identifiable; they must not be mislabeled as duplicates or expose raw asyncpg/database text.

### Agent's Discretion
- Exact helper/function placement for the shared collision predicate and conflict payload construction.
- Internal logging structure for sanitized non-duplicate constraint failures.
- Test file organization, provided coverage proves the service pre-check, router fallback, both SvelteKit actions, shared component behavior, partial-update/self-exclusion rules, and the existing ingest/import guarantees.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/ROADMAP.md` §"Phase 33: `update_argument_metadata` unique-constraint guard" — authoritative goal and three success criteria.
- `.planning/REQUIREMENTS.md` §"PIPE-27" — requires a clean 409/422 instead of an unhandled 500.

### Backend contract and write path
- `api/services/admin_arguments.py` — `check_duplicate_argument` is the existing reusable query pattern; `update_argument_metadata` builds the partial update pair and commits it.
- `api/routers/admin.py` — metadata PATCH currently catches every `IntegrityError` as a generic `409 constraint_violation`; this is where the new structured HTTP contract and rollback behavior connect.
- `api/schemas/admin_arguments.py` — `MetadataUpdate` defines partial-update/null semantics for docket arrays and free-text question numbers.
- `api/models/models.py` — `Argument.__table_args__` defines `uq_arguments_source_docket_question` and PostgreSQL NULL uniqueness semantics.

### Operator surfaces
- `app/src/lib/components/ArgumentDetailsCard.svelte` — shared form, existing inline `role="alert"`, failure-state docket restoration, and focus/link rendering point.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — `saveJobMetadata` currently collapses all non-OK responses to generic copy and only returns docket values on failure.
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — `saveArgumentDetails` mirrors the same metadata PATCH and generic failure behavior.

### Other uniqueness writers to audit
- `pipeline/commands/ingest.py` — insert-time `IntegrityError` handling for duplicate arguments.
- `pipeline/commands/import_convokit.py` — derives the next per-docket question number and retains an `IntegrityError` safety net.
- `pipeline/commands/parse.py` — can update `source_docket` from extracted cover metadata and must be included in the writer audit.

### Existing regression coverage
- `api/tests/test_question_number_nullable.py` — current source-inspection regression only proves the router mentions `IntegrityError`; Phase 33 needs behavioral collision coverage beyond this test.
- `api/tests/test_admin_arguments_service.py` — established service-test location for admin argument updates.
- `api/tests/test_admin_arguments_routes.py` — established route-test location for HTTP response contracts.

No external specs or ADRs — requirements are fully captured by ROADMAP.md, REQUIREMENTS.md, and the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `check_duplicate_argument()` already performs the core `(source_docket, question_number)` lookup. It can inform a shared helper, but the metadata-update variant must exclude the current argument and return the conflicting id.
- `ArgumentDetailsCard.svelte` is already shared by the pipeline-job detail page and argument editor and already contains the inline alert region, making consistent feedback possible without duplicating markup.
- The ingest and ConvoKit importer already demonstrate layered duplicate handling: proactive selection/checking plus database-constraint fallback.

### Established Patterns
- SvelteKit form actions return `fail(...)` payloads and the shared component restores submitted docket pills from `form.dockets`; Phase 33 extends that preservation contract to question number and argued date.
- FastAPI uses `HTTPException(detail=...)`; the chosen payload remains inside `detail` while changing it from a generic string to a stable object.
- Database error responses must be sanitized. Raw asyncpg constraint text is never returned to clients.
- PostgreSQL allows multiple rows when either unique-key column is NULL, so a collision exists only for a concrete final pair; Phase 34 separately owns rejection of blank docket values.

### Integration Points
- `update_argument_metadata()` computes `values_to_set`; the final-pair collision check must occur after normalization/parsing determines the effective values and before the UPDATE.
- Both SvelteKit actions must parse the structured `409` response and pass typed collision data plus all submitted values to `ArgumentDetailsCard.svelte`.
- The shared component owns alert rendering, focus management, and the new-tab link, ensuring identical behavior on both routes.
- The named-constraint fallback must handle a race between the pre-check and commit, rollback the failed transaction, and still recover the conflicting argument id for the response without using the failed transaction state.

</code_context>

<specifics>
## Specific Ideas

- The operator-facing link text is exactly **“Open conflicting argument”** and targets `/admin/arguments/{conflicting_argument_id}` in a new tab.
- The preferred message is concise and identifies both values: **“An argument already uses docket {docket}, question {number}. Open conflicting argument.”**

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Edit affordance on utterances and speaker popover** — explicitly kept out of Phase 33. It was moved from the recurring pending-todo queue to backlog Phase 999.9 so it can be prioritized later through `$gsd-review-backlog`.

</deferred>

---

*Phase: 33-metadata-update-unique-constraint-guard*
*Context gathered: 2026-07-13*