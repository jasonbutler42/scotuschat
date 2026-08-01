"""
Phase 44 — Resolve table rework — pure static source contract.

Plans 44-02, 44-03, and 44-04 all edit `ResolveCard.svelte` in place; this file is
shared across all three, organized with one section-comment banner per plan so each
plan's own contract stays easy to find as later plans append to it.

No frontend test framework exists in this repo (see 39-RESEARCH.md / 36-PATTERNS.md),
so a static source contract is the strongest automated gate available. Follows
`api/tests/test_phase39_popover_ui_contract.py`'s `ROOT` + module-level path constant
+ `_source()` shape, and `api/tests/test_phase38_extracted_value_contract.py`'s
sibling `RESOLVE_CARD_PATH` convention.

Plan 44-02 (this section's author) guards:
  1. Exactly five column headers exist, in the mockup's order, with no Action header
     and no residual Title header (RESOLVE-01).
  2. The Descriptor input carries its renamed field name, placeholder copy, and
     ellipsis-truncation declaration; the Raw Label badge snippet wraps rather than
     truncates (RESOLVE-01).
  3. The Descriptor cell snippet always renders — one snippet contains both the bench
     en-dash literal and the editable `<input` (RESOLVE-04).
  4. The dedicated accept-the-auto-match handler and both retired button labels are
     gone; the open-the-search handler is the one entry point; the "Suggested" badge
     lives inside the listbox-option region; the gated entry point is genuinely inert
     (D-03/D-04, T-44-07).
  5. Every hex colour literal in the file belongs to the UI-SPEC's approved palette —
     the standing guard against later passes smuggling in a new colour.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
RESOLVE_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ResolveCard.svelte"

APPROVED_HEX_COLORS = {
    "#1e293b",
    "#0f1117",
    "#334155",
    "#e2e8f0",
    "#94a3b8",
    "#93c5fd",
    "#4ade80",
    "#fbbf24",
    "#ef4444",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of `{#snippet {name}(...)} ... {/snippet}`."""
    match = re.search(rf"\{{#snippet\s+{re.escape(name)}\s*\(", source)
    assert match, f"could not find `{{#snippet {name}(` in source"
    start = match.start()
    end_match = re.search(r"\{/snippet\}", source[start:])
    assert end_match, f"could not find matching {{/snippet}} for {name}"
    return source[start : start + end_match.end()]


def _region(source: str, start_pattern: str, end_pattern: str) -> str:
    """Extract the substring from the first `start_pattern` match to the following
    `end_pattern` match (used to scope assertions to e.g. a single <li> block)."""
    start_match = re.search(start_pattern, source)
    assert start_match, f"could not find start pattern {start_pattern!r}"
    end_match = re.search(end_pattern, source[start_match.end() :])
    assert end_match, f"could not find end pattern {end_pattern!r} after start"
    return source[start_match.start() : start_match.end() + end_match.end()]


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-02 — RESOLVE-01: five-column structure, no Action column
# ─────────────────────────────────────────────────────────────────────────────


def test_exactly_five_column_headers_declared() -> None:
    source = _source(RESOLVE_CARD_PATH)
    count = source.count('<th scope="col"')
    assert count == 5, f"RESOLVE-01 requires exactly five <th scope=\"col\"> cells, found {count}"


def test_five_header_labels_appear_in_mockup_order() -> None:
    source = _source(RESOLVE_CARD_PATH)
    labels = [">Raw Label<", ">Resolved As<", ">Bench/Advocate<", ">Argument Role<", ">Descriptor<"]
    indices = []
    for label in labels:
        idx = source.find(label)
        assert idx != -1, f"RESOLVE-01: header label {label!r} not found in source"
        indices.append(idx)
    assert indices == sorted(indices), (
        f"RESOLVE-01: header labels must appear in mockup order (Raw Label, Resolved As, "
        f"Bench/Advocate, Argument Role, Descriptor); got index order {indices}"
    )


def test_no_action_header_and_no_residual_title_header() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count(">Action<") == 0, "RESOLVE-01: the retired Action column header must not exist"
    assert source.count(">Title<") == 0, "RESOLVE-01: the retired Title column header must not exist"


