# Phase 7: Pipeline Runner - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 delivers the full operator pipeline runner in the admin UI:

1. **Start a run** — operator enters a transcript PDF URL or uploads a local PDF file via a two-mode form at `/admin/pipeline`
2. **Live step monitoring** — `/admin/pipeline/[job_id]` shows three step cards (Ingest / Parse / Resolve) updating every 2.5s without a page reload; steps auto-advance when no discrepancies
3. **Discrepancy review** — when resolve produces flagged matches, the Resolve card pauses and shows an inline review table; operator confirms or corrects each match before continuing
4. **Resumable jobs** — job state persisted in `admin_jobs` DB table; operator can close the browser and return to the same URL to resume

No people directory, no full metadata editing. Phase 8 builds on the `argument_id` that this phase produces.

</domain>

<decisions>
## Implementation Decisions

### Subprocess Model

- **D-01:** Pipeline steps are invoked via **`subprocess.Popen`** — one OS process per step (`python -m pipeline ingest ...`, `python -m pipeline parse ...`, `python -m pipeline resolve ...`). No asyncio nesting conflict, clean process isolation. Not `asyncio.create_subprocess_exec` and not direct function import.
- **D-02:** Each pipeline subprocess accepts a **`--job-id {admin_job_id}`** argument and is responsible for writing its own status, `current_step`, and `discrepancies` to `admin_jobs` as it progresses. FastAPI is a reader, not a writer, for pipeline step progress.
- **D-03:** Subprocess stdout/stderr is **discarded (DEVNULL)**. All meaningful state goes to DB. On subprocess failure, `error_message` column captures the failure detail.
- **D-04:** **One subprocess per step** (three spawns per full run) — not a single wrapper script. This makes PIPE-15 pausing natural: FastAPI simply doesn't spawn the next step when discrepancies exist.
- **D-05:** **FastAPI poll endpoint triggers step-advance as a side effect.** When the poll sees `current_step='ingest'` and `status='completed'`, it spawns the parse subprocess. Double-spawn is prevented by an atomic DB guard: `UPDATE admin_jobs SET status='running', current_step='parse' WHERE id={job_id} AND current_step='ingest' AND status='completed'` — if 0 rows updated, another request already advanced it; skip spawn.
- **D-06:** FastAPI's **`GET /api/admin/jobs/{id}`** endpoint is the single poll target. It returns the full `admin_jobs` row (status, current_step, discrepancies JSONB, error_message, argument_id, created_at, updated_at). No split status/discrepancy endpoints.

### Page Flow & Navigation

- **D-07:** `/admin/pipeline` always lands on the **New Run start form**. Previous runs are listed **below the form** as a simple table (status badge, current step, created date, link to job detail page). No separate history route.
- **D-08:** Submitting the start form **redirects to `/admin/pipeline/[job_id]`** — a dedicated status page per job. This is how PIPE-17 resumability works: operator closes browser, reopens the same URL, sees the job exactly where it paused.
- **D-09:** The start form uses a **two-tab or toggle UI** — "Enter URL" and "Upload file" as modes; only one input is visible at a time. Submitting either starts the run.
- **D-10:** The status page `/admin/pipeline/[job_id]` shows **three step cards in a vertical stack** (Ingest → Parse → Resolve), each with a status badge (pending / running / completed / failed / paused). Active step shows a spinner; completed shows a checkmark; paused step shows the discrepancy review inline inside the card.

### Discrepancy Review (PIPE-15, PIPE-16)

- **D-11:** When resolve pauses, the Resolve step card renders an **inline review table**: each row shows `raw_speaker_label` on the left, auto-resolved person name + role on the right, with **Confirm** and **Correct** buttons.
- **D-12:** Clicking **Correct** replaces the suggested person with a **searchable dropdown** of all existing people records. The dropdown also includes an **"Add new person"** option for first-time advocates not yet in the DB.
- **D-13:** **"Add new person"** is a minimal creation form: **name + role only**. Bio text, photo URL, and tenure dates are Phase 8 (People Editor). The created person is immediately selectable for the corrected alias.
- **D-14:** After all rows are dispositioned (each confirmed or corrected), an explicit **"Continue Resolve"** button appears. Operator reviews the full list before clicking Continue — no auto-advance. Clicking Continue writes confirmed aliases to `speaker_alias` and marks the job completed.

