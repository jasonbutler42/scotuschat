---
status: diagnosed
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
  root_cause: "A standalone 'View source PDF' card (D-06/PIPE-22) at lines 529-547 of +page.svelte renders whenever liveJob.spaces_key/pdf_url/original_filename is truthy — it is separate from the ingest step row Phase 23 removed and was never in scope for that removal."
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      line_range: "529-547"
      issue: "Standalone 'View source PDF' card outside the step loop; was not removed in Phase 23 (different from the ingest step row that was removed)"
  missing:
    - "Remove the {#if liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename} block at lines 529-547 from +page.svelte"
  debug_session: ""

- truth: "The old argument metadata form (Case name / Source docket / Argued date) is replaced entirely by ArgumentDetailsCard — no residual static Argument card remains"
  status: failed
  reason: "User reported: There is another card before Argument Details titled 'Argument'. It has the static metadata from before."
  severity: major
  test: 3
  root_cause: "Phase 23 plan 03 Task 2 scoped its removal to the editable metadata form only; a separate pre-existing static 'Argument' preview card (lines 413-515) showing case_name, docket_number, argued_date, status badge, and 'Edit argument metadata' link was not called out for deletion and was left in place, so both now render."
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      line_range: "413-515"
      issue: "Static read-only 'Argument' preview card — pre-existing UI not removed in Phase 23; contains a nested 'Ready to publish' CTA at lines 479-514 that must be preserved"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      line_range: "517-527"
      issue: "ArgumentDetailsCard correctly added, but sits below the residual card rather than replacing it"
  missing:
    - "Remove the static 'Argument' preview card block at lines 413-515 from +page.svelte"
    - "Preserve the 'Ready to publish' CTA (lines 479-514, shown when liveJob.status === 'completed' && argStatus === 'draft') — re-introduce it as a standalone block after ArgumentDetailsCard"
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
  root_cause: "In update_argument_metadata (api/services/admin_arguments.py line 546), source_docket is only written when body.source_docket is not None; when all pills are removed the action sends source_docket: null, Pydantic deserializes as None, the guard skips the UPDATE, and the old value persists — clearing dockets is silently dropped."
  artifacts:
    - path: "api/services/admin_arguments.py"
      line_range: "546-547"
      issue: "Guard `if body.source_docket is not None` conflates 'field not sent' with 'intentionally cleared to null' — clearing all pills sends null which is skipped"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      line_range: "462-465"
      issue: "Action sends source_docket: dockets[0] ?? null — empty pill list sends null, which the service guard treats as 'not provided'"
    - path: "api/schemas/admin_arguments.py"
      line_range: "169-172"
      issue: "MetadataUpdate.source_docket is Optional[str] = None — no way to distinguish 'omitted' from 'explicitly cleared'"
  missing:
    - "Send source_docket: dockets[0] ?? '' (empty string) from the action when pills are empty"
    - "In the service, treat empty string as intentional clear: `if body.source_docket is not None: values_to_set['source_docket'] = body.source_docket or None`"
  debug_session: ""

- truth: "Extracted hints always reflect the raw extraction output and never change when the operator saves a value"
  status: failed
  reason: "User reported: When I change the question number and hit save, the Extract hint changes to reflect the number I entered. The extracted values should never change."
  severity: major
  test: 5
  root_cause: "hints.question_number in load() is sourced from Argument.question_number (the operator-editable DB column), not from any immutable extraction output — the cover extractor never produces a question_number key in cover_metadata, so after a save the reload surfaces the newly persisted operator value as the hint."
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      line_range: "132-136"
      issue: "hints.question_number reads argument.question_number — the same column mutated by saveJobMetadata — making the hint mutable"
    - path: "pipeline/parser/cover_extractor.py"
      line_range: "237-274"
      issue: "extract_cover_metadata produces only case_name, argued_date, primary_docket — no question_number key exists in cover_metadata to use as an immutable hint source"
  missing:
    - "No raw extracted question_number exists anywhere — the cover extractor deliberately omits it (it comes from the --question CLI flag at ingest, not from PDF extraction)"
    - "Fix: set hints.question_number = null always (no immutable extracted value to show); render hint row as italic N/A for question_number"
    - "Optional future: capture the --question CLI flag value into cover_metadata at ingest time so it can serve as a true immutable hint"
  debug_session: ""