def test_descriptor_input_carries_renamed_field_placeholder_and_truncation() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count('name="descriptor"') == 1, (
        "RESOLVE-04: exactly one input should carry the renamed descriptor form field"
    )
    assert 'placeholder="e.g. Attorney, Location, or Affiliation"' in source, (
        "UI-SPEC Copywriting Contract: Descriptor placeholder copy must be present"
    )
    assert "text-overflow: ellipsis" in source, (
        "UI-SPEC overflow consideration: Descriptor input must ellipsis-truncate when unfocused"
    )


def test_raw_label_badge_snippet_exists_and_wraps_rather_than_truncates() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#snippet rawLabelBadge(" in source, (
        "RESOLVE-01: the Raw Label badge must be extracted into its own snippet"
    )
    badge_body = _snippet_body(source, "rawLabelBadge")
    assert "white-space: normal" in badge_body, (
        "UI-SPEC long-text backstop: the Raw Label badge must wrap (white-space: normal), "
        "never truncate — truncating a raw label could hide the discrepancy it exists to show"
    )
    assert "text-overflow: ellipsis" not in badge_body, (
        "Raw Label badge must not declare ellipsis truncation — it wraps, per UI-SPEC"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-02 — RESOLVE-04 / D-03 / D-04: Descriptor always renders; collapsed
# Resolved As entry point
# ─────────────────────────────────────────────────────────────────────────────


def test_descriptor_cell_snippet_always_renders_bench_dash_and_editable_input() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#snippet descriptorCell(" in source, (
        "RESOLVE-04: the Descriptor cell must be extracted into its own always-rendered snippet"
    )
    body = _snippet_body(source, "descriptorCell")
    assert "–" in body, "RESOLVE-04: the Descriptor cell must render an en dash for BENCH rows"
    assert "<input" in body, (
        "RESOLVE-04: the Descriptor cell must render an editable <input> for non-BENCH rows — "
        "both states in the same snippet is the 'always renders' contract"
    )
    assert "side !== 'BENCH'" not in body, (
        "RESOLVE-04: the cell body must not be gated by a wrapping non-bench check — "
        "Phase 27 CR-01/CR-02 requires the data-carrying input stay in the DOM unconditionally"
    )


def test_dedicated_confirm_handler_and_retired_button_labels_are_gone() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "handleConfirm" not in source, (
        "D-03: the dedicated accept-the-auto-match handler must be deleted entirely — "
        "there is no separate Confirm action any more"
    )
    assert ">Confirm<" not in source, "D-03: no element may render the retired 'Confirm' label"
    assert ">Select<" not in source, "D-03: no element may render the retired 'Select' label"
    assert "Select Bench or Advocate to continue" not in source, (
        "D-07: the retired gate instructional sentence must be removed"
    )


def test_open_person_search_is_the_one_entry_point() -> None:
    source = _source(RESOLVE_CARD_PATH)
    count = source.count("openPersonSearch")
    assert count >= 3, (
        f"D-03: openPersonSearch must be the single entry point — expected a definition plus "
        f"at least two call sites (Change link, Select-person link), found {count} occurrences"
    )


def test_suggested_badge_lives_inside_the_listbox_option_region() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "Suggested" in source, "D-03: the pre-filled candidate must carry a 'Suggested' badge"
    option_region = _region(source, r'role="option"', r"</li>")
    assert "Suggested" in option_region, (
        "D-03: the 'Suggested' badge must render inside the <li role=\"option\"> block, "
        "distinguishing the pre-filled top suggestion from other candidates"
    )


def test_gated_entry_point_is_genuinely_inert() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert 'aria-disabled="true"' in source, (
        "T-44-07: the gated Resolved As entry point must carry aria-disabled=\"true\" — "
        "the D-11/PJOB-18 side-first gate must survive the removal of its instructional sentence"
    )
    assert "clip-path: inset(50%)" in source, (
        "D-07: the gated row must carry a visually-hidden (sr-only) explanation of the gate"
    )
    assert source.count("Select person…") == 2, (
        "the gated inert variant and the active search link should each render 'Select person…' "
        "exactly once, for a total of 2 occurrences"
    )


def test_no_unapproved_hex_colors_introduced() -> None:
    source = _source(RESOLVE_CARD_PATH)
    found = set(re.findall(r"#[0-9a-fA-F]{6}", source))
    unapproved = found - APPROVED_HEX_COLORS
    assert not unapproved, (
        f"UI-SPEC Color table: found hex colour(s) outside the approved palette: {unapproved}. "
        f"Approved set: {APPROVED_HEX_COLORS}"
    )
