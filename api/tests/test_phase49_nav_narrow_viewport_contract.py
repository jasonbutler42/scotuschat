"""
Phase 49 Plan 12 — computed page-chrome sweep for narrow-viewport nav overflow
(G-49-5c).

EVERY assertion in this module is a SOURCE-TEXT assertion. Source text cannot
observe layout. Three source-text gates in `test_phase49_review_ui_contract.py`
were correctly green about what they asserted (both queue tables, the status
segment group, and the dashboard grid were genuinely contained) WHILE THE PAGE
STILL VISIBLY SCROLLED SIDEWAYS — because `AdminSubNav.svelte`, a fourth
component nobody had thought to grep, was never in any assertion's field of
view. That is how G-49-5c survived 49-08. Therefore the behavioural claim "no
admin page scrolls horizontally at 375px" is closed ONLY by the real-browser
measurement recorded in 49-12-SUMMARY.md or by the operator's own eye —
NEVER by this module going green. A green run here proves declarations are
present in source; it proves nothing about the rendered page.

Design premise: this module does not enumerate the files it checks. Hand
enumeration is exactly what missed AdminSubNav — a human grepped for nav-like
components and stopped at three. Instead, `compute_chrome_set()` COMPUTES the
set of page-chrome files structurally, so a fifth undiscovered offender would
be swept in by construction rather than by someone remembering to add it.

A non-degeneracy guard exists because a computed set that silently collapses
to empty (regex drift, a renamed directory, an import syntax the walker
doesn't recognise) would make the live sweep pass VACUOUSLY — the same
false-green failure this whole plan exists to prevent. See
`test_non_degeneracy_guard_rejects_an_artificially_emptied_chrome_set` and
`test_walker_discovers_the_three_known_chrome_components`.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
ROUTES_DIR = ROOT / "app" / "src" / "routes"
COMPONENTS_DIR = ROOT / "app" / "src" / "lib" / "components"

ADMIN_SUBNAV_PATH = COMPONENTS_DIR / "AdminSubNav.svelte"
TOPNAV_PATH = COMPONENTS_DIR / "TopNav.svelte"
MOBILE_NAV_BAR_PATH = COMPONENTS_DIR / "MobileNavBar.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_script_and_style(source: str) -> str:
    source = re.sub(r"<script[^>]*>.*?</script>", "", source, flags=re.DOTALL)
    source = re.sub(r"<style[^>]*>.*?</style>", "", source, flags=re.DOTALL)
    return source


# ─────────────────────────────────────────────────────────────────────────
# Piece one: the chrome-set walker. Computes, never enumerates.
# ─────────────────────────────────────────────────────────────────────────

_IMPORT_RE = re.compile(
    r"""import\s+\w+\s+from\s+['"]\$lib/components/([A-Za-z0-9_]+\.svelte)['"]"""
)


def _imported_component_paths(source: str) -> set[Path]:
    """Every `$lib/components/*.svelte` import in a <script> block."""
    return {COMPONENTS_DIR / m.group(1) for m in _IMPORT_RE.finditer(source)}


def _first_markup_tag(source: str) -> str | None:
    """
    The first HTML tag name remaining after stripping <script> and <style>
    blocks. Svelte control-flow (`{#if}`, `{#each}`) is not a tag, so a
    component that opens with `{#if ...}<nav>` (MobileNavBar) still reports
    `nav` here — the walker looks for the first *tag*, not the first line.
    """
    stripped = _strip_script_and_style(source)
    match = re.search(r"<([a-zA-Z][a-zA-Z0-9]*)", stripped)
    return match.group(1).lower() if match else None


def compute_chrome_set() -> set[Path]:
    """
    The union of:
      (i)  every $lib/components/*.svelte transitively imported by any
           app/src/routes/**/+layout.svelte — this is what puts AdminSubNav
           in the set BY CONSTRUCTION, via the same edge
           (app/src/routes/admin/+layout.svelte importing it) that makes one
           component's overflow every admin page's overflow.
      (ii) every $lib/components/*.svelte whose first markup element is a
           <nav> — this catches nav chrome mounted by a page rather than a
           layout (MobileNavBar, SectionRail).
    """
    discovered: set[Path] = set()

    frontier: list[Path] = []
    for layout_path in ROUTES_DIR.glob("**/+layout.svelte"):
        frontier.extend(_imported_component_paths(_source(layout_path)))

    while frontier:
        candidate = frontier.pop()
        if candidate in discovered or not candidate.exists():
            continue
        discovered.add(candidate)
        frontier.extend(_imported_component_paths(_source(candidate)))

    for component_path in COMPONENTS_DIR.glob("*.svelte"):
        if _first_markup_tag(_source(component_path)) == "nav":
            discovered.add(component_path)

    return discovered


# ─────────────────────────────────────────────────────────────────────────
# Piece two: the detector. A pure function — no file I/O, no Path.
# ─────────────────────────────────────────────────────────────────────────

_WRAP_ESCAPES = {"flex-wrap:wrap", "flex-wrap:wrap-reverse"}
_OVERFLOW_ESCAPES = {"overflow-x:auto", "overflow-x:scroll"}


