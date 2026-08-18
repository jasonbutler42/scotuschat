# Deferred Items — Phase 44 (Resolve Table Rework)

Out-of-scope discoveries found during plan execution, logged per the executor's
scope-boundary rule (only auto-fix issues directly caused by the current task's
changes; pre-existing failures in unrelated files are logged here, not fixed).

## From 44-01 (Descriptor rename)

- **`api/tests/test_phase38_people_ui_contract.py`** — 4 pre-existing test errors
  (`test_personnames_ts_format_cases_match_shared_fixture`,
  `test_personnames_ts_normalization_cases_match_shared_fixture`,
  `test_personnames_ts_invalid_cases_raise_matching_error_codes`,
  `test_personnames_ts_preview_returns_na_until_first_or_last`). The test spawns
  a `node --input-type=module` subprocess and builds a fixture path by string
  concatenation without a path separator (`ROOT` + `"api"` + `"tests"` +
  `"fixtures"` glued with no `os.sep`), producing a mangled path like
  `...projectapi\tests\fixturesperson_name_cases.json` under this WSL/Windows
  environment. Unrelated to Phase 44 — this file is not in 44-01's
  `files_modified` list and was last touched in an earlier phase (Phase 38).
  Confirmed pre-existing by running the file in isolation before and after
  44-01's changes with identical failure output.
  status: resolved
  resolution: "Verified fixed on 2026-08-18: api/tests/test_phase38_people_ui_contract.py is 23 passed / 0 failed with node on PATH. The mangled C:\workspace path came from the pre-relocation Windows checkout; the WSL relocation resolved it. Backlog 999.10 closed in the same audit. Caveat recorded there: these 4 tests silently SKIP when node is absent from PATH. See .planning/notes/2026-08-18-uat-audit-closure.md"

- **Full-suite invocation quirk (not a code defect):** running
  `./.venv/Scripts/python.exe -m pytest api/tests -q` directly (the plan's
  literal `<verification>` item 3 command) does not trigger
  `tests/conftest.py`'s `load_dotenv()` / `TEST_DATABASE_URL` redirect, because
  `tests/` is a sibling directory, not an ancestor, of the paths passed. This
  leaves `DATABASE_URL` pointed at whatever the raw environment already has
  (the real dev DB), and unrelated tests that assume a clean `scotus_test` DB
  (`test_admin_dev_routes.py`, `test_speakers_service.py`) then collide with
  pre-existing dev-DB rows (e.g. `UniqueViolationError` on `roles.name`).
  Running `pytest tests/conftest.py api/tests -q` (forcing the redirect to
  load first) produces 542 passed / 0 failed, confirming zero regressions
  from 44-01's changes. Recommend running the suite as
  `pytest tests/conftest.py api/tests -q` (or via the project's normal test
  runner script, if one exists) rather than `pytest api/tests -q` alone, in
  any phase's `<verification>` block going forward — flagging here rather
  than editing the plan's already-written verification text.
  status: resolved
  resolution: "Superseded by Phase 46: conftest.py now lives at the pytest rootdir, so the TEST_DATABASE_URL redirect fires for every invocation shape including 'pytest api/tests -q'. Locked in by tests/test_pytest_isolation_invocation_shapes.py. See .planning/notes/2026-08-18-uat-audit-closure.md"
