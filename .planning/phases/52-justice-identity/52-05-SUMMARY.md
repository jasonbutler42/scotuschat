---
phase: 52-justice-identity
plan: 05
subsystem: admin-tooling
tags: [fastapi, sveltekit, pydantic, reset-to-fixture, dev-tooling, abortsignal]

# Dependency graph
requires:
  - phase: 52-04
    provides: "reset_to_fixture seeds the full justice bench between TRUNCATE and the fixture reseed loop (D-16); measured 71.67s wall-clock end-to-end reset duration used to size this plan's AbortSignal"
provides:
  - "GET /api/admin/dev/fixture-state (dev-only, read-only) — answers what FIXTURE_SET last landed as and whether a reset is currently in flight, without writing anything"
  - "reset_to_fixture records per-step progress (justice seed, then one per FIXTURE_SET entry, 5 steps total) in a process-local record, cleared in a finally block on any exit — success or raise"
  - "app/src/routes/admin/dev-fixture-state/+server.ts — browser-facing proxy for the above, mirroring admin/pipeline/[job_id]/+server.ts's shape"
  - "resetToFixture's frontend action re-reads fixture state on any non-404 failure and reports one of four evidence-based outcomes (full success/no error, partial reseed, inconclusive re-read, environment refusal) instead of asserting probable corruption for every failure mode"
  - "The reset fetch carries an AbortSignal (180s) sized above the measured 71.67s floor; exceeding it routes into the re-read rather than being reported as a failure outright"
  - "The Running state's status line advances through 5 per-fixture progress steps, polled from the backend's actual progress record — never advanced on a timer"
  - "43-UI-SPEC.md's Copywriting Contract carries a superseded-note recording that its original two-copy lock is lifted by D-14, pointing to 52-UI-SPEC.md as the live contract"
affects: [54]

# Actuals (#2632) — pairs with the plan's estimate to calibrate future estimates.
actuals:
  tokens: 15673
  tasks: 2
  commits: 3
  plan_head_before: 100223eaf6ba68e3df213ed97a24a433ff2bec23

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Process-local progress record guarded by asyncio.Lock, set/cleared inside the operation it tracks — explicitly documented as not needing to survive a restart or cross workers (single-operator, localhost, dev-only tool)"
    - "Backend progress token ('seeding_justices' | 'reseeding_fixture_N') vs. frontend-owned Copywriting Contract literal — the frontend maps the token to its own display string, so the two layers can't drift independently even though both know about fixture ordering"
    - "D-14 re-read convergence point: every non-404 resetToFixture failure (thrown fetch, non-ok status, unparseable body, wrong fixture count) routes through one resolveFromReRead helper, which classifies the re-read's evidence into full-success / partial / inconclusive rather than asserting from which code path failed"

key-files:
  created:
    - app/src/routes/admin/dev-fixture-state/+server.ts
  modified:
    - api/services/admin_dev.py
    - api/schemas/admin_dev.py
    - api/routers/admin_dev.py
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+page.svelte
    - .planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/43-UI-SPEC.md
    - api/tests/test_admin_dev_routes.py
    - tests/test_admin_dev_router_gate.py
    - tests/test_admin_dev_frontend_gate.py

key-decisions:
  - "The GET endpoint's progress field carries a machine token ('seeding_justices' | 'reseeding_fixture_N'), not the rendered copy string — the Svelte component owns the 52-UI-SPEC.md literal strings and maps the token to them, keeping the Copywriting Contract in exactly one place (the frontend) even though the backend independently knows fixture declaration order."
  - "The D-14 re-read runs directly against FASTAPI_BASE_URL from +page.server.ts's own server-side action, not through the new dev-fixture-state/+server.ts proxy — that proxy exists specifically for the browser's client-side polling (which has no FASTAPI_BASE_URL access), and the server action already has the same direct access resetToFixture's own POST uses."
  - "AbortSignal sized at 180s: ~2.5x the 71.67s measured floor (a direct-call measurement, not through HTTP — 52-04-SUMMARY.md's own methodology caveat), while staying well under undici's 300s headersTimeout ceiling. Not re-measured through the live HTTP path in this plan — deferred to the human-check UAT item, consistent with workflow.human_verify_mode=end-of-phase."
  - "'Full success, no error' interpretation compares the re-read's per-fixture status/latest_import_run_step against a hardcoded expected-end-state table (mirroring api/services/admin_dev.py's FIXTURE_SET state-realization block) rather than asking the backend for a computed 'matches expected' field — Task 1's GET returns only raw facts, so the frontend owns the interpretation, matching D-14's evidence-based framing."

