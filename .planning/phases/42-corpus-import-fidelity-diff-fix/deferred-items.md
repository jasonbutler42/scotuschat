# Phase 42 — Deferred (Out-of-Scope) Items

Issues discovered during plan execution that are pre-existing and unrelated
to the current task's changes. Not fixed here per the executor's scope
boundary rule.

## 42-02: Node.js path-mangling failure in api/tests (WSL environment)

**Found during:** 42-02 Task 2, running the full suite (`./.venv/Scripts/python.exe -m pytest -q`)
as a sanity check beyond the plan's required `pipeline/tests/ -q` gate.

**Symptom:** 4 errors in `api/tests/test_phase38_people_ui_contract.py`
(`test_personnames_ts_*`) — each spawns a Node.js subprocess that fails with
`ENOENT` on a mangled path:
`C:\workspace\scotuschat\project\workspacescotuschatprojectapi\tests\fixtures...`
(the WSL-mounted path and the Windows path appear to have been concatenated
instead of joined).

**Why out of scope:** Unrelated to `scripts/delete_fixture_argument.py` or
`pipeline/tests/test_delete_fixture_argument.py` (this plan's only files).
`pipeline/tests/ -q` — the plan's actual verification gate — is fully green
(207 passed, 5 xfailed). This is a pre-existing WSL/Windows path-construction
issue in an unrelated Node.js-backed contract test, not something either of
this plan's two tasks touched.

**Action:** Not fixed. Flagged here for a future phase/session that owns
`api/tests/test_phase38_people_ui_contract.py` or the WSL/Windows dev split.
