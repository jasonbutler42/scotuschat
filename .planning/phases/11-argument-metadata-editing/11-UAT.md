---
status: testing
phase: 11-argument-metadata-editing
source: [11-VERIFICATION.md]
started: 2026-06-22T00:00:00Z
updated: 2026-06-22T00:00:00Z
---

## Current Test

number: 1
name: Status badges and per-row publish toggles render correctly
expected: |
  /admin/arguments list page shows three distinct badge states:
  Published (green #4ade80), Resolved (purple #a78bfa), Pending (grey #94a3b8).
  Publish button visible for Resolved/Pending arguments; Unpublish button visible for Published arguments.
awaiting: user response

## Tests

### 1. Status badges and per-row publish toggles render correctly
expected: /admin/arguments list page shows Published/Resolved/Pending badges in distinct colors and per-row publish/unpublish buttons conditional on current state.
result: [pending]

### 2. Slug collision error displays in edit page
expected: Patching an argument with a case_name that would generate a slug already used by another argument triggers the `role=alert` error message in the edit form (text from UI-SPEC D-11 collision copy).
result: [pending]

### 3. Publish/unpublish round-trip + public visibility gate
expected: Publishing an argument stamps published_at and the argument's case appears in the public /cases list. Unpublishing clears published_at and the case disappears from the public list.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
