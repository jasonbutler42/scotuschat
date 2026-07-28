---
status: complete
phase: 39-bench-popover-additional-context-data
source: [39-01-SUMMARY.md, 39-02-SUMMARY.md, 39-03-SUMMARY.md, 39-04-SUMMARY.md, 39-05-SUMMARY.md, 39-06-SUMMARY.md]
started: 2026-07-28T23:26:54Z
updated: 2026-07-28T23:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Migrations applied to real dev database
expected: `python -m alembic current` names the reason-left revision (0024) as head after `upgrade head`
result: skipped
reason: Not explicitly reported by operator (real dev DB was likely already at head from an accidental early apply during 39-02 — see STATE.md blockers).

### 2. Importer backfill + idempotency
expected: First run backfills birthdate/death date/reason and creates rows as needed; second consecutive run creates 0 people and 0 tenures
result: pass

### 3. Local stack starts and argument pages are viewable
expected: `dev-start.ps1` brings up a working stack; argument pages load and speaker avatars are clickable
result: pass

### 4. Rehnquist two-tenure card
expected: Birth/death line, two tenure blocks (Chief 1986-2005 Died in office, Associate 1972-1986 Promoted), card fits or scrolls
result: skipped
reason: Individual field values not confirmed/denied by operator; the card's general layout is covered by Gap 13 below, which applies to every card including this one.

### 5. Living Justice card
expected: Birth line only, no death half, no dash, no reason line on current tenure
result: skipped
reason: Not explicitly reported by operator.

### 6. Party-neutral rendering across different parties
expected: Identical field order, font size, and color regardless of appointing president's party — no visual difference tied to party value
result: pass
reported: "yes, all parties render identically"

### 7. Bio clamp/toggle (3-line clamp, Read more/Show less)
expected: Long bio clips to 3 lines with a working Read more/Show less toggle; short bio shows no toggle; no bio shows no paragraph
result: issue
reported: "Could not be meaningfully verified — see test 10. The bio being tested was never actually saved, so there is no real long bio in the data to check clamp/toggle behavior against."
severity: major

### 8. Advocate card
expected: Role pill, italic "Coming soon" descriptor line, bio if present, no tenure section
result: skipped
reason: Not explicitly reported by operator.

### 9. No extraneous fields
expected: No age, tenure-length, case-count, or "Edit person" link on any card
result: skipped
reason: Not explicitly reported by operator (no such fields were reported as present, but not explicitly checked off either).

### 10. Admin editor round-trip
expected: Death Date, per-tenure Reason Left, and Bio & Photo all save and persist through Save Person / reload; a Bio & Photo save leaves a previously-set Death Date untouched
result: issue
reported: "death date saves fine. reason for leaving also saves and displays correctly. I can add more tenures and they show up as expected. I added a short bio to Felix Frankfurter but it did not show up on the card. Turns out, it didn't actually save, but the text I entered persisted in the box until I hit refresh."
severity: major

### 11. Reason Left dropdown exact options
expected: Dropdown offers exactly — None —, Retired, Died in office, Promoted
result: skipped
reason: Not explicitly reported by operator (implied working, given test 10's Reason Left save/display passed).

### 12. Separator dot legibility (new finding, not on original list)
expected: The `·` between birth/death dates and between president/party renders with clear, visible spacing on both sides
result: issue
reported: "The dot between birth and death and also between the president and their party affiliation is too small to be effective."
severity: minor

### 13. Overall visual style vs. Figma mockups (new finding, not on original list)
expected: Popover layout matches 39-UI-SPEC.md / the Figma mockups (popover - Bench.png, popover-Advocate.png)
result: issue
reported: "The overall style does not look like the design in Figma." Operator supplied a screenshot (bench popover.png) compared directly against both mockups.
severity: major

## Summary

total: 13
passed: 4
issues: 4
pending: 0
skipped: 5
blocked: 0

## Gaps

- truth: "Bio text saves and persists through the Bio & Photo card, and a saved bio's clamp/Read-more toggle can be verified against real data"
  status: failed
  reason: "User reported: added a short bio to Felix Frankfurter, it did not show up on the card; the typed text persisted in the input until refresh, then reverted — the save silently fails while appearing to succeed."
  severity: major
  test: 10
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "The separator dot (·) between birth/death dates and between president/party renders with clear, legible spacing on both sides"
  status: failed
  reason: "User reported: 'The dot between birth and death and also between the president and their party affiliation is too small to be effective.' Confirmed by direct comparison of the operator's screenshot (bench popover.png) against the Figma mockup (popover - Bench.png) — mockup shows clearly spaced ' · ', live version renders the dot flush against adjacent text on both sides."
  severity: minor
  test: 12
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Popover visual layout (tenure row structure, typography weight) matches the 39-UI-SPEC.md / Figma mockup contract"
  status: failed
  reason: "User reported: 'The overall style does not look like the design in Figma.' Confirmed by direct screenshot comparison: the mockup renders each tenure as a two-column row (bold tenure title left, year range right-aligned on the same line); the live version renders a single line with an em dash ('Chief Justice — 1953-1969'), not bold, not two-column. Name/title typography also reads less prominent than the mockup. Note: both mockups show an 'Edit person' link at bottom-right — its absence in the live popover is intentional (D-17, deferred to backlog item 999.9), not part of this gap."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