def _normalize(declaration: str) -> str:
    """
    Remove ALL whitespace before matching. 49-08's SUMMARY records that
    `margin:6px` vs `margin: 6px` already produced one false negative this
    phase — `display:flex` and `display: flex` must both be recognised here.
    """
    return re.sub(r"\s+", "", declaration)


def detect_unescaped_flex_row(declarations: set[str]) -> str | None:
    """
    Given every CSS declaration string that applies to ONE element, return
    None if the element is safe, or a violation string naming which escapes
    were absent otherwise.

    An element is a violation only if it declares `display: flex` (in any
    whitespace form) AND has none of: `flex-wrap: wrap|wrap-reverse`,
    `overflow-x: auto|scroll`, or `position: fixed` together with both a
    `left:` and a `right:` declaration (MobileNavBar's shape).
    """
    normalized = {_normalize(d) for d in declarations}
    if "display:flex" not in normalized:
        return None

    has_wrap = bool(normalized & _WRAP_ESCAPES)
    has_overflow = bool(normalized & _OVERFLOW_ESCAPES)
    has_fixed_lr = (
        "position:fixed" in normalized
        and any(d.startswith("left:") for d in normalized)
        and any(d.startswith("right:") for d in normalized)
    )
    if has_wrap or has_overflow or has_fixed_lr:
        return None

    missing = []
    if not has_wrap:
        missing.append("flex-wrap: wrap|wrap-reverse")
    if not has_overflow:
        missing.append("overflow-x: auto|scroll")
    if not has_fixed_lr:
        missing.append("position: fixed with left + right")
    return "display:flex with no escape found (missing all of: " + "; ".join(missing) + ")"


# ─────────────────────────────────────────────────────────────────────────
# Piece three: per-file collector. Groups inline styles AND <style>-block
# rules by TAG NAME so the two are unioned before the detector runs — this
# is what makes MobileNavBar pass honestly (its `display: flex` lives in a
# media-query rule while its `overflow-x: auto` lives inline; checking
# either alone gives the wrong answer).
#
# NOTE: grouping is by TAG NAME ONLY. Exact for today's chrome components,
# each of which has a single element per tag. If a chrome component ever
# grows a class- or id-based selector with per-instance CSS, this grouping
# will need to become selector-aware rather than tag-aware.
# ─────────────────────────────────────────────────────────────────────────

_OPENING_TAG_RE = re.compile(
    r"<([a-zA-Z][a-zA-Z0-9]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)>"
)
_STYLE_ATTR_RE = re.compile(r'style="([^"]*)"', re.DOTALL)
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL)
_BARE_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _split_declarations(block: str) -> set[str]:
    return {d.strip() for d in block.split(";") if d.strip()}


def _extract_inline_style_groups(markup: str) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for tag_match in _OPENING_TAG_RE.finditer(markup):
        tag = tag_match.group(1).lower()
        style_match = _STYLE_ATTR_RE.search(tag_match.group(2))
        if not style_match:
            continue
        groups.setdefault(tag, set()).update(_split_declarations(style_match.group(1)))
    return groups


def _extract_style_block_groups(source_with_style: str) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for style_block in _STYLE_BLOCK_RE.finditer(source_with_style):
        for rule_match in _BARE_RULE_RE.finditer(style_block.group(1)):
            selector = rule_match.group(1).strip()
            if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", selector):
                continue  # not a bare tag selector — out of scope (TAG NAME ONLY)
            groups.setdefault(selector.lower(), set()).update(
                _split_declarations(rule_match.group(2))
            )
    return groups


def collect_element_groups(path: Path) -> dict[str, set[str]]:
    """
    For one chrome file, the declarations that apply to each tag name,
    unioning inline `style="..."` attributes with same-tag `<style>`-block
    rules (including rules nested inside `@media`).
    """
    source = _source(path)
    script_stripped = re.sub(r"<script[^>]*>.*?</script>", "", source, flags=re.DOTALL)
    markup_only = re.sub(r"<style[^>]*>.*?</style>", "", script_stripped, flags=re.DOTALL)

    combined: dict[str, set[str]] = {}
    for tag, decls in _extract_inline_style_groups(markup_only).items():
        combined.setdefault(tag, set()).update(decls)
    for tag, decls in _extract_style_block_groups(script_stripped).items():
        combined.setdefault(tag, set()).update(decls)
    return combined


# ─────────────────────────────────────────────────────────────────────────
# Non-degeneracy guard. Factored into a standalone assertion function so it
# can be exercised both against the real walker AND against an artificially
# emptied set, proving the guard rejects degeneracy independent of whether
# today's real walker happens to behave.
# ─────────────────────────────────────────────────────────────────────────


def _assert_non_degenerate(chrome_set: set[Path]) -> None:
    assert len(chrome_set) >= 3, (
        f"chrome-set walker discovered only {len(chrome_set)} file(s) "
        f"({sorted(p.name for p in chrome_set)}) — regex drift may have "
        f"emptied the walker, which would make the live sweep pass "
        f"vacuously"
    )
    required = {ADMIN_SUBNAV_PATH, TOPNAV_PATH, MOBILE_NAV_BAR_PATH}
    missing = required - chrome_set
    assert not missing, (
        f"chrome-set walker failed to discover: {sorted(p.name for p in missing)} "
        f"— the sweep would silently skip these components"
    )


