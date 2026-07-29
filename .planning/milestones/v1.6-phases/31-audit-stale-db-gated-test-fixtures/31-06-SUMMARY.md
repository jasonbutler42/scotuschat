---
phase: 31-audit-stale-db-gated-test-fixtures
plan: 06
subsystem: testing
tags: [pytest, pytest-asyncio, sqlalchemy, asyncpg, pipeline, alembic]

# Dependency graph
requires:
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 01)
    provides: scotus_test provisioning + pipeline/tests/conftest.py session-scoped auto-reset fixture
  - phase: 31-audit-stale-db-gated-test-fixtures (Plan 02)
    provides: TEST_DATABASE_URL wiring in .env + leak-detector hook
provides:
  - 5 pipeline/tests files (test_ingest.py, test_parse.py, test_resolve.py, test_seed_aliases.py, test_pipeline_run.py) pass with 0 failures/errors against scotus_test
  - pytest.ini asyncio_default_fixture_loop_scope/asyncio_default_test_loop_scope = session (fixes session-scoped-engine vs function-scoped-loop mismatch for all pipeline/tests DB-gated tests)
  - pipeline/parser/state_machine.py SECTION_HINT_MAP now matches plural PETITIONERS/RESPONDENTS (real transcript convention)
affects: [31-audit-stale-db-gated-test-fixtures, testing infrastructure for pipeline/tests generally]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "argparse.Namespace test fixtures must include job_id=None to match run_ingest()/run_parse()/run_resolve()'s current signature"
    - "SAVEPOINT (session.begin_nested()) to scope an expected-to-fail DB call's rollback within a test that also asserts on an earlier successful call's rows, when the get_session() mock doesn't commit"

key-files:
  created: []
  modified:
    - pytest.ini
    - pipeline/parser/state_machine.py
    - pipeline/tests/test_ingest.py
    - pipeline/tests/test_parse.py
    - pipeline/tests/test_resolve.py
    - pipeline/tests/test_seed_aliases.py

key-decisions:
  - "Fixed pytest.ini's asyncio loop scope (session-scoped) rather than touching conftest.py's session-scoped engine fixture — root cause was the loop/fixture scope mismatch, not the fixture design itself; verified zero regressions against the full test suite"
  - "Fixed SECTION_HINT_MAP's plural-form regex bug in state_machine.py directly (Rule 1 auto-fix) rather than only documenting it, given it's a self-contained, low-risk parser fix with real user-facing impact (SectionRail UI) already flagged in CONCERNS.md"
  - "Rewrote test_ingest_idempotent to match ingest.py's actual current contract (Case reuse + Argument duplicate rejection via ValueError) instead of the stale 'both calls succeed silently' assumption"
  - "5 pytest.fail('not implemented') stub tests (never written, not schema drift) marked xfail(strict=True) with documented reasons rather than implemented from scratch — out of this plan's fixture-repair scope"

patterns-established:
  - "Whenever conftest.py defines a session-scoped async engine fixture shared across a pytest-asyncio suite, asyncio_default_fixture_loop_scope/asyncio_default_test_loop_scope must also be session-scoped, or pooled connections break across tests"

requirements-completed: [TEST-02]

coverage:
  - id: D1
    description: "test_ingest.py's 3 DB-gated tests pass against scotus_test (job_id Namespace fix + idempotency contract rewrite)"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "test_parse.py's DB-gated + unit tests pass (job_id fix, anthropic SDK RateLimitError construction fix, new-PipelineRun-id assertion fix, SECTION_HINT_MAP plural regex bug fix)"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_parse.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "test_resolve.py's implemented test passes (job_id fix); 3 never-implemented stubs marked xfail with documented reason"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_resolve.py -q"
        status: pass
    human_judgment: false
  - id: D4
    description: "test_seed_aliases.py's 2 never-implemented stubs marked xfail with documented reason"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_seed_aliases.py -q"
        status: pass
    human_judgment: false
  - id: D5
    description: "test_pipeline_run.py's 2 tests pass (Utterance.strategy already populated correctly; the actual blocker was a session-scoped-engine vs function-scoped-event-loop mismatch, fixed via pytest.ini, not the test file)"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_pipeline_run.py -q"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-07-13
