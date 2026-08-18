---
status: complete
phase: 14-speaker-popover-card
source: 14-01-SUMMARY.md, 14-02-SUMMARY.md, 14-03-SUMMARY.md
started: 2026-06-25T18:00:00Z
updated: 2026-06-25T18:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Argument page loads with speakers data
expected: Navigate to any published argument URL. The page renders normally — header with case name, docket, speaker roster columns, chat stream, and section rail. No errors or blank areas.
result: pass

### 2. Bench Justice popover — utterance avatar
expected: Click an avatar button next to a bench Justice's utterance bubble. A popover card appears near the clicked button containing: the Justice's full name, their role (e.g. "Associate Justice"), one or more tenure rows showing seat and year range (e.g. "Associate Justice — 1993–present"), and "Appointed by [President name]". No party affiliation appears anywhere on the card.
result: pass

### 3. Advocate popover — utterance avatar
expected: Click an avatar button next to an advocate's utterance. A popover card appears showing the advocate's name and role only. No tenure section and no "Appointed by" line appear.
result: pass

### 4. Header roster popover
expected: In the argument header, click an avatar circle in the Bench column or the Advocates column. A popover card appears near the clicked element with the correct speaker's information (same content rules as tests 2 and 3).
result: pass

### 5. Popover dismissal — click outside
expected: With a speaker popover open, click anywhere on the page outside the popover card. The popover closes.
result: pass

### 6. Popover dismissal — Escape key
expected: With a speaker popover open, press the Escape key. The popover closes.
result: pass

### 7. Keyboard access
expected: Tab to an avatar button (a visible focus ring appears on the button). Press Enter — the popover opens. Press Escape — the popover closes and focus returns to the button.
result: pass

### 8. Non-resolved utterance — no popover trigger
expected: An utterance whose speaker was not resolved (no person_id) shows a plain avatar circle that is NOT a button. Clicking the circle does nothing — no popover opens. (Skip this test if all utterances in your test argument are fully resolved.)
result: waived
reason: all utterances in test argument are fully resolved
waived_at: 2026-08-18
waived_by: "operator — instructed to skip the outstanding human UAT items and prepare for Phase 48"
waiver_reason: "NOT VERIFIED — deliberately not run, not a pass. The test's own instructions say to skip it when every utterance is resolved, and no argument with an unresolved speaker has been available since. Genuinely unverifiable without seeding one, so it is closed rather than carried indefinitely. If an unresolved-speaker argument appears during Phase 49's review-queue work, this is a one-click check worth taking then."

## Summary

total: 8
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0
waived: 1
audit_note: "2026-08-18 audit + operator waiver. Test 8 skipped → waived: NOT verified, deliberately not run. Unverifiable without an argument containing an unresolved speaker, which has never been available; closed rather than carried further."

## Gaps

