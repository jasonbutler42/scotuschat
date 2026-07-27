---
status: diagnosed
phase: 38-full-name-vs-name-parts-rethink
source: [38-VERIFICATION.md]
started: 2026-07-27T17:45:00Z
updated: 2026-07-27T19:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Live-updating generated Full Name preview
expected: Full Name preview matches the canonical First Middle Last, Suffix format live as parts are typed; no input control exists for it.
result: pass

### 2. First-only/last-only save success, blank-both error copy + preserved attempted values + focus-on-error
expected: |
  Submit the create/edit form with only a First Name (no Last), then only a Last Name (no First);
  confirm save succeeds and no "Enter at least a first or last name." error appears; then submit
  with both blank and confirm the error appears, attempted values are preserved, and focus moves
  to First Name.
result: pass

### 3. Per-part stacked provenance rendering and copy-only-interpreted-value behavior
expected: |
  Open an ambiguous legacy person record (one migration 0022 flagged name_needs_review=true) in
  the edit form; confirm each of First/Middle/Last/Suffix shows the stacked
  "Extracted: {value} / {Band} confidence · Raw: {raw}" hint (or the disabled N/A state for a
  still-blank field) at both wide and narrow viewport widths, and that clicking the copy
  affordance copies only the interpreted value. Layout remains usable/readable at narrow widths
  per 38-FIGMA.md.
result: pass

### 4. People directory "Name review" pill filter/tab-URL preservation and empty state
expected: |
  On the People directory, click the "Name review" pill/indicator; confirm it filters to only
  name_needs_review=true rows while preserving the active tab in the URL, and that the empty
  state (when no rows match) shows the exact locked copy "No people need name review" /
  "Ambiguous legacy names will appear here for review."
result: pass

### 5. Docket Pill provenance states against Figma reference
expected: |
  Exercise DocketPillInput's approved provenance states (editable/read-only, single/multiple
  pills, mixed confidence within a group, long raw text wrapping, remove-in-edit-mode-only)
  against the Figma component (38-FIGMA.md node 3:140 / review sheet 3:2) at narrow and wide
  widths. All approved visual states match the Figma reference; remove control only appears in
  editable mode; long raw text wraps without truncation or overflow.
result: pass

### 6. Docket Pill value with unusual characters/length used as pipeline ingest filename
expected: |
  A docket "number" value entered via DocketPillInput should either be constrained to
  valid-docket-shaped input, or safely sanitized before being used to construct a
  filesystem path during pipeline ingest — never passed raw into a file path.
result: issue
reported: |
  Entered a free-text string (containing a double-quote character) as a docket "number"
  on the Pipeline Runner's new-job form, left Question at its default, and ran it. The job
  errored: [Errno 22] Invalid argument: 'data\pdfs\I wonder if there is a limit to how long
  the docket "numbers" can be-q1.pdf'
severity: blocker

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-38-6
  truth: "A docket value entered via DocketPillInput should either be constrained to valid-docket-shaped input, or safely sanitized before being used to construct a filesystem path during pipeline ingest."
  status: failed
  reason: "User reported: docket value containing a double-quote character crashed pipeline ingest with [Errno 22] Invalid argument when used raw as a PDF filename component in pipeline/commands/ingest.py:291 (f\"{primary_docket}-q{args.question}.pdf\")"
  severity: blocker
  test: 6
  root_cause: "No validation/sanitization exists at any hop from DocketPillInput.svelte through +page.server.ts through api/routers/admin.py's _normalize_dockets/create_job through to pipeline/commands/ingest.py:291's f-string path construction. _normalize_dockets only rejects values starting with '-' (an argv-flag-injection guard for T-24-08, unrelated to filesystem safety). Confirmed exploitable beyond a crash: a docket value containing '../' segments or an absolute path/drive letter causes Path('data/pdfs') / docket to resolve outside the intended directory (verified via direct pathlib test) -- an authenticated-admin arbitrary-file-write primitive, not just an illegal-character crash."
  artifacts:
    - path: "pipeline/commands/ingest.py:291,299-301"
      issue: "pdf_filename built via unsanitized f-string interpolation of primary_docket; first and only point where the value touches a filesystem path"
    - path: "api/routers/admin.py:126-164,214"
      issue: "_normalize_dockets/create_job's only existing guard (leading '-' rejection) is scoped to argv-injection, not path-safety; primary_docket/source_dockets has no Pydantic length/pattern constraint"
    - path: "app/src/lib/components/DocketPillInput.svelte:61-68"
      issue: "addPill only trims and dedupes; no length cap or character allow-list at the original entry point"
    - path: "app/src/routes/admin/pipeline/+page.server.ts:40-51"
      issue: "passthrough with trim/dedupe only, no validation"
  missing:
    - "Docket-shape allow-list/length cap at the API boundary (Pydantic validator on create_job's primary_docket/source_dockets, or added to _normalize_dockets), matching the existing 422-validation-error pattern used elsewhere (cf. ResolveRowUpdate.title's Field(max_length=500))"
    - "Independent hardening of ingest.py's filename construction itself so a docket value can never produce a path component containing '/', '\\', '..', or resolve as absolute -- defense in depth, mirroring the existing two-layer _validate_pdf_url (API) + _validate_url (pipeline) SSRF pattern"
    - "Client-side UX feedback in DocketPillInput for immediate operator feedback (secondary to the two backend fixes above)"
  debug_session: .planning/debug/docket-filename-injection.md