status: complete
---

# Phase 31 Plan 06: Repair Stale DB-Gated Pipeline Fixtures Summary

**Fixed job_id/argparse drift, an anthropic SDK construction bug, a genuine parser regex bug (plural PETITIONERS/RESPONDENTS never matched), a stale idempotency assumption in test_ingest.py, and a session-scoped-engine/function-scoped-event-loop pytest-asyncio mismatch — all 5 pipeline/tests files now pass (19 passed, 5 documented xfails, 0 failures) against scotus_test.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-13
- **Tasks:** 1 (single-task plan)
- **Files modified:** 6 (pytest.ini, pipeline/parser/state_machine.py, 4 of the 5 target test files — test_pipeline_run.py itself needed no changes)

## Accomplishments
- `pytest pipeline/tests/test_ingest.py pipeline/tests/test_parse.py pipeline/tests/test_resolve.py pipeline/tests/test_seed_aliases.py pipeline/tests/test_pipeline_run.py -q` now reports **19 passed, 5 xfailed, 0 failed** (previously 14 failed, 10 passed) — verified stable across repeated runs.
- Diagnosed and fixed the root cause of `test_pipeline_run.py`'s "Event loop is closed" / "another operation is in progress" failures: `conftest.py`'s session-scoped `engine` fixture (Plan 01) conflicts with pytest-asyncio's default function-scoped event loop. Fixed via `pytest.ini` (no `conftest.py` changes — stayed within Plan 01's ownership boundary).
- Fixed a genuine, user-facing parser bug in `pipeline/parser/state_machine.py`: `SECTION_HINT_MAP`'s `\bPETITIONER\b`/`\bRESPONDENT\b` regexes never matched the plural forms real SCOTUS transcripts almost always use ("ON BEHALF OF PETITIONERS"), silently dropping every `section_hint` on those TOC markers — this field drives the SectionRail jump-to-section navigation UI.
- Every `argparse.Namespace(...)` test fixture across the 5 files that omitted `job_id` (added when `run_ingest`/`run_parse`/`run_resolve` gained job-driven mode) now includes `job_id=None`.

## Task Commits

1. **Task 1: Diagnose + fix schema mismatches in the 5 pipeline/tests files (TEST-02)** — split across 5 atomic commits:
   - `fd06ecdf` — fix(31-06): pin pytest-asyncio to session-scoped event loop for DB tests
   - `c36280cf` — fix(31-06): repair test_parse.py stale fixtures (TEST-02)
   - `d42f169a` — fix(31-06): repair test_ingest.py stale fixtures (TEST-02)
   - `74fe7b5f` — fix(31-06): repair test_resolve.py + xfail unimplemented stubs (TEST-02)
   - `affdea0b` — docs(31-06): log out-of-scope findings from TEST-02 fixture repair

**Plan metadata:** (recorded below, in the final metadata commit)

## Files Created/Modified
- `pytest.ini` - Added `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope = session` so pipeline/tests' session-scoped `engine` fixture doesn't get orphaned connections across per-test event loops.
- `pipeline/parser/state_machine.py` - `SECTION_HINT_MAP` regexes for PETITIONER/RESPONDENT now match the plural forms real transcripts use (`\bPETITIONERS?\b`, `\bRESPONDENTS?\b`).
- `pipeline/tests/test_ingest.py` - Added `job_id=None` to 3 Namespace fixtures; rewrote `test_ingest_idempotent` to match ingest.py's actual duplicate-Argument-rejection contract (was asserting a stale "silently succeeds" behavior).
- `pipeline/tests/test_parse.py` - Added `job_id=None`; fixed `anthropic.RateLimitError` construction (current SDK dereferences `response.request` unconditionally); fixed `test_run_id_strategy`'s assertion to query the new `PipelineRun` row `run_parse()` creates (PIPE-11 re-run semantics) instead of the source run's id.
- `pipeline/tests/test_resolve.py` - Added `job_id=None` to the one implemented DB/mocked test; marked 3 never-implemented stub tests `xfail(strict=True)` with documented reasons.
- `pipeline/tests/test_seed_aliases.py` - Marked 2 never-implemented stub tests `xfail(strict=True)` with documented reasons.
- `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md` - Logged out-of-scope findings (see Deviations below).

