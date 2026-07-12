---
phase: 26-arguments-admin
plan: 01
subsystem: api
tags: [sqlalchemy, fastapi, admin, lifecycle, audit-log]

# Dependency graph
requires:
  - phase: 22-schema-foundations
    provides: ArgumentStatusEnum.UNPUBLISHED value and the argument_status_log table (empty until this plan)
provides:
  - Backend source of truth for the three-state Argument lifecycle (DRAFT / PUBLISHED / UNPUBLISHED)
  - ArgumentStatusLog audit trail populated on every publish/unpublish/approve transition
  - Admin arguments list surfaces all three post-pipeline states
  - Delete gate and slug-freeze keyed on status instead of published_at
affects: [26-02, 26-03, 26-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Status transitions write Argument.status update and an ArgumentStatusLog row in the same transaction, inline (no shared helper) to avoid an admin_jobs -> admin_arguments import cycle"
    - "Guards on publish/unpublish/delete/slug-freeze key on Argument.status, never on published_at"

key-files:
  created: []
  modified:
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/routers/admin.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
    - api/tests/test_admin_jobs_service.py

key-decisions:
  - "Re-publish from UNPUBLISHED is allowed; publish_argument's guard now checks status == PUBLISHED instead of published_at is not None (D-02, AEDIT-08)"
  - "unpublish_argument no longer nulls published_at — it is preserved so the Status card can show the last-published date (D-02)"
  - "ArgumentStatusLog writes are inlined at each of the three call sites (publish, unpublish, approve_job) rather than factored into a shared helper, to avoid admin_jobs.py importing admin_arguments.py (D-10)"
  - "Slug-freeze and delete-gate both switched from published_at-based checks to status-based checks (ALIST-01, D-03/AEDIT-09)"

patterns-established:
  - "Argument.status is the single lifecycle source of truth for admin service guards; published_at is now purely a display timestamp, never a gate condition"

requirements-completed: [ALIST-02, AEDIT-02, AEDIT-08, AEDIT-09]

coverage:
  - id: D1
    description: "publish_argument sets status=PUBLISHED, stamps published_at, and writes one PUBLISHED ArgumentStatusLog row; re-publish from UNPUBLISHED succeeds"
    requirement: "AEDIT-08"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_publish_argument_from_draft_writes_one_published_log_row"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_unpublish_then_republish_succeeds_and_preserves_published_at"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_publish_argument_already_published_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "unpublish_argument sets status=UNPUBLISHED, leaves published_at intact, writes one UNPUBLISHED log row"
    requirement: "AEDIT-08"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_unpublish_then_republish_succeeds_and_preserves_published_at"
        status: pass
    human_judgment: false
  - id: D3
    description: "approve_job writes a DRAFT ('Created') ArgumentStatusLog row alongside its existing status=DRAFT update"
    requirement: "AEDIT-02"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_service.py#test_approve_job_writes_one_draft_log_row"
        status: pass
    human_judgment: false
  - id: D4
    description: "list_arguments includes DRAFT, PUBLISHED, and UNPUBLISHED rows; excludes only PIPELINE"
    requirement: "ALIST-02"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_list_arguments_includes_unpublished_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "delete_argument returns False for PUBLISHED/UNPUBLISHED, True for DRAFT; DELETE route returns 409 with updated copy for UNPUBLISHED"
    requirement: "AEDIT-09"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_delete_argument_returns_false_for_unpublished"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py#test_delete_argument_returns_409_for_unpublished"
        status: pass
    human_judgment: false
  - id: D6
    description: "update_argument freezes the slug (re-derives only while DRAFT) for both PUBLISHED and UNPUBLISHED arguments"
    requirement: "AEDIT-02"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_update_argument_slug_frozen_for_unpublished"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-07
status: complete
---

# Phase 26 Plan 01: Argument lifecycle rewrite Summary

**Rewrote publish/unpublish/delete/slug-freeze/list guards to key on Argument.status (not published_at), and started writing the ArgumentStatusLog audit trail on every transition.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 6 (3 source, 3 test)

## Accomplishments
- `publish_argument` / `unpublish_argument` now key their guards on `Argument.status` instead of `published_at`, so re-publish from UNPUBLISHED succeeds and unpublish no longer clobbers `published_at`
- Every publish, unpublish, and approve_job transition writes exactly one matching `ArgumentStatusLog` row in the same transaction as the status update — the audit trail (empty since Phase 22) is now populated going forward
- `list_arguments` surfaces DRAFT, PUBLISHED, and UNPUBLISHED rows; only PIPELINE-status arguments remain hidden from the admin list
- `delete_argument` and the slug-freeze logic in `update_argument` both switched from `published_at`-based checks to `status`-based checks, closing the gap where an UNPUBLISHED argument could previously be deleted or have its slug re-derived
- DELETE route 409 copy updated to reflect the three-state model ("Published and unpublished arguments cannot be deleted. Only drafts can be removed.")

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite publish/unpublish for three-state status + status-log writes; add "Created" log write to approve_job** - `176379e4` (feat)
2. **Task 2: Fix list filter, slug-freeze, and delete gate to key on status; update delete-route 409 copy** - `a86d5b78` (fix)

**Plan metadata:** committed alongside STATE.md/ROADMAP.md updates (see final commit below)

## Files Created/Modified
- `api/services/admin_arguments.py` - publish_argument/unpublish_argument status-keyed guards + ArgumentStatusLog writes; list_arguments UNPUBLISHED inclusion; update_argument slug-freeze on status==DRAFT; delete_argument gate on status in (PUBLISHED, UNPUBLISHED)
- `api/services/admin_jobs.py` - approve_job writes a DRAFT ArgumentStatusLog row ("Created" transition)
- `api/routers/admin.py` - DELETE /arguments/{id} 409 detail copy updated to match UI-SPEC
- `api/tests/test_admin_arguments_service.py` - re-publish, unpublish-preserves-published_at, one-log-row-per-transition, delete-returns-false-for-unpublished, list-includes-unpublished, slug-frozen-for-unpublished tests
- `api/tests/test_admin_arguments_routes.py` - DELETE route 409-for-unpublished test with updated copy assertion
- `api/tests/test_admin_jobs_service.py` - approve_job writes one DRAFT log row test

## Decisions Made
- Re-publish from UNPUBLISHED is allowed by design (D-02/AEDIT-08); only an already-PUBLISHED argument raises "Already published"
- `published_at` is preserved on unpublish (not nulled) so the Status card can display the argument's last-published date
- ArgumentStatusLog writes are inlined at each of the three sites (no shared helper) to avoid `admin_jobs.py` importing `admin_arguments.py` (D-10)

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (guard wording, `db.add(ArgumentStatusLog(...))` sites, grep checks for removed `published_at=None` and `Unpublish first.` strings) verified via grep after implementation.

## Issues Encountered

Running the full `api/tests/` suite together (not the plan's scoped verification command) surfaces 3 pre-existing failures in `test_arguments.py` and `test_people.py` (`RuntimeError: Database session factory is not initialised`) — a test-ordering/lifespan issue unrelated to this plan's files. Logged to `.planning/phases/26-arguments-admin/deferred-items.md` per the SCOPE BOUNDARY rule; not fixed here. The plan's own scoped verification command (`test_admin_arguments_service.py test_admin_arguments_routes.py test_admin_jobs_service.py`) passes cleanly: 24 passed, 20 skipped (DB-guarded tests skip when `DATABASE_URL` is not configured in this environment, matching the project's existing test pattern).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Backend now has a single, consistent source of truth for the argument lifecycle (status-keyed guards + audit log), which the remaining Phase 26 plans (frontend admin UI for the three-state model) can build on directly. No blockers identified.

---
*Phase: 26-arguments-admin*
*Completed: 2026-07-07*

## Self-Check: PASSED

All created/modified files verified present on disk; all task and summary commit hashes (176379e4, a86d5b78, 97aedc85) verified present in git log.
