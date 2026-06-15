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
