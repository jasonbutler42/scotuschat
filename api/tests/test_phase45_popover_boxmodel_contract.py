"""
Phase 45 Plan 02 — BUG-02 / D-03(revised) speaker popover box-model contract.

Original D-03 moved the whole card's scroll onto `Popover.Content` (surface,
border, radius, width bounds, max-height, and overflow all on one element).
Live operator verification at the Phase 45 checkpoint found that still wrong:
the "person popover with bio examples" Figma frame (page "screen mockups for
GSD") shows the card growing to fit its content with NO outer scroll at all —
only the biography paragraph itself scrolls internally, capped at a fixed
150px, while the header/dates/tenures/footer stay at natural size below it.

This module locks that revised contract:
  - `Popover.Content` owns the surface color, border, radius, width bounds,
    and z-index — but NOT max-height or overflow-y (removed; no outer cap,
    per explicit operator direction at the checkpoint).
  - The bio `<p>` in `SpeakerPopover.svelte` is the sole scrolling element,
    scoped via the `.bio-scroll` class + inline `max-height:150px;
    overflow-y:auto;`, applied only in the expanded state. The collapsed
    state keeps its pre-existing 3-line clamp (~55px), unchanged.
  - `.bio-scroll` carries a thin custom scrollbar (explicit operator
    direction reversing the original "no custom scrollbar theming"
    prohibition) built only from the existing #334155 token color.

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


def _bio_paragraph_tag(source: str) -> str:
    """Return the text of the bio <p bind:this={bioEl} ...> opening tag."""
    match = re.search(r"<p\s+bind:this=\{bioEl\}", source)
    assert match, "could not find the bio `<p bind:this={bioEl}` opening tag"
    end = source.index(">", match.start())
    return source[match.start() : end + 1]


# ─────────────────────────────────────────────────────────────────────────
# Group A: Popover.Content — surface/border/radius/width-bounds retained,
# max-height and overflow-y removed (no outer cap, per operator direction).
# ─────────────────────────────────────────────────────────────────────────


def test_popover_content_owns_surface_border_radius_and_width_bounds() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "background-color: #1e293b" in tag
    assert "border: 1px solid #334155" in tag
    assert "border-radius: 8px" in tag
    assert "min-width: 300px" in tag
    assert "max-width: 400px" in tag
    assert "z-index: 50" in tag


def test_popover_content_has_no_max_height_or_overflow() -> None:
    # The outer card no longer owns any scroll or height ceiling — it sizes
    # to its content, exactly as every state in the Figma reference frame
    # ("person popover with bio examples", node 4230:121) does.
    tag = _popover_content_tag(_source(PAGE_PATH))
    assert "max-height" not in tag
    assert "overflow-y" not in tag
    assert "overflow:" not in tag


def test_popover_card_reduced_to_padding_and_display_only() -> None:
    body = _css_rule_body(_source(POPOVER_PATH), ".popover-card")
    assert "padding: 24px" in body
    assert "display: block" in body
    for relocated in (
        "background-color: #1e293b",
        "border: 1px solid #334155",
        "border-radius: 8px",
        "min-width: 300px",
        "max-width: 400px",
    ):
        assert relocated not in body, f"{relocated!r} must not be on .popover-card"


def test_no_box_sizing_override_introduced() -> None:
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    assert "box-sizing" not in page_tag
    app_css = _source(APP_CSS_PATH)
    assert "box-sizing: border-box" in app_css
    assert "*, *::before, *::after" in app_css


# ─────────────────────────────────────────────────────────────────────────
# Group B: bio-scoped scroll — the revised D-03. Only the bio paragraph
# scrolls, capped at 150px, only in the expanded state.
# ─────────────────────────────────────────────────────────────────────────


def test_bio_expanded_branch_caps_height_and_scrolls() -> None:
    source = _source(POPOVER_PATH)
    assert "max-height:150px" in source
    assert "overflow-y:auto" in source


def test_bio_collapsed_branch_keeps_three_line_clamp_unchanged() -> None:
    source = _source(POPOVER_PATH)
    assert "-webkit-line-clamp:3" in source
    assert "display:-webkit-box" in source
    assert "-webkit-box-orient:vertical" in source


def test_bio_scroll_class_applied_only_when_expanded() -> None:
    tag = _bio_paragraph_tag(_source(POPOVER_PATH))
    assert "class={bioExpanded ? 'bio-scroll' : ''}" in tag


def test_bio_scroll_cap_and_clamp_are_mutually_exclusive_in_the_ternary() -> None:
    # Region-scoped: the same conditional expression must not apply both the
    # scroll cap and the line-clamp at once — they are alternate branches of
    # one ternary keyed on bioExpanded.
    tag = _bio_paragraph_tag(_source(POPOVER_PATH))
    assert "bioExpanded ? 'max-height:150px;overflow-y:auto;' : " in tag


def test_popover_content_no_longer_shares_scroll_with_bio() -> None:
    # The structural invariant of the revision: exactly one element owns the
    # scroll (the bio paragraph), not two, and not the outer card.
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    assert "overflow-y" not in page_tag
    assert "150px" not in page_tag


# ─────────────────────────────────────────────────────────────────────────
# Group C: custom scrollbar theming — explicit operator direction at the
# Phase 45 checkpoint reverses the original "no custom scrollbar theming"
# prohibition, scoped narrowly to `.bio-scroll`.
# ─────────────────────────────────────────────────────────────────────────


def test_bio_scroll_has_thin_custom_scrollbar() -> None:
    source = _source(POPOVER_PATH)
    assert "scrollbar-width: thin" in source
    assert "scrollbar-color: #334155 transparent" in source
    assert "::-webkit-scrollbar" in source
    assert "::-webkit-scrollbar-track" in source
    assert "::-webkit-scrollbar-thumb" in source


def test_scrollbar_theming_scoped_to_bio_scroll_only() -> None:
    # The custom scrollbar rules must be declared under `.bio-scroll` — not
    # applied globally or to `.popover-card` — and must not appear on the
    # Popover.Content tag (which no longer scrolls at all).
    source = _source(POPOVER_PATH)
    scrollbar_block = source[source.index(".bio-scroll") :]
    assert "::-webkit-scrollbar" in scrollbar_block
    card_body = _css_rule_body(source, ".popover-card")
    assert "::-webkit-scrollbar" not in card_body
    assert "scrollbar-width" not in card_body
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    assert "::-webkit-scrollbar" not in page_tag
    assert "scrollbar-width" not in page_tag


def test_scrollbar_thumb_reuses_existing_token_color() -> None:
    # No new color introduced for the scrollbar thumb — it reuses the
    # existing #334155 divider/border token already in the app.css palette.
    source = _source(POPOVER_PATH)
    thumb_body = _css_rule_body(source, ".bio-scroll::-webkit-scrollbar-thumb")
    assert "#334155" in thumb_body
    colors_in_thumb = set(re.findall(r"#[0-9a-fA-F]{6}", thumb_body))
    assert colors_in_thumb == {"#334155"}


def test_no_scrollbar_hiding_declaration_anywhere() -> None:
    popover_source = _source(POPOVER_PATH)
    page_tag = _popover_content_tag(_source(PAGE_PATH))
    forbidden = ("overflow-y: hidden", "overflow: hidden", "scrollbar-width: none")
    for literal in forbidden:
        assert literal not in popover_source
        assert literal not in page_tag


# ─────────────────────────────────────────────────────────────────────────
# Group D: Phase 39 field-set group — the nine UI-SPEC Regression Checklist
# bullets, re-asserted here as permanent automated gates against the box-
# model revision. Properties test_phase39_popover_ui_contract.py already
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
# Group E: precision — box-sizing invariant unaffected by the revision.
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
# Group F: prohibitions
# ─────────────────────────────────────────────────────────────────────────


def test_apolitical_guard_still_holds_after_revision() -> None:
    source = _source(POPOVER_PATH)
    for literal in ("Republican", "Democratic", "Federalist", "Whig"):
        assert literal not in source, f"party literal {literal!r} must never appear"
    assert "reason_left ===" not in source
    assert "reason_left ==" not in source
    assert "appointing_president_party ===" not in source
    assert "{@html" not in source


def test_relocated_colors_are_a_subset_of_the_documented_token_set() -> None:
    tag = _popover_content_tag(_source(PAGE_PATH))
    colors = set(re.findall(r"#[0-9a-fA-F]{6}", tag))
    allowed = {"#1e293b", "#334155", "#e2e8f0", "#94a3b8", "#93c5fd", "#0f1117"}
    offenders = colors - allowed
    assert not offenders, f"colors outside app.css token set: {offenders}"
    assert "#1e293b" in colors
    assert "#334155" in colors
