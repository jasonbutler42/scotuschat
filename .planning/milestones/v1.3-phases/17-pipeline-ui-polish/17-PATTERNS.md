# Phase 17: Pipeline UI Polish - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `alembic/versions/0009_add_original_filename.py` | migration | batch | `alembic/versions/0006_add_structured_name_fields.py` | exact |
| `api/models/models.py` (AdminJob column) | model | — | `api/models/models.py` existing AdminJob block | exact |
| `api/schemas/admin_jobs.py` (AdminJobResponse + ParseStats) | schema | request-response | `api/schemas/admin_jobs.py` AdminJobResponse + PersonResponse | exact |
| `api/services/admin_jobs.py` (create_job, get_job) | service | CRUD | `api/services/admin_jobs.py` existing create_job / get_job | exact |
| `api/services/spaces.py` (generate_pdf_presigned_url) | service | request-response | `api/services/spaces.py` upload_pdf_to_spaces | role-match |
| `api/routers/admin.py` (GET /jobs/{job_id}/pdf) | controller | request-response | `api/routers/admin.py` GET /jobs/{job_id} + create_job upload branch | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | route | request-response | same file — existing graceful-degrade fetch pattern | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | component | request-response | same file — argument metadata card label/value rows + step card loop | exact |

---

## Pattern Assignments

### `alembic/versions/0009_add_original_filename.py` (migration, batch)

**Analog:** `alembic/versions/0006_add_structured_name_fields.py`

**Full file structure** (lines 1–50 of 0006):
```python
"""Add structured name fields and appointment fields to people table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-19
...
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("first_name", sa.String(150), nullable=True))
    # ... more columns ...


def downgrade() -> None:
    op.drop_column("people", "first_name")
    # ... reverse order ...
```

**Adaptation for 0009:**
- `revision = "0009"`, `down_revision = "0008"`
- Target table is `admin_jobs`, not `people`
- Column: `sa.Column("original_filename", sa.Text(), nullable=True)`
- No backfill — existing rows receive NULL (safe; frontend hides via conditional)

---

### `api/models/models.py` — AdminJob column addition (model)

**Analog:** `api/models/models.py` existing AdminJob column declarations (line 324+)

The existing pattern for nullable Text columns on AdminJob (from the `pdf_url` and `spaces_key` declarations):
```python
# Existing pattern at AdminJob class (line 324+):
pdf_url = Column(String(500), nullable=True)
spaces_key = Column(String(500), nullable=True)
```

**New column follows identical pattern:**
```python
original_filename = Column(Text, nullable=True)
```

Import `Text` from `sqlalchemy` if not already imported — check existing `Column(Text, ...)` usage in the file first.

---

### `api/schemas/admin_jobs.py` — AdminJobResponse + new ParseStats (schema)

**Analog:** `api/schemas/admin_jobs.py` — AdminJobResponse (lines 17–31) and PersonResponse (lines 55–63)

**Existing AdminJobResponse pattern** (lines 17–31):
```python
class AdminJobResponse(BaseModel):
    """Full admin job row returned by the poll endpoint and job creation."""

    id: int
    status: AdminJobStatus
    current_step: Optional[AdminJobStep] = None
    argument_id: Optional[int] = None
    pdf_url: Optional[str] = None
    spaces_key: Optional[str] = None
    discrepancies: Optional[list[dict]] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
```

**Existing nested model pattern** (PersonResponse, lines 55–63):
```python
class PersonResponse(BaseModel):
    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None

    model_config = {"from_attributes": True}
```

**New additions — place ParseStats before AdminJobResponse:**
```python
class ParseStats(BaseModel):
    """Parse step stats embedded in AdminJobResponse — assembled from query results, not ORM."""
    utterance_count: int
    speaker_count: int
    # No model_config from_attributes — this is assembled from scalar query results, not an ORM row
```

**AdminJobResponse additions** (two new Optional fields after `spaces_key`):
```python
    original_filename: Optional[str] = None
    parse_stats: Optional[ParseStats] = None
```

`model_config = {"from_attributes": True}` stays on `AdminJobResponse`; `ParseStats` does NOT need it because it is constructed manually from scalar query results.

---

### `api/services/admin_jobs.py` — create_job + get_job extensions (service)