### Client-Side Polling (PIPE-14)

- **D-15:** The status page uses **`setInterval` (2.5s) + `invalidateAll()`** inside a Svelte 5 `$effect`. Each tick re-runs the `+page.server.ts` load function, which calls `GET /api/admin/jobs/{id}`. All job state lives in `page.data` — no separate component-level fetch state.
- **D-16:** Polling **stops when `admin_jobs.status` reaches a terminal state**: `completed`, `failed`, or `paused` (paused = waiting for operator — nothing will change until they act). After operator clicks "Continue Resolve", polling resumes until the job reaches the next terminal state.
- **D-17:** If the job is in **`failed`** state, the step card that failed shows a red "Failed" badge and renders `admin_jobs.error_message` inline. No retry button — operator navigates back to `/admin/pipeline` to start a new run.

### Claude's Discretion

- Exact visual styling of the step cards, status badges, and discrepancy table within the established dark admin theme (`#0f1117` bg, `#1e293b` card, `#334155` border, `#94a3b8` text, `#93c5fd` accent)
- Whether the "Add new person" creation form appears inline below the dropdown or in a small modal
- Exact toggle/tab styling for the URL vs. file upload mode switch on the start form
- DEVNULL routing specifics for subprocess stdout/stderr
- Whether `invalidateAll()` or a targeted `invalidate(url)` is more appropriate for the poll — either is fine if it re-runs the load function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Constraints
- `.planning/PROJECT.md` — Key Decisions table; pipeline-is-offline constraint; Alembic-is-sole-DDL-authority; PgBouncer `statement_cache_size=0`; apolitical framing
- `.planning/REQUIREMENTS.md` — PIPE-12 through PIPE-17 (Phase 7 scope); PEOPLE-01–04 (Phase 8, do not implement here)
- `.planning/ROADMAP.md` §Phase 7 — Success criteria (5 items that must be TRUE)
- `.planning/STATE.md` §Accumulated Context — fire-and-poll pattern decision; admin_jobs separate from pipeline_runs; DO Spaces for PDF persistence; `BODY_SIZE_LIMIT=10M` and `ORIGIN` env var blockers; no in-memory Map/cache

### Phase Foundation (what Phase 7 builds on)
- `.planning/phases/05-admin-foundation/05-CONTEXT.md` — admin_jobs full schema (D-01 through D-08); all 10 columns already in migration 0003; no migration 0004 needed
- `.planning/phases/06-auth/06-CONTEXT.md` — D-11 (X-Admin-Token stays for server-to-server FastAPI calls); SvelteKit session cookie guards all `/admin/*` routes; admin layout with placeholder Pipeline Runner nav link
- `api/models/models.py` — `AdminJob`, `AdminJobStatus` enum (pending/running/paused/completed/failed), `AdminJobStep` enum (ingest/parse/resolve); all columns present
- `api/routers/admin.py` — Current Phase 5 router; `verify_admin_token` dependency; `/api/admin/health` route; Phase 7 adds job routes here
- `api/core/config.py` — `Settings` class; `admin_token` field; `BODY_SIZE_LIMIT` and `ORIGIN` env var notes

### Pipeline CLI (what the subprocesses run)
- `pipeline/__main__.py` — CLI entry point; existing subcommands (ingest, parse, resolve); Phase 7 adds `--job-id` arg to each
- `pipeline/commands/ingest.py` — Ingest command; downloads PDF, creates case/argument/pipeline_run rows
- `pipeline/commands/parse.py` — Parse command; pdfplumber + LLM corrective pass; creates utterance rows
- `pipeline/commands/resolve.py` — Resolve command; speaker_alias lookup; currently interactive CLI — Phase 7 changes interaction model (writes discrepancies to admin_jobs instead of prompting operator in terminal)

