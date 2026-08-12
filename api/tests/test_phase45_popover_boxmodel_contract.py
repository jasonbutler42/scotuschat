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
