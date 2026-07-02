---
phase: 22-schema-foundations
plan: "01"
subsystem: database
tags: [migration, orm, schema, enum, audit-log]
status: complete

dependency_graph:
  requires:
    - "alembic/versions/0011_add_source_docket_cover_metadata.py (down_revision chain)"
  provides:
    - "argument_status PG enum value: unpublished"
    - "argument_status_log table (id, argument_id, status, created_at)"
    - "ArgumentStatusEnum.UNPUBLISHED ORM value"
    - "ArgumentStatusLog ORM model"
  affects:
    - "Phases 26 and 27 (argument status lifecycle UI and status timeline)"

tech_stack:
  added: []
  patterns:
    - "COMMIT before ALTER TYPE ADD VALUE (migration 0008 discipline, reused)"
    - "op.create_table after enum expansion (D-04 ordering constraint)"
    - "Single set-based INSERT...SELECT backfill (T-22-01 mitigation)"
    - "SAEnum bound to existing PG type via name='argument_status'"

key_files:
  created:
    - alembic/versions/0012_unpublished_enum_and_status_log.py
  modified:
    - api/models/models.py
    - tests/test_schema.py

decisions:
  - "Backfill uses status::argument_status cast from each argument's current status — never the literal 'created' (T-22-02 mitigation)"
  - "downgrade drops argument_status_log table only; unpublished enum value intentionally retained (PG cannot remove enum values)"
  - "ArgumentStatusLog has no previous_status, notes, or triggered_by (D-06 minimal schema)"
  - "COALESCE(resolved_at, CURRENT_TIMESTAMP) used for backfill timestamp to reflect pipeline completion time when available"

metrics:
  duration_minutes: 2
  completed_date: "2026-07-02"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 2
---

# Phase 22 Plan 01: Schema Foundations (Migration 0012) Summary

**One-liner:** Migration 0012 adds `unpublished` to the `argument_status` PG enum, creates the `argument_status_log` audit table, and backfills one row per argument using its current status — with matching ORM changes and schema test registration.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create migration 0012 (unpublished enum + argument_status_log + backfill) | 1d0b021c | alembic/versions/0012_unpublished_enum_and_status_log.py |
| 2 | Extend ArgumentStatusEnum and add ArgumentStatusLog ORM model | 620b8634 | api/models/models.py |
| 3 | Register argument_status_log in schema self-test | ad426e46 | tests/test_schema.py |

## What Was Built

### Migration 0012

`alembic/versions/0012_unpublished_enum_and_status_log.py` (down_revision `0011`):

1. **Enum expansion:** `op.execute(sa.text("COMMIT"))` followed immediately by `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'`. This reproduces the exact pattern from migration 0008 — ALTER TYPE ADD VALUE cannot run inside a transaction block.

2. **Table creation:** `op.create_table("argument_status_log", ...)` with columns id (PK), argument_id (FK→arguments.id NOT NULL), status (bound to existing `argument_status` PG enum via `name="argument_status"`), created_at (TIMESTAMPTZ NOT NULL, server_default now()). `op.create_table` placed after the enum expansion per D-04 ordering constraint.

3. **Backfill:** Single `INSERT INTO argument_status_log ... SELECT id, status::argument_status, COALESCE(resolved_at, CURRENT_TIMESTAMP) FROM arguments`. Seeds each argument's log with its actual current status — no hardcoded literal (T-22-02 mitigation).

4. **Downgrade:** `op.drop_table("argument_status_log")` only. The `unpublished` enum value is intentionally not reversed — PostgreSQL cannot remove enum values.

### ORM Changes (api/models/models.py)

- `ArgumentStatusEnum` gains `UNPUBLISHED = "unpublished"` as a fourth member (ALIST-01)
- New `ArgumentStatusLog(Base)` model with `__tablename__ = "argument_status_log"` and columns matching the migration exactly: id, argument_id, status, created_at. The `status` column uses `SAEnum(ArgumentStatusEnum, name="argument_status", values_callable=lambda e: [x.value for x in e])` — same constructor as `Argument.status` — to bind to the existing PG type (AEDIT-02)
- Module docstring updated to reflect 13 tables (argument_status_log + admin_jobs added since original 11)

### Schema Self-Test (tests/test_schema.py)

- `"argument_status_log"` added to `EXPECTED_TABLES` set (now 12 entries)
- `test_all_tables_exist` docstring updated: "All 12 tables must exist"
- Module docstring and section comment updated to 12

## Verification Results

| Check | Result |
|-------|--------|
| `ast.parse(migration 0012)` exits 0 | PASSED |
| `ArgumentStatusEnum.UNPUBLISHED.value == 'unpublished'` | PASSED |
| `ArgumentStatusLog.__tablename__ == 'argument_status_log'` | PASSED |
| `{'id','argument_id','status','created_at'} <= columns` | PASSED |
| `argument_status_log` in `tests/test_schema.py` | PASSED |
| `alembic upgrade head` / `alembic downgrade -1` round-trip | DEFERRED — no live DATABASE_URL in executor environment |

**Note on deferred round-trip:** The `alembic upgrade head` / `alembic downgrade -1` live database test is deferred to deployment smoke test. The migration file passes static syntax validation, contains all required SQL constructs, and chains correctly from revision 0011.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan creates migration DDL and ORM declarations; no UI stubs or placeholder data.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. The new `argument_status_log` table is write-only from the migration backfill and will be read by future phases 26/27 via existing admin API patterns.

## Self-Check: PASSED

- `alembic/versions/0012_unpublished_enum_and_status_log.py` — confirmed exists
- `api/models/models.py` — contains `UNPUBLISHED = "unpublished"` and `class ArgumentStatusLog`
- `tests/test_schema.py` — contains `"argument_status_log"` in EXPECTED_TABLES
- Commits 1d0b021c, 620b8634, ad426e46 — all confirmed in git log
