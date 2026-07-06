---
status: complete
phase: 23-shared-argument-details-component
source: [23-01-SUMMARY.md, 23-02-SUMMARY.md, 23-03-SUMMARY.md, 23-04-SUMMARY.md, 23-05-SUMMARY.md]
started: 2026-07-02T00:00:00Z
updated: 2026-07-06T15:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Expanded Parse Stat Card
expected: On the pipeline job detail page (/admin/pipeline/[job_id]), the parse stats section shows 8 fields: Utterances (always a number), then Bench speakers / Advocate speakers / Total speakers / Case name / Argued date / Docket(s) / Question number — each showing a numeric or text value, or italic "N/A" when not available. There are no duplicate Case name or Argued rows reading from the argument record directly.
result: pass

### 2. Source File Row Removed
expected: The pipeline job detail page has no standalone "View Source PDF" card. Instead, a "View source PDF" link appears inside the Ingest step card body (visible when any of spaces_key, pdf_url, or original_filename is present). Clicking it opens the source PDF.
result: issue
reported: "yes, but the link should open in a new tab"
severity: minor
fix: added target="_blank" rel="noopener noreferrer" to anchor — fixed inline

### 3. ArgumentDetailsCard Replaces Old Metadata Form
expected: On a pipeline job detail page that has a linked argument, the "Argument Details" card is visible with no residual static "Argument" preview card above it. A standalone "Ready to publish" CTA appears after the ArgumentDetailsCard when the job is completed and the argument is in draft status.
result: pass

### 4. Docket Pill Add and Remove
expected: Type a docket number (e.g., "21-1271") into the Docket input and press Enter. The docket appears as an editable pill with a × remove button. Clicking × removes it. Entering the same docket a second time is silently ignored (no duplicate pill added).
result: pass

### 4b. Docket Input — Enter-to-add instruction visibility
expected: The instruction to press Enter to add a docket is visible while the operator is typing (not only before they start). A static label "Type a docket number and press Enter to add it." appears above the text input at all times.
result: pass

### 5. Extracted Hints Always Visible
expected: Hint rows are always visible. The question number hint row always shows italic "N/A" regardless of what the operator saves — it never reflects a previously saved value.
result: pass

### 6. Save Argument Details — docket persistence
expected: After editing docket pills and clicking Save, on page reload the saved dockets are pre-populated as pills. Removing all pills and saving persists the cleared state (no pills on reload). Multiple docket pills can be added for consolidated cases (e.g., add "21-1271" and "22-1000" — both appear as pills simultaneously).
result: pass

### 7. Docket pill save and pre-population (re-verify)
expected: Add a docket pill (e.g. "21-1271"), click Save, reload the page — the pill is pre-populated. Then remove that pill, click Save, reload — no pills are shown (cleared state persists).
result: pass

### 8. Clearing all docket pills persists NULL
expected: Remove every docket pill so the docket input is empty, click Save. On reload, the docket field shows no pills and the "Extracted:" hint row still shows the original extracted docket (not the cleared operator value). The DB stores NULL for source_docket.
result: pass

### 9. Question number hint stays italic N/A after save
expected: Enter a question number (e.g. "1"), click Save. On reload, the question number input shows the saved value ("1"), but the "Extracted: N/A" hint row below it still shows italic N/A — it does not change to "1".
result: pass

### 10. Ready-to-publish CTA renders standalone
expected: On a job with status "completed" and a linked argument in "draft" status, a "Ready to publish" CTA block appears immediately after the ArgumentDetailsCard. It is a standalone block — not nested inside any other card. On jobs that don't meet both conditions, it is not visible.
result: pass
note: "All current arguments are in draft status (published/unpublished status transitions not yet implemented), so the conditional was only testable against the draft branch — CTA visibility and placement confirmed correct."

## Summary

total: 10
passed: 9
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Multiple docket pills can be added to an argument (one per docket number in a consolidated case)"
  status: resolved
  resolved_by: "23-07 (commits 872ab771, e14e71da, 91ebc759)"

- truth: "Source PDF link is accessible from the Ingest card (not as a standalone card, but still reachable)"
  status: resolved
  resolved_by: "23-06 (commit 2c3b9c4b) + inline UAT fix (target=_blank)"

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

- truth: "Add a docket pill (e.g. '21-1271'), click Save, reload — pill is pre-populated; remove that pill, click Save, reload — no pills shown"
  status: resolved
  resolved_by: "23-05 (commit 89c04d9a — four coordinated guards: addPill() early-return, disabled input, Enter-key guard, inline hint)"
  debug_session: ".planning/debug/docket-pill-multi-entry-guard.md"
