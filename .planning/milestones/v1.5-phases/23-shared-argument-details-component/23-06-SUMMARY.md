---
phase: 23-shared-argument-details-component
plan: "06"
subsystem: admin-ui
tags: [admin, pipeline, ingest, pdf-link, gap-closure]
status: complete
dependency_graph:
  requires: []
  provides: [PJOB-09]
  affects: [app/src/routes/admin/pipeline/[job_id]/+page.svelte]
tech_stack:
  added: []
  patterns: [svelte-conditional-block, inline-dark-theme-anchor]
key_files:
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
decisions:
  - Link placed inside Ingest step card body (not a standalone card) per operator's UAT report
  - Guard condition checks any of three source-PDF fields (spaces_key, pdf_url, original_filename) for broad compatibility
metrics:
  duration: "4 minutes"
  completed: "2026-07-06"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 23 Plan 06: Add View Source PDF Link to Ingest Step Card — Summary

Restored the "View source PDF" anchor inside the Ingest step card on the job detail admin page, closing UAT Test 2 (major).

## What Was Built

Added a Svelte conditional block immediately after the parse stat `{/if}` (line 605) and before the resolve discrepancy block in `app/src/routes/admin/pipeline/[job_id]/+page.svelte`. The block:

- Guards on `step === 'ingest' && (liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename)`
- Renders an `<a>` element with `href="/admin/pipeline/{liveJob.id}/pdf"` and visible text "View source PDF"
- Styles the anchor with `color: #93c5fd; font-size: 14px; text-decoration: none` to match the existing dark-theme link convention (identical to the "Go to argument editor" anchor near line 460)
- Wraps the anchor in a `<div style="margin-top: 12px;">` so it sits below the card header row at the same vertical rhythm as the parse stats block

No backend changes, no interface changes, no new routes — the PDF-serving route (`/admin/pipeline/[job_id]/pdf/+server.ts`) and all three source-PDF fields on `liveJob` were already in place.

## Root Cause Addressed

Commit `4278c9fb` deleted the standalone "View Source PDF" card per operator request but removed the link entirely instead of moving it into the Ingest step card, leaving the operator with no way to reach the source PDF from the job detail page.

## Verification

- `npx svelte-check --tsconfig ./tsconfig.json --threshold error` → `0 ERRORS` (18 warnings, pre-existing)
- `grep -q "View source PDF"` → found
- `grep -q "step === 'ingest'"` → found
- Commit `2c3b9c4b` contains 10 insertions, 0 deletions

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- File modified: `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — confirmed present
- Commit `2c3b9c4b` — confirmed in git log
- svelte-check: 0 errors
- Required strings present in file: "View source PDF", "step === 'ingest'"
