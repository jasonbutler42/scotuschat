"""
Proves the dev-only reset router is genuinely ABSENT (not merely refused)
outside development (Phase 43, Plan 43-01, DEVTOOL-02, D-07).

This module deliberately mutates os.environ and sys.modules (the same
module-re-import technique tests/test_admin_router.py::
test_api_main_imports_without_error already established) — it restores BOTH
in a finally block on every re-import, so the rest of the suite (which runs
against the real development settings loaded from .env) is never left
holding a production-configured module graph. This file must never open a
database connection: routing decisions are made before any handler or
dependency runs, so no DB is needed to prove a 404.
"""

import importlib
import sys
import os

import pytest
from httpx import ASGITransport, AsyncClient


def _all_route_paths(app) -> list[str]:
    """
    Recursively collect every registered route path on `app`.

    FastAPI >=0.139 (the version installed in this project's .venv at the
    time this test was written — requirements.txt pins fastapi[standard]
    >=0.115, so this is a same-major-version drift, not a pin violation)
    wraps each `include_router()` call in a private `fastapi.routing.
    _IncludedRouter` object that has no `.path` attribute of its own — the
    actual routes live on `.original_router.routes`. This helper walks both
    shapes so route-presence/absence assertions keep working regardless of
    which FastAPI minor version is installed.
    """
    paths: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            paths.append(path)
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            for sub_route in getattr(original_router, "routes", []):
                sub_path = getattr(sub_route, "path", None)
                if sub_path:
                    paths.append(sub_path)
    return paths


def _reimport_api_main(environment_value: str):
    """
    Re-import api.main with ENVIRONMENT set to `environment_value`.

    Saves the current ENVIRONMENT/ADMIN_TOKEN values from os.environ, sets
    ENVIRONMENT to the supplied value and os.environ.setdefault("ADMIN_TOKEN",
    ...) so Settings() construction succeeds, purges every sys.modules key
    starting with "api." for a fresh import, then imports api.main and
    returns it.

    Restores the original env values and purges api.* from sys.modules AGAIN
    in a finally block — this is the whole reason this is a helper and not
    two copy-pasted blocks. The returned module object remains valid to the
    caller even after restoration (Python does not garbage-collect an
    already-imported module merely because sys.modules no longer references
    it); restoring immediately is what lets the REST of the suite's own
    local `from api.main import app`-style imports (api/tests/conftest.py's
    _api_lifespan fixture) rebuild against the real development settings.
    """
    original_environment = os.environ.get("ENVIRONMENT")
    original_admin_token = os.environ.get("ADMIN_TOKEN")

    os.environ["ENVIRONMENT"] = environment_value
    os.environ.setdefault("ADMIN_TOKEN", "test-smoke-import")

    for mod in list(sys.modules.keys()):
        if mod.startswith("api."):
            del sys.modules[mod]

    try:
        main = importlib.import_module("api.main")
        return main
    finally:
        if original_environment is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = original_environment

        if original_admin_token is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = original_admin_token

        for mod in list(sys.modules.keys()):
            if mod.startswith("api."):
                del sys.modules[mod]


def _assert_pre_existing_routers_still_mounted(paths: list[str]) -> None:
    """
    Regression guard: the gate did not accidentally take the whole admin
    surface (or any other pre-existing router) down with it.

    Actual mount prefixes per api/routers/{admin,arguments,cases,people}.py:
    admin is under /api/admin; arguments/cases/people have NO /api prefix
    (api/routers/arguments.py: APIRouter(prefix="/arguments", ...), etc.) —
    NOT /api/arguments, /api/cases, /api/people.
    """
    assert any(p.startswith("/api/admin") for p in paths)
    assert any(p.startswith("/arguments") for p in paths)
    assert any(p.startswith("/cases") for p in paths)
    assert any(p.startswith("/people") for p in paths)


@pytest.mark.asyncio
async def test_dev_router_absent_outside_development():
    """
    Outside development, the dev router is genuinely unregistered — no route
    path starts with /api/admin/dev — and a request to it 404s, NOT 403. A
    403 would confirm to a prober that the endpoint exists at all
    (Information Disclosure, RESEARCH.md Security Domain table).
    """
    main = _reimport_api_main("production")
    paths = _all_route_paths(main.app)

    assert not any(p.startswith("/api/admin/dev") for p in paths)
    _assert_pre_existing_routers_still_mounted(paths)

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/admin/dev/reset-to-fixture")

    assert resp.status_code == 404
    assert resp.status_code != 403


def test_dev_router_present_in_development():
    """
    The inverse of the absence test — without this, the absence test would
    still pass if the router file were deleted entirely.
    """
    main = _reimport_api_main("development")
    paths = _all_route_paths(main.app)

    assert any(p == "/api/admin/dev/reset-to-fixture" for p in paths)


@pytest.mark.parametrize(
    "near_miss_value",
    ["", "Development", "DEVELOPMENT"],
    ids=["empty-string", "capitalized", "all-caps"],
)
def test_dev_router_absent_for_allowlist_near_misses(near_miss_value):
    """
    D-02: the gate is an ALLOW-list (== "development"), not a block-list.
    An empty string and near-miss capitalization variants must also yield
    absence — if this were a block-list (e.g. != "production"), these
    values would incorrectly pass.
    """
    main = _reimport_api_main(near_miss_value)
    paths = _all_route_paths(main.app)

    assert not any(p.startswith("/api/admin/dev") for p in paths)
