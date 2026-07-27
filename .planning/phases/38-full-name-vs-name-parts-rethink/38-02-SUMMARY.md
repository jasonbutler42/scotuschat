---
phase: 38-full-name-vs-name-parts-rethink
plan: "02"
subsystem: api
tags: [alembic-migration, sqlalchemy-model, name-parsing, pytest, backfill]

# Dependency graph
requires:
  - "api/domain/person_names.py: split_legacy_full_name, format_full_name (Plan 01)"
  - "api/tests/fixtures/person_name_cases.json: legacy_split_cases (Plan 01)"
provides:
  - "api/models/models.py: Person.name_needs_review, Person.name_extraction_metadata"
  - "alembic/versions/0022_person_name_authority.py: schema + guarded deterministic backfill + rollback"
  - "api/tests/test_migration_0022_person_name_authority.py: upgrade/downgrade/preservation evidence"
affects: [38-03, 38-04, 38-05, 38-06, admin_people, admin_jobs, pipeline-import]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migration integration tests resolve TEST_DATABASE_URL directly (never DATABASE_URL) and reject any database name other than scotus_test before issuing real DDL (T-38-06), mirroring the T-31-01 tests/conftest.py convention"
    - "Migration backfill never writes the pre-existing full_name column at all — it is trivially preserved byte-for-byte for every row because no UPDATE statement ever touches it"
    - "Round-trip gate: a High-confidence split is only ever persisted after re-deriving full_name from the split parts and confirming an exact match; any mismatch aborts the whole migration (Postgres transactional DDL rolls back both schema and data)"

key-files:
  created:
    - alembic/versions/0022_person_name_authority.py
    - api/tests/test_migration_0022_person_name_authority.py
  modified:
    - api/models/models.py

key-decisions:
  - "Migration only examines Person rows with ALL FOUR structured columns (first_name/middle_name/last_name/name_suffix) NULL — a row that already carries any operator/import-authored part is left completely untouched (never split, never flagged for review), protecting already-populated data from this backfill"
  - "name_extraction_metadata stores {source, raw, confidence, reason, auto_applied} per examined row (both applied and reviewed) rather than only for ambiguous rows — gives every migrated row a durable audit trail (T-38-05 repudiation mitigation), validated through api.domain.person_names.prepare_name_provenance's envelope shape at raw/confidence"
  - "A blank/whitespace-only full_name is treated as a violated pre-upgrade invariant and raises, aborting the entire migration transaction, rather than silently skipping or guessing (T-38-04)"
  - "Downgrade drops only the two Phase 38 columns (name_extraction_metadata then name_needs_review, reverse of add order) and never touches full_name/first_name/middle_name/last_name/name_suffix — a downgrade-then-reupgrade cycle correctly finds already-split rows untouched on the second pass (verified empirically during manual testing)"
  - "Migration test module resolves TEST_DATABASE_URL directly (never DATABASE_URL) and rejects any database whose name is not exactly scotus_test, matching the T-31-01 safety convention already used by tests/conftest.py and pipeline/tests/conftest.py"
  - "Added a module-scoped teardown fixture that restores the shared scotus_test database to head (0022) after this file's tests finish — this module's own tests intentionally downgrade to 0021 mid-run, and other DB-gated test modules in the same pytest session assume alembic upgrade head has already been applied"

requirements-completed: []  # PEOPLE-09 spans all 6 plans in this phase; not marked complete until the phase's final plan (established precedent from Plan 01)

