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

## 42-04: Duplicate `roles.name = 'Associate Justice'` UniqueViolation in api/tests

**Found during:** 42-04 Task 3, running `./.venv/Scripts/python.exe -m pytest api/tests -q`
per the plan's own verify block.

**Symptom:** 5 failures, all in `api/tests/test_speakers_service.py`
(`TestGetArgumentSpeakersReasonLeft`, `TestGetArgumentSpeakersWidenedContractShape`):
`sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint
"roles_name_key" DETAIL: Key (name)=(Associate Justice) already exists.` Each failing
test unconditionally does `Role(name="Associate Justice"); db_session.add(role)`,
assuming `db_session`'s per-test rollback (`api/tests/conftest.py`) fully isolates the
insert -- but a `roles` row with that exact name already exists persistently in
whichever database `DATABASE_URL` points to.

**Root cause hypothesis (not confirmed by a fix, since fixing conftest.py is out of
scope here):** `api/tests/conftest.py::db_session` does
`async with session.begin(): yield session; await session.rollback()` -- the explicit
`rollback()` call executes INSIDE the `session.begin()` context manager's block, so
when that `async with` block itself exits normally afterward, its own `__aexit__`
runs its normal commit-on-clean-exit path. If that ordering lets an already-rolled-back
transaction's inserts get committed anyway on a prior test run, a `Role` row created by
one of these tests could have leaked permanently into the real database instead of
being rolled back -- explaining why the FIRST run of these tests years/sessions ago
succeeded (creating the row) and every run since fails on the unique constraint.

**Why out of scope:** None of this plan's two tasks (`pipeline/commands/import_convokit.py`
section_hint derivation + bench-tenure mismatch check, `pipeline/corpus/apolitical.py`
docstring note) touch `api/tests/conftest.py`, `api/core/database.py`, `Role`, or
`test_speakers_service.py` in any way -- confirmed via
`git diff --stat HEAD~1 HEAD -- api/` returning empty for this plan's commits. The
failure reproduces identically on a fresh `api/tests` run with no other tests run first,
and the affected `roles` row's persistence predates this session.
`pipeline/tests/ -q` -- the plan's actual required gate for both Task 2 and Task 3 -- is
fully green (226 passed, 5 pre-existing xfailed).

**Action:** Not fixed. Flagged here for a future phase/session that owns
`api/tests/conftest.py::db_session`'s transaction-rollback ordering, or a one-time
manual cleanup of the stray `roles` row if `DATABASE_URL` is confirmed to point at a
disposable test database rather than the real dev DB.
