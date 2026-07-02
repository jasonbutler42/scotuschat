---
status: complete
phase: 23-shared-argument-details-component
source: [23-01-SUMMARY.md, 23-02-SUMMARY.md, 23-03-SUMMARY.md]
started: 2026-07-02T00:00:00Z
updated: 2026-07-02T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Expanded Parse Stat Card
expected: On the pipeline job detail page (/admin/pipeline/[job_id]), the parse stats section shows 8 fields: Utterances (always a number), then Bench speakers / Advocate speakers / Total speakers / Case name / Argued date / Docket(s) / Question number — each showing a numeric or text value, or italic "N/A" when not available. There are no duplicate Case name or Argued rows reading from the argument record directly.
result: pass

### 2. Source File Row Removed
expected: The pipeline job detail page has no "Source file" or ingest source-file row visible anywhere in the UI (it has been removed entirely).
result: issue
reported: "I still see a 'View Source PDF' card with a link"
severity: major

### 3. ArgumentDetailsCard Replaces Old Metadata Form
expected: On a pipeline job detail page that has a linked argument, an "Argument Details" card is visible with a dark card background. It has three input areas — Docket(s) (with a text input for entering dockets), Question number (text input), and Argued date (text input). The old form with Case name / Source docket / Argued date fields is gone.
result: issue
reported: "The Argument Details card shows and everything in it shows correctly. However, there is another card before Argument Details titled 'Argument'. It has the static metadata from before."
severity: major

### 4. Docket Pill Add and Remove
expected: Type a docket number (e.g., "21-1271") into the Docket input and press Enter. The docket appears as an editable pill with a × remove button. Clicking × removes it. Entering the same docket a second time is silently ignored (no duplicate pill added).
result: pass

### 4b. Docket Input — Enter-to-add instruction visibility
expected: The instruction to press Enter to add a docket is visible while the operator is typing (not only before they start). Instruction text should appear above the input field, not as placeholder text that disappears on focus.
result: issue
reported: "The prompt (Add docket and press Enter...) is helpful if you haven't started typing but because it doesn't work without hitting Enter, you lose the functionality if you've started typing. Maybe put the instructions above the text field?"
severity: minor

### 5. Extracted Hints Always Visible
expected: Below the Docket input, an "Extracted:" prefix row shows any extracted dockets as small read-only pills (no × button). Below Question number and Argued date inputs, "Extracted: {value}" text is shown, or italic "Extracted: N/A" when the extraction produced nothing. These hint rows are always visible — they do not disappear when the operator has filled in the field above them.
result: pass

### 6. Save Argument Details
expected: After editing docket(s), question number, or argued date in the ArgumentDetailsCard and clicking Save: the button label changes to "Saving…" with reduced opacity while the request is in flight, then shows "Saved." in green on success. On page reload, the previously saved values are pre-populated in the form.
result: issue
reported: "I added one docket and deleted another, changed the date, changed the question number, hit save and the date and question number saved fine but the docket pills didn't."
severity: major

## Summary

total: 6
passed: 3
issues: 4
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The pipeline job detail page has no Source file or ingest source-file row visible anywhere in the UI"
  status: failed
  reason: "User reported: I still see a 'View Source PDF' card with a link"
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "The old argument metadata form (Case name / Source docket / Argued date) is replaced entirely by ArgumentDetailsCard — no residual static Argument card remains"
  status: failed
  reason: "User reported: There is another card before Argument Details titled 'Argument'. It has the static metadata from before."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "The instruction to press Enter to add a docket is visible while the operator is typing, not only as placeholder text that disappears on focus"
  status: failed
  reason: "User reported: The prompt (Add docket and press Enter...) is helpful if you haven't started typing but because it doesn't work without hitting Enter, you lose the functionality if you've started typing. Maybe put the instructions above the text field?"
  severity: minor
  test: 4b
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Docket pill changes (adds and removes) are persisted on save and pre-populated on reload"
  status: failed
  reason: "User reported: I added one docket and deleted another, changed the date, changed the question number, hit save and the date and question number saved fine but the docket pills didn't."
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
