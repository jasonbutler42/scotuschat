---
status: complete
phase: 09-people-data-model-migration
source: [09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md]
started: 2026-06-19T00:00:00Z
updated: 2026-06-22T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Name-parts grid visible in person edit form
expected: Navigate to /admin/people/[id] for any person. In the Basic Info section, below the Full Name field and above the Role select, you should see four labeled text inputs — "First name", "Middle name", "Last name", "Suffix" — arranged in a horizontal grid (4 columns on desktop).
result: pass

### 2. Appointment section visible in person edit form
expected: On the same person edit page, scroll below the Court Tenure section. A 4th section labeled "Appointment" should appear with an "Appointed by" text input and an "Appointing president's party" select dropdown containing options: — No party —, Democratic, Democratic-Republican, Federalist, Independent, Republican, Whig.
result: pass

### 3. Name parts save and reload
expected: On a person edit page, fill in First name = "Amy", Middle name = "Coney", Last name = "Barrett", Suffix blank. Click Save. Page reloads — the four inputs should pre-fill with those exact values.
result: pass

### 4. Full-name derivation fires when first + last are both set
expected: After saving with First name = "Amy" and Last name = "Barrett" (both filled), the page title / Full name field should update to show "Amy Coney Barrett" (or "Amy Barrett" if middle was left blank). Derivation fires only when both first AND last are provided.
result: pass

### 5. Partial save preserves existing full_name
expected: On a person who already has a full_name set, clear the First name field only (leave Last name blank/empty) and click Save. The existing full_name should remain unchanged — the derivation guard requires both first AND last to be non-empty before overwriting full_name.
result: pass

### 6. Appointment fields save and reload
expected: Fill "Appointed by" with "Ronald Reagan" and select "Republican" from the party dropdown. Click Save. Page reloads — "Appointed by" input shows "Ronald Reagan" and the party select shows "Republican" as selected.
result: pass

### 7. Role preserved when "Add new role" sentinel not completed
expected: On the person edit form, choose "Add new role" from the Role dropdown, then immediately click Save without completing the new-role form. The person's existing role should NOT be wiped — either the save is rejected with an error message, or the original role is preserved. The sentinel value should not silently null out the role.
result: pass

### 8. People directory sorted by last name
expected: Navigate to /admin/people. People who have a last_name set should appear sorted alphabetically by last name. People with no last_name (pre-Phase-9 records) should appear at the bottom of the list, not interspersed with named records.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
