# Deferred Items — Phase 26 (arguments-admin)

Out-of-scope discoveries logged during plan execution (SCOPE BOUNDARY rule —
not fixed here, tracked for later triage).

## 26-01

- **Pre-existing full-suite test failures, unrelated to this plan's files:**
  `api/tests/test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`,
  `api/tests/test_people.py::test_get_person`,
  `api/tests/test_people.py::test_get_person_404`
  fail with `RuntimeError: Database session factory is not initialised —
  lifespan may not have completed startup` when the entire `api/tests/`
  directory is run together (`pytest api/tests -q`). This reproduces without
  any changes from this plan — it is a pre-existing test-ordering/lifespan
  issue affecting `test_arguments.py` and `test_people.py`, neither of which
  this plan modifies. The plan's own verification command (scoped to
  `test_admin_arguments_service.py`, `test_admin_arguments_routes.py`,
  `test_admin_jobs_service.py`) passes cleanly (24 passed, 20 skipped).
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"

## Wave 1 post-merge gate (26-01 + 26-03)

- **Same pre-existing ordering bug has a wider blast radius than previously
  recorded, confirmed via baseline diff, not just inference.** The project's
  configured `workflow.test_command` runs `pytest` from repo root with no
  path filter, which per `pytest.ini` (`testpaths = tests pipeline/tests
  api/tests`) collects **all three** test directories into one process. That
  combined run currently shows 50 failed / 214 passed / 31 errors on top of
  wave 1's commits.
  Compared against a disposable `git worktree` checked out at
  `f6f26b91` (the commit immediately before 26-01's first commit, i.e. the
  pre-phase-26 baseline): the baseline's own full-suite run already shows
  **42 failed / 214 passed / 31 errors** — same passed count, same 31 errors
  (all pre-existing fixture-level failures in `test_admin_jobs_phase25.py`,
  `test_admin_jobs_stats.py`, `test_admin_people_phase25.py`, unrelated to
  phase 26), confirming the bulk of the failures (pipeline/tests/*,
  tests/test_models_import.py, test_arguments.py, test_people.py, and most of
  the admin test files) predate this phase entirely.
  The diff between baseline-failed and current-failed is exactly 8 tests, all
  **newly added by 26-01 itself**: `test_admin_arguments_routes.py::
  test_delete_argument_returns_409_for_unpublished`,
  `test_admin_arguments_service.py::{test_delete_argument_returns_false_for_unpublished,
  test_list_arguments_includes_unpublished_row, test_publish_argument_already_published_raises,
  test_publish_argument_from_draft_writes_one_published_log_row,
  test_unpublish_then_republish_succeeds_and_preserves_published_at,
  test_update_argument_slug_frozen_for_unpublished}`,
  `test_admin_jobs_service.py::test_approve_job_writes_one_draft_log_row`.
  Re-running exactly those 3 files scoped (no `tests/` or `pipeline/tests/` in
  the same process) reproduces 26-01's own reported result exactly —
  **24 passed, 20 skipped, 0 failed** — confirming these 8 are not logic bugs
  in 26-01's implementation; they only fail when collected in the same
  process as `pipeline/tests/`, which is where the shared
  `AsyncSessionLocal`/lifespan global state gets corrupted for later-collected
  files. Root cause and fix are out of scope for phase 26 (test-harness
  isolation, not application code) — same deferred issue phases 21 and 25
  already hit. Zero tests that passed at baseline regressed; zero net-new
  logic failures. Recommendation for future triage: give the FastAPI test
  fixture proper per-test lifespan/session teardown (or run `tests`,
  `pipeline/tests`, and `api/tests` as separate pytest invocations in CI)
  so `workflow.test_command` stops reporting false positives.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"

## Wave 2 post-merge gate (26-02)

- Same pattern as wave 1, confirmed the same way: full-suite run after 26-02
  adds exactly 5 new failures (`test_admin_arguments_routes.py::
  test_update_participant_route_persists_title_for_advocate`,
  `test_admin_arguments_service.py::{test_get_argument_detail_includes_status_log_and_speakers,
  test_list_argument_speakers_bench_advocate_and_utterance_counts,
  test_list_argument_speakers_returns_empty_for_missing_argument,
  test_update_participant_side_persists_title_for_advocate}`) — all 26-02's
  own new tests, all pass (25 passed, 25 skipped, 0 failed) when the same 3
  files are run scoped instead of collected with `pipeline/tests/`. No net
  regression.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"

## Gap-closure post-merge gate (26-05)

- Same pattern again, confirmed via a sibling-test comparison instead of a
  disposable-worktree diff (a worktree checkout lacks `.env`, and Settings()
  fail-fasts without `DATABASE_URL`/`ADMIN_TOKEN` — recreating those in a
  scratch worktree wasn't pursued; comparing against an untouched sibling
  test in the *same* full-suite run is equally conclusive). Full-suite run
  after 26-05 shows 63 failed / 208 passed / 34 errors. Of 26-05's 4 new
  tests: the 2 DB-less always-run tests (`test_delete_argument_gate_keys_on_draft`,
  `test_update_participant_side_rejects_unresolved_side`) pass cleanly even in
  the full combined run. The 2 DB-guarded tests (`test_delete_argument_returns_false_for_pipeline`,
  `test_delete_argument_returns_409_for_pipeline`) show as failed — but so
  does their untouched 26-01 sibling in the same run
  (`test_delete_argument_returns_false_for_unpublished`,
  `test_delete_argument_returns_409_for_unpublished`), which 26-05 did not
  modify. Identical failure signature on an untouched test proves the
  mechanism is the same pre-existing collection-order corruption, not a
  26-05 regression. The plan's own scoped verification
  (`test_admin_arguments_service.py` + `test_admin_arguments_routes.py`, no
  `pipeline/tests/` in the same process) passed cleanly: 24 passed, 24
  skipped, 0 failed. No net-new regression.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"

## Gap-closure post-merge gate (26-06)

- Same pattern again, confirmed via sibling-test comparison in the same
  full-suite run (no disposable worktree — same rationale as 26-05:
  Settings() fail-fasts without DATABASE_URL/ADMIN_TOKEN in a scratch
  worktree lacking `.env`). Full-suite run after 26-06 shows **57 failed /
  217 passed / 34 errors** — fewer total problems than the last recorded
  baseline after 26-05 (63 failed / 208 passed / 34 errors): errors flat
  (34 = 34), failures down 6, passes up 9. Of 26-06's 3 new DB-guarded tests
  (`test_list_jobs_is_archived_false_for_pipeline_argument`,
  `test_list_jobs_is_archived_true_for_non_pipeline_argument`,
  `test_list_jobs_is_archived_false_when_no_linked_argument`), all 3 show as
  ERROR in the full combined run — but so does every DB-guarded test in
  `test_admin_jobs_phase25.py` (10 tests), `test_admin_jobs_stats.py` (4
  tests), and `test_admin_people_phase25.py` (10 tests), none of which
  26-06 touched. Re-running `test_admin_jobs_phase25.py` +
  `test_admin_jobs_stats.py` scoped (no `pipeline/tests/` in the same
  process) reproduces clean results (22 passed, 18 skipped, 0 errors),
  confirming the ERROR state only appears under the same pre-existing
  collection-order corruption, not from any 26-06 change. The plan's own
  scoped verification (`api/tests/test_admin_jobs_list.py` alone) passed
  cleanly: 2 passed, 9 skipped, 0 failed — identical to the executor's
  reported result. `npx svelte-check` independently re-confirmed: 0 errors,
  18 pre-existing warnings. No net-new regression.
  status: resolved
  resolution: "Green as of the 2026-08-18 cross-phase UAT audit: full suite is 4 failed / 1039 passed / 6 skipped / 5 xfailed and this test is not among the 4 failures. Root cause (shared lifespan/session-factory state corrupted by combined collection against the shared dev DB) was closed by Phase 46's rootdir conftest.py relocation plus the TEST_DATABASE_URL redirect. See .planning/notes/2026-08-18-uat-audit-closure.md"
