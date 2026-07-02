# Phase 19: Pipeline Reliability - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Two independent deliverables in one phase:

1. **Duplicate prevention**: The `arguments` table gets a unique constraint on `(source_docket, question_number)` so re-running ingest for the same argument cannot silently create a second row. The pipeline start form adds an optional docket field that enables a JS preflight duplicate check before submission.

2. **Metadata prefill**: The cover extractor (already runs during parse) is extended to extract docket numbers in addition to `argued_date` and `case_name`. Parse writes extraction results to a new `cover_metadata JSONB` column and auto-populates null metadata fields. The job detail page gains an editable metadata card where the operator reviews and overrides prefilled values.

</domain>

<decisions>
## Implementation Decisions

### Uniqueness Constraint
- **D-01:** Add `source_docket VARCHAR(50) NULL` column to `arguments`. Add UNIQUE constraint on `(source_docket, question_number)`. PostgreSQL NULL semantics apply — multiple rows with `source_docket = NULL` do NOT violate the constraint, so unknown-docket arguments cannot be DB-level deduplicated (preflight or operator awareness is the only check in that case). Migration 0011.
- **D-02:** If ingest hits the unique constraint at DB write time (e.g., preflight was skipped or docket was empty): mark `admin_jobs.status = FAILED` with a human-readable `error_message`. No silent creation of a duplicate row.

### Pipeline Start Form Changes
- **D-03:** Add an optional docket field (text input) and a Q1/Q2 question_number selector (default Q1) to the pipeline start form (`/admin/pipeline`). Both are passed to the ingest subprocess as `--primary-docket` and `--question` args. If the operator fills in the docket, ingest uses it to create a real `Case` row immediately (not a synthetic `job-{N}` placeholder).
- **D-04:** JS preflight fires on form submit if docket is filled: calls `GET /api/admin/arguments/check-duplicate?docket=...&question=...` before the SvelteKit form action. FastAPI checks `arguments.source_docket + question_number` for a match.
- **D-05:** If preflight finds a match: inline warning banner appears above the Submit button with a link to the existing argument. Two buttons: "Cancel" and "Start anyway". Operator can proceed if they choose.
- **D-06:** If the docket field is empty: no preflight fires. The DB unique constraint is the backstop. Upload mode gets no preflight (no docket known at submit time).

### Argument Model — New Columns (Migration 0011)
- **D-07:** Add `cover_metadata JSONB NULL` to `arguments`. Parse always writes the raw cover extractor output here unconditionally after parse completes. Used by the job detail page to render hint text.
- **D-08:** Make `Argument.argued_date` nullable. Job-driven ingest leaves it `NULL` instead of using today's date as a synthetic placeholder. Empty field in the editor = "not yet extracted" — no separate indicator needed.

### Metadata Write-back (Parse Step)
- **D-09:** At the end of parse, the parse step runs the cover extractor and: (a) always writes raw extraction output to `cover_metadata` (unconditional); (b) auto-populates null main fields — `argued_date`, `case_name`, `source_docket` — from extraction results if and only if those fields are currently NULL. Does NOT overwrite operator-entered values.
- **D-10:** If cover extraction fails or returns empty: leave null fields as null, continue parse normally. No parse failure for metadata-only issues. The job detail metadata card will show empty inputs signaling the operator to fill them in manually.
- **D-11:** Empty field = not yet extracted. No separate "extraction succeeded/failed" badge needed — emptiness is the signal.

### Cover Extractor Extension
- **D-12:** Extend `cover_extractor.py` to extract `primary_docket` (the docket number from the cover page) in addition to `argued_date` and `case_name`. Must support both Alderson and Heritage transcript cover formats. Docket numbers appear as "No. 14-556" on Alderson covers; pattern may differ on Heritage. Update `pipeline/tests/test_cover_extractor.py` with docket extraction tests.

