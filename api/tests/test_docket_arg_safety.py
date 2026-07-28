"""
Tests for the docket argv-injection rejection guard (Phase 24 Plan 05, CR-01/T-24-08).

These tests verify:
1. _normalize_dockets(None, ["14-556"]) returns ["14-556"] unchanged (no regression)
2. _normalize_dockets(None, ["--dockets"]) raises HTTPException with status_code == 422
3. _normalize_dockets("-1", []) raises HTTPException with status_code == 422
   (primary_docket is guarded too, not just source_dockets)
4. _normalize_dockets(None, ["  --url  "]) raises 422 (guard applies to the STRIPPED
   value, so leading/trailing whitespace does not bypass it)
5. (static) the source of _normalize_dockets contains a startswith("-") check and a
   status_code=422 raise, proving the guard is present

All tests are callable/static-analysis checks — no database or ASGI client required.
They run in < 2 seconds and pass in CI without DATABASE_URL set.

Run with:
    pytest api/tests/test_docket_arg_safety.py -x -q
"""

import os
import pathlib

import pytest
from fastapi import HTTPException

from api.domain.docket_values import DOCKET_VALUE_MAX_LENGTH
from api.routers.admin import _normalize_dockets


# ---------------------------------------------------------------------------
# Helper: resolve project root from this file's location
# ---------------------------------------------------------------------------


def _project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return pathlib.Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Test 1: well-formed dockets pass unchanged (no regression)
# ---------------------------------------------------------------------------


def test_normalize_dockets_allows_well_formed_values():
    """Well-formed docket values are unaffected by the new rejection guard."""
    result = _normalize_dockets(None, ["14-556"])
    assert result == ["14-556"]


def test_normalize_dockets_allows_multiple_well_formed_values():
    """Multiple well-formed docket values still dedupe/order correctly (no regression)."""
    result = _normalize_dockets(None, ["14-556", "14-571"])
    assert result == ["14-556", "14-571"]


# ---------------------------------------------------------------------------
# Test 2: flag-like source_dockets value raises 422
# ---------------------------------------------------------------------------


def test_normalize_dockets_rejects_flag_like_source_docket():
    """A docket pill value starting with '--' must raise HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["--dockets"])
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Test 3: flag-like primary_docket value raises 422 (not just source_dockets)
# ---------------------------------------------------------------------------


def test_normalize_dockets_rejects_flag_like_primary_docket():
    """primary_docket is guarded too, not just the source_dockets loop."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets("-1", [])
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: guard applies to the STRIPPED value (whitespace does not bypass it)
# ---------------------------------------------------------------------------


def test_normalize_dockets_rejects_flag_like_value_with_whitespace():
    """Leading/trailing whitespace around a flag-like value must not bypass the guard."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["  --url  "])
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Test 5 (static): source contains the startswith("-") check and 422 raise
# ---------------------------------------------------------------------------


def test_normalize_dockets_source_contains_rejection_guard():
    """Static-analysis proof that the rejection guard is present in the source."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    assert admin_py.exists(), "api/routers/admin.py does not exist"
    content = admin_py.read_text(encoding="utf-8")
    assert 'startswith("-")' in content, (
        "Expected a startswith(\"-\") check in api/routers/admin.py — "
        "the docket argv-injection rejection guard is missing"
    )
    assert "status_code=422" in content, (
        "Expected a status_code=422 raise in api/routers/admin.py near the "
        "docket rejection guard"
    )


# ---------------------------------------------------------------------------
# Gap closure G-38-6/T-38-20: path-hazard and over-length docket values are
# rejected at the _normalize_dockets boundary, before create_job creates an
# AdminJob row or spawns the ingest subprocess.
# ---------------------------------------------------------------------------


def test_normalize_dockets_rejects_double_quote():
    """A docket value containing a double quote raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ['22-915"evil'])
    assert exc_info.value.status_code == 422


def test_normalize_dockets_rejects_posix_absolute_path():
    """A POSIX absolute path docket value raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["/etc/cron.d/evil"])
    assert exc_info.value.status_code == 422


def test_normalize_dockets_rejects_windows_drive_path():
    """A Windows drive-letter path docket value raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["C:\\Windows\\System32\\evil"])
    assert exc_info.value.status_code == 422


def test_normalize_dockets_rejects_traversal_segment():
    """A '..' path-traversal docket value raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["../../../tmp/evil"])
    assert exc_info.value.status_code == 422


def test_normalize_dockets_rejects_over_length_value():
    """A docket value over DOCKET_VALUE_MAX_LENGTH raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(None, ["a" * (DOCKET_VALUE_MAX_LENGTH + 1)])
    assert exc_info.value.status_code == 422


def test_normalize_dockets_rejects_uat_reported_string():
    """The verbatim UAT Test 6 reported string raises HTTPException 422."""
    with pytest.raises(HTTPException) as exc_info:
        _normalize_dockets(
            None,
            ['I wonder if there is a limit to how long the docket "numbers" can be'],
        )
    assert exc_info.value.status_code == 422


def test_normalize_dockets_well_formed_multi_docket_unaffected():
    """Well-formed multi-docket input still returns both values in order."""
    result = _normalize_dockets("22-915", ["22-916"])
    assert result == ["22-915", "22-916"]


def test_normalize_dockets_source_references_normalize_docket_value():
    """Static-analysis proof that the domain rule is wired at this boundary."""
    admin_py = _project_root() / "api" / "routers" / "admin.py"
    content = admin_py.read_text(encoding="utf-8")
    assert "normalize_docket_value" in content, (
        "Expected _normalize_dockets to call normalize_docket_value — the "
        "boundary must never be silently unwired from the shared rule"
    )