requirements-completed: [JUSTICE-04]

coverage:
  - id: D1
    description: "GET /api/admin/dev/fixture-state answers what each FIXTURE_SET conversation landed as (present/status/latest_import_run_step) and whether a reset is currently in flight"
    requirement: JUSTICE-04
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_fixture_state_before_reset_reports_all_absent"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_fixture_state_after_reset_reports_expected_states"
        status: pass
    human_judgment: false
  - id: D2
    description: "The GET performs no write — calling it twice in a row leaves every table byte-identical"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_fixture_state_performs_no_write"
        status: pass
    human_judgment: false
  - id: D3
    description: "The new GET is dev-only — absent (404, not 403) outside development, via the same router gate its siblings use"
    verification:
      - kind: integration
        ref: "tests/test_admin_dev_router_gate.py#test_fixture_state_route_absent_outside_development"
        status: pass
      - kind: integration
        ref: "tests/test_admin_dev_router_gate.py#test_fixture_state_route_present_in_development"
        status: pass
    human_judgment: false
  - id: D4
    description: "reset_to_fixture records per-step progress (justice seed, then fixture 1-4 of 4) and clears the record on any exit — success or raise"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_progress_advances_through_expected_steps_then_clears"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_progress_cleared_after_mid_reset_failure"
        status: pass
    human_judgment: false
  - id: D5
    description: "The frontend resetToFixture action's D-14 re-read (four evidence-based outcomes) and the Running state's D-15 per-fixture progress polling behave correctly end-to-end against a real reset"
    verification: []
    human_judgment: true
    rationale: "This is TypeScript/Svelte runtime branching (resolveFromReRead's classification logic, and pollResetProgress's polling loop) inside a SvelteKit server action and component. Per CLAUDE.md's Testing Policy, frontend behavior is verified by the operator's eye or a real browser, never by a source-text contract test — tests/test_admin_dev_frontend_gate.py asserts structural/textual invariants only (the three error-copy literals exist verbatim, no fourth variant). The live end-to-end verification is Task 2's own <verify><human-check>, deferred to this phase's UAT batch per workflow.human_verify_mode=end-of-phase (not run synchronously during this autonomous plan)."
  - id: D6
    description: "43-UI-SPEC.md's Copywriting Contract records that its original two-copy lock is lifted by D-14, with a pointer to 52-UI-SPEC.md as the live contract, without deleting the historical text"
    verification:
      - kind: other
        ref: "grep -c 'No third variant is ever returned' .planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/43-UI-SPEC.md -> 1"
        status: pass
    human_judgment: false
  - id: D7
    description: "FASTAPI_BASE_URL (server-only env var) never reaches the browser — the new proxy route holds it, +page.svelte does not"
    verification:
      - kind: other
        ref: "grep -c FASTAPI_BASE_URL app/src/routes/admin/dev-fixture-state/+server.ts -> 4; grep -rc FASTAPI_BASE_URL app/src/routes/admin/+page.svelte -> 0"
        status: pass
    human_judgment: false

duration: 57min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 05: Reset-to-Fixture Evidence-Based Errors and Progress Summary

**A dev-only read-only GET answers what the last reset actually left behind, `resetToFixture` now re-reads that evidence on any failure instead of guessing which of two canned strings to show, and the Running state advances through five real per-fixture progress steps instead of one static line for a multi-minute operation.**

## Performance

