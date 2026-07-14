# Phase 35: Remove pipeline job rerun capability - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/routers/admin.py` | route/controller | request-response, file-I/O, process spawn | Surviving `POST /jobs` and `GET /jobs/{job_id}/pdf` in the same file | exact |
| `api/services/admin_jobs.py` | service | CRUD, transform | `create_job`, `get_job`, and `derive_failed_step_recovery` in the same file | exact |
| `api/schemas/admin_jobs.py` | schema/model | request-response serialization | Existing `FailedStepRecovery` / `AdminJobResponse` declarations in the same file | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | SvelteKit load/controller | request-response, aggregation | Its surviving `load`, `approve`, `resolve`, and delete members | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | read-only integration surface | reactive transform, request-response rendering | Existing `pdfHref` derivation and `RunStatusCard` integration | exact |
| `api/tests/test_admin_jobs_phase25.py` | test | transform, CRUD | Existing failed-step pure and DB-backed recovery tests | exact |
| `api/tests/test_admin_jobs_phase35.py` (expected focused regression module) | test | request-response, CRUD, file-I/O | `test_admin_dashboard_routes.py`, `test_admin_jobs_source.py`, and Phase 25 tests | role-match |
| `api/tests/test_admin_jobs_phase35_frontend.py` (expected structural regression module) | test | direct source inspection | `api/tests/test_question_number_nullable.py` | exact convention match |

The Svelte files use bracketed route directories literally; PowerShell commands must use `-LiteralPath` when reading them.

## Pattern Assignments

### `api/routers/admin.py` (route/controller, request-response + file-I/O)

**Analog:** surviving ordinary creation and PDF handlers in `api/routers/admin.py`.

**Ordinary creation delegation and subprocess boundary** (lines 210-249):

```python
@router.post("/jobs", status_code=202, response_model=AdminJobResponse)
async def create_job(..., db: AsyncSession = Depends(get_db)) -> AdminJobResponse:
    normalized_dockets = _normalize_dockets(primary_docket, source_dockets)
    if pdf_url is not None:
        _validate_pdf_url(pdf_url)
        job = await jobs_service.create_job(
            db, pdf_url=pdf_url, source_dockets=normalized_dockets or None
        )
        ingest_args = ["--url", pdf_url, "--question", str(question_number)]
        ingest_args += _dockets_to_ingest_args(normalized_dockets)
        spawn_pipeline_step("ingest", job.id, ingest_args)
        return job
```

Copy this boundary for positive route regression assertions: the router validates input, delegates persistence, then spawns ingest. Tests must mock `api.routers.admin.spawn_pipeline_step` so no process is launched.

**Upload validation and local-file pattern** (lines 251-324): content type and `%PDF` magic bytes are validated before `create_job`; local development writes `data/uploads/{job.id}.pdf`, then spawns ingest with `--local-file`. Preserve this entire surviving branch.

**Recovery error mapping** (lines 438-455):

```python
@router.get("/jobs/{job_id}/failed-recovery", response_model=FailedStepRecovery)
async def get_job_failed_recovery_endpoint(job_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await jobs_service.get_failed_step_recovery(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

**PDF lookup and safe response pattern** (lines 458-519): load the durable job, redirect Spaces-backed jobs, otherwise locate the ingest `PipelineRun.pdf_path`, verify the file exists, sanitize the display filename, and return `FileResponse(media_type="application/pdf")`. The Phase 35 PDF regression should seed both `AdminJob` and ingest `PipelineRun`; `original_filename` alone is insufficient.

**Retirement pattern:** delete the complete decorated rerun handler rather than substituting a compatibility handler. Absence of a matching route is what yields the required framework 404. Preserve neighboring route order and auth inherited from the router dependency.

---

### `api/services/admin_jobs.py` (service, CRUD + transform)

**Analog:** `create_job` and failed-step recovery in the same service.

**Persistence pattern** (lines 58-94):

```python
async def create_job(db: AsyncSession, *, pdf_url=None, spaces_key=None,
                     original_filename=None, source_dockets=None) -> AdminJob:
    job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        pdf_url=pdf_url,
        spaces_key=spaces_key,
        original_filename=original_filename,
        source_dockets=source_dockets,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job.__dict__["parse_stats"] = None
    return job
