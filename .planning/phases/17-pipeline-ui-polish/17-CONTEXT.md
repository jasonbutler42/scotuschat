# Phase 17: Pipeline UI Polish - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 17 adds two enhancements to the pipeline admin job detail page:

1. **Stage stat cards (PIPE-21)** — The Ingest card shows the source identifier (original filename for uploads, full URL for URL-sourced). The Parse card shows utterance count, distinct speaker count, and the extracted case metadata (case name, argued date) already written to the Argument row by Phase 16.

2. **Source PDF access (PIPE-22)** — A link on the pipeline job detail page lets the operator open the original source PDF in a new browser tab for visual verification against speaker assignments.

**Out of scope:**
- Parse stat snapshots or historical stat tracking — stats are queried at render time from existing DB rows
- Showing docket number on the Parse card (it's set at ingest, not extracted by parse — redundant with the Argument metadata preview already on the page)
- Any changes to the resolve review or approval flow
- Any new pipeline step or re-run behavior changes

</domain>

<decisions>
## Implementation Decisions

### Ingest Card — Source Identifier

- **D-01:** Display behavior is **mode-dependent**:
  - **Upload mode** (`spaces_key` is set): show the **original filename** (e.g., `transcript.pdf`) from the browser upload
  - **URL mode** (`pdf_url` is set): show the **full supremecourt.gov URL** verbatim
- **D-02:** The original upload filename is NOT currently stored — `spaces_key` is a synthetic key (`uploads/{job.id}.pdf`). This requires adding an **`original_filename` column to `admin_jobs`** via Alembic migration, populated at job creation time from the upload form's `pdf_file.filename`.
- **D-03:** For URL-sourced jobs, the display value comes from `pdf_url` already on the AdminJob row — no new storage needed.

### PDF Access UX (PIPE-22)

- **D-04:** The PDF link opens the source PDF **in a new browser tab** using the browser's native PDF viewer. Backend endpoint uses `Content-Disposition: inline` (not `attachment`). No download button needed.
- **D-05:** The link is labeled "View source PDF" (or similar) and is visible on the pipeline job detail page without leaving the view.

### PDF Serving Backend

- **D-06:** One unified endpoint: `GET /api/admin/jobs/{job_id}/pdf`
  - If `spaces_key` is set: redirect (HTTP 302) to a DO Spaces **pre-signed URL** with short TTL (e.g., 15 minutes)
  - Otherwise: stream the file from `pdf_path` on disk (`PipelineRun.pdf_path`) with `Content-Disposition: inline; filename=<original_filename or derived>` and `Content-Type: application/pdf`
- **D-07:** The frontend never needs to know which storage backend is in use — it always calls the same endpoint.

### Parse Card — Stats Source

- **D-08:** Parse stats are **queried at render time** from existing DB tables — no new storage:
  - Utterance count: `COUNT(utterances WHERE pipeline_run_id = latest_parse_run_id)`
  - Speaker count: `COUNT(DISTINCT argument_participants.raw_speaker_label WHERE argument_id = X)`
  - Case name and argued date: already in `data.argument` on the job detail page (written by Phase 16)
- **D-09:** If the job has been re-run (Phase 15 Re-run button), stats reflect the **latest parse run** (highest `pipeline_run_id` for step=parse for this argument).
- **D-10:** Stats section is only shown when the parse step status is `completed`. During running or pending, the card shows only the status badge (no placeholder stats).

### Claude's Discretion

- Whether to fetch parse stats in the existing `GET /api/admin/jobs/{job_id}` response or as a separate sub-request on the frontend
- Exact label and placement of the "View source PDF" link within the job detail page
- Pre-signed URL TTL for Spaces-backed PDFs
- Whether `original_filename` column allows null (yes — for jobs created before the migration)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §v1.3 Pipeline Confidence — PIPE-21, PIPE-22 (2 requirements this phase closes)
- `.planning/ROADMAP.md` §Phase 17 — Goal and 4 success criteria (all must be TRUE)

### Schema & Models — Read Before Writing
- `api/models/models.py` — `AdminJob` (line 324+: `id`, `status`, `current_step`, `argument_id`, `pdf_url`, `spaces_key`, `discrepancies`; no `original_filename` yet — migration needed); `PipelineRun` (line 237+: `pdf_path`, `step`, `status`); `Utterance` (line 272+: `pipeline_run_id`, `argument_id`); `ArgumentParticipant` (line 218+: `raw_speaker_label`, `argument_id`)
- `api/schemas/admin_jobs.py` — `AdminJobResponse` (add `original_filename: Optional[str]` and parse stats fields); `AdminJobCreateURL`, `ResolveRequest`
- `api/alembic/versions/` — read existing migrations for `ALTER TABLE ... ADD COLUMN` pattern; null-allowed column is safe for existing rows

### Existing Admin Job Flow — Extend, Don't Rewrite
- `api/routers/admin.py` — `POST /api/admin/jobs` (line 135+): job creation from URL and upload modes; `original_filename` must be captured here from `pdf_file.filename` for upload mode. `GET /api/admin/jobs/{job_id}` (line 246+): add parse stats to the response.
- `api/services/admin_jobs.py` — `create_job()`: add `original_filename` param; `get_job()`: add parse stats query (utterance count, speaker count from latest parse run)
- `api/services/spaces.py` — existing DO Spaces client; check for pre-signed URL generation pattern (used for photo upload in Phase 12)

### Frontend — Pipeline Job Detail Page
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — 1308 lines; stage cards HTML starts at ~line 458 (STEP_ORDER loop); Argument metadata preview at ~line 350; add stats sub-content inside Ingest and Parse cards; add "View source PDF" link
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — loads job data; extend to include `original_filename` and parse stats from API response

### Prior Phase Context
- `.planning/phases/16-parser-improvements/16-CONTEXT.md` — D-01 through D-09: what Phase 16 extracts (`case_name` to lead Case row, `argued_date` to Argument row); these values are already in `data.argument` on the job detail page via `argument_id`
- `.planning/phases/15-speaker-role-accuracy/15-CONTEXT.md` — D-10: Re-run button behavior; after re-run, a new AdminJob is created — parse stats always reflect the job's own parse run

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/spaces.py` — existing DO Spaces client (boto3); check whether it already supports pre-signed URL generation; if not, the pattern is `client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=900)`
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` `STEP_LABELS` and step card loop (line 458+) — the stats content slots into each card's existing `<div>` after the header row; reuse the card's label/value inline style pattern (`#94a3b8` label, `#e2e8f0` value) already used in the Argument metadata preview (line 370+)
- `api/services/admin_jobs.py` `get_run_id_for_step()` — already queries `PipelineRun` by job_id and step; extend or reuse to get the latest parse run's `pipeline_run_id` for the stats count query

