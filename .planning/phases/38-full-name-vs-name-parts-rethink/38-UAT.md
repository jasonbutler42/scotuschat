---
status: testing
phase: 38-full-name-vs-name-parts-rethink
source: [38-VERIFICATION.md]
started: 2026-07-27T17:45:00Z
updated: 2026-07-27T17:45:00Z
---

## Current Test

number: 1
name: Live-updating generated Full Name preview
expected: |
  Open the standalone create form and the person edit form; type into First/Middle/Last/Suffix
  and confirm the read-only Full Name <output> updates live, shows "Generated from name parts.",
  and cannot be typed into directly. Full Name preview matches the canonical
  First Middle Last, Suffix format live as parts are typed; no input control exists for it.
awaiting: user response

## Tests

### 1. Live-updating generated Full Name preview
expected: Full Name preview matches the canonical First Middle Last, Suffix format live as parts are typed; no input control exists for it.
result: [pending]

### 2. First-only/last-only save success, blank-both error copy + preserved attempted values + focus-on-error
expected: |
  Submit the create/edit form with only a First Name (no Last), then only a Last Name (no First);
  confirm save succeeds and no "Enter at least a first or last name." error appears; then submit
  with both blank and confirm the error appears, attempted values are preserved, and focus moves
  to First Name.
result: [pending]

### 3. Per-part stacked provenance rendering and copy-only-interpreted-value behavior
expected: |
  Open an ambiguous legacy person record (one migration 0022 flagged name_needs_review=true) in
  the edit form; confirm each of First/Middle/Last/Suffix shows the stacked
  "Extracted: {value} / {Band} confidence · Raw: {raw}" hint (or the disabled N/A state for a
  still-blank field) at both wide and narrow viewport widths, and that clicking the copy
  affordance copies only the interpreted value. Layout remains usable/readable at narrow widths
  per 38-FIGMA.md.
result: [pending]

### 4. People directory "Name review" pill filter/tab-URL preservation and empty state
expected: |
  On the People directory, click the "Name review" pill/indicator; confirm it filters to only
  name_needs_review=true rows while preserving the active tab in the URL, and that the empty
  state (when no rows match) shows the exact locked copy "No people need name review" /
  "Ambiguous legacy names will appear here for review."
result: [pending]

### 5. Docket Pill provenance states against Figma reference
expected: |
  Exercise DocketPillInput's approved provenance states (editable/read-only, single/multiple
  pills, mixed confidence within a group, long raw text wrapping, remove-in-edit-mode-only)
  against the Figma component (38-FIGMA.md node 3:140 / review sheet 3:2) at narrow and wide
  widths. All approved visual states match the Figma reference; remove control only appears in
  editable mode; long raw text wraps without truncation or overflow.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
