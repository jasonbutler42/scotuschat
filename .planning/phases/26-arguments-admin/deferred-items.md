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
