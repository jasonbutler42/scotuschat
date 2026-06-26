# Phase 17: Pipeline UI Polish - Research

**Researched:** 2026-06-26
**Domain:** FastAPI file serving, Alembic schema migration, Svelte 5 Runes conditional display, boto3 pre-signed URLs
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Ingest card source identifier is mode-dependent: upload mode shows `original_filename`; URL mode shows `pdf_url` verbatim.
**D-02:** `original_filename` column is NEW — not yet on `admin_jobs`. Requires Alembic migration `0009`, nullable TEXT column. Captured at `POST /api/admin/jobs` creation time from `pdf_file.filename`.
**D-03:** URL-mode jobs use the existing `pdf_url` column — no new storage needed.
**D-04:** PDF link opens in a new browser tab using browser's native PDF viewer. Backend serves `Content-Disposition: inline`. No download button.
**D-05:** Link is labeled "View source PDF" (or similar), visible on job detail page without leaving the view.
**D-06:** One unified backend endpoint: `GET /api/admin/jobs/{job_id}/pdf`. If `spaces_key` set: HTTP 302 redirect to pre-signed DO Spaces URL (15-minute TTL). Otherwise: stream file from `PipelineRun.pdf_path` with `Content-Disposition: inline`.
**D-07:** Frontend always calls the same endpoint regardless of storage mode.
**D-08:** Parse stats queried at render time from existing DB tables — no new storage. Utterance count: `COUNT(utterances WHERE pipeline_run_id = latest_parse_run_id)`. Speaker count: `COUNT(DISTINCT argument_participants.raw_speaker_label WHERE argument_id = X)`.
**D-09:** Stats reflect the latest parse run (highest `pipeline_run_id` for step=parse for this argument) when re-runs exist.
**D-10:** Stats section shown only when parse step status is `completed`. No placeholder when running/pending.

### Claude's Discretion

- Whether to fetch parse stats in the existing `GET /api/admin/jobs/{job_id}` response or as a separate sub-request on the frontend
- Exact label and placement of the "View source PDF" link within the job detail page
- Pre-signed URL TTL for Spaces-backed PDFs
- Whether `original_filename` column allows null (yes — for jobs created before the migration)

### Deferred Ideas (OUT OF SCOPE)

- Parse stat snapshots or historical stat tracking
- Showing docket number on the Parse card
- Any changes to the resolve review or approval flow
- Any new pipeline step or re-run behavior changes
- Incremental stats during parse (real-time polling a stats endpoint)
- Download button in addition to View
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-21 | Each pipeline stage card shows detailed stats — Ingest shows source filename; Parse shows utterance count, speaker count, and extracted case metadata | Stat queries use existing `get_run_id_for_step()` + COUNT on `utterances` and `argument_participants`; source identifier from new `original_filename` column or existing `pdf_url` |
| PIPE-22 | Operator can access the original source PDF for any ingested argument directly from the pipeline admin to verify speaker assignments | New `GET /api/admin/jobs/{job_id}/pdf` endpoint: 302 redirect to pre-signed Spaces URL or `FileResponse` from disk; plain `<a href>` in Svelte |
</phase_requirements>

---

## Summary

Phase 17 is a focused polish phase with two UI additions on the pipeline job detail page: stage stat cards (PIPE-21) and source PDF access (PIPE-22). The work splits cleanly into one backend plan (Alembic migration + API changes) and one frontend plan (Svelte inline additions).

The backend work involves: (1) adding `original_filename TEXT NULLABLE` to `admin_jobs` via migration 0009, (2) capturing the filename at job creation time, (3) adding parse stats queries to `get_job()` in `admin_jobs.py`, (4) extending `AdminJobResponse` with the new fields, and (5) adding the new `GET /api/admin/jobs/{job_id}/pdf` endpoint. The existing `get_run_id_for_step()` function and spaces service are reused directly.

The frontend work involves: (1) updating the `Job` TypeScript interface in `+page.svelte` to include the new fields, (2) adding the source identifier row inside the Ingest card, (3) adding the parse stat rows inside the Parse card (conditional on `status === 'completed'`), and (4) adding the "View source PDF" link card between the argument preview and the stage cards. No new Svelte components, no new API calls from the client — stats are included in the existing `GET /api/admin/jobs/{job_id}` response that the page already loads.

