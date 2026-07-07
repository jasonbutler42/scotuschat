---
status: testing
phase: 25-pipeline-job-detail-page
source: [25-VERIFICATION.md]
started: 2026-07-07T19:25:00Z
updated: 2026-07-07T19:25:00Z
---

## Current Test

number: 1
name: Create new person via Resolve card popover, then blur Title on same row (CR-01 regression check)
expected: |
  Create a new person via the Resolve card's "Create new person" popover on an intervention row
  (choosing Bench or Advocate), then blur the Title input on that same row immediately after.
  The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the
  popover. This exercises code-review fix dc8ad284 (CR-01), which threaded `side` through
  `handlePersonCreated`/`pendingSideOverrides` and calls `submitRow()` immediately.
awaiting: user response

## Tests

### 1. Create new person via Resolve card popover, then blur Title on same row (CR-01 regression check)
expected: The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises dc8ad284 / CR-01 fix.)
result: [pending]

### 2. Continue Resolve with zero discrepancies (WR-04 regression check)
expected: Pause a job whose discrepancies array is empty (or becomes empty after all rows are resolved via inline saveResolveRow edits). "Continue Resolve" is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises 8492f515 / WR-04 fix.)
result: [pending]

### 3. Full five-state lifecycle walkthrough
expected: Walk a single run through all five lifecycle states end-to-end: not-ready → ready → Create Argument → already-created (read-only), plus a failed run and a paused/resolve run. RunStatusCard shows correct badge/copy/CTA in each state; ArgumentDetailsCard and ResolveCard become read-only exactly once the argument leaves "pipeline" status; FailedStepGuidance shows step-specific copy for Ingest/Parse/Resolve failures; resolve-row side-first gate, per-row saveResolveRow persistence, and Missing-tenure/Edit-person link all behave as coded. Also confirms bench-role recalculation after saving Argument Details (roadmap SC #5) is visible in the resolve card.
result: [pending]

### 4. Mobile/responsive check on Resolve card and CreatePersonPopover
expected: On a narrow/mobile viewport, the horizontally-scrollable table wrapper avoids row text overlap; the popover stays within calc(100vw - 32px) and traps/returns focus correctly on open/close.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
