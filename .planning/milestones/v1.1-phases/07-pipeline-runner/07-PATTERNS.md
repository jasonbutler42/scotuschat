# Phase 7: Pipeline Runner - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 14 new/modified files
**Analogs found:** 13 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/routers/admin.py` (add routes) | controller | request-response | `api/routers/cases.py` | role-match |
| `api/schemas/admin_jobs.py` | model/schema | transform | `api/schemas/cases.py` | exact |
| `api/services/admin_jobs.py` | service | CRUD | `api/services/cases.py` | role-match |
| `api/services/spaces.py` | service | file-I/O | `api/services/cases.py` (structure only) | role-match |
| `api/core/config.py` (add fields) | config | — | `api/core/config.py` (self) | exact |
| `pipeline/__main__.py` (add --job-id) | config/CLI | — | `pipeline/__main__.py` (self) | exact |
| `pipeline/commands/ingest.py` (add --job-id + DB writes) | service | CRUD + file-I/O | `pipeline/commands/resolve.py` | exact |
| `pipeline/commands/parse.py` (add --job-id + DB writes) | service | CRUD | `pipeline/commands/resolve.py` | exact |
| `pipeline/commands/resolve.py` (replace interactive with DB writes) | service | CRUD | `pipeline/commands/resolve.py` (self) | exact |
| `app/src/routes/admin/+layout.svelte` (placeholder → real link) | component | — | `app/src/routes/admin/+layout.svelte` (self) | exact |
| `app/src/routes/admin/pipeline/+page.svelte` | component | request-response | `app/src/routes/admin/login/+page.svelte` | role-match |
| `app/src/routes/admin/pipeline/+page.server.ts` | controller | request-response | `app/src/routes/admin/login/+page.server.ts` | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | component | event-driven (polling) | `app/src/routes/admin/login/+page.svelte` | partial |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | controller | request-response | `app/src/routes/admin/login/+page.server.ts` | role-match |

---

## Pattern Assignments

### `api/routers/admin.py` — add job routes (controller, request-response)

**Analog:** `api/routers/cases.py` + existing `api/routers/admin.py`

**Imports pattern** (`api/routers/cases.py` lines 1–16):
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.schemas.cases import CaseListResponse
from api.services import cases as cases_service
```

**Router construction with auth dependency** (`api/routers/admin.py` lines 43–47):
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```
All new job routes are added to this same `router` — the `dependencies=[Depends(verify_admin_token)]` guard applies automatically.

**Route handler shape** (`api/routers/cases.py` lines 20–32):
```python
@router.get("", response_model=CaseListResponse)
async def get_cases(
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """..."""
    results = await cases_service.get_cases(db)
    return CaseListResponse(cases=results)
```
New job routes follow this exact shape: thin handler, delegates to service, returns typed schema. Add `status_code=202` for the `POST /jobs` creation route.

---

### `api/schemas/admin_jobs.py` (schema, transform)

**Analog:** `api/schemas/cases.py`

**Schema file structure** (`api/schemas/cases.py` lines 1–27):
```python
"""Pydantic v2 response models for the cases API endpoint."""

import datetime
from pydantic import BaseModel

class CaseItem(BaseModel):
    id: int
    slug: str
    # ... typed fields ...
    model_config = {"from_attributes": True}

class CaseListResponse(BaseModel):
    cases: list[CaseItem]
```

Apply `model_config = {"from_attributes": True}` to `AdminJobResponse` so it can be constructed directly from the ORM `AdminJob` instance.

Import the enums from models — they are already defined:
```python
from api.models.models import AdminJobStatus, AdminJobStep
```

The `discrepancies` column is `JSONB` → use `Optional[Any]` or `Optional[list[dict]]` in the schema.

---

### `api/services/admin_jobs.py` (service, CRUD)

**Analog:** `api/services/cases.py`

**Service function shape** (`api/services/cases.py` lines 20–49):
```python
async def get_cases(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Case, Argument)
        .join(...)
        .where(...)
        .order_by(...)
    )
    rows = result.all()
    return [{ ... } for case, argument in rows]
