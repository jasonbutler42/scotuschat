"""
Phase 48 Plan 08 — blocked-publish override UI contract.

Locks the SvelteKit publish action's branching on the structured 422 from
plan 48-07 (`uncertain_tier_blocked`, `blank_override_reason`, and the
pre-existing plain-string detail for the non-overridable resolve gate and
the already-published guard) and the Status card's block-reason panel that
consumes it, by *pure static source contract* — no database, no `node`
subprocess. This repo has no frontend test framework (48-RESEARCH.md), so
a source contract is the strongest automated gate available. Follows
`test_phase45_popover_boxmodel_contract.py`'s `ROOT` / path-constant /
`_source()` shape.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.server.ts"
PAGE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of `{name}: async (...) => { ... }` or
    `function {name}(...) { ... }` — whichever form is present in source.

    For the arrow-function action form, the parameter list itself is
    destructured (`({ request, params, fetch }) => { ... }`), so the search
    must locate the `=>` first and then the FIRST `{` after it — not the
    first `{` after the action name, which would land inside the parameter
    list's own braces.
    """
    match = re.search(rf"{re.escape(name)}\s*:\s*async\s*\([^)]*\)\s*=>\s*", source)
    if match:
        brace_start = source.index("{", match.end())
    else:
        match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*", source)
        assert match, f"could not find `{name}` action/function in source"
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
# Task 1: the publish action branches on the structured 422 / relays override
# ─────────────────────────────────────────────────────────────────────────


def test_publish_action_branches_on_uncertain_tier_blocked_code() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "uncertain_tier_blocked" in body
    idx = body.index("uncertain_tier_blocked")
    # publishBlocked, trustTier, and blockers must all be set on this branch.
    following = body[idx : idx + 400]
    assert "publishBlocked" in following
    assert "trustTier" in following
    assert "blockers" in following


def test_publish_action_branches_on_blank_override_reason_code() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "blank_override_reason" in body
    idx = body.index("blank_override_reason")
    following = body[idx : idx + 400]
    assert "publishBlocked" in following
    assert "overrideReasonRequired" in following


def test_publish_action_relays_plain_string_detail_without_publish_blocked() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    # A plain-string detail (resolve gate / already-published) takes the
    # `error` path and never sets publishBlocked — that gate is not
    # overridable (D-14), so no reason field must be offered for it.
    assert re.search(r"typeof\s+detail\s*===\s*['\"]string['\"]", body)
    string_branch_idx = re.search(r"typeof\s+detail\s*===\s*['\"]string['\"]", body).end()
    following = body[string_branch_idx : string_branch_idx + 400]
    assert "error:" in following
    assert "publishBlocked" not in following


def test_publish_action_sends_json_body_only_when_reason_supplied() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "override_reason" in body
    assert "Content-Type" in body
    assert "JSON.stringify" in body
    # The non-reason branch must still post a bare request (byte-identical
    # to pre-Phase-48 behaviour) — the admin token header alone, no body.
    assert re.search(r"headers:\s*\{\s*'X-Admin-Token':\s*ADMIN_TOKEN\s*\}\s*,?\s*\}\)", body) or (
        "'X-Admin-Token': ADMIN_TOKEN }," in body
    )


# ─────────────────────────────────────────────────────────────────────────
# Task 2: the block panel and override prompt on the Status card
# ─────────────────────────────────────────────────────────────────────────


def test_page_renders_override_reason_textarea_inside_publish_form_guarded_by_publish_blocked() -> None:
    source = _source(PAGE_PATH)
    assert "{#if form?.publishBlocked}" in source
    guard_idx = source.index("{#if form?.publishBlocked}")
    following = source[guard_idx : guard_idx + 3000]
    assert 'action="?/publish"' in following
    assert 'name="override_reason"' in following
    assert 'for="override_reason"' in following


def test_override_reason_required_attribute_documented_as_defense_in_depth() -> None:
    source = _source(PAGE_PATH)
    assert "required" in source
    # D-17: the client-side `required` attribute must never be the sole
    # enforcement — a comment must say so near the textarea.
    assert "defense-in-depth" in source.lower()


def test_blank_override_reason_renders_distinct_message() -> None:
    source = _source(PAGE_PATH)
    assert "form?.overrideReasonRequired" in source or "form.overrideReasonRequired" in source


def test_blocker_sentence_maps_all_four_server_side_codes() -> None:
    source = _source(PAGE_PATH)
    assert "function blockerSentence" in source
    body = _function_body(source, "blockerSentence")
    for code in [
        "unresolved_utterance_speaker",
        "unresolved_participant",
        "llm_corrective_utterance",
        "no_constituents",
    ]:
        assert code in body, f"blockerSentence does not map {code}"
    # At least one call site outside the definition itself.
    assert source.count("blockerSentence(") >= 2


def test_publish_visibility_condition_unchanged() -> None:
    source = _source(PAGE_PATH)
    assert "data.argument.status === 'draft' || data.argument.status === 'unpublished'" in source


def test_no_new_component_import_added() -> None:
    source = _source(PAGE_PATH)
    imports = re.findall(r"from\s+'\$lib/components/[^']+'", source)
    assert sorted(imports) == sorted(
        [
            "from '$lib/components/ArgumentDetailsCard.svelte'",
            "from '$lib/components/CopyableExtractedValue.svelte'",
        ]
    ), f"unexpected component import set: {imports}"


def test_no_retired_pipeline_literal_remains_in_either_file() -> None:
    for path in (PAGE_SERVER_PATH, PAGE_PATH):
        source = _source(path)
        assert "'pipeline'" not in source, f"retired born-state literal 'pipeline' found in {path.name}"
        assert '"pipeline"' not in source, f"retired born-state literal \"pipeline\" found in {path.name}"


def test_status_history_renders_override_reason_and_tier_at_transition() -> None:
    source = _source(PAGE_PATH)
    assert "entry.override_reason" in source
    assert "entry.trust_tier_at_transition" in source