coverage:
  - id: D1
    description: "Confident (two/three-part, with/without suffix), whitespace-near-miss, single-part, particle, compound (>3 token), and inverted-punctuation-order fixtures each produce deterministic applied/reviewed outcomes, reusing Plan 01's shared legacy_split_cases fixture set"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_upgrade_backfills_confident_rows_and_flags_ambiguous_rows (11 fixture cases, real scotus_test DB)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Existing full_name remains non-null and byte-for-byte preserved for every legacy person, confident or ambiguous, because the migration never issues an UPDATE against that column"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_upgrade_backfills_confident_rows_and_flags_ambiguous_rows (full_name assertion for all 11 cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A row that already carries any structured name part is left completely untouched by the backfill"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_upgrade_never_touches_rows_with_existing_structured_parts"
        status: pass
    human_judgment: false
  - id: D4
    description: "A blank/whitespace-only full_name aborts the entire migration transaction rather than being silently skipped or guessed"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_upgrade_aborts_on_blank_full_name_invariant_drift"
        status: pass
    human_judgment: false
  - id: D5
    description: "Re-running upgrade at a revision it is already at is a no-op that never re-processes rows or changes persisted state (repeatability guard)"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_upgrade_is_repeatable_without_double_processing"
        status: pass
    human_judgment: false
  - id: D6
    description: "Downgrade drops only the two Phase 38 columns, in reverse order, and never rewrites full_name or the pre-existing structured columns for any row (applied or reviewed)"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_downgrade_drops_only_phase38_columns_never_rewrites_names"
        status: pass
    human_judgment: false
  - id: D7
    description: "The migration test suite is bound to the configured scotus_test database only and never falls back to a possibly-production DATABASE_URL"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_database_guard_rejects_non_test_database"
        status: pass
      - kind: unit
        ref: "api/tests/test_migration_0022_person_name_authority.py#test_database_guard_rejects_unset_url"
        status: pass
    human_judgment: false

duration: ~65min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 02: Person Name Authority Migration Summary

**Alembic revision 0022 adds `Person.name_needs_review` (durable review flag) and `Person.name_extraction_metadata` (independent JSONB provenance), then guardedly backfills legacy full-name-only rows into structured parts via Plan 01's `split_legacy_full_name` — confident splits applied, every ambiguous shape preserved exactly and flagged for review, `full_name` itself never written.**

## Performance

