"""
Static-analysis tests for the GET /cases endpoint (Wave 0).

These tests verify:
1. The cases router is imported and registered in api/main.py
2. api/routers/cases.py defines a GET route
3. api/routers/cases.py does NOT call Base.metadata.create_all
4. api/services/cases.py does NOT call Base.metadata.create_all
5. api/services/cases.py contains the is_lead filter (prevents consolidated-docket duplication)
6. No SvelteKit cases route file uses PUBLIC_FASTAPI_BASE_URL (CLAUDE.md constraint)

All 6 tests are static analysis checks — no database required.
They run in < 1 second and pass in CI without DATABASE_URL set.

Run with:
    pytest tests/test_cases_api.py -x -q
"""

import os
import pathlib


# ---------------------------------------------------------------------------
# Helper: resolve project root from this file's location
# ---------------------------------------------------------------------------

def _project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Test 1: cases router is registered in api/main.py
# ---------------------------------------------------------------------------


def test_cases_router_registered_in_main():
    """The cases router must be imported and registered in api/main.py."""
    main_py = _project_root() / "api" / "main.py"
    content = main_py.read_text(encoding="utf-8")
    assert "cases" in content, (
        "Expected 'cases' to appear in api/main.py — "
        "cases router not imported or registered"
    )
    assert "cases_router" in content, (
        "Expected 'cases_router' to appear in api/main.py — "
        "import 'from api.routers import cases as cases_router' is missing"
    )


# ---------------------------------------------------------------------------
# Test 2: cases router defines a GET route
# ---------------------------------------------------------------------------


def test_cases_router_has_get_path():
    """api/routers/cases.py must define at least one GET route via @router.get."""
    cases_router = _project_root() / "api" / "routers" / "cases.py"
    content = cases_router.read_text(encoding="utf-8")
    assert "@router.get" in content, (
        "No '@router.get' decorator found in api/routers/cases.py — "
        "GET /cases endpoint is missing"
    )


# ---------------------------------------------------------------------------
# Test 3: no create_all in cases router
# ---------------------------------------------------------------------------


def test_no_create_all_in_cases_router():
    """api/routers/cases.py must not call Base.metadata.create_all."""
    cases_router = _project_root() / "api" / "routers" / "cases.py"
    content = cases_router.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "Found 'create_all' in api/routers/cases.py — "
        "Alembic is the sole DDL authority (CLAUDE.md hard constraint)"
    )


# ---------------------------------------------------------------------------
# Test 4: no create_all in cases service
# ---------------------------------------------------------------------------


def test_no_create_all_in_cases_service():
    """api/services/cases.py must not call Base.metadata.create_all."""
    cases_service = _project_root() / "api" / "services" / "cases.py"
    content = cases_service.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "Found 'create_all' in api/services/cases.py — "
        "Alembic is the sole DDL authority (CLAUDE.md hard constraint)"
    )


# ---------------------------------------------------------------------------
# Test 5: is_lead filter present in cases service
# ---------------------------------------------------------------------------


def test_is_lead_filter_in_cases_service():
    """
    api/services/cases.py must filter by is_lead to prevent duplicate rows
    from consolidated dockets (e.g. Obergefell 14-556/562/571/574).
    """
    cases_service = _project_root() / "api" / "services" / "cases.py"
    content = cases_service.read_text(encoding="utf-8")
    assert "is_lead" in content, (
        "Expected 'is_lead' filter in api/services/cases.py — "
        "without this filter, consolidated dockets produce duplicate case list rows "
        "(Pitfall 4 from RESEARCH.md)"
    )


# ---------------------------------------------------------------------------
# Test 6: no PUBLIC_FASTAPI_BASE_URL in cases SvelteKit routes
# ---------------------------------------------------------------------------


def test_no_public_fastapi_base_url_in_cases_pages():
    """
    No SvelteKit route under app/src/routes/cases/ may use PUBLIC_FASTAPI_BASE_URL.

    CLAUDE.md hard constraint: FASTAPI_BASE_URL is always imported from
    $env/static/private — never as a PUBLIC_ prefix env var.

    This test passes vacuously if the cases routes directory does not yet exist,
    and will catch violations once the directory is created (Plan 03-02).
    """
    cases_dir = _project_root() / "app" / "src" / "routes" / "cases"
    if not cases_dir.exists():
        # Directory not yet created — guard passes; will catch future violations
        return
    for ts_file in cases_dir.rglob("*.ts"):
        content = ts_file.read_text(encoding="utf-8", errors="ignore")
        assert "PUBLIC_FASTAPI_BASE_URL" not in content, (
            f"Found 'PUBLIC_FASTAPI_BASE_URL' in {ts_file} — "
            "violates CLAUDE.md constraint: use FASTAPI_BASE_URL from $env/static/private only"
        )
