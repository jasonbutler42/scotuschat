---
phase: 38-full-name-vs-name-parts-rethink
plan: 10
subsystem: testing
tags: [pytest, docket, validation, uat, regression-gate]

requires:
  - phase: 38-full-name-vs-name-parts-rethink
    provides: "api/domain/docket_values.py canonical rule (Plan 38-07), pipeline/commands/ingest.py path-safety guard (Plan 38-08), app/src/lib/docketValues.ts + DocketPillInput enforceShape + SvelteKit server re-check (Plan 38-09)"
provides:
  - "Consolidated regression-gate evidence (119 passed, 0 failures) across every suite touching create_job, _normalize_dockets, and ingest"
  - "On-disk data/pdfs corpus verification (58 existing filenames, 0 violations of the shared docket rule)"
  - "Operator sign-off on the original UAT Test 6 reproduction plus traversal and absolute-path variants against the live Pipeline Runner"
  - "38-UAT.md Test 6 flipped to pass and gap G-38-6 marked resolved"
affects: []

tech-stack:
  added: []
  patterns:
    - "Gap closure proven against the original human-reported reproduction on the live UI, not only unit tests, before flipping UAT status"

key-files:
  created: []
  modified:
    - .planning/phases/38-full-name-vs-name-parts-rethink/38-UAT.md

key-decisions:
  - "G-38-6 closed only after both the automated regression gate (Task 1) and explicit operator re-verification of all 6 checkpoint steps (Task 2) — matching the plan's stated purpose that a UI-found gap is closed by a human at the UI, not by tests alone"
  - "38-UAT.md's pre-existing test_phase38_people_ui_contract.py node-driver failure (Windows-path-in-JS-string issue, unrelated to this gap) was left undisturbed and not chased, per the plan's explicit scope note"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "Consolidated regression gate over every suite that exercises create_job, _normalize_dockets, or ingest, run together with a check that every already-ingested data/pdfs filename still satisfies the shared docket rule"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_values.py, test_docket_arg_safety.py, test_docket_ui_contract.py, pipeline/tests/test_ingest.py, test_ingest_startup_guard.py, api/tests/test_admin_jobs_list.py, test_admin_jobs_phase35.py, test_admin_jobs_phase35_frontend.py, test_admin_dashboard_routes.py (119 passed, 0 failures)"
        status: pass
      - kind: other
        ref: "On-disk listing of data/pdfs (58 files) checked against the shared docket rule"
        status: pass
    human_judgment: false
  - id: D2
    description: "Operator re-runs the exact UAT Test 6 reproduction (the reported double-quoted string), plus traversal (../../../tmp/evil) and Windows drive-path variants, on the running Pipeline Runner, confirms a real docket still starts a run, the metadata editor is unaffected, and non-docket failures keep the generic error message"
    requirement: "PEOPLE-09"
    verification:
      - kind: manual_procedural
        ref: "Operator checkpoint — all 6 steps of the plan's <how-to-verify> block"
        status: pass
    human_judgment: true
    rationale: "G-38-6 was originally found by a human at the Pipeline Runner UI; closing it requires the same human re-running the same reproduction against the live stack, which cannot be automated the same way pytest suites are."

duration: ~15min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 10: G-38-6 Regression Gate + Operator Sign-Off Summary

