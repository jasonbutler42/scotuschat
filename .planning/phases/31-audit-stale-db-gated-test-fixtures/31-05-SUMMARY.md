---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 05
subsystem: testing
tags: [pytest, sqlalchemy, asyncpg, fastapi, pydantic-settings]

# Dependency graph
requires:
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 02)
    provides: TEST_DATABASE_URL wiring + leak-detector hook
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 03)
    provides: consolidated api/tests/conftest.py db_session fixture
provides:
  - 5 api/tests files' DB-gated tests genuinely pass against scotus_test
  - api/core/config.py Settings no longer crashes when TEST_DATABASE_URL is in .env
  - publish_argument/unpublish_argument/approve_job return fresh (not stale) row data
affects: [31-06, 31-07, verify-work-phase-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "db.refresh(obj) after a synchronize_session=False bulk update whenever the same object is re-read later in the same session"
    - "Multi-block AsyncSessionLocal() sessions (not the shared db_session fixture) for tests exercising functions that commit() internally"
    - "Explicit db.flush() between dependent deletes when no ORM relationship() is configured (FK order not auto-derived)"

key-files:
  created: []
  modified:
    - api/core/config.py
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_jobs_phase25.py
    - api/tests/test_admin_jobs_service.py
    - api/tests/test_admin_jobs_stats.py
    - api/tests/test_arguments.py
    - .planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md

key-decisions:
  - "Fixed 3 genuine stale-identity-map production bugs (publish_argument, unpublish_argument, approve_job) rather than xfailing them — same low-risk db.refresh() pattern already used by sibling functions in the same files"
  - "Test fixture-vs-committing-function conflict resolved in test usage (multi-block AsyncSessionLocal), not by changing the services' commit semantics, per 31-CONTEXT.md's explicit instruction not to alter the 3 documented leak-source functions"
  - "test_arguments.py's hardcoded argument_id=1 replaced with a self-seeding fixture — scotus_test starts empty, unlike the shared dev DB's persistent Obergefell seed data"

requirements-completed: [TEST-02]

coverage:
  - id: D1
    description: "All DB-gated tests in the 5 assigned api/tests files pass against scotus_test (0 failures, 0 errors)"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pytest tests api/tests/test_admin_arguments_service.py api/tests/test_admin_jobs_phase25.py api/tests/test_admin_jobs_service.py api/tests/test_admin_jobs_stats.py api/tests/test_arguments.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "No nullable=False/enum/unique constraint in api/models/models.py was changed to make a test pass"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "git diff api/models/models.py (empty — file untouched by this plan)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 05: Repair Stale DB-Gated api/tests Fixtures Summary

**Fixed 5 api/tests files' DB-gated tests against scotus_test — including 3 genuine stale-identity-map bugs in publish_argument/unpublish_argument/approve_job that a config.py crash had masked from ever executing.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 1 (single-task plan)
- **Files modified:** 9 (1 config, 2 service, 5 test, 1 deferred-items doc)

## Accomplishments

- All DB-gated tests in `test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`, `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, and `test_arguments.py` now genuinely execute and pass against the isolated `scotus_test` database (128 tests passed, run repeatedly with no leftover-row accumulation).
- Fixed a blocking bug that had silently prevented *every* `api/tests` DB-gated test in the repo from running at all: `pydantic-settings`' `Settings(env_file=".env")` reads the whole `.env` file directly (independent of `os.environ`), so once Plan 31-01/02 added `TEST_DATABASE_URL` to `.env`, `Settings()` raised `extra_forbidden` on every construction — crashing the autouse `_api_lifespan` fixture.
- Found and fixed 3 genuine production bugs surfaced by making these tests execute for the first time: `publish_argument`, `unpublish_argument`, and `approve_job` each load a row, run a `synchronize_session=False` bulk `update()`, then re-read the *same* row in the *same* session — because `expire_on_commit=False`, the re-read returned the stale pre-update object instead of the committed value. Fixed with `db.refresh()`, matching the pattern already used in `create_person_for_job`/`update_resolve_row_for_job`.
- Fixed the canonical example cited in ROADMAP.md — tests inserting `Utterance` rows without the NOT NULL `strategy` column.
- Replaced `test_arguments.py`'s assumption of a persistent `argument_id=1` (real Obergefell data on the shared dev DB) with a self-contained `seeded_argument` fixture, since `scotus_test` starts empty except for migrations.
- Discovered and logged (not fixed — out of scope) that `test_argument_oyez_field.py`/`test_people.py` (owned by Plan 31-06) and several `pipeline/tests` files have their own genuine failures, now visible for the first time because of the config.py fix above.

## Task Commits

1. **Task 1: Diagnose + fix schema mismatches in the 5 api/tests files (TEST-02)**
   - `09a6ad78` (fix) — declare `test_database_url` in `Settings` to unblock DB-gated tests
   - `452c769b` (fix) — refresh session-cached rows after bulk status updates (`admin_arguments.py`, `admin_jobs.py`)
   - `0462ff86` (test) — repair stale DB-gated fixtures in the 5 assigned `api/tests` files
   - `8f3b03e7` (docs) — log out-of-scope findings from Plan 05 execution

## Files Created/Modified

- `api/core/config.py` — added `test_database_url: str = ""` field so `Settings()` no longer crashes on the `.env` key added by Plan 31-01/02.
- `api/services/admin_arguments.py` — `db.refresh(argument)` after commit in `publish_argument` and `unpublish_argument`.
- `api/services/admin_jobs.py` — `db.refresh(job)` after commit in `approve_job`.
- `api/tests/test_admin_arguments_service.py` — added `strategy="rule_based"` to 4 `Utterance` inserts; seeded a linked `Case`/`CaseArgument(is_lead=True)` for 3 tests whose assertions depend on `get_argument_detail`'s return value; added a missing `from sqlalchemy import select` import; fixed cleanup delete-ordering with explicit `flush()`.
- `api/tests/test_admin_jobs_phase25.py` — converted 4 tests (2 `create_person_for_job`, 2 `update_resolve_row_for_job`) from the shared `db_session` fixture to per-block `AsyncSessionLocal()` sessions, since those functions commit internally and conflict with `db_session`'s outer `session.begin()` wrapper; added explicit cleanup (previously absent — this is the exact leak pattern that produced the 5 duplicate "Ketanji Brown Jackson" `Person` rows referenced in `31-CONTEXT.md`).
- `api/tests/test_admin_jobs_service.py` — fixed a stale `raw_text=` kwarg (model field is `text`) and a missing `strategy`; switched a raw `status="completed"` string to `PipelineRunStatus.COMPLETED`; fixed cleanup delete-ordering.
- `api/tests/test_admin_jobs_stats.py` — added `strategy="rule_based"` to 3 loops of `Utterance` inserts.
- `api/tests/test_arguments.py` — added a `seeded_argument` fixture (self-contained `Argument`/`Case`/`CaseArgument`/`Person`/`Role`/`PipelineRun`/`Utterance` seed + teardown) and rewired the 3 real-DB tests to use it instead of a hardcoded `argument_id=1`.
- `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md` — logged the config.py finding and the out-of-scope failures now visible in `test_argument_oyez_field.py`, `test_people.py`, and several `pipeline/tests` files.

## Decisions Made

- Fixed the 3 stale-identity-map bugs in production service code (Rule 1 — auto-fix bugs) rather than leaving them as documented `xfail`s. All three are the exact same low-risk, well-understood fix (`db.refresh()` after a `synchronize_session=False` bulk update) already proven correct elsewhere in the same files (`create_person_for_job`, `update_resolve_row_for_job`). Given how central publish/unpublish/approve are to the three-state argument lifecycle (a major v1.5 feature), leaving all three un-fixed would have meant most of this test file's coverage stayed unverified — undermining the phase's stated purpose of "restoring real coverage." No `nullable=False`/enum/unique constraint or model was touched.
- The `create_person_for_job`/`update_resolve_row_for_job` internal `db.commit()` calls were left unchanged per `31-CONTEXT.md`'s explicit instruction that the 3 documented leak-source functions are not to be refactored in this phase — the fix went into test session usage instead (multi-block `AsyncSessionLocal()`, matching the established pattern elsewhere in the codebase for testing committing functions).
- `test_arguments.py`'s Tests 3–5 previously depended on a specific real utterance shape from the shared dev DB (first utterance unresolved, later ones resolved). The new `seeded_argument` fixture preserves that exact shape (sequence 1 unresolved, sequence 2 resolved) so both Test 3's "`person_id` must be null at Phase 1" assertion and Test 5's "at least one resolved utterance" assertion hold without weakening either.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `Settings()` crashed on every api/tests DB-gated test**
- **Found during:** Task 1, initial verification run
- **Issue:** `pydantic-settings`' `env_file=".env"` reads the file directly; `TEST_DATABASE_URL` (added by Plan 31-01/02) had no matching field, raising `extra_forbidden` on every `Settings()` construction and crashing the autouse `_api_lifespan` fixture for the whole suite, not just this plan's 5 files.
- **Fix:** Added `test_database_url: str = ""` to `Settings`.
- **Files modified:** `api/core/config.py`
- **Verification:** Full test suite runs without the `ValidationError`; 128/128 target tests pass.
- **Committed in:** `09a6ad78`

**2. [Rule 1 - Bug] Stale-identity-map bug in `publish_argument`/`unpublish_argument`/`approve_job`**
- **Found during:** Task 1, after adding `Case` linkage revealed the true assertion failure (status still showed the pre-transition value)
- **Issue:** Each function loads a row, bulk-updates it with `synchronize_session=False`, then re-reads the same row via a helper (`get_argument_detail`/`get_job`) in the same session. `expire_on_commit=False` means the already-loaded object is never synced, so the re-read hits the identity map and returns stale data.
- **Fix:** `await db.refresh(obj)` immediately after `db.commit()`, before the re-read.
- **Files modified:** `api/services/admin_arguments.py`, `api/services/admin_jobs.py`
- **Verification:** `test_publish_argument_from_draft_writes_one_published_log_row`, `test_unpublish_then_republish_succeeds_and_preserves_published_at`, `test_approve_job_writes_one_draft_log_row` all pass; the `xfail` marker initially added for `approve_job` was removed once the underlying bug was fixed.
- **Committed in:** `452c769b`

**3. [Rule 1 - Bug] Missing `from sqlalchemy import select` in `test_get_argument_detail_includes_status_log_and_speakers`**
- **Found during:** Task 1, after fixing the Case-linkage issue exposed a `NameError` in the test's own cleanup block that had never been reached before (the test always returned `None` before Phase 31)
- **Issue:** `select(ArgumentStatusLog)` used in the cleanup block with no import in that function's scope.
- **Fix:** Added the missing import.
- **Files modified:** `api/tests/test_admin_arguments_service.py`
- **Committed in:** `0462ff86`

**4. [Rule 1 - Bug] Delete-ordering FK violations in 4 test cleanup blocks**
- **Found during:** Task 1, iterative verification
- **Issue:** No `relationship()` is configured between any models in this codebase (Core-style FK columns only), so the ORM unit-of-work cannot auto-derive delete order from `db.delete()` calls issued in dependency order — a single `commit()` batching multiple deletes can execute them in the wrong order and violate FK constraints.
- **Fix:** Added explicit `await db.flush()` between dependent deletes (matching the manual FK-ordering convention already documented in `admin_arguments.delete_argument`'s Pitfall 2 comment).
- **Files modified:** `api/tests/test_admin_arguments_service.py`, `api/tests/test_admin_jobs_service.py`
- **Committed in:** `0462ff86`

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 bugs)
**Impact on plan:** All auto-fixes were necessary for correctness (the blocking fix was required just to run any test; the 3 production bug fixes restore real audit-trail coverage for the three-state argument lifecycle, a major v1.5 feature). No production schema/model was touched; no scope creep beyond what was needed to make the 5 assigned files' tests genuinely pass.

## Out-of-Scope Findings (logged, not fixed)

Full detail in `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md`. Summary:

- `api/tests/test_argument_oyez_field.py::test_utterances_payload_includes_oyez_transcript_id` and `api/tests/test_people.py::test_get_person` — both 404, both owned by Plan 31-06.
- `pipeline/tests/test_ingest.py`, `test_parse.py`, `test_pipeline_run.py`, `test_resolve.py`, `test_seed_aliases.py` — several `AttributeError`/`not implemented`/interface-error failures, outside this api-side plan's remit entirely.

All of these were previously unreachable (the config.py crash aborted every DB-gated test before its own logic ran) — fixing that crash is what surfaced them for the first time, exactly matching this phase's premise.

## Issues Encountered

- Repeated leftover synthetic rows (`26-01-TEST-PUB`/`26-01-TEST-REPUB` cases, orphaned test arguments) accumulated in `scotus_test` across iterative debugging runs whenever a test failed before reaching its own cleanup block. Manually purged via a one-off script during debugging — this is expected/disposable (`scotus_test` auto-resets every pytest *session* when `pipeline/tests` is included in collection; it does not reset between arbitrary sub-scoped invocations like the ones used for isolated debugging here). No action needed once all target tests pass and clean up after themselves correctly.
- Confirmed a pytest collection quirk: `tests/conftest.py` (which loads `.env` and redirects `DATABASE_URL` → `TEST_DATABASE_URL`) is only collected when `tests/` is included in the invocation path — running the plan's literal verify command (explicit 5 file paths only) bypasses it, so all DB-gated tests in that specific invocation skip (genuinely "unconfigured" for that run, satisfying the acceptance criteria's skip allowance) rather than exercising the DB. To genuinely verify against `scotus_test`, `tests/` must be included in the pytest invocation alongside the 5 target files (as done throughout this session).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 5 files assigned to this plan pass cleanly and repeatably against `scotus_test`.
- Plan 31-06 (owns `test_argument_oyez_field.py`, `test_people.py`) and whichever plan owns `pipeline/tests` should consult `deferred-items.md` before assuming their scope is clean — several genuine failures in those files are now visible for the first time.
- No blockers for subsequent Phase 31 plans.

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13*

## Self-Check: PASSED

All 9 modified files confirmed present on disk; all 4 task commit hashes
(`09a6ad78`, `452c769b`, `0462ff86`, `8f3b03e7`) confirmed in git log.
