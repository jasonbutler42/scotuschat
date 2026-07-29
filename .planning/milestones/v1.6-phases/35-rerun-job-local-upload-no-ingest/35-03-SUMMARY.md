---
phase: 35-rerun-job-local-upload-no-ingest
plan: 03
subsystem: testing
tags: [pytest, fastapi, sveltekit, admin-jobs, capability-removal]
requires:
  - phase: 35-rerun-job-local-upload-no-ingest
    provides: Backend and frontend same-source recreation seams removed by Plans 01 and 02
provides:
  - Authenticated public-contract proof that the retired route returns framework 404
  - Positive regressions for ordinary creation, recovery, persistence, and disk PDF delivery
  - Complete backend and frontend verification evidence for Phase 35
affects: [admin-jobs, pipeline-history, phase-35-verification]
tech-stack:
  added: []
  patterns: [Authenticated ASGI route absence tests paired with positive neighboring-contract regressions]
key-files:
  created: [api/tests/test_admin_jobs_phase35.py]
  modified: [api/tests/test_admin_jobs_phase25.py]
key-decisions:
  - "Treat exact retired-symbol matches in deliberate negative regressions as evidence, while retaining legitimate PipelineRun history and re-execution language."
  - "Use committed isolated-database fixtures with explicit cleanup for service, route, recovery, and disk-PDF public boundaries."
patterns-established:
  - "Capability-removal regression: prove authenticated 404-by-absence and independently prove supported neighboring contracts."
requirements-completed: [PIPE-29]
coverage:
  - id: D1
    description: "Authenticated same-source recreation requests receive framework 404 with no compatibility payload."
    requirement: PIPE-29
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase35.py#test_authenticated_retired_rerun_route_returns_framework_404"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ordinary service and route creation preserve source fields and launch exactly one ingest step."
    requirement: PIPE-29
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase35.py#create-job service and route tests"
        status: pass
    human_judgment: false
  - id: D3
    description: "Failed recovery and disk-backed source PDF delivery remain functional after capability removal."
    requirement: PIPE-29
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase35.py#recovery and PDF tests"
        status: pass
    human_judgment: false
  - id: D4
    description: "Focused, API, full pytest, Svelte check, and production build matrices pass."
    requirement: PIPE-29
    verification:
      - kind: other
        ref: "41 focused; 298 API; 492 passed and 5 xfailed full suite; svelte-check 0 errors; vite build success"
        status: pass
    human_judgment: false
duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 35 Plan 03: Removal Contract Regression Summary

**Authenticated removal-by-absence coverage now proves the retired route returns framework 404 while ordinary job creation, recovery, durable source fields, and disk-backed PDF delivery remain operational.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-14T21:20:00Z
- **Completed:** 2026-07-14T21:40:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added five isolated-database public-contract regressions covering authenticated route absence, service persistence, ordinary ingest launch, failed recovery, and sanitized disk-PDF delivery.
- Renamed the Phase 25 recovery guard around ordinary new-run behavior while retaining ingest/parse/resolve coverage and negative same-source guidance assertions.
- Passed the complete Phase 35 verification matrix: 41 focused tests, 298 API tests, 492 full-suite passes with 5 expected failures, Svelte check with 0 errors, and production build.

## Task Commits

1. **Task 1: Add focused public-contract removal and neighbor regressions** - `60306f4f`
2. **Task 2: Preserve recovery semantics and execute the complete verification matrix** - `56057f9a`

## Files Created/Modified

- `api/tests/test_admin_jobs_phase35.py` - Authenticated route absence plus supported creation, persistence, recovery, and PDF delivery regressions.
- `api/tests/test_admin_jobs_phase25.py` - Renamed ordinary-new-run negative guidance guard.

## Decisions Made

- Deliberate negative regression strings are the only exact retired-symbol matches; they prove absence and are not active capability ownership.
- Broad rerun-language matches remain because they describe legitimate PipelineRun history, individual-step continuation, idempotent imports, Svelte load execution, or test execution.
- Tests that cross commit-owning service/route boundaries use the configured isolated test database and explicit cleanup rather than nesting commits inside the rollback fixture.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The Windows restricted-token sandbox blocked the patch helper, pytest temporary paths, frontend compiler subprocesses, and the Git index. Exact plan-scoped PowerShell transformations and the required verification/commit commands were rerun with narrow approval; scoped diffs were inspected immediately.
- The initial ingest-argument expectation included the primary docket twice. The production normalization contract correctly emits the authoritative submitted source docket list after `--dockets`; the test expectation was corrected to the observed established interface.
- Disk-PDF fixture cleanup initially attempted to delete the Argument before its PipelineRun. Cleanup was corrected to delete PipelineRun, AdminJob, then Argument, matching foreign-key ownership.

## Verification

- Focused Phase 35 matrix: 41 passed.
- API suite: 298 passed.
- Full configured pytest suite: 492 passed, 5 xfailed.
- Svelte check: 0 errors, 16 pre-existing warnings.
- Production build: passed.
- Exact active-capability scan: only deliberate negative regression strings.
- Broad semantic scan: manually classified legitimate history, step continuation, import idempotency, load execution, and test terminology.

## Known Stubs

None.

## Security Verification

- T-35-09: the retired-route request uses the configured valid admin token, distinguishing route absence from authentication rejection.
- T-35-10: ordinary creation mocks only `api.routers.admin.spawn_pipeline_step` and asserts exactly one ingest call; no subprocess executes.
- T-35-11: the PDF test uses a temporary stored server path and proves Content-Disposition exposes only a sanitized display filename.
- T-35-12: all DB-backed checks use the configured isolated test database with explicit cleanup.
- T-35-13: exact and broad semantic scans are classified above.
- No unresolved critical or high-severity threat remains.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 35 is fully implemented and verified across backend and frontend suites.
- The phase can proceed to verification/completion routing with no open plan-scoped blocker.

## Self-Check: PASSED

- Both plan-scoped test files exist.
- Task commits `60306f4f` and `56057f9a` exist in repository history.
- No plan-scoped file deletion or unrelated staged change occurred.

---
*Phase: 35-rerun-job-local-upload-no-ingest*
*Completed: 2026-07-14*
