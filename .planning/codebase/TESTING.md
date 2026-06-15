# Testing Patterns

**Analysis Date:** 2026-06-15

## Test Framework

**Runner:**
- `pytest` (async mode enabled: `asyncio_mode = auto` in `pytest.ini`)
- Async test support via `pytest-asyncio`

**Config:** `pytest.ini`
```ini
[pytest]
asyncio_mode = auto
testpaths = tests pipeline/tests api/tests
```

**Assertion Library:**
- `pytest` assertions (built-in `assert` statements)
- `httpx.AsyncClient` for API testing (no `requests` library)

**Run Commands:**
```bash
pytest                           # Run all tests in tests/, pipeline/tests/, api/tests/
pytest tests/test_models_import.py  # Run single test file
pytest -x -q                    # Stop on first failure, quiet output (common for pipeline tests)
pytest --asyncio-mode=auto      # Explicitly enable async mode (set in pytest.ini)
pytest -v                       # Verbose output with test names
```

## Test File Organization

**Location:**
- **API tests:** `api/tests/test_*.py` (co-located with source in separate `tests/` subdir)
- **Pipeline tests:** `pipeline/tests/test_*.py` (co-located with source)
- **Root/integration tests:** `tests/test_*.py` (e.g., schema validation, model imports, constraints)

**Naming:**
- Test files: `test_*.py` (e.g., `test_arguments.py`, `test_models_import.py`)
- Test functions: `test_*` (e.g., `test_health()`, `test_get_utterances_returns_404_for_unknown_argument()`)
- Test function names describe the exact scenario (example: `test_utterances_ordered_by_sequence()` is explicit)

**Structure:**
```
api/tests/
├── __init__.py
├── test_arguments.py    # Tests for GET /arguments/{id}/utterances
└── test_people.py       # Tests for GET /people/{id}

pipeline/tests/
├── conftest.py          # Shared fixtures: engine, async_session, clean_db
├── test_seed_aliases.py
├── test_resolve.py
└── test_state_machine.py

tests/
├── conftest.py          # Root-level: loads .env
├── test_models_import.py       # Verify ORM model structure (TDD RED pattern)
├── test_cases_api.py           # API architectural constraints (no create_all, etc.)
└── test_schema.py              # Database schema validation
```

## Test Structure

**Suite Organization:**

```python
# From api/tests/test_arguments.py — pattern followed throughout

@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app."""
    from api.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """GET /health should return 200 {"status": "ok"}."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Patterns:**
- **Setup:** Fixtures with `@pytest.fixture` or `@pytest_asyncio.fixture` for async
- **Teardown:** Implicit via context managers; async fixtures use `async with` and `yield`
- **Assertions:** Plain `assert` statements with descriptive messages
- **Async execution:** Mark test function with `@pytest.mark.asyncio` and use `await`

**Fixture Scope:**
- `scope="session"`: Database connection setup (e.g., `engine` in `pipeline/tests/conftest.py`)
- `scope="function"`: Fresh state per test (e.g., `async_session` fixture)
- Default (no scope specified): Function-scoped

Example from `pipeline/tests/conftest.py`:
```python
@pytest.fixture(scope="session")
def engine(test_db_url: str):
    """Create a session-scoped async SQLAlchemy engine for tests."""
    return create_async_engine(test_db_url, connect_args={"statement_cache_size": 0})