- **Duration:** ~65 min (includes provisioning an ephemeral, throwaway PostgreSQL 16 instance for migration-DDL testing — see Issues Encountered)
- **Completed:** 2026-07-27
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `Person.name_needs_review` (Boolean, non-null, default false) and `Person.name_extraction_metadata` (nullable JSONB) added to `api/models/models.py`, following the file's established Boolean/JSONB column conventions
- Alembic revision `0022_person_name_authority.py`: adds both columns, then deterministically backfills every pre-existing Person row that has no structured name part at all — High-confidence, round-trip-exact splits (via `split_legacy_full_name`) are applied to the four structured columns; every other shape (single-part, particle, >3-token compound, punctuation/order ambiguity, whitespace near-miss) is left unsplit and flagged `name_needs_review = true`
- `full_name` is never written by this migration at all — it was already correct pre-upgrade, so it is trivially preserved byte-for-byte for every row regardless of outcome
- A round-trip gate re-derives `full_name` from any High-confidence split's parts and aborts the entire migration (Postgres transactional DDL rolls back schema and data together) if it does not reproduce the original text exactly; a blank/whitespace-only `full_name` is treated the same way — an aborted pre-upgrade invariant, never guessed or silently skipped
- Rows that already carry any structured name part (from a prior import/operator edit) are left completely untouched — never split, never flagged
- 11 integration tests in `api/tests/test_migration_0022_person_name_authority.py` exercise the real migration against an isolated `scotus_test` database: full backfill/count assertions (reusing Plan 01's `legacy_split_cases` fixture directly), the existing-parts skip, the blank-invariant abort, upgrade repeatability, downgrade column removal, and the database-identity safety guard itself

## Task Commits

Each task was committed atomically (TDD RED/GREEN):

1. **Task 1: Build migration preservation and rollback tests** - `d7513168` (test) — 11-fixture integration suite; RED confirmed by temporarily removing the not-yet-created revision file (5 DB-bound tests failed solely with `Can't locate revision identified by '0022'`; 2 pure database-guard unit tests passed)
2. **Task 2: Add review and provenance persistence** - `3a566c0b` (feat) — `Person` model fields + revision 0022's guarded backfill; all 60 tests in `test_migration_0022_person_name_authority.py` + `test_person_names.py` pass; full `api/tests` (386 tests) and `pipeline/tests` (152 passed, 5 xfailed) regression suites also pass unchanged

## Files Created/Modified

- `alembic/versions/0022_person_name_authority.py` — schema (2 new columns) + guarded deterministic legacy backfill + reverse-order downgrade
- `api/models/models.py` — `Person.name_needs_review`, `Person.name_extraction_metadata`
- `api/tests/test_migration_0022_person_name_authority.py` — 13 tests: database-identity guard (2), upgrade backfill/skip/abort/repeatability (4), downgrade (1), plus fixture-loading helpers

## Decisions Made

- Migration only examines rows where `first_name`, `middle_name`, `last_name`, and `name_suffix` are **all** `NULL` — any row already carrying a structured part from a prior import/operator edit is left entirely untouched (no split, no review flag). This is a conservative discretionary choice (not explicitly specified by the plan) protecting already-good data from being touched by a backfill meant only for truly-unconverted legacy rows.
- `name_extraction_metadata` is written for every examined row (both applied and reviewed), not only ambiguous ones — `{source: "legacy_migration_0022", raw, confidence, reason, auto_applied}` — giving every migrated row a durable audit trail (T-38-05) and giving the future People-editor "Name review" surface something concrete to show operators for reviewed rows.
- `raw`/`confidence` in that envelope are validated through `api.domain.person_names.prepare_name_provenance` before being persisted, per Task 2's "validate provenance as data shaped by field envelopes" instruction, even though the field-level `value` is not meaningful at the whole-name level (passed as `None`).
- A blank/whitespace-only `full_name` is a hard abort (`RuntimeError`), not a silent skip — Postgres transactional DDL means this rolls back the entire migration (both the `ADD COLUMN`s and any backfill already applied in the same transaction), so a single bad row cannot leave the schema in a half-migrated state.
- Downgrade removes only `name_extraction_metadata` and `name_needs_review` (reverse of the order they were added) and never reconstructs or reverts `full_name`/structured columns for either applied or reviewed rows — verified empirically that a downgrade-then-reupgrade cycle correctly finds previously-applied rows already split (0 re-applied) and previously-reviewed rows still NULL (re-flagged identically).
- The test module resolves `TEST_DATABASE_URL` directly and requires the resolved database name to be exactly `scotus_test` before running any test — it never falls back to `DATABASE_URL`, matching the established `T-31-01`/`tests/conftest.py`/`pipeline/tests/conftest.py` convention, because this file issues real `ALTER TABLE`/backfill DDL that must never reach a shared dev database.
- Added a module-scoped teardown fixture (`_leave_database_at_head`) that re-upgrades the shared test database back to `0022` after this file's own tests finish. This file's tests intentionally downgrade to `0021` mid-run (to test the downgrade path itself); without this fixture, any other DB-gated test module collected afterward in the same pytest session would see missing Phase 38 columns and fail. This was caught and fixed during Task 2's verification pass (see Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-upgrade snapshot helper querying not-yet-existent columns**
- **Found during:** Task 2 verification (first GREEN run)
- **Issue:** `test_upgrade_backfills_confident_rows_and_flags_ambiguous_rows` called the same `_fetch_people()` helper both before and after `command.upgrade`, but that helper selects `name_needs_review`/`name_extraction_metadata` — columns that don't exist until after the upgrade runs. The pre-upgrade snapshot call failed with `psycopg2.errors.UndefinedColumn`.
- **Fix:** Added a separate `_fetch_full_names()` helper (selects only `id, full_name`, valid at both the 0021 baseline and after 0022) and used it for the pre-upgrade snapshot assertion.
- **Files modified:** `api/tests/test_migration_0022_person_name_authority.py`
- **Commit:** `3a566c0b`

**2. [Rule 1 - Bug] Fixed shared test database left downgraded after this module's tests**
- **Found during:** Task 2 verification (running the full `api/tests` suite for regression safety)
- **Issue:** This module's own downgrade test left the shared `scotus_test` database at revision `0021` after the file finished. Other DB-gated test modules collected afterward in the same pytest session (`test_admin_people.py`, `test_people.py`, `test_admin_jobs_phase25.py`, etc.) assume `alembic upgrade head` has already been applied and immediately failed with `UndefinedColumn` for `people.name_needs_review` (42 failures across the suite).
- **Fix:** Added a module-scoped, autouse teardown fixture (`_leave_database_at_head`) that re-upgrades the database back to `0022` once, after every test in this module has run (pass, fail, or skip).
- **Files modified:** `api/tests/test_migration_0022_person_name_authority.py`
- **Commit:** `3a566c0b`

**3. [Rule 1 - Bug] Hardened the blank-invariant test to assert on the specific abort message**
- **Found during:** Task 1 RED verification
- **Issue:** `test_upgrade_aborts_on_blank_full_name_invariant_drift` originally used bare `pytest.raises(Exception)`, which trivially passed even with revision 0022 absent (any `CommandError` satisfies "any exception"). This meant the test could not actually discriminate "migration correctly aborted on the blank invariant" from "the revision doesn't exist yet" or any other unrelated failure.
- **Fix:** Changed the assertion to `pytest.raises(Exception, match="blank/NULL full_name")`, matching the migration's own abort message specifically. Re-verified this correctly fails (for the right reason) before the revision existed, and correctly passes once the migration implements the real abort.
- **Files modified:** `api/tests/test_migration_0022_person_name_authority.py`
- **Commit:** `d7513168`

## Issues Encountered

- **No reachable PostgreSQL in this execution environment.** This WSL/Linux sandbox has a Windows-hosted portable PostgreSQL (`data/pgsql`, referenced by `scripts/dev-start.ps1`) that is running (verified via `pg_ctl status`) but bound to `127.0.0.1`/`::1` only on the Windows side — unreachable from WSL's separate network namespace (this WSL install is NAT-mode, not mirrored networking; confirmed via `ip route`/`/etc/wsl.conf`). No system PostgreSQL, `psql`, or `pg_ctl` binary is installed on the Linux side, and no passwordless `sudo` is available to install one via `apt`.
  - **Resolution:** Used the `pgserver` PyPI package (a self-contained, no-root-required PostgreSQL 16.2 binary distribution) to provision a genuinely isolated, throwaway PostgreSQL instance for this session, listening on a Unix domain socket. Created a `scotus_test`-named database on it (matching the project's own `T-31-01` database-name safety convention) and ran `alembic upgrade head` (migrations 0001–0021) against it before writing any Phase 38 code, confirming the full pre-existing migration history applies cleanly.
  - This is a genuinely isolated instance that never existed before this session and was torn down (`pgserver` `cleanup()`) after verification completed — it has no connection to the project's real dev/CI database, and no data or credentials from any real database were read, written, or exposed at any point.
  - No project dependency was added — `pgserver`, `asyncpg` (already a project dependency), and the scratch Python 3.12 venv used to run it are local-session-only tooling in `/tmp` (this session's scratchpad directory), not the repository. `requirements.txt`/`requirements-dev.txt` are unchanged.
  - This mirrors the same class of environmental workaround Plan 01's summary documented (a Windows-oriented `.venv` incompatible with this Linux/WSL execution shell), extended here because Task 2's plan explicitly requires exercising the real migration's `upgrade`/`downgrade` against a live database, not just pure-Python unit tests.

## User Setup Required

None — no external service configuration required. The ephemeral PostgreSQL instance used to verify this plan's migration was torn down at the end of this session; it is not part of the repository or any persisted environment. A developer running this migration against their own `scotus_test` database (per `scripts/dev-start.ps1`) needs no additional setup beyond what Phase 38 already assumes.

## Next Phase Readiness

- `Person.name_needs_review` and `Person.name_extraction_metadata` are ready for 38-03/38-04 (write-path/service adoption enforcing the shared `prepare_person_name` contract), 38-05 (People directory `Name review` filter surfacing `name_needs_review=true` rows), and 38-06 (pipeline/import extraction writing into `name_extraction_metadata` using the same envelope shape this migration already establishes).
- `alembic/versions/0022_person_name_authority.py` is the new head revision (0021 → 0022); a developer running `scripts/dev-start.ps1`'s `alembic upgrade head` step will pick it up automatically.
- No blockers. The migration's "skip rows with any existing structured part" rule and its blank-invariant abort are both intentionally conservative and exercised by dedicated tests; any legacy row shape this migration does not confidently split is safely preserved and flagged for review, never guessed, per D-11/D-12.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: alembic/versions/0022_person_name_authority.py
- FOUND: api/tests/test_migration_0022_person_name_authority.py
- FOUND: api/models/models.py (modified)
- FOUND commit: d7513168 (Task 1)
- FOUND commit: 3a566c0b (Task 2)