**Analog:** `api/services/admin_jobs.py` — existing `create_job` (lines 46–67) and `get_job` (lines 70–75)

**Existing create_job signature and body** (lines 46–67):
```python
async def create_job(
    db: AsyncSession,
    *,
    pdf_url: str | None = None,
    spaces_key: str | None = None,
) -> AdminJob:
    job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        pdf_url=pdf_url,
        spaces_key=spaces_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
```

**create_job extension:** Add `original_filename: str | None = None` keyword param and pass it to `AdminJob(...)`.

**Existing get_job** (lines 70–75):
```python
async def get_job(db: AsyncSession, job_id: int) -> AdminJob | None:
    result = await db.execute(
        select(AdminJob).where(AdminJob.id == job_id)
    )
    return result.scalar_one_or_none()
```

**Existing COUNT / scalar_one pattern** (from `resolve_job`, lines 226–234 — adapted for COUNT):
```python
# The project already imports func from sqlalchemy (line 22)
from sqlalchemy import func, select

result = await db.execute(
    select(func.count(Utterance.id)).where(
        Utterance.pipeline_run_id == parse_run_id
    )
)
count = result.scalar_one()  # COUNT always returns a row — never scalar_one_or_none()
```

**Existing get_run_id_for_step** (lines 155–188) — reuse directly, do not re-implement:
```python
# Already handles recency: orders by created_at DESC LIMIT 1
parse_run_id = await get_run_id_for_step(db, job_id, "parse")
# Returns None if no parse run exists → parse_stats stays None
```

**get_job extension pattern** — append parse stats query after loading the job:
```python
async def get_job(db: AsyncSession, job_id: int) -> AdminJob | None:
    result = await db.execute(select(AdminJob).where(AdminJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        return None

    # Attach parse_stats as a non-ORM attribute when a parse run exists
    parse_run_id = await get_run_id_for_step(db, job_id, "parse")
    if parse_run_id is not None and job.argument_id is not None:
        utt_result = await db.execute(
            select(func.count(Utterance.id)).where(
                Utterance.pipeline_run_id == parse_run_id
            )
        )
        utterance_count = utt_result.scalar_one()

        spk_result = await db.execute(
            select(func.count(ArgumentParticipant.raw_speaker_label.distinct())).where(
                ArgumentParticipant.argument_id == job.argument_id
            )
        )
        speaker_count = spk_result.scalar_one()

        # Attach as dynamic attribute — AdminJobResponse reads it via parse_stats field
        job.__dict__["parse_stats"] = {"utterance_count": utterance_count, "speaker_count": speaker_count}
    else:
        job.__dict__["parse_stats"] = None

    return job
```

Note: `parse_stats` is not an ORM column so it must be injected into `__dict__` before the Pydantic schema reads it. `AdminJobResponse` has `model_config = {"from_attributes": True}` which reads attributes by name — injecting into `__dict__` makes the field visible to `model_validate(job, from_attributes=True)`. An alternative is to construct `AdminJobResponse` manually in the router rather than returning the ORM object directly — either approach works; choose whichever matches how the router currently calls `return job`.

---

### `api/services/spaces.py` — generate_pdf_presigned_url (service)

**Analog:** `api/services/spaces.py` — `upload_pdf_to_spaces` (lines 37–50) and `get_spaces_client` (lines 19–34)

**Existing client creation pattern** (lines 19–34):
```python
def get_spaces_client():
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=settings.do_spaces_region,
        endpoint_url=settings.do_spaces_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
```

**Existing synchronous upload function pattern** (lines 37–50):
```python
def upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str:
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return key
```

**New function — same sync pattern, same client:**
```python
def generate_pdf_presigned_url(key: str, expires_in: int = 900) -> str:
    """Generate a pre-signed GET URL for a Spaces-backed PDF.

    Returns a URL valid for `expires_in` seconds (default 15 minutes).
    Synchronous — wrap in run_in_executor when called from an async route.
    """
    client = get_spaces_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.do_spaces_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
```

---

### `api/routers/admin.py` — GET /jobs/{job_id}/pdf (controller)

**Analog:** `api/routers/admin.py` — `create_job` upload branch (lines 160–223) for the `run_in_executor` pattern; `get_job` route (lines 246–275) for the 404-guard + service-call pattern

