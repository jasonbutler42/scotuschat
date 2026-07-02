---
status: complete
phase: 18-people-schema-editor
source: 18-01-SUMMARY.md, 18-02-SUMMARY.md, 18-03-SUMMARY.md
started: 2026-06-29T00:00:00Z
updated: 2026-06-29T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Justice Badge in Directory
expected: In the admin people directory (/admin/people), any person with is_justice=true shows a blue "Justice" badge next to their name in the table. The badge is styled with accent color #93c5fd (light blue), a subtle fill background, border-radius 4px, and is visually distinct from the yellow missing-fields warning chip.
result: pass

### 2. Is Justice Checkbox in Editor
expected: Opening any person's editor (/admin/people/[id]) shows a visible "Is Justice" checkbox in the Basic Info section, positioned immediately after the section heading and before the Full Name field. The checkbox reflects the person's actual is_justice value on load (checked for justices, unchecked for non-justices).
result: pass

### 3. Bench Sections Visible When Justice Checked
expected: When the Is Justice checkbox is checked on a person's editor page, the Role select, Court Tenure card, and Appointment card are all visible on the page.
result: pass

### 4. Bench Sections Hide When Justice Unchecked
expected: When the Is Justice checkbox is unchecked, the Role select, Court Tenure card, and Appointment card all disappear from the page immediately — no save required. Toggling the checkbox in real-time shows/hides these sections.
result: pass

### 5. Save Justice Status
expected: Checking the Is Justice box on a non-justice person and clicking Save marks them as a justice. After reloading the editor, the checkbox is still checked. The person now shows the Justice badge in the directory listing.
result: pass

### 6. Uncheck Justice Preserves Tenures and Role
expected: Unchecking the Is Justice box on a justice person and clicking Save marks them as not a justice — but does NOT delete any court tenure rows or clear the role. The Justice badge disappears from the directory listing for that person.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
