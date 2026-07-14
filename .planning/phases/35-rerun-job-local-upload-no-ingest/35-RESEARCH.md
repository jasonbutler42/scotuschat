# Phase 35: Remove pipeline job rerun capability - Research

**Researched:** 2026-07-14
**Domain:** Capability retirement across FastAPI, service, SvelteKit server actions, and regression tests
**Confidence:** HIGH

## User Constraints

### Locked decisions

- **D-01:** Delete `POST /api/admin/jobs/{job_id}/rerun` completely; old callers receive the framework's normal `404 Not Found`, not a compatibility `410 Gone` route.
- **D-02:** Delete the `rerun_job` service function and all direct callers; do not retain dormant internal rerun support.
- **D-03:** Do not migrate, annotate, or otherwise rewrite historical jobs that may have been created through rerun. They remain ordinary existing job records.
- **D-04:** Add API-level coverage proving the removed route returns 404 and neighboring job creation and recovery routes remain functional.
- **D-05:** Remove the retired capability throughout active code and tests, including UI/action symbols, comments, error keys, and capability-specific tests. Do not rewrite historical or archived planning artifacts.
- **D-06:** Preserve legitimate uses of pipeline-run records, individual step recovery/re-execution concepts, and test reruns. The removal targets only same-source pipeline-job rerun capability.
- **D-07:** Remove the entire SvelteKit `rerun` form action and its `rerunError` response contract even if no current page renders a rerun button.
- **D-08:** When a rerun-specific test contains useful general job-creation or source-handling coverage, rewrite that coverage under a non-rerun test instead of deleting it wholesale.
- **D-09:** Keep the operator instruction to "start a new run"; it describes ordinary creation without implying a same-source rerun.
- **D-10:** Preserve distinct ingest, parse, and resolve failure guidance.
- **D-11:** Keep recovery links pointed at `/admin/pipeline/`, where the operator can start a genuinely new run.
- **D-12:** Preserve and rename the behavioral test guard that ensures failed-step guidance never recommends a same-source rerun.
- **D-13:** Add focused service and route coverage for the normal create-job path; a new broad browser/E2E test is not required.
- **D-14:** Add focused coverage proving a stored job can still expose its source PDF after rerun removal.
- **D-15:** Add job-detail load coverage proving an existing historical job remains viewable without rerun metadata or support.
- **D-16:** Verification must run focused removal regressions, relevant API tests, frontend checks, and the broader backend/frontend suites.

### the agent's Discretion

No discussed decisions were delegated to the agent.

### Deferred Ideas

None — discussion stayed within phase scope.

## Summary

This is a narrow deletion and regression-hardening phase, not a repair of the older PIPE-29 behavior. The current implementation has exactly three capability-owning seams: the FastAPI `POST /jobs/{job_id}/rerun` handler, `admin_jobs.rerun_job`, and the SvelteKit `rerun` action with its `rerunError` payload. The detail page currently renders no rerun form or button, so the visible UI criterion is already satisfied; the hidden server action still must be removed. [VERIFIED: codebase inspection]

The main planning risk is over-broad text cleanup. The repository uses “rerun” for several legitimate concepts: re-executing an individual pipeline step, selecting the latest `PipelineRun`, idempotent CLI imports, test reruns, and SvelteKit load re-execution. Those references must remain. Cleanup should target same-source **job** rerun ownership and stale capability comments, while preserving the failed-step guidance contract and renaming its negative behavioral guard as required. [VERIFIED: codebase inspection]