```

For `admin_jobs` service functions, the DB interaction pattern is:
- `select(AdminJob).where(AdminJob.id == job_id)` for single-row reads (use `.scalar_one_or_none()`)
- `select(AdminJob).order_by(AdminJob.created_at.desc()).limit(10)` for the history list
- `update(AdminJob).where(...).values(...).execution_options(synchronize_session=False)` for atomic step-advance guard (see Shared Patterns below)

---

### `api/services/spaces.py` (service, file-I/O)

**No codebase analog** — boto3 is new to this project.

Use the pattern from RESEARCH.md "DO Spaces Upload via boto3" code example. Key points:
- `get_spaces_client()` constructs the boto3 S3 client using `settings` fields
- `upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str` wraps `upload_fileobj`
- New `Settings` fields required: `do_spaces_region`, `do_spaces_endpoint`, `do_spaces_bucket`, `aws_access_key_id`, `aws_secret_access_key` — all optional with `= ""` defaults (same pattern as `anthropic_api_key` in config)

---

### `api/core/config.py` — add DO Spaces fields (config)

**Analog:** `api/core/config.py` (self, lines 1–47)

**Existing pattern for optional fields** (lines 17–18):
```python
# Optional in API — only needed for pipeline steps
anthropic_api_key: str = ""
```
Add five new optional fields using the same `str = ""` default pattern:
```python
# DO Spaces — required only for PIPE-13 file upload path
aws_access_key_id: str = ""
aws_secret_access_key: str = ""
do_spaces_bucket: str = ""
do_spaces_endpoint: str = ""  # e.g. "https://nyc3.digitaloceanspaces.com"
do_spaces_region: str = ""    # e.g. "nyc3"
```

---

### `pipeline/__main__.py` — add `--job-id` to subparsers (CLI config)

**Analog:** `pipeline/__main__.py` (self, lines 54–130)

**Existing argument declaration pattern** (lines 54–88):
```python
ingest_p.add_argument(
    "--url",
    required=True,
    help="URL of the transcript PDF (must be https://...supremecourt.gov/...)",
)
```

Add `--job-id` to `ingest_p`, `parse_p`, and `resolve_p` using the same `add_argument` call:
```python
ingest_p.add_argument(
    "--job-id",
    type=int,
    required=False,
    default=None,
    help="admin_jobs.id — when set, subprocess writes status to admin_jobs (Phase 7)",
)
```
`required=False` preserves backward compatibility for direct CLI use without an admin job.

**Asyncio event loop policy** (lines 27–28):
```python
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
This is set at module level. Must not be removed — asyncpg on Windows requires it.

---

### `pipeline/commands/ingest.py` — add `--job-id` + DB writes (service, CRUD + file-I/O)

**Analog:** `pipeline/commands/resolve.py`

**Session pattern for pipeline DB writes** (`pipeline/commands/resolve.py` lines 76–102):
```python
async with get_session() as session:
    # ORM operation here
    # get_session() commits on clean __aexit__
```

**Update pattern with execution_options** (`pipeline/commands/resolve.py` lines 158–168):
```python
await session.execute(
    update(Utterance)
    .where(
        Utterance.argument_id == parse_run.argument_id,
        Utterance.pipeline_run_id == args.run_id,
        Utterance.raw_speaker_label == raw_label,
    )
    .values(person_id=person_id)
    .execution_options(synchronize_session=False)  # required — Pitfall 3
)
```
Always include `.execution_options(synchronize_session=False)` on raw UPDATE calls from the pipeline CLI. This is a critical guard documented in resolve.py's module docstring.

**Error capture pattern** — wrap `run_ingest` body in try/except; on any exception:
```python
except Exception as exc:
    if args.job_id:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(status=AdminJobStatus.FAILED, error_message=str(exc))
                .execution_options(synchronize_session=False)
            )
    raise
```

**Import additions needed:**
```python
from sqlalchemy import select, update  # update is already in resolve.py
from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
```

---

### `pipeline/commands/parse.py` — add `--job-id` + DB writes (service, CRUD)

**Analog:** `pipeline/commands/resolve.py`

Same DB write pattern as ingest: mark `status=RUNNING`/`current_step=PARSE` at start, `status=COMPLETED` on success, `status=FAILED, error_message=str(exc)` on exception. See ingest pattern above — identical structure.

---

### `pipeline/commands/resolve.py` — replace interactive prompt with DB writes (service, CRUD)

**Analog:** `pipeline/commands/resolve.py` (self)

**The `_prompt_operator` call** (line 154) is replaced entirely. When `alias` is `None` (MISS), instead of awaiting `_prompt_operator`, collect the label into a `discrepancies` list.

**Existing KeyboardInterrupt handler** (lines 196–203) is the model for the new paused exit:
```python
except KeyboardInterrupt:
    resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
    await session.flush()
    print(...)
    return
```
Replace this block with a structured exit when `discrepancies` is non-empty: write `discrepancies` JSONB to `admin_jobs` and set `status=PAUSED`, then return (exit without error). The `_prompt_operator` and `_create_new_person` functions are no longer called — they can be removed.

