---
phase: 25-pipeline-job-detail-page
plan: 03
subsystem: api
tags: [sveltekit, fastapi, page-server, admin-jobs, resolve, actions]

# Dependency graph
requires:
  - phase: 25-01
    provides: "RunReadiness/FailedStepRecovery schemas and get_job_readiness/get_failed_step_recovery service helpers; ResolveRowUpdate schema and PATCH /jobs/{job_id}/resolve-rows mutation; PersonCreate raw_speaker_label/side fields"
  - phase: 25-02
    provides: "ResolveRow schema and GET /jobs/{job_id}/resolve-rows read endpoint"
provides:
  - "GET /api/admin/jobs/{job_id}/readiness and GET /api/admin/jobs/{job_id}/failed-recovery router endpoints (missing wiring for Plan 25-01's service functions — added here as a blocking fix)"
  - "+page.server.ts load returns readiness, failedRecovery, resolveRows, and readonlyMode alongside existing job/people/participants/argument/savedValues/hints"
  - "saveResolveRow server action — PATCHes participant_id/side/title to the job-scoped resolve-rows mutation"
  - "addPerson action extended to forward raw_speaker_label/side for the Phase 25 mini create-person popover"
  - "saveJobMetadata now returns refreshResolveRows: true alongside saved: true"
affects: [25-04-page-composition]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-derived readonlyMode: computed once in load() from argument.status !== 'pipeline' (falsy when no argument is linked yet) rather than recomputed per-component."
    - "Conditional non-critical fetches: failedRecovery only fetched when job.status === 'failed'; resolveRows only fetched when job.argument_id != null — mirrors the existing participants/argument conditional-fetch pattern in this file."
    - "saveResolveRow never accepts a client-supplied argument_id — job_id (route param) is the only trust boundary; argument ownership is re-derived and re-verified inside the FastAPI PATCH handler (T-25-16)."

key-files:
  created: []
  modified:
    - api/routers/admin.py
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts

key-decisions:
  - "Plan 25-01 built get_job_readiness and get_failed_step_recovery as service functions but never registered them on the router (only PATCH/GET .../resolve-rows and POST .../people were wired). This blocked Task 1 outright, so two new router endpoints were added under Rule 3 (auto-fix blocking issue): GET /jobs/{job_id}/readiness and GET /jobs/{job_id}/failed-recovery, both mapping the services' ValueError to 422 to match the sibling Phase 25 resolve-rows endpoints' established error-mapping convention."
  - "failedRecovery is only fetched when job.status === 'failed' (not unconditionally) — avoids a wasted round-trip for the common non-failed states, matching this file's existing conditional-fetch style for participants/argument."
  - "resolveRows is only fetched when job.argument_id != null — the backend 422s GET .../resolve-rows for a job with no linked argument (Plan 25-02), so the fetch is skipped entirely rather than relying on error-path degradation."
  - "readonlyMode is computed once in load() (argument != null && argument.status !== 'pipeline') rather than left for each Phase-25-04 component to re-derive, so RunStatusCard/ResolveCard/ArgumentDetailsCard all read the same boolean."
  - "saveJobMetadata's return payload gained refreshResolveRows: true as an explicit signal for D-17, even though ArgumentDetailsCard's existing use:enhance already triggers a default update() (which invalidates the load function and refetches resolveRows) — the flag documents the intent so Plan 25-04's page composition doesn't need to guess why the refresh happens."

requirements-completed: [PJOB-01, PJOB-02, PJOB-14, PJOB-17, PJOB-18, PJOB-19, PJOB-20, PJOB-21, PJOB-22]

