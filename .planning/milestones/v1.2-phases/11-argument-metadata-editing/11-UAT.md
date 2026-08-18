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
  status: resolved
  resolution: "Closed as BUG-01 in Phase 45. api/services/arguments.py::get_argument_with_utterances and api/services/speakers.py::get_argument_speakers both gate on Argument.published_at, and the router raises HTTPException(404) (api/routers/arguments.py:44-45,66-68), so an unpublished argument's direct URL 404s on both client-side nav and hard SSR refresh. 45-VERIFICATION.md truth 2 VERIFIED, operator-confirmed live at 45-01 Task 3 steps 2-3. Closed by the 2026-08-18 cross-phase UAT audit; see .planning/notes/2026-08-18-uat-audit-closure.md"
  previous_status: failed
  reason: "User reported: after unpublish, argument no longer appears in /cases list but is still accessible directly via slug"
  severity: major
  test: 3
  deferred: true
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
