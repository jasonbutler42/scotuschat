# Phase 31: Audit stale DB-gated test fixtures + fix real data leakage - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the root cause of real data leakage into the shared dev Postgres DB during pytest runs (production service functions — `create_person_for_job`, `publish_argument`, `run_import_convokit` — commit internally, surviving the test fixture's `rollback()`), get the ~28 stale DB-gated test fixtures passing against the current schema, clean up the leaked rows already sitting in the dev DB, and add a self-enforcing check that proves the full suite never leaves new rows behind. This is a data-integrity bug fix and test-infra hardening phase — no new user-facing capability.

</domain>

<decisions>
## Implementation Decisions

### Isolation Mechanism
- **D-01:** Use a **dedicated test database** (`scotus_test`, same local native Postgres install — no Docker) rather than savepoint-based nested transactions or snapshot/restore. `pipeline/tests/conftest.py`'s `test_db_url` fixture already prefers `TEST_DATABASE_URL` over `DATABASE_URL` — this decision means actually setting `TEST_DATABASE_URL` in `.env` and pointing `api/tests/` at it too.
- **D-02:** The test DB **auto-resets every pytest session** — a session-scoped fixture TRUNCATEs all tables (reuse the existing `clean_db` fixture's table list from `pipeline/tests/conftest.py`) before tests run against `TEST_DATABASE_URL`. No manual reset step required.
- **D-03:** Provisioning is **scripted**, not just documented — add a script that runs `CREATE DATABASE scotus_test` + `alembic upgrade head` against it. (Exact location — `scripts/` vs. a Makefile target vs. a pipeline maintenance command — is planner's call; keep it consistent with D-08's `scripts/` placement below.)

### Existing Leaked-Row Cleanup
- **D-04:** Write a **one-time reviewed cleanup script** — dry-run by default, prints what it would delete, requires explicit confirmation/flag to actually delete. Not a manual ad-hoc DELETE, and not deferred out of scope: the leak is confirmed *currently active* (see Specific Ideas below).
- **D-05:** Cleanup does a **broad sweep**, not just the 5 known duplicates: also check `Person` for any other `full_name` duplicates, and `Argument` rows matching test-fixture patterns (synthetic case_names/dockets, or arguments with no linked utterances/pipeline_run — orphaned test artifacts).
- **D-06:** For duplicate `Person` rows, the canonical row to keep is the one with real tenure/bio data (typically the earliest id) — verify before deleting, don't just keep-lowest-id blindly.
- **D-07:** This is a **standalone script**, not a `pipeline/` CLI subcommand — it's one-time remediation, not an ongoing pipeline step. Despite the "pipeline is offline-CLI-only, never an API endpoint" project rule, this doesn't need to live inside the `pipeline` package; a `scripts/` file run directly with `python` is fine and keeps it clearly separate from the recurring ingest/parse/resolve/import commands.
- **D-08:** Cleanup script location: `scripts/cleanup_leaked_test_rows.py` (or equivalent name under `scripts/`).

### db_session Fixture Consolidation
- **D-09:** **Consolidate** the identically-copy-pasted `db_session` fixture (currently duplicated verbatim across 7 files: `test_admin_dashboard_stats.py`, `test_admin_jobs_source.py`, `test_admin_jobs_stats.py`, `test_admin_jobs_list.py`, `test_argument_oyez_field.py`, `test_admin_people_phase25.py`, `test_admin_jobs_phase25.py`) into a single fixture in `api/tests/conftest.py` (which already holds `_api_lifespan`). Delete all 7 local copies.
- **D-10:** Keep `api/tests/db_session` and `pipeline/tests/async_session` as **two separate fixtures** — do not force a unified name/shared module across the two test suites. Different layers (API vs. pipeline), and unifying would touch every call site in both suites for a phase whose goal is fixing leaks, not renaming.

### Row-Count Verification Mechanism
- **D-11:** Implement success criterion 1 ("before/after row-count check") as an **automated pytest session hook** (`pytest_sessionstart` / `pytest_sessionfinish` in root `tests/conftest.py`), not a standalone manual script. It snapshots `Person`/`Argument` counts against the real `DATABASE_URL` (the shared dev DB) before the session and asserts they're unchanged after — self-enforcing on every future full-suite run.
- **D-12:** The hook checks **`Person` and `Argument` counts only** — matches the success criterion exactly and the tables confirmed leaked in the actual incident. Do not expand to the full `clean_db` table list; keep the failure message unambiguous.
- **D-13:** If `DATABASE_URL` is not configured in the environment, the hook **skips silently** — consistent with how DB-gated tests already no-op via `pytest.skip()` when unconfigured.

### Claude's Discretion
- Exact naming/location details noted as planner's call in D-03 and D-08 above (script filenames, whether provisioning is a Makefile target or plain script).
- Whether the cleanup script (D-04–D-08) runs as a prerequisite step before the isolation-mechanism plan work, or after — sequencing is a planning concern, not a discussion decision. The leak is confirmed currently active, so cleanup must land in this phase regardless of order.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 31 section ("Audit ~28 stale DB-gated test fixtures + fix real data leakage into shared dev DB") — goal text, success criteria, requirement mapping
- `.planning/REQUIREMENTS.md` — TEST-01, TEST-02 (lines 12–13, 76–77)

### Prior investigation of this exact bug
- `.planning/RETROSPECTIVE.md` (line 249) — flags this precise tradeoff (dedicated test DB vs. fixture-level fix) as an open systemic risk from v1.5
- CLAUDE.md — hard constraints: Alembic is the sole DDL authority (no `Base.metadata.create_all`); `asyncpg` requires `statement_cache_size=0` behind PgBouncer; pipeline is offline-CLI-only, never an HTTP endpoint

### Existing test infrastructure to build on
- `pipeline/tests/conftest.py` — `test_db_url` fixture already resolves `TEST_DATABASE_URL` before `DATABASE_URL`; `clean_db` fixture has the full TRUNCATE table list to reuse for D-02
- `api/tests/conftest.py` — `_api_lifespan` autouse fixture; add the consolidated `db_session` fixture here (D-09)
- `tests/conftest.py` — root-level `load_dotenv()`; add the session hook here (D-11)
- `pytest.ini` — `testpaths = tests pipeline/tests api/tests`

### Production functions confirmed to commit internally (leak source)
- `api/services/admin_jobs.py::create_person_for_job` (line ~856)
- `api/services/admin_arguments.py::publish_argument` (line ~557, `await db.commit()` at line 555 area)
- `pipeline/commands/import_convokit.py::run_import_convokit` (line ~949)

### The 7 files with duplicated db_session fixture (D-09)
- `api/tests/test_admin_dashboard_stats.py`
- `api/tests/test_admin_jobs_source.py`
- `api/tests/test_admin_jobs_stats.py`
- `api/tests/test_admin_jobs_list.py`
- `api/tests/test_argument_oyez_field.py`
- `api/tests/test_admin_people_phase25.py`
- `api/tests/test_admin_jobs_phase25.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/tests/conftest.py::clean_db` — existing TRUNCATE-all-tables fixture with correct FK/CASCADE ordering; reuse its table list for the D-02 auto-reset fixture
- `api/tests/conftest.py::_api_lifespan` — existing pattern for an autouse fixture that imports `lifespan`/`app` locally (not at module level) to avoid the module-reset split described in its own docstring; the new consolidated `db_session` fixture should follow the same local-import discipline if it touches `api.core.database`

### Established Patterns
- `db_session` fixture pattern today: `async with AsyncSessionLocal() as session: async with session.begin(): yield session; await session.rollback()` — this is the exact pattern that fails to protect against inner `db.commit()` calls; D-01/D-09 replace its target DB, not necessarily its shape
- Dependency override pattern for FastAPI tests: `app.dependency_overrides[get_db] = _override_get_db` / `app.dependency_overrides.pop(get_db, None)` in a try/finally — used throughout `api/tests/test_admin_people_phase25.py` and similar files; the consolidated fixture should remain compatible with this override pattern

### Integration Points
- `.env` needs a new `TEST_DATABASE_URL` entry (D-01) — do not touch `.env` directly during discuss-phase; planner/executor handles this
- Alembic migrations must be run against `scotus_test` once it exists (D-03) — the sole-DDL-authority CLAUDE.md rule applies to the test DB too, not just dev/prod

</code_context>

<specifics>
## Specific Ideas

**Confirmed live during this discussion (2026-07-13):** a direct `psql` query against the dev DB (`people` table) shows 5 duplicate "Ketanji Brown Jackson" rows still present — ids 116, 959, 1097, 1204, 1285, all `is_justice = true`. This is not a hypothetical risk from the prior incident; it is current, unresolved state that D-04–D-08 must clean up. Total row counts at time of check: 352 people, 211 arguments (baseline for planner/executor to compare cleanup script output against).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. The one todo match surfaced by cross-referencing (`2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md`, UI-scoped, low match score) was reviewed but not folded — it does not belong in a DB test-infra phase.

### Reviewed Todos (not folded)
- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` — an authenticated "Edit" affordance on utterances/speaker popover (UI area). Score 0.5, keyword match on "arguments" only. Out of scope for Phase 31; remains unassigned for a future UI phase.

</deferred>

---

*Phase: 31-audit-stale-db-gated-test-fixtures*
*Context gathered: 2026-07-13*
