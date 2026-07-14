---
status: diagnosed
phase: 33-metadata-update-unique-constraint-guard
source: [33-VERIFICATION.md]
started: 2026-07-14T13:06:00Z
updated: 2026-07-14T10:43:00-05:00
---

## Current Test

[testing complete]

## Tests

### 1. Duplicate recovery through both admin routes
expected: From both the pipeline job page and direct argument page, a colliding save preserves dockets, question number, and argued date. Focus lands on the single inline alert; its link is keyboard reachable, opens the numeric conflicting argument in a new tab, and isolates the opener.
result: issue
reported: "Everything works as expected including the window.opener check with one exception: the error message lists \"Open conflicting argument\" twice like this \"An argument already uses docket blobby, question 1. Open conflicting argument. Open conflicting argument.\""
severity: major

## Summary

total: 1
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "From both admin routes, duplicate recovery appears as one inline alert with one recovery link while preserving attempted metadata, moving focus to the alert, and opening the numeric conflict safely in a new tab."
  status: failed
  reason: "User reported: Everything works as expected including the window.opener check with one exception: the error message lists 'Open conflicting argument' twice: 'An argument already uses docket blobby, question 1. Open conflicting argument. Open conflicting argument.'"
  severity: major
  test: 1
  root_cause: "FastAPI's duplicate payload message already ends with 'Open conflicting argument.', while the shared Svelte card renders that message verbatim and then appends an anchor with the same label, so the composed alert repeats the recovery phrase on both routes."
  artifacts:
    - path: "api/routers/admin.py"
      issue: "Both duplicate response paths include UI action-oriented recovery copy in the backend message."
    - path: "app/src/lib/components/ArgumentDetailsCard.svelte"
      issue: "The shared card appends an identically labeled recovery link after rendering the backend message."
    - path: "api/tests/test_admin_arguments_routes.py"
      issue: "The route contract test locks the actionable phrase into the backend message."
    - path: "api/tests/test_question_number_nullable.py"
      issue: "The frontend contract test checks the alert and link separately but does not assert the composed phrase occurs once."
  missing:
    - "Establish one owner for the recovery action phrase, preferably a factual backend message plus the component-owned accessible link."
    - "Update backend contract assertions and add a composed frontend regression proving 'Open conflicting argument' appears exactly once."
  debug_session: ".planning/debug/phase-33-duplicate-recovery-link.md"
