"""
Phase 39 Plan 08 — SpeakerPopover.svelte mockup-fidelity gap closure
(39-UAT.md gaps 2 and 3, tests 12/13).

Locks the popover's separator spacing, per-section hairline dividers,
two-column tenure row layout, month-and-year tenure range granularity, and
the apolitical-rendering regression guard by *pure static source contract* —
no database, no `_db_configured` gate, no `node` subprocess. This repo has
no frontend test framework (39-RESEARCH.md Validation Architecture), so a
source contract is the strongest automated gate available. Follows
`api/tests/test_docket_ui_contract.py`'s `ROOT` + module-level path constant
+ `_source()` shape.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
POPOVER_PATH = ROOT / "app" / "src" / "lib" / "components" / "SpeakerPopover.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of `function {name}(...) { ... }`."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    assert match, f"could not find `function {name}(` in source"
    brace_start = source.index("{", match.end())
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : i + 1]
    raise AssertionError(f"unbalanced braces while extracting function {name}")


# ─────────────────────────────────────────────────────────────────────────
# Task 1: padded separator snippet + per-section hairline dividers
# ─────────────────────────────────────────────────────────────────────────


def test_separator_snippet_declared_and_glyph_appears_exactly_once() -> None:
    source = _source(POPOVER_PATH)
    assert "{#snippet separator(" in source
    dot_count = source.count("·")
    assert dot_count == 1, f"expected exactly 1 middle-dot glyph, found {dot_count}"


def test_both_separators_rendered_through_snippet_with_explicit_padding() -> None:
    source = _source(POPOVER_PATH)
    assert "{@render separator(8)}" in source
    assert "{@render separator(4)}" in source
    render_count = source.count("{@render separator(")
    assert render_count == 2, f"expected exactly 2 separator renders, found {render_count}"


def test_separator_snippet_applies_padding_argument_as_horizontal_padding() -> None:
    source = _source(POPOVER_PATH)
    assert "padding:0 {" in source


def test_every_section_below_header_carries_one_divider() -> None:
    source = _source(POPOVER_PATH)
    divider = "border-top:1px solid #334155;"
    count = source.count(divider)
    assert count == 4, f"expected exactly 4 section dividers, found {count}"


def test_section_spacing_stays_on_declared_scale() -> None:
    source = _source(POPOVER_PATH)
    values = re.findall(r"(?:margin|padding)-top:\s*(\d+px)", source)
    assert values, "expected at least one margin-top/padding-top declaration"
    allowed = {"4px", "8px", "16px", "24px"}
    offenders = [v for v in values if v not in allowed]
    assert not offenders, f"spacing values outside declared scale: {offenders}"


def test_type_scale_unchanged() -> None:
    source = _source(POPOVER_PATH)
    sizes = set(re.findall(r"font-size:\s*(\d+px)", source))
    assert sizes <= {"12px", "13px", "14px", "16px", "18px"}, sizes
    weights = set(re.findall(r"font-weight:\s*(\d+)", source))
    assert weights <= {"400", "600"}, weights


def test_color_set_unchanged() -> None:
    source = _source(POPOVER_PATH)
    colors = set(re.findall(r"#[0-9a-fA-F]{6}", source))
    allowed = {"#1e293b", "#334155", "#e2e8f0", "#94a3b8", "#93c5fd", "#0f1117"}
    offenders = colors - allowed
    assert not offenders, f"colors outside app.css token set: {offenders}"


def test_apolitical_rendering_guard() -> None:
    source = _source(POPOVER_PATH)
    for literal in ("Republican", "Democratic", "Federalist", "Whig"):
        assert literal not in source, f"party literal {literal!r} must never appear"
    assert "reason_left ===" not in source
    assert "reason_left ==" not in source
    assert "appointing_president_party ===" not in source
    assert "{@html" not in source


def test_no_deferred_affordance() -> None:
    source = _source(POPOVER_PATH)
    assert "href=" not in source
    assert "Edit person" not in source


# ─────────────────────────────────────────────────────────────────────────
# Task 2: two-column tenure row pair, month-and-year granularity
# ─────────────────────────────────────────────────────────────────────────


def test_two_column_rows_exist() -> None:
    source = _source(POPOVER_PATH)
    space_between_count = source.count("justify-content:space-between")
    assert space_between_count == 2, f"expected 2 flex rows, found {space_between_count}"
    right_align_count = source.count("text-align:right")
    assert right_align_count == 2, f"expected 2 right-aligned cells, found {right_align_count}"


def test_right_column_cannot_be_squeezed() -> None:
    source = _source(POPOVER_PATH)
    flex_shrink_count = source.count("flex-shrink:0")
    assert flex_shrink_count >= 2, f"expected at least 2 flex-shrink:0 cells, found {flex_shrink_count}"
    assert "white-space:nowrap" in source


def test_office_title_is_only_promoted_element() -> None:
    source = _source(POPOVER_PATH)
    assert re.search(r"font-weight:600[^\"]*color:#e2e8f0", source) or re.search(
        r"color:#e2e8f0[^\"]*font-weight:600", source
    ), "expected a span combining font-weight:600 with color:#e2e8f0 for the office title"
    weight_600_count = source.count("font-weight:600")
    assert weight_600_count == 4, (
        f"expected exactly 4 font-weight:600 uses (avatar initials, name, role pill, "
        f"office title), found {weight_600_count}"
    )


def test_dash_joined_single_line_is_gone() -> None:
    source = _source(POPOVER_PATH)
    assert "} — {" not in source, "the old dash-joined title-and-years line must be removed"


def test_format_month_year_is_utc_pinned_month_and_year_only() -> None:
    source = _source(POPOVER_PATH)
    assert "function formatMonthYear" in source
    body = _function_body(source, "formatMonthYear")
    assert "month: 'short'" in body
    assert "year: 'numeric'" in body
    assert "timeZone: 'UTC'" in body
    assert "day:" not in body
    assert "} – ${" in source, "tenure range must be joined by a spaced en dash"


def test_format_short_survives_for_birth_death_line() -> None:
    source = _source(POPOVER_PATH)
    assert "function formatShort" in source
    body = _function_body(source, "formatShort")
    assert "day: 'numeric'" in body


def test_no_trailing_gap_after_last_tenure_block() -> None:
    source = _source(POPOVER_PATH)
    assert "margin-bottom:16px" not in source
    assert "i === 0 ? '0' : '8px'" in source


def test_apolitical_rendering_guard_after_restyle() -> None:
    source = _source(POPOVER_PATH)
    for literal in ("Republican", "Democratic", "Federalist", "Whig"):
        assert literal not in source, f"party literal {literal!r} must never appear"
    assert "reason_left ===" not in source
    assert "reason_left ==" not in source
    assert "appointing_president_party ===" not in source
    assert "{@html" not in source
