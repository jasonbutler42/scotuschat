"""
Phase 49 Plan 05 — `/admin/review` queue screen source-contract module.

This is a PURE source-TEXT contract module, in the established
`test_phase38_people_ui_contract.py` / `test_phase49_cleanup_contract.py`
style: no database, no `node` subprocess, no Svelte component runner. It
proves the relevant strings/structures are PRESENT IN SOURCE — never that
the runtime behaves as intended. A `$state` proxy trap already let 28
green source-contract tests pass against a fully broken button in Phase 48
(plan 48-10, see the project memory note on this exact failure mode) — the
Task 2 `<human-check>` browser walkthrough recorded in
`49-05-SUMMARY.md` is the real behavioral evidence for this screen, not
the assertions below.

Sibling module `test_phase49_cleanup_contract.py` covers plan 49-03's
scope (popover/status-card/help-page) — kept separate, not merged here.

Backstop coverage (49-05-PLAN.md's four held-out UI-SPEC backstop
statements): E1 zero-one-many and E5 zero-one-many are rendering-shape
statements and live here; E6 partial and E6 long-text are data-shape
statements that need a real seeded discrepancy row and live in
`api/tests/test_admin_review_service.py` instead (per the plan's own
Task 3 split).
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]

REVIEW_PAGE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "review" / "+page.svelte"
ADMIN_SUBNAV_PATH = ROOT / "app" / "src" / "lib" / "components" / "AdminSubNav.svelte"
ADMIN_DASHBOARD_PATH = ROOT / "app" / "src" / "routes" / "admin" / "+page.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


REVIEW_SOURCE = _source(REVIEW_PAGE_PATH)


# ─────────────────────────────────────────────────────────────────────────
# Tabs, status segments, review-state/tier filter option labels (E3, E4)
# ─────────────────────────────────────────────────────────────────────────


def test_both_tab_labels_present() -> None:
    assert ">Arguments</button>" in REVIEW_SOURCE
    assert ">People</button>" in REVIEW_SOURCE


def test_all_five_status_segment_labels_present() -> None:
    for label in ("All", "Candidate", "Draft", "Published", "Unpublished"):
        assert f">{label}<" in REVIEW_SOURCE, f"missing status segment label {label!r}"


def test_trust_tier_and_review_state_select_options_present() -> None:
    for option in ("All tiers", "Verified", "Trusted", "Provisional", "Uncertain"):
        assert option in REVIEW_SOURCE
    for option in ("All review states", "Unreviewed", "Needs review", "Confirmed", "Edited"):
        assert option in REVIEW_SOURCE


# ─────────────────────────────────────────────────────────────────────────
# Badge colors (UI-SPEC § Color) — all five new review_state/discrepancy
# hexes present in a color lookup, each exactly once (no accidental
# duplication that would suggest a copy-paste drift from the formula).
# ─────────────────────────────────────────────────────────────────────────


def test_all_five_review_state_and_discrepancy_hexes_present_exactly_once() -> None:
    for hex_value in ("#475569", "#fbbf24", "#2dd4bf", "#e879f9", "#fb7185"):
        count = REVIEW_SOURCE.count(hex_value)
        assert count == 1, f"{hex_value} appears {count} times, expected exactly 1"


# ─────────────────────────────────────────────────────────────────────────
# Expand/collapse (E1 populated) — aria-expanded present, no native
# disclosure element used to wrap a <tr>.
# ─────────────────────────────────────────────────────────────────────────


def test_aria_expanded_present_and_no_native_details_element() -> None:
    assert "aria-expanded" in REVIEW_SOURCE
    assert "<details" not in REVIEW_SOURCE


# ─────────────────────────────────────────────────────────────────────────
# Overflow/long-text discipline (E1/E2/E3/E5/E6/E7)
# ─────────────────────────────────────────────────────────────────────────


def test_flex_wrap_present_on_filter_row_and_action_row() -> None:
    assert REVIEW_SOURCE.count("flex-wrap: wrap") >= 2


def test_no_text_overflow_anywhere_in_the_review_screen() -> None:
    assert "text-overflow" not in REVIEW_SOURCE


def test_no_class_attribute_anywhere_inline_styles_only() -> None:
    assert "class=" not in REVIEW_SOURCE


# ─────────────────────────────────────────────────────────────────────────
# Fixed action labels (E7 long-text)
# ─────────────────────────────────────────────────────────────────────────


def test_four_action_labels_present_verbatim() -> None:
    for label in (
        "Confirm",
        "Confirm as unattributable",
        "Re-flag for review",
        "Edit pipeline run",
        "Edit argument",
    ):
        assert label in REVIEW_SOURCE, f"missing action label {label!r}"


# ─────────────────────────────────────────────────────────────────────────
# Empty-state copy (E1/E2/E9)
# ─────────────────────────────────────────────────────────────────────────


def test_both_empty_state_body_strings_present() -> None:
    assert "No arguments currently need review." in REVIEW_SOURCE
    assert "No people currently need review." in REVIEW_SOURCE
    assert "All caught up" in REVIEW_SOURCE


# ─────────────────────────────────────────────────────────────────────────
# Entry points (D-27, D-30)
# ─────────────────────────────────────────────────────────────────────────


def test_subnav_contains_review_link() -> None:
    subnav_source = _source(ADMIN_SUBNAV_PATH)
    assert '/admin/review' in subnav_source
    assert re.search(r'href="/admin/review"[^>]*>\s*Review\s*</a>', subnav_source), (
        "expected a Review link in AdminSubNav.svelte"
    )


# ─────────────────────────────────────────────────────────────────────────
# G-49-5a (49-08): the dashboard StatCard grid's track-fit arithmetic. UAT
# sub-item 5 (five cards in one row at desktop width) and sub-item 7 (no
# horizontal scroll at 375px) were reported as being in direct conflict —
# true only under a FIXED five-column grid. `_tracks_that_fit` is the CSS
# Grid `auto-fit` track-count formula; encoding it here makes both UAT
# sub-items executable rather than commented, so raising the floor or the
# gap past the point where five tracks fit at the desktop width fails a
# test instead of surfacing six weeks later in a browser.
# ─────────────────────────────────────────────────────────────────────────

DASHBOARD_DESKTOP_INNER_PX = 812  # max-width: 860px minus 2 x 24px padding
DASHBOARD_NARROW_INNER_PX = 327  # a 375px viewport minus the same padding


def _tracks_that_fit(inner_px: int, floor_px: int, gap_px: int) -> int:
    """
    The CSS Grid `repeat(auto-fit, minmax(floor_px, 1fr))` track-count
    formula: how many tracks of at least `floor_px` (separated by
    `gap_px`) fit inside `inner_px`.
    """
    return max(1, (inner_px + gap_px) // (floor_px + gap_px))


def test_dashboard_has_five_column_grid_and_five_statcards() -> None:
    """
    Rewritten by 49-08 (G-49-5a): the fixed five-column literal this test
    used to key on is deleted by that plan's own edit, so this test cannot
    be red-gated the way the two tests below can — it is a rewrite, not a
    new gate. The fixed-column absence assertions are now regression
    guards (a future contributor reintroducing a fixed column count would
    fail here), and the five-in-one-row guarantee itself now lives in
    `test_dashboard_grid_track_floor_fits_five_cards_at_desktop_and_reflows_at_375px`
    below, as executable arithmetic rather than a string match.
    """
    dashboard_source = _source(ADMIN_DASHBOARD_PATH)
    assert "grid-template-columns: repeat(5, 1fr)" not in dashboard_source
    assert "repeat(4, 1fr)" not in dashboard_source
    assert dashboard_source.count("<StatCard") == 5
    assert 'title="Review queue"' in dashboard_source
    assert "gap: 32px" in dashboard_source


def test_dashboard_grid_track_floor_fits_five_cards_at_desktop_and_reflows_at_375px() -> None:
    """
    UAT sub-items 5 and 7 were reported as being in direct conflict; the
    conflict exists only under a fixed-column grid. This test is what
    keeps both true: it parses the auto-fit floor and the gap out of the
    dashboard source and asserts five filled tracks at the 812px desktop
    inner width (sub-item 5) and at most two tracks — each still at least
    as wide as the floor — at the 327px 375px-viewport inner width
    (sub-item 7). Raising the floor or the gap far enough to break either
    end fails here.
    """
    dashboard_source = _source(ADMIN_DASHBOARD_PATH)
    floor_match = re.search(r"repeat\(auto-fit,\s*minmax\((\d+)px,\s*1fr\)\)", dashboard_source)
    assert floor_match, (
        "expected a `repeat(auto-fit, minmax(<n>px, 1fr))` grid-template-columns "
        "pattern in the dashboard source — none found"
    )
    gap_match = re.search(r"gap:\s*(\d+)px", dashboard_source)
    assert gap_match, "expected a `gap: <n>px` declaration in the dashboard source — none found"

    floor = int(floor_match.group(1))
    gap = int(gap_match.group(1))

    assert _tracks_that_fit(DASHBOARD_DESKTOP_INNER_PX, floor, gap) == 5, (
        f"floor={floor}px, gap={gap}px does not yield 5 filled tracks at "
        f"{DASHBOARD_DESKTOP_INNER_PX}px — UAT sub-item 5 would regress"
    )

    narrow_tracks = _tracks_that_fit(DASHBOARD_NARROW_INNER_PX, floor, gap)
    assert narrow_tracks <= 2, (
        f"floor={floor}px, gap={gap}px yields {narrow_tracks} tracks at "
        f"{DASHBOARD_NARROW_INNER_PX}px — expected at most 2"
    )
    per_track_width = (DASHBOARD_NARROW_INNER_PX - gap * (narrow_tracks - 1)) / narrow_tracks
    assert per_track_width >= floor, (
        f"per-track width {per_track_width}px at {DASHBOARD_NARROW_INNER_PX}px is "
        f"narrower than the {floor}px floor — UAT sub-item 7 would regress"
    )


def test_dashboard_grid_uses_no_media_query_and_no_class_attribute() -> None:
    """
    D-29 locks the inline-style idiom and this plan introduces no
    responsive breakpoint logic — the auto-fit track floor itself is what
    makes the grid responsive, with no @media query and no class=
    anywhere in the grid's style block.
    """
    dashboard_source = _source(ADMIN_DASHBOARD_PATH)
    assert "@media" not in dashboard_source
    grid_match = re.search(
        r'<div\s*\n?\s*style="[^"]*grid-template-columns[^"]*"',
        dashboard_source,
        re.DOTALL,
    )
    assert grid_match, "expected to find the grid <div style=...> block"
    assert "class=" not in grid_match.group(0)


# ─────────────────────────────────────────────────────────────────────────
# Backstop E1 (zero-one-many): the Copywriting Contract's plural rule
# renders "1 participant needs review" at exactly one (singular subject,
# singular verb) and "{N} participants need review" otherwise (plural
# subject, plural verb) — locked to a `=== 1` comparison (not a hardcoded
# plural string) so a hardcoded plural cannot pass this assertion. This
# also closes G-49-4b (domain noun) and G-49-5b (subject-verb agreement)
# on this line.
# ─────────────────────────────────────────────────────────────────────────


def test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one() -> None:
    assert "function attentionCountText" in REVIEW_SOURCE
    # The strict-equality keying survives the noun/verb rewrite.
    assert "n === 1" in REVIEW_SOURCE
    assert "1 participant needs review" in REVIEW_SOURCE
    assert "participants need review" in REVIEW_SOURCE


# ─────────────────────────────────────────────────────────────────────────
# G-49-4a: the row action anchor's label must branch on the same
# condition as its href, so a static label cannot serve two destinations.
# ─────────────────────────────────────────────────────────────────────────


def test_action_link_label_branches_on_the_same_condition_as_the_href() -> None:
    """
    G-49-4a. Source-text assertion only — proves the label helper exists,
    is wired into the anchor's text content, and tests the identical
    condition as argumentEditHref, not that the rendered anchor is
    visually correct.
    """
    assert "function argumentEditLabel" in REVIEW_SOURCE
    match = re.search(
        r"<a\s+href=\{argumentEditHref\(item\)\}.*?\{argumentEditLabel\(item\)\}.*?</a>",
        REVIEW_SOURCE,
        re.DOTALL,
    )
    assert match, (
        "expected one anchor whose href is argumentEditHref(item) and "
        "whose text content is {argumentEditLabel(item)}"
    )
    # One `admin_job_id !== null` occurrence per helper — the parity claim.
    assert REVIEW_SOURCE.count("admin_job_id !== null") == 2


# ─────────────────────────────────────────────────────────────────────────
# G-49-4b: the internal rollup noun must never render as operator-facing
# copy on the review page. This gate is the reason the wire code and API
# schema rename was scoped OUT of this plan (49-07-PLAN.md
# <planner_decisions>) — it is structural-only (source text, not rendered
# DOM), and it deliberately permits the wire code (`no_constituents`) and
# the property/loop-variable accessors (`item.constituents`,
# `as constituent`, `constituent.<field>`) that this page still uses
# internally.
# ─────────────────────────────────────────────────────────────────────────


def test_review_page_rendered_copy_uses_the_domain_noun() -> None:
    allowed_pattern = re.compile(
        r"no_constituents|item\.constituents|as constituent\b|constituent\.[A-Za-z_]+"
    )
    for lineno, line in enumerate(REVIEW_SOURCE.splitlines(), start=1):
        if "constituent" not in line.lower():
            continue
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("<!--"):
            continue
        remainder = allowed_pattern.sub("", line)
        assert "constituent" not in remainder.lower(), (
            f"line {lineno} renders the internal rollup noun as operator "
            f"copy: {line!r}"
        )


# ─────────────────────────────────────────────────────────────────────────
# Backstop E5 (zero-one-many): one constituent block or many share ONE
# layout path — a single {#each} over the constituent list, with the
# container declaring the 16px (md) block-spacing gap.
# ─────────────────────────────────────────────────────────────────────────


def test_backstop_E5_constituent_blocks_share_one_each_loop_with_16px_gap() -> None:
    match = re.search(
        r'<div style="[^"]*gap: 16px;[^"]*">\s*\{#each item\.constituents as constituent',
        REVIEW_SOURCE,
    )
    assert match, (
        "expected a single 16px-gap container immediately wrapping the "
        "{#each item.constituents} loop — one layout path for one block "
        "or many"
    )


# ─────────────────────────────────────────────────────────────────────────
# G-49-5a (49-08): horizontal-scroll containment. Three overflow-x: auto
# wrappers — the two queue tables and the status segment group's outer
# wrapper — so wide content scrolls inside itself instead of pushing the
# page body sideways at a 375px viewport. Source-text structural
# assertions only; the behavioural evidence is Task 3's <human-check>
# browser pass.
# ─────────────────────────────────────────────────────────────────────────


def test_both_queue_tables_are_wrapped_in_an_overflow_container() -> None:
    """
    Exactly three overflow-x: auto declarations exist in the file (the two
    queue tables plus the status segment group's outer wrapper), and each
    <table opening tag is immediately preceded — modulo whitespace and an
    optional HTML comment — by a div whose inline style declares
    overflow-x: auto.
    """
    assert REVIEW_SOURCE.count("overflow-x: auto") == 3
    table_wrapper_pattern = re.compile(
        r'<div style="overflow-x: auto;">\s*(?:<!--.*?-->\s*)?<table',
        re.DOTALL,
    )
    matches = table_wrapper_pattern.findall(REVIEW_SOURCE)
    assert len(matches) == 2, (
        f"expected both <table> elements to be immediately preceded by an "
        f"overflow-x: auto wrapper div, found {len(matches)}"
    )


def test_status_segment_group_can_shrink_and_scroll() -> None:
    """
    A flex item's default min-width: auto resolves to its content's
    min-content size — without min-width: 0 on the outer wrapper, the
    overflow-x: auto declaration on that same wrapper never engages
    because the item refuses to shrink below the five buttons' combined
    natural width. width: max-content on the inner group keeps the five
    segments at their natural widths so the group scrolls as a unit
    instead of the buttons compressing. The outer wrapper's min-width: 0
    must appear before the inner group's width: max-content in source.
    """
    assert "min-width: 0" in REVIEW_SOURCE
    assert "width: max-content" in REVIEW_SOURCE
    assert REVIEW_SOURCE.index("min-width: 0") < REVIEW_SOURCE.index("width: max-content"), (
        "expected the outer wrapper's min-width: 0 to appear before the "
        "inner group's width: max-content"
    )


# ─────────────────────────────────────────────────────────────────────────
# Phase 50 plan 50-04, Task 1: argument-level / lead-case-level discrepancy
# rendering. Structural source-text assertions only — the real behavioral
# evidence is Task 2's <human-check> browser walkthrough (see the project
# memory note on the $state-proxy-vs-grep-contract-test trap: a green
# assertion here does not by itself prove the render is correct).
# ─────────────────────────────────────────────────────────────────────────


def test_argument_discrepancies_referenced_at_least_three_times() -> None:
    assert REVIEW_SOURCE.count("argument_discrepancies") >= 3


def test_argument_discrepancies_iterated_with_keyed_each_on_id() -> None:
    assert "{#each item.argument_discrepancies as d (d.id)}" in REVIEW_SOURCE


def test_argument_discrepancies_render_both_existing_and_incoming_through_display_helper() -> None:
    match = re.search(
        r"\{#each item\.argument_discrepancies as d \(d\.id\)\}.*?\{/each\}",
        REVIEW_SOURCE,
        re.DOTALL,
    )
    assert match, "expected an {#each item.argument_discrepancies as d (d.id)} block"
    block = match.group(0)
    assert "discrepancyValueDisplay(d.existing_value)" in block
    assert "discrepancyValueDisplay(d.incoming_value)" in block


def test_argument_level_discrepancy_row_badge_conditioned_on_non_empty_list() -> None:
    assert "{#if item.argument_discrepancies.length > 0}" in REVIEW_SOURCE
    # At least two guards: the collapsed-row case-name badge and the
    # expanded-panel block, both keyed on the same non-empty-list condition.
    assert REVIEW_SOURCE.count("{#if item.argument_discrepancies.length > 0}") >= 2


def test_no_truncation_or_media_query_introduced_on_the_review_page() -> None:
    """
    49-UI-SPEC E1/E2 long-text and E6 overflow forbid truncation outright —
    truncating a discrepancy value could hide the exact disagreement the
    operator is being asked to adjudicate. D-29 locks the inline-style-only
    idiom; re-asserted here at the point of change since the new overflow
    containers are one small step from a clipping container. Note: unlike
    the two tests above, this assertion is a negative-space regression
    guard — it holds both before and after the G-49-5a edit because the
    forbidden patterns are being avoided, not introduced, so it cannot be
    observed RED the way the two structural tests above can.
    """
    assert "text-overflow" not in REVIEW_SOURCE
    assert "overflow: hidden" not in REVIEW_SOURCE
    assert "@media" not in REVIEW_SOURCE
    assert "class=" not in REVIEW_SOURCE
