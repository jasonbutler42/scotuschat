# Phase 24: Pipeline List Page - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Update `/admin/pipeline/` — the pipeline list page — with four targeted changes:

1. Replace the question number `<select>` dropdown with a free-text `<input type="text">` field (PLIST-01)
2. Replace the single docket text input with a pill/tag input consistent with Phase 23's `ArgumentDetailsCard` pattern, backed by a new shared `DocketPillInput.svelte` sub-component (PLIST-02)
3. Show all pipeline runs in the table (not just the most recent 10); rename section from "Recent Runs" to "All Runs" (PLIST-03)
4. Replace the current single-status badge + separate Step column with a compound badge that combines stage and status (e.g., "Parse · Running", "Resolve · Needs Review", "Completed") — Step column removed (PLIST-05)

PLIST-04 (incomplete toggle) is already fully implemented and requires no changes.

</domain>

<decisions>
## Implementation Decisions

### Question Number Field (PLIST-01)
- **D-01:** Replace `<select name="question_number">` with `<input type="text" name="question_number">`. No browser constraints (no `min`, `max`, `pattern`, or `type="number"`). FastAPI already coerces to `int`; it returns 422 if the value is unparseable.
- **D-02:** Placeholder and label stay the same. Default value behavior: the old select defaulted to "1" — the text input should pre-fill with "1" for the same UX.

