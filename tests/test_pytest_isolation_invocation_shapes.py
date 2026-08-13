"""
Permanent regression test for D-03 (pytest DB-isolation bypass).

Proves that the rootdir `conftest.py`'s TEST_DATABASE_URL redirect fires
for every pytest invocation shape, not only the bare `pytest` one. Runs
pytest as a real subprocess three times — bare/testpaths-driven, explicit
single file, and explicit multi-path (the exact `pytest <file> <file> -q`
shape that wiped the shared dev database twice during Phase 45) — and
asserts each exits 0.

Hermetic by construction: each subprocess's DATABASE_URL starts as the
literal placeholder DSN `postgresql+asyncpg://user:pass@host/db`, which
`_db_configured()` (root conftest.py, api/tests/conftest.py) rejects by
name, so the session-level row-count tripwire no-ops instead of dialling a
real server. Each subprocess's TEST_DATABASE_URL is the synthetic DSN
`postgresql+asyncpg://probe:probe@127.0.0.1:1/scotus_probe_isolation`,
whose database name is deliberately NOT `scotus_test`, so
`pipeline/tests/conftest.py`'s `_reset_test_db` guard no-ops and truncates
nothing. The only way each child's DATABASE_URL can end up equal to its
TEST_DATABASE_URL is if the rootdir conftest.py was actually collected and
its module-level redirect ran — which is exactly what this test proves for
all three invocation shapes.
"""

import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_PLACEHOLDER_DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"
_SYNTHETIC_TEST_DATABASE_URL = "postgresql+asyncpg://probe:probe@127.0.0.1:1/scotus_probe_isolation"

INVOCATION_SHAPES = [
    pytest.param(["-k", "db_isolation_probe"], id="bare-testpaths-driven"),
    pytest.param(["api/tests/test_db_isolation_probe.py"], id="explicit-single-file"),
    pytest.param(
        [
            "api/tests/test_db_isolation_probe.py",
            "pipeline/tests/test_db_isolation_probe.py",
        ],
        id="explicit-multi-path-phase45-wipe-shape",
    ),
]


@pytest.mark.parametrize("shape_args", INVOCATION_SHAPES)
def test_pytest_isolation_fires_for_every_invocation_shape(shape_args):
    env = os.environ.copy()
    env["DATABASE_URL"] = _PLACEHOLDER_DATABASE_URL
    env["TEST_DATABASE_URL"] = _SYNTHETIC_TEST_DATABASE_URL

    argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *shape_args]
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, (
        f"Invocation shape {shape_args!r} did not exit 0 — the rootdir "
        "conftest.py redirect may not have fired for this shape.\n"
        f"argv: {argv}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
