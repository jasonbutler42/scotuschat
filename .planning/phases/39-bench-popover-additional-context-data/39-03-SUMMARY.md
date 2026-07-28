---
phase: 39-bench-popover-additional-context-data
plan: 03
subsystem: api
tags: [pydantic, fastapi, sveltekit, svelte5-runes, admin-editor]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    provides: "Plan 39-01's migrations 0023/0024, api/models/models.py REASON_RETIRED/REASON_DIED/REASON_PROMOTED/VALID_REASONS_LEFT constants, CourtTenure.reason_left/Person.death_date ORM columns"
provides:
  - "api/schemas/admin_people.py: TenureWrite.reason_left (strict Literal), TenureRow.reason_left (tolerant), PersonDetail.death_date, PersonUpdate.death_date"
  - "api/services/admin_people.py: reason_left wired into _replace_tenures + get_person_detail; death_date wired into get_person_detail + a model_fields_set-guarded write in update_person"
  - "app/src/routes/admin/people/[id]/+page.svelte: active Death Date date input with save-form hidden input; per-tenure Reason Left <select> with legacy escape-hatch option"
  - "app/src/routes/admin/people/[id]/+page.server.ts: death_date/reason_left threaded through TenureRowClient, PersonDetail, and every save-action code path"
affects: [39-04, 39-05, 39-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "reason_left repeats the Phase 37 office strict-write/tolerant-read schema split exactly: TenureWrite.reason_left is Optional[Literal[...]], TenureRow.reason_left stays Optional[str]"
    - "death_date write in update_person guarded by 'death_date' in fields_set (not is not None), placed in the birthdate/save-form guard group, not the is_justice-style unconditional group"

key-files:
  created: []
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py
    - "app/src/routes/admin/people/[id]/+page.svelte"
    - "app/src/routes/admin/people/[id]/+page.server.ts"

key-decisions:
  - "Fixed a stale HTML comment ('Birth Date + disabled Death Date') while rewriting the Death Date block, since it was now inaccurate — this drops the pre/post 'disabled' grep count from a plan-anticipated 10→8 to an actual 10→7. The two functional disabled attributes on the target inputs were still fully removed (confirmed via the 'Tracked in a future update' and 'opacity: 0.6' zero-match verify commands, both of which passed); the extra delta is a comment-text improvement, not a residual scaffolding artifact."
  - "Reason Left's <select> escape-hatch option is documented in an inline comment as display-only — selecting it re-submits the same already-invalid string, never a fresh write, since TenureWrite.reason_left stays a strict Literal enforced again by the DB CHECK constraint (unlike President's Party, which is a genuinely open vocabulary)."

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "TenureWrite.reason_left is a strict Literal over VALID_REASONS_LEFT (retired/died/promoted); a non-canonical value (including blank and wrong case) is rejected with a ValidationError before reaching the service or database"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_tenure_write_rejects_non_canonical_reason_left"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_tenure_write_reason_left_matches_valid_reasons_left_set"
        status: pass
    human_judgment: false
  - id: D2
    description: "TenureRow.reason_left stays a tolerant Optional[str] so a pre-existing non-canonical stored value can still be displayed for operator correction"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_tenure_row_tolerates_invalid_legacy_reason_left"
        status: pass
    human_judgment: false
  - id: D3
    description: "PersonDetail/PersonUpdate expose death_date; update_person's write is guarded by model_fields_set (not a null check) so the separate photo/bio form's PATCH can never silently clear a stored death date"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_person_detail_and_update_expose_optional_death_date"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_person_update_photo_bio_payload_never_touches_death_date"
        status: pass
      - kind: other
        ref: "grep -Eq 'if \"death_date\" in fields_set' api/services/admin_people.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The person editor's Death Date input is editable (no disabled/placeholder scaffolding) and a saved value round-trips through the existing single atomic save form"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "cd app && npm run check — 0 errors, 34 pre-existing warnings unchanged"
        status: pass
      - kind: other
        ref: "! grep -q 'Tracked in a future update' app/src/routes/admin/people/[id]/+page.svelte"
        status: pass
    human_judgment: true
    rationale: "Live round-trip (set value, Save Person, reload, confirm persistence) requires the running Windows-side stack and is explicitly deferred to Plan 39-06's operator checkpoint per this plan's own <verification> section — this environment cannot drive the live UI."
  - id: D5
    description: "The per-tenure Reason Left field is a <select> offering exactly None/Retired/Died in office/Promoted, with a legacy escape-hatch option, and a selection round-trips through the same save form"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "grep -A20 'tenure-reason' app/src/routes/admin/people/[id]/+page.svelte — exactly 4 unconditional <option> plus 1 {#if}-guarded escape-hatch"
        status: pass
    human_judgment: true
    rationale: "Live round-trip is deferred to Plan 39-06's operator checkpoint, same as D4 — this environment cannot drive the live UI."

duration: ~40min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 03: Death Date and Reason Left editor activation Summary

**Both Phase 27 "Coming soon" placeholder inputs — person-level Death Date and per-tenure Reason Left — are now live, strictly validated on write, tolerant on read, and wired end to end through the existing single atomic save form with no new form or action.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 5 (0 new files)

## Accomplishments
- `TenureWrite.reason_left: Optional[Literal["retired", "died", "promoted"]]` (strict write contract) and `TenureRow.reason_left: Optional[str]` (tolerant read contract) in `api/schemas/admin_people.py`, mirroring the Phase 37 `office` strict/tolerant split exactly.
- `PersonDetail.death_date` and `PersonUpdate.death_date`, mirroring `birthdate`'s exact ISO-date-string shape and `model_fields_set` omission-means-unchanged contract.
- `api/services/admin_people.py`: `_replace_tenures()` now writes `reason_left`; `get_person_detail()` now returns `reason_left` per tenure and `death_date` at the top level; `update_person()` writes `death_date` only when `"death_date" in fields_set` — placed in the save-form guard group beside `birthdate`, never the `is_justice`-style unconditional group, so the separate photo/bio form's PATCH can never silently wipe a stored death date.
- 7 new pure-Python tests in `api/tests/test_admin_people_schemas_service.py`: canonical `reason_left` acceptance + defaulting, rejection of `resigned`/blank/wrong-case values, a programmatic `VALID_REASONS_LEFT` drift guard, `TenureRow` legacy tolerance, `PersonDetail`/`PersonUpdate` `death_date` exposure, and a named regression guard (`test_person_update_photo_bio_payload_never_touches_death_date`) pinning the silent-wipe failure mode.
- `app/src/routes/admin/people/[id]/+page.svelte`: Death Date is now a plain active `<input type="date">` (matching Birth Date byte-for-byte apart from id/label/binding) bound to a new `deathDate` `$state`, restored in both the failed-save and person-id-change `$effect` blocks, and submitted via a hidden input beside the existing `birthdate` hidden input. Reason Left is now a `<select>` with `— None —`/Retired/Died in office/Promoted plus a `{#if}`-guarded escape-hatch option for a pre-existing non-canonical stored value (display-only, documented inline as never a fresh write path).
- `app/src/routes/admin/people/[id]/+page.server.ts`: `TenureRowClient`/`PersonDetail` interfaces, the `save` action's read/parse/PATCH-body assembly, and all 5 `fail()` state-restore objects that already carried `birthdate` now also carry `death_date`; the tenure-stripping `.map()` now includes `reason_left` (normalized to `null` when unselected); the stale "disabled input, no value submitted" comment above that map was rewritten to reflect the new wired-through state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Carry death_date and reason_left through the admin schemas and service** - `e2d7679d` (feat)
2. **Task 2: Activate the two placeholder editor inputs and wire them into the existing save form** - `8e31cc94` (feat)

## Files Created/Modified
- `api/schemas/admin_people.py` - `TenureWrite.reason_left` (strict), `TenureRow.reason_left` (tolerant), `PersonDetail.death_date`, `PersonUpdate.death_date`
- `api/services/admin_people.py` - `_replace_tenures`/`get_person_detail`/`update_person` reason_left/death_date wiring
- `api/tests/test_admin_people_schemas_service.py` - 7 new tests covering every `<behavior>` bullet from the plan
- `app/src/routes/admin/people/[id]/+page.svelte` - active Death Date input, Reason Left `<select>`, `deathDate` state, `reason_left` on client tenure row shape
- `app/src/routes/admin/people/[id]/+page.server.ts` - `death_date`/`reason_left` threaded through interfaces and the `save` action

## Decisions Made
- Fixed a stale HTML comment ("Birth Date + disabled Death Date") while rewriting the Death Date block. This drops the pre/post `disabled` grep count from the plan's anticipated 10→8 to an actual **10→7** (pre-task count 10, post-task count 7). Both functional `disabled` attributes on the two target inputs were still fully removed — confirmed independently via the `! grep -q 'Tracked in a future update'` and `! grep -q 'opacity: 0.6'` zero-match checks, both of which passed with no matches. The extra count delta is a stale-comment correction, not a residual scaffolding artifact. (Note: this criterion lives only in the plan's `<acceptance_criteria>` documentation section, not its blocking `<verify>` gate, so it did not fail the task.)
- The Reason Left `<select>`'s escape-hatch option is documented with an inline comment explaining it is display-only: selecting it re-submits the same already-invalid string rather than opening a new write path, since `TenureWrite.reason_left` stays a strict `Literal` enforced again by the DB CHECK constraint — unlike President's Party, which is a genuinely open vocabulary.