### SvelteKit Patterns
- `app/src/routes/admin/+layout.svelte` — Admin layout shell with placeholder Pipeline Runner nav link (Phase 7 makes it a real link)
- `app/src/routes/admin/+page.server.ts` — Server load pattern for admin pages
- `app/src/hooks.server.ts` — Session cookie validation; all `/admin/*` routes already guarded

### Storage
- DO Spaces via boto3 — PDF persistence for uploaded files (ephemeral container filesystem on App Platform); credentials via env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DO_SPACES_BUCKET`, `DO_SPACES_ENDPOINT`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/models/models.py` `AdminJob` ORM class — fully defined with all columns; no model work needed in Phase 7
- `api/routers/admin.py` `verify_admin_token` dependency — stays in place; Phase 7 adds job routes alongside `/health`
- `app/src/routes/admin/+layout.svelte` — Admin nav already structured; Pipeline Runner placeholder link needs to become a real `<a href="/admin/pipeline">`
- `api/core/config.py` `Settings` — pydantic-settings pattern for adding new env vars (DO Spaces credentials)

### Established Patterns
- **Svelte 5 Runes**: `$props()`, `$state`, `$derived`, `$effect` — no `export let`, no `$:`, no legacy stores
- **Server-only env vars**: `$env/static/private` only — `ADMIN_TOKEN`, `FASTAPI_BASE_URL`, DO Spaces credentials are all private; never `PUBLIC_` prefix
- **SvelteKit form actions**: `export const actions = { default: ... }` in `+page.server.ts` — pattern from Phase 6 login; use same approach for start-run form submission
- **Dark admin theme**: `#0f1117` bg, `#1e293b` card surface, `#334155` border, `#94a3b8` body text, `#93c5fd` accent — established in Phase 6; all Phase 7 UI must match
- **FastAPI router pattern**: router + service + schema + model layers; Phase 7 admin routes follow same structure as `api/routers/cases.py`
- **PipelineRun status machine**: pending → running → completed/failed/needs_review — admin_jobs has a parallel but distinct status machine (pending/running/paused/completed/failed)

### Integration Points
- `app/src/routes/admin/pipeline/` — New route directory; `+page.svelte` (start form + history list), `+page.server.ts` (load recent jobs + handle start form action)
- `app/src/routes/admin/pipeline/[job_id]/` — New route; `+page.svelte` (status cards), `+page.server.ts` (load job state from FastAPI; polling drives invalidateAll())
- `api/routers/admin.py` — New routes added here: `POST /api/admin/jobs` (create job + spawn ingest), `GET /api/admin/jobs/{id}` (poll endpoint + step-advance side effect), `POST /api/admin/jobs/{id}/resolve` (write confirmed aliases + mark completed), `GET /api/admin/jobs` (list for history)
- `pipeline/commands/ingest.py`, `parse.py`, `resolve.py` — Each needs a `--job-id` flag added; resolve changes from interactive CLI to writing discrepancies to DB instead of prompting operator

</code_context>

<specifics>
## Specific Ideas

- The resolve command's current interactive prompting (asks operator to select from people table in terminal) is replaced by the admin UI review flow: resolve writes `discrepancies` JSONB to `admin_jobs` and sets status to `paused`, then exits. The operator reviews in the browser.
- "Add new person" during discrepancy correction creates a minimal person record (name + role); the new person_id is immediately usable as the corrected alias. Full metadata editing (bio, photo, tenure dates) is Phase 8.
- The `argument_id` on `admin_jobs` is NULL until ingest creates the argument row — Phase 8 uses this FK to show the per-argument participant review after a successful run.
- Previous runs list below the start form is a simple read: most recent 10 jobs, status badge, step, created date, clickable to `/admin/pipeline/[job_id]`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-pipeline-runner*
*Context gathered: 2026-06-16*
