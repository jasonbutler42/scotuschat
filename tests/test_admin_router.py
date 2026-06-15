"""
Static-analysis tests for the admin router (Phase 5, Plan 02).

These tests verify:
1. api/routers/admin.py defines verify_admin_token
2. admin.py declares the router with prefix="/api/admin"
3. verify_admin_token is injected via Depends at the router level (not per-route)
4. @router.get("/health") route exists
5. Health route returns {"status": "ok"}
6. verify_admin_token raises 401 with detail "Unauthorized"
7. admin.py contains no create_all (Alembic is sole DDL authority)
8. api/main.py imports admin_router
9. api/main.py mounts admin_router.router via include_router
10. api/main.py still registers all three existing routers (regression guard)
11. api.main imports without error (smoke import)

All tests are static analysis checks — no database or ASGI client required.
They run in < 1 second and pass in CI without DATABASE_URL set (per D-15).

Run with:
    pytest tests/test_admin_router.py -x -q
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
# Test 1: verify_admin_token is defined in admin.py
# ---------------------------------------------------------------------------


def test_admin_router_defines_verify_admin_token():
    """api/routers/admin.py must define the verify_admin_token dependency function."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    assert admin_py.exists(), (
        "api/routers/admin.py does not exist — "
        "admin router file must be created for Phase 5"
    )
    content = admin_py.read_text(encoding="utf-8")
    assert "def verify_admin_token" in content, (
        "Expected 'def verify_admin_token' in api/routers/admin.py — "
        "auth dependency function is missing"
    )


# ---------------------------------------------------------------------------
# Test 2: router uses prefix="/api/admin"
# ---------------------------------------------------------------------------


def test_admin_router_has_correct_prefix():
    """api/routers/admin.py must declare the router with prefix='/api/admin' (D-09)."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert 'prefix="/api/admin"' in content, (
        "Expected 'prefix=\"/api/admin\"' in api/routers/admin.py — "
        "prefix must be /api/admin not /admin (D-09: avoids SvelteKit /admin/* collision)"
    )


# ---------------------------------------------------------------------------
# Test 3: verify_admin_token injected at the router level via Depends
# ---------------------------------------------------------------------------


def test_admin_router_dependency_at_router_level():
    """
    verify_admin_token must appear inside the APIRouter(...) declaration
    via Depends, not only on individual routes.

    The dependency lives at the router level so Phase 6 can swap it in one place
    without touching route signatures (D-12).
    """
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert "Depends(verify_admin_token)" in content, (
        "Expected 'Depends(verify_admin_token)' in api/routers/admin.py — "
        "dependency must be wired into the APIRouter constructor"
    )


# ---------------------------------------------------------------------------
# Test 4: health route is defined
# ---------------------------------------------------------------------------


def test_admin_router_has_health_route():
    """api/routers/admin.py must define GET /health via @router.get('/health')."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert '@router.get("/health")' in content, (
        "Expected '@router.get(\"/health\")' in api/routers/admin.py — "
        "GET /health smoke-test route is missing (D-11)"
    )


# ---------------------------------------------------------------------------
# Test 5: health route returns {"status": "ok"}
# ---------------------------------------------------------------------------


def test_admin_router_health_returns_ok():
    """api/routers/admin.py health handler must return the string 'status': 'ok'."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert '"status": "ok"' in content, (
        "Expected '\"status\": \"ok\"' in api/routers/admin.py — "
        "health route must return {\"status\": \"ok\"} mirroring the main app /health probe"
    )


# ---------------------------------------------------------------------------
# Test 6: verify_admin_token raises 401 with detail "Unauthorized"
# ---------------------------------------------------------------------------


def test_admin_router_raises_401_unauthorized():
    """verify_admin_token must raise HTTPException with status_code=401 and detail='Unauthorized'."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert "status_code=401" in content, (
        "Expected 'status_code=401' in api/routers/admin.py — "
        "verify_admin_token must raise HTTPException(status_code=401, ...)"
    )
    assert '"Unauthorized"' in content, (
        "Expected '\"Unauthorized\"' as the 401 detail in api/routers/admin.py — "
        "detail must be the constant string 'Unauthorized' (T-05-05: no token info in response)"
    )


# ---------------------------------------------------------------------------
# Test 7: no create_all in admin router (Alembic is sole DDL authority)
# ---------------------------------------------------------------------------


def test_no_create_all_in_admin_router():
    """api/routers/admin.py must not call Base.metadata.create_all."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "Found 'create_all' in api/routers/admin.py — "
        "Alembic is the sole DDL authority (CLAUDE.md hard constraint)"
    )


# ---------------------------------------------------------------------------
# Task 2: main.py mounting assertions
# ---------------------------------------------------------------------------


def test_main_py_imports_admin_router():
    """api/main.py must import the admin router as admin_router."""
    main_py = _project_root() / "api" / "main.py"
    content = main_py.read_text(encoding="utf-8")
    assert "admin_router" in content, (
        "Expected 'admin_router' in api/main.py — "
        "admin router import is missing (from api.routers import admin as admin_router)"
    )
    assert "admin" in content, (
        "Expected 'admin' in api/main.py — "
        "admin router not referenced"
    )


def test_main_py_mounts_admin_router():
    """api/main.py must call app.include_router(admin_router.router)."""
    main_py = _project_root() / "api" / "main.py"
    content = main_py.read_text(encoding="utf-8")
    assert "include_router(admin_router.router)" in content, (
        "Expected 'include_router(admin_router.router)' in api/main.py — "
        "admin router is not mounted"
    )


def test_main_py_still_registers_all_existing_routers():
    """
    api/main.py must still register arguments_router, cases_router, and people_router.

    Regression guard (D-14): Phase 5 adds the admin router without touching existing
    v1.0 router registrations.
    """
    main_py = _project_root() / "api" / "main.py"
    content = main_py.read_text(encoding="utf-8")
    for router_name in ("arguments_router", "cases_router", "people_router"):
        assert router_name in content, (
            f"Expected '{router_name}' in api/main.py — "
            f"existing router registration was removed (regression — D-14)"
        )


def test_api_main_imports_without_error():
    """
    Importing api.main must succeed with the admin router mounted.

    This is a smoke import — no requests made, no DB connection required.
    ADMIN_TOKEN is set to a sentinel value for this test only; pydantic-settings
    reads it at import time. The value is not a real secret.
    """
    import importlib
    import sys
    import os

    # Set ADMIN_TOKEN so pydantic-settings Settings() construction succeeds.
    # This does not test the token value itself — only that the module loads.
    os.environ.setdefault("ADMIN_TOKEN", "test-smoke-import")

    # Remove cached api.* modules so we get a fresh import with ADMIN_TOKEN set.
    for mod in list(sys.modules.keys()):
        if mod.startswith("api."):
            del sys.modules[mod]

    try:
        importlib.import_module("api.main")
    except Exception as exc:
        raise AssertionError(
            f"Importing api.main failed with: {exc}\n"
            "Ensure ADMIN_TOKEN env var is set and api/main.py is valid."
        ) from exc