**Primary recommendation:** Split execution into a backend retirement/regression plan and a frontend contract-removal/job-detail regression plan, then finish with a repository-wide semantic scan plus focused and full-suite verification.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Ordinary job creation | `api/routers/admin.py` | `api/services/admin_jobs.py` | Router validates URL/upload and spawns ingest; service persists the `AdminJob`. [VERIFIED: codebase inspection] |
| Retired same-source job rerun | `api/routers/admin.py` | `api/services/admin_jobs.py` | The route calls the service, rebuilds docket arguments, and conditionally spawns ingest. Both ownership points must disappear. [VERIFIED: codebase inspection] |
| Job-detail orchestration | `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | `+page.svelte` | The load function composes the existing job view; the hidden action proxies mutations. [VERIFIED: codebase inspection] |
| Source PDF | `GET /api/admin/jobs/{job_id}/pdf` | SvelteKit `pdf/+server.ts` and detail-page `pdfHref` | Spaces jobs redirect; disk-backed jobs resolve the ingest `PipelineRun.pdf_path`. [VERIFIED: codebase inspection] |
| Failed-step recovery | `derive_failed_step_recovery` | API endpoint and `FailedStepGuidance.svelte` | Backend owns distinct guidance and the `/admin/pipeline/` recovery link. [VERIFIED: codebase inspection] |

## Standard Stack

No new dependency or stack choice is needed. Use the repository’s existing FastAPI router, SQLAlchemy async service, pytest/httpx `ASGITransport`, and SvelteKit server-load/action patterns. [VERIFIED: `requirements.txt`, `api/tests`, `app/package.json`]

### Core

| Library/framework | Project use | Phase use |
|---|---|---|
| FastAPI / Starlette routing | Admin API | Deleting the route should naturally produce 404 for the retired path. [VERIFIED: codebase inspection] |
| SQLAlchemy async | `AdminJob` persistence and retrieval | Preserve `create_job`, `get_job`, `get_run_id_for_step`, and PDF lookup behavior. [VERIFIED: codebase inspection] |
| pytest + httpx ASGITransport | API/service tests | Prove retired route 404 and neighboring routes still work without a network server. [VERIFIED: codebase inspection] |
| SvelteKit | Admin server loads/actions | Remove only the named rerun action and verify historical-job load composition. [VERIFIED: codebase inspection] |

## Architecture Patterns

### System Architecture Diagram

```text
Operator starts genuinely new run
  -> SvelteKit /admin/pipeline action
  -> POST /api/admin/jobs
  -> admin_jobs.create_job
  -> spawn ingest with URL, Spaces key, or local-file path

Operator opens existing job
  -> SvelteKit [job_id] load
  -> GET job + optional participants/argument/readiness/recovery/resolve rows
  -> detail page renders history and derives /admin/pipeline/{id}/pdf
  -> source PDF proxy -> FastAPI PDF route -> Spaces redirect OR disk FileResponse

Old caller posts /jobs/{id}/rerun
  -> no matching route
  -> framework 404
