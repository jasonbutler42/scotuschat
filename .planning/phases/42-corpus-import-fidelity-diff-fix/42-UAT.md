---
status: testing
phase: 42-corpus-import-fidelity-diff-fix
source: [42-VERIFICATION.md]
started: 2026-07-30T21:15:00Z
updated: 2026-07-30T21:15:00Z
---

## Current Test

number: 1
name: Item 9 (Post-Review Correction) operator disposition
expected: |
  Operator reviews the "Post-Review Correction" section of .planning/CORPUS-FIDELITY-DIFF.md
  and records an explicit approve/adjust/decline disposition for the case-level `advocates`
  dead-key finding (CR-01), matching the treatment already given to the structurally
  identical item 5 (dead `conversation_id` key). The document's own text states this
  classification is "a proposal awaiting explicit operator confirmation, not something
  this correction may decide on its own."
awaiting: user response

## Tests

### 1. Item 9 (Post-Review Correction) operator disposition is still open
expected: Operator reviews and records an explicit disposition for item 9 (the case-level
  `advocates` dead-key finding, found by code review after the original D-05/D-06 batch
  review), matching the treatment already given to structurally identical item 5. Items
  1-8 all have recorded dispositions; item 9 does not yet.
result: [pending]

### 2. Concurrency-safety truth for the --conversation-id scoped import path was never tested
expected: A human judges whether the existing `(source_docket, question_number)` DB UNIQUE
  constraint is sufficient assurance that two concurrent scoped imports of the same
  conversation id never both create an Argument row (Plan 02's must-have truth, declared
  `verification: backstop` / `human_judgment: true` — no concurrency harness exists or was
  built, given this is offline, operator-only tooling per CLAUDE.md).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
