"""
Phase 38 Plan 09 — Docket-value operator-facing feedback UI contract.

Locks TypeScript/Python parity for the docket-value shape rule (G-38-6 gap
closure, item 3 of the UAT `missing` list) by *source extraction plus Python
execution of the extracted rule* — deliberately not by spawning `node`.

Rationale: the existing api/tests/test_phase38_people_ui_contract.py node
driver currently errors in this environment because its inline driver script
interpolates a Windows path into a JavaScript string literal and the
backslashes are consumed. A docket rule is one anchored pattern plus one
integer, which source extraction can lock exactly and without an external
toolchain dependency. No DB, no network, no node — this module passes with
no DATABASE_URL set.
"""

import json
import re
from pathlib import Path

import pytest

from api.domain.docket_values import (
    DOCKET_VALUE_MAX_LENGTH,
    DOCKET_VALUE_PATTERN,
    DocketValueError,
    normalize_docket_value,
)

ROOT = Path(__file__).parents[2]
DOCKET_VALUES_TS_PATH = ROOT / "app" / "src" / "lib" / "docketValues.ts"
FIXTURE_PATH = ROOT / "api" / "tests" / "fixtures" / "docket_value_cases.json"
DOCKET_PILL_INPUT_PATH = ROOT / "app" / "src" / "lib" / "components" / "DocketPillInput.svelte"
ARGUMENT_DETAILS_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ArgumentDetailsCard.svelte"
PIPELINE_PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "+page.svelte"
PIPELINE_PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "+page.server.ts"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_pattern_literal(source: str) -> str:
    match = re.search(r"export const DOCKET_VALUE_PATTERN\s*=\s*'([^']*)'", source)
    assert match, "Could not find DOCKET_VALUE_PATTERN string literal in docketValues.ts"
    return match.group(1)


def _extract_max_length(source: str) -> int:
    match = re.search(r"export const DOCKET_VALUE_MAX_LENGTH\s*=\s*(\d+)", source)
    assert match, "Could not find DOCKET_VALUE_MAX_LENGTH constant in docketValues.ts"
    return int(match.group(1))


def _extracted_verdict(value, pattern: str, max_length: int):
    """Replay the extracted client rule's check ordering (blank, then
    length, then pattern) exactly as documented in the fixture metadata."""
    stripped = (value or "").strip()
    if not stripped:
        return "empty", None
    if len(stripped) > max_length:
        return "length_exceeded", None
    compiled = re.compile(pattern)
    if not compiled.fullmatch(stripped):
        return "invalid_characters", None
    return None, stripped


@pytest.fixture(scope="module")
def ts_source() -> str:
    return _source(DOCKET_VALUES_TS_PATH)


@pytest.fixture(scope="module")
def fixture_cases() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────
# Task 1: TypeScript mirror parity, locked via source extraction + Python
# execution of the extracted rule.
# ─────────────────────────────────────────────────────────────────────────


def test_docket_pattern_literal_matches_python(ts_source: str) -> None:
    extracted = _extract_pattern_literal(ts_source)
    assert extracted == DOCKET_VALUE_PATTERN


def test_docket_max_length_matches_python(ts_source: str) -> None:
    extracted = _extract_max_length(ts_source)
    assert extracted == DOCKET_VALUE_MAX_LENGTH


def test_docket_values_ts_declares_all_three_error_codes(ts_source: str) -> None:
    for code in ("empty", "length_exceeded", "invalid_characters"):
        assert f"'{code}'" in ts_source, f"missing error code {code!r} in docketValues.ts"


def test_docket_values_ts_builds_regex_from_exported_constant(ts_source: str) -> None:
    assert "new RegExp(DOCKET_VALUE_PATTERN)" in ts_source


def test_extracted_rule_matches_python_on_every_fixture_case(ts_source: str, fixture_cases: dict) -> None:
    pattern = _extract_pattern_literal(ts_source)
    max_length = _extract_max_length(ts_source)

    for case in fixture_cases["valid_cases"]:
        code, normalized = _extracted_verdict(case["value"], pattern, max_length)
        assert code is None, f"{case['name']}: expected accept, extracted rule rejected with {code}"
        assert normalized == case["normalized"]
        # Cross-check the extracted verdict against the real Python module too.
        assert normalize_docket_value(case["value"]) == case["normalized"]

    for case in fixture_cases["invalid_cases"]:
        code, _ = _extracted_verdict(case["value"], pattern, max_length)
        assert code == case["code"], f"{case['name']}: expected {case['code']}, extracted rule gave {code}"
        with pytest.raises(DocketValueError) as excinfo:
            normalize_docket_value(case["value"])
        assert excinfo.value.code == case["code"]


# ─────────────────────────────────────────────────────────────────────────
# Task 2: Inline shape error in DocketPillInput, opted into by the Pipeline
# Runner only. ArgumentDetailsCard (the post-ingest metadata editor) must
# stay untouched.
# ─────────────────────────────────────────────────────────────────────────


def test_docket_pill_input_imports_and_calls_normalize_docket_value() -> None:
    source = _source(DOCKET_PILL_INPUT_PATH)
    assert "from '$lib/docketValues'" in source
    assert "normalizeDocketValue(" in source


def test_docket_pill_input_declares_enforce_shape_prop_defaulting_false() -> None:
    source = _source(DOCKET_PILL_INPUT_PATH)
    assert "enforceShape?: boolean;" in source
    assert "enforceShape = false" in source


def test_docket_pill_input_renders_role_alert_shape_error() -> None:
    source = _source(DOCKET_PILL_INPUT_PATH)
    assert 'role="alert"' in source


def test_argument_details_card_does_not_reference_enforce_shape() -> None:
    source = _source(ARGUMENT_DETAILS_CARD_PATH)
    assert "enforceShape" not in source


def test_pipeline_page_svelte_passes_enforce_shape_to_docket_pill_input() -> None:
    source = _source(PIPELINE_PAGE_SVELTE_PATH)
    assert "<DocketPillInput" in source
    # Find the (single) DocketPillInput usage and confirm enforceShape is on it.
    match = re.search(r"<DocketPillInput\b[^>]*/>", source, flags=re.DOTALL)
    assert match, "Could not find a self-closing <DocketPillInput ... /> usage"
    assert "enforceShape" in match.group(0)
