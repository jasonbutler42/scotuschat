# Phase 31: Audit Stale DB-Gated Test Fixtures - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 13 (3 conftest.py modified, 7 test files modified, 1 pytest.ini modified, 2 new scripts)
**Analogs found:** 11 / 13 (2 new scripts have no direct analog — see "No Analog Found")

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `api/tests/conftest.py` (add `db_session` fixture) | test-fixture | CRUD (session lifecycle) | `pipeline/tests/conftest.py::async_session` | exact |
| `tests/conftest.py` (add `pytest_sessionstart`/`pytest_sessionfinish`) | test-hook | event-driven | `api/tests/conftest.py::_api_lifespan` (guard pattern) + `pipeline/tests/conftest.py::test_db_url` (skip pattern) | role-match |
| `pipeline/tests/conftest.py` (add session-scoped auto-reset fixture, D-02) | test-fixture | batch (TRUNCATE) | `pipeline/tests/conftest.py::clean_db` (same file, existing fixture) | exact |
| `pytest.ini` (no structural change expected — verify `TEST_DATABASE_URL` doesn't need new markers) | config | — | itself | exact |
| `api/tests/test_admin_dashboard_stats.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` (identical fixture body) | exact |
| `api/tests/test_admin_jobs_source.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` | exact |
| `api/tests/test_admin_jobs_stats.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` | exact |
| `api/tests/test_admin_jobs_list.py` (delete local `db_session`) | test | CRUD | itself (fixture body is the canonical copy to consolidate) | exact |
| `api/tests/test_argument_oyez_field.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` | exact |
| `api/tests/test_admin_people_phase25.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` | exact |
| `api/tests/test_admin_jobs_phase25.py` (delete local `db_session`) | test | CRUD | `api/tests/test_admin_jobs_list.py` | exact |
| `scripts/cleanup_leaked_test_rows.py` (new, D-04–D-08) | utility | batch / dry-run-then-delete | `pipeline/tests/conftest.py::clean_db` (TRUNCATE table/order reference only — not a script analog) | partial (no scripts/ dir precedent exists) |
| DB provisioning script (new, D-03; e.g. `scripts/provision_test_db.py`) | utility | batch (CREATE DATABASE + alembic upgrade) | `pipeline/tests/conftest.py::test_db_url` (URL resolution convention) + Alembic CLI itself | partial (no scripts/ dir precedent exists) |

## Pattern Assignments

### `api/tests/conftest.py` — add consolidated `db_session` fixture (test-fixture, CRUD)

**Analog:** `pipeline/tests/conftest.py::async_session` (session lifecycle) combined with the existing local copy in `api/tests/test_admin_jobs_list.py` (lines 41-54) for the exact body to preserve.

**Existing local copy to consolidate** (`api/tests/test_admin_jobs_list.py` lines 41-54):
```python
@pytest_asyncio.fixture
async def db_session():
    """
    Async DB session seeded for each test, rolled back after.

    Requires DATABASE_URL to be set. Each test gets a fresh transaction
    that is rolled back, so seeded rows do not persist across tests.
    """
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

**Local-import discipline to preserve** (`api/tests/conftest.py` lines 25-44, `_api_lifespan`):
```python
@pytest_asyncio.fixture(autouse=True)
async def _api_lifespan():
    """
    Run FastAPI's lifespan around each api/tests test so AsyncSessionLocal is live.

    Imports lifespan/app locally (not at module level) because
    tests/test_admin_router.py::test_api_main_imports_without_error deletes and
    re-imports every api.* module mid-suite — a module-level import here would
    bind to the pre-reset module object, while fixtures elsewhere that import
    api.main.app inside their own function bodies pick up the post-reset object,
    silently splitting the process into two disconnected module graphs.
    """
    if not _db_configured():
        yield
        return
    from api.core.database import lifespan
    from api.main import app

    async with lifespan(app):
        yield
```

**Guard helper already present in `api/tests/conftest.py` (lines 19-22) — reuse, do not duplicate:**
```python
def _db_configured() -> bool:
    """Same guard every api/tests DB-gated fixture uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```

**Guidance:** The consolidated fixture keeps the exact `AsyncSessionLocal()` + `session.begin()` + `rollback()` shape (per CONTEXT.md D-01/D-09 — shape unchanged, only the target DB changes via `TEST_DATABASE_URL` wiring upstream in `api/core/database.py` / `.env`). Import `AsyncSessionLocal` locally inside the fixture function, matching `_api_lifespan`'s local-import discipline, since it touches `api.core.database`.

---

### `tests/conftest.py` — add `pytest_sessionstart`/`pytest_sessionfinish` hook (test-hook, event-driven)

**Analog A (skip-when-unconfigured convention):** `pipeline/tests/conftest.py::test_db_url` (lines 35-52):
```python
@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not url:
        pytest.skip(
            "No DATABASE_URL configured — skipping DB-dependent tests. "
            "Set TEST_DATABASE_URL or DATABASE_URL in .env to run them."
        )
    return url
```
Note: a `pytest_sessionstart` hook cannot call `pytest.skip()` (no active test context) — per D-13 it must **silently no-op** (log or pass) rather than skip/fail when `DATABASE_URL` is unset. Use the same `_db_configured()`-style boolean guard, not `pytest.skip`.

**Analog B (engine construction convention, mandatory asyncpg flag):** `pipeline/tests/conftest.py::engine` (lines 55-70):
```python
@pytest.fixture(scope="session")
def engine(test_db_url: str):
    return create_async_engine(
        test_db_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
```
Any raw connection/engine the hook opens against `DATABASE_URL` (not `TEST_DATABASE_URL` — D-11 explicitly targets the **real dev DB**) must include `connect_args={"statement_cache_size": 0}` per the CLAUDE.md PgBouncer constraint.

**Existing file to extend** (`tests/conftest.py`, full file, 13 lines):
```python
"""
Root-level pytest conftest.

Loads .env so DATABASE_URL and other env vars are available to all test
modules in the `tests/` directory.
"""

from dotenv import load_dotenv

# Load .env before any tests run.
# Tests that need DATABASE_URL will get it from os.environ after this call.
load_dotenv()
```

**Guidance:** Add module-level `pytest_sessionstart(session)` that queries `SELECT COUNT(*) FROM people` and `SELECT COUNT(*) FROM arguments` against `DATABASE_URL` (sync psycopg2/asyncpg one-shot query is fine — this runs once, not inside async test infra) and stashes counts on `session.config`. Add `pytest_sessionfinish(session, exitstatus)` that re-queries and asserts equality, printing counts on mismatch per D-12 ("unambiguous" failure message). Both hooks must exit silently (no assertion, no error) if `DATABASE_URL` is absent, per D-13.

---

### `pipeline/tests/conftest.py` — add session-scoped auto-reset fixture (D-02) (test-fixture, batch)

**Analog:** the existing `clean_db` fixture in the same file (lines 95-128):
```python
@pytest.fixture()
async def clean_db(async_session: AsyncSession) -> None:
    """
    Truncate all pipeline-relevant tables with CASCADE.

    Opt-in fixture — only add to tests that need a truly empty DB.
    Usage:
        async def test_something(async_session, clean_db):
            ...

    Tables are truncated in dependency order to satisfy FK constraints
    (CASCADE handles the rest).
    """
    from sqlalchemy import text

    await async_session.execute(
        text(
            """
            TRUNCATE TABLE
                utterances,
                pipeline_runs,
                case_arguments,
                case_appearances,
                argument_participants,
                arguments,
                cases,
                court_tenures,
                people,
                roles
            CASCADE
            """
        )
    )
    await async_session.flush()
```

**Guidance:** D-02 wants this table list reused, but converted to `scope="session", autouse=True` (or explicitly wired into `pytest_sessionstart` in root `tests/conftest.py`) so it runs once against `TEST_DATABASE_URL` before the suite, not per-function like the existing opt-in `clean_db`. Keep the identical TRUNCATE table order (already correct for FK/CASCADE per the docstring) — do not re-derive it.

---

### Deleting the 7 duplicated `db_session` fixtures (test, CRUD)

**Canonical body to keep (already shown above)** — verify byte-for-byte identical across all 7 files before deleting; if any file's copy has drifted (e.g., different rollback placement), flag rather than silently picking one.

Files to strip the fixture from (keep all test functions unchanged — they only reference the fixture by name, so removing the local definition and relying on `api/tests/conftest.py`'s version requires no test-body edits):
- `api/tests/test_admin_dashboard_stats.py`
- `api/tests/test_admin_jobs_source.py`
- `api/tests/test_admin_jobs_stats.py`
- `api/tests/test_admin_jobs_list.py`
- `api/tests/test_argument_oyez_field.py`
- `api/tests/test_admin_people_phase25.py`
- `api/tests/test_admin_jobs_phase25.py`

**Dependency-override compatibility to preserve** (pattern used throughout these files, e.g. `api/tests/test_admin_people_phase25.py`):
```python
app.dependency_overrides[get_db] = _override_get_db
try:
    ...
finally:
    app.dependency_overrides.pop(get_db, None)
```
The consolidated fixture must still be usable as a plain `AsyncSession` yield-value compatible with this try/finally override pattern — no signature change needed since the body is preserved verbatim.

---

### Leak-source production functions (service, CRUD) — no signature change, but commit behavior is phase-relevant

These three functions are NOT rewritten to remove `db.commit()` — the isolation fix is the dedicated test DB (D-01), not changing production commit semantics. Listed here so the planner does not accidentally scope a "stop committing internally" refactor:

- `api/services/admin_jobs.py::create_person_for_job` — starts at line 856, commits at line 957 (`await db.commit()`)
- `api/services/admin_arguments.py::publish_argument` — starts at line 557, commits at line 592 (note: CONTEXT.md's line ~555 reference is the *preceding* function's commit; `publish_argument` itself commits at line 592)
- `pipeline/commands/import_convokit.py::run_import_convokit` — starts at line 949

**Guidance:** No code changes to these three functions are implied by this phase. They remain as-is; the fix is environmental (route tests at `scotus_test` instead of the shared dev DB).

---

### `scripts/cleanup_leaked_test_rows.py` (new, utility, batch/dry-run)

No existing `scripts/` directory or script exists in this codebase (confirmed via glob — zero matches). Nearest structural analog is the TRUNCATE table list/ordering convention in `pipeline/tests/conftest.py::clean_db` (for FK-safe ordering awareness, not applicable here since this is a targeted DELETE of specific duplicate rows, not TRUNCATE) and the `Person`/`Argument` models this script will query against (see `api/services/admin_jobs.py`, `api/services/admin_arguments.py` for SQLAlchemy model import conventions).

**Guidance for planner:** Since there is no local `scripts/` convention, follow RESEARCH-free defaults:
- `argparse` with a `--execute` (or `--force`) flag; default behavior is dry-run (print candidate rows) per D-04.
- Reuse `api.core.database.AsyncSessionLocal` (or a fresh `create_async_engine` matching the `connect_args={"statement_cache_size": 0}` convention from `pipeline/tests/conftest.py::engine`) to connect — this must point at `DATABASE_URL` (the shared dev DB), not `TEST_DATABASE_URL`.
- D-05's broad sweep (all `Person.full_name` duplicates, orphaned `Argument` rows) requires a `GROUP BY full_name HAVING COUNT(*) > 1` query plus a LEFT JOIN against `utterances`/`pipeline_runs` to find orphans — no existing query in the codebase does this; write fresh.
- D-06's "keep the row with real tenure/bio data" requires checking each duplicate's `court_tenures` linkage and non-null bio fields before selecting a survivor — do not default to lowest-id.

---

### DB provisioning script (new, D-03, utility, batch)

No existing provisioning script exists. Closest convention is `pipeline/tests/conftest.py::test_db_url`'s env-var resolution order (lines 35-52, shown above) for how `TEST_DATABASE_URL` should be read, and the project's Alembic setup for the `alembic upgrade head` step.

**Guidance for planner:** Locate the project's `alembic.ini` / `alembic/env.py` (not yet inspected in this pass — planner should confirm exact invocation, e.g. whether `alembic upgrade head` needs `-x` params or reads `DATABASE_URL`/`TEST_DATABASE_URL` via `env.py`). Script should: (1) connect to the Postgres server (not a specific DB) and run `CREATE DATABASE scotus_test` if not exists, (2) invoke `alembic upgrade head` with `sqlalchemy.url` pointed at `TEST_DATABASE_URL`. Consistent placement with D-08 means `scripts/provision_test_db.py` (or similar name) alongside `cleanup_leaked_test_rows.py`.

## Shared Patterns

### DB-configured guard (skip/no-op convention)
**Source:** `api/tests/conftest.py` lines 19-22 (`_db_configured`) and `pipeline/tests/conftest.py` lines 46-51 (`test_db_url`'s `pytest.skip` block)
**Apply to:** the new `pytest_sessionstart`/`pytest_sessionfinish` hook (D-13), any new script that touches `DATABASE_URL`
```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```
Note the placeholder-string checks (`"sk-ant" not in url`, exact placeholder match) — these guard against `.env.example` values leaking into CI; replicate them exactly rather than simplifying to `bool(url)`.

### asyncpg/PgBouncer engine flag (CLAUDE.md hard constraint)
**Source:** `pipeline/tests/conftest.py` lines 65-70 (`engine` fixture)
**Apply to:** any new engine/connection created in the sessionstart/sessionfinish hook, the cleanup script, and the provisioning script
```python
create_async_engine(
    db_url,
    connect_args={"statement_cache_size": 0},
    pool_size=2,
    echo=False,
)
```

### Local-import discipline for `api.core.database` / `api.main`
**Source:** `api/tests/conftest.py` lines 25-44 (`_api_lifespan` docstring + body)
**Apply to:** the consolidated `db_session` fixture in `api/tests/conftest.py`
Import `AsyncSessionLocal`, `lifespan`, `app` etc. inside the fixture function body, never at module level — the suite has a test (`tests/test_admin_router.py::test_api_main_imports_without_error`) that deletes/re-imports `api.*` modules mid-run, and module-level imports elsewhere would bind to a stale module object.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/cleanup_leaked_test_rows.py` | utility | batch/dry-run | No `scripts/` directory or script exists anywhere in the repo; write fresh following argparse + AsyncSessionLocal conventions described above |
| DB provisioning script (D-03) | utility | batch | Same — no provisioning script precedent; must be written fresh, consulting `alembic.ini`/`alembic/env.py` (not yet reviewed) for exact upgrade invocation |

## Metadata

**Analog search scope:** `pipeline/tests/`, `api/tests/`, `tests/`, `api/services/`, `pipeline/commands/`, repo root (`pytest.ini`, `scripts/`)
**Files scanned:** `pipeline/tests/conftest.py`, `api/tests/conftest.py`, `tests/conftest.py`, `api/tests/test_admin_jobs_list.py`, `api/tests/test_admin_people_phase25.py` (grep only), `api/services/admin_jobs.py`, `api/services/admin_arguments.py`, `pipeline/commands/import_convokit.py` (grep only), `pytest.ini`, glob of `scripts/*.py` (zero results)
**Pattern extraction date:** 2026-07-13
