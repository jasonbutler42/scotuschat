# Phase 46 — Deferred Items (out-of-scope discoveries)

Logged per the executor's SCOPE BOUNDARY rule: issues discovered during
execution that are NOT caused by this phase's own changes are recorded here,
not fixed inline.

## Found during 46-03 Task 3 (bare `pytest -q` full-suite run, 2026-08-13)

This is the first time `pytest -q` has been run to completion against a
reachable dev/test Postgres in this environment (D-02 cutover). It surfaced
5 pre-existing failures, all in files unrelated to Phase 46 and predating it:

1. **`tests/test_schema.py::test_no_create_all_in_codebase`** (file authored
   2026-07-02, Phase 22) — its filesystem scanner walks `api/`, `alembic/`,
   `pipeline/` recursively via `rglob("*.py")`, which also sweeps `api/tests/`.
   It flags `api/tests/test_phase44_descriptor_rename.py` (authored
   2026-08-01, Phase 44) because that test file's OWN assertion text contains
   the literal substring `Base.metadata.create_all` (checking that string's
   *absence* in a migration file) — a false positive, not an actual DDL call.
   No production code violates the Alembic-sole-DDL-authority constraint;
   `grep -rn 'Base\.metadata\.create_all(' --include='*.py' api pipeline scripts tests alembic conftest.py`
   confirms zero actual invocations exist anywhere in the repo.

2. **`api/tests/test_phase44_argument_role_roundtrip.py::test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum`**
   (4 parametrized cases: UNKNOWN/PETITIONER/RESPONDENT/AMICUS, file authored
   2026-08-10, Phase 44 Plan 09) — `isinstance(body.side, SideEnum)` is
   `False` on a constructed `ResolveRowUpdate`. The equality assertion on the
   same line (`body.side == SideEnum(value)`) is not what fails — only the
   `isinstance` check — suggesting `ResolveRowUpdate.side` is being coerced
   to its plain string value rather than staying a `SideEnum` member
   (possibly a Pydantic v2 `use_enum_values`-style config difference, current
   installed `pydantic==2.13.4`). Needs investigation by whoever owns Phase
   44's resolve-table code; not touched by any 46-01/46-02/46-03 change.
   **Order-dependent:** confirmed this test passes cleanly (9 passed) when
   `api/tests/test_phase44_argument_role_roundtrip.py` is run alone, and also
   passes when the whole `api/tests` directory is run alone (718 passed, 6
   skipped, 0 failed) — it only fails when the bare full-suite `pytest -q`
   collects `tests/`, `pipeline/tests/`, AND `api/tests/` together in one
   session, indicating cross-test-file global-state pollution somewhere in
   the suite (not isolated to this file). A `grep` for
   `use_enum_values`/`model_config` monkeypatching across `tests/`,
   `api/tests/`, `pipeline/tests/` found no obvious source — root cause not
   identified, flagged for whoever picks this up next.

**Why deferred, not fixed here:** both are pre-existing, in files this plan's
tasks never declared as `files_modified`, and unrelated to D-01/D-02/D-03 (the
WSL-to-Windows-Postgres cutover and the pytest DB-isolation fix). Per the
executor's scope-boundary rule, only issues directly caused by the current
task's own changes are auto-fixed; these predate Phase 46 entirely (git log
confirms authorship dates of 2026-07-02 and 2026-08-01/2026-08-10,
respectively, well before Phase 46 started 2026-08-12).

**Row-count impact:** none — both failures are pure assertion failures with
no database writes; the Task 3 row-count regression check (the actual point
of this checkpoint) is unaffected by their presence. See
`46-03-SUMMARY.md`'s row-count table.

**Recommended next step:** a follow-up todo/phase to fix the `test_schema.py`
scanner's search-dir scope (exclude `*/tests/` subdirectories from the
production-source sweep) and to investigate the `SideEnum` coercion behavior
in `api/schemas/admin_jobs.py::ResolveRowUpdate`.
  status: acknowledged
