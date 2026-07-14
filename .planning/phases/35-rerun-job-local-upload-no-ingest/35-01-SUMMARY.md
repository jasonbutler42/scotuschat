---
phase: 35-rerun-job-local-upload-no-ingest
plan: 01
subsystem: api
tags: [fastapi, admin-jobs, pipeline, capability-removal]
requires:
  - phase: 25-pipeline-job-detail
    provides: Failed-step recovery and job readiness contracts
provides:
  - Retired same-source job recreation API route
  - Removed backend service seam for cloning jobs from prior sources
  - Recovery wording aligned to ordinary new-run creation
affects: [admin-jobs, pipeline-history, phase-35-regression-tests]
tech-stack:
  added: []
  patterns: [Capability retirement by deleting route and service ownership without data migration]
key-files:
  created: []
  modified:
    - api/routers/admin.py
    - api/services/admin_jobs.py
    - api/schemas/admin_jobs.py
key-decisions:
  - "Retire same-source recreation by deleting the route and service function, leaving ordinary creation and durable history unchanged."
  - "Retain broad rerun wording only where it describes legitimate PipelineRun history rather than an operator capability."
patterns-established:
  - "Removal-only retirement: no compatibility response, migration, provenance rewrite, or replacement abstraction."
requirements-completed: [PIPE-29]
coverage:
  - id: D1
    description: "Authenticated callers receive the framework 404 because the same-source recreation route is absent."
    requirement: PIPE-29
    verification:
      - kind: other
        ref: "compileall plus rg absence check for rerun_job and /rerun"
        status: pass
    human_judgment: false
  - id: D2
    description: "The cloning service seam is absent while creation, recovery, PDF, and PipelineRun history code remains."
    requirement: PIPE-29
    verification:
      - kind: other
        ref: "scoped diff inspection and surviving-interface symbol check"
        status: pass
    human_judgment: false
  - id: D3
    description: "Active recovery wording directs operators to ordinary new-run creation without changing schema fields."
    requirement: PIPE-29
    verification:
      - kind: other
        ref: "compileall plus classified broad-language search"
        status: pass
    human_judgment: false
duration: 12min
completed: 2026-07-14
status: complete
---

# Phase 35 Plan 01: Retire Backend Job Recreation Summary

**Deleted same-source job recreation ownership from FastAPI and its service layer while preserving ordinary creation, recovery, PDF delivery, and durable PipelineRun history.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-14T21:20:00Z
- **Completed:** 2026-07-14T21:32:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Removed `POST /jobs/{job_id}/rerun` without adding a compatibility handler, restoring FastAPI's ordinary unmatched-route 404 behavior.
- Removed `admin_jobs.rerun_job` and its cloning ownership without changing stored AdminJob, PipelineRun, or source data.
- Reworded active recovery documentation to ordinary new-run creation while retaining legitimate latest-run and multi-PipelineRun history language.

## Task Commits

1. **Task 1: Delete backend job-recreation ownership seams** - `e4f7bab2`
2. **Task 2: Align active backend wording to the surviving recovery contract** - `d56762fe`

## Files Created/Modified

- `api/routers/admin.py` - Removed the retired route and updated adjacent active route documentation.
- `api/services/admin_jobs.py` - Removed the cloning service and aligned active recovery documentation.
- `api/schemas/admin_jobs.py` - Aligned recovery docstrings without changing fields or response shapes.

## Decisions Made

- Used deletion-only retirement: no compatibility response, replacement abstraction, migration, backfill, or historical-row rewrite.
- Classified the two remaining broad-search matches as legitimate history semantics: latest parse run selection and multiple PipelineRun rows accumulated across step advances.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The Windows restricted-token wrapper blocked the normal patch helper. The orchestrator authorized exact, plan-scoped PowerShell transformations; each replacement asserted a single match and was immediately checked with scoped diffs and `git diff --check`.

## Security Verification

- Router-level admin authentication on all surviving routes was unchanged.
- Source-PDF lookup, stored-path checks, filename sanitization, and redirect/FileResponse behavior were unchanged.
- Ordinary creation validation and ingest argument construction were unchanged.
- No migration, schema mutation, stored-data rewrite, dependency change, or new trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend ownership seams are retired and ready for client cleanup in Plan 35-02.
- Plan 35-03 can add regression coverage for ordinary 404 behavior and preserved neighboring interfaces.

## Self-Check: PASSED

- All three scoped source files exist and compile.
- Task commits `e4f7bab2` and `d56762fe` exist.
- Exact capability symbols are absent; only two manually classified historical-run matches remain.

---
*Phase: 35-rerun-job-local-upload-no-ingest*
*Completed: 2026-07-14*