```

### Pattern 1: Delete ownership seams, retain neighbors

Remove the whole FastAPI rerun decorator/function block, the whole service function, and the whole SvelteKit action member. Then repair section headers and route-ordering comments so they no longer name the retired capability. Do not add a tombstone handler. [VERIFIED: codebase inspection]

### Pattern 2: Regression tests follow surviving contracts

Tests should assert positive behavior through surviving public/service seams rather than reconstructing the removed implementation. A focused phase test module can cover: service `create_job`; authenticated POST creation with subprocess spawning mocked; retired POST returns 404; failed-recovery endpoint/guidance; source PDF response; and detail-load composition. [VERIFIED: existing pytest/httpx patterns]

### Pattern 3: Semantic cleanup, not raw keyword deletion

Use targeted searches for `/rerun`, `rerun_job`, `rerunError`, and the SvelteKit action key to prove capability removal. Review broader `rerun|re-run` matches manually and retain legitimate pipeline-step, import-idempotency, test-run, and framework-load meanings. [VERIFIED: codebase inspection]

### Component Responsibilities

| File | Required planning action |
|---|---|
| `api/routers/admin.py` | Delete lines owning the rerun POST behavior; update “Approve, Re-run…” and route ordering comments; preserve create, approve, recovery, PDF, delete, and participant routes. |
| `api/services/admin_jobs.py` | Delete `rerun_job`; rename the Phase 15 section header; preserve `create_job`, historical job lookup, latest pipeline-run semantics, and recovery behavior. |
| `api/schemas/admin_jobs.py` | Reword active comments that describe the retired action while preserving the “ordinary new run” contract. |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Delete the entire `rerun` action and all `rerunError` returns; preserve load and neighboring actions. |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | No button currently exists; preserve page composition and `pdfHref`. Add only test coverage needed for D-15. |
| `api/tests/test_admin_jobs_phase25.py` | Rename/preserve the failed-guidance negative guard; do not delete the distinct ingest/parse/resolve tests. |
| New or existing focused Phase 35 tests | Add 404, normal creation, recovery, source-PDF, and historical-detail regressions without introducing browser E2E scope. |

### Anti-Patterns to Avoid

- **Compatibility tombstone:** A 410 route violates D-01 and keeps retired API ownership alive.
- **Deleting every “rerun” string:** This would damage legitimate step/pipeline-run and idempotency documentation/tests protected by D-06.
- **Testing only symbol absence:** D-04 and D-13 through D-15 require positive neighboring behavior, not only grep assertions.
- **Recreating a same-source job in fixtures as the behavior under test:** Historical job fixtures should simply seed an ordinary `AdminJob`; no rerun metadata exists in the model. [VERIFIED: codebase inspection]
- **Migrating historical rows:** There is no phase-authorized schema/data rewrite.
- **Broad E2E addition:** The locked decision explicitly calls for focused service/route/load coverage.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Retired-route response | Explicit catch-all or 410 endpoint | Framework route absence | Produces the required normal 404 with no dormant compatibility surface. |
| API test client | Live server harness | Existing `httpx.AsyncClient(ASGITransport(app=app))` pattern | Matches repository tests and stays focused. |
| Historical provenance | Rerun markers or migrations | Existing `AdminJob` rows and `get_job` | D-03 says historical jobs are ordinary records. |
| PDF fixture path | New storage abstraction | Existing `PipelineRun.pdf_path` + temporary file, or existing Spaces mock pattern | Exercises the actual source-PDF route contract. |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Existing `admin_jobs`, linked arguments, and `pipeline_runs`; no rerun-specific model column or metadata was found. [VERIFIED: codebase inspection] | Preserve all rows; no migration, annotation, backfill, or cleanup. |
| In-memory state | No rerun-specific client state is rendered in `+page.svelte`; `rerunError` exists only as a SvelteKit action return contract. [VERIFIED: codebase inspection] | Delete the action/error contract; preserve live job polling and detail state. |
| Persisted client state | No localStorage, cookie, or URL parameter for job rerun was found. [VERIFIED: codebase inspection] | No client-state migration. |
| Configuration | No rerun flag/environment variable was found; ordinary admin token, FastAPI URL, storage, and database configuration remain shared dependencies. [VERIFIED: codebase inspection] | Do not change configuration. |
| External/cached state | Spaces objects and local uploaded PDFs may be referenced by historical jobs; pipeline-run records identify disk PDF paths. [VERIFIED: codebase inspection] | Preserve source objects and PDF lookup; do not delete or rewrite them. |

## Exact Active References and Cleanup Boundary

### Remove or rewrite

- `api/routers/admin.py`: route block at current lines 1256–1290; Phase 15 header near 1227; delete-route ordering note near 1310–1312. [VERIFIED: codebase inspection]
- `api/services/admin_jobs.py`: `rerun_job` at current lines 611–635; Phase 15 header near 541. [VERIFIED: codebase inspection]
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`: `rerun` action block beginning near current line 352, including all `rerunError` keys. [VERIFIED: codebase inspection]
- `api/schemas/admin_jobs.py`, `api/routers/admin.py`, and `api/services/admin_jobs.py`: stale same-source-action wording should be rewritten to describe ordinary new-run recovery while keeping the behavior. [VERIFIED: codebase inspection]
- `api/tests/test_admin_jobs_phase25.py`: preserve but rename `test_derive_failed_step_recovery_never_recommends_same_source_rerun` per D-12. [VERIFIED: codebase inspection]

### Preserve