- **Duration:** 57 min (estimated — start time not explicitly logged at session start; see Issues Encountered)
- **Started:** ~2026-09-25T13:41:04Z (estimated, using the prior plan's own completion timestamp as a floor)
- **Completed:** 2026-09-25T14:38:21Z
- **Tasks:** 2
- **Files modified:** 9 (8 modified, 1 created)

## Accomplishments

- `GET /api/admin/dev/fixture-state` (dev-only, mounted only when `settings.environment == "development"`, the same gate `reset-to-fixture` uses) re-reads what each `FIXTURE_SET` conversation landed as — presence, status, latest import-run step — and the current reset progress record, performing zero writes; proven by a row-count snapshot taken before and after two consecutive calls
- `reset_to_fixture` now records progress through 5 steps (`seeding_justices`, then `reseeding_fixture_1`..`reseeding_fixture_4`) in a process-local record guarded by an `asyncio.Lock`, cleared in a `finally` block so a raise at any point never leaves a stale "still running" record — proven both for the success path and for a raise partway through the reseed loop
- `app/src/routes/admin/dev-fixture-state/+server.ts` proxies the GET for the browser's own polling, keeping `FASTAPI_BASE_URL`/`ADMIN_TOKEN` server-only (Architecture Rule 2) — the `+page.server.ts` action's own re-read calls the backend directly instead, since it already has the same server-side access
- `resetToFixture`'s frontend action carries an `AbortSignal` (180s, sized above the 71.67s measured floor from 52-04) and routes every non-404 failure — thrown fetch/abort, non-ok status, unparseable body, or a fixtures array that isn't exactly 4 entries — through one `resolveFromReRead` convergence point, which classifies the re-read's evidence into full success (no error shown — the existing Success markup renders), a genuine partial reseed (new `RESET_PARTIAL_ERROR`), or an inconclusive re-read (`RESET_MID_ERROR`, text unchanged, now the true fallback instead of the default for every failure)
- The Running state's status line polls the new proxy every second and renders the backend's actually-reported step, never advancing on a timer — `Seeding justices…` through `Reseeding fixture 4 of 4…`
- `43-UI-SPEC.md`'s Copywriting Contract carries a dated superseded-note recording that its original "No third variant is ever returned" lock is lifted by Phase 52 D-14, quoting the original lock text and pointing to `52-UI-SPEC.md` as the live contract, without deleting the historical row

## Task Commits

Each task was committed atomically:

1. **Task 1: One dev-only read that answers both "what landed" and "where is it now"** - `1e53b3b59` (feat)
2. **Task 2: Four outcomes driven by evidence, and a progress line that only reports what it observed** - `41e2d5d9b` (feat)
3. **Follow-up (Task 1 scope, Rule 2 deviation): pin the progress record's step sequence and clear-on-exit** - `dd0a48fe1` (test)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified
- `app/src/routes/admin/dev-fixture-state/+server.ts` - new browser-facing proxy for the fixture-state GET
- `api/services/admin_dev.py` - `get_fixture_state()`, the process-local progress record + helpers, `reset_to_fixture` wrapped in try/finally with per-step progress calls
- `api/schemas/admin_dev.py` - `FixtureStateItem`, `ResetProgress`, `FixtureStateResponse`
- `api/routers/admin_dev.py` - `GET /fixture-state`
- `app/src/routes/admin/+page.server.ts` - `RESET_PARTIAL_ERROR`, `RESET_ABORT_TIMEOUT_MS`, `EXPECTED_FIXTURE_END_STATES`, `reReadFixtureState`/`classifyFixtureStateOutcome`/`resolveFromReRead`, restructured `resetToFixture` action
- `app/src/routes/admin/+page.svelte` - progress polling (`pollResetProgress`, `fixtureProgressCopy`, `resetProgressText`), Running-state text swap
- `.planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/43-UI-SPEC.md` - superseded-note amendment
- `api/tests/test_admin_dev_routes.py` - 6 new tests (fixture-state before/after reset, no-write snapshot, auth-required, progress-sequence, progress-cleared-on-raise)
- `tests/test_admin_dev_router_gate.py` - 2 new tests (absence outside development, presence in development)
- `tests/test_admin_dev_frontend_gate.py` - updated for the three-copy (was two) error-literal contract

## Decisions Made
See `key-decisions` in frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated `tests/test_admin_dev_frontend_gate.py`'s "no third variant" assertion**
- **Found during:** Task 2, running its own `<verify>` block
- **Issue:** `test_error_copies_match_ui_spec` asserted that exactly two `'Reset failed...'` string literals exist in `+page.server.ts` and rejected any third — the exact lock D-14 explicitly lifts. Left unchanged, this test would fail against Task 2's own required behavior (adding `RESET_PARTIAL_ERROR`).
- **Fix:** Added `RESET_PARTIAL_ERROR` as a recognized third literal; updated the assertion to allow exactly three, still rejecting a fourth.
- **Files modified:** `tests/test_admin_dev_frontend_gate.py`
- **Verification:** `pytest tests/test_admin_dev_frontend_gate.py -q` — 4 passed
- **Committed in:** `41e2d5d9b` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added direct test coverage for the progress record's step sequence and clear-on-exit**
- **Found during:** post-Task-2 review, before writing this SUMMARY
- **Issue:** Task 1's tests proved the GET endpoint's shape and no-write property, but nothing directly observed the progress record advancing through its 5 steps in order, or being cleared after a raise partway through the reseed loop — both explicit `<behavior>` requirements of Task 1.
- **Fix:** Two new tests wrap `run_import_justices_csv`/`run_import_convokit` to observe `_get_reset_progress()` from inside each real step (not a replacement, a transparent wrapper), and a second test proves the record clears after a `ResetIncompleteError` raised partway through the reseed loop.
- **Files modified:** `api/tests/test_admin_dev_routes.py`
- **Verification:** `pytest api/tests/test_admin_dev_routes.py -k progress -v` — 2 passed; full file re-run — 28 passed
- **Committed in:** `dd0a48fe1`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical test coverage).
**Impact on plan:** Both auto-fixes necessary for the plan's own stated behavior/`<verify>` requirements to hold together. No scope creep — no new user-facing surface was added beyond what the plan specified.

