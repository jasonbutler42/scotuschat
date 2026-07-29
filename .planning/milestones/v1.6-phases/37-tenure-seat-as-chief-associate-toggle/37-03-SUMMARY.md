---
phase: 37-tenure-seat-as-chief-associate-toggle
plan: "03"
subsystem: backend
tags: [sqlalchemy, pydantic, fastapi, pipeline, tdd]

requires:
  - phase: 37-02
    provides: nullable seat-to-office rename revision, audited normalization CLI, named binary office check and NOT NULL contraction
provides:
  - CourtTenure.office ORM column + OFFICE_CHIEF/OFFICE_ASSOCIATE/VALID_OFFICES constants + office_title() formal-title helper
  - Strict TenureWrite submitted-tenure schema and legacy-tolerant TenureRow read schema
  - Validated atomic _replace_tenures with no blank-row skip
  - Canonical chief/associate CSV import with (person_id, office, start_date) dedup
affects: [37-04, 37-05, admin-people-api, justice-csv-import]

tech-stack:
  added: []
  patterns: [strict-write/tolerant-read schema split, exhaustive canonical-to-display title helper, validate-before-mutate replace-all]

key-files:
  created: []
  modified:
    - api/models/models.py
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py
    - api/tests/test_admin_people_phase25.py
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_import_justices_csv.py

key-decisions:
  - "CourtTenure.office declares its own named CheckConstraint (ck_court_tenures_office) matching migration 0021's DB-level constraint, for ORM-level self-documentation — it performs no DDL of its own (Alembic remains sole DDL authority)."
  - "TenureWrite (strict, Literal['chief','associate']) and TenureRow (tolerant Optional[str]) are two separate schemas rather than one schema with mode flags, so a write can never accidentally reuse response tolerance (D-03/D-04 and D-11 coexist without cross-contamination)."
  - "_replace_tenures validates every row's office against VALID_OFFICES before the DELETE executes, as defense-in-depth alongside the TenureWrite Pydantic Literal and the DB CHECK constraint."
  - "_bench_role_and_missing_tenure now returns office_title(t.office) (the formal display title) rather than the raw storage value, since 'chief'/'associate' alone are not acceptable UI role labels (D-15)."

patterns-established:
  - "Canonical vs. display split: one office_title() helper is the single source of truth mapping chief/associate to Chief Justice/Associate Justice; every projection in this plan's scope routes through it rather than re-deriving the formal title."
  - "Strict-write / tolerant-read schema pair: a write-path schema enforces the invariant with a Literal type; a separate read-path schema stays permissive so invalid/legacy data can still be displayed for correction, never for re-acceptance."

requirements-completed: [PEOPLE-08]

coverage:
  - id: D1
    description: Every active backend and import write path accepts exactly chief or associate and persists/serializes as office end to end.
    requirement: PEOPLE-08
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_tenure_write_rejects_blank_office, ::test_tenure_write_rejects_missing_office, ::test_tenure_write_rejects_unknown_office_values"
        status: pass_by_static_review
      - kind: unit
        ref: "pipeline/tests/test_import_justices_csv.py::test_upgrades_existing_person_in_place, ::test_elevated_justice_gets_two_tenures"
        status: pass_by_static_review
    human_judgment: false
  - id: D2
    description: Associate-to-Chief elevation remains two dated tenure rows after the canonical-office conversion.
    requirement: PEOPLE-08
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_justices_csv.py::test_elevated_justice_gets_two_tenures, ::test_idempotent_rerun_creates_no_duplicates"
        status: pass_by_static_review
    human_judgment: false
  - id: D3
    description: Response schemas can still surface an invalid/original office value for operator correction without the write path ever accepting it.
    requirement: PEOPLE-08
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_tenure_row_tolerates_invalid_legacy_office"
        status: pass_by_static_review
    human_judgment: false

duration: 25min
completed: 2026-07-21
status: complete
---

# Phase 37 Plan 03: Backend/Import Office Contract Summary

**CourtTenure.office replaces free-text seat end to end across the ORM, admin-people schemas/service, and the justice CSV importer, with a strict write / tolerant read schema split and validated atomic tenure replacement**

## Performance

