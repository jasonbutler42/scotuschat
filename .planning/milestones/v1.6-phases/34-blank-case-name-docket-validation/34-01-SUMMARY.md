---
phase: 34-blank-case-name-docket-validation
plan: 01
subsystem: api
tags: [pydantic, fastapi, validation, patch]
requires: []
provides:
  - Required case and docket validation at the Pydantic request boundary
  - Deterministic normalized source-docket collection precedence
affects: [34-02]
tech-stack:
  added: []
  patterns: [Pydantic field validators preserving model_fields_set omission semantics]
key-files:
  created: []
  modified:
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
decisions:
  - source_dockets is authoritative when supplied and its first normalized entry is canonical
  - required PATCH fields retain Optional defaults so omission remains distinct from explicit null
metrics:
  duration: 10m
  completed: 2026-07-14
status: complete
---

# Phase 34 Plan 01: Backend Required Metadata Contract Summary

Pydantic request validation now rejects explicit null and blank required case/docket values while preserving PATCH omission, with normalized docket arrays flowing directly into canonical service writes.

## Accomplishments

- Added Unicode-aware outer-whitespace trimming and nonblank enforcement for required scalar fields without changing public schema allow-lists.
- Normalized docket arrays by dropping blanks and de-duplicating in first-seen order, rejecting collections with no valid docket.
- Removed duplicate service normalization and made the validated array authoritative over a simultaneously supplied singular docket.
- Proved invalid direct requests return standard loc-addressable FastAPI 422 responses before service invocation.

## Task Commits

1. `33733d9f` — `feat(34-01): validate required argument metadata`
2. `d2995e53` — `feat(34-01): consume canonical docket metadata`

## Verification

- `.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py -q`
- Result: 65 passed, 24 skipped.

## Decisions Made

- An explicitly supplied `source_dockets` array wins over `source_docket`; its first normalized entry becomes the canonical docket.
- Optional defaults remain intact so omitted required fields stay absent from `model_fields_set`, while explicit null is rejected.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- All four modified implementation/test files exist.
- Both task commits are present in git history.
- Targeted schema, service, and route tests pass.