## Decisions Made
- Fixed the `pytest.ini` loop-scope mismatch instead of modifying `conftest.py`'s fixtures (explicitly owned by Plan 01) — verified zero regressions against the full test suite (`tests/`, `pipeline/tests/`, `api/tests/`) both before and after the change.
- Fixed the `SECTION_HINT_MAP` plural-regex bug directly in production code (Rule 1) rather than only documenting it as out-of-scope, given it's a tiny, self-contained, low-risk fix with a real correctness/UX impact already flagged as a known fragility in `.planning/codebase/CONCERNS.md`.
- Rewrote `test_ingest_idempotent`'s assertions to match `ingest.py`'s actual current behavior (Case-level SELECT-first idempotency + Argument-level duplicate rejection via `ValueError`) rather than the stale "both calls succeed silently" assumption baked into the original test.
- Marked the 5 `pytest.fail("not implemented")` stub tests `xfail(strict=True)` rather than writing real implementations — these were never-implemented placeholders, not schema drift, and implementing them (mocked interactive `input()` flow, DB-integration resume-after-interrupt scenario, full seed-aliases coverage) is substantial new test-authoring work outside this plan's stated scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `pytest.ini` asyncio loop-scope mismatch blocked every second-or-later DB-gated test in a session**
- **Found during:** Task 1, initial verification run and repeated isolation testing
- **Issue:** `conftest.py`'s `engine` fixture (Plan 01) is session-scoped, but pytest-asyncio's default fixture/test loop scope is function-scoped. A pooled asyncpg connection checked out under one test's (now-closed) event loop and reused by the next test's (new) loop raised `RuntimeError("Event loop is closed")` or `sqlalchemy.exc.InterfaceError("another operation is in progress")`.
- **Fix:** Set `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope = session` in `pytest.ini`. Verified against the FULL test suite (not just this plan's 5 files) with `git diff`-comparable before/after runs: fixes exactly the 5 target failures this plan needed fixed, introduces 0 new failures.
- **Files modified:** `pytest.ini`
- **Verification:** `pytest pipeline/tests/*.py` (target 5 files) run twice consecutively: stable `19 passed, 5 xfailed`. Full suite (`tests/ pipeline/tests/ api/tests/`) before vs. after this change: 8 failures → 3 failures, all 3 remaining pre-existing and unrelated (see below).
- **Committed in:** `fd06ecdf`

**2. [Rule 1 - Bug] `SECTION_HINT_MAP` never matched plural TOC markers ("ON BEHALF OF PETITIONERS")**
- **Found during:** Task 1, `test_section_hint_not_cascade` investigation
- **Issue:** `\bPETITIONER\b`/`\bRESPONDENT\b` regexes require a word boundary immediately after the word — which never exists when the transcript says "PETITIONERS" (plural, the overwhelmingly common real-world form, e.g. Obergefell's "ON BEHALF OF PETITIONERS"). This silently dropped every `section_hint` on those markers — a real production bug, not test drift, already flagged as a fragility risk in `.planning/codebase/CONCERNS.md` and user-facing via the SectionRail navigation UI (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`).
- **Fix:** Changed `\bPETITIONER\b`/`\bRESPONDENT\b` to `\bPETITIONERS?\b`/`\bRESPONDENTS?\b`.
- **Files modified:** `pipeline/parser/state_machine.py`
- **Verification:** `test_section_hint_not_cascade` passes; full 5-file suite run clean.
- **Committed in:** `c36280cf`

**3. [Rule 1 - Bug] `argparse.Namespace` test fixtures missing `job_id` attribute**
- **Found during:** Task 1, initial failure triage across all 3 command modules
- **Issue:** `run_ingest()`, `run_parse()`, and `run_resolve()` all now unconditionally read `args.job_id` (added for job-driven admin-UI mode). 4 test fixtures across `test_ingest.py` (3) and `test_resolve.py` (1) constructed `argparse.Namespace(...)` without `job_id`, raising `AttributeError` before ever reaching DB logic.
- **Fix:** Added `job_id=None` to each Namespace.
- **Files modified:** `pipeline/tests/test_ingest.py`, `pipeline/tests/test_parse.py`, `pipeline/tests/test_resolve.py`
- **Verification:** All previously-`AttributeError`-failing tests now proceed to their DB logic.
- **Committed in:** `c36280cf`, `d42f169a`, `74fe7b5f`

**4. [Rule 1 - Bug] `anthropic.RateLimitError` construction incompatible with current anthropic SDK**
- **Found during:** Task 1, `test_llm_failure_modes`
- **Issue:** The current installed `anthropic` SDK's `RateLimitError.__init__` dereferences `response.request` unconditionally; the test's `response=None` construction (valid in an older SDK version) raised `AttributeError: 'NoneType' object has no attribute 'request'` before the test's own tenacity-retry assertion ever ran.
- **Fix:** Built a real `httpx.Request`/`httpx.Response` pair and passed that as `response=`.
- **Files modified:** `pipeline/tests/test_parse.py`
- **Verification:** `test_llm_failure_modes` passes.
- **Committed in:** `c36280cf`

### Documented, Not Fixed (per plan's explicit "genuine production bug → document, don't mask" guidance and executor scope-boundary rules)

**5. `test_ingest_idempotent` encoded a stale "duplicate ingest succeeds silently" assumption**
- **Found during:** Task 1
- **Issue:** `ingest.py` (D-01) enforces `UNIQUE(source_docket, question_number)` on `Argument` by attempting a fresh INSERT and converting the resulting `IntegrityError` into `ValueError("Duplicate argument: ...")` — it is NOT idempotent at the Argument level (only Case creation is SELECT-first). The original test expected the second `run_ingest()` call to complete without raising.
- **Fix:** This wasn't a bug to "not fix" — it was a genuine test-vs-current-behavior mismatch, squarely within this plan's stated scope ("Assertions on obsolete shapes: update to the current schema's actual behavior"). Rewrote the test to assert the current contract explicitly (Case reused, Argument duplicate rejected with `ValueError`, exactly 1 row of each exists). Used a `session.begin_nested()` SAVEPOINT to scope the expected-to-fail second call's rollback, since the test's `_make_session_cm` mock never commits (unlike production's real `get_session()`), so both calls otherwise share one transaction.
- **Files modified:** `pipeline/tests/test_ingest.py`
- **Committed in:** `d42f169a`

**6. `test_argument_oyez_field.py`/`test_people.py` (api/tests) 404s — NOT actually in this plan's scope**
- **Found during:** Full-suite regression check after the `pytest.ini` fix
- **Issue:** Plan 31-05's `deferred-items.md` entry claims these two files are "explicitly assigned to Plan 31-06" — that's inaccurate; this plan's `files_modified` frontmatter lists only the 5 `pipeline/tests` files. Both fail with `404` when run as part of the full suite but pass/skip in isolation — an order-dependent test-data assumption (fixed `id=1` rows), not schema drift, and reproduced identically before and after this plan's `pytest.ini` change.
- **Why not fixed here:** Genuinely outside this plan's declared file scope; flagged for whoever actually owns these two files.
- **Status:** Logged to `deferred-items.md` for the record.

**7. `test_resolve_interrupt_sets_needs_review` — pre-existing cross-test event-loop-policy pollution (full `pipeline/tests/` dir only)**
- **Found during:** Full `pipeline/tests/` directory regression check (broader than this plan's exact 5-file verification command)
- **Issue:** `pipeline/tests/test_ingest_startup_guard.py` (not in this plan's scope) imports `pipeline.__main__`, whose module body unconditionally calls `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` at import time. When the full `pipeline/tests/` directory runs (not this plan's 5-file verification command), this import precedes `test_resolve_interrupt_sets_needs_review`, and its internal `asyncio.run(...)` then behaves differently — `run_resolve()`'s `except KeyboardInterrupt:` branch never executes.
- **Why not fixed here:** `test_ingest_startup_guard.py` is not in this plan's `files_modified`. Reproduced identically with both the pre- and post-31-06 `pytest.ini`, confirming it's pre-existing and unrelated to this plan's changes. Does NOT affect this plan's own acceptance criteria — the plan's verification command runs only the 5 target files, which never import `pipeline.__main__`.
- **Status:** Logged to `deferred-items.md`; suggested fix noted there (scope the policy mutation to a fixture, don't set it at module import time).

**8. 5 `pytest.fail("not implemented")` stub tests — never written, not schema drift**
- **Found during:** Task 1, initial failure triage
- **Issue:** `test_resolve_alias_hit`, `test_resolve_interactive_prompt`, `test_resolve_resumes_after_interrupt` (test_resolve.py) and `test_seed_creates_justices`, `test_seed_idempotent` (test_seed_aliases.py) are literal `pytest.fail("not implemented")` bodies — pre-existing placeholders, never implemented at all, not broken by any schema change.
- **Why not fixed here:** Writing real implementations (a mocked interactive `input()` flow, a DB-integration resume-after-interrupt scenario, and full seed-aliases integration coverage) is substantial new test-authoring work, outside this plan's scope of repairing existing fixtures against the current schema.
- **Fix:** Marked `xfail(strict=True)` with a documented reason, satisfying this plan's acceptance criteria ("Any remaining xfail/skip carries a documented reason in the SUMMARY").
- **Files modified:** `pipeline/tests/test_resolve.py`, `pipeline/tests/test_seed_aliases.py`
- **Committed in:** `74fe7b5f`

---

**Total deviations:** 4 auto-fixed (1 blocking test-infra config, 1 bug fix in production code, 2 stale-fixture-drift categories across multiple files), 4 documented-not-fixed (1 stale-assumption test rewrite within scope, 3 genuinely out-of-scope findings logged to deferred-items.md).
**Impact on plan:** All auto-fixes were necessary for correctness (parser bug) or to unblock the plan's own DB-gated tests (loop-scope config, job_id drift, anthropic SDK drift). No scope creep into unrelated production files (`admin_arguments.py`, `test_ingest_startup_guard.py`, `api/tests/*` were all left untouched and logged instead).

## Issues Encountered
- Diagnosing the "Event loop is closed" / "another operation is in progress" failures required building 3 standalone diagnostic scripts (in the session scratchpad, not committed) to isolate the root cause from `pytest-asyncio`'s fixture/loop-scope interaction — direct reproduction via `asyncio.run()` called repeatedly against a shared `engine` object confirmed the theory before touching any project file.
- An initial attempt to fix via a per-test-file `pytest.mark.asyncio(loop_scope="session")` marker did not fully resolve the issue (the `async_session`/`engine` fixtures still resolved to a different loop scope than the marked test) — the working fix required the `pytest.ini`-level `asyncio_default_fixture_loop_scope` setting instead.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 `pipeline/tests` files this plan owned pass cleanly (0 failures/errors) against `scotus_test`, matching TEST-02.
- `pytest.ini`'s new session-scoped loop config benefits the whole `pipeline/tests` directory, not just this plan's 5 files — verified no regressions against the full suite.
- Remaining known gaps (logged to `deferred-items.md`, not blocking this plan): 5 never-implemented resolve/seed-aliases test stubs; a pre-existing `test_ingest_startup_guard.py` event-loop-policy pollution bug (full-directory-run only); 2 api/tests 404s incorrectly attributed to this plan by 31-05's notes.

## Self-Check: PASSED

- FOUND: `pipeline/tests/test_ingest.py`
- FOUND: `pipeline/tests/test_parse.py`
- FOUND: `pipeline/tests/test_resolve.py`
- FOUND: `pipeline/tests/test_seed_aliases.py`
- FOUND: `pipeline/parser/state_machine.py`
- FOUND: `pytest.ini`
- FOUND: `.planning/phases/31-audit-stale-db-gated-test-fixtures/deferred-items.md`
- FOUND commit `fd06ecdf`
- FOUND commit `c36280cf`
- FOUND commit `d42f169a`
- FOUND commit `74fe7b5f`
- FOUND commit `affdea0b`

---
*Phase: 31-audit-stale-db-gated-test-fixtures*
*Completed: 2026-07-13*
