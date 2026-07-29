---
phase: 34-blank-case-name-docket-validation
plan: 04
subsystem: ui
tags: [sveltekit, constraint-validation, accessibility, edge, cdp, browser-test]

requires:
  - phase: 34-03
    provides: Accessible native and pill-based required-value recovery
provides:
  - Native-only Case required flags reset at the constraint-valid enhanced-submit boundary
  - Dependency-free real-browser regression for invalid-to-corrected failure recovery
affects: [admin-argument-editor, PIPE-28, phase-34-verification]

tech-stack:
  added: []
  patterns: [Node built-in test runner with installed Edge over CDP, client-only validation state reset before enhanced submission]

key-files:
  created: [app/tests/case-required-recovery.browser.test.mjs]
  modified: [app/src/routes/admin/arguments/[id]/+page.svelte, api/tests/test_question_number_nullable.py]

key-decisions:
  - "Clear only native-owned required flags when native validation permits enhanced submission; later structured server-required state remains authoritative."
  - "Exercise the actual authenticated SvelteKit route with an isolated mock API and installed Edge without adding browser-test dependencies."

patterns-established:
  - "Native-to-server validation handoff: clear stale client-only flags synchronously before setting saving state."
  - "Fail-closed browser harness: own dynamic ports, isolated credentials, browser profile, mock API, Vite process, and cleanup."

requirements-completed: [PIPE-28]

coverage:
  - id: D1
    description: "Corrected Case controls clear stale native required feedback before collision or generic failures render."
    requirement: PIPE-28
    verification:
      - kind: automated_ui
        ref: "app/tests/case-required-recovery.browser.test.mjs#native required state clears before later enhanced failures"
        status: pass
    human_judgment: false
  - id: D2
    description: "Current structured backend required responses still control required copy, ARIA state, borders, and focus."
    requirement: PIPE-28
    verification:
      - kind: automated_ui
        ref: "app/tests/case-required-recovery.browser.test.mjs#native required state clears before later enhanced failures"
        status: pass
      - kind: unit
        ref: "api/tests/test_question_number_nullable.py#test_case_form_clears_native_required_state_before_enhanced_save"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-14
status: complete
---

# Phase 34 Plan 04: Required-State Recovery Gap Closure Summary

**Constraint-valid Case resubmissions now discard stale native required state while preserving authoritative server-required, collision, and generic failure handling.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-07-14T18:29:00Z
- **Completed:** 2026-07-14T19:03:49Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Closed CR-01 by clearing both native-only required flags synchronously at the valid enhanced-submit boundary.
- Added a real Edge/CDP regression that drives login, native invalid events, corrected submission, structured required responses, collision responses, and generic responses through the actual SvelteKit route.
- Verified exact ordered copy, request cancellation/execution, ARIA state, red borders, focus behavior, isolated runtime resources, and full-suite compatibility.

## Task Commits

1. **Task 1 RED: Add failing required-state recovery regression** - `5ee71b10` (test)
2. **Task 1 GREEN: Clear stale native required state** - `c4176551` (fix)

## Files Created/Modified

- `app/tests/case-required-recovery.browser.test.mjs` - Dependency-free authenticated browser lifecycle regression using Node, mock HTTP API, Vite, installed Edge, and CDP.
- `app/src/routes/admin/arguments/[id]/+page.svelte` - Clears native-only Case required flags before a valid enhanced request starts.
- `api/tests/test_question_number_nullable.py` - Supplemental source-order contract for the valid-submit reset.

## Decisions Made

- Clear native flags rather than recomputing all required state because the callback is reachable only after native constraints pass; server flags remain derived from the subsequent action result.
- Keep the behavioral browser test authoritative and retain the Python source assertion only as a fast ordering guard.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Raw Edge/CDP setup required an explicit remote-origin allowance and hydration wait; the harness now starts and tears down deterministically.
- The initial focus assertion confused retained browser focus with a repeated required-focus action. The test now places focus on the submitter before each enhanced request, making focus recurrence observable.

## User Setup Required

None - the regression uses installed Microsoft Edge and isolated local test processes with no real credentials, backend, database, or network.

## Verification

- `node --test app/tests/case-required-recovery.browser.test.mjs` — 1 passed
- `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` — 10 passed
- `npm run check` — 0 errors, 16 pre-existing warnings
- `.\.venv\Scripts\python.exe -m pytest -q` — 483 passed, 5 xfailed

## Next Phase Readiness

- CR-01 is closed with executable lifecycle coverage; Phase 34 is ready for re-verification and the remaining explicit browser UAT checks.
- No unresolved high-severity threat remains in the gap-closure scope.

## Self-Check: PASSED

- Created browser regression exists and both RED/GREEN commits are present.
- All plan verification and full regression commands passed.

---
*Phase: 34-blank-case-name-docket-validation*
*Completed: 2026-07-14*
