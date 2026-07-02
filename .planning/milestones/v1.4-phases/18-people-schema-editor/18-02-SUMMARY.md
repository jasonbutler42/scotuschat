---
phase: 18-people-schema-editor
plan: "02"
subsystem: api
tags: [schema, service, pydantic, people, is_justice, admin]
status: complete

dependency_graph:
  requires: [18-01 (people.is_justice DB column, Person.is_justice ORM)]
  provides: [PersonDetail.is_justice, PersonUpdate.is_justice, PersonListItem.is_justice, service read/write paths for is_justice]
  affects: [api/schemas/admin_people.py, api/services/admin_people.py, api/tests/test_admin_people_schemas_service.py]

tech_stack:
  added: []
  patterns: [Pydantic Optional[bool] for leave-unchanged semantics, explicit dict key inclusion to prevent silent default on reload (Pitfall 2), None-guarded conditional write (D-08)]

key_files:
  created: []
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py

decisions:
  - "PersonDetail.is_justice: bool = False (backward compatible default, Phase 18 addition comment)"
  - "PersonUpdate.is_justice: Optional[bool] = None — None means leave unchanged (D-08/D-11), consistent with all other Optional fields"
  - "PersonListItem.is_justice: bool = False (directory badge, D-10)"
  - "get_person_detail return dict explicitly includes is_justice key (Pitfall 2 — missing key would silently default on reload)"
  - "update_person guards write with 'if body.is_justice is not None' — role_id and tenures preserved when is_justice set False (D-06, D-07)"

metrics:
  duration_min: 12
  completed_date: "2026-06-29"
  tasks_completed: 3
  files_changed: 3
---

# Phase 18 Plan 02: is_justice Schema and Service Wiring Summary

**One-liner:** Three Pydantic schemas extended with is_justice, both service read paths return the field explicitly, update_person writes it through a None-guarded conditional, and 24 no-DB schema/service tests all pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add is_justice to PersonDetail, PersonUpdate, PersonListItem schemas | f7e58907 | api/schemas/admin_people.py |
| 2 | Read and write is_justice in the people service layer | 740440f0 | api/services/admin_people.py |
| 3 | Extend schema/service tests for is_justice | 43e6e99f | api/tests/test_admin_people_schemas_service.py |

## What Was Built

**`api/schemas/admin_people.py` — three schema additions:**
- `PersonDetail.is_justice: bool = False` — default False keeps backward compatibility with any constructor call that omits it; `# Phase 18 addition — migration 0010` comment added
- `PersonUpdate.is_justice: Optional[bool] = None` — added to the mass-assignment allow-list; None means "leave unchanged" per the existing PersonUpdate convention (D-08, D-11). This is the ONLY new field added to the allow-list.
- `PersonListItem.is_justice: bool = False` — for the directory badge (D-10)
- All three class docstrings updated with Phase 18 addition notes

**`api/services/admin_people.py` — three service path changes:**
- `get_person_detail`: added `"is_justice": person.is_justice` to the returned dict (alongside Phase 9 keys) with Pitfall 2 guard comment — prevents silent default when `PersonDetail(**p)` is constructed in the router
- `list_people`: added `"is_justice": person.is_justice` to each row dict in the list comprehension
- `update_person`: added `if body.is_justice is not None: person.is_justice = body.is_justice` — conditional write with D-06/D-07 comment confirming role_id and CourtTenure rows are NOT cleared when is_justice is set False

**`api/tests/test_admin_people_schemas_service.py` — three new tests:**
- `test_person_update_is_justice_optional`: asserts `PersonUpdate().is_justice is None`, `PersonUpdate(is_justice=True).is_justice is True`, `PersonUpdate(is_justice=False).is_justice is False`
- `test_person_detail_is_justice_default_false`: asserts default False and explicit True both work
- `test_person_list_item_is_justice`: asserts `PersonListItem(id=1, full_name='X', missing=[], is_justice=True).is_justice is True`
- All 24 tests pass (21 existing + 3 new), no DB required

## Verification

- `python -m pytest api/tests/test_admin_people_schemas_service.py -q` → 24 passed in 0.44s
- `inspect.getsource` confirmed: `is_justice` in both service read paths and `body.is_justice is not None` guard in update_person
- D-06/D-07: `delete(CourtTenure)` confirmed absent from `update_person` source; `role_id = None` not conditioned on `is_justice`
- T-18-MASS: Only `is_justice` added to PersonUpdate allow-list; no other Person column became writable

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan is pure schema/service/test work with no UI stubs.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. The existing X-Admin-Token guard on all `/api/admin/people` routes (T-18-AUTH) covers the is_justice read/write paths unchanged.

## Self-Check: PASSED

- api/schemas/admin_people.py: FOUND
- api/services/admin_people.py: FOUND
- api/tests/test_admin_people_schemas_service.py: FOUND
- .planning/phases/18-people-schema-editor/18-02-SUMMARY.md: FOUND
- Commit f7e58907: FOUND (schemas)
- Commit 740440f0: FOUND (service)
- Commit 43e6e99f: FOUND (tests)
