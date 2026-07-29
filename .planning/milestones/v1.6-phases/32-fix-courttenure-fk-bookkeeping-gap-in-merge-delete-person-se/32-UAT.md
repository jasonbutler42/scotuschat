---
status: complete
phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
source: [32-VERIFICATION.md]
started: 2026-07-13T20:00:00Z
updated: 2026-07-13T20:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Manual UI exercise of merge/delete on a Justice with tenure rows
expected: Delete button disabled with tenure rows present; merge-preview breakdown renders the tenure count; after merge, no IntegrityError, and the target person's tenure history includes the transferred rows.
result: pass

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

Note: VERIFICATION.md originally listed a second item (live-DB pass of the 3 new CourtTenure
tests). That item was resolved by the orchestrator without human action — see the "Behavioral
Spot-Checks" addendum and Human Verification #1 in `32-VERIFICATION.md` for the passing evidence
(`28 passed, 409 deselected`, including all 3 new tests). Only the manual UI exercise remains.
