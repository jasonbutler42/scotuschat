# Phase 43 — Deferred Items

Pre-existing failures found during execution, out of scope for this plan's tasks
(SCOPE BOUNDARY: only auto-fix issues directly caused by the current task's changes).

## 1. `api/tests/test_phase38_people_ui_contract.py` — Node subprocess path-join bug

**Found during:** Plan 43-01, Task 1 verification (`./.venv/Scripts/python.exe -m pytest -q`).

4 errors:
- `test_personnames_ts_format_cases_match_shared_fixture`
- `test_personnames_ts_normalization_cases_match_shared_fixture`
- `test_personnames_ts_invalid_cases_raise_matching_error_codes`
- `test_personnames_ts_preview_returns_na_until_first_or_last`

**Symptom:** A Node.js subprocess driver invoked by these tests fails with
`ENOENT: no such file or directory, open 'C:\workspace\scotuschat\project\workspacescotuschatprojectapi\tests\fixturesperson_name_cases.json'`
— path segments are concatenated without separators (`project` + `api` + `tests` +
`fixtures` all run together), producing an unresolvable path on Windows/WSL.

**Confirmed pre-existing:** Reproduced identically via `git stash` on `api/core/config.py`
(i.e., with none of this plan's changes applied) — same 4 errors, same path. Not caused
by the `environment` setting added in Task 1.

**Disposition:** Out of scope for Phase 43. Not fixed. Full suite is otherwise green
(823 passed, 5 xfailed) with the new required `environment` field in place — the
Pitfall 5 regression gate this task's acceptance criteria target is satisfied.
