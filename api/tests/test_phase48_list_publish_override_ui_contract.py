"""
Phase 48 Plan 10 — list-page blocked-publish override UI contract.

Mirrors `test_phase48_publish_override_ui_contract.py` (plan 48-08's
detail-page contract) exactly, reusing its `_source()`/`_function_body()`
helper shapes against the LIST page's
`app/src/routes/admin/arguments/+page.server.ts` and `+page.svelte` instead
of the `[id]` variants. Pure static source contract — no database, no
`node` subprocess. This repo has no frontend test framework (48-RESEARCH.md),
so a source contract is the strongest automated gate available.

Unlike plan 48-08's sibling contract test, this module does NOT assert the
absence of the retired `'pipeline'` literal in these two files — that
literal already exists in the list page's pre-existing badge fallback (dead
code today, since D-04 excludes candidate-status rows from this list
entirely) and fixing it was not part of this plan's four approved items
(see 48-10-PLAN.md's flagged_assumptions). Adding that assertion here would
silently expand scope beyond what was approved.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "+page.server.ts"
PAGE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "+page.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of `{name}: async (...) => { ... }` or
    `function {name}(...) { ... }` — whichever form is present in source.

    For the arrow-function action form, the parameter list itself is
    destructured (`({ request, fetch }) => { ... }`), so the search must
    locate the `=>` first and then the FIRST `{` after it — not the first
    `{` after the action name, which would land inside the parameter list's
    own braces.
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
# Task 1: the publish action branches on the structured 422 / relays override,
# every fail() payload carries argumentId
# ─────────────────────────────────────────────────────────────────────────


def test_publish_action_branches_on_uncertain_tier_blocked_code() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "uncertain_tier_blocked" in body
    idx = body.index("uncertain_tier_blocked")
    following = body[idx : idx + 400]
    assert "publishBlocked" in following
    assert "trustTier" in following
    assert "blockers" in following
    assert "argumentId" in following


def test_publish_action_branches_on_blank_override_reason_code() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "blank_override_reason" in body
    idx = body.index("blank_override_reason")
    following = body[idx : idx + 400]
    assert "publishBlocked" in following
    assert "overrideReasonRequired" in following
    assert "argumentId" in following


def test_publish_action_relays_plain_string_detail_without_publish_blocked() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    # A plain-string detail (resolve gate / already-published) takes the
    # `error` path and never sets publishBlocked — that gate is not
    # overridable (D-14), so no reason field must be offered for it.
    match = re.search(r"typeof\s+detail\s*===\s*['\"]string['\"]", body)
    assert match
    following = body[match.end() : match.end() + 400]
    assert "error:" in following
    assert "publishBlocked" not in following
    assert "argumentId" in following


def test_publish_action_carries_argument_id_on_every_fail_branch() -> None:
    """
    Per-row addressing (T-48-10-ROWMISMATCH): this page shares ONE `form`
    prop across many rows, so every returned fail(...) payload must carry
    `argumentId` — without it the page cannot tell which row's submission
    the returned form state belongs to.
    """
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert body.count("argumentId") >= 4, (
        "expected argumentId on every fail() branch (thrown-fetch, "
        "uncertain_tier_blocked, blank_override_reason, plain-string, "
        "generic) — found fewer occurrences than expected"
    )


def test_publish_action_sends_json_body_only_when_reason_supplied() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "override_reason" in body
    assert "Content-Type" in body
    assert "JSON.stringify" in body
    assert "'X-Admin-Token': ADMIN_TOKEN }," in body


def test_publish_action_still_redirects_on_success() -> None:
    body = _function_body(_source(PAGE_SERVER_PATH), "publish")
    assert "redirect(303, '/admin/arguments')" in body


# ─────────────────────────────────────────────────────────────────────────
# Task 1/2: the block panel, per-row addressing, tier badge, override prompt
# ─────────────────────────────────────────────────────────────────────────


def test_page_renders_override_reason_textarea_inside_publish_form_guarded_by_row_match() -> None:
    source = _source(PAGE_PATH)
    # Widened by the Cancel-affordance follow-up to also exclude a
    # dismissed panel — the row-addressing prefix is unchanged.
    guard = "{#if form?.publishBlocked && form.argumentId === arg.id && form !== dismissedForm}"
    assert guard in source
    guard_idx = source.index(guard)
    following = source[guard_idx : guard_idx + 4000]
    assert 'action="?/publish"' in following
    assert 'name="override_reason"' in following
    assert "for={'override_reason_' + arg.id}" in following or 'for="override_reason' in following


def test_override_reason_required_attribute_documented_as_defense_in_depth() -> None:
    source = _source(PAGE_PATH)
    assert "required" in source
    assert "defense-in-depth" in source.lower()


def test_blank_override_reason_renders_distinct_message_guarded_by_row_match() -> None:
    source = _source(PAGE_PATH)
    assert "form?.overrideReasonRequired && form.argumentId === arg.id" in source


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
    assert source.count("blockerSentence(") >= 2


def test_row_scoped_visible_error_for_plain_string_detail() -> None:
    """
    Defect 1's second half: a non-overridable-gate failure or already-
    published guard must now be visible on the list page, row-scoped, and
    must NOT offer a reason field.
    """
    source = _source(PAGE_PATH)
    assert "form?.error && form.argumentId === arg.id && !form.publishBlocked" in source
    idx = source.index("form?.error && form.argumentId === arg.id && !form.publishBlocked")
    following = source[idx : idx + 400]
    assert 'role="alert"' in following


def test_passive_tier_badge_renders_per_row() -> None:
    source = _source(PAGE_PATH)
    assert "function tierBadgeStyle" in source
    assert "function tierLabel" in source
    assert "tierBadgeStyle(arg.trust_tier)" in source
    assert "tierLabel(arg.trust_tier)" in source


def test_publish_button_never_disabled_based_on_tier_or_block_state() -> None:
    """
    Operator-rejected alternative, structurally enforced: the Publish
    button's `disabled` attribute must only ever reference `publishingId`
    (per-row in-flight state), never `trust_tier`, `publishBlocked`, or any
    tier-derived condition.
    """
    source = _source(PAGE_PATH)
    disabled_exprs = re.findall(r"disabled=\{([^}]*)\}", source)
    assert disabled_exprs, "expected at least one disabled={...} expression on a Publish button"
    for expr in disabled_exprs:
        assert "trust_tier" not in expr
        assert "publishBlocked" not in expr
        assert "publishingId" in expr


def test_publishing_id_state_and_enhance_wiring_present() -> None:
    source = _source(PAGE_PATH)
    assert "let publishingId = $state<number | null>(null);" in source
    assert source.count("publishingId") >= 2


# ─────────────────────────────────────────────────────────────────────────
# Follow-up polish item: the block panel's Cancel affordance
# ─────────────────────────────────────────────────────────────────────────


def test_block_panel_dismissal_uses_a_local_rune_not_form_mutation() -> None:
    """
    The panel is driven by server `form` state shared across every row —
    dismissal must be tracked with its own local Rune (comparing by
    reference against the current `form`), never by mutating `form` itself,
    which would either lose the row's identity or bleed into another row.
    """
    source = _source(PAGE_PATH)
    assert "let dismissedForm" in source
    assert "$state" in source.split("let dismissedForm", 1)[1][:60]


def test_block_panel_guard_excludes_dismissed_form() -> None:
    """
    The panel's render guard must additionally check the current `form`
    against the dismissed one, on top of the pre-existing per-row
    `publishBlocked && argumentId === arg.id` guard — dismissing must not
    weaken the existing row-addressing contract (T-48-10-ROWMISMATCH).
    """
    source = _source(PAGE_PATH)
    guard = "{#if form?.publishBlocked && form.argumentId === arg.id && form !== dismissedForm}"
    assert guard in source


def test_block_panel_offers_a_keyboard_reachable_cancel_affordance_with_accessible_label() -> None:
    """
    A real `<button>` element (never a `<div>`/`<span>` with an onclick) so
    it is naturally focusable and reachable by tab order, and it must carry
    an accessible name — either visible text content (e.g. "Cancel") or,
    if an icon-only "x" is used instead, an explicit `aria-label`.
    """
    source = _source(PAGE_PATH)
    guard_idx = source.index(
        "{#if form?.publishBlocked && form.argumentId === arg.id && form !== dismissedForm}"
    )
    panel = source[guard_idx : guard_idx + 4000]

    # Find a <button ...>...</button> whose onclick sets dismissedForm.
    match = re.search(
        r"<button[^>]*onclick=\{[^}]*dismissedForm\s*=[^}]*\}[^>]*>([^<]*)</button>",
        panel,
        re.DOTALL,
    )
    assert match, "expected a <button> element wiring dismissedForm assignment on click"
    button_tag_and_text = match.group(0)
    visible_text = match.group(1).strip()
    has_aria_label = 'aria-label=' in button_tag_and_text
    assert visible_text or has_aria_label, (
        "the Cancel/dismiss button must have an accessible name: either "
        "non-empty visible text or an aria-label (required if an icon-only "
        "'x' is used instead of text)"
    )
    assert 'type="button"' in button_tag_and_text, (
        "the dismiss control must be type=\"button\" so it never submits "
        "the surrounding form"
    )


def test_dismissing_one_rows_panel_cannot_leak_into_another_row() -> None:
    """
    Only one row's panel can ever be visible at a time (one shared `form`
    reflects only the most recently submitted action), so a reference-based
    dismissal Rune structurally cannot affect a different row — assert the
    guard is argumentId-scoped (not merely a page-global boolean) so this
    stays true if the panel logic is ever refactored.
    """
    source = _source(PAGE_PATH)
    guard_idx = source.index(
        "{#if form?.publishBlocked && form.argumentId === arg.id && form !== dismissedForm}"
    )
    following = source[guard_idx : guard_idx + 200]
    assert "form.argumentId === arg.id" in following


# ─────────────────────────────────────────────────────────────────────────
# Task 3 adjacency: the list page's ArgumentListItem type includes trust_tier
# ─────────────────────────────────────────────────────────────────────────


def test_list_page_server_type_declares_trust_tier() -> None:
    source = _source(PAGE_SERVER_PATH)
    assert "trust_tier: string" in source


def test_no_new_component_import_added() -> None:
    source = _source(PAGE_PATH)
    imports = re.findall(r"from\s+'\$lib/components/[^']+'", source)
    assert imports == [], f"unexpected component import(s) added: {imports}"
