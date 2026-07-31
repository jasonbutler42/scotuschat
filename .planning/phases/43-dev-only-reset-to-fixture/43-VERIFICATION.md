---
phase: 43-dev-only-reset-to-fixture
verified: 2026-07-31T21:57:37Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 43: Dev-Only Reset to Fixture Verification Report

**Phase Goal:** The operator can return a local database to a known four-fixture state from the
admin panel in a single action, making the corpus and resolve work iterable instead of requiring
hand-built SQL cleanup between attempts. The action is fully destructive by design — it wipes
every argument, utterance, person, court tenure, and argument participant, then reseeds exactly
Phase 41's four-fixture set plus their associated people — so an environment gate that makes it
impossible to fire against a real/production database is a hard requirement of the feature, not
follow-up polish. Reseeding runs through the same `import-convokit` path a normal corpus import
uses, so Phase 42's importer fixes flow through automatically rather than being duplicated in a
hand-rolled seeder.

**Verified:** 2026-07-31T21:57:37Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Reset produces exactly the 4 fixture arguments + their people, zero others | VERIFIED | `api/services/admin_dev.py::TRUNCATE_SQL` (9 named tables + CASCADE, `roles` excluded) confirmed by direct source read; `api/tests/test_admin_dev_routes.py::test_reset_wipes_and_reseeds_fixtures` passes live (re-ran: 18/18 tests pass); 43-04-SUMMARY.md Task 1 records the live dev-DB run producing `arguments=4` (oyez_transcript_id 15169/13015/18897/22372), `roles` row count unchanged, throwaway pre-reset rows gone |
| 2 | Production-like setting refuses, demonstrated by actually attempting it | VERIFIED | `api/main.py`'s conditional `include_router` (read directly, matches claim) + `tests/test_admin_dev_router_gate.py` (5 tests, incl. near-miss allow-list cases) pass live; 43-04-SUMMARY.md Task 2 records the operator/orchestrator actually running `curl` against a `production`-configured stack (404, not 403/200), diffing `openapi.json`, and confirming "Dev Tools"/"DEV ONLY" absent from `/admin`'s served HTML source — this is a `checkpoint:human-verify gate="blocking"` plan task (43-04-PLAN.md Task 2), not an inference from source |
| 3 | Explicit operator confirmation states exactly what will be wiped before deletion | VERIFIED | `app/src/routes/admin/+page.svelte` lines 387-461 (read directly): Confirming state renders the full wipe-scope statement ("every argument, utterance, person, court tenure, and participant record — not just the fixtures. It cannot be undone.") before the only submitting control (`Confirm reset`); Idle button is `type="button"`, never submits; 43-04-SUMMARY.md Task 1 steps 7-11 record the operator clicking Reset to Fixture, reading the confirmation text, clicking Cancel, and confirming zero row-count change |
| 4 | Each fixture immediately usable in resolve→approve→publish; state-variety fixtures land in distinct states | VERIFIED | `api/services/admin_dev.py`'s state-realization block (read directly) drives 13015→DRAFT via `approve_job`, 18897→DRAFT→PUBLISHED via `approve_job` then `publish_argument`, 22372's AdminJob→RUNNING; `test_reset_realizes_state_variety` + `test_reset_writes_status_log_rows` pass live; 43-04-SUMMARY.md Task 1 steps 22-27 record the operator observing all four distinct state combinations live, all four jobs non-null, and the complexity fixture's Resolve card editable |
| 5 | Reset after Phase 42's fixes lands corrected field values on the complexity fixture | VERIFIED | 43-04-SUMMARY.md Task 1 step 24 records the operator running the real reset against the real 900MB corpus and observing 480 utterances, exactly 1 non-null `section_hint`, and 17 `argument_participants` on conversation 15169 — these three numbers independently cross-check against `.planning/STATE.md` lines 119-120's Phase 42 Plan 05 baseline (480 utterances, section_hint 1/480, 17-row ArgumentParticipant roster), confirming the reseed used the fixed importer rather than a stale copy |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/core/config.py` | `Settings.environment: str`, no default | VERIFIED | Read directly; field present immediately after `admin_token`, no default, matches D-02 |
| `api/schemas/admin_dev.py` | `ResetFixtureItem`, `ResetToFixtureResponse` | VERIFIED | Read directly; both models present with the documented 6-field shape |
| `api/services/admin_dev.py` | `FIXTURE_SET` (4 entries), `TRUNCATE_SQL`, `reset_to_fixture`, `CorpusUnavailableError`, `ResetIncompleteError` | VERIFIED | Read directly; all present, `FIXTURE_SET` has exactly 4 entries in declaration order (15169/13015/18897/22372), state-realization block present and matches plan |
| `api/routers/admin_dev.py` | separate conditionally-mounted `APIRouter` | VERIFIED | Read directly; separate router, `verify_admin_token` imported (not redefined), maps `CorpusUnavailableError`→503, `ResetIncompleteError`→500 |
| `api/main.py` | conditional `app.include_router(admin_dev_router.router)` | VERIFIED | Read directly; guarded on `settings.environment == "development"`, 4 pre-existing includes unconditional and unchanged |
| `app/src/routes/admin/+page.server.ts` | `isDevelopment`, `actions.resetToFixture` | VERIFIED | Read directly; `isDevelopment` derived via `$env/dynamic/private` (not static, per D-07), `resetToFixture` action present, maps failures to exactly the two locked error copies |
| `app/src/routes/admin/+page.svelte` | Dev Tools section, 5 states | VERIFIED | Read directly; section gated entirely inside `{#if data.isDevelopment}`, all 5 states (Idle/Confirming/Running/Success/Error) present and match UI-SPEC styling/copy |
| `api/tests/test_admin_dev_routes.py` | 9 tests | VERIFIED | 9 test functions confirmed via `--collect-only`; all pass live |
| `tests/test_admin_dev_router_gate.py` | route-absence/presence tests | VERIFIED | 3 functions (5 parametrized items) confirmed; all pass live |
| `tests/test_admin_dev_frontend_gate.py` | source-invariant gate guard | VERIFIED | 4 test functions confirmed; all pass live |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/main.py` | `admin_dev_router.router` | `settings.environment == "development"` conditional include | WIRED | Confirmed by direct source read and by `tests/test_admin_dev_router_gate.py` passing live |
| `api/services/admin_dev.py` | `pipeline.commands.import_convokit.run_import_convokit` | in-process call, real importer | WIRED | Confirmed by direct source read (module-level import, called in the reseed loop) — same path Phase 42's fixes landed on |
| `api/services/admin_dev.py` | `api/services/admin_jobs.py::approve_job` / `api/services/admin_arguments.py::publish_argument` | state-realization block | WIRED | Confirmed by direct source read; ordering (`approve_job` before `publish_argument` for 18897) preserved with an explanatory comment |
| `app/src/routes/admin/+page.server.ts` | `POST /api/admin/dev/reset-to-fixture` | `actions.resetToFixture`'s `fetch` call with `X-Admin-Token` | WIRED | Confirmed by direct source read |
| `app/src/routes/admin/+page.svelte` | `actions.resetToFixture` | `<form method="POST" action="?/resetToFixture">` + `use:enhance` | WIRED | Confirmed by direct source read; `invalidateAll()` called in the success branch |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 43's 3 new/extended test files pass | `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py tests/test_admin_dev_router_gate.py tests/test_admin_dev_frontend_gate.py -q` | `18 passed in 12.67s` | PASS |
| Full backend suite has no regressions | `./.venv/Scripts/python.exe -m pytest -q` | `841 passed, 5 xfailed, 4 errors` (the 4 errors are the pre-existing, git-stash-confirmed-unrelated Node path-join bug in `test_phase38_people_ui_contract.py`, logged in `deferred-items.md`) | PASS |
| Frontend type/lint check clean | `cd app && npm run check` | `804 FILES 0 ERRORS 36 WARNINGS` (36 warnings identical baseline before/after, per 43-03-SUMMARY.md) | PASS |
| `api/routers/admin.py` untouched by this phase | `git log --oneline -- api/routers/admin.py` | last touch Phase 38, none since | PASS |
| All 8 phase commit hashes present | `git log --oneline --all \| grep -E "dde83642\|bd107923\|e26b81b3\|aa98872f\|85d404b3\|6c533cc3\|6465b893\|7832865d"` | all 8 found | PASS |

### Live Human-Verify Checkpoints (43-04, gate="blocking")

Plan 43-04 (`files_modified: [], autonomous: false`) is itself the phase's human-verification
mechanism, per ROADMAP success criteria 2/5's explicit requirement that the refusal and the
Phase-42-fix propagation be "demonstrated by actually attempting it, not asserted from the code."
Both of its tasks are `type="checkpoint:human-verify" gate="blocking"` and have already run to
completion with specific, falsifiable observed values recorded in 43-04-SUMMARY.md (exact row
counts, exact status codes, an `openapi.json` diff, a `ValidationError` traceback for the
unset-value case) rather than a vague "looks good." These values cross-check against
independently-recorded data in `.planning/STATE.md` (Phase 42's fixture counts) and against the
source code read directly in this verification pass. No further human action is required for
this phase's own success criteria.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DEVTOOL-01 | 43-01, 43-02, 43-03, 43-04 | Reset to Fixture wipes and reseeds all 4 fixtures + people from the admin panel | SATISFIED | Backend (43-01/02) + frontend trigger (43-03) + live proof (43-04); REQUIREMENTS.md marks it Complete, consistent with the evidence above |
| DEVTOOL-02 | 43-01, 43-03, 43-04 | Hard-gated so it cannot execute against a real/production environment | SATISFIED | Router-level conditional mount (backend) + `$env/dynamic/private`-gated section (frontend), both proven absent/404 live in 43-04 including an unset-value and a capitalization near-miss; REQUIREMENTS.md marks it Complete |

No orphaned requirements — `grep -E "Phase 43" .planning/REQUIREMENTS.md` shows only DEVTOOL-01/02, both of which appear in every plan's `requirements` frontmatter for this phase.

### Anti-Patterns Found

No blocking anti-patterns (no unresolved `TBD`/`FIXME`/`XXX` markers with no follow-up reference,
no stub returns, no hardcoded-empty-data-that-renders found in the files this phase modified).

The independent code review (`43-REVIEW.md`, `depth: standard`) found 0 critical, 6 warning, 2
info findings — per this task's instructions, this review's findings are advisory and
non-blocking under this project's config. Noted for completeness, not treated as gaps:

| File | Finding | Severity | Impact |
|------|---------|----------|--------|
| `api/services/admin_dev.py:197-200`, `api/routers/admin_dev.py:48-51` | Raw exception `repr()` returned verbatim in the 500 response body (WR-01) | Warning | Internal-detail leak, reachable only with a valid admin token in a dev-gated environment |
| `api/services/admin_dev.py:138,147` | `CorpusUnavailableError` embeds the raw server filesystem path in the 503 detail (WR-02) | Warning | Same exposure class as WR-01 |
| `api/services/admin_dev.py:249-260` | State-realization `approve_job`/`publish_argument` calls are not wrapped the way the reseed loop is, so a plain `ValueError` from either escapes as a generic 500 instead of the module's own `ResetIncompleteError` contract (WR-03) | Warning | Consistency gap in the failure contract, most likely on re-entry after a partial run |
| `api/services/admin_dev.py` (whole function) | No guard against two overlapping `reset-to-fixture` invocations (WR-04) | Warning | Two concurrent calls could interleave `TRUNCATE`/reseed and produce an inconsistent state or lock wait |
| `app/src/routes/admin/+page.server.ts:245-251` | A `401` (e.g. admin-token drift) is mapped to the same "database may be inconsistent" copy as a genuine mid-reset failure (WR-05) | Warning | Misleading operator guidance on an auth failure that never touched the DB |
| `api/tests/test_admin_dev_routes.py:290-298` | `test_reset_requires_admin_token` calls `_require_test_db()` even though it never touches the DB, so it's silently skipped without `TEST_DATABASE_URL` set (WR-06) | Warning | Reduces auth-gate regression coverage in some environments |
| `app/src/routes/admin/+page.svelte:424,443` | Dead `disabled={resetRunning}` in the mutually-exclusive Confirming branch (IN-01) | Info | Harmless |
| `api/services/admin_dev.py:314` | Unreachable `else ""` fallback for `admin_job_status` (IN-02) | Info | Harmless |

### Human Verification Required

None. Plan 43-04's own blocking human-verify checkpoints already satisfy every roadmap success
criterion that requires live observation (SC-1, SC-2, SC-3, SC-4, SC-5), with specific recorded
evidence cross-checked against independent prior-phase data and against the source code read
directly in this pass.

### Gaps Summary

None. All 5 roadmap success criteria are VERIFIED. Both requirement IDs (DEVTOOL-01, DEVTOOL-02)
are SATISFIED and correctly marked Complete in REQUIREMENTS.md. All 18 phase-specific automated
tests pass live, the full backend suite (841 passed / 5 xfailed / 4 pre-existing-and-unrelated
errors) shows no regressions, and the frontend type-check is clean (0 errors). The independent
code review's 6 warnings and 2 info findings are real, worth a future follow-up (particularly
WR-01/WR-02's internal-detail leaks and WR-03's inconsistent failure contract on the
state-realization block), but none of them block this phase's stated goal or any of its 5
success criteria, and they are explicitly non-blocking per this project's review-depth
configuration.

---

_Verified: 2026-07-31T21:57:37Z_
_Verifier: Claude (gsd-verifier)_
