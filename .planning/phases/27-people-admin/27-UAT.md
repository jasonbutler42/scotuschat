---
status: testing
phase: 27-people-admin
source: [27-VERIFICATION.md]
started: 2026-07-09T19:05:00Z
updated: 2026-07-09T19:05:00Z
---

## Current Test

number: 1
name: Person-detail page loads without the effect_update_depth_exceeded loop (smoke test, unblocks everything else below)
expected: |
  Opening /admin/people/{id} for a Justice with >=1 tenure row shows no repeated "updated at" console spam, no thrown "Uncaught (in promise) Svelte error: effect_update_depth_exceeded", and normal click-to-navigation responsiveness (not the previously-reported 3-5s lag).
awaiting: user response

## Tests

### 1. Smoke test — effect loop fixed
expected: Opening /admin/people/{id} for a Justice with >=1 tenure row shows no repeated "updated at" console spam, no thrown "Uncaught (in promise) Svelte error: effect_update_depth_exceeded", and normal click-to-navigation responsiveness (not the previously-reported 3-5s lag).
result: [pending]

### 2. CR-01 data-preservation round-trip
expected: Open an existing Justice with tenure rows and a birthdate, click "Advocate", click "Save Person", reload the page. Tenure rows and birthdate are unchanged after reload — not wiped.
result: [pending]

### 3. CR-02 data-preservation round-trip
expected: Merge person A into person B (redirects to /admin/people/{B}). On that page, click "Save Person" without further edits. Reload. B's tenure rows after reload are B's own — not A's stale pre-merge tenureRows array.
result: [pending]

### 4. Bench/Advocate slide-reveal animation re-check
expected: Toggle Bench↔Advocate on /admin/people/{id} and observe the transition. Slide transition still animates smoothly (not fade/snap); DESIGN-SYSTEM.md token compliance; in-progress tenure edits still preserved across a Bench→Advocate→Bench toggle.
result: [pending]

### 5. Column spacing visual re-check (27-07 fix, carried forward)
expected: On /admin/people, view both the Bench tab and Advocate tab middle columns. Clear horizontal gutter between the two middle columns on each tab.
result: [pending]

### 6. President's Party dropdown round-trip (27-09 fix, carried forward)
expected: Select a party from the dropdown, save, reload; separately confirm a legacy out-of-list value still displays selected. Selection persists; legacy values preserved.
result: [pending]

### 7. Create-person name-parts persistence, full click-through (27-08 fix, carried forward)
expected: On /admin/people/new, fill in Full Name and all four name-part fields, submit, reopen the created person. All four name-part fields display the submitted values.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
