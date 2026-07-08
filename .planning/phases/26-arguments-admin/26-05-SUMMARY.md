---
phase: 26-arguments-admin
plan: 05
subsystem: api
tags: [fastapi, sqlalchemy, svelte, admin, access-control, gap-closure]

# Dependency graph
requires:
  - phase: 26-arguments-admin
    provides: "26-01 delete_argument (status-keyed gate), 26-02 update_participant_side / unified Speakers table, 26-04 argument edit page UI"
provides:
  - "DRAFT-only server-side delete gate for delete_argument (closes T-26-13 broken-access-control gap)"
  - "Authoritative backend rejection of UNKNOWN/legacy ADVOCATE advocate sides in update_participant_side"
  - "Explicit 'Unresolved — choose a role' state and Save-disable on the argument edit page's advocate rows"
affects: [26-arguments-admin verification, any future phase touching admin_arguments.py delete/participant-side logic]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Delete/status gates use a single positive == DRAFT condition rather than enumerating disallowed statuses, so newly-added statuses fail closed by default"
    - "Unresolved enum sentinel values (UNKNOWN, legacy ADVOCATE) are rejected in a pre-SELECT guard block alongside existing guards (BENCH), keeping guard tests DB-less and always-run"
    - "Client-side unresolved-state sentinel ('UNKNOWN') seeded once into per-row $state from server data, refreshed via the existing redirect(303)-after-save reload pattern"

key-files:
  created: []
  modified:
    - api/services/admin_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "delete_argument gate rewritten to a single positive condition (status != DRAFT -> False) instead of enumerating PUBLISHED/UNPUBLISHED, so PIPELINE is now blocked too (T-26-13)"
  - "update_participant_side gained a second pre-SELECT guard (alongside the existing BENCH guard) rejecting SideEnum.UNKNOWN and legacy SideEnum.ADVOCATE"
  - "speakerSideById $state seeded once from data.argument.speakers, collapsing non-standard sides to a 'UNKNOWN' sentinel; relies on the page's existing redirect(303)-after-save flow to refresh the seed rather than a $derived/$effect sync"

requirements-completed: [AEDIT-06, AEDIT-09]

coverage:
  - id: D1
    description: "delete_argument rejects PIPELINE-status arguments server-side (DRAFT-only gate), matching the router's 409 and the client's can_delete gate"
    requirement: "AEDIT-09"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_gate_keys_on_draft"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_returns_false_for_pipeline"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py::test_delete_argument_returns_409_for_pipeline"
        status: pass
    human_judgment: false
  - id: D2
    description: "update_participant_side authoritatively rejects an UNKNOWN or legacy ADVOCATE side (ValueError -> router 422), and the edit-page advocate row shows an explicit 'Unresolved — choose a role' placeholder with Save disabled until a real role is chosen"
    requirement: "AEDIT-06"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_update_participant_side_rejects_unresolved_side"
        status: pass
      - kind: other
        ref: "cd app && npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "The visual 'Unresolved — choose a role' placeholder and Save-disable behavior on the edit page require a human to open an argument with an unresolved advocate and confirm the UI renders and blocks Save as intended — svelte-check only proves the code compiles, not that the rendered UX matches the intent."

duration: ~15min
completed: 2026-07-08
status: complete
---

# Phase 26 Plan 05: Gap-Closure — DRAFT-only Delete Gate + Unresolved Advocate Side Guard Summary

**Tightened delete_argument to a single positive DRAFT-only status gate and added an authoritative backend + explicit UI guard preventing an unresolved advocate's side from being silently persisted.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-08T12:03:56Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `delete_argument`'s status gate is now a single positive condition (`status != DRAFT` → `False`), closing the broken-access-control gap where a direct API call could delete a mid-pipeline (`PIPELINE`-status) argument and strand an active `AdminJob` — server-side enforcement now matches the router's "DRAFT only" docstring claim and the client's `can_delete` gate (T-26-13, D-03/AEDIT-09).
- `update_participant_side` gained a second pre-SELECT guard, alongside the existing BENCH guard, that raises `ValueError` for `SideEnum.UNKNOWN` and legacy `SideEnum.ADVOCATE` — the router maps this to a 422, making the backend the authoritative source of truth for advocate-side writes (T-26-14, AEDIT-06, CLAUDE.md no-silent-inference constraint).
- The argument edit page's advocate `<select name="side">` now has a leading "Unresolved — choose a role" option and is driven by a per-row `speakerSideById` `$state`; the Save button (and its cursor/opacity styling) disables while a row's side is unresolved, so an accidental submit can no longer silently reclassify an advocate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Enforce DRAFT-only delete gate in delete_argument + regression tests** - `d957f810` (fix)
2. **Task 2: Authoritative backend guard rejecting UNKNOWN/ADVOCATE advocate sides + regression test** - `44a09c48` (fix)
3. **Task 3: Make the unresolved advocate side explicit and block accidental Save (edit page)** - `d322d297` (fix)

