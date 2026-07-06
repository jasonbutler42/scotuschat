---
status: diagnosed
phase: 23-shared-argument-details-component
source: [23-01-SUMMARY.md, 23-02-SUMMARY.md, 23-03-SUMMARY.md, 23-04-SUMMARY.md, 23-05-SUMMARY.md]
started: 2026-07-02T00:00:00Z
updated: 2026-07-06T14:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Expanded Parse Stat Card
expected: On the pipeline job detail page (/admin/pipeline/[job_id]), the parse stats section shows 8 fields: Utterances (always a number), then Bench speakers / Advocate speakers / Total speakers / Case name / Argued date / Docket(s) / Question number — each showing a numeric or text value, or italic "N/A" when not available. There are no duplicate Case name or Argued rows reading from the argument record directly.
result: pass

### 2. Source File Row Removed
expected: The pipeline job detail page has no "View Source PDF" card or ingest source-file row visible anywhere in the UI.
result: issue
reported: "yes, it's gone but it's not exactly what I wanted. I wanted the separate standalone card with the view source pdf link gone. You've done that, but I still need a link to it. It should be in the Ingest card as a link to the source PDF, not in a standalone card. I'm not sure how the card was written to delete the link entirely, but it should be where I said, in the Ingest card."
severity: major

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
expected: After editing docket pills and clicking Save, on page reload the saved dockets are pre-populated as pills. Removing all pills and saving persists the cleared state (no pills on reload).
result: issue
reported: "I can still only add one docket pill, but the expected behavior is that I can add multiple docket pills to an argument"
severity: major

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
passed: 8
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Multiple docket pills can be added to an argument (one per docket number in a consolidated case)"
  status: failed
  reason: "User reported: I can still only add one docket pill, but the expected behavior is that I can add multiple docket pills to an argument"
  severity: major
  test: 6
  root_cause: "The one-pill cap (addPill() returns if pills.length >= 1; input disabled at same threshold) is intentional and matches the backend — source_docket is a single String(50) column in the DB, the Pydantic schema is Optional[str], and the server action explicitly rejects dockets.length > 1 with a 400. The full stack is single-docket by design; this is a requirements conflict, not a code defect."
  artifacts:
    - path: "app/src/lib/components/ArgumentDetailsCard.svelte"
      issue: "addPill() returns early at pills.length >= 1; input disabled at same threshold — intentional cap matching backend constraint"
      line_hint: "lines 42, 176, 180"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      issue: "saveJobMetadata action rejects dockets.length > 1 with fail(400)"
      line_hint: "lines 374–379"
    - path: "api/models/models.py"
      issue: "source_docket = Column(String(50), nullable=True) — single varchar, not an array"
      line_hint: "line 189"
    - path: "api/schemas/admin_arguments.py"
      issue: "source_docket: Optional[str] = None — single string in PATCH body"
      line_hint: "line 170"
  missing:
    - "DB migration: change source_docket String(50) to source_dockets ARRAY or a separate argument_dockets join table"
    - "SQLAlchemy model: replace source_docket Column(String(50)) with array-capable type"
    - "Pydantic schema: source_dockets: list[str] = [] in PATCH body"
    - "Service layer: write all dockets, not just dockets[0]"
    - "Server action: remove dockets.length > 1 guard; pass full array to PATCH body"
    - "Frontend: remove pills.length >= 1 guard in addPill() and disabled binding; add duplicate-only guard"
    - "Update all query/display paths that read source_docket throughout API and frontend"
  debug_session: "The existing .planning/debug/docket-pill-multi-entry-guard.md already noted this: the one-pill cap and server-side guard were added together in 23-05 (commit ee7fc92a) as a consistent pair. The UAT expectation assumed multi-docket support but the entire stack was deliberately designed for a single source_docket string."

- truth: "Source PDF link is accessible from the Ingest card (not as a standalone card, but still reachable)"
  status: failed
  reason: "User reported: standalone card is gone but the source PDF link was deleted entirely — it should have been moved into the Ingest card as a link"
  severity: major
  test: 2
  root_cause: "Commit 4278c9fb deleted the standalone View Source PDF card without moving the link into the Ingest step card — the UI element was simply removed, but all three source-PDF fields (spaces_key, pdf_url, original_filename) are still present in AdminJobResponse and still arrive in liveJob"
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "Ingest step card has no View source PDF link — the {#if step === 'ingest'} branch with the PDF anchor was deleted with no replacement; unlike the parse step which has a stat block, the ingest card body is empty"
      line_hint: "lines 471–518 (each STEP_ORDER loop, Ingest card header block)"
  missing:
    - "Inside the Ingest step card (after the badge row), add: {#if step === 'ingest' && (liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename)} <a href='/admin/pipeline/{liveJob.id}/pdf'>View source PDF</a> {/if} — no backend changes needed, all three fields already present in Job interface and AdminJobResponse"
  debug_session: "Pure UI omission — the PDF-serving route /admin/pipeline/[job_id]/pdf/+server.ts still exists and all PDF source fields are in the API response; only the anchor element inside the Ingest card is missing"

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
