"""
TypeScript/Python parity for the docket-value shape rule (G-38-6).

The docket pattern and max length are declared in BOTH `api/domain/
docket_values.py` and its TypeScript twin. A divergence between them is a
real bug class: the browser would accept a value the server then rejects,
or vice versa. These tests EXTRACT the rule from the TypeScript source and
EXECUTE it in Python against every fixture case, so a drift in either
declaration fails here.

That extract-and-execute shape is why this module survives the testing
policy's ban on static source contracts: it does not assert that a string
is present, it runs the extracted rule and compares behavior.

No DB, no network, no node — passes with no DATABASE_URL set.

Trimmed 2026-08-27 (debridement pass): 8 declaration-presence greps against
`.svelte`/`+page.server.ts` removed. See CLAUDE.md -> Testing Policy.
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


# ─────────────────────────────────────────────────────────────────────────
# Task 3: SvelteKit action re-check with accurate operator copy. A forged
# docket[] value must be rejected server-side before FastAPI is called, and
# every other failure branch must keep its existing generic copy.
# ─────────────────────────────────────────────────────────────────────────


