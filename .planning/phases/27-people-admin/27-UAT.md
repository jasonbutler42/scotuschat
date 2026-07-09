---
status: testing
phase: 27-people-admin
source: [27-VERIFICATION.md]
started: 2026-07-09T11:25:00Z
updated: 2026-07-09T11:25:00Z
---

## Current Test

number: 1
name: Click-to-filter pill round-trip in a live browser
expected: |
  On /admin/people, click a missing-field pill, confirm the table filters and
  the "Filtering by … · Clear filter" line appears; click the pill again (or
  "Clear filter") and confirm it resets. URL updates to
  ?tab={tab}&missing={field}; table shows only matching rows; clicking again
  returns to the unfiltered ?tab={tab} view.
awaiting: user response

## Tests

### 1. Click-to-filter pill round-trip in a live browser
expected: URL updates to ?tab={tab}&missing={field}; table shows only matching rows; clicking again (or "Clear filter") returns to the unfiltered ?tab={tab} view.
result: [pending]

### 2. Bench/Advocate slide-reveal animation and visual token compliance
expected: On /admin/people/new and /admin/people/{id}, toggling Bench↔Advocate grows/shrinks the Person Type card's Birth Date/Death Date/Tenure Periods section (including the restored Seat field) via a slide transition (not a fade or instant snap); colors/spacing match .planning/codebase/DESIGN-SYSTEM.md tokens; switching Advocate→Bench→Advocate preserves any in-progress tenure edits, including a partially-typed Seat value.
result: [pending]

### 3. Photo/Merge/Delete gating on the create route
expected: Loading /admin/people/new shows a clean layout with only Identity and Person Type cards — no dangling whitespace or broken card boundaries where Photo, Biography, Merge, or Delete would normally sit.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
