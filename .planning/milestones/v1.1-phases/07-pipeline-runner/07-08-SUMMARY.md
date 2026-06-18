---
phase: 07-pipeline-runner
plan: "08"
subsystem: pipeline / api
tags: [gap-closure, resolve, visibility-gate, migration]
dependency_graph:
  requires: ["07-07"]
  provides: ["arguments.resolved_at column", "public case visibility gate"]
  affects: ["api/services/cases.py", "api/services/admin_jobs.py", "pipeline/commands/resolve.py", "api/models/models.py"]
tech_stack:
  added: []
  patterns: ["resolved_at visibility gate", "post-session resolved_at stamp"]
key_files:
  created:
    - alembic/versions/0004_add_arguments_resolved_at.py
  modified:
    - api/models/models.py
    - api/services/cases.py
    - api/services/admin_jobs.py
    - pipeline/commands/resolve.py
decisions:
  - "Metadata fabrication is out of scope: the visibility gate (resolved_at IS NOT NULL) is sufficient to close Gap 3. The apolitical/no-derived-insight constraint forbids synthesizing case names at resolve time. Operators who did not supply real metadata at ingest will edit it via Phase 8 (People Editor). The UAT 'real metadata' requirement is satisfied by preventing premature visibility, not by inventing names."
metrics:
  duration_minutes: 8
  completed_date: "2026-06-17"
  tasks_completed: 2
  files_modified: 4
---

# Phase 07 Plan 08: Resolve-Completion Visibility Gate Summary

**One-liner:** Added `arguments.resolved_at` column and visibility gate so cases only appear in `/cases/` after resolve completes — closes UAT Gap 3 (Test 0).

## What Was Built

### Task 1: Migration 0004 + Argument.resolved_at column

- **`alembic/versions/0004_add_arguments_resolved_at.py`**: New Alembic migration (`revision="0004"`, `down_revision="0003"`). `upgrade()` calls `op.add_column("arguments", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))`. `downgrade()` drops the column. No backfill — existing rows stay NULL (hidden) until re-resolved.
- **`api/models/models.py`**: Added `resolved_at = Column(DateTime(timezone=True), nullable=True)` to the `Argument` ORM model after `question_number`. Includes comment: NULL = not yet resolved → hidden from /cases/.

### Task 2: Gate get_cases + stamp resolved_at on completion

- **`api/services/cases.py`**: Added `.where(Argument.resolved_at.isnot(None))` to `get_cases()` select chain. Unresolved arguments (placeholder ingest rows) are now invisible in the public list.
- **`api/services/admin_jobs.py`**: Imported `Argument` and `func` (from sqlalchemy). In `resolve_job` Step 3, before `await db.commit()`, added UPDATE that stamps `resolved_at=func.now()` for `job.argument_id` when it is not None. This covers the operator-confirmed completion path (HIT rows confirmed via Continue Resolve UI).
- **`pipeline/commands/resolve.py`**: Imported `Argument`. Captured `resolved_argument_id = parse_run.argument_id` inside the main session block. In the all-auto-resolved `not discrepancies and args.job_id` post-session block, added `UPDATE Argument SET resolved_at=datetime.now(utc)` alongside the `AdminJob COMPLETED` update, with mandatory `.execution_options(synchronize_session=False)` (Pitfall 3).

## Architecture Notes

Both resolve-completion paths now stamp `resolved_at`:
1. **Operator-confirmed path** (`resolve_job` in `admin_jobs.py`): handles jobs that went through discrepancy review (all rows confirmed via Continue Resolve).
2. **All-auto-resolved fallback** (`resolve.py`): handles jobs where every label had a pre-existing alias — no operator review needed.

The visibility gate in `get_cases()` is a single added `.where()` clause — no schema reshaping, no dict shape change.

## Decision: Metadata Fabrication Out of Scope

The plan's part (d) ("real metadata overwrite") is satisfied by the gate alone, not by synthesizing case names. The apolitical/no-derived-insight hard constraint prohibits fabricating case names at resolve time. Operators who did not supply real metadata at ingest will edit it via Phase 8 (People Editor). The UAT requirement "metadata displayed reflects whatever the operator supplied at ingest" is already true — ingest writes whatever the operator provided, and the gate prevents premature visibility of placeholder rows.

## Deviations from Plan

None — plan executed exactly as written. Part (d) was fully handled by documentation decision (as the plan itself specified — "Document this decision in the SUMMARY").

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. The visibility gate is a read-path filter.

## Self-Check: PASSED

- `alembic/versions/0004_add_arguments_resolved_at.py` exists and parses cleanly
- `api/models/models.py` has `resolved_at` column on `Argument`
- `api/services/cases.py` has `resolved_at.isnot(None)` filter
- `api/services/admin_jobs.py` stamps `resolved_at=func.now()` before commit
- `pipeline/commands/resolve.py` stamps `resolved_at=datetime.now(utc)` with `synchronize_session=False`
- Commits: `43b8f88` (Task 1), `9543a3c` (Task 2)