## Files Created/Modified

- `api/services/admin_arguments.py` - `delete_argument` gate rewritten to `status != ArgumentStatusEnum.DRAFT`; `update_participant_side` gained a pre-SELECT `UNKNOWN`/`ADVOCATE` guard alongside the existing BENCH guard; both docstrings updated
- `api/tests/test_admin_arguments_service.py` - added `test_delete_argument_gate_keys_on_draft` (structural, always-runs), `test_delete_argument_returns_false_for_pipeline` (DB-guarded), `test_update_participant_side_rejects_unresolved_side` (always-runs)
- `api/tests/test_admin_arguments_routes.py` - added `test_delete_argument_returns_409_for_pipeline` (DB-guarded)
- `app/src/routes/admin/arguments/[id]/+page.svelte` - added `speakerSideById` `$state<Record<number, string>>`; advocate `<select>` gained a leading `UNKNOWN` placeholder option and `bind:value`; Save button `disabled`/`cursor`/`opacity` now also key on the unresolved sentinel

## Decisions Made

- `delete_argument` gate rewritten to a single positive `status == DRAFT` condition rather than continuing to enumerate disallowed statuses — this makes any future new `ArgumentStatusEnum` member fail closed (blocked) by default instead of requiring an explicit addition to a blocklist.
- The new `update_participant_side` guard sits before the DB `SELECT`, mirroring the existing BENCH guard's placement, so `test_update_participant_side_rejects_unresolved_side` can run as an always-on, DB-less regression test with a sentinel `None` session.
- `speakerSideById` is seeded once from `data.argument.speakers` rather than kept in sync via a `$derived`/`$effect` — this matches the existing pattern in the file (the page already reloads via `redirect(303)` after every successful save, which naturally refreshes the seed) and avoids introducing a new reactivity pattern for a single control.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The first `Edit` attempt on the advocate `<select>` block failed with a "String to replace not found" error because the file's indentation uses tabs, and the initially-typed `old_string` used spaces. Resolved by extracting the exact tab-indented block via `sed -n ... | cat -A` and applying the replacement with a small Python script for byte-exact matching; the subsequent Save-button `Edit` succeeded normally against the same file. No impact on the final diff, which matches the plan's specified changes exactly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both confirmed Phase 26 verification gaps are closed:
- Gap 1 (broken access control on delete): `delete_argument` now blocks every non-DRAFT status server-side, with structural + DB-guarded regression coverage.
- Gap 2 (silent advocate misattribution risk): the backend authoritatively rejects UNKNOWN/ADVOCATE sides, and the edit-page UI makes the unresolved state explicit with Save blocked until a real role is chosen.

`api/tests/test_admin_arguments_service.py` and `api/tests/test_admin_arguments_routes.py` collect cleanly (24 passed, 24 skipped — DB-guarded tests skip without `DATABASE_URL`, matching the project's documented test pattern). `cd app && npm run check` reports 0 errors.

Remaining before Phase 26 is fully closed: the orchestrator must re-run phase-level verification (`verify_phase_goal`) and, only after it passes, record the phase-level ROADMAP.md completion marker via `gsd_run query phase.complete` — per this plan's `<critical_constraint>`, this executor did not touch that phase-level marker.

---
*Phase: 26-arguments-admin*
*Completed: 2026-07-08*

## Self-Check: PASSED

All files created/modified verified present; all three task commit hashes (d957f810, 44a09c48, d322d297) verified present in git log.
