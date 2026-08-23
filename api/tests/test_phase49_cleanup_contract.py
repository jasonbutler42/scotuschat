"""
Phase 49 Plan 03 — cleanup pass source-contract module.

Three independent folded todos closed in one plan: the create-person
popover's side inheritance and post-create selection (Task 1), the argument
Status card's mislabelled resolve timestamp (Task 2), and the Admin Help
page documenting the post-migration-0029 three-axis admin vocabulary
(Task 3). This module follows the established static source-contract
pattern used across the codebase where no frontend test framework exists
(see test_phase38_people_ui_contract.py, test_phase48_publish_override_ui_
contract.py) — no database, no `node` subprocess, no Svelte component
runner.

These are source-TEXT assertions. They prove the relevant strings/wiring
are present in the source, never that the runtime behaves as intended. A
`$state` proxy trap already let 28 green source-contract tests pass against
a fully broken button in Phase 48 (plan 48-10, see the project memory note
on this exact failure mode) — the `<human-check>` browser walkthroughs in
49-03-PLAN.md's Task 1 and Task 3 are the actual behavioral evidence for
this plan, not the tests below.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]

CREATE_PERSON_POPOVER_PATH = ROOT / "app" / "src" / "lib" / "components" / "CreatePersonPopover.svelte"
RESOLVE_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ResolveCard.svelte"
ARGUMENT_DETAIL_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.svelte"
HELP_PAGE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "help" / "+page.svelte"
SUBNAV_PATH = ROOT / "app" / "src" / "lib" / "components" / "AdminSubNav.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plain_function_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of a plain `function {name}(...) { ... }`
    declaration (not an arrow function or object property)."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*", source)
    assert match, f"could not find `function {name}(...)` in source"
    brace_start = source.index("{", match.end())
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : i + 1]
    raise AssertionError(f"unbalanced braces while extracting {name}")


# ─────────────────────────────────────────────────────────────────────────
# Task 1 (popover): initialSide prop declared/destructured/used in
# resetForm and the $state initializer; passed at the ResolveCard call
# site; s.comboQuery assigned in handlePersonCreated.
# ─────────────────────────────────────────────────────────────────────────


def test_popover_declares_initial_side_prop_in_interface() -> None:
    source = _source(CREATE_PERSON_POPOVER_PATH)
    assert re.search(r"initialSide\??\s*:\s*'BENCH'\s*\|\s*'ADVOCATE'", source)


def test_popover_destructures_initial_side_with_advocate_default() -> None:
    source = _source(CREATE_PERSON_POPOVER_PATH)
    assert re.search(r"initialSide\s*=\s*'ADVOCATE'\s*,", source)


def test_popover_side_state_initializes_from_initial_side() -> None:
    source = _source(CREATE_PERSON_POPOVER_PATH)
    assert re.search(
        r"let\s+side\s*=\s*\$state<'BENCH'\s*\|\s*'ADVOCATE'>\(initialSide\)", source
    )


def test_popover_reset_form_reassigns_initial_side_not_a_hardcoded_literal() -> None:
    source = _source(CREATE_PERSON_POPOVER_PATH)
    body = _plain_function_body(source, "resetForm")
    assert "side = initialSide;" in body
    assert "side = 'ADVOCATE';" not in body


def test_popover_resolved_side_untouched() -> None:
    # resolvedSide()'s Bench/defaultAdvocateSide mapping is a separate
    # concern from which radio starts selected — this plan does not touch it.
    source = _source(CREATE_PERSON_POPOVER_PATH)
    body = _plain_function_body(source, "resolvedSide")
    assert "side === 'BENCH' ? 'BENCH' : defaultAdvocateSide" in body


def test_popover_resolve_card_passes_initial_side_from_the_row_side() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert re.search(
        r"initialSide=\{side === 'BENCH' \? 'BENCH' : 'ADVOCATE'\}", source
    )
    # Passed exactly once (one CreatePersonPopover call site in this file).
    assert len(re.findall(r"initialSide=", source)) == 1


def test_popover_resolve_card_sets_combo_query_on_person_created() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _plain_function_body(source, "handlePersonCreated")
    assert "s.comboQuery = enriched.full_name;" in body
    # Must come after personId is set (mirrors the existing-person pick path's
    # ordering intent, though the field itself is independent of personId).
    person_id_idx = body.index("s.personId = enriched.id;")
    combo_query_idx = body.index("s.comboQuery = enriched.full_name;")
    assert combo_query_idx > person_id_idx


def test_popover_resolve_card_does_not_clear_side_bucket_tracking_on_create() -> None:
    # Explicitly preserved per the plan's action text: create-and-select does
    # not run the side-change clear.
    source = _source(RESOLVE_CARD_PATH)
    body = _plain_function_body(source, "handlePersonCreated")
    assert "lastSideBucket[participantId] = sideBucket(side);" in body
    assert "pendingSideOverrides[participantId] = side;" in body


# ─────────────────────────────────────────────────────────────────────────
# Task 2 (status_card): the Status card's resolved_at row reads "Resolved",
# never "Created".
# ─────────────────────────────────────────────────────────────────────────


def test_status_card_labels_resolved_at_as_resolved() -> None:
    source = _source(ARGUMENT_DETAIL_PATH)
    assert "Resolved {formatDateTime(data.argument.resolved_at)}" in source


def test_status_card_no_longer_calls_resolved_at_created() -> None:
    source = _source(ARGUMENT_DETAIL_PATH)
    assert "Created {formatDateTime(data.argument.resolved_at)}" not in source


def test_status_card_published_label_treatment_unchanged() -> None:
    # Plan 48-10's Published-label honesty fix stays exactly as shipped —
    # this plan changes nothing else on the card.
    source = _source(ARGUMENT_DETAIL_PATH)
    assert (
        "{data.argument.status === 'published' ? 'Published' : 'Last published'} "
        "{formatDateTime(data.argument.published_at)}" in source
    )


# ─────────────────────────────────────────────────────────────────────────
# Task 3 (help_page): /admin/help exists, is linked from the subnav, and
# documents all four statuses, all four trust tiers, and all four review
# states.
# ─────────────────────────────────────────────────────────────────────────

_STATUS_LABELS = ["Candidate", "Draft", "Published", "Unpublished"]
_TIER_LABELS = ["Verified", "Trusted", "Provisional", "Uncertain"]
_REVIEW_STATE_LABELS = ["Unreviewed", "Needs review", "Confirmed", "Edited"]


def test_help_page_exists() -> None:
    assert HELP_PAGE_PATH.is_file()


def test_subnav_links_to_help_page() -> None:
    source = _source(SUBNAV_PATH)
    assert 'href="/admin/help"' in source


def test_help_page_documents_all_four_lifecycle_statuses() -> None:
    source = _source(HELP_PAGE_PATH)
    for label in _STATUS_LABELS:
        assert label in source, f"missing status label: {label}"


def test_help_page_documents_all_four_trust_tiers() -> None:
    source = _source(HELP_PAGE_PATH)
    for label in _TIER_LABELS:
        assert label in source, f"missing trust tier label: {label}"


def test_help_page_documents_all_four_review_states() -> None:
    source = _source(HELP_PAGE_PATH)
    for label in _REVIEW_STATE_LABELS:
        assert label in source, f"missing review state label: {label}"


def test_help_page_documents_both_publish_gates() -> None:
    source = _source(HELP_PAGE_PATH)
    assert "resolve" in source.lower() and "gate" in source.lower()
    assert "trust gate" in source.lower()
    assert "override" in source.lower()


def test_help_page_uses_inline_styles_only_no_utility_classes() -> None:
    source = _source(HELP_PAGE_PATH)
    assert "class=" not in source


def test_help_page_contains_no_speaker_ranking_or_comparison_language() -> None:
    # Apolitical hard constraint (CLAUDE.md) — a coarse static guard, not a
    # substitute for the <human-check> read-through the plan also requires.
    source = _source(HELP_PAGE_PATH).lower()
    banned_terms = [
        "more reliable",
        "less reliable",
        "more credible",
        "less credible",
        "justice is",
        "justices are",
        "advocate is",
        "advocates are",
    ]
    for term in banned_terms:
        assert term not in source, f"found comparative/ranking language: {term!r}"


def test_help_page_min_length() -> None:
    # min_lines: 80 per 49-03-PLAN.md's must_haves.artifacts
    lines = _source(HELP_PAGE_PATH).splitlines()
    assert len(lines) >= 80