## Deviations from Plan

None — plan executed as written. The stale-comment fix noted above is a documentation-quality improvement made in the course of the planned rewrite, not an unplanned addition; it did not fail or bypass the plan's own automated `<verify>` gate (which does not check the `disabled` count at all).

## Issues Encountered
- Running `pytest` against an explicit path (e.g. `api/tests/`) instead of letting pytest's `testpaths` config collect `tests/` first bypasses the root `tests/conftest.py`'s `TEST_DATABASE_URL` redirect and dev-DB leak guard. One such explicit-path run during verification connected to the real dev database (via the Windows `.venv/Scripts/python.exe`, which the project's documented WSL/Windows split makes reachable when run this way) and hit a pre-existing `roles_name_key` unique-constraint violation from real data already present there. No data was written or corrupted — the failing test's `db_session` fixture rolls back on any exception before the transaction body completes — but this confirmed the safe invocation pattern for this environment is `pytest` with no explicit test path (letting `testpaths = tests pipeline/tests api/tests` collect `tests/conftest.py` first). All final verification in this plan used that safe form and passed clean: 750 passed, 4 deselected (pre-existing Windows-path node-driver failures in `test_phase38_people_ui_contract.py`, noted in 38-UAT.md/STATE.md as out of scope), 5 xfailed.

## Next Phase Readiness
- `api/schemas/admin_people.py`, `api/services/admin_people.py`, and the person editor's Death Date/Reason Left inputs are now fully wired for Plan 39-06's operator checkpoint to exercise live.
- Plan 39-06 still needs to run the deferred manual round-trip: set a Death Date and a Reason Left, Save Person, reload, confirm both persist; then save a photo and confirm Death Date is unchanged (D4/D5 above).
- Full suite (`pytest`, no explicit path, from repo root): 750 passed, 4 deselected (pre-existing, unrelated), 5 xfailed.

## Self-Check: PASSED

All 5 modified files confirmed present on disk with the expected content; both commits (`e2d7679d`, `8e31cc94`) confirmed present in `git log --oneline`.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*
