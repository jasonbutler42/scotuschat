# Phase 35: Remove pipeline job rerun capability - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the same-source pipeline-job rerun capability from the active admin UI, SvelteKit server actions, FastAPI route, service layer, and capability-specific tests and references. Preserve existing job records and the ordinary job-creation, failed-step recovery, source-PDF, pipeline-run history, and job-detail flows.

</domain>

<decisions>
## Implementation Decisions

### API retirement
- **D-01:** Delete `POST /api/admin/jobs/{job_id}/rerun` completely; old callers receive the framework's normal `404 Not Found`, not a compatibility `410 Gone` route.
- **D-02:** Delete the `rerun_job` service function and all direct callers; do not retain dormant internal rerun support.
- **D-03:** Do not migrate, annotate, or otherwise rewrite historical jobs that may have been created through rerun. They remain ordinary existing job records.
- **D-04:** Add API-level coverage proving the removed route returns 404 and neighboring job creation and recovery routes remain functional.

### Cleanup breadth
- **D-05:** Remove the retired capability throughout active code and tests, including UI/action symbols, comments, error keys, and capability-specific tests. Do not rewrite historical or archived planning artifacts.
- **D-06:** Preserve legitimate uses of pipeline-run records, individual step recovery/re-execution concepts, and test reruns. The removal targets only same-source pipeline-job rerun capability.
- **D-07:** Remove the entire SvelteKit `rerun` form action and its `rerunError` response contract even if no current page renders a rerun button.
- **D-08:** When a rerun-specific test contains useful general job-creation or source-handling coverage, rewrite that coverage under a non-rerun test instead of deleting it wholesale.

### Failed-job guidance
- **D-09:** Keep the operator instruction to "start a new run"; it describes ordinary creation without implying a same-source rerun.
- **D-10:** Preserve distinct ingest, parse, and resolve failure guidance.
- **D-11:** Keep recovery links pointed at `/admin/pipeline/`, where the operator can start a genuinely new run.
- **D-12:** Preserve and rename the behavioral test guard that ensures failed-step guidance never recommends a same-source rerun.

### Regression coverage
- **D-13:** Add focused service and route coverage for the normal create-job path; a new broad browser/E2E test is not required.
- **D-14:** Add focused coverage proving a stored job can still expose its source PDF after rerun removal.
- **D-15:** Add job-detail load coverage proving an existing historical job remains viewable without rerun metadata or support.
- **D-16:** Verification must run focused removal regressions, relevant API tests, frontend checks, and the broader backend/frontend suites.

### the agent's Discretion
No discussed decisions were delegated to the agent.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirement history
- `.planning/ROADMAP.md` — Current Phase 35 title, goal, boundary, and success criteria; its removal scope is authoritative.
- `.planning/REQUIREMENTS.md` — Contains the older `PIPE-29` wording about repairing local-upload reruns. Treat it as requirement history superseded by the current Phase 35 ROADMAP definition, not as the implementation direction.

### Active implementation surfaces
- `api/routers/admin.py` — FastAPI rerun endpoint and neighboring job routes that must remain intact.
- `api/services/admin_jobs.py` — `rerun_job`, normal job creation, failed-step recovery, and existing-job service behavior.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — Hidden SvelteKit rerun action/error contract and neighboring detail-page actions.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Existing job detail, source-PDF link, and failed-step guidance integration.
- `api/tests/test_admin_jobs_phase25.py` — Existing failed-step guard and reusable recovery coverage.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `create_job` and the normal admin jobs POST route: canonical new-run creation path that remains supported.
- `derive_failed_step_recovery` / `get_failed_step_recovery`: existing step-specific recovery behavior to preserve.
- Job PDF route and `pdfHref`/source link derivation: existing source-PDF access path to protect with regression coverage.

### Established Patterns
- SvelteKit form actions proxy authenticated admin mutations to FastAPI and return scoped `fail(...)` payloads; removal must delete the entire rerun action contract.
- FastAPI routers delegate job business logic to `api/services/admin_jobs.py`; route and service removal should be coordinated.
- Existing jobs are durable history and do not require provenance cleanup when a capability is retired.

### Integration Points
- FastAPI admin job router, admin-jobs service, SvelteKit job-detail server actions, job-detail page loading, source-PDF access, and related API/frontend tests.

</code_context>

<specifics>
## Specific Ideas

- Removal should look like the capability never existed in the active API: normal 404, no tombstone endpoint.
- "Start a new run" remains the preferred operator language for recovery.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 35-Remove pipeline job rerun capability*
*Context gathered: 2026-07-14*
