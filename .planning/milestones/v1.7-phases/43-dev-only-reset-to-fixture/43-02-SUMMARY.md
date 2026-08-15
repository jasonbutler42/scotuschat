---
phase: 43-dev-only-reset-to-fixture
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, admin, dev-tooling, import-convokit, truncate, state-machine]

# Dependency graph
requires:
  - phase: 43-dev-only-reset-to-fixture (Plan 43-01)
    provides: reset_to_fixture's TRUNCATE + in-process run_import_convokit reseed slice, ResetToFixtureResponse contract, conditional router mount
  - phase: 41-canonical-corpus-fixture-selection
    provides: FIXTURES.md's confirmed four-fixture set (13015, 18897, 22372 added by this plan; 15169 already reseeded by 43-01)
provides:
  - api/services/admin_dev.py::FIXTURE_SET — all four confirmed fixtures (15169 Complexity, 13015 Draft, 18897 Published, 22372 Mid-pipeline)
  - api/services/admin_dev.py::reset_to_fixture — per-fixture AdminJob existence check (in addition to 43-01's Argument check) and a run_import_convokit exception translated into ResetIncompleteError, so a partial reseed always fails loudly
  - api/services/admin_dev.py::reset_to_fixture — state-realization block driving 13015 to DRAFT and 18897 to DRAFT-then-PUBLISHED via the real admin_jobs.approve_job / admin_arguments.publish_argument service functions, and 22372's AdminJob to RUNNING via the one documented direct column write (D-04)
  - Nine new/extended integration tests in api/tests/test_admin_dev_routes.py covering the full 4-fixture reseed, response ordering, repeatability, empty-DB idempotency, partial-reseed failure, and all four end states plus their audit-log footprint
affects: [43-03-frontend-confirm-ui, 43-04-live-uat, 44-resolve-table-rework]

# Actuals (#2632)
actuals:
  tokens: 10115
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State-realization runs strictly after every fixture's existence checks pass, keyed by ids collected during the reseed loop — never assumed/hardcoded ids"
    - "db.expire_all() + re-select before building a response, whenever prior writes in the same call used synchronize_session=False (Phase 31 refresh-after-bulk-update precedent, generalized to a whole batch of fixtures)"
    - "Wrap a third-party/pipeline call site in try/except and re-raise the module's own domain exception, rather than letting an unrelated exception type escape a service function unhandled"

key-files:
  created: []
  modified:
    - api/services/admin_dev.py
    - api/tests/test_admin_dev_routes.py

key-decisions:
  - "FIXTURE_SET extended to all four fixtures in FIXTURES.md's declaration order (Complexity, Draft, Published, Mid-pipeline) — this order is also the reseed order and the response order."
  - "Added a per-fixture AdminJob existence check (not just the Argument check plan 43-01 shipped) — a fixture that landed an Argument row but no paired AdminJob is exactly as incomplete as a missing Argument, per the Phase 30 invariant."
  - "Wrapped the run_import_convokit call in try/except and re-raise as ResetIncompleteError — a scoped --conversation-id lookup failure raises argparse.ArgumentTypeError BEFORE run_import_convokit's own per-conversation try/except guard, so an unrelated exception type would otherwise escape this service unhandled (RESEARCH.md Open Question 2, resolved in favor of the service catching it directly rather than relying on the router's generic exception handling)."
  - "18897 (Published) requires approve_job() THEN publish_argument(), in that exact order — publish_argument's resolve-gate raises when resolved_at is null, which is the freshly-imported PIPELINE state. Commented explicitly so the two calls are never 'simplified' into one."
  - "22372 (Mid-pipeline)'s AdminJob.status flip to RUNNING is the one direct column write in this service — D-03's 'never direct column writes' rule is scoped to Argument.status, not AdminJob.status, and no existing service function performs a PAUSED->RUNNING flip (RESEARCH.md Pitfall 3). Chose the simple flip over partially resolving ArgumentParticipant rows because the Complexity fixture (15169) already gives Phase 44's Resolve Table Rework a fully editable PIPELINE argument."
  - "Did NOT mark DEVTOOL-01 complete in REQUIREMENTS.md, even though this plan's frontmatter lists it. DEVTOOL-01's text requires the operator can trigger the reset 'from the admin panel' — that UI trigger ships in Plan 43-03, not here. Marking it now (backend-only) would misstate phase progress, mirroring 43-01-SUMMARY's identical decision for the same reason."

patterns-established:
  - "State-realization block pattern: collect (entry, argument_id, admin_job_id) triples during the reseed loop, look up by conversation_id AFTER all existence checks pass, call service functions in the load-bearing order, then rebuild the response from a fully re-selected (expire_all()'d) view of the database — never from values the code intended to write."

requirements-completed: []  # DEVTOOL-01 intentionally NOT marked — see key-decisions; the admin-panel trigger ships in Plan 43-03

coverage:
  - id: D1
    description: "reset_to_fixture reseeds all four confirmed fixtures (15169, 13015, 18897, 22372) through the real import-convokit path in FIXTURE_SET declaration order, and nothing that predated the reset survives"
    requirement: "DEVTOOL-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_wipes_and_reseeds_fixtures"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_response_order_is_declaration_order"
        status: pass
    human_judgment: false
  - id: D2
    description: "Repeat resets and a reset against an already-empty database both converge on the same identical four-fixture end state, with no duplicate (source_docket, question_number) pairs"
    requirement: "DEVTOOL-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_is_repeatable"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_against_empty_database"
        status: pass
    human_judgment: false
  - id: D3
    description: "A partial reseed (corpus missing one of the four conversations) never returns a 200 with a short fixtures list"
    requirement: "DEVTOOL-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_incomplete_reseed_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "The three state-variety fixtures land in mutually distinguishable end states (Draft/Published/Mid-pipeline) via the real service functions, with matching argument_status_log rows for the two that transitioned and none for the two that stayed pipeline, and every fixture retains exactly one AdminJob"
    requirement: "DEVTOOL-01"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_realizes_state_variety"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_writes_status_log_rows"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_response_reports_realized_states"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-31
status: complete
---

# Phase 43 Plan 2: Dev-Only Reset to Fixture — Full Four-Fixture Reseed + State Realization Summary

**`reset_to_fixture` now reseeds all four confirmed CORPUS-12 fixtures (15169, 13015, 18897, 22372) through the real `run_import_convokit` importer and drives the three state-variety fixtures into distinguishable Draft/Published/Mid-pipeline end states via the real `approve_job`/`publish_argument` service functions, with a documented single exception for the Mid-pipeline `AdminJob` flip.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `FIXTURE_SET` grown from 1 entry to all 4, transcribed from `.planning/FIXTURES.md`, in the exact declaration order that is also the reseed order and the response order
- Two new failure surfaces closed: a `run_import_convokit` exception is now caught and re-raised as `ResetIncompleteError` (rather than escaping the service unhandled), and a fixture landing without its paired `AdminJob` now also raises `ResetIncompleteError`
- State-realization block: 15169 stays untouched (PIPELINE/PAUSED-RESOLVE); 13015 moves to DRAFT via `approve_job`; 18897 moves to DRAFT then PUBLISHED via `approve_job` then `publish_argument` (order load-bearing); 22372's `AdminJob` flips PAUSED→RUNNING via the one documented direct column write (D-04)
- Response `argument_status`/`admin_job_status` fields are populated from a fresh post-transition database read (`db.expire_all()` + re-select), never from `FIXTURE_SET` or intended write values
- Nine tests total in `api/tests/test_admin_dev_routes.py` (2 pre-existing extended, 7 new): full reseed/wipe proof across five table types, response-order determinism, repeatability, empty-database idempotency, partial-reseed failure, and the full four-state-variety assertion set including `argument_status_log` presence/absence

## Task Commits

Each task was committed atomically:

1. **Task 1: Reseed all four fixtures and prove nothing else survives** - `aa98872f` (feat, tdd)
2. **Task 2: Drive the three state-variety fixtures to their intended states (D-03, D-04)** - `85d404b3` (feat, tdd)

_Plan-metadata commit (SUMMARY/STATE/ROADMAP) follows below._

## Files Created/Modified
- `api/services/admin_dev.py` — `FIXTURE_SET` extended to 4 entries; reseed loop now catches `run_import_convokit` exceptions and checks for a paired `AdminJob`, both raising `ResetIncompleteError`; new state-realization block (Task 2) calling `admin_jobs.approve_job`/`admin_arguments.publish_argument` and one direct `AdminJob.status` bulk update; response rebuilt from a fully re-selected post-transition view
- `api/tests/test_admin_dev_routes.py` — synthetic corpus grown to all four fixtures (`FIXTURE_CONVERSATIONS`, each with a real October-Term-prefixed `case_id` and distinct docket); `test_reset_wipes_and_reseeds_fixtures` extended to seed throwaway rows across Person/CourtTenure/Argument/PipelineRun/Utterance; seven new tests added (`test_reset_response_order_is_declaration_order`, `test_reset_is_repeatable`, `test_reset_against_empty_database`, `test_reset_incomplete_reseed_raises`, `test_reset_realizes_state_variety`, `test_reset_writes_status_log_rows`, `test_reset_response_reports_realized_states`)

## Decisions Made
- `FIXTURE_SET`'s four entries are transcribed verbatim from `.planning/FIXTURES.md`'s Fixture Set table, in that table's row order (Complexity, Draft, Published, Mid-pipeline) — a code comment records `.planning/FIXTURES.md` as the authority if the two ever disagree.
- Added a defensive AdminJob-existence check to the reseed loop (not in 43-01's original scope) — a fixture landing an Argument row but no paired AdminJob is exactly as incomplete as a missing Argument row, matching the Phase 30 invariant this whole reset exists to preserve.
- Wrapped `run_import_convokit` in try/except, re-raising as `ResetIncompleteError` — resolves RESEARCH.md's Open Question 2 in favor of the service catching the failure directly (a scoped `--conversation-id` lookup miss raises `argparse.ArgumentTypeError` *before* `run_import_convokit`'s own per-conversation resilience guard, so it would otherwise escape this service as an unrelated, unhandled exception type).
- 18897 (Published)'s two service calls (`approve_job` then `publish_argument`) are commented as strictly ordered — `publish_argument`'s resolve-gate (`ValueError` when `resolved_at IS NULL`) makes the ordering load-bearing, not stylistic.
- 22372 (Mid-pipeline)'s `AdminJob.status` flip to RUNNING is the one direct column write in this service, per D-04/RESEARCH.md Pitfall 3 — D-03's "never direct column writes" rule is scoped to `Argument.status`, and no service function performs a PAUSED→RUNNING flip. Took the simple flip over partially resolving `ArgumentParticipant` rows because 15169 (Complexity) already gives Phase 44's Resolve Table Rework a fully editable PIPELINE argument with a PAUSED/RESOLVE job, so the heavier alternative would add cost without unlocking anything Phase 44 lacks.
- Did **not** mark DEVTOOL-01 complete in `REQUIREMENTS.md`, despite this plan's frontmatter listing it as a `requirements` entry. DEVTOOL-01's text explicitly requires the operator can trigger the action "from the admin panel" — that UI trigger is Plan 43-03's deliverable, not this plan's. Marking it complete now would misstate phase progress; this mirrors 43-01-SUMMARY's identical decision and rationale.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/Test design] Deadlock between consecutive HTTP resets and the test's own DB session**
- **Found during:** Task 1, first run of `test_reset_is_repeatable` and `test_reset_against_empty_database`
- **Issue:** Both tests execute two consecutive `_post_reset` calls, with a `db.execute(select(...))` read via the test's own `db` fixture session in between. SQLAlchemy's autobegin leaves that session's transaction open (no implicit commit after a bare `select()`), holding an `ACCESS SHARE` lock on `arguments`. Postgres's `TRUNCATE` (used by the second reset) requires `ACCESS EXCLUSIVE`, which conflicts with any open transaction touching the same table, even a read-only one — the second reset's `TRUNCATE` blocked indefinitely waiting for the test's own session to release its lock, and the test process hung (observed as a 7+ minute stall with no test progress, confirmed via `ps`/`etimes`).
- **Fix:** Added an explicit `await db.commit()` after each such read, immediately before triggering the next reset — ends the test session's read transaction and releases the lock. Documented inline with a comment explaining the lock-conflict mechanism so a future reader doesn't reintroduce it.
- **Files modified:** `api/tests/test_admin_dev_routes.py`
- **Verification:** Both tests complete in ~1-2s each after the fix; full `test_admin_dev_routes.py` module runs in ~11s (previously hung indefinitely).
- **Committed in:** `aa98872f` (Task 1 commit)

**2. [Rule 1 - Bug/Test design] `sqlalchemy.exc.MissingGreenlet` from reading an expired ORM attribute outside an explicit await**
- **Found during:** Task 1 (throwaway-row assertions) and Task 2 (state-variety/status-log/response-state assertions)
- **Issue:** `db.expire_all()` expires every attribute of every already-loaded ORM object, including primary keys. Several test helpers (`_fetch_argument`, `_fetch_admin_job`) called `db.expire_all()` internally; when a later line accessed an already-fetched object's attribute (e.g. `throwaway_person.id`, or `draft_arg.id` after a subsequent `_fetch_argument` call for a different conversation), SQLAlchemy attempted a synchronous lazy-reload of the expired attribute, which requires `greenlet_spawn` context and isn't available at plain attribute-access time in an async test — raising `sqlalchemy.exc.MissingGreenlet`.
- **Fix:** (a) Captured throwaway rows' primary keys as plain ints immediately after each `flush()`/`commit()`, before any `expire_all()` call, and used those captured ints in later assertions instead of re-reading the ORM object's `.id`. (b) Removed the internal `db.expire_all()` from `_fetch_admin_job` (kept only in `_fetch_argument`, called once per "fresh look") since no test path re-uses a stale `AdminJob` object across a write. (c) In `test_reset_writes_status_log_rows`, read each `.id` immediately after its own `_fetch_argument` call rather than holding four `Argument` objects across multiple subsequent `_fetch_argument` invocations.
- **Files modified:** `api/tests/test_admin_dev_routes.py`
- **Verification:** Full `api/tests/test_admin_dev_routes.py` module: 10 passed.
- **Committed in:** `aa98872f` (throwaway-row fix) and `85d404b3` (state-variety/status-log fix)

---

**Total deviations:** 2 auto-fixed, both Rule 1 (test-technique bugs discovered while writing verification — a session-lock deadlock and an ORM-attribute-expiry footgun — not implementation defects in `admin_dev.py` itself). No scope creep; both were necessary to make the plan's own verification actually run and pass.

## Issues Encountered

None beyond the two deviations above, which were resolved during Task 1/Task 2 execution before their respective commits.

## User Setup Required

None — reuses the `ENVIRONMENT=development`/`TEST_DATABASE_URL` setup already confirmed present by Plan 43-01. `app/.env`'s independent `ENVIRONMENT` value (needed by Plan 43-03, not this plan) remains unset per 43-01-SUMMARY's carry-forward note — still flagged for the Plan 43-03 executor, not actioned here.

## Next Phase Readiness
- The backend is now feature-complete for DEVTOOL-01's data behavior: all four fixtures reseed deterministically, land in four distinguishable states, and a partial reseed always fails loudly. Plan 43-03 (frontend) can build the admin-panel trigger against the same `ResetToFixtureResponse` contract Plan 43-01 locked, now backed by the full four-fixture implementation.
- `ArgumentStatusLog` rows for 13015/18897 and their absence for 15169/22372 are asserted directly — Phase 44's Resolve Table Rework and Phase 45's publish-visibility bug work can rely on this reset producing a real, audit-consistent Draft/Published pair rather than a synthetic shortcut.
- **Carry-forward for Plan 43-03/43-04:** DEVTOOL-01 remains unchecked in `REQUIREMENTS.md` pending the admin-panel UI trigger; DEVTOOL-02 (environment hard-gate) was already fully delivered by Plan 43-01 and remains unchecked only because it was bundled with DEVTOOL-01 in this phase's not-yet-run state-sync step.
- **Performance note carried into any future manual/live-corpus run:** a real-corpus reset (not the synthetic test corpus) performs four full streaming passes over `data/corpus/utterances.jsonl`, one per fixture's October Term — expect roughly 80-120 seconds end-to-end, documented in `reset_to_fixture`'s own docstring so Plan 43-04's live UAT isn't mistaken for a hang.

## Self-Check: PASSED

Confirmed both modified files exist on disk with the expected content (`api/services/admin_dev.py`'s `FIXTURE_SET` has 4 entries; `api/tests/test_admin_dev_routes.py` has 10 test functions). Both task commit hashes (`aa98872f`, `85d404b3`) confirmed present in `git log --oneline --all`. Full test suite (`./.venv/Scripts/python.exe -m pytest -q`) shows 837 passed, 5 xfailed, 4 pre-existing errors (backlog item 999.10, unrelated to this plan) — no regressions from the 834-passed baseline recorded in 43-01-SUMMARY.

---
*Phase: 43-dev-only-reset-to-fixture*
*Completed: 2026-07-31*
</content>