# ─────────────────────────────────────────────────────────────────────────
# Detector unit tests (<behavior> list)
# ─────────────────────────────────────────────────────────────────────────

# The historical pre-fix AdminSubNav <nav> declaration set, frozen here as a
# literal fixture (not read from git history). This is the permanent,
# non-destructive proof that this gate catches this exact bug — it stays
# green forever without anyone having to break the component again.
HISTORICAL_PRE_FIX_ADMIN_SUBNAV_NAV_DECLARATIONS = {
    "background-color: #1e293b",
    "border-bottom: 1px solid #334155",
    "padding: 12px 24px",
    "display: flex",
    "align-items: center",
    "gap: 16px",
}


def test_detector_flags_the_historical_pre_fix_admin_subnav_declaration_set() -> None:
    violation = detect_unescaped_flex_row(HISTORICAL_PRE_FIX_ADMIN_SUBNAV_NAV_DECLARATIONS)
    assert violation is not None, (
        "expected a violation on the historical pre-fix AdminSubNav <nav> "
        "declaration set (display:flex, no flex-wrap, no overflow-x) — this "
        "is the exact bug G-49-5c reported"
    )


def test_detector_clears_the_same_set_once_flex_wrap_is_added() -> None:
    fixed = HISTORICAL_PRE_FIX_ADMIN_SUBNAV_NAV_DECLARATIONS | {"flex-wrap: wrap"}
    assert detect_unescaped_flex_row(fixed) is None


def test_detector_accepts_overflow_x_auto_as_an_escape() -> None:
    declarations = {"display: flex", "overflow-x: auto"}
    assert detect_unescaped_flex_row(declarations) is None


def test_detector_accepts_position_fixed_with_left_and_right_as_an_escape() -> None:
    declarations = {"display: flex", "position: fixed", "left: 0", "right: 0"}
    assert detect_unescaped_flex_row(declarations) is None


def test_detector_ignores_missing_whitespace_after_the_colon() -> None:
    """`display:flex` with no space must still be detected as display:flex."""
    violation = detect_unescaped_flex_row({"display:flex"})
    assert violation is not None


def test_detector_returns_none_when_display_flex_is_entirely_absent() -> None:
    assert detect_unescaped_flex_row({"position: sticky", "top: 0"}) is None


# ─────────────────────────────────────────────────────────────────────────
# Chrome-set walker tests
# ─────────────────────────────────────────────────────────────────────────


def test_walker_discovers_the_three_known_chrome_components() -> None:
    chrome_set = compute_chrome_set()
    assert ADMIN_SUBNAV_PATH in chrome_set, (
        "AdminSubNav must be discovered via rule (i) — it is imported by "
        "app/src/routes/admin/+layout.svelte"
    )
    assert TOPNAV_PATH in chrome_set, (
        "TopNav must be discovered via rule (i) — it is imported by both "
        "+layout.svelte files"
    )
    assert MOBILE_NAV_BAR_PATH in chrome_set, (
        "MobileNavBar must be discovered via rule (ii) — its first markup "
        "element is a <nav>"
    )
    assert len(chrome_set) >= 3


def test_non_degeneracy_guard_passes_on_the_real_walker() -> None:
    _assert_non_degenerate(compute_chrome_set())


def test_non_degeneracy_guard_rejects_an_artificially_emptied_chrome_set() -> None:
    """
    Proves the guard itself is load-bearing: an empty (or too-small)
    discovered set MUST fail the assertion, not silently pass. This
    substitutes a stand-in empty set for the discovered set to prove the
    guard's assertion logic rejects degeneracy — independent of whether
    today's real walker happens to work. (The real walker was also manually
    broken and observed to fail this same guard during Task 2's execution;
    see 49-12-SUMMARY.md.)
    """
    with pytest.raises(AssertionError):
        _assert_non_degenerate(set())
    with pytest.raises(AssertionError):
        _assert_non_degenerate({ADMIN_SUBNAV_PATH, TOPNAV_PATH})  # missing MobileNavBar


# ─────────────────────────────────────────────────────────────────────────
# The live sweep. This is the assertion that must be run BEFORE TopNav is
# fixed, and must fail naming TopNav.svelte — see 49-12-SUMMARY.md for the
# quoted pre-fix failure message.
# ─────────────────────────────────────────────────────────────────────────


def test_no_chrome_component_has_an_unescaped_flex_row_at_narrow_viewport() -> None:
    _assert_non_degenerate(compute_chrome_set())
    failures = []
    for path in sorted(compute_chrome_set()):
        for tag, declarations in collect_element_groups(path).items():
            violation = detect_unescaped_flex_row(declarations)
            if violation is not None:
                failures.append(f"{path.name}:<{tag}> — {violation}")
    assert not failures, "unescaped display:flex chrome row(s) found:\n" + "\n".join(failures)
