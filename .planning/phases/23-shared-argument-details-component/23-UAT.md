---
status: testing
phase: 23-shared-argument-details-component
source: [23-01-SUMMARY.md, 23-02-SUMMARY.md, 23-03-SUMMARY.md, 23-04-SUMMARY.md]
started: 2026-07-02T00:00:00Z
updated: 2026-07-03T00:00:00Z
---

## Current Test

number: 7
name: Docket pill save and pre-population
expected: |
  Add a docket pill, save, reload — pill is pre-populated. Remove all pills, save, reload — no pills shown.
awaiting: user response

## Tests

### 1. Expanded Parse Stat Card
expected: On the pipeline job detail page (/admin/pipeline/[job_id]), the parse stats section shows 8 fields: Utterances (always a number), then Bench speakers / Advocate speakers / Total speakers / Case name / Argued date / Docket(s) / Question number — each showing a numeric or text value, or italic "N/A" when not available. There are no duplicate Case name or Argued rows reading from the argument record directly.
result: pass

### 2. Source File Row Removed
expected: The pipeline job detail page has no "View Source PDF" card or ingest source-file row visible anywhere in the UI.
result: resolved
resolved_by: 23-04 (commit 4278c9fb — removed standalone View source PDF card block)

### 3. ArgumentDetailsCard Replaces Old Metadata Form
expected: On a pipeline job detail page that has a linked argument, the "Argument Details" card is visible with no residual static "Argument" preview card above it. A standalone "Ready to publish" CTA appears after the ArgumentDetailsCard when the job is completed and the argument is in draft status.
result: resolved
resolved_by: 23-04 (commit 4278c9fb — removed orphaned Argument preview card; standalone CTA added)

### 4. Docket Pill Add and Remove
expected: Type a docket number (e.g., "21-1271") into the Docket input and press Enter. The docket appears as an editable pill with a × remove button. Clicking × removes it. Entering the same docket a second time is silently ignored (no duplicate pill added).
result: pass

### 4b. Docket Input — Enter-to-add instruction visibility
expected: The instruction to press Enter to add a docket is visible while the operator is typing (not only before they start). A static label "Type a docket number and press Enter to add it." appears above the text input at all times.
result: resolved
resolved_by: 23-04 (commit 5ac10e1a — promoted placeholder to always-visible static label above input)

### 5. Extracted Hints Always Visible
expected: Hint rows are always visible. The question number hint row always shows italic "N/A" regardless of what the operator saves — it never reflects a previously saved value.
result: resolved
resolved_by: 23-04 (commit a1f41371 — hints.question_number frozen to null literal in load())

### 6. Save Argument Details — docket persistence
expected: After editing docket pills and clicking Save, on page reload the saved dockets are pre-populated as pills. Removing all pills and saving persists the cleared state (no pills on reload).
result: resolved
resolved_by: 23-04 (commits d8a657cb + a1f41371 — empty-string sentinel chain: frontend sends '' → service converts to None → DB stores NULL)

### 7. Docket pill save and pre-population (re-verify)
expected: Add a docket pill (e.g. "21-1271"), click Save, reload the page — the pill is pre-populated. Then remove that pill, click Save, reload — no pills are shown (cleared state persists).
result: pending

### 8. Clearing all docket pills persists NULL
expected: Remove every docket pill so the docket input is empty, click Save. On reload, the docket field shows no pills and the "Extracted:" hint row still shows the original extracted docket (not the cleared operator value). The DB stores NULL for source_docket.
result: pending

### 9. Question number hint stays italic N/A after save
expected: Enter a question number (e.g. "1"), click Save. On reload, the question number input shows the saved value ("1"), but the "Extracted: N/A" hint row below it still shows italic N/A — it does not change to "1".
result: pending

### 10. Ready-to-publish CTA renders standalone
expected: On a job with status "completed" and a linked argument in "draft" status, a "Ready to publish" CTA block appears immediately after the ArgumentDetailsCard. It is a standalone block — not nested inside any other card. On jobs that don't meet both conditions, it is not visible.
result: pending

## Summary

total: 10
passed: 4
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

- truth: "The pipeline job detail page has no Source file or ingest source-file row visible anywhere in the UI"
  status: resolved
  resolved_by: "23-04 (commit 4278c9fb)"

- truth: "The old argument metadata form is replaced entirely by ArgumentDetailsCard — no residual static Argument card remains"
  status: resolved
  resolved_by: "23-04 (commit 4278c9fb)"

- truth: "The instruction to press Enter to add a docket is visible while the operator is typing, not only as placeholder text"
  status: resolved
  resolved_by: "23-04 (commit 5ac10e1a)"

- truth: "Docket pill changes (adds and removes) are persisted on save and pre-populated on reload"
  status: resolved
  resolved_by: "23-04 (commits d8a657cb + a1f41371)"

- truth: "Extracted hints always reflect the raw extraction output and never change when the operator saves a value"
  status: resolved
  resolved_by: "23-04 (commit a1f41371)"
