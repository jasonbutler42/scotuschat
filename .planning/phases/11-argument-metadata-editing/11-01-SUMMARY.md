---
phase: 11-argument-metadata-editing
plan: "01"
subsystem: api
tags: [alembic, orm, visibility-gate, published_at, tdd]
status: complete
dependency_graph:
  requires: []
  provides:
    - "Argument.published_at ORM column (nullable DateTime tz-aware)"
    - "Alembic migration 0007 chaining from 0006"
    - "get_cases() public visibility gate: published_at IS NOT NULL"
    - "test_published_gate.py — source-level gate assertion (4 tests)"
  affects:
    - "api/services/cases.py — public /cases/ now hides unpublished arguments"
    - "Plans 11-02 through 11-04 — all read/write published_at column"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN for visibility gate swap"
    - "Alembic sole DDL authority (no create_all)"
    - "AST-based source inspection test (no DB dependency)"
key_files:
  created:
    - "alembic/versions/0007_add_published_at.py"
    - "api/tests/test_published_gate.py"
  modified:
    - "api/models/models.py"
    - "api/services/cases.py"
decisions:
  - "D-05 implemented: published_at is nullable TIMESTAMP WITH TIME ZONE; resolved_at unchanged"
  - "D-06 implemented: get_cases() gate swapped from resolved_at to published_at; confirmed no other service uses resolved_at.isnot as a public filter"
  - "TDD chosen for Task 3: written as failing source-level test first, then implementation"
  - "Test uses AST parse to strip docstrings/comments before asserting filter presence — avoids false positives from comment text"
metrics:
  duration_minutes: 2
  tasks_completed: 3
  files_created: 2
  files_modified: 2
  completed_date: "2026-06-22"
---

# Phase 11 Plan 01: published_at Migration and Visibility Gate Summary

**One-liner:** Alembic migration 0007 adds nullable `published_at` to `arguments`; `get_cases()` gate swapped from `resolved_at` to `published_at` with source-level TDD assertion.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Alembic migration 0007 | 8d89a95 | alembic/versions/0007_add_published_at.py |
| 2 | Add published_at to Argument ORM model | d2ee3ef | api/models/models.py |
| 3 (RED) | Write failing test for published_at gate | 34fe93a | api/tests/test_published_gate.py |
| 3 (GREEN) | Swap get_cases() to published_at filter | 971b968 | api/services/cases.py |

## What Was Built

### Migration 0007 (`alembic/versions/0007_add_published_at.py`)
- Chains from `down_revision = "0006"`
- `upgrade()`: `op.add_column("arguments", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))`
- `downgrade()`: `op.drop_column("arguments", "published_at")`
- No `create_all` call — Alembic is sole DDL authority (CLAUDE.md)

### ORM Model (`api/models/models.py`)
- Added `published_at = Column(DateTime(timezone=True), nullable=True)` to `Argument` class after `resolved_at`
- Clarifying comment: `# Phase 11 (D-05): public visibility gate — replaces resolved_at as the public filter`
- `resolved_at` column and comments updated to clarify it retains pipeline-completion meaning

### Visibility Gate (`api/services/cases.py`)
- Changed `.where(Argument.resolved_at.isnot(None))` to `.where(Argument.published_at.isnot(None))`
- Updated trailing comment to `# hide unpublished arguments (D-06)`
- Confirmed no other `api/services/` file uses `resolved_at.isnot` as a public filter (D-06 full compliance)

### Test (`api/tests/test_published_gate.py`)
- 4 tests, all passing; run without a live database
- Uses AST parsing to extract the `get_cases()` function body, then strips comment/blank lines before asserting
- `test_get_cases_uses_published_at_filter` — asserts `Argument.published_at.isnot` present
- `test_get_cases_does_not_use_resolved_at_filter` — asserts `Argument.resolved_at.isnot` absent
- `test_get_cases_preserves_is_lead_filter` — asserts `is_lead` filter still present
- `test_get_cases_preserves_return_keys` — asserts all 8 return dict keys are present

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Verified

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-11-01 | get_cases() filters `Argument.published_at.isnot(None)` — unpublished args hidden from public | MITIGATED — test_published_gate.py assertions pass |
| T-11-02 | DDL via Alembic migration only; nullable column; no create_all | MITIGATED |
| T-11-SC | No package installs in this plan | ACCEPTED (no action needed) |

## TDD Gate Compliance

- RED gate: `34fe93a test(11-01): add failing test for published_at visibility gate (RED)` — test fails before implementation
- GREEN gate: `971b968 feat(11-01): swap public visibility gate from resolved_at to published_at (GREEN)` — all 4 tests pass

## Self-Check: PASSED

Files exist:
- alembic/versions/0007_add_published_at.py: FOUND
- api/models/models.py (modified): FOUND
- api/services/cases.py (modified): FOUND
- api/tests/test_published_gate.py: FOUND

Commits exist:
- 8d89a95: FOUND (migration 0007)
- d2ee3ef: FOUND (ORM model)
- 34fe93a: FOUND (RED test)
- 971b968: FOUND (GREEN implementation)

Tests: `python -m pytest api/tests/test_published_gate.py -x -q` — 4 passed