```

Use this directly for D-13: call the public service, reload/assert the persisted source fields and `PENDING`/`INGEST` state. Delete `rerun_job` completely; do not replace it with an alias or dormant helper.

**Recovery transform** (lines 643-679):

```python
guidance = _FAILED_STEP_GUIDANCE.get(current_step, _DEFAULT_FAILED_GUIDANCE)
return FailedStepRecovery(
    step=current_step.value if current_step is not None else None,
    guidance=guidance,
    href="/admin/pipeline/",
    raw_error=error_message,
)
```

Preserve distinct ingest/parse/resolve strings and “start a new run.” Rewrite only stale comments that name same-source job rerun; the behavior is an ordinary creation recovery link.

---

### `api/schemas/admin_jobs.py` (schema/model, serialization)

**Analog:** existing `FailedStepRecovery` and `AdminJobResponse` contracts in this file.

No rerun-specific model or persisted field exists, so no migration or schema removal pattern is required. Restrict changes to active comments/docstrings that describe the retired action. Preserve response fields such as `original_filename`, `spaces_key`, `pdf_url`, and failed recovery fields because the detail/PDF and recovery flows consume them.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (load/controller, request-response aggregation)

**Analog:** the same file's surviving load and mutation members.

**Authenticated primary load** (lines 104-122): fetch `GET /api/admin/jobs/{job_id}` with server-only `X-Admin-Token`; convert 404 to SvelteKit 404 and other failures to 502. This primary job fetch remains fatal, while auxiliary requests degrade gracefully.

**Auxiliary recovery load** (lines 208-229):

```typescript
let failedRecovery: FailedStepRecovery | null = null;
if (job.status === 'failed') {
  try {
    const failedRes = await fetch(
      `${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/failed-recovery`,
      { headers: { 'X-Admin-Token': ADMIN_TOKEN } },
    );
    if (failedRes.ok) failedRecovery = await failedRes.json();
  } catch (err) {
    console.error('[load] failed-recovery fetch threw:', err);
  }
}
```

**Stable historical-detail return contract** (lines 286-303): retain `job`, participants, argument, readiness, failed recovery, resolve rows, and `readonlyMode`. Historical jobs need no rerun metadata to load.

**Retirement pattern:** remove the complete `rerun` member from `export const actions`, including every `rerunError` return. Do not disturb the surrounding `approve`, `resolve`, people, row-update, or delete actions. The closest surviving action convention is authenticated server-side fetch, scoped `fail(...)`, then `throw redirect(...)` when navigation is required.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (component/page, reactive transform)

**Analog:** current source-PDF derivation and status-card composition.

**Source link derivation** (lines 193-218):

```svelte
let pdfHref = $derived(
  liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename
    ? `/admin/pipeline/${liveJob.id}/pdf`
    : null,
);

<RunStatusCard
  jobStatus={liveJob.status}
  {pdfHref}
  readiness={data.readiness}
  approveError={form?.approveError}
/>
```

There is no visible rerun button to delete. Preserve this page and protect the `pdfHref`/historical-job composition with focused structural coverage. Do not add browser E2E infrastructure solely for this cleanup.

---

### `api/tests/test_admin_jobs_phase25.py` (test, transform + CRUD)

**Analog:** existing pure guidance tests and DB-backed service test.

**Pure negative guard** (lines 156-166): iterate ingest/parse/resolve, derive recovery, lowercase the guidance, and assert it does not recommend the retired same-source action. Rename the test to express the preserved behavior without deleting it.

**DB fixture/service pattern** (lines 336-356): create an `AdminJob`, `add`, `commit`, `refresh`, call `get_failed_step_recovery`, then assert step/guidance/href/raw error. Reuse this fixture style for the focused `create_job` service regression.

---

### `api/tests/test_admin_jobs_phase35.py` (test, request-response + CRUD + file-I/O)

**Primary analog 1:** `api/tests/test_admin_dashboard_routes.py` lines 16-61.

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

@pytest_asyncio.fixture
async def client():
    from api.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

def _admin_headers() -> dict:
    from api.core.config import settings
    return {"X-Admin-Token": settings.admin_token}
```

