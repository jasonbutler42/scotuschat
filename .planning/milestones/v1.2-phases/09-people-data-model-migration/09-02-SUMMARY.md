---
phase: 09-people-data-model-migration
plan: "02"
subsystem: backend-service
tags: [fastapi, sqlalchemy, pydantic, derivation, tdd, people, service-layer]
status: complete

dependency_graph:
  requires:
    - "09-01: Person ORM with six nullable attributes; PersonUpdate with six new Optional fields"
    - "api/services/admin_people.py (existing update_person, get_person_detail, list_people)"
    - "api/tests/test_admin_people_schemas_service.py (existing DB-free test suite)"
  provides:
    - "_derive_full_name(first, middle, last, suffix) -> str helper (D-04)"
    - "update_person() with six column assignments + derivation guard (D-04, D-05, Pitfall 3, Pitfall 4)"
    - "get_person_detail() return dict extended with all six new keys (Pitfall 2)"
    - "list_people() sorted by last_name NULLS LAST, full_name ASC (D-07)"
    - "4 DB-free unit tests for _derive_full_name covering all behavior cases"
  affects:
    - "09-03 (SvelteKit edit form — consumes PersonDetail fields now returned by get_person_detail)"

tech_stack:
  added: []
  patterns:
    - "_derive_full_name: join(p for p in [...] if p) one-liner from CONTEXT.md Specifics"
    - "Empty-string-to-None normalization: if body.field else None (Pattern 4 from 09-PATTERNS.md)"
    - "Derivation guard: both first_name AND last_name non-empty (Pitfall 3, D-04/D-05 deviation)"
    - "SQLAlchemy .nulls_last() column method; no additional import (Pattern 6 from 09-PATTERNS.md)"
    - "TDD RED/GREEN cycle for _derive_full_name"

key_files:
  created: []
  modified:
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py

decisions:
  - "_derive_full_name requires BOTH first_name AND last_name non-empty to trigger derivation (D-04/D-05 deviation, Pitfall 3 — prevents anchor corruption from partial saves)"
  - "Empty-string normalization applied to all six new fields (Pitfall 4 — empty string -> NULL)"
  - "get_person_detail return dict explicitly includes all six new keys (Pitfall 2 — missing keys silently default to None on reload)"
  - "list_people sort: last_name NULLS LAST, full_name ASC — secondary sort ensures stable ordering among null-last_name records"

metrics:
  duration_seconds: 119
  completed_date: "2026-06-19"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 9 Plan 02: Service Layer — _derive_full_name, update_person, get_person_detail, list_people Summary

**One-liner:** Service layer extended with _derive_full_name TDD helper, six-field column assignments + both-parts derivation guard in update_person, six-key return dict in get_person_detail, and last_name NULLS LAST sort in list_people.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add _derive_full_name helper (test-first) | 9cd2179 | api/services/admin_people.py, api/tests/test_admin_people_schemas_service.py |
| 2 | Wire derivation and six column assignments into update_person; extend get_person_detail return dict | 2aaec13 | api/services/admin_people.py |
| 3 | Change list_people sort to last_name NULLS LAST, full_name ASC | 59ca693 | api/services/admin_people.py |

## What Was Built

**`_derive_full_name` helper** (`api/services/admin_people.py`): Module-level private function added below `_replace_tenures`. Joins non-blank parts using `" ".join(p for p in [first, middle or "", last, suffix or ""] if p)`. Blank/None middle and suffix are omitted; output has no double or trailing spaces. Implements D-04.

**`update_person()` column assignments** (`api/services/admin_people.py`): Six `person.<field> = body.<field> if body.<field> else None` assignments added after the existing `photo_url` normalization line. Empty strings normalize to NULL (Pitfall 4). Derivation branch guarded on `body.first_name and body.last_name` (both truthy) — a deliberate deviation from D-04's "first_name only" literal text, documented with a code comment, to prevent the Pitfall 3 anchor-corruption scenario.

**`get_person_detail()` return dict** (`api/services/admin_people.py`): Six new keys appended to the return dict literal — `first_name`, `last_name`, `middle_name`, `name_suffix`, `appointing_president`, `appointing_president_party` — each reading directly from the `person` ORM object. Prevents the Pitfall 2 silent-None reload scenario.

**`list_people()` sort** (`api/services/admin_people.py`): `.order_by(Person.full_name)` replaced with `.order_by(Person.last_name.nulls_last(), Person.full_name.asc())`. No new import — `.nulls_last()` is a SQLAlchemy 2.0.51 column method. Secondary `full_name.asc()` provides stable ordering among records sharing a last_name or having NULL last_name.

**Unit tests** (`api/tests/test_admin_people_schemas_service.py`): 4 new DB-free tests covering all four behavior cases from the plan spec. `_derive_full_name` added to `test_service_import` import list. 21 total tests pass.

## Verification Results

All automated checks passed:

- `pytest api/tests/test_admin_people_schemas_service.py -x -q`: **21 passed** (17 existing + 4 new)
- Task 2 source assertion (assigns, derivation call, guard regex, dict keys): **OK**
- Task 3 source assertion (nulls_last present, full_name.asc present, old sort absent): **OK**
- `from api.services import admin_people` module import: **OK**

## Deviations from Plan

### Auto-documented Deviations

**1. [Documented deviation from D-04 literal text] Both-parts derivation guard**
- **Context:** D-04 says "when first_name is non-empty." The plan and RESEARCH.md both note this is deliberately changed.
- **Decision:** Derivation fires only when BOTH `first_name` AND `last_name` are non-empty. This is the resolved open question from 09-RESEARCH.md — user confirmed "Both-field guard adopted per Pitfall 3."
- **Code comment:** Added to `update_person()` explaining the deviation from D-04 literal text.
- **Impact:** Partial saves (e.g., `first_name="Amy"` without `last_name`) leave `full_name` unchanged, preserving the resolution anchor. This is the correct behavior per D-05 intent.

No other deviations — plan executed as written.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's threat model covers.

- T-09-05 (Tampering — derivation guard): Mitigated. `if body.first_name and body.last_name:` guard prevents partial-save anchor corruption.
- T-09-06 (Repudiation — empty-string normalization): Mitigated. All six fields use `if body.field else None` pattern; PostgreSQL IS NULL semantics preserved.
- T-09-07 (Information disclosure — get_person_detail): Accepted. Admin-auth gate unchanged; no new public exposure.

## Known Stubs

None. All six fields are fully wired: assigned in `update_person()`, returned in `get_person_detail()`. The round-trip is complete at the service layer. 09-03 wires the SvelteKit form layer.

## TDD Gate Compliance

Task 1 followed the RED/GREEN cycle:
- RED: Tests added referencing `_derive_full_name` before it existed; `ImportError` confirmed failure.
- GREEN: Helper implemented; 21 tests pass including all 4 new cases.
- No REFACTOR step needed (implementation is a clean 1-line join expression).

## Self-Check: PASSED

- `api/services/admin_people.py` contains `_derive_full_name`: FOUND
- `api/tests/test_admin_people_schemas_service.py` contains `test_derive_full_name_first_middle_last`: FOUND
- Commits 9cd2179, 2aaec13, 59ca693 all present in git log: FOUND
