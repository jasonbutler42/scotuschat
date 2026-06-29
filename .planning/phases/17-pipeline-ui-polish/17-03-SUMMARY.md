---
phase: 17-pipeline-ui-polish
plan: "03"
subsystem: ui
tags: [svelte, pipeline, admin, pdf]

requires:
  - phase: 17-pipeline-ui-polish/17-01
    provides: FastAPI proxy endpoint GET /admin/pipeline/{id}/pdf that handles disk-backed jobs via pdf_path
  - phase: 17-pipeline-ui-polish/17-02
    provides: Frontend pipeline job detail page structure including the "View source PDF" card

provides:
  - "View source PDF" card is now visible for local file-upload jobs (original_filename set, spaces_key and pdf_url null)

affects: [17-UAT, pipeline-job-detail]

tech-stack:
  added: []
  patterns:
    - "Three-way OR gate for PDF source visibility: spaces_key || pdf_url || original_filename"

key-files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

key-decisions:
  - "No backend change needed — FastAPI proxy at GET /admin/pipeline/{id}/pdf already reads pdf_path from PipelineRun ingest row for disk-backed jobs; only the template gate needed fixing"

patterns-established:
  - "PDF card visibility pattern: check all three storage origins (Spaces key, external URL, local filename) — never rely on a subset"

requirements-completed:
  - PIPE-22

coverage:
  - id: D1
    description: "View source PDF card renders for local file-upload jobs where only original_filename is set"
    requirement: PIPE-22
    verification:
      - kind: manual_procedural
        ref: "UAT test 5 — open a local-upload job detail page; card visible between Argument card and step cards"
        status: unknown
    human_judgment: true
    rationale: "Requires a running app with a local-upload job in the database to visually confirm card presence; no automated UI test exists for this specific condition"
  - id: D2
    description: "View source PDF card remains absent when spaces_key, pdf_url, and original_filename are all null"
    requirement: PIPE-22
    verification:
      - kind: manual_procedural
        ref: "UAT test 7 — open a job with no PDF source; confirm card is absent"
        status: unknown
    human_judgment: true
    rationale: "Requires a running app with a no-PDF job to visually confirm card absence"

duration: 5min
completed: 2026-06-29
status: complete
---

# Phase 17 Plan 03: PDF Card Gate Fix Summary

**Extended {#if} gate for the 'View source PDF' card to include `original_filename`, unblocking UAT test 5 for local file-upload jobs**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-29T15:10:00Z
- **Completed:** 2026-06-29T15:15:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Single-line template fix closes the UAT test 5 gap: local file-upload jobs now show the "View source PDF" card
- No backend changes required — the FastAPI proxy at `GET /admin/pipeline/{id}/pdf` already branches on `spaces_key` first and falls back to `pdf_path` on disk for local jobs
- No regressions to Spaces-backed (`spaces_key`) or URL-backed (`pdf_url`) job display

## Task Commits

1. **Task 1: Extend PDF card visibility condition to include original_filename** - `72b3bd33` (fix)

## Files Created/Modified

- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Changed `{#if spaces_key || pdf_url}` to `{#if spaces_key || pdf_url || original_filename}` at line 471

## Decisions Made

None — followed plan as specified. The FastAPI proxy already handled the disk case; only the template gate needed the third OR clause.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- UAT test 5 (PDF card visible for local upload) is unblocked — can now be verified against a running instance
- UAT test 7 (card absent when all PDF fields null) can also be re-verified
- Phase 17 plans 01–03 are all complete; phase is ready for final UAT sign-off

---
*Phase: 17-pipeline-ui-polish*
*Completed: 2026-06-29*
