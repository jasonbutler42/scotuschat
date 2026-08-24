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


def test_dashboard_has_five_column_grid_and_five_statcards() -> None:
    dashboard_source = _source(ADMIN_DASHBOARD_PATH)
    assert dashboard_source.count("grid-template-columns: repeat(5, 1fr)") == 1
    assert "repeat(4, 1fr)" not in dashboard_source
    assert dashboard_source.count("<StatCard") == 5
    assert 'title="Review queue"' in dashboard_source


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