## Issues Encountered

**Start time not explicitly logged.** The `record_start_time` step's timestamp capture was not run as the very first action of this session (required reading happened first, mirroring the same gap noted in 52-04-SUMMARY.md). `Started`/`duration` above are estimated using the prior plan's own recorded completion timestamp (`2026-09-25T13:41:04Z`) as a floor; `Completed` is a real `date -u` capture taken just before writing this SUMMARY. Does not affect the plan's substantive output.

**The plan's `<verification>` section names "the operator checkpoint in Task 3"** — this plan has only two tasks (Task 1 and Task 2); no Task 3 exists. Read as a boilerplate carry-over referring to Task 2's own embedded `<verify><human-check>` item, which is what actually gets confirmed (deferred to the phase's end-of-phase UAT batch, per `workflow.human_verify_mode`). Not acted on beyond this note — nothing in the plan's actual task list depends on a Task 3.

**The AbortSignal timeout (180s) is not re-measured through the live HTTP path in this plan.** 52-04-SUMMARY.md's own methodology caveat says the 71.67s measurement bypassed HTTP-layer overhead; this plan sizes the signal with a ~2.5x margin above that floor rather than measuring the real endpoint end-to-end, since doing so requires the live dev-stack run that Task 2's `<human-check>` performs. If that UAT run reveals the real HTTP-path duration is closer to the 180s ceiling than expected, the constant is a one-line change in `app/src/routes/admin/+page.server.ts`.

## User Setup Required

None — no new external service configuration required. This plan builds entirely on the corpus files 52-04 already required (already confirmed present in that plan's `user_setup`).

## Next Phase Readiness

- JUSTICE-04's remaining half (D-14/D-15's evidence-based reset UX) is now implemented and automated-verified; the live end-to-end browser confirmation (Task 2's `<human-check>`) is deferred to this phase's end-of-phase UAT batch, consistent with `workflow.human_verify_mode=end-of-phase`.
- No blockers for Plan 52-06 or Phase 54.
- Full test suite: 1402 passed, 5 xfailed, 0 failed (`./.venv/bin/python -m pytest -q`, run twice during this plan — once mid-plan at 1400/5/0, once at close at 1402/5/0, both clean).
- `npm --prefix app run check`: 0 errors, 32 pre-existing warnings (unrelated files, tracked in STATE.md's "Code debt" section). `npm --prefix app run build`: exit 0.
- `node --test --test-concurrency=1 app/tests/*.browser.test.mjs`: 11 passed, 0 failed.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

All key files verified present on disk (`app/src/routes/admin/dev-fixture-state/+server.ts`,
`api/services/admin_dev.py`, `api/schemas/admin_dev.py`, `api/routers/admin_dev.py`,
`app/src/routes/admin/+page.server.ts`, `app/src/routes/admin/+page.svelte`,
`.planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/43-UI-SPEC.md`). All three
commits (`1e53b3b59`, `41e2d5d9b`, `dd0a48fe1`) verified present in `git log`. All acceptance
criteria re-run and passing at each task's own checkpoint (Task 1: 26/26 tests including the
6 new ones, Task 2: `npm run check` 0 errors / `npm run build` exit 0 / all grep-based textual
checks pass). Plan-level `<verification>` re-run: `pytest -q` → 1402 passed, 5 xfailed, 0 failed;
`node --test --test-concurrency=1 app/tests/*.browser.test.mjs` → 11 passed, 0 failed;
`api/tests/test_trust_public_leak_ban.py` → 110 passed.
