"""
Phase 48 Plan 10 — detail-page publish-error rendering contract.

Locks the fix for the real defect found live during plan 48-10's Task 4
operator checkpoint (step 9): the detail page's (`/admin/arguments/[id]`)
`?/publish` action correctly returned `fail(422, { error: detail })` for the
non-overridable resolve gate / already-published guard (D-14), but the
`+page.svelte` template rendered `form?.error` in exactly ONE place — the
case-metadata card's form-level alert slot — so a publish error produced no
visible feedback in the Status card (where the Publish button and block
panel actually live) and, worse, could leak into the unrelated
case-metadata card's alert region since `form` is shared across every
action on this page.

The fix tags every publish-action `fail(...)` payload with
`source: 'publish'` and uses that marker to (a) keep publish errors OUT of
the case-metadata card's alert slot and (b) render them, visibly and with
no override reason field, in the Status card next to the Publish button.

Mirrors `test_phase48_publish_override_ui_contract.py`'s `ROOT` /
`_source()` / `_function_body()` helper shapes against the SAME
`[id]` files that module covers — this module is additive, not a
replacement.
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
# The publish action tags every fail() payload with a discriminator
# ─────────────────────────────────────────────────────────────────────────


def test_publish_action_tags_every_fail_branch_with_publish_source() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert body.count("source: 'publish'") >= 5, (
        "expected `source: 'publish'` on every fail() branch (thrown-fetch, "
        "uncertain_tier_blocked, blank_override_reason, plain-string, "
        "generic) so the page can discriminate a publish error from any "
        "other action's error on this page's shared `form` prop"
    )


def test_plain_string_detail_branch_carries_publish_source_and_no_publish_blocked() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    match = re.search(r"typeof\s+detail\s*===\s*['\"]string['\"]", body)
    assert match
    following = body[match.end() : match.end() + 800]
    assert "error:" in following
    assert "source: 'publish'" in following
    assert "publishBlocked" not in following


# ─────────────────────────────────────────────────────────────────────────
# The template renders publish errors in the Status card, not the
# case-metadata card, and offers no reason field for the plain-string path
# ─────────────────────────────────────────────────────────────────────────


def test_case_metadata_alert_excludes_publish_sourced_errors() -> None:
    source = _source(PAGE_PATH)
    guard = "{#if caseNameRequired || docketRequired || (form?.error && form.source !== 'publish')}"
    assert guard in source, (
        "case-metadata card's alert slot must exclude publish-sourced "
        "errors — otherwise a publish failure leaks into an unrelated "
        "card's alert region"
    )


def test_status_card_renders_visible_publish_error_next_to_publish_button() -> None:
    source = _source(PAGE_PATH)
    guard = "{#if form?.error && form.source === 'publish' && !form.publishBlocked}"
    assert guard in source
    guard_idx = source.index(guard)
    following = source[guard_idx : guard_idx + 400]
    assert 'role="alert"' in following
    # No override reason field must be offered on this branch (D-14) — the
    # non-overridable resolve gate and the already-published guard are not
    # overridable. The reason textarea only exists inside the
    # `publishBlocked` panel elsewhere in the file, not here.
    assert 'name="override_reason"' not in following


def test_status_card_publish_error_guard_precedes_publish_blocked_panel() -> None:
    """
    The new visible-error block must sit adjacent to the Publish button —
    i.e. before the `publishBlocked` panel in source order — so it renders
    in the Status card where the operator is looking, not buried elsewhere.
    """
    source = _source(PAGE_PATH)
    error_guard_idx = source.index(
        "{#if form?.error && form.source === 'publish' && !form.publishBlocked}"
    )
    blocked_panel_idx = source.index("{#if form?.publishBlocked}")
    assert error_guard_idx < blocked_panel_idx


def test_publish_blocked_panel_still_untouched_by_source_discriminator() -> None:
    """
    The structured-block panel (`uncertain_tier_blocked` /
    `blank_override_reason`) already renders correctly and must remain
    keyed on `form?.publishBlocked` alone — the `source` discriminator is
    additive scaffolding for the plain-string path, not a replacement for
    the existing, working branch.
    """
    source = _source(PAGE_PATH)
    assert "{#if form?.publishBlocked}" in source
