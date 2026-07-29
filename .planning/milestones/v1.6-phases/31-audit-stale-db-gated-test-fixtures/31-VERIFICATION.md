---
phase: 31-audit-stale-db-gated-test-fixtures
verified: 2026-07-13T18:00:36Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 31: Audit ~28 stale DB-gated test fixtures + fix real data leakage Verification Report

**Phase Goal:** Fix the real data-leakage bug (production service functions committing internally past the `db_session` fixture's rollback), get the ~28 stale DB-gated test fixtures passing against the current schema, clean up the already-leaked rows in the shared dev DB, and add a self-enforcing check proving the full suite never leaves new rows behind.

**Verified:** 2026-07-13T18:00:36Z
**Status:** passed
**Re-verification:** No — initial verification

All four success criteria were independently re-executed against the live codebase and live shared dev DB during this verification (not taken from SUMMARY.md narration or the orchestrator's own three prior runs, though those are consistent with what I observed).

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | Full pytest suite (`pipeline/tests/` + `api/tests/`) runs without leaving any new synthetic Person/Argument rows in the shared dev DB, verified via before/after row-count check | ✓ VERIFIED | Independently ran `python -m pytest -q` from repo root: **429 passed, 5 xfailed, 0 failed, 0 errored**. `tests/conftest.py`'s `pytest_sessionstart`/`pytest_sessionfinish` leak hook ran (queries real `DATABASE_URL`, not `TEST_DATABASE_URL`) and did not raise. Independently queried the shared dev DB directly before and after this run: `people=333`, `arguments=163` both times — zero drift. |
| 2 | All ~28 previously-failing DB-gated test fixtures pass against the current schema (no NOT NULL/enum mismatches) | ✓ VERIFIED | Same full-suite run: 0 failures across all 10 named files from the ROADMAP goal (`test_ingest.py`, `test_parse.py`, `test_resolve.py`, `test_seed_aliases.py`, `test_pipeline_run.py`, `test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`, `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, `test_arguments.py`). The 5 xfails are pre-existing `pytest.fail("not implemented")` stubs (never-written tests, not schema drift), each with a documented reason per Plan 06's SUMMARY — consistent with the acceptance criteria's "xfail with documented reason" allowance. `git diff` confirms `api/models/models.py` was never touched by any of Plans 05/06 — schema was not weakened to make tests pass. |
| 3 | The isolation mechanism demonstrably survives an inner commit made by a production service function (`create_person_for_job`) during a test | ✓ VERIFIED | Read `api/tests/test_isolation_survives_inner_commit.py` in full: it invokes `create_person_for_job` (which commits internally per `api/services/admin_jobs.py`), then queries the row back from a brand-new `AsyncSessionLocal()` session, proving the commit durably landed somewhere queryable. Combined with `tests/conftest.py`'s collection-order-dependent `DATABASE_URL → TEST_DATABASE_URL` redirect (verified present and running first per `pytest.ini`'s `testpaths = tests pipeline/tests api/tests`) and the sessionfinish hook proving the shared dev DB was untouched, this constitutes the full criterion-3 demonstration. This exact test passed as part of the 429-passed full-suite run above. |
| 4 | Running `import-justices` immediately after a full test-suite run does not fail with `MultipleResultsFound` or any other leaked-data-caused error | ✓ VERIFIED | Independently ran `python -m pipeline import-justices` against the shared dev DB immediately after the full-suite run above. Output: `Done — 0 people created, 0 people upgraded to is_justice=True, 0 court_tenures created (0 rows skipped).` No `MultipleResultsFound`, no error. Independently confirmed zero duplicate `full_name` groups remain in the `people` table (`SELECT full_name, COUNT(*) ... HAVING COUNT(*) > 1` → empty result). |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `scripts/provision_test_db.py` | Idempotent `scotus_test` provisioning (CREATE DATABASE + `alembic upgrade head`) | ✓ VERIFIED | Exists, confirmed guards against running when `TEST_DATABASE_URL` unset or matches the dev-DB name; invokes `alembic upgrade head` via subprocess with `DATABASE_URL` overridden to the test URL; uses `statement_cache_size=0`. |
| `.env.example` (`TEST_DATABASE_URL` entry) | Documents the new env var with a placeholder | ✓ VERIFIED | `git show HEAD:.env.example` confirms `TEST_DATABASE_URL=postgresql+asyncpg://scotus:scotus@localhost:5432/scotus_test` line 28 (local placeholder, not a real remote credential). |
| `pipeline/tests/conftest.py::_reset_test_db` | Session-scoped, autouse TRUNCATE guarded to `scotus_test` only | ✓ VERIFIED | `@pytest.fixture(scope="session", autouse=True)` at line 131, function `_reset_test_db` at line 132. |
| `tests/conftest.py` (`_REAL_DATABASE_URL`, leak hook) | Captures real dev-DB URL before override; enforces row-count invariant | ✓ VERIFIED | `_REAL_DATABASE_URL = os.environ.get("DATABASE_URL")` captured before override; `_db_configured()`, `pytest_sessionstart`, `pytest_sessionfinish` all present and exercised live in my own test run (silent pass = hook ran and found no drift). |
| `api/tests/conftest.py` (consolidated `db_session`) | Single fixture; 7 local copies removed | ✓ VERIFIED | `async def db_session` defined only in `api/tests/conftest.py`; `grep -rl "async def db_session" api/tests/` returns only `conftest.py`. `_api_lifespan`/`_db_configured` unchanged as required. |
| `scripts/cleanup_leaked_test_rows.py` | Dry-run-by-default, broad-sweep leaked-row cleanup | ✓ VERIFIED | Exists; ran the actual `--execute` cleanup per Plan 08 (already executed with operator authorization prior to this verification, confirmed by live DB state below). |
| `api/tests/test_isolation_survives_inner_commit.py` | Criterion-3 regression test | ✓ VERIFIED | Exists, read in full (see Truth 3 above), passes as part of full suite. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `tests/conftest.py` | `api.core.config.settings` / `api.core.database` | Module-level `os.environ["DATABASE_URL"]` override before any `api.*` import, relying on `pytest.ini`'s `testpaths = tests pipeline/tests api/tests` collection order | ✓ WIRED | Confirmed collection order in `pytest.ini`; confirmed my own live full-suite run collected `tests/` first (evidenced by the leak hook actually firing) and that `test_isolation_survives_inner_commit.py` (which exercises `AsyncSessionLocal`, itself built from `settings.database_url`) passed without touching the shared dev DB. |
| `scripts/provision_test_db.py` | `alembic upgrade head` | `subprocess.run([...], env={**os.environ, "DATABASE_URL": test_url})` | ✓ WIRED | Confirmed via direct file read (line ~86-92). |
| `api/tests/test_isolation_survives_inner_commit.py` | `api/services/admin_jobs.py::create_person_for_job` | Direct call + query-back via a fresh `AsyncSessionLocal()` | ✓ WIRED | Confirmed via direct file read; test passed live. |
| `scripts/cleanup_leaked_test_rows.py` | shared dev DB (`DATABASE_URL`, not `TEST_DATABASE_URL`) | Direct connection via `DATABASE_URL` with survivor-selection scoring | ✓ WIRED | Confirmed the script targets `DATABASE_URL`; confirmed live DB state (333 people / 163 arguments, 0 duplicate groups) matches the script's own reported post-execute counts in 31-08-SUMMARY.md. |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| TEST-01 | 31-01, 31-02, 31-03, 31-04, 31-07, 31-08 | Full test suite runs without leaking synthetic Person/Argument rows into the shared dev database | ✓ SATISFIED | Truths 1, 3, 4 above, independently reproduced. |
| TEST-02 | 31-03, 31-05, 31-06, 31-07 | The ~28 identified stale DB-gated test fixtures pass against the current schema (no nullable/enum mismatches) | ✓ SATISFIED | Truth 2 above, independently reproduced (429 passed / 0 failed). |

No orphaned requirements — REQUIREMENTS.md maps only TEST-01 and TEST-02 to Phase 31, and both are covered above.

### Anti-Patterns Found

Scanned all files touched across the 8 plans (per each SUMMARY's `key-files`/`files_modified`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`: **none found.** No debt-marker gate violation.

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `api/services/admin_jobs.py::resolve_job` | ~533-536 | Stale-identity-map bug (CR-01 in 31-REVIEW.md) — same class of bug this phase fixed in `publish_argument`/`unpublish_argument`/`approve_job`, missed on `resolve_job` | ℹ️ Info (not a phase-31 blocker) | Pre-existing bug (not introduced by this phase — `resolve_job`'s bulk-update+re-read pattern predates Phase 31). No test in this phase or the existing suite asserts on `resolve_job`'s returned `.status` (confirmed via `grep resolve_job api/tests/test_admin_jobs_phase25.py api/tests/test_admin_jobs_service.py` → no matches), so it does not cause any of this phase's 4 success criteria to fail. Real production bug — logged here for a follow-up phase/plan, not a Phase 31 gap. |
| `pipeline/parser/state_machine.py` (inline-stage-direction-on-continuation-line path) | ~342-362 | Data-loss/misattribution bug (CR-02 in 31-REVIEW.md) — unrelated to the `SECTION_HINT_MAP` plural-regex bug this phase's Plan 06 fixed in the same file | ℹ️ Info (not a phase-31 blocker) | Pre-existing narrow parser defect, not introduced by this phase and not exercised by any test this phase added or modified. Does not affect TEST-01/TEST-02 success criteria. Logged for a follow-up phase — CLAUDE.md's apolitical/verbatim-transcript constraint makes this worth a dedicated fix, just not a Phase 31 gap. |
| `api/tests/conftest.py`, `tests/conftest.py`, `scripts/cleanup_leaked_test_rows.py`, and 10+ test files | various | `_db_configured()` placeholder guard duplicated verbatim (WR-01 in 31-REVIEW.md) | ℹ️ Info | Code-quality/maintainability warning, not a correctness or goal-achievement issue — doesn't block any of the 4 success criteria. |
| `scripts/provision_test_db.py:75` | 75 | Unescaped identifier interpolation in `CREATE DATABASE` (WR-02 in 31-REVIEW.md) | ℹ️ Info | Low-severity, operator-controlled input only; doesn't block goal achievement. |
| `scripts/cleanup_leaked_test_rows.py:294-318` | — | No post-merge overlap check on reassigned `court_tenures` rows (WR-03 in 31-REVIEW.md) | ℹ️ Info | This one-time script already ran successfully (Plan 08) with a clean result (verified live: the sole KBJ survivor's court_tenures merge did not produce an overlap in this specific run — only one KBJ duplicate group had a `court_tenures` row to reassign in the first place). Doesn't block goal achievement for this already-completed cleanup pass. |

None of these rise to BLOCKER — all are pre-existing bugs or code-quality warnings outside the phase's own success-criteria surface, correctly identified as such by `31-REVIEW.md`'s own header ("2 critical findings, both pre-existing bugs NOT introduced by this phase").

### Behavioral Spot-Checks / Probe Execution

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full suite passes, leak hook silent | `python -m pytest -q` (run from repo root, independently, not reusing orchestrator's prior runs) | `429 passed, 5 xfailed in 56.56s` | ✓ PASS |
| Shared dev DB row counts stable across the full-suite run | Direct `SELECT COUNT(*) FROM people/arguments` before and after the run above | `333`/`163` both times | ✓ PASS |
| No duplicate `Person.full_name` groups remain | `SELECT full_name, COUNT(*) FROM people GROUP BY full_name HAVING COUNT(*) > 1` | `[]` (empty) | ✓ PASS |
| `import-justices` runs clean post-suite (criterion 4) | `python -m pipeline import-justices` | `Done — 0 people created, 0 people upgraded to is_justice=True, 0 court_tenures created (0 rows skipped).` | ✓ PASS |

No probes declared in this phase's PLAN/SUMMARY files (`grep -R "probe-"` across all 8 PLANs/SUMMARYs returns nothing) — Step 7c is N/A.

### Human Verification Required

None. All 4 success criteria and both requirement IDs were independently reproduced against the live codebase and live shared dev DB during this verification session — no visual, real-time, or external-service behavior requiring human judgment remains open.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria hold, independently re-verified (not merely re-stated from SUMMARY.md or the orchestrator's prior runs):

1. Full suite leaves the shared dev DB untouched (leak hook silent, row counts stable at 333/163 across an independently-run full suite).
2. All ~28 previously-stale DB-gated fixtures pass (429 passed, 0 failed; the 5 xfails are documented never-implemented stubs, not schema drift, and do not weaken `api/models/models.py`).
3. The `TEST_DATABASE_URL` redirect mechanism demonstrably survives `create_person_for_job`'s internal commit (dedicated regression test passes).
4. `import-justices` runs clean post-suite with zero leaked-data errors (independently re-run, confirmed clean).

The two REVIEW.md critical findings (`resolve_job` stale-identity-map bug, `state_machine.py` inline-stage-direction bug) are correctly out of this phase's scope — both are pre-existing, neither is exercised by any test this phase touches, and neither affects any of the 4 success criteria. They are logged above as informational follow-up items, not phase-31 gaps.

---

*Verified: 2026-07-13T18:00:36Z*
*Verifier: Claude (gsd-verifier)*