**Primary recommendation:** Extend `AdminJobResponse` with `original_filename` and a nested `parse_stats` object (utterance_count, speaker_count), and add parse stats computation inline in `get_job()` reusing the existing `get_run_id_for_step()` helper. Serve the PDF from a new endpoint using FastAPI's `FileResponse` for disk paths and boto3 `generate_presigned_url` for Spaces-backed files.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `original_filename` storage | Database (Alembic) | API (service layer) | Schema addition requires migration; captured at job creation in service |
| Parse stats computation | API (service layer) | Database (queries) | Computed at render time from existing tables via SQLAlchemy; returned in existing response |
| PDF serving (Spaces) | API (admin router) | External (DO Spaces) | Pre-signed URL generation is a backend concern; frontend never touches Spaces credentials |
| PDF serving (disk) | API (admin router) | — | `FileResponse` streams from `PipelineRun.pdf_path`; backend handles range requests |
| Source identifier display | Frontend (Svelte) | — | Conditional rendering on `data.job.original_filename` vs `data.job.pdf_url` |
| Parse stat display | Frontend (Svelte) | — | Conditional on `status === 'completed'`; values passed through `data` from server load |
| PDF link placement | Frontend (Svelte) | — | `<a href>` plain link in a surface card below argument preview |

---

## Standard Stack

### Core (already in project — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | 2.0 (in-project) | Parse stats COUNT queries | Existing ORM; `select(func.count(...))` pattern already used in `admin_jobs.py` |
| Alembic | in-project | `original_filename` column migration | Sole DDL authority per CLAUDE.md — `op.add_column` with nullable=True |
| FastAPI `FileResponse` | 0.115+ (in-project) | Stream local PDF with correct headers | Built-in Starlette response; handles `Content-Disposition: inline`, range requests |
| FastAPI `RedirectResponse` | in-project | 302 to Spaces pre-signed URL | Built-in; status_code=302 |
| boto3 `generate_presigned_url` | in-project (boto3 already used) | Pre-signed URL generation for Spaces | Existing `get_spaces_client()` returns a client that supports this method |
| Svelte 5 Runes (`$derived`, `$props`) | 5.x (in-project) | Conditional stat display | Already used throughout the page; no `$:` blocks |

### No New Packages Required

This phase installs no external packages. All capabilities are served by libraries already present:
- `boto3` — already used in `api/services/spaces.py` for `upload_pdf_to_spaces`
- `starlette.responses.FileResponse` — available as part of FastAPI
- `starlette.responses.RedirectResponse` — same

**Package Legitimacy Audit:** Not applicable — zero new packages are introduced.

---

## Architecture Patterns

### System Architecture Diagram

```
[Browser: "View source PDF" click]
         │
         ▼
[SvelteKit: plain <a href="/api/admin/jobs/{id}/pdf" target="_blank">]
         │
         ▼ (request goes to FastAPI)
[FastAPI: GET /api/admin/jobs/{job_id}/pdf]
         │
         ├─── spaces_key is set ──────► [boto3: generate_presigned_url(ExpiresIn=900)]
         │                                       │
         │                                       ▼
         │                              [302 RedirectResponse to DO Spaces URL]
         │                                       │
         │                                       ▼
         │                              [Browser: fetches PDF from DO Spaces directly]
         │
         └─── spaces_key is None ──────► [FileResponse(pdf_path, media_type="application/pdf")]
                                                  │
                                                  ▼
                                         [Browser: receives streamed PDF]


[SvelteKit: load function fetches GET /api/admin/jobs/{job_id}]
         │
         ▼
[FastAPI: get_job() → get_run_id_for_step(db, job_id, "parse")]
         │
         ├─── parse_run_id found ──────► COUNT(utterances WHERE pipeline_run_id=run_id)
         │                              COUNT(DISTINCT argument_participants.raw_speaker_label
         │                                    WHERE argument_id=job.argument_id)
         │                                       │
         │                                       ▼
         │                              [AdminJobResponse with parse_stats embedded]
         │
         └─── no parse_run_id ─────────► [AdminJobResponse with parse_stats=None]
                  │
                  ▼
         [Svelte: hides stat rows]
```

### Recommended File Changes

