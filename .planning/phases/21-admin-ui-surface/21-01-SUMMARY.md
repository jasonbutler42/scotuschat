---
phase: 21-admin-ui-surface
plan: 01
subsystem: api, ui
tags: [fastapi, svelte5, sqlalchemy, delete, cascade, admin]

# Dependency graph
requires:
  - phase: 15-admin-ui-surface (argument status enum)
    provides: ArgumentStatusEnum.PUBLISHED used as the published guard
  - phase: 11-admin-ui-surface (argument edit page)
    provides: +page.server.ts and +page.svelte target files
provides:
  - delete_argument service function with FK-ordered cascade
  - DELETE /api/admin/arguments/{id} FastAPI endpoint
  - Two-step inline confirm delete UI on argument edit page
  - can_delete server-side gate in load function
affects:
  - 21-02-PLAN (job delete — same pattern for admin jobs)
  - 21-03-PLAN (AdminSubNav — layout changes around same edit page)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-table FK-ordered cascade delete: Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id → Argument"
    - "can_delete flag computed from already-loaded argument.status — no extra API call"
    - "Two-step inline confirm: deleteConfirming + deleteSubmitting $state; $effect resets on soft nav"

key-files:
  created: []
  modified:
    - api/services/admin_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/routers/admin.py
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "delete_argument returns bool | None: True=deleted, False=published (409), None=not found (404)"
  - "FK delete order: Utterance before PipelineRun (Pitfall 2 — utterances.pipeline_run_id FK); AdminJob NULLed before Argument (Pitfall 1 — no ondelete on FK)"
  - "All delete() and update() in delete_argument use .execution_options(synchronize_session=False) (Pitfall 3)"
  - "can_delete = argument.status !== 'published' — no extra API call; derived from already-loaded ArgumentDetail"
  - "DELETE endpoint placed after all literal-path /arguments/* routes to avoid shadowing check-duplicate"

patterns-established:
  - "Pattern: Multi-table cascade delete follows people delete pattern with manual FK sequence"
  - "Pattern: Two-step confirm — deleteConfirming gates the form submit, deleteSubmitting tracks in-flight state"

requirements-completed: [ADMIN-01]

coverage:
  - id: D1
    description: "delete_argument service function: FK-ordered cascade, returns True/False/None"
    requirement: ADMIN-01
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_importable"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_utterances_before_pipeline_runs"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_admin_job_nulled_before_argument_deleted"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_all_deletes_have_synchronize_session_false"
        status: pass
    human_judgment: false
  - id: D2
    description: "DELETE /api/admin/arguments/{id} endpoint: 200 deleted, 404 not found, 409 published"
    requirement: ADMIN-01
    verification:
      - kind: unit
        ref: "python -m pytest api/tests/ -x -q -k argument --ignore=api/tests/test_arguments.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Argument edit page: two-step Danger Zone delete, can_delete gate, blocked state tooltip"
    requirement: ADMIN-01
    verification:
      - kind: unit
        ref: "app svelte-check --threshold error: 0 errors"
        status: pass
    human_judgment: true
    rationale: "UI interaction state (deleteConfirming toggle, redirect, disabled tooltip) requires visual verification in a running browser"

duration: ~25min
completed: 2026-07-01
status: complete
---

# Phase 21 Plan 01: Argument Delete (ADMIN-01) Summary

**Multi-table FK-ordered cascade delete for unpublished arguments via two-step inline confirm, with server-side published guard and AdminJob FK NULLing**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-01T19:00:00Z
- **Completed:** 2026-07-01T19:19:48Z
- **Tasks:** 3 (TDD: RED commit + GREEN commit for Task 1)
- **Files modified:** 5

## Accomplishments

- `delete_argument(db, argument_id) -> bool | None` added to admin_arguments.py with exact FK delete order (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id → Argument)
- `DELETE /api/admin/arguments/{id}` endpoint added, mirroring people delete pattern: 200 + `{"deleted": True}`, 404 not found, 409 published
- Argument edit page adds Danger Zone card with two-step inline confirm (`deleteConfirming` / `deleteSubmitting` Svelte 5 `$state`), `can_delete` load flag, and blocked-state tooltip for published arguments
- Four structural test cases verify FK order, synchronize_session guards, and import correctness without requiring a live DB

## Task Commits

1. **Task 1 RED: Failing tests for delete_argument** - `3e9aa975` (test)
2. **Task 1 GREEN: delete_argument service implementation** - `f1a7b7c7` (feat)
3. **Task 2: DELETE /arguments/{id} endpoint** - `1ca94a96` (feat)
4. **Task 3: Danger Zone UI + can_delete + delete action** - `6169da46` (feat)

## Files Created/Modified

- `api/services/admin_arguments.py` — Added `delete_argument` function; added `delete`, `AdminJob`, `PipelineRun`, `Utterance` imports
- `api/tests/test_admin_arguments_service.py` — Added 5 test cases (4 structural + 1 DB-guarded None check); updated imports list
- `api/routers/admin.py` — Added `DELETE /arguments/{argument_id}` handler after existing argument routes
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — Added `can_delete` to load return; added `delete` form action
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Added `deleteConfirming`/`deleteSubmitting` `$state`, `$effect` for soft-nav reset, Danger Zone card with two-step confirm and blocked state

## Decisions Made

- `delete_argument` returns `bool | None` (True/False/None) matching the `delete_person_if_orphan` convention — routed to 200/409/404 at the router layer
- FK order is: Utterance → PipelineRun (Pitfall 2: utterances.pipeline_run_id); ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id (Pitfall 1: no ondelete clause) → Argument
- `can_delete` derived from `argument.status !== 'published'` with no extra API call (Pitfall 4 avoidance)
- `$effect` referencing `data.argument.id` resets confirm state on SvelteKit soft navigation between arguments (Pitfall 7)
- DELETE endpoint placed after all literal-path argument routes to avoid shadowing `check-duplicate` GET route

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `test_arguments.py::test_get_utterances_returns_404_for_unknown_argument` fails with `RuntimeError: Database session factory is not initialised` — confirmed pre-existing failure unrelated to this plan's changes (reproduced on clean stash before any edits).

## Threat Surface Scan

No new threat surface beyond what is in the plan's threat model. All five STRIDE threats (T-21-01-IDOR, T-21-01-PUB, T-21-01-FK, T-21-01-CSRF, T-21-01-AUTH) are mitigated as designed:
- IDOR: `argument_id` typed `int`; service returns None → 404
- Published guard: service-level `status == PUBLISHED` check → False → 409
- FK order: cascade verified by structural tests
- CSRF: SvelteKit ORIGIN CSRF active; form action POST only
- Auth: router-level `verify_admin_token` inherited

## Known Stubs

None — all data is live from the database.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 (job delete) can proceed immediately — same endpoint/service/UI pattern
- Plan 03 (AdminSubNav) is independent and can proceed in parallel
- `delete_argument` service is the canonical cascade delete pattern for this codebase

---
*Phase: 21-admin-ui-surface*
*Completed: 2026-07-01*
