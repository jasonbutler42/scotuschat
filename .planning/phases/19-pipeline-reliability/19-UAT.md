---
status: testing
phase: 19-pipeline-reliability
source: 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md, 19-04-SUMMARY.md
started: 2026-06-30T16:17:28Z
updated: 2026-07-01T00:01:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 7
name: Metadata card — hint text from cover extraction (re-test after argued_date JSONB fix)
expected: |
  Run the pipeline with a purposely incorrect docket number. After the job completes parse, navigate to its detail page. In the Argument Metadata card, the Docket field should show faint hint text "Extracted: [value]" if the PDF cover's docket differs from what you typed as the argument's docket. Fields where extracted and stored values match show no hint text.
awaiting: user response

## Tests

### 1. Pipeline start form — Docket and Question fields present
expected: Open /admin/pipeline. A "Docket number" text input (optional, placeholder "e.g. 14-556 (optional)") and a "Question number" selector (Q1/Q2 options, default Q1) appear on the start form above the Start Run button.
result: pass

### 2. Preflight — no duplicate, form submits normally
expected: Enter a docket string that does NOT match any existing argument (e.g. "00-9999") and question Q1, then click Start Run. No warning banner appears — the pipeline run starts as normal with no interruption.
result: pass

### 3. Preflight — duplicate detected, warning banner appears
expected: Enter the docket number and question of an argument that already exists in the DB, then click Start Run. An amber-bordered warning banner appears with heading "⚠ Argument already exists", showing the matched docket and question, plus "Cancel" and "Start anyway" buttons.
result: pass

### 4. Duplicate banner — Cancel resets state
expected: After the duplicate warning banner appears (test 3), click Cancel. The banner disappears and both the docket field and question selector remain editable so the operator can change them and retry preflight.
result: pass

### 5. Duplicate banner — Start anyway proceeds (re-test after Plan 05 fix)
expected: Trigger the duplicate warning again, then click "Start anyway". The pipeline run starts despite the detected duplicate (the DB unique constraint is the authoritative backstop). No secondary prompt; the run proceeds. The operator is navigated to the new job detail page — NOT logged out.
result: pass

### 6. Job detail — Argument Metadata card present
expected: Navigate to a completed job's detail page that has an argument linked. An "Argument Metadata" card appears between the argument preview and the View source PDF card, with Case name, Docket, and Argued date input fields pre-populated from the stored argument data, and a "Save metadata" button at the bottom.
result: pass

### 7. Metadata card — hint text from cover extraction
expected: For a job where the PDF cover extractor found a docket or date different from what is currently stored, the relevant field shows faint hint text like "Extracted: 14-556". Fields where extracted and stored values match, or where cover_metadata is null, show no hint text.
result: [pending]
note: Re-testing after cover_extractor.py fix — argued_date was stored as a date object (not JSON-serializable); changed to .isoformat() string in commit pending. Run the pipeline again with a purposely incorrect docket to create a suitable test job.

### 8. Metadata card — save succeeds
expected: Edit one of the metadata fields (e.g., change case_name or source_docket) and click Save metadata. A green "Metadata saved." success message appears below the button. Refreshing the page shows the updated value pre-populated.
result: pass

## Summary

total: 8
passed: 7
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

[none — previous gap (test 5) addressed by Plan 05 fix; re-verification in progress]
