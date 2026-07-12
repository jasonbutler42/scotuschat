---
phase: 29-historical-corpus-import
plan: 03
subsystem: pipeline
tags: [python, sqlalchemy, csv, dateutil, idempotency, court-tenures]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import (Plan 01)
    provides: schema foundation (Person.oyez_speaker_id, data/corpus/ directory, python-dateutil)
provides:
  - "pipeline/commands/import_justices_csv.py: reconstruct_full_name(), MANUAL_NAME_OVERRIDES, run_import_justices_csv()"
  - "import-justices CLI subcommand (with --csv) registered in pipeline/__main__.py"
  - "Full historical justice roster seeding: upgrade-in-place for the 13 seed_aliases.py Person rows + create-new for the rest, with dual court_tenures for elevated justices"
affects: [29-historical-corpus-import Plan 04/05/06 (corpus importer needs the full bench roster to resolve bench speakers across 1955-2019)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "reconstruct_full_name(first, middle, last, suffix) is a plain concatenation (no punctuation synthesis) because the source CSV's 'Middle Name or Initial' column already embeds the trailing period for single-initial values"
    - "Two-section CSV parsing via a single csv.reader pass that tracks 'current section header' state, switching the court_tenures.seat value used for subsequent data rows"
    - "Per-file dedicated async engine/session pytest fixture (isolated_session) as an alternative to conftest.py's session-scoped engine fixture, for test files with 2+ DB-writing async tests on Windows"

key-files:
  created:
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_import_justices_csv.py
  modified:
    - pipeline/__main__.py

key-decisions:
  - "reconstruct_full_name needs no MANUAL_NAME_OVERRIDES entries — all 13 existing seed_aliases.py justices reconstruct byte-identically from the real CSV's raw First/Middle/Last/Suffix values via plain string concatenation; the override mapping is kept empty but in place as a documented escape hatch"
  - "court_tenures.seat value for CSV-imported justices is the CSV section header text itself ('Chief Justice' / 'Associate Justice'), per RESEARCH.md Open Question 2 — no numbered-seat data exists in this CSV"
  - "Person.birthdate/Death Date/Reason Left CSV columns are read by the row parser but intentionally not written to any model field — out of this plan's explicit field list (full_name, name parts, is_justice, and the 4 CourtTenure fields only)"
  - "Task 2's DB-integration tests use a dedicated per-test engine/session fixture (isolated_session) instead of conftest.py's session-scoped `engine` fixture, to avoid a pre-existing Windows asyncpg + pytest-asyncio stale-event-loop failure (same symptom already present, independently of this plan, in pipeline/tests/test_pipeline_run.py::test_rerun_creates_new_rows) — conftest.py itself was left untouched"

patterns-established:
  - "Per-file dedicated engine/session pytest fixture for DB-heavy test modules on this Windows dev environment, avoiding shared session-scoped engine reuse across pytest-asyncio's function-scoped event loops"

requirements-completed: [CORPUS-01, CORPUS-11]

coverage:
  - id: D1
    description: "reconstruct_full_name() reproduces all 13 existing seed_aliases.py Person.full_name literals byte-for-byte from CSV-shaped name parts, with documented no-middle/no-suffix edge case handling"
    requirement: "CORPUS-01"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_justices_csv.py -k reconstruct (17 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_import_justices_csv() upgrades an existing Person row in place (is_justice=True + one CourtTenure) matched by exact full_name, without duplicating the row or touching role_id/speaker_alias"
    requirement: "CORPUS-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_upgrades_existing_person_in_place"
        status: pass
    human_judgment: false
  - id: D3
    description: "A justice appearing in both the Chief and Associate CSV sections gets both court_tenures rows auto-created for one Person row, not flagged for manual review"
    requirement: "CORPUS-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_elevated_justice_gets_two_tenures"
        status: pass
    human_judgment: false
  - id: D4
    description: "Re-running the same CSV import twice creates zero duplicate people and zero duplicate tenures, including for the elevated-justice dual-tenure case"
    requirement: "CORPUS-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_idempotent_rerun_creates_no_duplicates"
        status: pass
    human_judgment: false
  - id: D5
    description: "Blank 'Date Service Terminated' CSV cells (currently-active justices) yield CourtTenure.end_date = None; the command never writes role_id and never creates speaker_alias rows"
    requirement: "CORPUS-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_blank_end_date_yields_none, ::test_new_person_never_gets_role_id_or_speaker_alias"
        status: pass
    human_judgment: false
  - id: D6
    description: "import-justices subcommand (with --csv) is registered in the pipeline CLI and dispatches to run_import_justices_csv"
    requirement: "CORPUS-01"
    verification:
      - kind: unit
        ref: "python -m pipeline import-justices --help (exit 0, lists --csv); python -m pipeline --help (lists import-justices)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-09
status: complete
---

# Phase 29 Plan 03: Historical Corpus Import — Justice CSV Import Summary

**A new `import-justices` CLI command upgrades the 13 pre-existing seed_aliases.py Person rows in place (is_justice=True + court_tenures) and creates the remaining historical justices, with idempotent check-before-insert dedup and auto dual-tenure handling for elevated justices.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-09 (this session)
- **Completed:** 2026-07-09
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `reconstruct_full_name(first, middle, last, suffix)` reproduces all 13 existing `seed_aliases.py` `Person.full_name` literals byte-for-byte from the real justices tenure CSV's raw name parts — verified against the actual CSV row data (`C:\workspace\scotuschat\supreme_court_justices_sections.csv`) rather than assumed; no manual overrides were needed since the CSV's "Middle Name or Initial" column already embeds the trailing period for single-initial values (e.g. "G.", "M.")
- `run_import_justices_csv()` parses the CSV's two sections (Chief Justices, then Associate Justices), dedups people by exact `full_name` match (D-02), upgrades matching existing rows in place (`is_justice=True` + a new `CourtTenure`) without touching `role_id` or `speaker_alias` (D-03), and creates new justices with structured name parts otherwise
- `CourtTenure` rows are check-before-inserted on `(person_id, seat, start_date)`, so justices elevated from Associate to Chief Justice (e.g. Rehnquist, Rutledge) automatically get both tenure rows, and re-running the whole import is fully idempotent (D-04/D-08)
- `--csv` path is validated to exist before any DB session opens (T-29-08 input validation); defaults to `data/corpus/supreme_court_justices_sections.csv`, matching Plan 01's `data/corpus/` scaffolding
- `import-justices` subcommand registered in `pipeline/__main__.py` following the existing `ingest`/`parse`/`resolve`/`seed-aliases` subparser and dispatch pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: full_name reconstruction from CSV parts** - `c0b752ac` (feat)
2. **Task 2: Justice CSV import command (upgrade-in-place + create, idempotent, multi-tenure)** - `a18e17d3` (feat)
3. **Task 3: Register import-justices subcommand in the pipeline CLI** - `a9d0f329` (feat)

## Files Created/Modified
- `pipeline/commands/import_justices_csv.py` - `reconstruct_full_name()`, `MANUAL_NAME_OVERRIDES` (empty, documented escape hatch), `_parse_optional_date()`, `_iter_csv_rows()`, `run_import_justices_csv()`
- `pipeline/tests/test_import_justices_csv.py` - 17 reconstruction tests (all 13 seeded justices + edge cases) + 6 integration tests (upgrade-in-place, elevated dual-tenure, idempotent re-run, blank end_date, role_id/speaker_alias invariant, missing-path validation)
- `pipeline/__main__.py` - `import-justices` subparser (`--csv` flag) + dispatch branch, plus the new import at the top

## Decisions Made
- No `MANUAL_NAME_OVERRIDES` entries were needed — verified all 13 seed_aliases.py justices reconstruct correctly via plain concatenation directly against the real CSV data
- `court_tenures.seat` for CSV-imported rows uses the CSV section header text itself ("Chief Justice" / "Associate Justice"), per RESEARCH.md's Open Question 2 recommendation
- CSV columns `Birthdate`, `Death Date`, and `Reason Left` are read by the row parser (needed to correctly delimit CSV structure) but are not written to any Person/CourtTenure field — this plan's explicit field list doesn't include them, and adding them would be scope creep beyond the locked decisions
- Task 2's integration tests use a dedicated per-test engine/session fixture (`isolated_session`) rather than conftest.py's shared session-scoped `engine` fixture — see Deviations below

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dedicated per-test engine fixture to avoid a pre-existing Windows asyncpg/pytest-asyncio stale-event-loop failure**
- **Found during:** Task 2 (writing the integration test suite)
- **Issue:** Running 2+ of this file's DB-writing async tests together (using conftest.py's session-scoped `engine` + `async_session` fixtures, as `pipeline/tests/test_ingest.py` does) triggered `AttributeError: 'NoneType' object has no attribute 'send'` inside asyncpg's Proactor transport on the second DB-touching test — the exact same failure already present, independently of this plan, in `pipeline/tests/test_pipeline_run.py::test_rerun_creates_new_rows` (one of the 14 documented pre-existing failures). Root cause: the session-scoped engine's asyncpg connection pool binds to whichever event loop was active on first use; pytest-asyncio's default function-scoped event loop gives each subsequent test a new loop, breaking the pool.
- **Fix:** Added a function-scoped `isolated_session` fixture local to `pipeline/tests/test_import_justices_csv.py` that creates its own dedicated engine per test (disposed after) instead of reusing conftest.py's shared `engine` fixture. `conftest.py` itself was not modified — this is scoped entirely to the new test file.
- **Files modified:** `pipeline/tests/test_import_justices_csv.py`
- **Verification:** `python -m pytest pipeline/tests/test_import_justices_csv.py -x -q` — all 23 tests pass together (previously failed at the 2nd DB test); re-running twice in a row confirms no residual pollution.
- **Committed in:** `a18e17d3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, test-infra-only)
**Impact on plan:** Test-only change, scoped to the new test module; no production code, conftest.py, or other test files touched. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None — no external service configuration required. The actual justices tenure CSV file itself is an operator-supplied local input (per D-20/D-21, gitignored under `data/corpus/`) and was not committed to the repo; running `python -m pipeline import-justices` against real data requires the operator to place the CSV at `data/corpus/supreme_court_justices_sections.csv` (or pass `--csv <path>`) first — this is unchanged from Plan 01's established convention, not new setup work from this plan.

## Next Phase Readiness
- The full historical justice roster (all 13 existing seed_aliases.py justices upgraded + all remaining historical justices, with tenure/appointment data) can now be seeded in one idempotent CLI command before the corpus importer (Plan 04/05/06) runs.
- Plan 04+ can now resolve bench speakers across all 65 terms (1955-2019) against a complete `court_tenures` table, once an operator runs `python -m pipeline import-justices` against the real CSV.
- Verified: `python -m pytest pipeline/tests/test_import_justices_csv.py -q` (23/23 pass), `python -m pipeline import-justices --help` (exit 0, lists `--csv`), `python -m pipeline --help` (lists `import-justices`). Full `pipeline/tests/` suite run: 104 passed, 14 failed — exactly the pre-existing, phase-29-unrelated failures already documented (test_ingest.py, test_parse.py, test_pipeline_run.py, test_resolve.py, test_seed_aliases.py); no regressions introduced.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: pipeline/commands/import_justices_csv.py
- FOUND: pipeline/tests/test_import_justices_csv.py
- FOUND: pipeline/__main__.py
- FOUND: .planning/phases/29-historical-corpus-import/29-03-SUMMARY.md
- FOUND commit: c0b752ac (Task 1)
- FOUND commit: a18e17d3 (Task 2)
- FOUND commit: a9d0f329 (Task 3)
