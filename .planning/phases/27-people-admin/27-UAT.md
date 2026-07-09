---
status: partial
phase: 27-people-admin
source: [27-VERIFICATION.md]
started: 2026-07-09T15:10:00Z
updated: 2026-07-09T15:30:00Z
---

## Current Test

[testing paused — 5 items outstanding]

## Tests

### 1. CR-01 data-preservation round-trip
expected: Open an existing Justice with tenure rows and a birthdate, click "Advocate", click "Save Person", reload the page. Tenure rows and birthdate are unchanged after reload — not wiped.
result: issue
reported: "there's some issue that I can't figure out. The site is running crazy slow just navigating. Like, 3-5 seconds between click and navigation. I'm also getting console errors: repeated 'updated at' effect reruns at +page.svelte:132:42, :133:14, :134:44/142:9 (Array.map at $effect), culminating in 'Uncaught (in promise) Svelte error: effect_update_depth_exceeded — Maximum update depth exceeded. This typically indicates that an effect reads and writes the same piece of state.'"
severity: blocker

### 2. CR-02 data-preservation round-trip
expected: Merge person A into person B (redirects to /admin/people/{B}). On that page, click "Save Person" without further edits. Reload. B's tenure rows after reload are B's own — not A's stale pre-merge tenureRows array.
result: blocked
blocked_by: other
reason: "I can't do any testing with this blocking error (see Test 1 — effect_update_depth_exceeded loop makes the page unusable)"

### 3. Bench/Advocate slide-reveal animation re-check
expected: Toggle Bench↔Advocate on /admin/people/{id} and observe the transition. Slide transition still animates smoothly (not fade/snap); DESIGN-SYSTEM.md token compliance; in-progress tenure edits still preserved across a Bench→Advocate→Bench toggle. (DOM changed slightly by the CR-01/CR-02 fix — worth a fresh look.)
result: blocked
blocked_by: other
reason: "I can't do any testing with this blocking error (see Test 1)"

### 4. Column spacing visual re-check (27-07 fix, carried forward)
expected: On /admin/people, view both the Bench tab and Advocate tab middle columns. Clear horizontal gutter between the two middle columns on each tab.
result: blocked
blocked_by: other
reason: "I can't do any testing with this blocking error (see Test 1)"

### 5. President's Party dropdown round-trip (27-09 fix, carried forward)
expected: Select a party from the dropdown, save, reload; separately confirm a legacy out-of-list value still displays selected. Selection persists; legacy values preserved.
result: blocked
blocked_by: other
reason: "I can't do any testing with this blocking error (see Test 1)"

### 6. Create-person name-parts persistence, full click-through (27-08 fix, carried forward)
expected: On /admin/people/new, fill in Full Name and all four name-part fields, submit, reopen the created person. All four name-part fields display the submitted values.
result: blocked
blocked_by: other
reason: "I can't do any testing with this blocking error (see Test 1)"

## Summary

total: 6
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 5

## Gaps

- truth: "Open an existing Justice with tenure rows and a birthdate, click Advocate, click Save Person, reload the page — tenure rows and birthdate are unchanged after reload, not wiped."
  status: failed
  reason: "User reported: site running crazy slow just navigating (3-5 seconds between click and navigation), plus console errors — repeated 'updated at' effect reruns at +page.svelte:132:42, :133:14, :134:44/142:9 (Array.map at $effect), culminating in 'Uncaught (in promise) Svelte error: effect_update_depth_exceeded — Maximum update depth exceeded. This typically indicates that an effect reads and writes the same piece of state.'"
  severity: blocker
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