```
alembic/versions/
└── 0009_add_original_filename.py    # new: nullable TEXT column on admin_jobs

api/models/models.py
└── AdminJob                          # add: original_filename = Column(Text, nullable=True)

api/schemas/admin_jobs.py
└── AdminJobResponse                  # add: original_filename, parse_stats fields

api/services/admin_jobs.py
├── create_job()                      # add: original_filename param
└── get_job()                         # extend: query parse stats after loading job

api/routers/admin.py
├── create_job route                  # pass pdf_file.filename to create_job()
└── GET /jobs/{job_id}/pdf            # new route: RedirectResponse or FileResponse

app/src/routes/admin/pipeline/[job_id]/
├── +page.server.ts                   # update: Job interface passthrough (data already flows)
└── +page.svelte                      # add: source identifier row, parse stat rows, PDF link card
```

### Pattern 1: Alembic Nullable Column Addition

Established in migration 0006. The pattern for adding a nullable column is:

```python
# Source: alembic/versions/0006_add_structured_name_fields.py (VERIFIED: codebase)
def upgrade() -> None:
    op.add_column("admin_jobs", sa.Column("original_filename", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("admin_jobs", "original_filename")
```

No backfill required. Existing rows receive NULL, which the frontend hides via `{#if}` gate.

### Pattern 2: SQLAlchemy Async COUNT Query

The existing pattern for scalar counts in `admin_jobs.py`:

```python
# Source: api/services/admin_jobs.py (VERIFIED: codebase) — adapted for COUNT
from sqlalchemy import func, select

# Count utterances for a parse run
utt_result = await db.execute(
    select(func.count(Utterance.id)).where(
        Utterance.pipeline_run_id == parse_run_id
    )
)
utterance_count = utt_result.scalar_one()

# Count distinct speaker labels for an argument
spk_result = await db.execute(
    select(func.count(ArgumentParticipant.raw_speaker_label.distinct())).where(
        ArgumentParticipant.argument_id == job.argument_id
    )
)
speaker_count = spk_result.scalar_one()
```

Use `scalar_one()` not `scalar_one_or_none()` — COUNT always returns a row (returns 0 when empty).

### Pattern 3: boto3 Pre-Signed URL

The `get_spaces_client()` function already returns a boto3 S3 client. Pre-signed URL generation:

```python
# Source: api/services/spaces.py existing client + boto3 docs (ASSUMED: boto3 generate_presigned_url)
def generate_pdf_presigned_url(key: str, expires_in: int = 900) -> str:
    client = get_spaces_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.do_spaces_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
```

The `generate_presigned_url` call is synchronous (boto3 is synchronous). Wrap in `loop.run_in_executor(None, ...)` if called from an async FastAPI route, matching the existing upload pattern in `admin.py`.

### Pattern 4: FastAPI FileResponse for Local PDFs

```python
# Source: FastAPI/Starlette docs (ASSUMED: FileResponse pattern)
from starlette.responses import FileResponse, RedirectResponse

@router.get("/jobs/{job_id}/pdf")
async def get_job_pdf(job_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    job = await jobs_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.spaces_key:
        # Spaces-backed: generate pre-signed URL and redirect
        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None,
            spaces_service.generate_pdf_presigned_url,
            job.spaces_key,
        )
        return RedirectResponse(url=url, status_code=302)
    else:
        # Disk-backed: find pdf_path from latest ingest run
        run_id = await jobs_service.get_run_id_for_step(db, job_id, "ingest")
        if run_id is None:
            raise HTTPException(status_code=404, detail="PDF not available")
        # Fetch PipelineRun to get pdf_path
        run_result = await db.execute(
            select(PipelineRun).where(PipelineRun.id == run_id)
        )
        run = run_result.scalar_one_or_none()
        if run is None or run.pdf_path is None:
            raise HTTPException(status_code=404, detail="PDF path not recorded")
        filename = job.original_filename or f"argument-{job_id}.pdf"
        return FileResponse(
            path=run.pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
```

`FileResponse` is imported from `starlette.responses` — same package that FastAPI depends on.

### Pattern 5: AdminJobResponse Extension

The schema uses `model_config = {"from_attributes": True}`. New optional fields with `None` default are safe for existing rows:

```python
# Source: api/schemas/admin_jobs.py (VERIFIED: codebase) — extended
class ParseStats(BaseModel):
    utterance_count: int
    speaker_count: int

class AdminJobResponse(BaseModel):
    # ... existing fields ...
    original_filename: Optional[str] = None
    parse_stats: Optional[ParseStats] = None

    model_config = {"from_attributes": True}
```

`ParseStats` is a separate nested model (not from_attributes) because it's assembled from query results, not from an ORM column.

### Pattern 6: Svelte 5 Stat Display (Ingest card)