### Job Detail Page — Metadata Card
- **D-13:** The job detail page (`/admin/pipeline/[id]`) gains a new "Argument Metadata" card with editable inputs for case name, docket, and argued date. This is the primary place the operator reviews and overrides prefilled values — no need to navigate to the argument admin editor.
- **D-14:** When `cover_metadata` contains a value for a field that is already populated (operator-entered), the editor shows hint text below the input: `Extracted: [extracted value]`. Operator decides whether to apply the extracted value or keep their entry. When a field is null and extraction found a value, it is auto-populated and shown in the input (no hint — it's already the value).
- **D-15:** Saving the metadata card calls a new FastAPI admin endpoint that updates the `Argument` row (`argued_date`, `source_docket`) and the linked `Case` row (`case_name`) in the DB.

### Folded Todos
- **"Prevent duplicate argument creation during ingest"** — folded. This todo is the core of PIPE-25 and is addressed by D-01 through D-06.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — PIPE-25 (duplicate prevention) and PIPE-26 (metadata prefill) are the two requirements for this phase; success criteria defined here
- `.planning/ROADMAP.md` — Phase 19 goal, success criteria, and phase boundary

### Existing Models & Schema
- `api/models/models.py` — `Argument` model (lines 160–183): `argued_date NOT NULL` (becomes nullable), `question_number`, `status`. `AdminJob` model (line 327): `pdf_url`, `spaces_key`, `original_filename`, `argument_id`. `Case` model: `docket_number UNIQUE NOT NULL`, `case_name`. Read before writing migration 0011.
- `alembic/versions/` — most recent migration is `0010_add_is_justice.py`; new migration is `0011`. Follow existing Alembic hand-written migration pattern (not autogenerate).

### Existing Pipeline Code
- `pipeline/commands/ingest.py` — full ingest command. `_derive_metadata_from_key()` (lines ~130–140) generates synthetic placeholders — this behavior changes with D-03/D-08. `_run_ingest_inner()` Step 5 creates the `Argument` row without a source_docket — must be updated to populate `source_docket` when provided.
- `pipeline/parser/cover_extractor.py` — existing extractor. Currently extracts `argued_date` and `case_name`. Must be extended to also extract `primary_docket` (D-12). Fail-safe: returns `{}` on any exception. Tests are in `pipeline/tests/test_cover_extractor.py`.
- `pipeline/commands/parse.py` — parse command. Must call cover extractor at the end of parse and write results per D-09.

### Existing Admin UI
- `app/src/routes/admin/pipeline/+page.svelte` — pipeline start form. Current form has URL/upload modes but no docket or question_number field. Needs new optional docket input + Q1/Q2 selector (D-03).
- `app/src/routes/admin/pipeline/+page.server.ts` — start form action. Passes args to ingest subprocess. Needs `--primary-docket` and `--question` forwarding.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — job detail page. Needs new "Argument Metadata" card (D-13/D-14).
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — job detail load + actions. Needs to load `cover_metadata` from `Argument` and serve it to the metadata card; handle save action for metadata updates.

### Existing Admin FastAPI Layer
- `api/routers/` and `api/services/` — existing admin CRUD patterns. A new endpoint `GET /api/admin/arguments/check-duplicate?docket=...&question=...` and a new `PATCH /api/admin/arguments/{id}/metadata` (or similar) endpoint are needed. Follow the `X-Admin-Token` auth pattern used by all existing admin endpoints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AdminJob.pdf_url`, `AdminJob.spaces_key`, `AdminJob.original_filename` — source tracking already exists on `admin_jobs`. The `source_docket` uniqueness approach is consistent: we're adding analogous source tracking to `Argument` itself.
- `cover_extractor.py` is already tested and fail-safe — extend it, don't rewrite it. Its return signature `{argued_date: date, case_name: str}` expands to also include `primary_docket: str | None`.
- `use:enhance` + form actions pattern throughout the admin UI — JS preflight can use `onsubmit` intercept before `use:enhance` fires, or a custom submit handler that calls a fetch before delegating to the form action.
- `admin_jobs.discrepancies JSONB` — already used for resolve-step discrepancy data. The new `arguments.cover_metadata JSONB` follows the same JSONB-column-for-structured-output pattern but lives on `arguments` (not `admin_jobs`) so the argument editor can read it directly.

### Established Patterns
- Alembic hand-written migrations (not autogenerate); FK ordering matters. `op.execute("COMMIT")` before `ALTER TYPE ADD VALUE` — not needed for column adds, but follow migration 0010 as the closest template.
- Ingest step is the only place `Argument` rows are created — all uniqueness enforcement happens there (no other code path creates Argument rows).
- `PipelineRun.pdf_url` and `PipelineRun.pdf_path` already track source at the pipeline-run level. The new `Argument.source_docket` tracks source at the argument level for business-key deduplication.
- Job-driven ingest path (`args.job_id is not None`) currently calls `_derive_metadata_from_key` for synthetic values. D-03/D-08 change this: if `args.primary_docket` is set (from form), use it; if not set, leave `source_docket = NULL` and `argued_date = NULL`.
- Cover extractor is called from parse step. Look at `pipeline/commands/parse.py` for where to hook in the write-back logic at D-09.

### Integration Points
- `Argument.source_docket` (new) → populated by ingest from `args.primary_docket`, updated by parse from cover extractor (only if null)
- `Argument.cover_metadata` (new) → always written by parse after cover extraction; read by job detail page to render hint text
- `Argument.argued_date` (nullable after migration) → populated by parse from cover extractor (only if null); editable on job detail metadata card
- `Case.case_name` → updated by parse from cover extractor (only if the linked case's name still matches the synthetic pattern)
- New FastAPI endpoint `GET /api/admin/arguments/check-duplicate` → called by JS preflight on pipeline start form
- New FastAPI endpoint for metadata save → called by job detail page metadata card save action

</code_context>

<specifics>
## Specific Ideas

- The inline duplicate warning on the pipeline start form should appear between the submit button and the form fields (above the button), show the docket and question number that matched, include a direct link to the existing argument admin page, and offer "Cancel" and "Start anyway" as distinct CTAs.
- The "Extracted: [value]" hint text on the job detail metadata card should be secondary/muted text below the field — not a badge or icon. Small text, consistent with the existing admin UI aesthetic.
- The docket field on the start form should be labeled clearly as optional (e.g., placeholder text "e.g. 14-556 (optional)") so operators understand they can skip it.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **"Live polling for pipeline list page job cards"** — this belongs to Phase 20: Live Pipeline Status (PIPE-23, PIPE-24). Reviewed here for awareness; not in Phase 19 scope.

</deferred>

---

*Phase: 19-Pipeline Reliability*
*Context gathered: 2026-06-30*
