---
status: complete
phase: 27-people-admin
source: [27-VERIFICATION.md]
started: 2026-07-09T11:25:00Z
updated: 2026-07-09T12:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Click-to-filter pill round-trip in a live browser
expected: URL updates to ?tab={tab}&missing={field}; table shows only matching rows; clicking again (or "Clear filter") returns to the unfiltered ?tab={tab} view.
result: issue
reported: "functional pass but the table spacing between argument count and missing fields is too tight"
severity: cosmetic

### 2. Bench/Advocate slide-reveal animation and visual token compliance
expected: On /admin/people/new and /admin/people/{id}, toggling Bench↔Advocate grows/shrinks the Person Type card's Birth Date/Death Date/Tenure Periods section (including the restored Seat field) via a slide transition (not a fade or instant snap); colors/spacing match .planning/codebase/DESIGN-SYSTEM.md tokens; switching Advocate→Bench→Advocate preserves any in-progress tenure edits, including a partially-typed Seat value.
result: issue
reported: "The animation works perfectly and preserves previous tenure entries. Seat and President's Party should both be dropdowns, though."
severity: minor

### 3. Photo/Merge/Delete gating on the create route
expected: Loading /admin/people/new shows a clean layout with only Identity and Person Type cards — no dangling whitespace or broken card boundaries where Photo, Biography, Merge, or Delete would normally sit.
result: pass

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

Note: Test 3 itself passed (Photo/Merge/Delete gating confirmed clean). The
tester found an additional, unrelated bug on the same page while testing it —
recorded below as a third Gaps entry (tagged to test 3 for provenance) without
changing test 3's own pass result.

## Gaps

- truth: "The Advocate-tab table's Argument count and Missing fields columns have adequate spacing between them"
  status: failed
  reason: "User reported: functional pass but the table spacing between argument count and missing fields is too tight"
  severity: cosmetic
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Bench/Advocate slide-reveal animation and visual token compliance"
  status: failed
  reason: "User reported: The animation works perfectly and preserves previous tenure entries. Seat and President's Party should both be dropdowns, though."
  severity: minor
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Creating a person with both Full Name and first/last/middle/suffix name-part fields filled in persists all of them, matching the [id] editor's save behavior"
  status: failed
  reason: >
    User reported (found during test 3, unrelated to that test's own pass):
    "What is a real bug is that if I enter something into full name AND into
    the component parts it only saves the full name and discards the
    components. That only happens on person creation; it saves properly on
    saving an existing person."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
