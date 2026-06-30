---
phase: 19
plan: "01"
subsystem: database
tags:
  - alembic
  - migration
  - sqlalchemy
  - schema
dependency_graph:
  requires:
    - alembic/versions/0010_add_is_justice.py
  provides:
    - alembic/versions/0011_add_source_docket_cover_metadata.py
    - Argument.source_docket
    - Argument.cover_metadata
    - Argument.argued_date (nullable)
    - uq_arguments_source_docket_question constraint
  affects:
    - api/models/models.py
    - All callers of Argument.argued_date (now nullable)
tech_stack:
  added: []
  patterns:
    - Alembic hand-written migration following migration 0010 as template
    - JSONB column from sqlalchemy.dialects.postgresql (existing import)
    - UniqueConstraint in __table_args__ tuple
key_files:
  created:
    - alembic/versions/0011_add_source_docket_cover_metadata.py
  modified:
    - api/models/models.py
decisions:
  - "[19-01]: Migration 0011 adds source_docket VARCHAR(50) NULL, cover_metadata JSONB NULL, makes argued_date nullable, and adds UNIQUE constraint uq_arguments_source_docket_question on (source_docket, question_number) — migration 0010 used as exact template"
  - "[19-01]: Argument model __table_args__ added with UniqueConstraint; JSONB and UniqueConstraint were already imported in models.py — no new imports needed"
  - "[19-01]: NULL semantics documented — multiple rows with source_docket=NULL do NOT violate the unique constraint per SQL standard; deduplication only applies when docket is known (D-01)"
  - "[19-01]: argued_date nullable change requires all callers to handle Optional[date]; downstream plans and schemas must audit argued_date usage (Pitfall 2 from RESEARCH.md)"
metrics:
  duration: 12
  completed: "2026-06-30"
status: complete
---

# Phase 19 Plan 01: Schema Foundation — Migration 0011 Summary

**One-liner:** Alembic migration 0011 adds source_docket VARCHAR(50) and cover_metadata JSONB columns to arguments, makes argued_date nullable, and enforces a UNIQUE constraint on (source_docket, question_number) — the schema foundation all other Phase 19 plans depend on.

## What Was Built

### Task 1: Alembic Migration 0011

`alembic/versions/0011_add_source_docket_cover_metadata.py` — a hand-written migration following the 0010 template exactly.

**upgrade() operations (in order):**
1. `op.add_column("arguments", Column("source_docket", String(50), nullable=True))` — tracks primary docket used at ingest; NULL when operator did not supply one (D-01)
2. `op.add_column("arguments", Column("cover_metadata", JSONB(), nullable=True))` — stores raw cover extractor output written unconditionally by parse step (D-07)
3. `op.alter_column("arguments", "argued_date", nullable=True)` — no backfill needed; all existing rows have argued_date set (D-08)
4. `op.create_unique_constraint("uq_arguments_source_docket_question", "arguments", ["source_docket", "question_number"])` — deduplication constraint when docket is known (D-01)

**downgrade() operations (reverse order):** drop constraint → alter argued_date back to NOT NULL → drop cover_metadata → drop source_docket.

**Verification:** `alembic upgrade head` exited 0. Round-trip (downgrade -1 → upgrade head) also exited 0 cleanly.

### Task 2: Argument SQLAlchemy Model Update

`api/models/models.py` — Argument class updated to mirror the schema:

- `argued_date` changed from `nullable=False` to `nullable=True` with Phase 19 D-08 comment
- `source_docket = Column(String(50), nullable=True)` added with D-01 comment
- `cover_metadata = Column(JSONB, nullable=True)` added with D-07 comment
- `__table_args__` tuple added containing `UniqueConstraint("source_docket", "question_number", name="uq_arguments_source_docket_question")`

JSONB was already imported from `sqlalchemy.dialects.postgresql` at line 27. UniqueConstraint was already imported from sqlalchemy at line 24. No new imports needed.

**Verification:** `python -c "from api.models.models import Argument; ..."` exits 0. UniqueConstraint name confirmed as `uq_arguments_source_docket_question` on columns `['source_docket', 'question_number']`. `argued_date.nullable` is `True`.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both files are a migration and a model definition — no UI rendering, no placeholder text, no hardcoded empty values.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model documents. The migration runs with DB admin credentials in an operator-controlled environment (T-19-01-SC: accepted). The unique constraint NULL semantics are intentional and documented (T-19-01-NULL: accepted).

## Self-Check

| Artifact | Status |
|----------|--------|
| alembic/versions/0011_add_source_docket_cover_metadata.py | FOUND — created, committed at 0bb57186 |
| api/models/models.py Argument model | FOUND — updated, committed at 0acc077b |
| argued_date nullable=True | VERIFIED — python import confirms nullable=True |
| source_docket Column(String(50), nullable=True) | VERIFIED — column present in Argument.__table__.c |
| cover_metadata Column(JSONB, nullable=True) | VERIFIED — column present in Argument.__table__.c |
| UniqueConstraint uq_arguments_source_docket_question | VERIFIED — name and columns confirmed via python |
| alembic upgrade head exit 0 | VERIFIED — clean upgrade output, no errors |
| downgrade + upgrade round-trip | VERIFIED — both legs exited 0 cleanly |

## Self-Check: PASSED

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1: Migration 0011 | 0bb57186 | feat(19-01): add Alembic migration 0011 (source_docket, cover_metadata, argued_date nullable) |
| Task 2: Argument model | 0acc077b | feat(19-01): update Argument SQLAlchemy model to reflect migration 0011 |
