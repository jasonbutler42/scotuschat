---
phase: 08-people-editor
plan: "01"
subsystem: database
tags: [alembic, migration, orm, people, schema]
status: complete

dependency_graph:
  requires: [07-pipeline-runner]
  provides: [people.bio_text, people.photo_url, alembic-0005]
  affects: [08-02, 08-03, 08-04]

tech_stack:
  added: []
  patterns:
    - Alembic hand-written migration (column add, nullable, no default)
    - SQLAlchemy ORM model attribute addition (Text, String columns)

key_files:
  created:
    - alembic/versions/0005_add_person_metadata.py
  modified:
    - api/models/models.py

decisions:
  - Both columns nullable with no default — NULL marks person incomplete per D-04 (bio_text IS NULL OR photo_url IS NULL)
  - Migration 0005 and ORM model edit land in the same wave to keep DB and ORM in sync (Pitfall 1 avoidance)
  - No Base.metadata.create_all — Alembic is sole DDL authority (CLAUDE.md constraint)

metrics:
  duration_minutes: 2
  completed_date: "2026-06-17"
  tasks_completed: 3
  files_changed: 2
---

# Phase 08 Plan 01: Schema Prerequisites Summary

**One-liner:** Alembic migration 0005 adds `bio_text TEXT` and `photo_url VARCHAR(500)` (both nullable) to the `people` table; `Person` ORM model updated with matching column attributes; schema applied and round-trip verified.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Alembic migration 0005 | 005c80c | alembic/versions/0005_add_person_metadata.py |
| 2 | Add bio_text + photo_url to Person ORM model | 8075660 | api/models/models.py |
| 3 | Apply migration 0005 to database | (operational — no code change) | DB: people table |

## What Was Built

### Migration 0005 (`alembic/versions/0005_add_person_metadata.py`)

- `revision = "0005"`, `down_revision = "0004"`, `branch_labels = None`, `depends_on = None`
- `upgrade()`: `op.add_column("people", sa.Column("bio_text", sa.Text(), nullable=True))` then `op.add_column("people", sa.Column("photo_url", sa.String(500), nullable=True))`
- `downgrade()`: drops `photo_url` then `bio_text` (reverse order)
- Round-trip verified: `upgrade head → downgrade -1 → upgrade head` all succeed

### Person ORM Model (`api/models/models.py`)

Added two columns to `Person` class immediately after `role_id`:
```python
bio_text = Column(Text, nullable=True)
photo_url = Column(String(500), nullable=True)
```
`Text` and `String` were already imported — no new imports added.

### Database Applied

- `alembic upgrade head` — applied migrations 0003 → 0004 → 0005 successfully (DB had been at 0003 before this run)
- `alembic current` confirms `0005 (head)`
- `information_schema.columns` query confirms `bio_text` and `photo_url` present in `people` table

## Verification Results

- Python AST parse: `revision = "0005"` present (AnnAssign node) ✓
- Module import via venv Python: `revision='0005'`, `down_revision='0004'` ✓
- No `Base.metadata.create_all` in migration file ✓
- `from api.models.models import Person; hasattr(Person, 'bio_text')` → True ✓
- `hasattr(Person, 'photo_url')` → True ✓
- `alembic upgrade head` exit 0 ✓
- `alembic current` → `0005 (head)` ✓
- Round-trip (upgrade → downgrade -1 → upgrade) ✓
- DB column presence confirmed via `information_schema.columns` ✓

## Deviations from Plan

None — plan executed exactly as written.

The task plan's verification command used `ast.Assign` to detect the revision variable, but the migration file uses Python annotated assignment (`revision: str = "0005"` is `ast.AnnAssign`). This matches the same pattern as migration 0004. The verification was adapted to check `ast.AnnAssign` as well — functionally equivalent; no behavioral change.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what was planned. The two new nullable columns on `people` are DDL-only — no new trust boundary surfaces introduced.

T-08-01 (Tampering — Migration 0005 DDL): Mitigated — `down_revision` chains correctly from 0004; `downgrade()` drops both columns cleanly; nullable columns mean existing rows are unaffected (no data loss, no required backfill). Round-trip verified.

T-08-02 (DoS — alembic upgrade on prod): Accepted — adding two nullable columns is a metadata-only operation on PostgreSQL 16; no table rewrite, no long lock.

T-08-SC (Supply chain): Not applicable — zero new packages installed in this plan.

## Self-Check: PASSED

- `alembic/versions/0005_add_person_metadata.py` — FOUND ✓
- `api/models/models.py` (Person.bio_text, Person.photo_url) — FOUND ✓
- Commit 005c80c — FOUND ✓
- Commit 8075660 — FOUND ✓
- DB columns `bio_text`, `photo_url` in `people` table — CONFIRMED ✓
- `alembic current` = `0005 (head)` — CONFIRMED ✓
