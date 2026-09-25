---
status: testing
phase: 52-justice-identity
source: [52-VERIFICATION.md]
started: 2026-09-25T16:05:00Z
updated: 2026-09-25T17:05:00Z
---

## Current Test

number: 2
name: Live reset-to-fixture run — progress line and evidence-based outcomes
expected: |
  Status line advances Seeding justices… → Reseeding fixture 1 of 4… → …4 of 4,
  in place, never leading reality; Success state renders on completion; the People
  directory shows the full justice roster; a mid-reset failure shows the
  evidence-based partial/inconclusive message, not the blanket corruption claim.
awaiting: user response

## Tests

### 1. Admin person page Identity card — placement and treatment
expected: Open /admin/people/{id} for a corpus-joined justice (non-blank Oyez Speaker ID) and for an advocate or a D-04 justice (Barrett/Jackson). Confirm (1) the two new rows sit between Full Name and the Name Parts inputs; (2) they match the Full Name readout's box/border/padding/text size; (3) the justice shows real values and the other person shows 'Not in corpus' in grey italic in both rows; (4) neither row can be typed into or focused as a form control.
result: pass
note: |
  Passed after three operator-reported defects were fixed in-flight. Recorded here
  because the test did NOT pass on first presentation, and the automated suite could
  not have caught any of the three.
    1. READ-PATH BUG (fix af7d6b384) — get_person_detail() omitted display_name and
       oyez_speaker_id from the dict the router expands into PersonDetail(**p), which
       silently defaults Optional fields to None. Every person rendered "Not in corpus"
       regardless of stored data. The existing test asserted both fields were None for
       a person with NO corpus join, so it could never fail while the bug existed.
       New test test_get_person_returns_the_actual_corpus_values_not_null pins the
       other half and was verified to fail without the fix.
    2. COPY DEFECT (fix 08327b1e3) — the blank display_name state read "Not in corpus",
       which is false for advocates: they ARE corpus speakers and carry an
       oyez_speaker_id. Measured live: 114 people have both fields, 16 (advocates) have
       an id but no display name, 2 (D-04) have neither. 52-UI-SPEC E3/E4's stated
       rationale — "both fields are blank for exactly the same reason" — was false and
       has been corrected in place. Blank display_name now reads "Uses Full Name".
    3. VISUAL (operator design call) — the read-only readouts were byte-identical to the
       editable inputs. Now flat-chrome (transparent fill, 40%-strength border per the
       new Figma Input/disabled variant), with field descriptions moved below the
       control per Input/invalid. Text contrast kept at 11.87:1 rather than the 3.04:1
       a literal opacity:0.4 would have produced on load-bearing data.

### 2. Live reset-to-fixture run — progress line and evidence-based outcomes
expected: Run one real reset against the dev database: open /admin, run Reset to Fixture through its two-step confirm, watch the status line for the whole run, then open the People directory. Optionally kill the FastAPI process mid-reset to observe the partial-reseed message. The status line advances Seeding justices… → Reseeding fixture 1 of 4… → …4 of 4, in place, never leading reality; the Success state renders on completion; the People directory shows the full justice roster; a mid-reset failure shows the evidence-based partial/inconclusive message, not the blanket corruption claim.
result: [pending]

### 3. Admin Resolve card — JH rendering and unresolved-row avatar
expected: Open an admin pipeline job's Resolve card for an argument with a bench row whose person has a name suffix. Confirm the avatar circle shows JH for John Marshall Harlan, II (not the suffix letter JI), and confirm an unresolved row's avatar looks exactly as it did before this change.
result: [pending]

## Summary

total: 3
passed: 1
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