coverage:
  - id: D1
    description: "Load function fetches and returns backend-derived readiness, failed-step guidance, and every resolve row for the job, plus a computed readonlyMode boolean, while preserving all existing return fields during the transition."
    requirement: "PJOB-01"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "npm run check confirms the load function type-checks and the new fields are correctly typed, but no runtime/browser verification of the three new backend calls against a live database was performed in this environment (no DATABASE_URL configured) — needs a manual pass against /admin/pipeline/[id] or a DB-backed test run before sign-off."
  - id: D2
    description: "Missing GET /jobs/{job_id}/readiness and GET /jobs/{job_id}/failed-recovery router endpoints were added (Plan 25-01 built the service layer but never wired the router) so the load function in Task 1 has a working HTTP contract to call."
    requirement: "PJOB-02"
    verification:
      - kind: unit
        ref: "pytest api/tests/test_admin_jobs_phase25.py api/tests/test_admin_people_phase25.py -q"
        status: pass
      - kind: unit
        ref: ".venv/Scripts/python.exe -c \"from api.routers import admin\" (router imports cleanly)"
        status: pass
    human_judgment: true
    rationale: "The existing Phase 25 test suites (30 passed, 24 skipped for DB-gated cases) confirm no regression and that the router module imports cleanly with the two new routes, but there is no dedicated HTTP-level test for the two new endpoints themselves in this plan (out of the plan's stated file scope) — a DB-backed manual check or a follow-up test addition should confirm the 200/422 paths before production sign-off."
  - id: D3
    description: "saveResolveRow action submits participant_id, side (BENCH allowed), and title to the job-scoped resolve-row mutation without ever accepting a client-supplied argument_id, and addPerson forwards raw_speaker_label/side for the Phase 25 mini popover contract."
    requirement: "PJOB-14"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "Type-checks and source-level review confirm the action shape matches the Plan 25-01 PATCH contract, but no browser-driven or backend-integration test exercised the new saveResolveRow/addPerson actions end-to-end against a running FastAPI + database in this environment — needs manual UAT or a follow-up integration test."

duration: ~40min
completed: 2026-07-07
status: complete
---

# Phase 25 Plan 03: Job Detail Server Bridge Summary