**Existing run_in_executor pattern for sync boto3 call** (lines 180–203):
```python
loop = asyncio.get_running_loop()
try:
    await loop.run_in_executor(
        None,
        spaces_service.upload_pdf_to_spaces,
        file_bytes,
        key,
    )
except Exception as upload_exc:
    # ... error handling ...
```

**Existing get_job 404-guard pattern** (lines 246–268):
```python
@router.get("/jobs/{job_id}", response_model=AdminJobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    job = await jobs_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
```

**Existing router-level imports** (lines 36–50):
```python
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
```

**New PDF endpoint — combine both patterns:**
```python
from starlette.responses import FileResponse, RedirectResponse, Response

@router.get("/jobs/{job_id}/pdf")
async def get_job_pdf(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve the source PDF for a pipeline job.

    - Spaces-backed (spaces_key set): 302 redirect to pre-signed DO Spaces URL (15-min TTL).
    - Disk-backed: FileResponse streams from PipelineRun.pdf_path with Content-Disposition: inline.

    Auth: inherited from router-level verify_admin_token dependency.
    """
    job = await jobs_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.spaces_key:
        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None,
            spaces_service.generate_pdf_presigned_url,
            job.spaces_key,
        )
        return RedirectResponse(url=url, status_code=302)
    else:
        run_id = await jobs_service.get_run_id_for_step(db, job_id, "ingest")
        if run_id is None:
            raise HTTPException(status_code=404, detail="PDF not available")
        run_result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
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

Key: annotate with `-> Response` and do NOT set `response_model` — the route returns either `RedirectResponse` or `FileResponse`, not a Pydantic model.

Also add `select` and `PipelineRun` to existing imports: `from sqlalchemy import select, update` (update already imported); `PipelineRun` already imported in the router via `from api.models.models import ...` — verify and add if missing.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load function extension

**Analog:** Same file — existing graceful-degrade fetch blocks (lines 40–107)

**Existing graceful-degrade pattern** (lines 62–81):
```typescript
let participants: ParticipantItem[] = [];
if ((job.status === 'completed' || job.status === 'paused') && job.argument_id != null) {
    try {
        const participantsRes = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/participants`,
            { headers: { 'X-Admin-Token': ADMIN_TOKEN } },
        );
        if (participantsRes.ok) {
            participants = await participantsRes.json();
        } else {
            console.error(`[load] participants fetch failed: ...`);
        }
    } catch (err) {
        console.error('[load] participants fetch threw:', err instanceof Error ? err.message : String(err));
    }
}
```

**Extension needed:** No new fetch call required. `original_filename` and `parse_stats` are returned in the existing `GET /api/admin/jobs/{job_id}` response (same fetch at line 26). The `job` object already flows through `return { job, ... }`. Update the `ArgumentPreview` interface if needed, but the primary change is extending the `Job` interface in `+page.svelte`.

**Interface update — add to existing return** (line 106):
```typescript
return { job, people, peopleLoadError, participants, argument };
// No change — parse_stats and original_filename come through the job object directly
```

---

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — stat rows + PDF link (component)

**Analog:** Same file — argument metadata card label/value rows (lines 370–412) and step card loop (lines 458–504)

**Existing Job interface** (lines 26–32 — must be extended):
```typescript
interface Job {
    id: number;
    status: string;
    current_step: string;
    error_message?: string | null;
    discrepancies?: Discrepancy[] | null;
}
```

**Extension:**
```typescript
interface ParseStats {
    utterance_count: number;
    speaker_count: number;
}

interface Job {
    id: number;
    status: string;
    current_step: string;
    error_message?: string | null;
    discrepancies?: Discrepancy[] | null;
    pdf_url?: string | null;
    spaces_key?: string | null;
    original_filename?: string | null;
    parse_stats?: ParseStats | null;
}
```

**Existing label/value row pattern** (lines 370–385 — the canonical inline style token set):
```svelte
<div style="margin-bottom: 12px;">
    <span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Case title</span>
    <span style="font-size: 16px; color: #e2e8f0;">{arg.case_name}</span>
</div>
```

**Existing link style** (line 407–411 — "Edit argument metadata"):
```svelte
<a
    href="/admin/arguments/{arg.id}"
    style="font-size: 14px; color: #93c5fd; text-decoration: underline;"
>
    Edit argument metadata
</a>
```

**Existing step card per-step conditional pattern** (lines 506–511):
```svelte
{#if step === 'resolve' && data.job.status === 'paused' && data.job.discrepancies?.length}
    <!-- resolve-specific content -->
{/if}
```

**Existing formatArgDate scope note** (line 355):
```svelte
{@const formatArgDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '—'}
```

This `{@const}` is scoped inside `{#if data.argument}` and NOT accessible from the `{#each STEP_ORDER as step}` loop. Define a standalone function in the `<script>` block instead:
```typescript
function formatDate(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}
```

**Ingest card stat row** — insert after the step card header `<div>` (after line 504), inside `{#each STEP_ORDER as step}`:
```svelte
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

**Parse card stat rows** — insert after ingest conditional, same loop:
```svelte
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
                <span style="font-size: 16px; color: #e2e8f0;">{formatDate(data.argument.argued_date)}</span>
            </div>
        {/if}
    </div>
{/if}
```

**"View source PDF" link** — place below the argument metadata preview card (`{/if}` at line 451) and above the step cards container (`<div aria-live="polite">` at line 454):
```svelte
{#if data.job.id}
    <div
        style="
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 16px 24px;
            margin-bottom: 24px;
        "
    >
        <a
            href="/api/admin/jobs/{data.job.id}/pdf"
            target="_blank"
            rel="noopener noreferrer"
            style="font-size: 14px; color: #93c5fd; text-decoration: underline;"
        >
            View source PDF
        </a>
    </div>
{/if}
```

Note: The link href points directly to the FastAPI endpoint via the SvelteKit proxy (or direct API URL). If the project routes `/api/*` through SvelteKit's server to FastAPI, use `/api/admin/jobs/{data.job.id}/pdf`. If it calls FastAPI directly from the browser, the URL must include the base. Confirm routing config matches existing fetch calls in the page — the browser-side fetch pattern is different from server-side `FASTAPI_BASE_URL` calls. Since this is a plain anchor tag (not a fetch), it must use the browser-accessible URL. Check if the project uses a SvelteKit proxy route or if the operator browser has direct access to the FastAPI port.

---

## Shared Patterns

### Admin Token Auth
**Source:** `api/routers/admin.py` lines 115–132 (router-level dependency)
**Apply to:** The new GET /jobs/{job_id}/pdf route inherits automatically — no per-route change needed. The new route is added to the same `router` object that has `verify_admin_token` applied at construction time.

### run_in_executor for Sync boto3 Calls
**Source:** `api/routers/admin.py` lines 180–203
**Apply to:** `generate_pdf_presigned_url` call in the new PDF endpoint
```python
loop = asyncio.get_running_loop()
url = await loop.run_in_executor(
    None,
    spaces_service.generate_pdf_presigned_url,
    job.spaces_key,
)
```

### Nullable Optional Field with None Default (Pydantic)
**Source:** `api/schemas/admin_jobs.py` lines 22–29
**Apply to:** All new fields on `AdminJobResponse` (`original_filename`, `parse_stats`)
```python
field_name: Optional[TypeHint] = None
```

### scalar_one() for COUNT Queries
**Source:** `api/services/admin_jobs.py` — COUNT queries always return a row; use `scalar_one()` not `scalar_one_or_none()`
**Apply to:** utterance_count and speaker_count queries in `get_job()`

### Inline Style Token Set (Svelte)
**Source:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte` lines 370–385
**Apply to:** All new stat rows inside Ingest and Parse cards
- Label: `font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;`
- Value: `font-size: 16px; color: #e2e8f0;`
- Link: `font-size: 14px; color: #93c5fd; text-decoration: underline;`

### Alembic Migration Chain
**Source:** `alembic/versions/0008_side_enum_and_argument_status.py` line 2
**Apply to:** Migration 0009
- `down_revision` must be `"0008"`
- Never call `Base.metadata.create_all` — use `op.add_column` only

---

## No Analog Found

All files in this phase have close analogs in the existing codebase. No greenfield patterns required.

---

## Metadata

**Analog search scope:** `api/routers/`, `api/services/`, `api/schemas/`, `api/models/`, `alembic/versions/`, `app/src/routes/admin/pipeline/[job_id]/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-26
