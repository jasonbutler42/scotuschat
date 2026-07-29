---
phase: 36-click-to-copy-extracted-values-design-pattern
verified: 2026-07-15T17:23:08Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/9
  gaps_closed:
    - "Repeated copy activation restarts one full 1500ms success interval for the newest attempt"
    - "Local feedback always describes the value currently displayed by the reused component instance"
    - "Clipboard rejection shows local fixed failure feedback and a later successful retry clears it"
  gaps_remaining: []
  regressions: []
---

# Phase 36 Verification Report

**Status:** passed
**Re-verification:** Yes — after Plan 36-03 gap closure

## Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Eligible pipeline extracted displays use the shared affordance. | VERIFIED | Pipeline case name, formatted date, docket, question number, and editable resolve title hints use `CopyableExtractedValue`. |
| 2 | Eligible argument-editor displays, including individual dockets, use the identical affordance. | VERIFIED | Shared argument details and speaker title hints use the component; prior UAT confirmed individual docket copying. |
| 3 | N/A values remain visible and disabled. | VERIFIED | Native disabled button, approved tooltip, no tab focus, and no misleading copy icon. |
| 4 | One reusable component owns clipboard and feedback behavior. | VERIFIED | All consumers import it; the only production clipboard call is inside it. |
| 5 | The exact displayed value is copied. | VERIFIED | Rendered and copied payload are the same prop; callers provide final formatting. |
| 6 | Tooltip, keyboard, focus, wrapping, and exclusions work. | VERIFIED | Centralized native semantics plus completed operator UAT. |
| 7 | Newest activation owns a full 1500ms interval. | VERIFIED | Generation checks guard every completion and timer; focused browser regression passed. |
| 8 | Payload changes and destruction invalidate stale work. | VERIFIED | Payload-keyed effect resets state and cleanup; browser regression covers pending, success, error, late settlement, and destruction. |
| 9 | Clipboard rejection is fixed-copy, local, and recoverable. | VERIFIED | Browser regression proves no raw error disclosure and successful retry replaces failure with `Copied`. |

**Score:** 9/9 truths verified.

## Behavioral Evidence

- `node --test tests/copyable-extracted-value.browser.test.mjs`: **1/1 passed**
- `npm run check`: passed with zero errors and existing warnings
- `npm run build`: passed
- Previous operator UAT remains valid
- Previous full regression: 492 passed, 5 expected xfails

The optional unrelated `case-required-recovery.browser.test.mjs` check crashed in the current Node runtime before test execution. This is not a Phase 36 product regression and was not used as evidence.

## Requirements Coverage

UX-01 is satisfied. All approved surfaces share the reusable component, N/A remains disabled, and every formerly unverified asynchronous lifecycle behavior now has passing real-browser coverage.

## Human Verification Required

None. Prior UAT covers the interaction and visual contract; the focused browser regression covers all previously unproven state transitions.

## Gaps Summary

Both prior gaps are closed with no regressions. Phase 38 presentation changes remain intentionally outside this phase.

_Verifier: generic-agent workaround using the gsd-verifier role preamble_