Use the authenticated client to assert `POST /api/admin/jobs/{id}/rerun` returns 404. Also assert the normal `POST /api/admin/jobs` path returns 202 and invokes one mocked ingest spawn; route absence, not a tombstone response body, is the contract.

**Primary analog 2:** `api/tests/test_admin_jobs_source.py` lines 35-78. Seed related ORM records with `db_session.add`, `flush`, then call the public service and assert the returned durable job. This is the closest historical-job fixture pattern and proves existing rows need no provenance rewrite.

**Primary analog 3:** `api/routers/admin.py` lines 492-519 describes the exact disk-PDF state to fixture: an ingest `PipelineRun` with a real temporary `pdf_path`, plus an `AdminJob` whose source display name is independent of that server path. Assert 200, `application/pdf`, content disposition, and bytes.

**Frontend structural contract:** follow the repository's existing Python source-inspection test convention rather than introducing a TypeScript test runner. Read `+page.server.ts` and `+page.svelte`; assert the load still fetches/returns `job`, the action object has no `rerun` member or `rerunError`, and the page retains the `pdfHref` derivation. Keep structural assertions narrow enough not to duplicate Svelte syntax checking.

---

### `api/tests/test_admin_jobs_phase35_frontend.py` (test, direct source inspection)

**Analog:** `api/tests/test_question_number_nullable.py` and its focused Python assertions over frontend source text.

Use the same lightweight source-inspection convention to read `+page.server.ts` and assert the authenticated primary job load, returned `job`, and absence of the retired action/error contract. Treat `app/src/routes/admin/pipeline/[job_id]/+page.svelte` as a read-only integration surface: inspect it only to protect the existing `pdfHref` derivation and `RunStatusCard` wiring, and do not modify the page or freeze unrelated Svelte markup, styling, or action order.

## Shared Patterns

### Authentication

**Sources:** `api/routers/admin.py` router dependency; `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`; `api/tests/test_admin_dashboard_routes.py` lines 57-61.

All surviving admin calls keep `X-Admin-Token`. Tests obtain the configured token rather than hardcoding it. The removed route should still return 404 under an authenticated request so the assertion tests route absence rather than authentication failure.

### Error Handling

- FastAPI service `ValueError` is mapped explicitly by the owning route when that is the established neighboring contract.
- SvelteKit's primary job fetch raises `error(...)`; optional detail enrichments catch/log and degrade to empty or null values.
- SvelteKit actions return a scoped `fail(...)` payload for retryable mutations and `throw redirect(...)` after success.
- PDF lookup uses specific 404s for missing job/run/path/file while sanitizing the response filename.

### Database and Runtime Isolation

Use `db_session`, `add`/`flush` or `commit`/`refresh` following the assertion boundary. Mock process spawning for create-route tests. Use a temporary real PDF file for `FileResponse`; never point the test at a repository file or allow a pipeline subprocess to run.

### Semantic Cleanup Boundary

Exact active-capability scans should target `rerun_job`, `/rerun`, `rerunError`, and the SvelteKit action key. Broader `rerun|re-run` results require manual classification: retain pipeline-step execution, latest `PipelineRun`, import idempotency, test reruns, and Svelte load re-execution language.

## No Analog Found

None. Every planned modification is a deletion or regression-hardening change with a close in-repository analog. The expected Phase 35 test module is new, but all of its fixture, transport, persistence, PDF, and structural-inspection patterns already exist.

## Metadata

**Analog search scope:** `api/routers`, `api/services`, `api/schemas`, `api/tests`, `app/src/routes/admin/pipeline`
**Strong analog families:** 4
**Pattern extraction date:** 2026-07-14
