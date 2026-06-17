---
status: testing
phase: 07-pipeline-runner
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md
started: 2026-06-16T00:00:00Z
updated: 2026-06-16T00:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

number: 13
name: Failed-state error panel
expected: |
  For a job where a step failed, /admin/pipeline/{id} shows "This run failed."
  followed by the verbatim error message in monospace text. No Retry button —
  only a "Start a new run" link back to /admin/pipeline.
awaiting: user response

## Tests

### 1. Pipeline Runner nav link is active
expected: Navigate to any /admin/* page. The sidebar/nav shows "Pipeline Runner" as a clickable link (not greyed-out text). Clicking it takes you to /admin/pipeline.
result: pass

### 2. /admin/pipeline page loads with URL mode by default
expected: Navigating to /admin/pipeline shows the "New Run" form in URL mode by default. The URL input field is visible; no file picker is shown. A "Start Run" button is present but disabled when the input is empty.
result: pass

### 3. Toggle to file upload mode
expected: Clicking the "Upload PDF" / file toggle button switches the form so the URL input disappears and a file picker appears. The toggle button reflects the active mode (aria-pressed state). Clicking back to URL mode restores the URL input.
result: pass

### 4. Recent Runs history table
expected: The /admin/pipeline page shows a "Recent Runs" table below the New Run form. If no jobs exist yet, an empty-state message is shown. If jobs exist, each row shows the job id, status badge (with correct color per status), and relevant info.
result: pass

### 5. Start a run via URL mode
expected: Enter a supremecourt.gov PDF URL in the URL input (e.g. https://www.supremecourt.gov/oral_arguments/argument_audio/2023/22-1036.pdf) and click Start Run. The page redirects to /admin/pipeline/{id}. The new run appears in the Recent Runs table on returning to /admin/pipeline.
result: pass

### 6. SSRF guard rejects non-supremecourt.gov URLs
expected: Enter a URL that is NOT from supremecourt.gov (e.g. https://example.com/file.pdf) and click Start Run. The form shows an error (e.g. "Could not start the run") without creating a job or redirecting.
result: pass

### 7. /admin/pipeline/[job_id] live step cards
expected: Opening /admin/pipeline/{id} for an active job shows three step cards: Ingest, Parse, Resolve. The current running step shows a spinner and "Running" badge. The page auto-refreshes every ~2.5 seconds without any manual action — status badges update as the pipeline progresses.
result: pass

### 8. Polling stops on terminal state
expected: Once a job reaches "completed", "failed", or "paused" state, the page stops auto-refreshing (no more 2.5s network requests). The final state is displayed statically.
result: pass

### 9. Discrepancy review table appears on PAUSED resolve step
expected: When the Resolve step is PAUSED (speaker aliases could not be auto-resolved), the Resolve step card expands to show a discrepancy table. Each row lists a raw speaker label, the auto-matched candidate name (if any), and Confirm / Correct buttons. The "Continue Resolve" button is NOT yet visible.
result: skipped
reason: No job currently in PAUSED state; requires a run with unresolved speaker aliases

### 10. Confirm and Correct disposition in discrepancy table
expected: Clicking Confirm on a row marks that speaker match as accepted (visual indicator updates). Clicking Correct opens a dropdown populated with candidate names from that row only. Selecting a candidate from the dropdown marks it as corrected. Once ALL rows are dispositioned, the "Continue Resolve" button appears.
result: skipped
reason: Depends on test 9 (PAUSED state required)

### 11. Add new person inline
expected: In the Correct dropdown, selecting "— Add new person —" reveals a small form with Full Name and Role fields. Submitting it creates the person and auto-selects them in that row's dropdown, dismissing the form. The new person is now available as a candidate in that row.
result: skipped
reason: Depends on test 9 (PAUSED state required)

### 12. Continue Resolve submits and restarts polling
expected: After all rows are dispositioned, clicking Continue Resolve submits the matches. The button text changes to "Submitting…" and becomes disabled. The page then transitions the Resolve step from PAUSED back to RUNNING (or COMPLETED if no further issues), and polling resumes to show the updated state.
result: skipped
reason: Depends on test 9 (PAUSED state required)

### 13. Failed-state error panel
expected: For a job where a step failed, /admin/pipeline/{id} shows "This run failed." followed by the verbatim error message in monospace text. There is no Retry button — only a "Start a new run" link back to /admin/pipeline.
result: [pending]

### 14. Pipeline CLI --job-id flag (ingest)
expected: Running `python -m pipeline ingest --help` in a terminal shows both `--job-id` and `--spaces-key` flags listed. Running `python -m pipeline parse --help` and `python -m pipeline resolve --help` each show `--job-id`.
result: [pending]

## Summary

total: 14
passed: 8
issues: 0
pending: 2
skipped: 4
skipped: 0
blocked: 0

## Gaps

[none yet]