- **Duration:** 25 min
- **Completed:** 2026-07-21
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Renamed `CourtTenure.seat` to `CourtTenure.office` (NOT NULL, named `ck_court_tenures_office` CHECK matching migrations 0020/0021), added `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`/`VALID_OFFICES` constants and the exhaustive `office_title()` formal-title helper (D-01, D-15, D-17).
- Split the admin-people tenure schema into `TenureWrite` (strict submitted contract — `office: Literal["chief", "associate"]`, used by `PersonUpdate.tenures`) and `TenureRow` (legacy-tolerant read response — `office: Optional[str]`, used by `PersonDetail.tenures`), so D-03/D-04 (strict writes) and D-11 (tolerant display of invalid originals) coexist without either compromising the other.
- Hardened `_replace_tenures`: validates every submitted row's `office` against `VALID_OFFICES` before the delete executes (no partial mutation on an invalid row), removed the old blank-row skip (every submitted row is now inserted — an empty list is the only way to represent "no tenures"), and writes/serializes `office` throughout.
- `_bench_role_and_missing_tenure` now returns the formal `office_title()` projection (e.g. "Chief Justice") instead of the raw storage value, preserving its existing inclusive date-window and no-fallback missing-tenure semantics (D-15).
- Converted `pipeline/commands/import_justices_csv.py` to emit canonical `chief`/`associate` from CSV section classification, renamed `seat`-named locals/comments to `office`, and changed the idempotency/dedup key from `(person_id, seat, start_date)` to `(person_id, office, start_date)` — elevated-justice imports still produce two separate tenure rows (D-02, D-04).
- Updated all three focused test modules in scope to the new canonical `office` shape, including new coverage in `test_admin_people_schemas_service.py` for blank/missing/legacy-string office rejection on write and legacy-value tolerance on read.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define canonical model and strict request contracts** - `c0ac042f` (feat)
2. **Task 2: Enforce validated atomic tenure replacement** - `76dc3e6f` (feat)
3. **Task 3: Convert Justice CSV import to canonical Office** - `859bffd1` (feat)

## Files Created/Modified

- `api/models/models.py` - `CourtTenure.office` column + named CHECK constraint; `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`/`VALID_OFFICES`/`OFFICE_TITLES`/`office_title()`.
- `api/schemas/admin_people.py` - New `TenureWrite` (strict) schema; `TenureRow` narrowed to the legacy-tolerant read shape; `PersonUpdate.tenures` retyped to `list[TenureWrite]`.
- `api/services/admin_people.py` - `_replace_tenures` validates-before-mutate and drops the blank-row skip; `get_person_detail` serializes `office`; `_bench_role_and_missing_tenure` returns the formal title via `office_title()`.
- `api/tests/test_admin_people_schemas_service.py` - `TenureWrite`/`TenureRow` split coverage (canonical accept, blank/missing/legacy-string reject, legacy-value read tolerance).
- `api/tests/test_admin_people_phase25.py` - `_FakeTenure` stand-in and DB-guarded fixtures updated to `office`; `bench_role` assertions expect the formal title.
- `pipeline/commands/import_justices_csv.py` - Canonical `chief`/`associate` section classification, `office`-named locals, `(person_id, office, start_date)` dedup key.
- `pipeline/tests/test_import_justices_csv.py` - Assertions updated to canonical `office` values.

## Decisions Made