@pytest.fixture()
async def async_session(engine) -> AsyncSession:
    """Yield an AsyncSession for each test, rolling back after completion."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
```

## Mocking

**Framework:** No external mocking library detected; uses built-in Python mocks or fixture-based isolation

**Patterns:**
- **Database-backed tests:** Use real `AsyncSession` fixture with test database (opt-in via `clean_db` fixture for table truncation)
- **API-backed tests:** Use `ASGITransport` with FastAPI app in-process (no real HTTP server)
- **Conditional skipping:** Use `@pytest.mark.skipif()` to skip tests when dependencies (e.g., database) are unavailable

Example from `api/tests/test_arguments.py`:
```python
def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"

@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_get_utterances_returns_utterances(client: AsyncClient) -> None:
    """Test only runs if database is configured."""
    response = await client.get("/arguments/1/utterances")
    assert response.status_code == 200
```

**What to Mock:**
- Nothing (codebase uses real objects with test database)
- Use `clean_db` fixture for opt-in table truncation before tests

**What NOT to Mock:**
- Database connections (use test database via `async_session` fixture)
- FastAPI app (test via `ASGITransport`, not mocked)
- API responses (test against real endpoints when possible; use fixtures for test data)

## Fixtures and Factories

**Test Data:**
- **Database fixtures:** `async_session` provides a clean session per test (implicit rollback isolation)
- **Data factories:** Not explicitly implemented; tests assume seeded data (e.g., Obergefell case with argument_id=1)

Example from `pipeline/tests/test_seed_aliases.py`:
```python
async def test_seed_creates_justices(async_session):
    """Test that seed-aliases creates Justice roles and people."""
    # No explicit factory; just use async_session and assert on ORM queries
    from api.models.models import Role, Person
    # ... run seed_aliases command ...
    result = await async_session.execute(select(Role).filter(Role.name == "Associate Justice"))
    assert result.scalar_one_or_none() is not None
```

**Location:**
- Fixtures: `tests/conftest.py`, `pipeline/tests/conftest.py`, `api/tests/conftest.py`
- Test data: Seeded via pipeline commands (e.g., `seed_aliases`) or hardcoded in individual test functions
- Database cleanup: `clean_db` fixture in `pipeline/tests/conftest.py` truncates tables with CASCADE

## Coverage

**Requirements:** No coverage target enforced; tests are TDD-driven for phases

**View Coverage:**
```bash
pytest --cov=api --cov=pipeline --cov-report=html
```
(Coverage tool `pytest-cov` not listed in `requirements.txt`; would need to be added)

**Current coverage approach:**
- Critical paths tested: API endpoints, schema validation, parser state machine
- Database constraints tested via `test_schema.py`
- Model structure tested via `test_models_import.py` (TDD RED pattern)

## Test Types

**Unit Tests:**
- **Scope:** Individual functions or small modules
- **Approach:** No mocking; use real dependencies where feasible
- Example: `test_normalize_label()` in `pipeline/tests/test_resolve.py` tests a pure function
  ```python
  def test_normalize_label():
      """Test label normalization."""
      assert normalize_label("JUSTICE THOMAS") == "justice thomas"
  ```

**Integration Tests:**
- **Scope:** Multiple components working together (e.g., API endpoint → service → database)
- **Approach:** Use real `AsyncSession` and database; tests marked with `@pytest.mark.skipif(not _db_configured())`
- Example: `test_get_utterances_returns_utterances()` in `api/tests/test_arguments.py` tests full flow
  ```python
  @pytest.mark.asyncio
  @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
  async def test_get_utterances_returns_utterances(client: AsyncClient) -> None:
      response = await client.get("/arguments/1/utterances")
      assert response.status_code == 200
      # Assertions on real data from database
  ```

**E2E Tests:**
- Not used; pipeline is CLI-only (offline operator tool) and website is read-only
- No browser automation tests

**Constraint/Compliance Tests:**
- Database schema validation: `tests/test_schema.py`
- Architectural invariants: `tests/test_cases_api.py` (e.g., verify no `create_all` calls)
- Model structure: `tests/test_models_import.py` (TDD RED pattern)

Example from `tests/test_cases_api.py`:
```python
def test_no_create_all_in_cases_router():
    """Verify that create_all is not called in the router module."""
    import inspect
    import api.routers.cases as router_module
    source = inspect.getsource(router_module)
    assert "create_all" not in source, "create_all found in cases router"
```

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_async_operation(async_session: AsyncSession) -> None:
    """Test an async function or operation."""
    result = await some_async_function(async_session)
    assert result is not None
```

**Error Testing:**
```python
@pytest.mark.asyncio
async def test_get_utterances_returns_404_for_unknown_argument(
    client: AsyncClient,
) -> None:
    """Verify 404 when argument is not found."""
    response = await client.get("/arguments/99999/utterances")
    assert response.status_code in (404, 500)  # Accept 500 if DB is down
    if response.status_code == 404:
        assert response.json()["detail"] == "Argument not found"
```

**Database Isolation:**
```python
@pytest.fixture()
async def async_session(engine) -> AsyncSession:
    """Yield an AsyncSession with automatic rollback after test."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # Rolls back all changes after test completes
```

**Conditional Database Tests:**
```python
@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_with_real_database(client: AsyncClient) -> None:
    """This test only runs if database is configured."""
    response = await client.get("/arguments/1/utterances")
    assert response.status_code == 200
```

**Test Organization with Sections:**
```python
# From api/tests/test_arguments.py

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    ...

# ---------------------------------------------------------------------------
# Test 1: Health endpoint — works without a real database
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    ...

# ---------------------------------------------------------------------------
# Test 2: 404 for unknown argument — works without real DB data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_utterances_returns_404_for_unknown_argument(
    client: AsyncClient,
) -> None:
    ...
```

---

*Testing analysis: 2026-06-15*
