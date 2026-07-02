---
phase: 18-people-schema-editor
plan: "01"
subsystem: database
tags: [migration, alembic, orm, schema, people, is_justice]
status: complete

dependency_graph:
  requires: [migration 0009 (down_revision chain)]
  provides: [people.is_justice column, Person.is_justice ORM, migration 0010, test_people_has_is_justice_column]
  affects: [api/models/models.py, alembic/versions/0010_add_is_justice.py, tests/test_schema.py]

tech_stack:
  added: [false() from sqlalchemy (server_default for boolean)]
  patterns: [Alembic hand-written migration with backfill UPDATE, information_schema introspection test]

key_files:
  created:
    - alembic/versions/0010_add_is_justice.py
  modified:
    - api/models/models.py
    - tests/test_schema.py

decisions:
  - "D-01/D-02 honored: backfill sources from court_tenures only — no argument_participants inference"
  - "false() imported from sqlalchemy for server_default to match migration 0010 exactly"
  - "AsyncFunctionDef (async def) used for DB-gated test — pytest collects correctly"

metrics:
  duration_min: 15
  completed_date: "2026-06-29"
  tasks_completed: 3
  files_changed: 3
---

# Phase 18 Plan 01: is_justice Schema Migration Summary

**One-liner:** Alembic migration 0010 adds `is_justice BOOLEAN NOT NULL DEFAULT FALSE` to `people`, backfilling TRUE from `court_tenures`, with matching ORM column and DB-gated schema test.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create migration 0010 — is_justice with tenure backfill | da164446 | alembic/versions/0010_add_is_justice.py |
| 2 | Add Person.is_justice ORM column | 76d34ba7 | api/models/models.py |
| 3 | Add schema smoke test for people.is_justice | 31092c29 | tests/test_schema.py |

## What Was Built

Migration `0010_add_is_justice.py` chains from `0009` and:
- Adds `is_justice BOOLEAN NOT NULL server_default=FALSE` via `op.add_column` (PG fills existing rows via server default — no separate FALSE UPDATE needed)
- Runs a single backfill `UPDATE people SET is_justice = TRUE WHERE id IN (SELECT DISTINCT person_id FROM court_tenures)` (D-01, D-02)
- `downgrade()` drops the column cleanly

`api/models/models.py` additions:
- `false` imported from sqlalchemy (added to existing import block)
- `is_justice = Column(Boolean, nullable=False, server_default=false())` added after Phase 9 additions block with `# Phase 18 — migration 0010` comment

`tests/test_schema.py` addition:
- `test_people_has_is_justice_column` async test decorated with `@requires_db` and `@pytest.mark.asyncio`
- Queries `information_schema.columns` for `data_type`, `is_nullable`, `column_default`
- Asserts: data_type='boolean', is_nullable='NO', column_default contains 'false'
- Skips gracefully without DATABASE_URL; all 4 tests collect without error

## Verification

- `python -c "from api.models.models import Person; ..."` — prints `OK is_justice BOOLEAN nullable= False`
- `python -m pytest tests/test_schema.py --collect-only` — 4 tests collected
- `python -m pytest tests/test_schema.py::test_no_create_all_in_codebase` — 1 passed
- Static check: `argument_participants` absent from migration 0010 (D-02 compliant)
- Static check: `create_all` absent from migration 0010 (CLAUDE.md compliant)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed 'argument_participants' from migration docstring/comments**
- **Found during:** Task 1 verification
- **Issue:** Plan's automated verify asserted `argument_participants` must not appear anywhere in the migration file (D-02 compliance). The initial docstring and inline comment both contained the string as a reference to what NOT to use.
- **Fix:** Replaced both occurrences with neutral phrasing ("no side-based inference") that conveys the same meaning without triggering the D-02 check.
- **Files modified:** alembic/versions/0010_add_is_justice.py
- **Commit:** da164446

**2. [Rule 2 - Missing] Imported false() from sqlalchemy for server_default**
- **Found during:** Task 2 implementation
- **Issue:** `sa` is not imported in `api/models/models.py` (only named imports). The `false()` function needed for `server_default` required adding it to the existing import block.
- **Fix:** Added `false` to the `from sqlalchemy import (...)` block.
- **Files modified:** api/models/models.py
- **Commit:** 76d34ba7

## Known Stubs

None — this plan is pure schema/migration work with no UI stubs.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- alembic/versions/0010_add_is_justice.py: FOUND
- api/models/models.py: FOUND
- tests/test_schema.py: FOUND
- .planning/phases/18-people-schema-editor/18-01-SUMMARY.md: FOUND
- Commit da164446: FOUND (migration 0010)
- Commit 76d34ba7: FOUND (ORM column)
- Commit 31092c29: FOUND (schema test)