The step card loop currently has no per-step conditional content. Adding it:

```svelte
<!-- Source: app/src/routes/admin/pipeline/[job_id]/+page.svelte (VERIFIED: codebase) -->
{#if step === 'ingest' && (data.job.original_filename || data.job.pdf_url)}
    <div style="margin-top: 12px;">
        <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">
            Source file
        </span>
        <span style="font-size: 16px; color: #e2e8f0; word-break: break-all;">
            {data.job.original_filename ?? data.job.pdf_url}
        </span>
    </div>
{/if}
```

### Pattern 7: Svelte 5 Stat Display (Parse card)

```svelte
<!-- Conditional on parse status === 'completed' AND parse_stats present -->
{#if step === 'parse' && status === 'completed' && data.job.parse_stats}
    {@const ps = data.job.parse_stats}
    <div style="margin-top: 12px; display: flex; flex-direction: column;">
        <div style="margin-bottom: 12px;">
            <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Utterances</span>
            <span style="font-size: 16px; color: #e2e8f0;">{ps.utterance_count}</span>
        </div>
        <div style="margin-bottom: 12px;">
            <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Distinct speakers</span>
            <span style="font-size: 16px; color: #e2e8f0;">{ps.speaker_count}</span>
        </div>
        {#if data.argument}
            <div style="margin-bottom: 12px;">
                <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Case name</span>
                <span style="font-size: 16px; color: #e2e8f0;">{data.argument.case_name || '—'}</span>
            </div>
            <div style="margin-bottom: 12px;">
                <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Argued</span>
                <span style="font-size: 16px; color: #e2e8f0;">{formatArgDate(data.argument.argued_date)}</span>
            </div>
        {/if}
    </div>
{/if}
```

The `formatArgDate` function already exists on the page (line 355 of `+page.svelte`) — reuse it directly.

### Anti-Patterns to Avoid

- **Do NOT call `Base.metadata.create_all`** — Alembic is the sole DDL authority (CLAUDE.md hard constraint). Migration 0009 must use `op.add_column`.
- **Do NOT add `original_filename` to `AdminJob.__init__` via a keyword override** — SQLAlchemy Column declarations make the field available automatically after migration.
- **Do NOT fetch parse stats as a separate client-side request** — stats belong in the existing `GET /api/admin/jobs/{job_id}` response (D-08, no-client-fetch pattern in CLAUDE.md).
- **Do NOT use `$:` reactive statements** — Svelte 5 Runes; use `$derived()` or plain `{#if}` blocks (CLAUDE.md constraint).
- **Do NOT make the PDF endpoint return the Spaces URL directly to the frontend** — the 302 redirect pattern keeps Spaces credentials server-side.
- **Do NOT use `scalar_one_or_none()` for COUNT queries** — COUNT always returns a value; `scalar_one()` is correct and prevents silent `None` being passed as a count.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Streaming PDF with range support | Custom byte streaming | `starlette.responses.FileResponse` | Handles `Content-Range`, `Accept-Ranges`, proper MIME headers automatically |
| Pre-signed URL generation | Manual HMAC signing of S3 URL | `boto3 client.generate_presigned_url()` | Handles signature version, expiry, path encoding; already in project via `get_spaces_client()` |
| Utterance count | Custom Python accumulator | `select(func.count(...))` via SQLAlchemy | Single DB round-trip; COUNT is atomic and consistent |
| Async wrapper for boto3 | Custom thread management | `asyncio.get_running_loop().run_in_executor(None, fn)` | Same pattern already used for `upload_pdf_to_spaces` in `admin.py` line 185 |

---

## Runtime State Inventory

> Omitted — this is a greenfield feature addition, not a rename/refactor/migration of existing identifiers.

---

## Common Pitfalls

### Pitfall 1: `parse_stats` sourced from wrong run after re-run

**What goes wrong:** If stats are computed using `job.argument_id` directly to find the latest `PipelineRun`, a re-run creates a new `AdminJob` with the same `argument_id`. The old job's "parse" run in `pipeline_runs` is the highest `id` for that `argument_id`, so `get_run_id_for_step(db, job_id, "parse")` joins through `job.argument_id` — which is correct (it returns the latest parse run for this argument regardless of which AdminJob created it).

**However:** D-09 says stats reflect the latest parse run. `get_run_id_for_step()` already orders by `created_at DESC LIMIT 1`, so this is handled. Verify the query returns the correct run_id when there are multiple parse runs for the same `argument_id`.

