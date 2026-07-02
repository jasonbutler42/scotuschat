---
phase: 22-schema-foundations
plan: "02"
subsystem: database/orm/api/frontend
status: complete
tags: [migration, alembic, schema, pedit-10, pjob-13, column-move, orm, cleanup]
dependency_graph:
  requires: [22-01]
  provides: [argument_participants.title column, court_tenures.appointed_by, court_tenures.appointing_president_party]
  affects: [27-tenure-editor-ui, phase-23-participant-editor]
tech_stack:
  added: []
  patterns: [nullable-column-add, column-drop-without-backfill, orm-column-move, service-field-removal]
key_files:
  created:
    - alembic/versions/0013_participant_title_and_tenure_appointed_by.py
  modified:
    - api/models/models.py
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/services/speakers.py
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte
decisions:
  - "Migration 0013 chains from 0012 with down_revision='0012'"
  - "court_tenures column named appointed_by (not appointing_president) per D-08/A4 rename-by-move decision"
  - "No backfill on dropped people columns — existing data was test/incorrect (D-08)"
  - "SpeakerPopoverEntry.appointing_president field retained in api/schemas/speakers.py with None value from service — Phase 27 wires from court_tenures.appointed_by"
  - "Appointment section removed from person editor entirely — Phase 27 adds per-tenure row controls"
metrics:
  duration: "~15 minutes"
  completed: "2026-07-02"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 7
---

# Phase 22 Plan 02: Participant Title + Tenure Appointed-By Migration Summary

**One-liner:** Alembic migration 0013 adds `argument_participants.title` and moves appointment columns from `people` to `court_tenures`, with simultaneous ORM/schema/service/frontend cleanup eliminating every person-level `appointing_president` reference.

## What Was Built

Migration 0013 delivers the schema half of PJOB-13 (`argument_participants.title` for TOC subtitle storage) and completes PEDIT-10 (moving appointment tracking from the person level to the tenure level). All five code layers that previously referenced `person.appointing_president` were updated in the same plan to prevent the AttributeError window that would otherwise open between migration and code deployment.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migration 0013 + ORM update | `00398efd` | alembic/versions/0013_..., api/models/models.py |
| 2 | Schema and service cleanup | `f0cff1cb` | api/schemas/admin_people.py, api/services/admin_people.py, api/services/speakers.py |
| 3 | Person editor frontend cleanup | `e980b335` | app/src/routes/admin/people/[id]/+page.server.ts, +page.svelte |

## Migration 0013 Details

**upgrade() order:**
1. `op.add_column("argument_participants", sa.Column("title", sa.String(500), nullable=True))`
2. `op.add_column("court_tenures", sa.Column("appointed_by", sa.String(200), nullable=True))`
3. `op.add_column("court_tenures", sa.Column("appointing_president_party", sa.String(50), nullable=True))`
4. `op.drop_column("people", "appointing_president")`
5. `op.drop_column("people", "appointing_president_party")`

**downgrade()** reverses in opposite order: restores both `people` columns as nullable, drops the three `court_tenures`/`argument_participants` columns.

No backfill on any column — all new court_tenures rows stay NULL until Phase 27 UI.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Additional Notes

- `api/services/speakers.py`: the dict key `"appointing_president"` is retained but now sends `None` as a literal rather than reading `person.appointing_president`. This avoids breaking the `SpeakerPopoverEntry` Pydantic schema in `api/schemas/speakers.py` (which the plan explicitly says to leave unchanged). The `{#if speaker.appointing_president}` guard in the frontend template handles `None` safely.

## Verification Results

All automated checks passed:

- Migration 0013 parses cleanly (`ast.parse`)
- `CourtTenure.__table__.columns` contains `appointed_by` and `appointing_president_party`
- `ArgumentParticipant.__table__.columns` contains `title`
- `Person.__table__.columns` contains neither `appointing_president` nor `appointing_president_party`
- `python -c "import api.services.admin_people, api.services.speakers, api.schemas.admin_people"` — imports without error
- No `person.appointing_president` in `api/services/speakers.py` or `api/services/admin_people.py`
- No `appointing_president` in `api/schemas/admin_people.py`
- No `appointing_president` in `app/src/routes/admin/people/[id]/+page.server.ts` or `+page.svelte`
- `name_suffix` and `is_justice` controls confirmed present in `+page.svelte` (8 occurrences)

**Deferred verification:** `alembic upgrade head` then `alembic downgrade -1` requires a live DATABASE_URL. The migration file is syntactically valid and chains from 0012 per `down_revision = "0012"`. Live migration smoke test deferred to deployment environment.

## Known Stubs

- `api/services/speakers.py` returns `"appointing_president": None` for all speakers. This is intentional — Phase 27 will wire the value from `court_tenures.appointed_by` once the tenure-level appointment UI exists. The frontend template's `{#if speaker.appointing_president}` guard handles `None` safely with no visible regression.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond those documented in the plan's threat model. T-22-04 (AttributeError window) is fully closed — no Python layer references a dropped column.

## Self-Check: PASSED

- `alembic/versions/0013_participant_title_and_tenure_appointed_by.py` — FOUND
- `api/models/models.py` modified — FOUND (ORM assertions passed)
- `api/schemas/admin_people.py` modified — FOUND
- `api/services/admin_people.py` modified — FOUND
- `api/services/speakers.py` modified — FOUND
- `app/src/routes/admin/people/[id]/+page.server.ts` modified — FOUND
- `app/src/routes/admin/people/[id]/+page.svelte` modified — FOUND
- Commits `00398efd`, `f0cff1cb`, `e980b335` — FOUND in git log
