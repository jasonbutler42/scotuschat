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
    for label in ("Confirm", "Confirm as unattributable", "Edit", "Re-flag for review"):
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
# renders "1 constituent needs review" at exactly one and
# "{N} constituents need review" otherwise — locked to a `=== 1`
# comparison (not a hardcoded plural string) so a hardcoded plural cannot
# pass this assertion.
# ─────────────────────────────────────────────────────────────────────────


def test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one() -> None:
    assert "function attentionCountText" in REVIEW_SOURCE
    # The plural branch must be keyed on a strict `=== 1` comparison, not a
    # hardcoded plural string — this exact substring is what a hardcoded
    # plural (e.g. always emitting "s") would NOT contain.
    assert "n === 1 ? '' : 's'" in REVIEW_SOURCE
    assert "need review" in REVIEW_SOURCE


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