**How to avoid:** Use `get_run_id_for_step(db, job_id, "parse")` exactly — do not write a separate query. That function already handles recency correctly.

### Pitfall 2: `pdf_path` is None for Spaces-uploaded jobs

**What goes wrong:** For jobs using DO Spaces (`spaces_key` is set), the pipeline downloads the PDF to a temp path during ingest. The `PipelineRun.pdf_path` may be the temp path or may be NULL depending on how the ingest step was implemented.

**Resolution:** For the PDF endpoint: if `job.spaces_key` is set, always use the pre-signed URL path (D-06). Never fall through to `pdf_path` for Spaces jobs. The `if job.spaces_key` branch short-circuits before any `pdf_path` lookup.

**How to avoid:** Branch on `spaces_key` first (pre-signed URL), with `pdf_path` as the fallback for disk-only jobs. Match the branch order in D-06 exactly.

### Pitfall 3: `original_filename` captured from wrong source

**What goes wrong:** FastAPI's `UploadFile.filename` is client-supplied from the multipart `Content-Disposition` header. For file upload jobs, `pdf_file.filename` gives the browser's reported filename. This is the correct value for display.

**However:** `UploadFile.filename` can be `None` if the browser sends a malformed upload (rare but possible). Store `pdf_file.filename or None` — do not assume it's non-null.

**How to avoid:** In `create_job()`, accept `original_filename: str | None = None`. In the router, pass `pdf_file.filename` (which may be `None`) without assertion.

### Pitfall 4: Svelte `Job` TypeScript interface not updated