### Established Patterns
- **AdminJobResponse via `model_config = {"from_attributes": True}`** — add new fields (`original_filename`, parse stats) as `Optional[...]` with `None` default; existing rows return None, frontend hides the section
- **Alembic DDL authority** — never `Base.metadata.create_all`; migration adds `original_filename TEXT NULLABLE` to `admin_jobs` table
- **No client-side fetch** — parse stats are returned in the existing `GET /api/admin/jobs/{id}` response, not fetched separately; `+page.server.ts` passes them through `data`
- **Svelte 5 Runes** — `$derived()` for conditional display of stats section (`status === 'completed'`); no stores or `$:` blocks
- **asyncpg `statement_cache_size=0`** — already in engine config; no change needed

### Integration Points
- The `original_filename` is captured at `POST /api/admin/jobs` time from `pdf_file.filename` (UploadFile has a `.filename` attribute in FastAPI/Starlette); stored on `AdminJob` row; returned in every `AdminJobResponse` thereafter
- Parse stats query joins `utterances` (count by `pipeline_run_id`) and `argument_participants` (count DISTINCT `raw_speaker_label` by `argument_id`); the latest parse run ID comes from `get_run_id_for_step(db, job_id, "parse")` which already exists in `admin_jobs.py`
- The `GET /api/admin/jobs/{job_id}/pdf` endpoint is a new route on the existing admin router; it uses the existing `get_db` dependency and the admin token auth already applied router-wide

</code_context>

<specifics>
## Specific Ideas

- **Mode detection for filename display**: `if job.spaces_key: show job.original_filename else: show job.pdf_url` — simple conditional in the Svelte template; no new type field needed
- **PDF link placement**: Below the Argument metadata preview card (or below the Ingest stage card) — "View source PDF" as a plain link styled like the existing "Edit argument metadata" link (`#93c5fd`, underline)
- **Streaming local PDFs**: Use FastAPI's `FileResponse` (from `starlette.responses`) with `media_type="application/pdf"` and `filename` set — handles range requests and proper headers automatically

</specifics>

<deferred>
## Deferred Ideas

- **Showing docket number on the Parse card** — the docket is set at ingest, not extracted by parse, and is already visible in the Argument metadata preview card above the stage cards; redundant
- **Incremental stats during parse** — showing utterance count update in real time while the parse step is running would require polling a stats endpoint during parse; out of scope and adds complexity
- **Download button in addition to View** — PIPE-22 says "open or download"; the operator can use the browser's built-in PDF viewer save/download action after opening inline

</deferred>

---

*Phase: 17-pipeline-ui-polish*
*Context gathered: 2026-06-26*
