"""
Permanent regression probe for D-03 (pytest DB-isolation bypass).

Asserts that, whenever TEST_DATABASE_URL is configured, the rootdir
`conftest.py` has already redirected DATABASE_URL onto it — regardless of
which invocation shape (bare, explicit single file, explicit multi-path)
collected this test. This is the exact explicit-multi-path shape that
wiped the shared dev database during Phase 45.

Performs no I/O and opens no database connection — this is a pure
environment/config assertion, and must stay that way so it can run as part
of `tests/test_pytest_isolation_invocation_shapes.py`'s hermetic subprocess
probes without needing a real database.
"""

import os

import pytest


def test_db_isolation_probe(pytestconfig):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not configured — nothing to probe.")

    assert getattr(pytestconfig, "_scotus_redirect_fired", False), (
        "The rootdir conftest.py's pytest_configure hook did not fire — "
        "the TEST_DATABASE_URL redirect (D-03) is not guaranteed to have "
        "run for this invocation. See root conftest.py and "
        "tests/test_pytest_isolation_invocation_shapes.py."
    )
    assert os.environ["DATABASE_URL"] == os.environ["TEST_DATABASE_URL"], (
        "DATABASE_URL does not equal TEST_DATABASE_URL — the rootdir "
        "conftest.py redirect (D-03) did not take effect for this "
        "invocation shape. This is the exact bug class that wiped the "
        "shared dev DB during Phase 45."
    )
