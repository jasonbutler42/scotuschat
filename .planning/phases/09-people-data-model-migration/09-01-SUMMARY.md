---
phase: 09-people-data-model-migration
plan: "01"
subsystem: database / backend-schema
tags: [alembic, sqlalchemy, pydantic, migration, people, schema-extension]
status: complete

dependency_graph:
  requires:
    - "alembic/versions/0005_add_person_metadata.py (down_revision anchor)"
    - "api/models/models.py Person class (existing column set)"
    - "api/schemas/admin_people.py PersonDetail + PersonUpdate (existing fields)"
  provides:
    - "alembic/versions/0006_add_structured_name_fields.py (DDL for six nullable columns)"
    - "Person ORM with six new nullable attributes"
    - "PersonDetail + PersonUpdate with six new Optional[str] = None fields"
  affects:
    - "09-02 (service layer + form action — consumes Person attributes and PersonUpdate fields)"
    - "09-03 (SvelteKit edit form — consumes PersonDetail fields)"

tech_stack:
  added: []
  patterns:
    - "Alembic op.add_column per nullable column (Pattern 1 from 09-PATTERNS.md)"
    - "SQLAlchemy Column(String(N), nullable=True) ORM extension (Pattern 2)"
    - "Pydantic v2 Optional[str] = None schema field extension (Pattern 3)"

key_files:
  created:
    - alembic/versions/0006_add_structured_name_fields.py
  modified:
    - api/models/models.py
    - api/schemas/admin_people.py

decisions:
  - "D-01: Six nullable VARCHAR columns added to people — first_name(150), last_name(150), middle_name(150), name_suffix(50), appointing_president(200), appointing_president_party(50)"
  - "D-02: full_name Column(String(300), nullable=False) untouched — resolution anchor preserved"
  - "D-03: No backfill, no server_default — all new columns NULL on existing rows"
  - "T-09-01 mitigated: PersonUpdate mass-assignment guard extended with six explicit fields"
  - "T-09-02 mitigated: DDL exclusively via Alembic op.add_column; create_all absent and grep-verified"

metrics:
  duration_seconds: 97
  completed_date: "2026-06-19"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3
---

# Phase 9 Plan 01: Alembic Migration 0006 + ORM + Schema Summary

**One-liner:** Alembic migration 0006 adds six nullable columns to `people`; `Person` ORM and `PersonDetail`/`PersonUpdate` Pydantic schemas extended with matching fields.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create Alembic migration 0006 | d2143bb | alembic/versions/0006_add_structured_name_fields.py |
| 2 | Add six Person ORM attributes | 2f7e083 | api/models/models.py |
| 3 | Add six fields to PersonDetail and PersonUpdate | 7df822d | api/schemas/admin_people.py |

## What Was Built

Three additive, layered changes that form the data foundation for Phase 9:

**Migration 0006** (`alembic/versions/0006_add_structured_name_fields.py`): Chains from `down_revision = "0005"`. Adds six `nullable=True` columns to `people` via separate `op.add_column` calls. Reversible `downgrade()` drops in reverse add order. No `server_default`, no backfill, no `Base.metadata.create_all` (CLAUDE.md constraint verified).

**Person ORM** (`api/models/models.py`): Six `Column(String(N), nullable=True)` attributes appended after `photo_url`. Types match the migration exactly. `full_name = Column(String(300), nullable=False)` is untouched (D-02).

**Pydantic schemas** (`api/schemas/admin_people.py`): `PersonDetail` gains six `Optional[str] = None` fields before `model_config`. `PersonUpdate` gains the same six fields at the end of the class body — extending the mass-assignment allow-list so these fields can be written via the PATCH endpoint (T-09-01 mitigation).

## Verification Results

All automated checks passed:

- Migration AST parse, revision identifiers, 6 add/6 drop columns, no `create_all`, all column names present: **OK**
- `Person.__table__.columns` contains all six new names; each `nullable is True`; `full_name.nullable is False`: **OK**
- `PersonDetail.model_fields` and `PersonUpdate.model_fields` contain all six new field names; empty `PersonUpdate()` returns `None` for all six; `PersonDetail(id=1, full_name='Amy Coney Barrett', first_name='Amy', last_name='Barrett')` round-trips correctly: **OK**
- ORM import (`from api.models.models import Person`): **OK**
- Existing test suite (`api/tests/test_admin_people_schemas_service.py`): **17 passed**

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's threat model covers. All mitigations applied:

- T-09-01 (mass assignment): `PersonUpdate` extended with exactly six fields — no other writable surface added.
- T-09-02 (DDL bypass): `create_all` string absent from all three files.
- T-09-03 (full_name integrity): `full_name` column not touched in migration or ORM.

## Known Stubs

None. This plan delivers DDL, ORM, and schema layers only — no UI or service layer. Downstream plans (09-02, 09-03) wire the data.

## Self-Check: PASSED

- `alembic/versions/0006_add_structured_name_fields.py` exists: FOUND
- `api/models/models.py` modified with six new columns: FOUND
- `api/schemas/admin_people.py` modified with six new fields on both classes: FOUND
- Commits d2143bb, 2f7e083, 7df822d all present in git log: FOUND