**Consolidated 119-test regression gate across all docket-guard-touching suites plus operator re-verification of the original UAT Test 6 reproduction (and traversal/absolute-path variants) on the live Pipeline Runner, closing UAT gap G-38-6.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-27T20:45:00Z
- **Completed:** 2026-07-27T21:00:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Ran the consolidated regression gate specified in Task 1 across all nine listed suites (`api/tests/test_docket_values.py`, `test_docket_arg_safety.py`, `test_docket_ui_contract.py`, `pipeline/tests/test_ingest.py`, `test_ingest_startup_guard.py`, `api/tests/test_admin_jobs_list.py`, `test_admin_jobs_phase35.py`, `test_admin_jobs_phase35_frontend.py`, `test_admin_dashboard_routes.py`): **119 passed, 0 failures**. No source changes were required — every suite passed cleanly on the first run.
- Verified the on-disk `data/pdfs` corpus is unaffected by the new docket guards: listed all 58 existing PDF filenames and confirmed every filename's docket component satisfies the shared `api/domain/docket_values.py` rule — 0 violations, no previously-ingested PDF became unreachable, no re-ingest needed.
- The known pre-existing, unrelated `test_phase38_people_ui_contract.py` node-driver failure (Windows-path-interpolated-into-JS-string issue) was neither encountered as a regression nor chased — it is outside this gap's suite list and outside this gap's scope per the plan.
- Operator re-ran the exact UAT Test 6 reproduction (the reported double-quoted string) against the running Pipeline Runner and confirmed: no pill created, an inline red error appears below the input, the typed text is preserved for editing, no job starts, and no `[Errno 22] Invalid argument` occurs anywhere.
- Operator confirmed the traversal case (`../../../tmp/evil`) and a Windows drive-path value are both rejected inline the same way, with nothing written outside `data/pdfs` and no new file anywhere under `/tmp`.
- Operator confirmed the happy path is unaffected: a real docket (`22-915`) still creates a pill, starts a run, and produces the expected `data/pdfs` filename.
- Operator confirmed `ArgumentDetailsCard`'s metadata editor is untouched — existing argument docket pills render and save exactly as before, including historical/unusual stored values.
- Operator confirmed the server-side layer: a non-docket run failure (e.g. a bad PDF URL) still shows the familiar generic "could not start the run" message rather than docket-specific wording.
- Operator gave full sign-off on all six checkpoint steps with the response "Approved."
- Updated `38-UAT.md`: Test 6's `result` flipped from `issue` to `pass` with a `resolution` field documenting the closure evidence; the overall file `status` flipped from `diagnosed` to `complete`; the `## Summary` counts updated to `passed: 6, issues: 0`; gap `G-38-6` in `## Gaps` marked `status: resolved` with `resolved_by`/`resolved_date` fields, preserving the original `reason`/`root_cause`/`artifacts`/`missing`/`debug_session` fields as the audit trail of what was found and fixed.

## Task Commits

Task 1 made no source changes (files_modified: [] per plan frontmatter) and required no commit of its own — its regression-gate results are recorded here and folded into this plan's single documentation commit alongside Task 2's UAT update.

1. **Task 1: Consolidated G-38-6 regression gate** - no commit (verification only, 0 files changed)
2. **Task 2: Operator re-runs the UAT Test 6 reproduction on the Pipeline Runner** - checkpoint approved by operator ("Approved"); result recorded in `38-UAT.md`

**Plan metadata:** see final `docs(38-10): complete ...` commit below.

## Files Created/Modified

- `.planning/phases/38-full-name-vs-name-parts-rethink/38-UAT.md` - Test 6 flipped to `pass` with resolution evidence; file `status` flipped to `complete`; `## Summary` counts updated; gap `G-38-6` marked `resolved`

## Decisions Made

- G-38-6 is closed only on the combination of the automated regression gate (Task 1) and explicit operator re-verification of all 6 checkpoint steps (Task 2) on the live Pipeline Runner — consistent with the plan's premise that a gap found by a human at the UI is closed by a human at the UI, not by unit tests alone.
- The pre-existing, unrelated `test_phase38_people_ui_contract.py` node-driver failure was left undisturbed and only noted, per the plan's explicit instruction not to chase it here.

## Deviations from Plan

None - plan executed exactly as written. No auto-fixes were needed; every listed suite passed on the first run and the operator confirmed every checkpoint step without deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three layers of the G-38-6 fix (Plans 38-07, 38-08, 38-09) are now proven end-to-end and operator-signed-off; the gap is closed.
- This was the final plan (10 of 10) in Phase 38 (full-name-vs-name-parts-rethink). Phase 38 is ready for phase-level verification/close-out.
- No blockers.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

`.planning/phases/38-full-name-vs-name-parts-rethink/38-UAT.md` found on disk with the expected edits (status: complete, Test 6 result: pass, Summary passed: 6/issues: 0, gap G-38-6 status: resolved). No commit hashes to verify for Task 1 (no source changes); Task 2 is an operator checkpoint approval, not a code commit.
