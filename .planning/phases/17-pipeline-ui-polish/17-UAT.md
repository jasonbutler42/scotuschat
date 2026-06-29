---
status: complete
phase: 17-pipeline-ui-polish
source: 17-01-SUMMARY.md, 17-02-SUMMARY.md
started: 2026-06-27T00:00:00Z
updated: 2026-06-27T00:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, migration 0009 (add_original_filename) applies cleanly, and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass

### 2. Ingest card shows source file row
expected: Upload a transcript PDF through /admin/pipeline and open the job detail page /admin/pipeline/{job_id}. The Ingest stage card shows a "Source file" label row with the uploaded filename (e.g. transcript.pdf). For a URL-sourced job the row shows the full supremecourt.gov URL verbatim with long-URL word-wrapping. For an old pre-migration job with both values null, the row is entirely absent.
result: pass

### 3. Parse stats appear after parse completes
expected: On a job where the Parse step shows "Completed", the Parse stage card shows four rows: "Utterances" (an integer count), "Distinct speakers" (an integer count), "Case name" (text or em dash), and "Argued" (formatted date like "Jun 27, 2026" or em dash). All values are raw counts only — no percentages, ratios, or derived labels.
result: issue
reported: "FAIL. The Parse card only shows the 'Completed' badge"
severity: major

### 4. Parse stats absent while parse is pending or running
expected: On a job where the Parse step is still pending or running (not yet "Completed"), the Parse stage card shows NO Utterances, Distinct speakers, Case name, or Argued rows. The card may show the step status badge only.
result: pass

### 5. View source PDF link card visible
expected: On a job detail page where either spaces_key or pdf_url is set, a "View source PDF" link card appears between the Argument card and the step cards. The link is styled in blue underline text and opens in a new tab.
result: issue
reported: "There is no link for the source pdf"
severity: major

### 6. View source PDF opens PDF correctly without token leakage
expected: Click the "View source PDF" link. For a Spaces-backed job the address bar in the new tab shows a DO Spaces pre-signed URL (not /api/admin/... and not /admin/pipeline/...). For a local disk-backed job the PDF streams inline. The X-Admin-Token value must NOT appear in the address bar, visible response headers, or any network request visible to the browser. The admin token must remain server-side.
result: pass

### 7. View source PDF link absent when no PDF source
expected: On a job detail page where both spaces_key and pdf_url are null (e.g. a freshly created job before ingest runs with no PDF URL), the "View source PDF" link card does not appear between the Argument card and the step cards. No broken anchor or placeholder text is visible.
result: skipped
reason: "Cannot determine — new jobs (which should have spaces_key or pdf_url set) are already showing the link absent incorrectly; cannot isolate the truly-null case from the broken-response case"

## Summary

total: 7
passed: 4
issues: 2
pending: 0
skipped: 1
blocked: 0

## Gaps

- truth: "On a completed parse job, the Parse stage card shows Utterances, Distinct speakers, Case name, and Argued rows"
  status: failed
  reason: "User reported: FAIL. The Parse card only shows the 'Completed' badge"
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "On a job detail page where spaces_key or pdf_url is set, a 'View source PDF' link card appears between the Argument card and the step cards"
  status: failed
  reason: "User reported: There is no link for the source pdf"
  severity: major
  test: 5
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
