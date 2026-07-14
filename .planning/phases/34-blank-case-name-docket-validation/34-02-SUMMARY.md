---
phase: 34-blank-case-name-docket-validation
plan: 02
subsystem: admin-ui-server
tags: [sveltekit, validation, recovery, form-actions]
requires: [34-01]
provides:
  - Structured Pydantic location parsing for every Phase 34 action owner
  - Complete attempted-value recovery across required, conflict, malformed, and network failures
affects: [34-03]
tech-stack:
  added: []
  patterns: [unknown-safe detail-loc parsing, presence-preserving failure payloads]
key-files:
  created: []
  modified:
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - api/tests/test_question_number_nullable.py
decisions:
  - Required failures are identified only from terminal detail loc fields
  - Case form raw strings and metadata empty arrays remain present in every failure payload
metrics:
  duration: 8m
  completed: 2026-07-14
status: complete
---

# Phase 34 Plan 02: Structured Action Recovery Summary

Both admin action owners now translate shape-checked Pydantic locations into stable required-field flags while preserving every attempted value, including blank native fields and empty docket arrays.

## Accomplishments

- Added unknown-safe, accumulating `detail[].loc` parsing without coupling required recovery to message text.
- Preserved raw Case form strings through transport and every failure response.
- Added symmetric required-docket recovery to argument and pipeline metadata actions while retaining distinct 409 conflict handling.
- Added source-contract tests covering parser symmetry, location mapping, raw attempts, and message independence.

## Task Commits

1. `f70e47a1` — `feat(34-02): map argument validation locations`
2. `908ee620` — `feat(34-02): mirror pipeline validation recovery`

## Verification

- `.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` — 7 passed.
- `Push-Location app; npm run check; Pop-Location` — 0 errors, 16 pre-existing warnings.

## Decisions Made

- Required error routing trusts only shape-checked terminal field names in Pydantic `loc` arrays.
- Attempted-value objects are spread into every failure class so presence, including `dockets: []`, is never lost.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- All three modified action/test files exist.
- Both task commits are present in git history.
- Focused source-contract tests and Svelte diagnostics pass.
