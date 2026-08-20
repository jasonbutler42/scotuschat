"""
Phase 48 Plan 10 — detail-page publish/unpublish error rendering contract.

Locks the fix for two real defects found live during plan 48-10's Task 4
operator checkpoint (step 9) and its immediate follow-up.

**Publish (found live, step 9):** the detail page's (`/admin/arguments/[id]`)
`?/publish` action correctly returned `fail(422, { error: detail })` for the
non-overridable resolve gate / already-published guard (D-14), but the
`+page.svelte` template rendered `form?.error` in exactly ONE place — the
case-metadata card's form-level alert slot — so a publish error produced no
visible feedback in the Status card (where the Publish button and block
panel actually live) and, worse, leaked into the unrelated case-metadata
card's alert region since `form` is shared across every action on this page.

**Unpublish (same defect, found by inspection immediately after fixing
publish):** the `?/unpublish` action's two `fail(...)` payloads were
likewise untagged, so an unpublish failure took the same wrong path into the
case-metadata card's alert slot. The unpublish failure path is hard to
trigger from a real browser (it requires the backend call itself to fail,
not any state the operator can put an argument into), so this module — not
a live walkthrough — is the verification for it.

The fix tags every publish- and unpublish-action `fail(...)` payload with
`source: 'publish'` / `source: 'unpublish'` respectively. The case-metadata
card's alert slot uses a positive test (`!form.source`) rather than a
negative list of excluded sources — `?/save` is the only action on this
page that returns an untagged `error`, so `!form.source` is both correct
today and robust to a future action being added without anyone having to
remember to extend an exclusion list. The Status card renders a single
widened error block, placed AFTER the draft/unpublished-vs-published
branch (not duplicated inside each arm), that fires for either source and
offers no override reason field for either (neither gate is overridable).

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
# The unpublish action tags both of its fail() payloads with a discriminator
# (same defect as publish, found by inspection — not independently live-
# verifiable, since triggering it requires the backend call itself to fail)
# ─────────────────────────────────────────────────────────────────────────


def test_unpublish_action_tags_both_fail_branches_with_unpublish_source() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "unpublish")
    assert body.count("source: 'unpublish'") >= 2, (
        "expected `source: 'unpublish'` on both fail() branches "
        "(thrown-fetch and non-ok response) so the page can discriminate "
        "an unpublish error from any other action's error on this page's "
        "shared `form` prop"
    )
    # Neither branch is a structured/overridable gate — no publishBlocked.
    assert "publishBlocked" not in body


# ─────────────────────────────────────────────────────────────────────────
# The template renders publish/unpublish errors in the Status card, not the
# case-metadata card, and offers no reason field for either plain-string path
# ─────────────────────────────────────────────────────────────────────────


def test_case_metadata_alert_uses_positive_no_source_test() -> None:
    """
    The case-metadata card's alert slot must use a positive test
    (`!form.source`) rather than a growing negative list of excluded
    sources — `?/save` is the only action on this page that returns an
    untagged `error`, so this stays correct if a future action is added
    without anyone having to remember to extend an exclusion list.
    """
    source = _source(PAGE_PATH)
    guard = "{#if caseNameRequired || docketRequired || (form?.error && !form.source)}"
    assert guard in source, (
        "case-metadata card's alert slot must exclude ANY sourced error "
        "(publish or unpublish) via a positive `!form.source` test — "
        "otherwise a publish or unpublish failure leaks into an unrelated "
        "card's alert region"
    )
    # The inner rendering must apply the same positive test, not just the
    # outer guard — otherwise the outer condition could be true for a
    # native-validation reason while the inner span still renders a
    # sourced error's message.
    guard_idx = source.index(guard)
    following = source[guard_idx : guard_idx + 800]
    assert "form?.error && !form.source" in following


def test_case_metadata_alert_no_longer_uses_publish_only_negative_exclusion() -> None:
    """
    Regression guard for the intermediate state this module replaces: a
    negative exclusion naming only 'publish' would silently let unpublish
    errors keep leaking into this card, reintroducing the same defect for
    a different action.
    """
    source = _source(PAGE_PATH)
    assert "form.source !== 'publish'" not in source


def test_status_card_renders_visible_error_for_both_publish_and_unpublish_sources() -> None:
    source = _source(PAGE_PATH)
    guard = "{#if form?.error && (form.source === 'publish' || form.source === 'unpublish') && !form.publishBlocked}"
    assert guard in source
    guard_idx = source.index(guard)
    following = source[guard_idx : guard_idx + 400]
    assert 'role="alert"' in following
    # No override reason field must be offered on this branch (D-14) — none
    # of the resolve gate, the already-published guard, or an unpublish
    # failure is overridable. The reason textarea only exists inside the
    # `publishBlocked` panel elsewhere in the file, not here.
    assert 'name="override_reason"' not in following


def test_status_card_error_block_is_not_duplicated_per_source() -> None:
    """
    The fix widens ONE existing condition rather than adding a second
    near-duplicate block for unpublish — assert there is exactly one
    `role="alert"` error paragraph guarded by a `form.source` check in the
    Status card region (i.e. not two separate blocks, one per action).
    """
    source = _source(PAGE_PATH)
    assert source.count("form.source === 'publish' || form.source === 'unpublish'") == 1
    # And no leftover single-source guard from the intermediate publish-only fix.
    assert "form.source === 'publish' && !form.publishBlocked" not in source


def test_status_card_error_guard_sits_outside_the_publish_vs_unpublish_branch() -> None:
    """
    The widened error block must render regardless of which control
    (Publish or Unpublish) is currently shown, so it must sit AFTER the
    `{#if data.argument.status === 'draft' || ... }{:else if ... ===
    'published'}...{/if}` branch closes — not nested inside either arm.
    """
    source = _source(PAGE_PATH)
    branch_open = "{#if data.argument.status === 'draft' || data.argument.status === 'unpublished'}"
    branch_open_idx = source.index(branch_open)
    error_guard = (
        "{#if form?.error && (form.source === 'publish' || form.source === 'unpublish') "
        "&& !form.publishBlocked}"
    )
    error_guard_idx = source.index(error_guard)

    # The error guard must come after the branch opens...
    assert error_guard_idx > branch_open_idx
    # ...and after the LAST {/if} that closes that branch (found by scanning
    # forward from the branch open to the error guard and confirming the
    # unpublish button's own closing form tag precedes the error guard).
    unpublish_button_idx = source.index("action=\"?/unpublish\"")
    assert branch_open_idx < unpublish_button_idx < error_guard_idx


def test_status_card_publish_blocked_panel_still_untouched_by_source_discriminator() -> None:
    """
    The structured-block panel (`uncertain_tier_blocked` /
    `blank_override_reason`) already renders correctly and must remain
    keyed on `form?.publishBlocked` alone — the `source` discriminator is
    additive scaffolding for the plain-string paths, not a replacement for
    the existing, working branch.
    """
    source = _source(PAGE_PATH)
    assert "{#if form?.publishBlocked}" in source
