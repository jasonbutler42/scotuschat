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
result: blocked
reason: all utterances in test argument are fully resolved
waived_at: 2026-08-18
waived_by: "operator — instructed to skip the outstanding human UAT items and prepare for Phase 48"
waiver_reason: "NOT VERIFIED — deliberately not run, not a pass. The test's own instructions say to skip it when every utterance is resolved, and no argument with an unresolved speaker has been available since. Genuinely unverifiable without seeding one, so it is closed rather than carried indefinitely. If an unresolved-speaker argument appears during Phase 49's review-queue work, this is a one-click check worth taking then."
phase_49_06_update: |
  2026-08-23 (Phase 49 plan 49-06): `api.services.admin_dev.seed_unresolved_speaker_fixture`
  (D-33a) now makes an unresolved-utterance argument reachable on demand — the state this test
  has been waiting on since it was written. Run once against the live dev database (conversation
  15169, "Baltimore & Ohio Railroad Company v. United States", argument id 1784), it nulled
  `person_id` on all 5 `Utterance` rows carrying participant 3500's (Lloyd N. Cutler)
  `raw_speaker_label`, confirmed by direct query immediately afterward (5 matching rows, all 5
  `person_id IS NULL`). This is a genuine correction, not the original plan's premise as written:
  nulling `ArgumentParticipant.person_id` alone does NOT touch `Utterance.person_id` (they are
  independent columns — `api/services/arguments.py` reads `Utterance.person_id` directly for the
  public chat page, never through `ArgumentParticipant`) — the seeder was extended during this
  plan's own execution to null both, specifically so this test could become reachable.

  **A second, separate precondition remains, outside this seeder's scope: the argument must be
  PUBLISHED to appear on the public chat page Test 8 actually exercises.** The Complexity fixture
  (15169) is deliberately left CANDIDATE/DRAFT by `reset_to_fixture` (it is the reference
  "freshly imported, still editable" fixture other Phase 44/49 work relies on) — this seeder does
  not publish it, and auto-publishing a fixture argument as a side effect of a "seed unresolved
  speaker" dev action would be surprising, unscoped behavior with no test coverage of its own, so
  it was deliberately NOT added here (Rule 4 boundary, not an oversight). A human who wants to see
  this on the public site must deliberately publish this argument themselves via the admin UI,
  understanding that leaves a corpus fixture in a modified (published) state until the next reset.

  **This is a data-layer observation only** — a direct query, not a browser, and not the public
  page itself. This sandbox's permission policy denies reading `.env` (admin credentials), so no
  authenticated browser session was reachable to complete either the admin-side confirmation or
  the public-page walkthrough. **STILL NOT VERIFIED — do not read this note as a pass.** A human
  must run `Reset to Fixture` + `Seed unresolved speaker`, publish the argument if they want the
  public view, open the argument's public chat page, confirm the plain non-interactive avatar
  renders for Lloyd N. Cutler's utterances, and flip this `result` to `pass` or `issue`.
blocking_reason_now: "authenticated browser access unavailable to the automated executor, plus a deliberate publish step this seeder does not perform — no longer a missing-underlying-state blocker"

## Summary

total: 8
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 1
waived: 0
audit_note: "2026-08-18 audit + operator waiver. Test 8 skipped → waived: NOT verified, deliberately not run. Unverifiable without an argument containing an unresolved speaker, which has never been available; closed rather than carried further."
phase_49_06_note: "2026-08-23 (plan 49-06): Test 8's original blocking reason (no unresolved-speaker argument available) is resolved at the data layer — see the test's own phase_49_06_update. Reclassified waived -> blocked (blocked on authenticated-browser access plus a deliberate publish step, not on a missing state). A human must complete the browser check before this can become pass/issue."

## Gaps

