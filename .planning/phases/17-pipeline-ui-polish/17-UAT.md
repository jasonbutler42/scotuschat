---
status: testing
phase: 17-pipeline-ui-polish
source: 17-01-SUMMARY.md, 17-02-SUMMARY.md, 17-03-SUMMARY.md
started: 2026-06-27T00:00:00Z
updated: 2026-06-29T00:00:00Z
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
result: pass
note: initial failure was a stale-page misread — parse_stats JSON confirmed flowing correctly via DevTools

### 4. Parse stats absent while parse is pending or running
expected: On a job where the Parse step is still pending or running (not yet "Completed"), the Parse stage card shows NO Utterances, Distinct speakers, Case name, or Argued rows. The card may show the step status badge only.
result: pass

### 5. View source PDF link card visible
expected: On a job detail page where spaces_key, pdf_url, or original_filename is set, a "View source PDF" link card appears between the Argument card and the step cards. The link is styled in blue underline text and opens in a new tab.
result: pending
note: "Gap resolved by plan 17-03 — condition at +page.svelte:471 now includes original_filename. Needs live re-verification."

### 6. View source PDF opens PDF correctly without token leakage
expected: Click the "View source PDF" link. For a Spaces-backed job the address bar in the new tab shows a DO Spaces pre-signed URL (not /api/admin/... and not /admin/pipeline/...). For a local disk-backed job the PDF streams inline. The X-Admin-Token value must NOT appear in the address bar, visible response headers, or any network request visible to the browser. The admin token must remain server-side.
result: pass

### 7. View source PDF link absent when no PDF source
expected: On a job detail page where spaces_key, pdf_url, and original_filename are all null, the "View source PDF" link card does not appear between the Argument card and the step cards. No broken anchor or placeholder text is visible.
result: pending
note: "Unblocked by 17-03 fix — now testable with a job that has all three fields null."

## Summary

total: 7
passed: 5
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

- truth: "On a job detail page where spaces_key, pdf_url, or original_filename is set, a 'View source PDF' link card appears between the Argument card and the step cards"
  status: resolved
  resolved_by: "17-03"
  resolved_at: "2026-06-29"
  fix: "Added `|| data.job.original_filename` to condition at +page.svelte:471 — now a three-way OR"
  test: 5
  pending_live_verification: true