### Docket Pill Input (PLIST-02)
- **D-03:** Extract a shared `DocketPillInput.svelte` sub-component from `ArgumentDetailsCard.svelte`. It encapsulates: pill `$state`, Enter-key add handler, remove handler, hidden `<input type="hidden" name="docket[]" value="...">` per pill, and the pill display + remove button UI.
- **D-04:** `ArgumentDetailsCard.svelte` is refactored to import and use `DocketPillInput.svelte` instead of its current inline pill logic. Behavior must be identical post-refactor.
- **D-05:** The New Run form's `+page.svelte` imports and uses `DocketPillInput.svelte` for the docket field. The component renders inside the existing `<form method="POST" enctype="multipart/form-data">` — no nested form issues.
- **D-06:** `DocketPillInput.svelte` accepts at minimum an `initialValues: string[]` prop (for `ArgumentDetailsCard`'s `savedValues.dockets`) and a `name` prop (default `"docket[]"`). The New Run form passes `initialValues={[]}` (empty on load).

### Multi-Docket Submission for New Runs
- **D-07:** When operator enters multiple docket pills and clicks "Start Run", the SvelteKit server action uses the **first pill** as `primary_docket` (sent to FastAPI `POST /api/admin/jobs`) and **immediately PATCHes** the new argument with all remaining pills after the run is created. This requires a second round-trip in the action before redirecting to `/admin/pipeline/{id}`.
- **D-08:** The duplicate preflight check fires for **every pill** before submit. If any `(docket, question_number)` pair matches an existing argument, the warning banner shows. The existing `check-duplicate` endpoint is called once per pill (sequential or parallel — researcher decides).
- **D-09:** The `duplicateWarning` state should show which specific docket triggered the warning so the operator knows which one matches.

### Runs Table (PLIST-03)
- **D-10:** Remove the `limit` from `list_jobs` service call entirely (pass `limit=None` or remove the `.limit()` clause from the SQLAlchemy query). The API endpoint signature change: `limit` param removed or made optional and defaulting to no limit.
- **D-11:** Section heading changes from "Recent Runs" to "All Runs".
- **D-12:** No pagination UI. Single query, all rows.

### Compound Status Badge (PLIST-05)
- **D-13:** The Status column badge becomes a compound label combining `current_step` and `status`. Format: `"{Step} · {status_label}"` when a step is active (e.g., "Parse · Running", "Resolve · Needs Review") or just `"{status_label}"` when Completed (no step prefix needed).
- **D-14:** The separate "Step" column is **removed** from the table. Compound badge in the Status column carries all the information.
- **D-15:** `badgeLabel()` is updated to accept both `status` and `current_step`. `badgeStyle()` remains driven by `status` alone (color meaning stays consistent). Step capitalization: "Ingest", "Parse", "Resolve" (title case). "Needs Review" maps from `paused` status (existing behavior).
- **D-16:** When `current_step` is null (pending state before ingest starts), the badge shows just the status label ("Pending").

### Claude's Discretion
- Whether the `DocketPillInput.svelte` `name` prop defaults to `"docket[]"` or is required — researcher can determine the cleanest API
- Exact props interface for `DocketPillInput.svelte` beyond `initialValues` and `name` (e.g., whether it emits a `change` event or is fully self-contained via hidden inputs)
- How to PATCH additional dockets onto the new argument after run creation — whether this uses the existing `ArgumentUpdate` endpoint or a new dedicated endpoint (researcher audits the available save paths from Phase 23)
- Whether preflight pill checks fire in parallel (Promise.all) or sequentially — either works; pick the simpler implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Pipeline List Page (the file being changed)
- `app/src/routes/admin/pipeline/+page.svelte` — current page: docket text input, question select, Recent Runs table (limit 10), badgeLabel/badgeStyle helpers. Replace docket input, replace question select, update table and badges.
- `app/src/routes/admin/pipeline/+page.server.ts` — server load (calls `/api/admin/jobs`) and form action (reads `primary_docket`, `question_number`, posts to FastAPI). Update to read `docket[]` pills, forward first pill as `primary_docket`, PATCH remaining pills after run creation.

### Phase 23 Component (shared sub-component source)
- `app/src/lib/components/ArgumentDetailsCard.svelte` — contains the inline pill implementation to extract into `DocketPillInput.svelte`. Also the first consumer to be refactored to import the new sub-component.

### Backend: Admin Jobs Endpoint
- `api/routers/admin.py` — `POST /api/admin/jobs` accepts `primary_docket: Optional[str] = Form(None)`, `question_number: int = Form(1)`. `GET /api/admin/jobs` passes `limit=10` to the service — this limit gets removed.
- `api/services/admin_jobs.py` — `list_jobs(db, limit=10, incomplete=False)` — the `limit` param is removed or made optional (no limit). Check what PATCH/update path is available for saving additional dockets to a new argument.

### Backend: Duplicate Check Endpoint
- `api/routers/admin.py` `GET /api/admin/check-duplicate?docket=X&question=Y` — called once per pill during preflight. Review signature to confirm it accepts one docket at a time.

### Backend: Argument Update (for multi-docket PATCH)
- `api/routers/admin.py` — argument metadata PATCH endpoint; check if it accepts `docket[]` / consolidated dockets. See Phase 23 decisions (D-05: server reads `FormData.getAll('docket[]')`) for the existing save path from `ArgumentDetailsCard`.
- `api/services/admin_arguments.py` — argument metadata update service; check if `source_docket` update path is available for saving additional dockets.

### Schema
- `api/schemas/admin_jobs.py` — `AdminJobResponse` has `status: AdminJobStatus` and `current_step: Optional[AdminJobStep]`. Both fields feed into the compound badge.

### Requirements
- `.planning/REQUIREMENTS.md` — PLIST-01 through PLIST-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/lib/components/ArgumentDetailsCard.svelte` — the pill `$state`, Enter-key handler, `removePill()`, hidden input pattern, and pill UI markup are all extractable into `DocketPillInput.svelte`. This is the primary source.
- `badgeLabel()` and `badgeStyle()` functions in `+page.svelte` — update these to accept `current_step` for compound labels. Style (color) stays driven by `status` alone.
- `handleToggle()` / incomplete toggle — already works; no changes.
- `$effect` polling (unconditional `invalidateAll()` every 1 second) — keep as-is for PIPE-23/24 compliance.

### Established Patterns
- **Svelte 5 Runes exclusively**: `$state`, `$derived`, `$effect` — no `export let`, no `$:` reactive blocks
- **Inline CSS dark design system**: `#0f1117` page bg, `#1e293b` card bg, `#334155` borders, `#e2e8f0` primary text, `#94a3b8` muted text
- **`DocketPillInput` precedent**: D-04/D-05 from Phase 23 — Enter adds pill, hidden `docket[]` inputs serialize for the form, remove button per pill
- **Form action pattern**: `enctype="multipart/form-data"` already set (needed for file uploads); pill hidden inputs serialize correctly in multipart

### Integration Points
- `app/src/lib/components/DocketPillInput.svelte` — new file; `ArgumentDetailsCard.svelte` and `+page.svelte` both import it
- `api/services/admin_jobs.py` `list_jobs()` — remove `limit` param; called from `api/routers/admin.py` `GET /api/admin/jobs`
- `+page.server.ts` form action — reads `docket[]` (multiple values) instead of `primary_docket` (single); sends first pill to FastAPI; PATCHes remaining pills after run creation

</code_context>

<specifics>
## Specific Ideas

- Compound badge "Completed" has no step prefix — just "Completed". All other statuses prefix with the step name: "Ingest · Pending", "Parse · Running", "Resolve · Needs Review", "Ingest · Failed", etc.
- The removed Step column should not be replaced — the table becomes: Status (compound badge) | Created | View. Simpler and cleaner.
- When multiple docket pills trigger a duplicate warning, show which specific docket matched (D-09) — update `duplicateWarning` state to include `docket: string` (the specific pill that matched).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 24-pipeline-list-page*
*Context gathered: 2026-07-06*
