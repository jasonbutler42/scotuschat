---
status: complete
phase: 21-admin-ui-surface
source: [21-VERIFICATION.md]
started: 2026-07-01T23:00:00Z
updated: 2026-07-02T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. ADMIN-01: Two-step confirm on an unpublished argument
expected: |
  Navigate to an unpublished argument edit page (/admin/arguments/[id]).
  Click 'Delete argument' → the button row changes in-place to 'Confirm delete' + 'Cancel'
  with no layout shift (Danger Zone card height unchanged).
  Click 'Confirm delete' → DELETE request fires, argument is removed,
  browser redirects to /admin/arguments list.
result: pass

### 2. ADMIN-01: Disabled Delete button + tooltip on a published argument
expected: |
  Navigate to a published argument edit page.
  The 'Delete argument' button is disabled (grayed out, not clickable).
  A tooltip or help text reading 'Published arguments cannot be deleted. Unpublish first.'
  is visible or accessible via screen reader / aria-describedby.
result: pass

### 3. ADMIN-02: Two-step confirm on a pipeline run + argument survives
expected: |
  Navigate to a pipeline run detail page (/admin/pipeline/[job_id]).
  Click 'Delete run' → two-button row appears in-place (no layout shift).
  Click 'Confirm delete' → DELETE request fires, run deleted, browser redirects to /admin/pipeline.
  Verify the linked argument and its utterances still exist at /admin/arguments.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
