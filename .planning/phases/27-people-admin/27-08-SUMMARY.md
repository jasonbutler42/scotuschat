---
phase: 27-people-admin
plan: 08
subsystem: api
tags: [pydantic, sqlalchemy, sveltekit, admin-people, uat-gap-closure]

# Dependency graph
requires:
  - phase: 27-people-admin
    provides: PersonCreateRequest/create_person (Plan 27-03), the [id] editor's save action as working reference (Plan 27-06)
provides:
  - PersonCreateRequest schema with four optional name-part fields (first_name/middle_name/last_name/name_suffix)
  - create_person service persisting name parts with empty-string-to-None normalization
  - SvelteKit create action reading/forwarding all four name-part fields to match the [id] editor
affects: [people-admin, admin-people-create-flow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Standalone script verification against the live dev DB (bypassing pytest's DATABASE_URL visibility gap) used for TDD RED/GREEN confirmation on DB-guarded service tests — mirrors 27-03-SUMMARY.md precedent"

key-files:
  created: []
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - app/src/routes/admin/people/new/+page.server.ts
    - api/tests/test_admin_people_schemas_service.py

key-decisions:
  - "Fixed as a bug (parity with [id] editor), not a scope amendment to D-08 — D-08's deferred-fields list never named structured name parts, only tenure/bio/photo/birthdate"
  - "create_person normalizes name-part blank strings to None using the same convention as update_person (Pitfall 5), so a blank-string submission stores NULL rather than an empty string"

requirements-completed: [PEDIT-01, PDIR-07]

coverage:
  - id: D1
    description: "Creating a person via /admin/people/new with Full Name AND any of First/Middle/Last/Suffix filled persists all of them"
    requirement: "PEDIT-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people_schemas_service.py#test_create_person_persists_name_parts_when_supplied"
        status: pass
      - kind: manual_procedural
        ref: "standalone script against live dev DB (verify_green.py) — case 1: all four name parts persisted and refetched correctly"
        status: pass
    human_judgment: false
  - id: D2
    description: "Omitting the name-part fields on create still succeeds and leaves those columns NULL"
    requirement: "PEDIT-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people_schemas_service.py#test_create_person_leaves_name_parts_none_when_omitted"
        status: pass
    human_judgment: false
  - id: D3
    description: "All three layers (SvelteKit create action, PersonCreateRequest schema, create_person service) carry the four name-part fields end-to-end"
    requirement: "PDIR-07"
    verification:
      - kind: unit
        ref: "cd app && npm run check (0 errors)"
        status: pass
      - kind: other
        ref: "grep -c formData.get('first_name'|'middle_name'|'last_name'|'name_suffix') app/src/routes/admin/people/new/+page.server.ts == 4"
        status: pass
    human_judgment: true
    rationale: "Full end-to-end browser confirmation (create a person with name parts via the UI, then open the editor and confirm persistence) is explicitly deferred to the Phase 27 UAT retest per the plan's verification section — automated coverage proves each layer independently but not the full click-through flow."

# Metrics
duration: 15min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 08: Create-path name-part persistence Summary

**Closed UAT Gap 3 — PersonCreateRequest, create_person, and the SvelteKit create action now carry first_name/middle_name/last_name/name_suffix end-to-end, matching the [id] editor's save behavior.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-09T13:15:00Z
- **Completed:** 2026-07-09T13:30:59Z
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments
- `PersonCreateRequest` gained four optional name-part fields, keeping `full_name`/`is_justice` required per D-08's minimum-required contract
- `create_person` now sets `first_name`/`middle_name`/`last_name`/`name_suffix` on the new `Person` row, normalizing blank strings to `None` (matching `update_person`'s Pitfall 5 convention)
- The `/admin/people/new` `create` server action now reads and forwards all four name-part fields, mirroring the `[id]` editor's `save` action exactly
- Two new DB-guarded tests added proving both the supplied-persists and omitted-stays-null cases
- RED and GREEN states independently confirmed against the live dev database via standalone scripts, since `DATABASE_URL` is not visible inside pytest's process for this project (documented pre-existing limitation, 27-03-SUMMARY.md) — same limitation the plan's own `<verify>` command runs into (new tests correctly show as `skipped`, not `failed`, in the pytest run)

## Task Commits

Each task was committed atomically:

1. **Task 1: Accept and persist name parts in the create schema and service** (TDD)
   - `a70bbb40` — `test(27-08): add failing test for create_person name-part persistence` (RED)
   - `623413f7` — `feat(27-08): persist name-part fields on create_person` (GREEN)
2. **Task 2: Read and forward name parts in the create server action** — `f5a49d8c` — `feat(27-08): forward name-part fields in create server action`

**Plan metadata:** (final docs commit — see below)

_Note: Task 1 is TDD (tdd="true") — test → feat, two commits._

## Files Created/Modified
- `api/schemas/admin_people.py` — `PersonCreateRequest` gains `first_name`/`middle_name`/`last_name`/`name_suffix` (all `Optional[str] = None`); docstring updated to record the new create-time acceptance
- `api/services/admin_people.py` — `create_person` sets the four fields on the new `Person` row with blank-string-to-`None` normalization; docstring updated
- `app/src/routes/admin/people/new/+page.server.ts` — `create` action reads the four `FormData` fields (trim + `''`→`null`) and includes them in the POST body; doc comment updated to remove name parts from the "intentionally NOT sent" framing
- `api/tests/test_admin_people_schemas_service.py` — two new DB-guarded tests (`test_create_person_persists_name_parts_when_supplied`, `test_create_person_leaves_name_parts_none_when_omitted`) using the direct-engine + manual-cleanup pattern from `test_admin_people_merge.py` (required because `create_person` calls `db.commit()` internally, so the rollback-fixture pattern used elsewhere in this file's sibling modules doesn't apply)

## Decisions Made
- Treated as a bug fix aligning the create path with the `[id]` editor's established behavior, not a scope amendment to D-08 — D-08's own enumerated deferred-fields list (tenure/bio/photo/birthdate) never named structured name parts, so deferring them was an implementation gap, not a documented decision (per the debug diagnosis in `.planning/debug/create-person-discards-name-parts.md`)
- Blank-string name-part submissions coerce to `None` (not empty string), keeping create's normalization behavior identical to `update_person`'s existing Pitfall 5 convention

## Deviations from Plan

None — plan executed exactly as written. TDD RED/GREEN confirmation used a standalone script against the live dev DB (rather than a pytest run showing red-to-green transition) because `DATABASE_URL` is not visible inside pytest's process for this project's `api/tests` directory when invoked with an explicit file path (pytest only auto-loads `.env` via `tests/conftest.py`'s `load_dotenv()`, which is a sibling directory to `api/tests` and doesn't apply). This is a pre-existing, previously-documented project limitation (see 27-03-SUMMARY.md), not something introduced by this plan — the new tests correctly `skip` (not fail) under the plan's own `<verify>` pytest invocation, consistent with every other DB-guarded test in this module.

## Issues Encountered
None beyond the DATABASE_URL/pytest visibility gap described above, which was worked around using the same standalone-script pattern already established in 27-03.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- UAT Gap 3 is closed at the code level; full click-through browser confirmation (create with name parts → open editor → confirm persistence) is deferred to the Phase 27 UAT retest per this plan's `<verification>` section, alongside the other two UAT gaps being closed in sibling plans (27-09, etc.)
- No blockers for the remaining Phase 27 plans.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*
