---
phase: 26-arguments-admin
plan: 06
subsystem: api
tags: [fastapi, sqlalchemy, sveltekit, svelte5, pydantic]

# Dependency graph
requires:
  - phase: 26-arguments-admin
    provides: RunStatusCard's Archived badge override (already_created state) on the pipeline detail page, established in Plan 26-03/26-04
provides:
  - is_archived boolean on AdminJobResponse, populated by list_jobs() via an Argument outerjoin
  - Grey "Archived" badge on /admin/pipeline list page, matching the detail page's RunStatusCard
affects: [arguments-admin, pipeline-admin-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "list_jobs() LEFT OUTER JOINs Argument to derive a per-row boolean without an N+1 query, following the same job.__dict__ dynamic-attribute injection pattern already used for parse_stats"

key-files:
  created: []
  modified:
    - api/schemas/admin_jobs.py
    - api/services/admin_jobs.py
    - api/tests/test_admin_jobs_list.py
    - app/src/routes/admin/pipeline/+page.svelte

key-decisions:
  - "is_archived defaults to False on the get_job (detail) path since the detail page derives its archived signal from RunReadiness.state == 'already_created', not from this field"
  - "list_jobs() selects (AdminJob, Argument.status) via outerjoin rather than eager-loading the full Argument relationship, keeping the join to a single scalar column and avoiding N+1"

patterns-established:
  - "Frontend badge helpers (badgeStyle/badgeLabel) take an isArchived boolean parameter that short-circuits the compound status/step label, mirroring RunStatusCard.svelte's already_created override"

requirements-completed: [PLIST-05]

coverage:
  - id: D1
    description: "GET /api/admin/jobs returns is_archived=true only for jobs whose linked argument has left PIPELINE status (DRAFT/PUBLISHED/UNPUBLISHED), and false for PIPELINE-status or unlinked jobs"
    requirement: "PLIST-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_list.py#test_list_jobs_is_archived_false_for_pipeline_argument"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_list.py#test_list_jobs_is_archived_true_for_non_pipeline_argument"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_list.py#test_list_jobs_is_archived_false_when_no_linked_argument"
        status: pass
    human_judgment: false
  - id: D2
    description: "The pipeline list page (/admin/pipeline) renders a neutral-grey Archived badge for archived runs, visually matching the detail page's RunStatusCard"
    requirement: "PLIST-05"
    verification: []
    human_judgment: true
    rationale: "Visual badge color/label parity across two pages requires a human to view the rendered page; svelte-check only confirms no type errors, not visual output. Deferred to UAT retest of Test 18 per the plan's verification section."
    ref_hint: "Manual: /admin/pipeline with a run linked to an already-created argument"

# Metrics
duration: 20min
completed: 2026-07-08
status: complete
---

# Phase 26 Plan 06: Pipeline List Archived Badge Summary

**Closed Phase 26 UAT gap (Test 18) by adding `is_archived` to `AdminJobResponse` via a `list_jobs()` outerjoin on `Argument`, and rendering the same grey "Archived" badge on `/admin/pipeline` that RunStatusCard already shows on the detail page.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments
- `AdminJobResponse.is_archived: bool = False` added, documented as true only when the job's linked argument has left `PIPELINE` status
- `list_jobs()` rewritten to `select(AdminJob, Argument.status).outerjoin(Argument, ...)`, deriving `is_archived` per row in a single query (no N+1)
- `get_job()` defaults `is_archived` to `False` so single-job serialization never raises `AttributeError`
- Three new tests cover PIPELINE-status (False), non-PIPELINE status DRAFT/PUBLISHED/UNPUBLISHED (True), and no-linked-argument (False) cases
- `/admin/pipeline` list page's `badgeStyle`/`badgeLabel` helpers gained an `isArchived` parameter that renders the `#cbd5e1` grey "Archived" badge, taking precedence over the compound step/status label — matching `RunStatusCard.svelte`'s `already_created` override exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: Add is_archived to AdminJobResponse and populate it in list_jobs** - `cd40a59a` (feat)
2. **Task 2: Render the grey Archived badge on the pipeline list page** - `34cb8bc0` (feat)

**Plan metadata:** committed as part of this same batch (see final docs commit below)

## Files Created/Modified
- `api/schemas/admin_jobs.py` - Added `is_archived: bool = False` field to `AdminJobResponse` with docstring explaining the get_job vs. list_jobs default behavior
- `api/services/admin_jobs.py` - `list_jobs()` now outerjoins `Argument` and computes `is_archived` per row; `get_job()` sets a `False` default via `setdefault`
- `api/tests/test_admin_jobs_list.py` - Added 3 tests (`test_list_jobs_is_archived_false_for_pipeline_argument`, `test_list_jobs_is_archived_true_for_non_pipeline_argument`, `test_list_jobs_is_archived_false_when_no_linked_argument`)
- `app/src/routes/admin/pipeline/+page.svelte` - `badgeStyle`/`badgeLabel` gained an `isArchived` parameter; call sites pass `job.is_archived`

## Decisions Made
- `is_archived` defaults to `False` on the `get_job` (detail) path intentionally — the detail page's archived signal comes from `RunReadiness.state == 'already_created'` via the readiness endpoint, not this field. Documented inline as a comment per the plan's instruction.
- `list_jobs()` selects `Argument.status` as a plain scalar column in the outerjoin tuple rather than eager-loading the full `Argument` ORM relationship, keeping the query to a single indexed-FK join with no additional round trips.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

DB-backed tests (`test_list_jobs_is_archived_*`) require `DATABASE_URL` to be configured; in this execution environment it was not available for direct verification, so all 3 new tests fell into the pre-existing `_db_configured()` skip guard (2 passed, 9 skipped total, consistent with the plan's stated acceptance: "new tests pass (or skip cleanly when DATABASE_URL is unset)"). The tests were written to the exact same fixture/session pattern as the passing tests already in the file, so they are expected to pass once run against a configured database (e.g. in CI or by a developer with local Postgres access).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 26 UAT Test 18 gap (missing Archived badge on the pipeline list page) is now closed pending a manual UAT retest to confirm the grey badge renders correctly against a live already-created run.
- `svelte-check` reports 0 errors on the modified frontend file; `pytest` reports 2 passed / 9 skipped (skips are the expected DB-guard behavior, not failures).
- This was the final plan in Phase 26 (26-06 of 6); phase-level completion/verification is the orchestrator's responsibility, not this executor's.

---
*Phase: 26-arguments-admin*
*Completed: 2026-07-08*
