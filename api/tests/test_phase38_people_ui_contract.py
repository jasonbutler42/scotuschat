"""
Phase 38 Plan 06 — People editor UI contract.

No frontend test harness exists in app/package.json (see 38-RESEARCH.md /
36-PATTERNS.md) — most of this file follows the established static
source-contract pattern (test_admin_jobs_phase35_frontend.py,
test_phase38_extracted_value_contract.py) to lock the Svelte/TypeScript
contract without a Svelte component test runner.

Task 1's parity section is the one exception: Node.js (v22.6+, and
unconditionally on v23.6+) can execute plain, erasable TypeScript syntax
directly (`node file.ts`), so app/src/lib/personNames.ts's live-preview
formatter is executed for real against the exact same shared fixture
(api/tests/fixtures/person_name_cases.json) api/tests/test_person_names.py
consumes — this is genuine cross-language parity verification, not just a
substring match against the source text. If `node` is unavailable in the
execution environment, the parity tests are skipped (not failed) — every
other assertion in this file is a pure static source-contract check with no
such dependency.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
PERSON_NAMES_TS_PATH = ROOT / "app" / "src" / "lib" / "personNames.ts"
FIXTURE_PATH = ROOT / "api" / "tests" / "fixtures" / "person_name_cases.json"

NODE_BIN = shutil.which("node")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: personNames.ts — preview-only formatter, parity-locked to the
# shared fixture (D-01, D-02, D-05–D-09). Never a second independent rule,
# never accepts full_name as input (T-38-16 — the backend is the sole
# persistence authority).
# ─────────────────────────────────────────────────────────────────────────────


_NODE_DRIVER = r"""
import { readFileSync } from "node:fs";
import {
  previewFullName,
  normalizeNamePart,
  formatFullName,
} from "PERSON_NAMES_TS_URL";

const fixture = JSON.parse(readFileSync("FIXTURE_JSON_PATH", "utf-8"));

function materialize(spec) {
  if (spec === null || spec === undefined) return null;
  if (typeof spec === "object" && "repeat_char" in spec) {
    return spec.repeat_char.repeat(spec.length);
  }
  return spec;
}

const results = { format_cases: [], normalization_cases: [], invalid_cases: [] };

for (const c of fixture.format_cases) {
  try {
    const actual = formatFullName(c.first, c.middle, c.last, c.suffix);
    results.format_cases.push({ name: c.name, ok: actual === c.expected_full_name, actual });
  } catch (e) {
    results.format_cases.push({ name: c.name, ok: false, error: String(e) });
  }
}

for (const c of fixture.normalization_cases) {
  try {
    const actual = normalizeNamePart(c.raw, c.field);
    results.normalization_cases.push({ name: c.name, ok: actual === c.expected, actual });
  } catch (e) {
    results.normalization_cases.push({ name: c.name, ok: false, error: String(e) });
  }
}

const blankCase = fixture.invalid_cases.find(
  (c) => c.name === "blank_first_and_last_rejected"
);
results.preview_blank_is_na =
  previewFullName({
    first: blankCase.parts.first,
    middle: blankCase.parts.middle,
    last: blankCase.parts.last,
    suffix: blankCase.parts.suffix,
  }) === "N/A";

for (const c of fixture.invalid_cases) {
  if (c.name === "blank_first_and_last_rejected") continue;
  const parts = c.parts;
  let code = null;
  try {
    const first = normalizeNamePart(materialize(parts.first), "first_name");
    const middle = normalizeNamePart(materialize(parts.middle), "middle_name");
    const last = normalizeNamePart(materialize(parts.last), "last_name");
    const suffix = normalizeNamePart(materialize(parts.suffix), "name_suffix");
    formatFullName(first, middle, last, suffix);
  } catch (e) {
    code = e && e.code ? e.code : null;
  }
  results.invalid_cases.push({ name: c.name, ok: code === c.expected_error_code, code });
}

console.log(JSON.stringify(results));
"""


@pytest.fixture(scope="module")
def node_parity_results() -> dict:
    if NODE_BIN is None:
        pytest.skip("node is not available in this execution environment")

    driver = _NODE_DRIVER.replace(
        "PERSON_NAMES_TS_URL", PERSON_NAMES_TS_PATH.resolve().as_uri()
    ).replace("FIXTURE_JSON_PATH", str(FIXTURE_PATH.resolve()))

    proc = subprocess.run(
        [NODE_BIN, "--input-type=module"],
        input=driver,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node driver failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_personnames_ts_format_cases_match_shared_fixture(node_parity_results) -> None:
    failures = [c for c in node_parity_results["format_cases"] if not c["ok"]]
    assert not failures, f"formatFullName mismatches: {failures}"


def test_personnames_ts_normalization_cases_match_shared_fixture(node_parity_results) -> None:
    failures = [c for c in node_parity_results["normalization_cases"] if not c["ok"]]
    assert not failures, f"normalizeNamePart mismatches: {failures}"


def test_personnames_ts_invalid_cases_raise_matching_error_codes(node_parity_results) -> None:
    failures = [c for c in node_parity_results["invalid_cases"] if not c["ok"]]
    assert not failures, f"error-code mismatches: {failures}"


def test_personnames_ts_preview_returns_na_until_first_or_last(node_parity_results) -> None:
    assert node_parity_results["preview_blank_is_na"] is True


def test_personnames_ts_never_accepts_full_name_as_input() -> None:
    """T-38-16 (never a second independent authority): this module has no
    persistence path at all — no fetch/network call, and no function accepts
    a `full_name` parameter to compute or override the preview."""
    source = _source(PERSON_NAMES_TS_PATH)
    assert "fetch(" not in source
    assert "full_name:" not in source
    assert "full_name =" not in source


def test_personnames_ts_declares_same_column_bounds_as_backend() -> None:
    source = _source(PERSON_NAMES_TS_PATH)
    assert "FIRST_NAME_MAX_LENGTH = 150" in source
    assert "MIDDLE_NAME_MAX_LENGTH = 150" in source
    assert "LAST_NAME_MAX_LENGTH = 150" in source
    assert "NAME_SUFFIX_MAX_LENGTH = 50" in source
    assert "FULL_NAME_MAX_LENGTH = 300" in source