- `CourtTenure.office` declares its own named `CheckConstraint` (matching migration 0021's DB-level constraint) purely for ORM self-documentation — Alembic remains the sole DDL authority; the ORM-level constraint issues no DDL of its own.
- Kept `TenureWrite` and `TenureRow` as two distinct schemas (not one schema with a validation-mode flag) so a write path can never accidentally reuse the tolerant read schema.
- `_replace_tenures` re-validates every row's office even though `TenureWrite`'s `Literal` type already guarantees it at the Pydantic boundary — defense-in-depth per the plan's threat model (T-37-05/T-37-06), since not every possible caller of this service function necessarily constructs its tenures via the strict schema.

## Deviations from Plan

None — plan executed exactly as written. The one piece of defense-in-depth (the explicit `VALID_OFFICES` check inside `_replace_tenures`) was called out explicitly in the plan's task action and acceptance criteria, so it is not a deviation.

## Issues Encountered

- **Verification environment limitation:** the plan's `<verify>` commands call `.\.venv\Scripts\python.exe -m pytest ...`, a Windows venv (`.venv/Scripts/*.exe`, PE32+ binaries) that cannot execute in this Linux/WSL execution environment. The system Python (3.14) has no `pip`/`ensurepip` and none of `pydantic`/`sqlalchemy`/`pytest` installed, so no automated pytest run — DB-gated or otherwise — could be executed for this plan. Verification was instead performed via: (1) `python3 -m py_compile` on all seven modified files (all compile cleanly); (2) full manual line-by-line trace of every changed function against the plan's `<behavior>`/`<acceptance_criteria>` and the 37-PATTERNS.md contract; (3) a repo-wide `rg`/`grep` sweep confirming zero remaining active `seat` identifiers in the plan's scoped files (only historical/prose mentions of the word remain, e.g. describing the D-17 rename itself); (4) confirming no other production file in `api/`/`pipeline/` constructs `TenureRow`/`TenureWrite`/`CourtTenure(seat=...)` outside the files this plan owns. This is a hard environment constraint, not a plan or implementation defect — the coverage table above is marked `pass_by_static_review` rather than an executed-test status for this reason.
- **Expected temporary inter-plan breakage:** `api/services/speakers.py`, `api/services/admin_arguments.py`, and their tests (`test_speakers_service.py`, `test_admin_arguments_service.py`), plus `api/tests/test_admin_dashboard_stats.py`, still reference the now-removed `CourtTenure.seat` ORM attribute and construct `CourtTenure(seat=...)` fixtures. These files are explicitly out of this plan's `files_modified` scope and are owned by 37-04 (`speakers.py`/`admin_arguments.py` + their tests) and 37-05 (`test_admin_dashboard_stats.py` + the frontend/editor slice), per the phase's own file assignments and 37-PATTERNS.md's wave grouping. They will fail until those plans run — this is the intended sequencing (D-17's "no compatibility alias" decision means there is no bridge value to keep them passing in the interim), not a regression introduced here.
- **Local git identity:** this environment's git config (local, global, and system) had no `user.name`/`user.email` set, blocking all commits. Set via `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_NAME`/`GIT_COMMITTER_EMAIL` environment variables on each commit invocation (matching the identity — Jason Butler <jason.butler@offenpetro.com> — already used by every prior commit in this repo's history), rather than writing to git config (attempting `git config --local` also failed: `chmod` on `.git/config.lock` is not permitted on this mounted filesystem). No git config file was modified.
- **Self-corrected staging mistake:** the working tree contains substantial unrelated pre-existing staged/modified content (a draft Phase 38 plan, corpus/PDF data, memory files, etc., per the orchestrator's briefing). The first Task 1 commit attempt swept up all of that pre-existing staged content because it was already sitting in the git index before this session began. This was caught immediately after the commit (via `git show --stat`), undone with a non-destructive `git reset HEAD~1` (mixed reset — restores the index to the parent commit without touching any working-tree file content), and redone with only the three intended files explicitly `git add`-ed and verified via `git diff --cached --stat` before each of the three real commits. All three final commits (`c0ac042f`, `76dc3e6f`, `859bffd1`) touch only the seven files in this plan's `files_modified` list, confirmed via `git diff --stat` against the pre-plan commit and a `--diff-filter=D` deletion check (empty). The mixed reset did change the staged/unstaged split of the unrelated pre-existing content (some previously-staged files are now shown as unstaged) but did not alter any file's on-disk content.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 37-04 can now convert `api/schemas/speakers.py`, `api/services/speakers.py`, and `api/services/admin_arguments.py` (plus their tests) to canonical `office`/`office_title()` against this plan's completed backend contract — those files currently reference the now-removed `CourtTenure.seat` attribute and will fail until 37-04 runs (see Issues Encountered).
- Plan 37-05 can proceed with the frontend editor (Office radios), `test_admin_dashboard_stats.py`, and the final stale-`seat`-identifier audit script once 37-04 lands.
- No blockers remain specific to this plan's scope; the pytest execution-environment limitation (no Linux-compatible Python + dependencies available) applies equally to 37-04/37-05 and should be flagged to the operator before/alongside those plans if the same execution environment is used.

## Self-Check: PASSED

- All seven files listed in `key-files.modified` exist and contain the expected changes (`office` column/schema/service/importer changes verified via `grep`).
- Task commits `c0ac042f`, `76dc3e6f`, and `859bffd1` all exist in `git log`.
- All seven modified files pass `python3 -m py_compile` (syntax-valid).
- `rg -n "\bseat\b"` against the plan's seven scoped files returns only historical/prose mentions of the word "seat" (describing the D-17 rename or the legacy numbered-seat concept) — zero remaining active `seat` identifiers, keyword arguments, or dict keys.

---
*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Completed: 2026-07-21*
