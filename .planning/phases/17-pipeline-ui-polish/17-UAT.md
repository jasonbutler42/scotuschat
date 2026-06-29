---
status: diagnosed
phase: 17-pipeline-ui-polish
source: 17-01-SUMMARY.md, 17-02-SUMMARY.md
started: 2026-06-27T00:00:00Z
updated: 2026-06-27T00:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

number: 8
name: [testing complete]
awaiting: n/a

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, migration 0009 (add_original_filename) applies cleanly, and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass

### 2. Ingest card shows source file row
expected: Upload a transcript PDF through /admin/pipeline and open the job detail page /admin/pipeline/{job_id}. The Ingest stage card shows a "Source file" label row with the uploaded filename (e.g. transcript.pdf). For a URL-sourced job the row shows the full supremecourt.gov URL verbatim with long-URL word-wrapping. For an old pre-migration job with both values null, the row is entirely absent.
result: issue
reported: "when I try to upload a transcript, I get a 502 error"
severity: blocker

### 3. Parse stats appear after parse completes
expected: On a job where the Parse step shows "Completed", the Parse stage card shows four rows: "Utterances" (an integer count), "Distinct speakers" (an integer count), "Case name" (text or em dash), and "Argued" (formatted date like "Jun 27, 2026" or em dash). All values are raw counts only — no percentages, ratios, or derived labels.
result: blocked
blocked_by: server
reason: "I get 502 for every pipeline job I try to view"

### 4. Parse stats absent while parse is pending or running
expected: On a job where the Parse step is still pending or running (not yet "Completed"), the Parse stage card shows NO Utterances, Distinct speakers, Case name, or Argued rows. The card may show the step status badge only.
result: blocked
blocked_by: server
reason: "I get 502 for every pipeline job I try to view"

### 5. View source PDF link card visible
expected: On a job detail page where either spaces_key or pdf_url is set, a "View source PDF" link card appears between the Argument card and the step cards. The link is styled in blue underline text and opens in a new tab.
result: blocked
blocked_by: server
reason: "I get 502 for every pipeline job I try to view"

### 6. View source PDF opens PDF correctly without token leakage
expected: Click the "View source PDF" link. For a Spaces-backed job the address bar in the new tab shows a DO Spaces pre-signed URL (not /api/admin/... and not /admin/pipeline/...). For a local disk-backed job the PDF streams inline. The X-Admin-Token value must NOT appear in the address bar, visible response headers, or any network request visible to the browser. The admin token must remain server-side.
result: blocked
blocked_by: server
reason: "I get 502 for every pipeline job I try to view"

### 7. View source PDF link absent when no PDF source
expected: On a job detail page where both spaces_key and pdf_url are null (e.g. a freshly created job before ingest runs with no PDF URL), the "View source PDF" link card does not appear between the Argument card and the step cards. No broken anchor or placeholder text is visible.
result: blocked
blocked_by: server
reason: "I get 502 for every pipeline job I try to view"

## Summary

total: 7
passed: 1
issues: 1
pending: 0
skipped: 0
blocked: 5

## Gaps

- truth: "Upload a transcript PDF through /admin/pipeline succeeds and the job detail page shows the source file on the Ingest card"
  status: failed
  reason: "User reported: when I try to upload a transcript, I get a 502 error"
  severity: blocker
  test: 2
  root_cause: "create_job() returns AdminJob with no parse_stats in __dict__; Pydantic v2 from_attributes does getattr(job, 'parse_stats') which raises AttributeError -> ValidationError during response serialization -> 500 -> 502. Same issue in rerun_job()."
  artifacts:
    - path: "api/services/admin_jobs.py"
      issue: "create_job() and rerun_job() return AdminJob without setting job.__dict__['parse_stats'] = None"
  missing:
    - "Set job.__dict__['parse_stats'] = None before return in create_job() and rerun_job()"
  debug_session: ""

- truth: "The pipeline job detail page /admin/pipeline/{job_id} loads successfully for any existing job"
  status: failed
  reason: "User reported: I get 502 for every pipeline job I try to view"
  severity: blocker
  test: 3
  root_cause: "Infinite mutual recursion: get_job() (line 97) calls get_run_id_for_step(), which (line 221) calls get_job() back. Python hits recursion limit -> RecursionError -> 500 -> 502 on every job detail load."
  artifacts:
    - path: "api/services/admin_jobs.py"
      issue: "get_run_id_for_step() calls get_job() to fetch argument_id, but get_job() calls get_run_id_for_step() — mutual recursion"
  missing:
    - "In get_run_id_for_step, replace get_job() call with a direct select(AdminJob.argument_id).where(AdminJob.id == job_id) query"
  debug_session: ""