**SvelteKit `+page.server.ts` load/action bridge for the Phase 25 job detail page — new readiness, failed-recovery, and resolve-row HTTP fetches feeding a computed `readonlyMode`, plus a `saveResolveRow` action and extended `addPerson`/`saveJobMetadata` actions — including two router endpoints (`GET .../readiness`, `GET .../failed-recovery`) that Plan 25-01 had built the service layer for but never exposed over HTTP.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 completed
- **Files modified:** 2 (`app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `api/routers/admin.py`)

## Accomplishments

- Load function now fetches backend-derived `readiness` (always), `failedRecovery` (only when `job.status === 'failed'`), and `resolveRows` (only when `job.argument_id != null`) with the same graceful-degradation pattern already used for `participants`/`argument`, plus a computed `readonlyMode` boolean (`argument != null && argument.status !== 'pipeline'`) — all returned alongside the existing `job`/`people`/`participants`/`argument`/`savedValues`/`hints` fields so current consumers keep working during the transition (D-01 through D-04, D-18 through D-21).
- Added `saveResolveRow` server action: reads `participant_id`, `side` (BENCH allowed), and optional `title` from form data and PATCHes the Plan 25-01 job-scoped resolve-row endpoint, deriving argument ownership entirely server-side (the action never accepts a client-supplied `argument_id`, T-25-16) and surfacing backend 4xx guard failures as a scoped `resolveRowError` (D-14, D-18, PJOB-14, PJOB-18).
- Extended `addPerson` to forward `raw_speaker_label`/`side` for the Phase 25 mini create-person popover (D-12, D-13, PJOB-19), while keeping `role_name` optional/backward-compatible for the older typeahead-driven flow.
- Extended `saveJobMetadata`'s return payload with `refreshResolveRows: true` alongside the existing `saved: true`, making the D-17 bench-role-refresh-after-metadata-save behavior explicit for Plan 25-04's page composition (PJOB-17).
- **Blocking fix:** added `GET /api/admin/jobs/{job_id}/readiness` and `GET /api/admin/jobs/{job_id}/failed-recovery` to `api/routers/admin.py`. Plan 25-01's summary describes `get_job_readiness`/`get_failed_step_recovery` as backend contracts for this plan to call over HTTP, but only wired the resolve-rows PATCH/GET and people POST endpoints on the router — the readiness/failed-recovery service functions were never exposed. Both new endpoints follow the same ValueError-to-422 mapping already established by the sibling Phase 25 resolve-rows endpoints.

## Task Commits

Each task was committed atomically:

1. **Task 1: Load readiness, failed guidance, resolve rows, and readonly mode** - `d89e6934` (feat) — includes the router-endpoint blocking fix (see Deviations)
2. **Task 2: Update server actions for metadata refresh, mini person payload, and resolve-row edits** - `d5c90670` (feat)

_Note: `tdd_mode` is `false` in `.planning/config.json`; both tasks were implemented and verified with `npm run check` per commit rather than as separate RED/GREEN commits._

## Files Created/Modified

- `api/routers/admin.py` - Added `GET /jobs/{job_id}/readiness` and `GET /jobs/{job_id}/failed-recovery`; imports `RunReadiness`/`FailedStepRecovery` from `api.schemas.admin_jobs`.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - Added `RunReadiness`/`FailedStepRecovery`/`ResolveRow` TS interfaces; load fetches `readiness`/`failedRecovery`/`resolveRows` and computes `readonlyMode`; `addPerson` forwards `raw_speaker_label`/`side`; added `saveResolveRow` action; `saveJobMetadata` returns `refreshResolveRows: true`.

## Decisions Made

- The missing router wiring for `get_job_readiness`/`get_failed_step_recovery` was treated as a Rule 3 blocking-issue auto-fix (not a Rule 4 architectural question) because it is a straightforward "expose an existing, already-tested service function over HTTP" gap with an established error-mapping pattern to follow (422-on-ValueError, matching the sibling resolve-rows endpoints) — no new architecture, schema, or design decision was required.
- `failedRecovery` is fetched conditionally on `job.status === 'failed'` rather than unconditionally, to avoid a wasted round-trip on every load for the common non-failed states — matches this file's existing conditional-fetch style for `participants`/`argument`.
- `resolveRows` is fetched conditionally on `job.argument_id != null` rather than always attempting the call and relying on error-path degradation — the backend 422s `GET .../resolve-rows` for an unlinked job (Plan 25-02), so skipping the call entirely avoids a guaranteed-failing request on every job without a linked argument.
- `readonlyMode` is computed once in `load()` instead of left for each Plan 25-04 component to re-derive independently, so `RunStatusCard`, `ResolveCard`, and `ArgumentDetailsCard` all consume the same boolean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added GET /jobs/{job_id}/readiness and GET /jobs/{job_id}/failed-recovery router endpoints**
- **Found during:** Task 1 (Load readiness, failed guidance, resolve rows, and readonly mode)
- **Issue:** The plan's Task 1 action explicitly says to fetch readiness and failed recovery "from the Plan 25-01 job endpoints," but Plan 25-01's `get_job_readiness` and `get_failed_step_recovery` were only ever wired as importable service functions — no router endpoint exposed either one over HTTP. Without this, Task 1 had nothing to fetch from.
- **Fix:** Added `GET /api/admin/jobs/{job_id}/readiness` (`response_model=RunReadiness`) and `GET /api/admin/jobs/{job_id}/failed-recovery` (`response_model=FailedStepRecovery`) to `api/routers/admin.py`, both calling the existing service functions and mapping `ValueError` to 422 — the same pattern already used by the sibling `PATCH`/`GET .../resolve-rows` endpoints from Plans 25-01/25-02.
- **Files modified:** `api/routers/admin.py`
- **Verification:** `python -c "from api.routers import admin"` imports cleanly; `pytest api/tests/test_admin_jobs_phase25.py api/tests/test_admin_people_phase25.py -q` → 30 passed, 24 skipped (no regressions); `cd app; npm run check` → 0 errors.
- **Committed in:** `d89e6934` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue).
**Impact on plan:** Necessary for Task 1 to function at all; no scope creep beyond exposing already-built, already-tested service functions over HTTP using an established error-mapping convention. No new schemas, models, or architectural decisions introduced.

## Issues Encountered

None beyond the router-wiring gap documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 25-04 can now build `RunStatusCard.svelte`, `ResolveCard.svelte`, `FailedStepGuidance.svelte`, and `CreatePersonPopover.svelte` against a stable `+page.server.ts` contract: `data.readiness`, `data.failedRecovery`, `data.resolveRows`, and `data.readonlyMode` are all present, and `?/saveResolveRow`, `?/addPerson`, and `?/saveJobMetadata` (with `refreshResolveRows`) are ready to wire from the new components.
- No `DATABASE_URL` was configured in this execution environment, so the new `GET /jobs/{job_id}/readiness`, `GET /jobs/{job_id}/failed-recovery`, and the `saveResolveRow`/`addPerson` action round-trips were verified via type-checking and the existing (DB-gated-skip) Phase 25 test suites only — not exercised end-to-end against a live database. Per Offen's AI Innovation Program stage-gate, confirm this work has cleared Sandbox → Pilot review, and run a DB-backed manual pass against `/admin/pipeline/[id]` before any production-facing rollout of Plan 25-04's UI.

---

*Phase: 25-pipeline-job-detail-page*
*Completed: 2026-07-07*

## Self-Check: PASSED

All created/modified files exist on disk and all task commit hashes (`d89e6934`, `d5c90670`, `948c460b`) are present in git history.
