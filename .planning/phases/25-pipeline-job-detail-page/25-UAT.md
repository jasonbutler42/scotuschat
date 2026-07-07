---
status: partial
phase: 25-pipeline-job-detail-page
source: [25-VERIFICATION.md]
started: 2026-07-07T19:30:58Z
updated: 2026-07-07T19:50:00Z
---

## Current Test

[testing paused — 1 item outstanding]

## Tests

### 1. Create new person via Resolve card popover, then blur Title on same row (CR-01 regression check)
expected: The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises dc8ad284 / CR-01 fix.)
result: issue
reported: "Looks like there's no trigger on the resolve card to create or even switch people"
severity: major

### 2. Continue Resolve with zero discrepancies (WR-04 regression check)
expected: Pause a job whose discrepancies array is empty (or becomes empty after all rows are resolved via inline saveResolveRow edits). "Continue Resolve" is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises 8492f515 / WR-04 fix.)
result: issue
reported: "I don't see anything like this"
severity: major

### 3. Full five-state lifecycle walkthrough
expected: Walk a single run through all five lifecycle states end-to-end: not-ready → ready → Create Argument → already-created (read-only), plus a failed run and a paused/resolve run. RunStatusCard shows correct badge/copy/CTA in each state; ArgumentDetailsCard and ResolveCard become read-only exactly once the argument leaves "pipeline" status; FailedStepGuidance shows step-specific copy for Ingest/Parse/Resolve failures; resolve-row side-first gate, per-row saveResolveRow persistence, and Missing-tenure/Edit-person link all behave as coded. Also confirms bench-role recalculation after saving Argument Details (roadmap SC #5) is visible in the resolve card without a manual page reload.
result: skipped
reason: "User cannot test in current state. User also raised out-of-scope feedback: (1) requests a new 'Archived' status (grey/neutral color) for pipeline runs whose argument has been created and are now read-only, distinct from 'completed'; (2) observed the Resolve status card and the resolve table card render with no visual spacing between them, reading as malformed/merged HTML; (3) intends to write up further requirements for reworking the resolve table as part of this milestone. Not converted to a Gap — see note below Gaps."

### 4. Mobile/responsive check on Resolve card and CreatePersonPopover
expected: On a narrow/mobile viewport, the horizontally-scrollable table wrapper avoids row text overlap; the popover stays within calc(100vw - 32px) and traps/returns focus correctly on open/close.
result: blocked
blocked_by: prior-phase
reason: "Table portion passed on mobile (no row text overlap). Popover portion (viewport-bounded width, focus trap/return) cannot be tested yet because the Resolve card has no visible trigger to open Create/Switch Person — see Test 1."

## Summary

total: 4
passed: 0
issues: 2
pending: 0
skipped: 1
blocked: 1

## Gaps

- truth: "The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises dc8ad284 / CR-01 fix.)"
  status: failed
  reason: "User reported: Looks like there's no trigger on the resolve card to create or even switch people"
  severity: major
  test: 1
  artifacts: []
  missing: []

- truth: "\"Continue Resolve\" is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises 8492f515 / WR-04 fix.)"
  status: failed
  reason: "User reported: I don't see anything like this"
  severity: major
  test: 2
  artifacts: []
  missing: []

- truth: "Resolve card status card and resolve table card render as visually distinct, properly spaced cards."
  status: failed
  reason: "User reported: the resolve card html feels malformed: there is a card that says 'resolve' and has the current status. Then, immediately below it with no spacing between them, is another card with the resolve table."
  severity: cosmetic
  test: 3
  artifacts: []
  missing: []

<!-- Out-of-scope feedback (not a failed-test Gap, needs user decision on where to route):
- New pipeline-run status "Archived" (grey/neutral color) for runs whose argument is created and are now read-only, distinct from "completed".
- User intends to write up further requirements for reworking the Resolve table as part of this milestone.
-->

