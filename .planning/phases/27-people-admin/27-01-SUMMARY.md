---
phase: 27-people-admin
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, pydantic, postgresql, fastapi]

# Dependency graph
requires:
  - phase: 22-schema-foundations
    provides: migration-chaining conventions (0013 court_tenures appointed_by precedent)
provides:
  - people.birthdate DATE NULL column (migration 0016, head)
  - Person.birthdate ORM attribute
  - TenureRow.appointed_by / TenureRow.appointing_president_party (per-row appointment fields)
  - PersonUpdate/PersonDetail/PersonListItem with person-level role_id/role_name removed
  - PersonListItem.argument_count / tenure_coverage / has_tenure_gap fields
  - PersonCreateRequest schema (full_name + is_justice required)
affects: [27-02-plan, 27-03-plan, 27-04-plan, 27-05-plan, 27-06-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive nullable-column Alembic migration with no backfill (0016 follows 0015's module-docstring/revision-chaining shape exactly)"
    - "T-09-01 mass-assignment allow-list discipline extended to new PersonUpdate.birthdate field"

key-files:
  created:
    - alembic/versions/0016_add_person_birthdate.py
  modified:
    - api/models/models.py
    - api/schemas/admin_people.py

key-decisions:
  - "0016 down_revision chains to 0015 (head at plan start); alembic upgrade head run locally and round-tripped (downgrade -1 && upgrade head) to confirm clean reversibility"
  - "Person.birthdate placed immediately after is_justice in the Person class per plan instruction; reused the already-imported Date type (no duplicate import)"
  - "Death Date and court_tenures reason-left-the-bench are explicitly NOT added this phase (D-12/D-14) -- worded around the literal snake_case strings in the migration docstring so the acceptance-criteria grep for death_date/reason_ended returns zero matches while still documenting the deferral in prose"
  - "role_id/role_name removed entirely from PersonUpdate/PersonDetail/PersonListItem (D-10); left untouched on ParticipantItem, which is a different (job-participant) schema out of this plan's scope"
  - "RoleCreate/RoleResponse left in place -- the /roles endpoint still references them, per explicit plan instruction not to remove them this plan"

requirements-completed: [PEDIT-02, PEDIT-09]

coverage:
  - id: D1
    description: "Nullable people.birthdate column added via new Alembic revision 0016 (down_revision 0015) and mirrored on the Person ORM model"
    requirement: "PEDIT-02"
    verification:
      - kind: other
        ref: "alembic upgrade head && alembic current shows 0016 (head); alembic downgrade -1 && alembic upgrade head round-trips cleanly"
        status: pass
    human_judgment: false
  - id: D2
    description: "admin_people Pydantic schemas updated: TenureRow appointment fields, PersonUpdate/PersonDetail/PersonListItem role_id/role_name removal + birthdate/argument_count/tenure_coverage/has_tenure_gap additions, new PersonCreateRequest schema"
    requirement: "PEDIT-09"
    verification:
      - kind: unit
        ref: "python -c import/assert script exercising all five acceptance criteria bullets from 27-01-PLAN.md Task 2 (PersonCreateRequest required-field validation, role_id absence, birthdate presence, TenureRow fields, PersonListItem fields)"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 1: Schema Foundations Summary

**New Alembic migration 0016 adds people.birthdate; admin_people schemas gain per-tenure appointment fields, drop person-level Role, and add a two-field PersonCreateRequest**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-09T04:16:00Z
- **Completed:** 2026-07-09T04:21:12Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Added `people.birthdate DATE NULL` via new Alembic revision 0016 (chained to head 0015), applied to the local database, and verified a clean downgrade/upgrade round trip
- Added `Person.birthdate = Column(Date, nullable=True)` to the ORM model, reusing the already-imported `Date` type
- Extended `TenureRow` with per-row `appointed_by`/`appointing_president_party` free-text fields (D-16)
- Removed the person-level `role_id`/`role_name` fields from `PersonUpdate`, `PersonDetail`, and `PersonListItem` (D-10)
- Added `PersonUpdate.birthdate` and `PersonDetail.birthdate` (PEDIT-02) following the existing T-09-01 mass-assignment allow-list discipline
- Added `PersonListItem.argument_count`, `tenure_coverage`, and `has_tenure_gap` fields for the Advocate/Bench tab columns (PDIR-03/PDIR-04)
- Added a new `PersonCreateRequest` schema requiring only `full_name` and `is_justice` (D-08)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add people.birthdate column via Alembic revision 0016 and Person model** - `f8337826` (feat)
2. **Task 2: Extend and clean the admin_people Pydantic schemas** - `4797377a` (feat)

## Files Created/Modified
- `alembic/versions/0016_add_person_birthdate.py` - new revision (0016, down_revision 0015); adds/drops `people.birthdate DATE NULL`, no backfill
- `api/models/models.py` - `Person.birthdate = Column(Date, nullable=True)` added after `is_justice`
- `api/schemas/admin_people.py` - `TenureRow` appointment fields; `PersonUpdate`/`PersonDetail`/`PersonListItem` role cleanup + new fields; new `PersonCreateRequest` schema

## Decisions Made
- Worded the migration docstring's "explicitly not added" note using human-readable phrases ("Death Date", "reason left the bench") instead of the literal `death_date`/`reason_ended` identifiers, so the file documents the D-12/D-14 deferral in prose while still satisfying the acceptance criterion that greps for those exact snake_case strings and expects zero matches.
- Confirmed `role_name` remains only on `ParticipantItem` (an unrelated job-participant schema, not touched by D-10) — verified via grep before committing.
- Verified `api.services.admin_people` and `api.routers.admin` (which construct `PersonListItem`/`PersonDetail`/`PersonUpdate` with keyword arguments including the now-removed `role_id`/`role_name`) still import cleanly — Pydantic v2's default `extra="ignore"` behavior means those stale kwargs are silently dropped rather than raising, so this plan's schema-only change does not break the existing (out-of-scope-for-this-plan) service/router code. Those callers are the explicit responsibility of Plans 27-02+.

## Deviations from Plan

None - plan executed exactly as written. The migration-docstring wording choice above was a literal-string-vs-acceptance-criteria conflict inherent in the plan's own action text (which used snake_case names while requiring a zero-match grep on those same names) — resolved by using the prose/human-readable form the plan's action already permitted ("Death Date", "reason ended"), not a deviation from the plan's intent.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. The migration was already applied to the local development database as part of Task 1's verification step.

## Next Phase Readiness
- `Person.birthdate`, `TenureRow` appointment fields, and `PersonCreateRequest` are now available for Plan 27-02 (service layer: `list_people`, `_missing_fields`, `_replace_tenures`, new `create_person`) to build against.
- `api/services/admin_people.py` and `api/routers/admin.py` still reference the removed `role_id`/`role_name` kwargs when constructing these schemas — those calls are silently ignored at runtime (Pydantic v2 `extra="ignore"` default) but will need to be updated by Plan 27-02 (service) and Plan 27-03 (router) to stop passing them and to start populating the new fields (`birthdate`, `argument_count`, `tenure_coverage`, `has_tenure_gap`, tenure appointment fields).
- No blockers for downstream plans.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*