**What goes wrong:** `+page.svelte` defines a local `Job` interface (line 26). If `original_filename` and `parse_stats` are not added to this interface, TypeScript will reject access to `data.job.original_filename` at build time (SvelteKit's strict mode).

**How to avoid:** Update the `Job` interface in `+page.svelte` to include `original_filename?: string | null` and `parse_stats?: { utterance_count: number; speaker_count: number } | null`.

### Pitfall 5: `formatArgDate` not accessible inside the step loop

**What goes wrong:** In `+page.svelte`, `formatArgDate` is defined as a `{@const}` inside the `{#if data.argument}` block (line 355). It is NOT in script scope — it cannot be called from within the `{#each STEP_ORDER as step}` loop.

**How to avoid:** Define a standalone date-formatting function in the `<script>` block (e.g., `function formatDate(iso: string | null): string { ... }`). Or reference `data.argument` and apply `new Date(iso).toLocaleDateString(...)` inline inside the Parse card branch. Do not attempt to reference the `{@const formatArgDate}` from a sibling block.

### Pitfall 6: Missing `Response` return type on the PDF endpoint

**What goes wrong:** The PDF endpoint returns either `RedirectResponse` or `FileResponse`. FastAPI's response model inference will fail if the return type annotation is `AdminJobResponse` or omitted with a response_model set.

**How to avoid:** Annotate the route with `response_class=Response` or no `response_model`, and use `-> Response` as the return type. Import `Response` from `fastapi` or `starlette.responses`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| boto3 (in venv) | Pre-signed URL generation | ✓ | present in project | — |
| starlette FileResponse | Local PDF serving | ✓ | bundled with FastAPI 0.115+ | — |
| PostgreSQL (local) | COUNT queries in tests | ✓ | running (local dev DB) | — |
| DO Spaces credentials | Pre-signed URL path | ✗ (local dev) | not configured locally | Disk path fallback covers dev; Spaces only needed in production |

**Missing dependencies with no fallback:** None — the disk path fallback covers local development. Pre-signed URL path is production-only.

**Missing dependencies with fallback:** DO Spaces credentials — local dev uses `pdf_path` on disk; Spaces path activates only when `settings.do_spaces_bucket` is non-empty.

---

## Validation Architecture

> `nyquist_validation` is set to `false` in `.planning/config.json` — this section is skipped per config.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing router-level `verify_admin_token` dependency applies to all `/api/admin/*` routes — the new PDF endpoint inherits this |
| V3 Session Management | no | No session changes in this phase |
| V4 Access Control | yes | The PDF endpoint is admin-only; `verify_admin_token` covers it automatically via router prefix |
| V5 Input Validation | yes | `job_id` is typed `int` — FastAPI rejects non-integer values at the boundary; no additional validation needed |
| V6 Cryptography | no | Pre-signed URL uses boto3's signing — not hand-rolled |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on PDF endpoint | Information disclosure | `verify_admin_token` is a router-level dependency — all routes including the new PDF endpoint require valid admin token |
| Path traversal via `pdf_path` | Tampering | `pdf_path` is written by the pipeline at ingest time — never derived from user input; read from the database row, not from a request parameter |
| Pre-signed URL leakage | Information disclosure | URL is generated server-side and delivered via a 302 redirect — the client sees the pre-signed URL in the browser's address bar, which is acceptable for this admin-only flow (the URL expires in 15 minutes) |
| Client-supplied `original_filename` misuse | Spoofing | `original_filename` is display-only — it is never used as a file path or in any server-side file operation |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `boto3 client.generate_presigned_url("get_object", ...)` is the correct method signature for DO Spaces pre-signed URL generation | Pattern 3 (PDF endpoint) | Wrong method signature would cause runtime error on the pre-signed URL path; easy to fix at implementation time |
| A2 | `starlette.responses.FileResponse` handles `Content-Disposition: inline` via the `headers` kwarg | Pattern 4 (PDF endpoint) | May need to use `filename` kwarg instead or set header differently; verify against Starlette source at implementation |
| A3 | `PipelineRun.pdf_path` is populated for disk-backed ingest runs (non-Spaces) | Pitfall 2 | If `pdf_path` is never set, disk path for PDF serving is unavailable; would need to inspect ingest pipeline command to confirm |

---

## Open Questions

1. **Is `PipelineRun.pdf_path` reliably set for disk-backed uploads?**
   - What we know: The `PipelineRun` model has a `pdf_path` column (`String(500), nullable=True`)
   - What's unclear: The ingest pipeline command (`pipeline/commands/ingest.py`) — not read in this session — is responsible for writing `pdf_path`; if it doesn't set it for upload-mode jobs, the disk path fallback fails
   - Recommendation: Read `pipeline/commands/ingest.py` in Plan 17-01 before implementing the PDF endpoint; confirm `pdf_path` is written for both URL-sourced and locally-saved jobs

2. **Does `spaces_service` need a new function or can the router call `get_spaces_client()` directly?**
   - What we know: `spaces.py` has `get_spaces_client()` and two upload functions; no pre-signed URL function exists yet
   - What's unclear: Whether to add `generate_pdf_presigned_url()` to `spaces.py` or inline the call in the router
   - Recommendation: Add a `generate_pdf_presigned_url(key, expires_in=900)` function to `spaces.py` — keeps Spaces client logic centralized, consistent with `upload_pdf_to_spaces` pattern

---

## Sources

### Primary (HIGH confidence — verified from codebase)
- `api/services/admin_jobs.py` — `get_run_id_for_step()` pattern; COUNT query adaptation; `create_job()` signature
- `api/services/spaces.py` — `get_spaces_client()` pattern; boto3 client creation
- `api/schemas/admin_jobs.py` — `AdminJobResponse` with `from_attributes=True`; optional field pattern
- `api/routers/admin.py` — `create_job` route; existing `verify_admin_token` dependency scope; `run_in_executor` pattern for sync boto3 calls
- `api/models/models.py` — `AdminJob`, `PipelineRun`, `Utterance`, `ArgumentParticipant` column definitions
- `alembic/versions/0006_add_structured_name_fields.py` — nullable column migration pattern
- `alembic/versions/0008_side_enum_and_argument_status.py` — migration structure reference
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Svelte step card loop structure; existing inline style tokens; `formatArgDate` scope
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load function pattern; graceful degradation pattern
- `.planning/phases/17-pipeline-ui-polish/17-CONTEXT.md` — all implementation decisions D-01 through D-10
- `.planning/phases/17-pipeline-ui-polish/17-UI-SPEC.md` — component inventory, copywriting contract, interaction contract

### Secondary (ASSUMED — training knowledge, not verified in this session)
- boto3 `generate_presigned_url` method signature (A1)
- Starlette `FileResponse` headers kwarg behavior (A2)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present in project; no new packages
- Architecture: HIGH — derived directly from locked CONTEXT.md decisions and existing codebase patterns
- Pitfalls: MEDIUM — pitfalls 1–4 and 6 verified from codebase; pitfall 5 (`formatArgDate` scope) verified from reading `+page.svelte` line 355

**Research date:** 2026-06-26
**Valid until:** 2026-07-26 (stable stack — 30-day window)
