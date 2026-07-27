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
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
PERSON_NAMES_TS_PATH = ROOT / "app" / "src" / "lib" / "personNames.ts"
FIXTURE_PATH = ROOT / "api" / "tests" / "fixtures" / "person_name_cases.json"

NEW_PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "new" / "+page.server.ts"
NEW_PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "new" / "+page.svelte"
ID_PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "[id]" / "+page.server.ts"
ID_PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "[id]" / "+page.svelte"
LIST_PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "+page.svelte"
LIST_PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "+page.server.ts"

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


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: standalone create + person edit forms convert to a generated,
# read-only Full Name preview; server actions read/forward only name parts
# (never full_name, T-38-16) and preserve attempted values on a 422/400
# (D-01, D-02, D-09, D-12, D-14-D-18).
# ─────────────────────────────────────────────────────────────────────────────


def test_new_page_server_never_reads_or_sends_full_name() -> None:
    """T-38-16: no code path reads a client-posted full_name or forwards one
    to FastAPI (prose mentioning `full_name` in comments/docstrings is fine —
    this checks actual identifier usage/JSON keys only)."""
    source = _source(NEW_PAGE_SERVER_PATH)
    assert "formData.get('full_name')" not in source
    assert re.search(r"\bfull_name\s*[:,=]", source) is None
    assert "const full_name" not in source


def test_new_page_server_create_action_enforces_first_or_last_minimum() -> None:
    source = _source(NEW_PAGE_SERVER_PATH)
    assert "Enter at least a first or last name." in source
    assert "if (!first_name && !last_name)" in source


def test_new_page_server_preserves_attempted_parts_on_every_failure_branch() -> None:
    """Every fail() in the create action must return the attempted name parts —
    this route has no prior person record to fall back to, so a bare fail()
    without them would silently discard operator input (D-16)."""
    source = _source(NEW_PAGE_SERVER_PATH)
    fail_calls = re.findall(r"fail\(\d+,\s*\{.*?\}\s*\)", source, flags=re.DOTALL)
    assert len(fail_calls) >= 3
    for call in fail_calls:
        assert "first_name" in call, f"missing attempted-value preservation: {call}"
        assert "last_name" in call, f"missing attempted-value preservation: {call}"


def test_new_page_svelte_renders_generated_preview_not_editable_input() -> None:
    source = _source(NEW_PAGE_SVELTE_PATH)
    assert "id=\"full_name\"" not in source
    assert 'name="full_name"' not in source
    assert "<output" in source
    assert "Generated from name parts." in source
    assert "previewFullName(" in source
    assert "bind:value={firstName}" in source
    assert "bind:value={middleName}" in source
    assert "bind:value={lastName}" in source
    assert "bind:value={nameSuffix}" in source


def test_new_page_svelte_shared_min_name_hint_not_html_required() -> None:
    """UI-SPEC: 'Do not mark both fields individually required' — no bare
    HTML `required` attribute on the name-part inputs (prose like 'is
    required before create can submit' in an unrelated comment is fine)."""
    source = _source(NEW_PAGE_SVELTE_PATH)
    assert "Enter at least a first or last name." in source
    assert re.search(r"<input\b[^>]*\brequired\b", source) is None


def test_id_page_server_never_reads_or_sends_full_name_in_save_action() -> None:
    source = _source(ID_PAGE_SERVER_PATH)
    save_action = source.split("save: async", 1)[1].split("photo: async", 1)[0]
    assert "formData.get('full_name')" not in save_action
    assert "full_name" not in save_action


def test_id_page_server_save_action_enforces_first_or_last_minimum() -> None:
    source = _source(ID_PAGE_SERVER_PATH)
    save_action = source.split("save: async", 1)[1].split("photo: async", 1)[0]
    assert "Enter at least a first or last name." in save_action
    assert "if (!first_name && !last_name)" in save_action


def test_id_page_server_person_detail_exposes_name_review_and_provenance() -> None:
    source = _source(ID_PAGE_SERVER_PATH)
    assert "name_needs_review: boolean;" in source
    assert "name_extraction_metadata:" in source