**People query for candidates** (lines 218–225) — this select pattern is reused to populate `candidates` in each discrepancy entry:
```python
people_result = await session.execute(
    select(Person, Role.name.label("role_name"))
    .outerjoin(Role, Person.role_id == Role.id)
    .order_by(Person.full_name)
)
```

---

### `app/src/routes/admin/+layout.svelte` — placeholder to real link (component)

**Analog:** `app/src/routes/admin/+layout.svelte` (self, lines 28–35)

Replace the disabled `<span>` for Pipeline Runner with a real `<a>` tag:
```svelte
<!-- Current (lines 28–35): -->
<span
    aria-disabled="true"
    aria-label="Pipeline Runner (coming soon)"
    style="font-size: 14px; font-weight: 400; color: #94a3b8; opacity: 0.5; cursor: default;"
>
    Pipeline Runner
</span>

<!-- Replace with: -->
<a
    href="/admin/pipeline"
    style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;"
>
    Pipeline Runner
</a>
```
People Editor `<span>` stays disabled — it is Phase 8.

---

### `app/src/routes/admin/pipeline/+page.server.ts` (controller, request-response)

**Analog:** `app/src/routes/admin/login/+page.server.ts`

**Load function pattern** (`app/src/routes/admin/login/+page.server.ts` lines 7–13):
```typescript
export const load: PageServerLoad = async ({ locals }) => {
    if (locals.session) {
        throw redirect(302, '/admin');
    }
    return {};
};
```
The pipeline start page needs a load function that fetches the recent jobs list from `GET /api/admin/jobs` and returns it. Pattern for calling FastAPI from `+page.server.ts`:
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
// ...
const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
    headers: { 'X-Admin-Token': ADMIN_TOKEN },
});
const jobs = await res.json();
return { jobs };
```

**Form action pattern** (`app/src/routes/admin/login/+page.server.ts` lines 15–51):
```typescript
export const actions: Actions = {
    default: async ({ request, cookies }) => {
        const data = await request.formData();
        // ... validate ...
        throw redirect(302, '/admin');
    }
};
```
The pipeline start form action reads `mode` (`url` or `upload`) from `formData`, calls `POST /api/admin/jobs` with `X-Admin-Token`, then does `throw redirect(303, '/admin/pipeline/${id}')`. Use `throw redirect` (not bare `redirect`) — consistent with all existing SvelteKit actions in this project.

**Private env imports** (line 1):
```typescript
import { ADMIN_USERNAME, ADMIN_PASSWORD } from '$env/static/private';
```
For pipeline pages, import `ADMIN_TOKEN` and `FASTAPI_BASE_URL` from `$env/static/private`.

---

### `app/src/routes/admin/pipeline/+page.svelte` (component, request-response)

**Analog:** `app/src/routes/admin/login/+page.svelte`

**Props pattern** (`app/src/routes/admin/login/+page.svelte` line 6):
```svelte
<script lang="ts">
    let { form } = $props();
