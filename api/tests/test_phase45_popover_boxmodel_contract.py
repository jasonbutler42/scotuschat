"""
Phase 45 Plan 02 — BUG-02 / D-03 box-model relocation contract.

Locks single-element ownership of the speaker popover's visible box model:
`Popover.Content` (in `+page.svelte`) now owns the surface color, border,
radius, width bounds, max-height, and overflow together, so the native
scrollbar renders flush inside the card's visible rounded boundary instead
of at the edge of an invisible scroll container.

This repo has no frontend test framework (see `test_phase39_popover_ui_
contract.py`'s docstring), so a static source contract is the strongest
automated gate available. Follows that module's `ROOT` / path-constant /
`_source()` shape.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
POPOVER_PATH = ROOT / "app" / "src" / "lib" / "components" / "SpeakerPopover.svelte"
PAGE_PATH = (
    ROOT
    / "app"
    / "src"
    / "routes"
    / "cases"
    / "[slug]"
    / "arguments"
    / "[id]"
    / "+page.svelte"
)
APP_CSS_PATH = ROOT / "app" / "src" / "app.css"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _css_rule_body(source: str, selector: str) -> str:
    """Extract the brace-balanced body of a CSS rule from a <style> block."""
    match = re.search(rf"{re.escape(selector)}\s*{{", source)
    assert match, f"could not find CSS rule `{selector} {{` in source"
    brace_start = match.end() - 1
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : i + 1]
    raise AssertionError(f"unbalanced braces while extracting rule {selector}")


def _popover_content_tag(source: str) -> str:
    """Return the text of the opening <Popover.Content ...> tag."""
    match = re.search(r"<Popover\.Content", source)
    assert match, "could not find `<Popover.Content` opening tag"
    end = source.index(">", match.start())
    return source[match.start() : end + 1]


# ─────────────────────────────────────────────────────────────────────────
# Task 1: single-box ownership
# ─────────────────────────────────────────────────────────────────────────


def test_popover_content_owns_full_box_model() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "background-color: #1e293b" in tag
    assert "border: 1px solid #334155" in tag
    assert "border-radius: 8px" in tag
    assert "min-width: 300px" in tag
    assert "max-width: 400px" in tag
    assert "max-height: min(560px, 80vh)" in tag
    assert "overflow-y: auto" in tag
    assert "z-index: 50" in tag


def test_popover_card_reduced_to_padding_and_display_only() -> None:
    body = _css_rule_body(_source(POPOVER_PATH), ".popover-card")
    assert "padding: 24px" in body
    assert "display: block" in body
    # Region-scoped absence: these declarations moved up to Popover.Content.
    # Assert against the extracted rule body only — the file legitimately
    # keeps border-radius:50% on the avatar circles and border-top hairlines
    # elsewhere, so a whole-file assertion would be unsatisfiable.
    for relocated in (
        "background-color: #1e293b",
        "border: 1px solid #334155",
        "border-radius: 8px",
        "min-width: 300px",
        "max-width: 400px",
    ):
        assert relocated not in body, f"{relocated!r} should have moved off .popover-card"


def test_no_scrollbar_theming_introduced() -> None:
    popover_source = _source(POPOVER_PATH)
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    forbidden = (
        "::-webkit-scrollbar",
        "scrollbar-width",
        "scrollbar-color",
    )
    for literal in forbidden:
        assert literal not in popover_source, f"{literal!r} must not appear in SpeakerPopover.svelte"
        assert literal not in page_tag, f"{literal!r} must not appear in the Popover.Content tag"


def test_no_box_sizing_override_introduced() -> None:
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    assert "box-sizing" not in page_tag
    app_css = _source(APP_CSS_PATH)
    assert "box-sizing: border-box" in app_css
    assert "*, *::before, *::after" in app_css


# ─────────────────────────────────────────────────────────────────────────
# Task 2: Phase 39 field-set group — the nine UI-SPEC Regression Checklist
# bullets, re-asserted here as permanent automated gates against the box-
# model relocation. Properties test_phase39_popover_ui_contract.py already
# asserts (type scale, color subset, spacing scale, separator snippet,
# two-column tenure rows, month-year granularity, apolitical guard) are
# referenced by comment, not duplicated.
# ─────────────────────────────────────────────────────────────────────────


def test_avatar_circle_and_initials_fallback_both_present() -> None:
    source = _source(POPOVER_PATH)
    assert "border-radius:50%" in source  # avatar image circle
    assert "showInitials" in source  # initials fallback branch


def test_full_name_and_conditional_role_pill_present() -> None:
    source = _source(POPOVER_PATH)
    assert "{speaker.full_name}</p>" in source
    assert "{#if speaker.role_name}" in source
    assert "{speaker.role_name}</span>" in source


def test_birth_death_line_halves_independently_guarded() -> None:
    source = _source(POPOVER_PATH)
    assert "{#if speaker.birthdate}b. " in source
    assert "{#if speaker.death_date}d. " in source
    assert "isBench && (speaker.birthdate || speaker.death_date)" in source


def test_advocate_descriptor_placeholder_present() -> None:
    source = _source(POPOVER_PATH)
    assert "{#if !isBench}" in source
    assert "Coming soon" in source


def test_bio_block_clamp_and_both_toggle_labels_present() -> None:
    source = _source(POPOVER_PATH)
    assert "-webkit-line-clamp:3" in source
    assert "Read more" in source
    assert "Show less" in source


def test_tenure_list_office_row_and_conditional_second_row_present() -> None:
    source = _source(POPOVER_PATH)
    assert "officeTitle(t.office)" in source
    assert "tenureRange(t.start_date, t.end_date)" in source
    assert "{#if t.appointed_by || t.reason_left}" in source


def test_exactly_four_internal_hairline_dividers() -> None:
    source = _source(POPOVER_PATH)
    divider = "border-top:1px solid #334155;"
    count = source.count(divider)
    assert count == 4, f"expected exactly 4 section dividers, found {count}"


def test_popover_card_padding_still_present() -> None:
    body = _css_rule_body(_source(POPOVER_PATH), ".popover-card")
    assert "padding: 24px" in body


def test_width_bounds_present_on_popover_content_tag() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "min-width: 300px" in tag
    assert "max-width: 400px" in tag


# ─────────────────────────────────────────────────────────────────────────
# Task 2: boundary group — EDGE boundary truth (BUG-02)
# ─────────────────────────────────────────────────────────────────────────


def test_max_height_is_two_branch_min_form_with_both_operands_intact() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "max-height: min(560px, 80vh)" in tag
    assert "560px" in tag
    assert "80vh" in tag


def test_overflow_declaration_is_scrolling_not_clipping() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "overflow-y: auto" in tag
    assert "overflow-y: hidden" not in tag
    assert "overflow: hidden" not in tag
    assert "overflow-y: clip" not in tag


def test_boundary_declarations_share_the_same_tag_as_border_and_radius() -> None:
    # The structural invariant that makes the threshold behavior continuous:
    # the scrolling declarations and the visible-boundary declarations must
    # be on the same extracted tag text (one element), not split across two.
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "max-height: min(560px, 80vh)" in tag
    assert "overflow-y: auto" in tag
    assert "border: 1px solid #334155" in tag
    assert "border-radius: 8px" in tag


# ─────────────────────────────────────────────────────────────────────────
# Task 2: precision group — EDGE precision truth (BUG-02)
# ─────────────────────────────────────────────────────────────────────────


def test_global_border_box_rule_covers_universal_selector_and_pseudo_elements() -> None:
    app_css = _source(APP_CSS_PATH)
    assert "*, *::before, *::after" in app_css
    assert "box-sizing: border-box" in app_css


def test_no_box_sizing_override_on_popover_content_or_card() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    card_body = _css_rule_body(_source(POPOVER_PATH), ".popover-card")
    assert "box-sizing" not in tag
    assert "box-sizing" not in card_body


# ─────────────────────────────────────────────────────────────────────────
# Task 2: prohibitions group
# ─────────────────────────────────────────────────────────────────────────


def test_apolitical_guard_still_holds_after_relocation() -> None:
    # Mirrors test_phase39_popover_ui_contract.py's apolitical guard list —
    # the relocation must not reintroduce any of these.
    source = _source(POPOVER_PATH)
    for literal in ("Republican", "Democratic", "Federalist", "Whig"):
        assert literal not in source, f"party literal {literal!r} must never appear"
    assert "reason_left ===" not in source
    assert "reason_left ==" not in source
    assert "appointing_president_party ===" not in source
    assert "{@html" not in source


def test_no_scrollbar_hiding_declaration_in_either_file() -> None:
    popover_source = _source(POPOVER_PATH)
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    forbidden = ("overflow-y: hidden", "overflow: hidden", "scrollbar-width: none")
    for literal in forbidden:
        assert literal not in popover_source
        assert literal not in page_tag


def test_relocated_colors_are_a_subset_of_the_documented_token_set() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    colors = set(re.findall(r"#[0-9a-fA-F]{6}", tag))
    allowed = {"#1e293b", "#334155", "#e2e8f0", "#94a3b8", "#93c5fd", "#0f1117"}
    offenders = colors - allowed
    assert not offenders, f"colors outside app.css token set: {offenders}"
    # The tag must actually declare the two relocated colors, not merely
    # avoid declaring forbidden ones.
    assert "#1e293b" in colors
    assert "#334155" in colors