def test_id_page_svelte_renders_generated_preview_not_editable_input() -> None:
    source = _source(ID_PAGE_SVELTE_PATH)
    assert "<output" in source
    assert "Generated from name parts." in source
    assert "previewFullName(" in source
    assert "bind:value={firstName}" in source
    assert "bind:value={middleName}" in source
    assert "bind:value={lastName}" in source
    assert "bind:value={nameSuffix}" in source


def test_id_page_svelte_renders_independent_provenance_per_name_part() -> None:
    """Each of First/Middle/Last/Suffix gets its own CopyableExtractedValue
    instance (D-14/D-15/D-19) gated on the person's provenance envelope."""
    source = _source(ID_PAGE_SVELTE_PATH)
    assert source.count("<CopyableExtractedValue") == 4
    assert 'copyLabel="Copy extracted first name"' in source
    assert 'copyLabel="Copy extracted middle name"' in source
    assert 'copyLabel="Copy extracted last name"' in source
    assert 'copyLabel="Copy extracted suffix"' in source
    assert source.count("{#if data.person.name_extraction_metadata}") == 4


def test_id_page_svelte_provenance_never_overwrites_operator_value_on_edit() -> None:
    """The stacked hints are read-only reference material — there is no
    click-to-fill/autofill wiring for name parts in this plan (D-15)."""
    source = _source(ID_PAGE_SVELTE_PATH)
    assert "firstName = data.person.name_extraction_metadata" not in source
    assert "onclick={() => (firstName" not in source


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: People directory "Name review" filter/indicator (D-12, D-13) —
# reuses the existing click-to-filter pill mechanism (URL/tab-preserving,
# single-select) rather than a new dashboard queue or rerun control.
# ─────────────────────────────────────────────────────────────────────────────


def test_list_page_server_threads_name_needs_review_field() -> None:
    source = _source(LIST_PAGE_SERVER_PATH)
    assert "name_needs_review: boolean;" in source


def test_list_page_svelte_declares_pill_label_helper_for_name_review() -> None:
    source = _source(LIST_PAGE_SVELTE_PATH)
    assert "function pillLabel(field: string): string {" in source
    assert "field === 'name review' ? 'Name review' : field" in source


def test_list_page_svelte_pill_rendering_uses_pill_label_and_preserves_filter_mechanism() -> None:
    """Same togglePillFilter/data.missing/data.tab mechanism as every other
    missing-field pill — Name review is additive, not a parallel code path."""
    source = _source(LIST_PAGE_SVELTE_PATH)
    assert "onclick={() => togglePillFilter(field)}" in source
    assert ">{pillLabel(field)}</button>" in source
    assert 'aria-label="Filter by {pillLabel(field)}"' in source
    assert "class:pill-active={data.missing === field}" in source


def test_list_page_svelte_exact_name_review_empty_state_copy() -> None:
    source = _source(LIST_PAGE_SVELTE_PATH)
    assert "{:else if data.missing === 'name review'}" in source
    assert "No people need name review" in source
    assert "Ambiguous legacy names will appear here for review." in source


def test_list_page_svelte_togglepillfilter_preserves_tab_in_url() -> None:
    """Selecting/clearing any pill (including Name review) round-trips through
    the same `?tab=...&missing=...` URL, preserving the active tab."""
    source = _source(LIST_PAGE_SVELTE_PATH)
    fn = source.split("function togglePillFilter(field: string) {", 1)[1].split("\n\t}", 1)[0]
    assert "goto('/admin/people?tab=' + data.tab)" in fn
    assert "goto('/admin/people?tab=' + data.tab + '&missing=' + encodeURIComponent(field))" in fn


def test_no_dashboard_queue_or_rerun_control_introduced() -> None:
    """D-13: the focused People directory filter is deliberately NOT paired
    with a general-purpose Admin Dashboard attention queue, and this plan
    must not resurrect the Phase 35-removed job-rerun control."""
    for path in (LIST_PAGE_SVELTE_PATH, LIST_PAGE_SERVER_PATH, ID_PAGE_SVELTE_PATH, ID_PAGE_SERVER_PATH):
        source = _source(path)
        assert "rerun" not in source.lower()
    assert not (ROOT / "app" / "src" / "routes" / "admin" / "dashboard").exists()