</script>
```
For the pipeline start page: `let { data, form } = $props();` — `data` carries the jobs list from the load function.

**Dark theme card** (`app/src/routes/admin/login/+page.svelte` lines 20–30):
```svelte
<div style="
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 32px;
">
```
All new admin cards and panels use these exact color tokens.

**Form with method POST** (line 43): `<form method="POST">` — no `action` attribute needed when there is a single `default` action. For file upload tab add `enctype="multipart/form-data"` on the form (or conditionally via JS).

**Error display pattern** (lines 112–125): `{#if form?.error}` with `role="alert"` and `color: #ef4444`.

**Label/input pattern** (lines 45–76): `<label for="...">` + `<input style="background-color: #0f1117; border: 1px solid #334155; ...">`. Reuse these exact inline styles for all new form inputs.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (controller, request-response)

**Analog:** `app/src/routes/admin/login/+page.server.ts`

**Load function** fetches `GET /api/admin/jobs/{job_id}` and returns the full job row. If 404, throw `error(404, 'Job not found')`.

**Form action for "Continue Resolve"**: follows same `export const actions: Actions = { default: async ({ request, params }) => { ... } }` shape. Calls `POST /api/admin/jobs/{params.job_id}/resolve` with the confirmed matches JSON body.

**Env imports** — same as pipeline start page: `ADMIN_TOKEN`, `FASTAPI_BASE_URL` from `$env/static/private`.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (component, event-driven)

**Analog:** Partial — no existing polling component. Use RESEARCH.md Pattern 1 as the reference.

**Props pattern** — Svelte 5 Runes:
```svelte
<script lang="ts">
    import { invalidateAll } from '$app/navigation';
    let { data } = $props();
</script>
```

**Polling `$effect`** (RESEARCH.md Pattern 1):
```svelte
$effect(() => {
    const TERMINAL = new Set(['completed', 'failed', 'paused']);
    if (TERMINAL.has(data.job.status)) return;

    const interval = setInterval(async () => {
        await invalidateAll();
    }, 2500);

    return () => clearInterval(interval);
});
```
`$effect` returning a cleanup function is Svelte 5 canonical pattern — no `onMount`/`onDestroy` imports needed.

**Dark theme card** — reuse the `#1e293b` / `#334155` / `#94a3b8` tokens from `+layout.svelte` and `login/+page.svelte`. Step cards are `<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 16px;">`.

**No legacy Svelte** — never use `export let`, `$:`, `onMount`, or `$store` syntax. All reactive state is `$state`, `$derived`, or `$effect`.

---

## Shared Patterns

### Authentication: X-Admin-Token on all SvelteKit → FastAPI calls

**Source:** `app/src/routes/admin/login/+page.server.ts` line 1 + `api/routers/admin.py` lines 26–47

All `fetch()` calls from any `+page.server.ts` to FastAPI must include this header:
```typescript
headers: {
    'X-Admin-Token': ADMIN_TOKEN,
    'Content-Type': 'application/json',
}
```
`ADMIN_TOKEN` imported from `$env/static/private`. Never `PUBLIC_` prefix.

### Session guard

**Source:** `app/src/hooks.server.ts` (Phase 6)

All `/admin/*` routes are already guarded by `hooks.server.ts`. No per-page auth check needed in new `+page.server.ts` load functions.

### SQLAlchemy UPDATE with execution_options

**Source:** `pipeline/commands/resolve.py` lines 158–168

Every raw `update(Model).values(...).execute()` call from pipeline CLI code must include `.execution_options(synchronize_session=False)`. This is a mandatory guard documented in resolve.py's module docstring.

### Atomic step-advance guard (FastAPI service layer)

**Source:** RESEARCH.md Pattern 3 — no existing codebase analog (first use of atomic rowcount guard)

```python
result = await db.execute(
    update(AdminJob)
    .where(
        AdminJob.id == job_id,
        AdminJob.current_step == AdminJobStep.INGEST,
        AdminJob.status == AdminJobStatus.COMPLETED,
    )
    .values(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.PARSE)
    .execution_options(synchronize_session=False)
)
await db.commit()
spawned = result.rowcount == 1
```
Return `spawned` to the caller; only call `spawn_pipeline_step(...)` if `spawned is True`.

### Fire-and-forget subprocess spawn

**Source:** RESEARCH.md Pattern 2 — no existing codebase analog

```python
import subprocess, sys

def spawn_pipeline_step(step: str, job_id: int, extra_args: list[str]) -> None:
    cmd = [sys.executable, "-m", "pipeline", step, "--job-id", str(job_id)] + extra_args
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)
```
Use `sys.executable` — never bare `"python"` (Pitfall 7 in RESEARCH.md).

### Dark admin theme tokens

**Source:** `app/src/routes/admin/+layout.svelte` and `app/src/routes/admin/login/+page.svelte`

| Token | Value | Usage |
|---|---|---|
| Page background | `#0f1117` | `<main>` or `<body>` background |
| Card surface | `#1e293b` | Card, nav, input backgrounds |
| Border | `#334155` | All borders |
| Body text | `#94a3b8` | Labels, secondary text |
| Accent | `#93c5fd` | Active links, highlights |
| Heading | `#e2e8f0` | Primary heading text |
| Error | `#ef4444` | Error messages (`role="alert"`) |

### SvelteKit `throw redirect` convention

**Source:** `app/src/routes/admin/login/+page.server.ts` line 49 and `app/src/routes/admin/+page.server.ts` line 15

All redirects in SvelteKit actions use `throw redirect(...)` (not bare `redirect(...)`). This is consistent with SvelteKit 2 behavior as used throughout this project.

### Pydantic schema `model_config`

**Source:** `api/schemas/cases.py` line 20

```python
model_config = {"from_attributes": True}
```
Required on all response schemas that are constructed from SQLAlchemy ORM objects.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `api/services/spaces.py` | service | file-I/O | boto3 is new to this project; no S3/object-storage code exists yet |

---

## Metadata

**Analog search scope:** `api/routers/`, `api/services/`, `api/schemas/`, `api/core/`, `pipeline/commands/`, `pipeline/`, `app/src/routes/admin/`
**Files read:** 15 source files
**Pattern extraction date:** 2026-06-16
