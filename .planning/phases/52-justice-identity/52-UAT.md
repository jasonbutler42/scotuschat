---
status: testing
phase: 52-justice-identity
source: [52-VERIFICATION.md]
started: 2026-09-25T16:05:00Z
updated: 2026-09-25T16:05:00Z
---

## Current Test

number: 1
name: Admin person page Identity card — placement and treatment of the two read-only rows
expected: |
  Placement, treatment, and empty/populated contrast match 52-UI-SPEC.md exactly:
  the two new rows sit between Full Name and the Name Parts inputs; they match the
  Full Name readout's box/border/padding/text size; a corpus-joined justice shows
  real values while an advocate or a D-04 justice (Barrett/Jackson) shows
  'Not in corpus' in grey italic in both rows; neither row can be typed into or
  focused as a form control.
awaiting: user response

## Tests

### 1. Admin person page Identity card — placement and treatment
expected: Open /admin/people/{id} for a corpus-joined justice (non-blank Oyez Speaker ID) and for an advocate or a D-04 justice (Barrett/Jackson). Confirm (1) the two new rows sit between Full Name and the Name Parts inputs; (2) they match the Full Name readout's box/border/padding/text size; (3) the justice shows real values and the other person shows 'Not in corpus' in grey italic in both rows; (4) neither row can be typed into or focused as a form control.
result: [pending]

### 2. Live reset-to-fixture run — progress line and evidence-based outcomes
expected: Run one real reset against the dev database: open /admin, run Reset to Fixture through its two-step confirm, watch the status line for the whole run, then open the People directory. Optionally kill the FastAPI process mid-reset to observe the partial-reseed message. The status line advances Seeding justices… → Reseeding fixture 1 of 4… → …4 of 4, in place, never leading reality; the Success state renders on completion; the People directory shows the full justice roster; a mid-reset failure shows the evidence-based partial/inconclusive message, not the blanket corruption claim.
result: [pending]

### 3. Admin Resolve card — JH rendering and unresolved-row avatar
expected: Open an admin pipeline job's Resolve card for an argument with a bench row whose person has a name suffix. Confirm the avatar circle shows JH for John Marshall Harlan, II (not the suffix letter JI), and confirm an unresolved row's avatar looks exactly as it did before this change.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