- Latest-`PipelineRun` selection comments and tests in `admin_jobs.py`, `arguments.py`, and `pipeline/tests/test_pipeline_run.py`; these concern step/run history, not job recreation. [VERIFIED: codebase inspection]
- Idempotent CLI/import “rerun” language and tests. [VERIFIED: codebase inspection]
- Svelte `$effect` and redirect comments about load functions re-running. [VERIFIED: codebase inspection]
- `derive_failed_step_recovery`, its distinct strings, its `/admin/pipeline/` href, and `FailedStepGuidance.svelte`. [VERIFIED: codebase inspection]
- `GET /jobs/{job_id}/pdf`, the SvelteKit PDF proxy, `pdfHref`, and the ingest-failure source link. [VERIFIED: codebase inspection]

## Regression Test Design

### Backend service and route

1. **Service create path:** with `db_session`, call `create_job` using representative source fields and assert a PENDING/INGEST job with source values survives reload. This is the focused D-13 service proof. [VERIFIED: existing fixture pattern]
2. **Route create path:** use `ASGITransport`, authenticated multipart POST, and mock `spawn_pipeline_step`; prefer URL mode for a compact route test, or local upload if explicitly protecting that surviving branch. Assert 202 and one ingest spawn. Avoid allowing a real subprocess. [VERIFIED: router implementation]
3. **Retired route:** authenticated POST `/api/admin/jobs/{id}/rerun` must return 404. This can run without a live DB because no handler/dependency should match. [VERIFIED: routing structure]
4. **Recovery neighbor:** retain the pure guidance tests and add/retain endpoint-level coverage where practical; assert ingest/parse/resolve wording remains distinct and href is `/admin/pipeline/`. [VERIFIED: current tests and service]
5. **Source PDF:** seed a stored job plus ingest `PipelineRun` with a temporary PDF path, call authenticated GET, and assert 200/application-pdf/content-disposition. This directly covers the disk-backed historical/local path; a separate lightweight mock can preserve the Spaces redirect branch if existing coverage already supports it. [VERIFIED: PDF route implementation]

### Frontend server load

The repository has no frontend unit-test runner in `app/package.json`; it exposes `check` and `build` only. D-15 therefore needs either a narrowly introduced test harness (not recommended for this cleanup) or a focused structural/load contract test using the repository’s existing test conventions. The least-expansive executable approach is a Python structural test that reads `+page.server.ts` and proves: the load still fetches the job; returns the job; has no `rerun` action or `rerunError`; and the Svelte page still derives `pdfHref` from the historical job source fields. Pair that with `npm run check` and `npm run build`. [VERIFIED: `app/package.json` and route source]

If the planner chooses a TypeScript-level load test, it must first plan the required test runner/config dependency explicitly; no such infrastructure exists today, making that approach disproportionate to the phase. [VERIFIED: codebase inspection]

## Common Pitfalls

| Pitfall | Consequence | Prevention |
|---|---|---|
| Local-upload creation spawns a real process during API testing | Flaky or destructive test | Mock `spawn_pipeline_step` at the router import seam. |
| Disk PDF test points only at `AdminJob.original_filename` | Route still 404s because disk lookup uses the ingest `PipelineRun.pdf_path` | Seed both the job and ingest run, and create a real temporary PDF file. |
| Removing recovery comments/functions because they mention rerun negatively | Violates D-09 through D-12 | Reword stale references but preserve guidance, link, and negative guard. |
| Treating ROADMAP and REQUIREMENTS as equally current | Planner tries to repair local-upload rerun | Make ROADMAP removal scope and D-01–D-16 authoritative; PIPE-29 is superseded history. |
| Assuming there is a visible rerun button to delete | Wasted UI work or unrelated page changes | Record that no rendered form/button exists; remove the hidden server action only. |
| Raw grep gate rejects legitimate `rerun` words | Unrelated pipeline/import semantics get rewritten | Gate exact capability symbols first, then manually classify broad matches. |

## Security and ASVS Review

`security_enforcement` remains applicable because admin API and PDF routes are authenticated, but this phase introduces no new input surface. Removing the rerun POST reduces mutation surface. Preserve the router-level admin-token dependency, server-only `ADMIN_TOKEN` use in SvelteKit, typed `job_id`, URL/PDF validation on ordinary creation, and source-PDF filename sanitization. [VERIFIED: codebase inspection]

Relevant ASVS-style checks for this phase:

- **Access control:** Retired path must be absent; neighboring create/recovery/PDF routes retain admin authentication. [VERIFIED: router-level dependency and SvelteKit private-env usage]
- **Input validation:** Ordinary URL/upload creation continues to validate trusted host, content type, PDF magic bytes, and docket normalization. [VERIFIED: `api/routers/admin.py`]
- **File handling/output encoding:** Disk PDF path comes from a stored pipeline run; filename is sanitized before `Content-Disposition`. Preserve these guards. [VERIFIED: `api/routers/admin.py`]
- **Process invocation:** Tests must mock ingest spawning; implementation must preserve the existing validated argument construction for ordinary creation. [VERIFIED: `api/routers/admin.py`]
- **Data protection:** No historical job/source object deletion or migration is authorized. [VERIFIED: locked D-03]

## Suggested Plan Decomposition

### Plan 35-01: Backend capability retirement and API/service regressions

- Remove the FastAPI rerun handler and service function.
- Clean capability-owning backend comments while preserving step-level rerun/history language.
- Add focused service create, API create, retired-route 404, recovery-neighbor, and source-PDF tests.
- Run focused Phase 35/API tests.

### Plan 35-02: SvelteKit contract retirement, historical detail guard, and full verification

- Remove the SvelteKit rerun action and `rerunError` contract.
- Add focused structural/load coverage for a historical job and preserved PDF link without adding broad E2E infrastructure.
- Rename/preserve the failed-guidance negative guard.
- Run targeted symbol scans, `npm run check`, `npm run build`, broader backend tests, and the full configured pytest suite.

## Verification Strategy

Suggested commands (planner should adjust filenames to the tests it creates):

```powershell
rg -n "rerun_job|/rerun|rerunError" api app -g '!**/node_modules/**'
rg -n -i "rerun|re-run|same.source" api app pipeline -g '!**/node_modules/**'
.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_phase35.py api/tests/test_admin_jobs_phase25.py -q
.\.venv\Scripts\python.exe -m pytest api/tests -q
.\.venv\Scripts\python.exe -m pytest -q
Set-Location app
npm run check
npm run build
```

The first exact-symbol scan should have no active capability matches (except a deliberately named negative regression if the planner keeps the term there). The broad scan is a manual classification tool, not a zero-match gate. [VERIFIED: codebase inspection]

## Open Questions

None. The locked decisions fully determine the retirement behavior and regression scope.

## Sources

### Primary (HIGH confidence)

- `.planning/ROADMAP.md` — authoritative Phase 35 removal goal and success criteria. [VERIFIED: repository source]
- `.planning/phases/35-rerun-job-local-upload-no-ingest/35-CONTEXT.md` — locked D-01 through D-16. [VERIFIED: repository source]
- `api/routers/admin.py`, `api/services/admin_jobs.py`, `api/schemas/admin_jobs.py` — active API/service/recovery/PDF implementation. [VERIFIED: codebase inspection]
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `+page.svelte`, and `pdf/+server.ts` — active load/action/detail/PDF proxy implementation. [VERIFIED: codebase inspection]
- `api/tests/test_admin_jobs_phase25.py`, `api/tests/conftest.py`, and neighboring route tests — established regression patterns. [VERIFIED: codebase inspection]
- `app/package.json`, `pytest.ini` — available frontend and backend verification commands. [VERIFIED: codebase inspection]

### Historical context only

- `.planning/REQUIREMENTS.md` PIPE-29 — superseded repair wording; not implementation direction. [VERIFIED: repository source]

## Metadata

**Confidence breakdown:**
- Capability ownership and exact references: HIGH — directly inspected.
- Regression seams and fixture requirements: HIGH — directly inspected existing routes/tests.
- Frontend structural-test recommendation: HIGH for infrastructure observation; MEDIUM for planner choice because an executor could elect to introduce a runner, though that would expand scope.
- External documentation: not needed; this phase changes no dependency or framework behavior beyond relying on ordinary absence-of-route handling, which the planned API regression verifies directly.

**Research date:** 2026-07-14
**Valid until:** Until the Phase 35 implementation surfaces change.
