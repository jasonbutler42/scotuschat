---
status: complete
phase: 11-argument-metadata-editing
source: [11-VERIFICATION.md]
started: 2026-06-22T00:00:00Z
updated: 2026-06-23T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Status badges and per-row publish toggles render correctly
expected: /admin/arguments list page shows Published/Resolved/Pending badges in distinct colors and per-row publish/unpublish buttons conditional on current state.
result: pass

### 2. Slug collision error displays in edit page
expected: Patching an argument with a case_name that would generate a slug already used by another argument triggers the `role=alert` error message in the edit form (text from UI-SPEC D-11 collision copy).
result: pass

### 3. Publish/unpublish round-trip + public visibility gate
expected: Publishing an argument stamps published_at and the argument's case appears in the public /cases list. Unpublishing clears published_at and the case disappears from the public list.
result: pass

## Summary

total: 3
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Unpublishing an argument hides it at its direct /cases/{slug} URL"
  status: failed
  reason: "User reported: after unpublish, argument no longer appears in /cases list but is still accessible directly via slug"
  severity: major
  test: 3
  deferred: true
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
