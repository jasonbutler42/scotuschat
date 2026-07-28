---
phase: 39-bench-popover-additional-context-data
plan: 02
subsystem: pipeline
tags: [csv-import, sqlalchemy, alembic, pytest, asyncpg]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    provides: "Plan 39-01's court_tenures.reason_left / people.death_date columns, VALID_REASONS_LEFT, and the office_title()-shaped constant pattern this plan's _REASON_LEFT_CSV_MAP mirrors"
provides:
  - "pipeline/commands/import_justices_csv.py reads Birthdate/Death Date/Reason Left from the CSV and null-only backfills Person.birthdate, Person.death_date and CourtTenure.reason_left"
  - "_REASON_LEFT_CSV_MAP: closed 5-key CSV-raw-value -> canonical mapping with an explicit membership check (no .get() silent-collapse)"
  - "New else: arm on the existing-tenure branch performing one blank-only write (reason_left)"
  - "8 new DB-gated regression tests pinning the null-only backfill / never-overwrite / open-tenure-null / unrecognised-value / idempotency contract"
affects: [39-03, 39-04, 39-05, 39-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Membership check (value in map) rather than .get() when a recognised value legitimately maps to None, so 'recognised-but-null' stays distinguishable from 'never seen' (reasons_unmatched counter + set)"
    - "Blank-only backfill on an existing-row branch mirrors the exact shape Phase 38 established for name parts (if current is None and new is not None)"

key-files:
  created: []
  modified:
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_import_justices_csv.py

key-decisions:
  - "Ran alembic upgrade head via the Windows .venv against the real dev DB (data/corpus... unaffected) by accident early in this session, because WSL interop does not forward shell-exported env vars into the Windows python.exe subprocess (confirmed empirically: os.environ.get('DATABASE_URL') was None inside that process, so it fell back to .env's real DATABASE_URL). Migrations 0023/0024 are purely additive (nullable column + permissive CHECK constraint) so no data was at risk, and this was Plan 39-06's job anyway — but it happened one plan early and without being asked. All actual test execution for this plan used a separate ephemeral WSL-native pgserver instance + Linux Python 3.12 venv, never the real dev DB."
  - "_write_justices_csv()/_CSV_HEADER in the test file already carried the full 11-column shape (Reason Left/Birthdate/Death Date) since Phase 29 Plan 03 — the plan's Task 2 anticipated needing to extend it, but no change to the CSV-writing helper was needed; only new test functions were added."

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "A brand-new person + tenure from a CSV row with Birthdate/Death Date/Reason Left=Died gets Person.birthdate, Person.death_date, and CourtTenure.reason_left=='died' set from the CSV (D-04, D-05)"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_new_person_and_tenure_gets_birthdate_death_date_and_reason_left"
        status: pass
    human_judgment: false
  - id: D2
    description: "Re-running the importer over already-imported rows never overwrites an operator-set birthdate, death_date, or reason_left, but fills only currently-NULL values (D-06)"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_backfill_never_overwrites_operator_birthdate_or_death_date"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_backfill_never_overwrites_operator_reason_left"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_backfill_fills_blank_birthdate_and_death_date"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_backfill_fills_blank_tenure_reason_left"
        status: pass
    human_judgment: false
  - id: D3
    description: "A CSV Reason Left cell of 'Still in Office' stores reason_left=NULL, not a reason string (D-02)"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_still_in_office_tenure_has_no_reason_left"
        status: pass
    human_judgment: false
  - id: D4
    description: "A Reason Left value outside the recognised 5-key vocabulary is counted, stored as NULL, and named in the run's captured stdout rather than silently coerced"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_unrecognised_reason_left_is_null_and_reported"
        status: pass
    human_judgment: false
  - id: D5
    description: "The importer stays idempotent — a second consecutive run creates zero additional people/tenures and changes no field values (D-07)"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_second_run_creates_no_duplicates_and_changes_no_field_values"
        status: pass
      - kind: other
        ref: "manual: python -m pipeline import-justices run twice against the real CSV after seed-aliases — first run: 13 birthdates + 2 death dates backfilled, 0 tenure reasons unmatched; second run: 0/0/0 across the board"
        status: pass
    human_judgment: false
  - id: D6
    description: "The importer's never-overwrite guard actually guards — removing the is-None check on the tenure backfill causes a named regression test to fail"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_backfill_never_overwrites_operator_reason_left (observed RED with the guard replaced by `True`: asserted 'retired', got 'died'; guard restored, reran green)"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 02: Justice CSV importer backfills birthdate/death_date/reason_left Summary

**`python -m pipeline import-justices` now reads the CSV's Birthdate, Death Date and Reason Left columns and null-only backfills Person.birthdate/death_date and CourtTenure.reason_left, mapping the 5-value CSV vocabulary through an explicit membership check that surfaces (rather than silently drops) anything unrecognised.**

## Performance

- **Duration:** ~55 min (includes provisioning a second throwaway ephemeral PostgreSQL instance for this WSL session)
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `_REASON_LEFT_CSV_MAP` — a closed 5-key dict (`Died`→`died`, `Retired`→`retired`, `Promoted to Chief Justice`→`promoted`, `Still in Office`→`None`, `""`→`None`) resolved via an explicit `in` membership check rather than `.get()`, so a recognised-value-that-maps-to-None stays distinguishable from a never-seen value; the docstring records the verified per-value census from `39-02-PLAN.md`'s `<verified_csv_facts>`.
- `run_import_justices_csv()` now reads `Birthdate`/`Death Date`/`Reason Left` per row, writes them directly on new-row creation, and blank-only backfills them on the existing-person branch (birthdate/death_date) and a newly-added `else:` arm on the existing-tenure branch (reason_left) — mirroring the exact `is None`-guarded shape Phase 38 established for name parts.
- Zero derivation logic added or present: no comparison of `end_date`/`death_date`, no Associate→Chief transition detection — every stored value traces back to its own CSV cell (D-03), confirmed by the plan's own negative grep check.
- Closing summary line now reports per-field backfill counts and, when any `Reason Left` cell doesn't match the vocabulary, a second line naming the count and the sorted set of unrecognised raw values.
- 8 new DB-gated integration tests added, covering every `<behavior>` bullet in the plan: full new-row population, both never-overwrite regression guards (birthdate/death_date and reason_left), both blank-only-fill cases, the open-tenure NULL rule, unrecognised-value reporting via `capsys`, and second-run idempotency with no field drift.
- Verified the never-overwrite guard is load-bearing, not decorative: temporarily replaced the tenure-backfill `is None` check with `True`, re-ran the suite, and observed `test_backfill_never_overwrites_operator_reason_left` fail (asserted `'retired'`, got `'died'`); restored the guard and confirmed green again (git diff showed zero net change to the source file).
- Ran the real importer against the real `data/corpus/supreme_court_justices_sections.csv` (after `seed-aliases`) on the ephemeral test DB: first run backfilled 13 birthdates + 2 death dates onto the pre-seeded justices with 0 unrecognised Reason Left values; second run backfilled 0/0/0 across the board — matching the plan's `<verification>` section exactly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Read the three CSV columns and backfill them null-only** - `2616bc88` (feat)
2. **Task 2: Cover the backfill contract with DB-gated integration tests** - `ef8454fe` (test)

## Files Created/Modified
- `pipeline/commands/import_justices_csv.py` - `_REASON_LEFT_CSV_MAP`, per-row Birthdate/Death Date/Reason Left reads, blank-only backfill on the person-upgrade and existing-tenure branches, `reasons_unmatched` counter, extended summary print
- `pipeline/tests/test_import_justices_csv.py` - 8 new integration tests (new-row population, 2 never-overwrite guards, 2 blank-fill cases, open-tenure-NULL, unrecognised-value + stdout, idempotency)

## Decisions Made
- See `key-decisions` in frontmatter: (1) the accidental real-dev-DB migration application via the Windows venv's env-var isolation from WSL, and its non-destructive/additive-only nature; (2) the test file's CSV header helper already had the full 11-column shape from Phase 29, so Task 2 needed no helper changes, only new test functions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned a fresh ephemeral pgserver PostgreSQL instance for this session's DB-gated tests**
- **Found during:** Task 1, environment setup
- **Issue:** Plan 39-01's ephemeral pgserver instance had already been torn down at the end of that session (per its own SUMMARY). This plan's `<environment_note>` explicitly requires the same WSL-native ephemeral-DB workaround (real dev Postgres is Windows-loopback-only and unreachable from WSL).
- **Fix:** Created a scratch Python 3.12 venv (`pgvenv`) with `pgserver` installed, provisioned a session-local instance, created `scotus_test`, and ran `alembic upgrade head` (through the full 0001–0024 chain) against it via a second scratch venv (`testvenv`) that has this project's `requirements-dev.txt` installed — necessary because a Linux-native Python process is required to reach the WSL-local Unix domain socket path pgserver binds to.
- **Files modified:** none tracked (scratch venvs live in the session scratchpad directory, never in the repo).
- **Verification:** `pytest pipeline/tests/` — 187 passed, 5 xfailed against the ephemeral instance. Instance torn down at session end; confirmed via `ps aux | grep postgres` showing no remaining processes.
- **Committed in:** not applicable (no tracked files changed).

**2. [Rule 1 - Bug, discovered not introduced] Confirmed the Windows `.venv/Scripts/python.exe` cannot be used to run this plan's DB-gated tests against the ephemeral WSL DB**
- **Found during:** Task 1, initial attempt to run `alembic upgrade head` via `./.venv/Scripts/python.exe` with `DATABASE_URL`/`TEST_DATABASE_URL` exported in the WSL shell
- **Issue:** The command appeared to succeed (`alembic` printed "Running upgrade 0022 -> 0023" and "0023 -> 0024" with no errors), but a follow-up probe (`os.environ.get('DATABASE_URL')` printed from inside that same Windows process invocation) showed the value was `None` — WSL's interop layer does not forward the calling shell's exported environment variables into the launched Windows executable. `alembic/env.py`'s `load_dotenv()` (which does not override already-set vars, but there was nothing set) then fell back to `.env`'s real `DATABASE_URL` (`postgresql+asyncpg://...@localhost:5432/scotus`), meaning migrations 0023/0024 were actually applied to the real local dev database, not the intended ephemeral test DB.
- **Fix:** No code fix needed — this is an environment characteristic, not a bug in the codebase. Documented it here and switched to running all subsequent alembic/pytest invocations for this plan through the WSL-native `testvenv` Python (see Deviation 1), which correctly connects to the ephemeral instance via its Unix domain socket.
- **Impact assessment:** Migrations 0023 (`people.death_date`, nullable DATE, pure add) and 0024 (`court_tenures.reason_left` + a permissive CHECK constraint allowing NULL) are purely additive — no existing rows were altered or at risk. This is functionally equivalent to running Plan 39-06's real-dev-DB migration step one plan early; Plan 39-06 should verify `alembic current` on the real dev DB already reports `0024 (head)` before re-running its own migration step, to avoid a confusing "nothing to do" surprise.
- **Files modified:** none.
- **Committed in:** not applicable (no tracked files changed; the real dev DB's schema state, not this repo, is what changed).

---

**Total deviations:** 2 (1 blocking environment-setup step, 1 discovered — and worked around — environment behavior; no code changes stemmed from either)
**Impact on plan:** Both were necessary to actually run this plan's own required verification commands against an isolated test database, as `39-02-PLAN.md`'s own `<environment_note>` anticipated. No scope creep in the source files — only `pipeline/commands/import_justices_csv.py` and `pipeline/tests/test_import_justices_csv.py` were touched.

## Issues Encountered
- No PostgreSQL reachable from this WSL sandbox by TCP (confirmed: `localhost:5432` connection refused from the WSL side), consistent with the project's documented split-environment constraint. Resolved via the ephemeral pgserver instance described above.
- The Windows-side real dev DB now has migrations 0023/0024 applied (see Deviation 2) — this is forward-compatible with Plan 39-06's stated task and does not block it, but Plan 39-06 should account for it rather than treat it as a fresh apply.

## Next Phase Readiness
- `import_justices_csv.py` fully implements D-01 through D-07 for this plan's scope; 34/34 tests in `test_import_justices_csv.py` pass (26 pre-existing + 8 new), and the full `pipeline/tests/` suite is green (187 passed, 5 xfailed) against a from-scratch migrated database.
- Running the real importer against the real CSV confirms zero unrecognised `Reason Left` values in the current source file — the 5-key map fully covers it today.
- Plan 39-06 (real dev DB operator step) should check `alembic current` first — migrations 0023/0024 may already be at head on the real dev DB per Deviation 2 above.

## Self-Check: PASSED

Both modified files confirmed present on disk with the expected content; both commits (`2616bc88`, `ef8454fe`) confirmed present in `git log --oneline --all`.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*
