---
phase: 15-speaker-role-accuracy
plan: "01"
subsystem: database
tags: [alembic, migration, orm, schema, enum]
dependency_graph:
  requires: [migration-0007]
  provides: [migration-0008, ArgumentStatusEnum, SideEnum-expanded, Argument.status]
  affects: [api/models/models.py, alembic/versions/0008_side_enum_and_argument_status.py]
tech_stack:
  added: []
  patterns: [alembic-op-execute-DDL, SAEnum-values_callable, DO-block-enum-creation]
key_files:
  created:
    - alembic/versions/0008_side_enum_and_argument_status.py
  modified:
    - api/models/models.py
decisions:
  - "[15-01] Migration 0008 commits Alembic's implicit transaction before ALTER TYPE ADD VALUE calls (Pitfall 1 guard)"
  - "[15-01] SideEnum.ADVOCATE retained as legacy member — PG cannot drop enum values; ADVOCATE→UNKNOWN backfill in migration"
  - "[15-01] ArgumentStatusEnum placed after AdminJobStep in models.py; Argument.status uses identical SAEnum pattern as PipelineRun.status"
  - "[15-01] Migration path confirmed: alembic/versions/ (not api/alembic/versions/) — plan.md path reference corrected during execution"
metrics:
  duration: 3
  completed: "2026-06-25"
status: complete
---

# Phase 15 Plan 01: Schema Migration — side Enum Expansion + argument_status Column Summary

**One-liner:** Alembic migration 0008 expands the `side` PG enum with PETITIONER/RESPONDENT/AMICUS, backfills ADVOCATE to UNKNOWN, creates the `argument_status` enum type, and adds a non-null `arguments.status` column backfilled from existing lifecycle columns; ORM models updated to match.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write Alembic migration 0008 | 455fa91 | alembic/versions/0008_side_enum_and_argument_status.py |
| 2 | Update SideEnum and add ArgumentStatusEnum + Argument.status to ORM models | 3ea0e47 | api/models/models.py |

## What Was Built

### Task 1: Alembic Migration 0008

New file `alembic/versions/0008_side_enum_and_argument_status.py` (revision `"0008"`, down_revision `"0007"`) performs:

**Part A — side enum expansion:** Commits Alembic's open transaction before any `ALTER TYPE ... ADD VALUE` call (critical per Pitfall 1 — PG forbids ADD VALUE inside a transaction block). Three `ALTER TYPE side ADD VALUE IF NOT EXISTS` calls add PETITIONER, RESPONDENT, AMICUS.

**Part B — ADVOCATE→UNKNOWN backfill:** `UPDATE argument_participants SET side = 'UNKNOWN' WHERE side = 'ADVOCATE'` (D-06).

**Part C — argument_status type creation:** DO-block guarded `CREATE TYPE argument_status AS ENUM ('pipeline', 'draft', 'published')` using the same idempotent pattern as migration 0001.

**Part D — status column:** `op.add_column("arguments", Column("status", Enum(...), nullable=True))` — nullable initially for backfill.

**Part E — three-way backfill:** published → draft → pipeline in precedence order so every row receives a value before the NOT NULL constraint is applied.

**Part F — NOT NULL enforcement:** `op.alter_column("arguments", "status", nullable=False)`.

**Downgrade:** drops the status column and argument_status type. Side enum additions are intentionally not reversed (PG cannot drop enum values).

### Task 2: ORM Model Updates (`api/models/models.py`)

- `SideEnum` extended with `PETITIONER = "PETITIONER"`, `RESPONDENT = "RESPONDENT"`, `AMICUS = "AMICUS"`; `ADVOCATE` retained with inline legacy comment.
- `ArgumentStatusEnum(str, enum.Enum)` added after `AdminJobStep` with members `PIPELINE = "pipeline"`, `DRAFT = "draft"`, `PUBLISHED = "published"`.
- `Argument.status` column added using the `SAEnum(ArgumentStatusEnum, name="argument_status", values_callable=lambda e: [x.value for x in e])` pattern copied from `PipelineRun.status`; `nullable=False`, `default=ArgumentStatusEnum.PIPELINE`.

## Verification Results

All automated checks passed:

```
parse-ok     # ast.parse on migration 0008
models-ok    # import assertion: SideEnum.PETITIONER/RESPONDENT/AMICUS/ADVOCATE, ArgumentStatusEnum values, Argument.__table__.columns includes status
not found    # Base.metadata.create_all not introduced
```

## Decisions Made

1. **Migration path:** The plan references `api/alembic/versions/` but the actual migration directory is `alembic/versions/` (at project root, not under `api/`). File created at the correct location.
2. **COMMIT placement:** `op.execute(sa.text("COMMIT"))` placed as the very first statement in `upgrade()`, before any ALTER TYPE call. This ensures Alembic's implicit transaction is closed before the ADD VALUE calls.
3. **`ArgumentStatusEnum` placement:** Added immediately after `AdminJobStep` as specified in the plan. The `Argument.status` column definition follows the existing `PipelineRun.status` SAEnum pattern exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Correction] Migration file path**
- **Found during:** Task 1
- **Issue:** The plan's `files_modified` field listed `api/alembic/versions/0008_side_enum_and_argument_status.py` but the project's actual Alembic directory is `alembic/versions/` at the project root.
- **Fix:** Created the file at the correct path `alembic/versions/0008_side_enum_and_argument_status.py`. Verified by checking the existing 0001-0007 migrations.
- **Impact:** Cosmetic — plan path was wrong, implementation is correct.

## Known Stubs

None — this plan produces schema artifacts only (migration + model definitions), no UI or service layer.

## Threat Flags

None — this plan adds DDL only (no new network endpoints, no auth paths, no file access patterns at trust boundaries).

## Self-Check: PASSED

- [x] `alembic/versions/0008_side_enum_and_argument_status.py` exists (confirmed)
- [x] `api/models/models.py` modified (confirmed)
- [x] Commit 455fa91 exists (confirmed)
- [x] Commit 3ea0e47 exists (confirmed)
- [x] parse-ok assertion passed
- [x] models-ok assertion passed
