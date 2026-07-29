---
phase: 35-rerun-job-local-upload-no-ingest
plan: 02
subsystem: ui
tags: [sveltekit, admin-pipeline, regression-tests]

requires:
  - phase: 25-admin-job-detail
    provides: Historical job detail, failed-step recovery, and source-PDF composition
provides:
  - Job detail action surface without the retired rerun contract
  - Structural regression coverage for historical load, recovery, and PDF wiring
affects: [admin-pipeline, phase-35-verification]

tech-stack:
  added: []
  patterns: [Python source-structure regression for SvelteKit contracts]

key-files:
  created: [api/tests/test_admin_jobs_phase35_frontend.py]
  modified: [app/src/routes/admin/pipeline/[job_id]/+page.server.ts]

key-decisions:
  - "Removal is represented by complete absence of the rerun action and error payload; no compatibility UI was added."

patterns-established:
  - "Frontend capability retirement deletes the complete server action while preserving neighboring load and mutation contracts."

requirements-completed: [PIPE-29]
coverage:
  - id: D1
    description: "The hidden SvelteKit rerun action and rerunError payload are absent."
    requirement: PIPE-29
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase35_frontend.py#test_job_detail_has_no_recreation_action_or_error_contract"
        status: pass
    human_judgment: false
  - id: D2
    description: "Historical job loading, failed recovery, and local source-PDF wiring remain intact."
    requirement: PIPE-29
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase35_frontend.py"
        status: pass
      - kind: integration
        ref: "npm --prefix app run check"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-07-14
status: complete
---

# Phase 35 Plan 02: Retire Job-Detail Rerun Contract Summary

**Removed the hidden job-detail rerun action while preserving authenticated historical loads, failed-run recovery, and local source-PDF navigation.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-14T21:20:00Z
- **Completed:** 2026-07-14T21:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Deleted the complete SvelteKit rerun action, redirect, and rerunError contract without adding replacement UI.
- Added four narrow structural tests covering authenticated historical detail loading, action absence, failed recovery, and PDF composition.
- Preserved the existing job-detail Svelte page byte-for-byte.

## Task Commits

1. **Task 1: Delete the hidden SvelteKit recreation action contract** - `a8008264`
2. **Task 2: Guard historical detail, recovery, and source-link composition** - `82b800f1`

## Files Created/Modified

- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - Removed only the retired rerun action.
- `api/tests/test_admin_jobs_phase35_frontend.py` - Guards surviving load, recovery, and PDF contracts plus rerun absence.

## Decisions Made

- Removal remains an absence-only UI contract; no disabled affordance, notice, or compatibility state was introduced.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The sandbox blocked the frontend build helper with `spawn EPERM`; the same required check passed outside the sandbox with 0 errors.
- The patch editor could not initialize under the Windows restricted-token sandbox, so the two scoped files were written through approved PowerShell operations.

## User Setup Required

None - no external service configuration required.

## Verification

- `python -m pytest api/tests/test_admin_jobs_phase35_frontend.py -q`: 4 passed.
- `npm --prefix app run check`: 0 errors (16 pre-existing warnings).
- Retired symbols `rerunError`, `/rerun`, and `rerun:` are absent from the job-detail server route.

## Known Stubs

None.

## Next Phase Readiness

- Frontend job-recreation ownership is retired and covered for Phase 35 verification.
- No unresolved high-severity threat remains in this plan scope.

## Self-Check: PASSED

- Both scoped files exist.
- Task commits `a8008264` and `82b800f1` exist in history.

---
*Phase: 35-rerun-job-local-upload-no-ingest*
*Completed: 2026-07-14*
