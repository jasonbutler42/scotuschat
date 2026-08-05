"""
Phase 44 — Resolve table rework — pure static source contract.

Plans 44-02, 44-03, 44-04, and 44-05 all edit `ResolveCard.svelte` in place; this file
is shared across all four, organized with one section-comment banner per plan so each
plan's own contract stays easy to find as later plans append to it.

No frontend test framework exists in this repo (see 39-RESEARCH.md / 36-PATTERNS.md),
so a static source contract is the strongest automated gate available. Follows
`api/tests/test_phase39_popover_ui_contract.py`'s `ROOT` + module-level path constant
+ `_source()` shape, and `api/tests/test_phase38_extracted_value_contract.py`'s
sibling `RESOLVE_CARD_PATH` convention.

Plan 44-02 (this section's author) guards:
  1. Established the five-column header order with no Action header and no residual
     Title header (RESOLVE-01) — superseded by Plan 44-05's four-column merge
     (RESOLVE-07); see that plan's banner below for the current header contract.
  2. The Descriptor input carries its renamed field name, placeholder copy, and
     ellipsis-truncation declaration; the Raw Label badge snippet wraps rather than
     truncates (RESOLVE-01).
  3. The Descriptor cell snippet always renders — one snippet contains both the bench
     en-dash literal and the editable `<input` (RESOLVE-04).
  4. The dedicated accept-the-auto-match handler and both retired button labels are
     gone; the "Suggested" badge lives inside the listbox-option region — the
     open-the-search handler itself is retired by Plan 44-05 (RESOLVE-08).
  5. Every hex colour literal in the file belongs to the UI-SPEC's approved palette —
     the standing guard against later passes smuggling in a new colour.

Plan 44-05 adds: the four-column merge and the dropdown-only Resolved As contract
(RESOLVE-07/08) — see its own banner section below. A Task 3 checkpoint-remediation
section follows it, added after the operator rejected the first Task 3 checkpoint
with specific defects: create-person moved inside the open popup, a combobox
affordance icon, a neutral gated placeholder, and a fix for the toggle discarding a
previously-chosen specific advocate role.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
RESOLVE_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ResolveCard.svelte"

APPROVED_HEX_COLORS = {
    "#1e293b",
    "#0f1117",
    "#334155",
    "#e2e8f0",
    "#94a3b8",
    "#93c5fd",
    "#4ade80",
    "#fbbf24",
    "#ef4444",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_body(source: str, name: str) -> str:
    """Extract the brace-balanced body of `{#snippet {name}(...)} ... {/snippet}`."""
    match = re.search(rf"\{{#snippet\s+{re.escape(name)}\s*\(", source)
    assert match, f"could not find `{{#snippet {name}(` in source"
    start = match.start()
    end_match = re.search(r"\{/snippet\}", source[start:])
    assert end_match, f"could not find matching {{/snippet}} for {name}"
    return source[start : start + end_match.end()]


def _region(source: str, start_pattern: str, end_pattern: str) -> str:
    """Extract the substring from the first `start_pattern` match to the following
    `end_pattern` match (used to scope assertions to e.g. a single <li> block)."""
    start_match = re.search(start_pattern, source)
    assert start_match, f"could not find start pattern {start_pattern!r}"
    end_match = re.search(end_pattern, source[start_match.end() :])
    assert end_match, f"could not find end pattern {end_pattern!r} after start"
    return source[start_match.start() : start_match.end() + end_match.end()]


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-02 — RESOLVE-01: five-column structure, no Action column
# ─────────────────────────────────────────────────────────────────────────────


def test_exactly_four_column_headers_declared() -> None:
    source = _source(RESOLVE_CARD_PATH)
    count = source.count('<th scope="col"')
    assert count == 4, f"RESOLVE-07 requires exactly four <th scope=\"col\"> cells, found {count}"


def test_four_header_labels_appear_in_canonical_order() -> None:
    source = _source(RESOLVE_CARD_PATH)
    labels = [">Raw Label<", ">Resolved As<", ">Argument Role<", ">Descriptor<"]
    indices = []
    for label in labels:
        idx = source.find(label)
        assert idx != -1, f"RESOLVE-07: header label {label!r} not found in source"
        indices.append(idx)
    assert indices == sorted(indices), (
        f"RESOLVE-07: header labels must appear in canonical order (Raw Label, Resolved As, "
        f"Argument Role, Descriptor); got index order {indices}"
    )
    assert ">Bench/Advocate<" not in source, (
        "RESOLVE-07: no Bench/Advocate header cell may exist anywhere in the component — "
        "expressed with > and < delimiters so it cannot match the toggle's own segment "
        "labels (>Bench< / >Advocate<)"
    )


def test_no_action_header_and_no_residual_title_header() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count(">Action<") == 0, "RESOLVE-01: the retired Action column header must not exist"
    assert source.count(">Title<") == 0, "RESOLVE-01: the retired Title column header must not exist"


def test_descriptor_input_carries_renamed_field_placeholder_and_truncation() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count('name="descriptor"') == 1, (
        "RESOLVE-04: exactly one input should carry the renamed descriptor form field"
    )
    assert 'placeholder="e.g. Attorney, Location, or Affiliation"' in source, (
        "UI-SPEC Copywriting Contract: Descriptor placeholder copy must be present"
    )
    assert "text-overflow: ellipsis" in source, (
        "UI-SPEC overflow consideration: Descriptor input must ellipsis-truncate when unfocused"
    )


def test_raw_label_badge_snippet_exists_and_wraps_rather_than_truncates() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#snippet rawLabelBadge(" in source, (
        "RESOLVE-01: the Raw Label badge must be extracted into its own snippet"
    )
    badge_body = _snippet_body(source, "rawLabelBadge")
    assert "white-space: normal" in badge_body, (
        "UI-SPEC long-text backstop: the Raw Label badge must wrap (white-space: normal), "
        "never truncate — truncating a raw label could hide the discrepancy it exists to show"
    )
    assert "text-overflow: ellipsis" not in badge_body, (
        "Raw Label badge must not declare ellipsis truncation — it wraps, per UI-SPEC"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-02 — RESOLVE-04 / D-03 / D-04: Descriptor always renders; collapsed
# Resolved As entry point
# ─────────────────────────────────────────────────────────────────────────────


def test_descriptor_cell_snippet_always_renders_bench_dash_and_editable_input() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#snippet descriptorCell(" in source, (
        "RESOLVE-04: the Descriptor cell must be extracted into its own always-rendered snippet"
    )
    body = _snippet_body(source, "descriptorCell")
    assert "–" in body, "RESOLVE-04: the Descriptor cell must render an en dash for BENCH rows"
    assert "<input" in body, (
        "RESOLVE-04: the Descriptor cell must render an editable <input> for non-BENCH rows — "
        "both states in the same snippet is the 'always renders' contract"
    )
    assert "side !== 'BENCH'" not in body, (
        "RESOLVE-04: the cell body must not be gated by a wrapping non-bench check — "
        "Phase 27 CR-01/CR-02 requires the data-carrying input stay in the DOM unconditionally"
    )


def test_dedicated_confirm_handler_and_retired_button_labels_are_gone() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "handleConfirm" not in source, (
        "D-03: the dedicated accept-the-auto-match handler must be deleted entirely — "
        "there is no separate Confirm action any more"
    )
    assert ">Confirm<" not in source, "D-03: no element may render the retired 'Confirm' label"
    assert ">Select<" not in source, "D-03: no element may render the retired 'Select' label"
    assert "Select Bench or Advocate to continue" not in source, (
        "D-07: the retired gate instructional sentence must be removed"
    )
    assert ">Change</button>" not in source, (
        "RESOLVE-08: the Change link's button is retired — the always-rendered dropdown is "
        "the entry point now, there is nothing left to click to reveal it"
    )
    assert "✓ Corrected" not in source, (
        "RESOLVE-08: the Corrected banner is retired along with the confirm/correct "
        "disposition state machine"
    )


def test_person_dropdown_is_always_rendered_not_click_revealed() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function openPersonSearch(" not in source, (
        "RESOLVE-08: openPersonSearch must be deleted entirely — there is no click-to-reveal "
        "entry point any more, the dropdown itself is the entry point"
    )
    assert "openPersonSearch" not in source, (
        "RESOLVE-08: no reference to openPersonSearch (definition or call site) may remain"
    )
    assert source.count('role="combobox"') == 1, (
        "RESOLVE-08: exactly one always-rendered combobox input must exist for the Resolved As cell"
    )


def test_suggested_badge_lives_inside_the_listbox_option_region() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "Suggested" in source, "D-03: the pre-filled candidate must carry a 'Suggested' badge"
    option_region = _region(source, r'role="option"', r"</li>")
    assert "Suggested" in option_region, (
        "D-03: the 'Suggested' badge must render inside the <li role=\"option\"> block, "
        "distinguishing the pre-filled top suggestion from other candidates"
    )


def test_gated_entry_point_is_genuinely_inert() -> None:
    source = _source(RESOLVE_CARD_PATH)
    dropdown_body = _snippet_body(source, "personDropdown")
    assert "disabled" in dropdown_body, (
        "T-44-18: the gated person input must carry `disabled` — never removed from the DOM"
    )
    assert re.search(r"aria-disabled=\{[^}]*gated[^}]*\}", dropdown_body), (
        "T-44-07/T-44-18: the gated Resolved As entry point must bind aria-disabled to the "
        "gate state — the D-11/PJOB-18 side-first gate must survive the removal of its "
        "instructional sentence"
    )
    assert "clip-path: inset(50%)" in dropdown_body, (
        "D-07: the gated row must carry a visually-hidden (sr-only) explanation of the gate"
    )
    combobox_match = re.search(r'role="combobox"', dropdown_body)
    assert combobox_match, "RESOLVE-08: personDropdown must render the combobox input"
    input_start = dropdown_body.rfind("<input", 0, combobox_match.start())
    assert input_start != -1, "could not locate the <input role=\"combobox\"> tag's own start"
    preceding_window = dropdown_body[max(0, input_start - 120) : input_start]
    assert "{#if" not in preceding_window, (
        "T-44-18/Pitfall 4: no {#if} may immediately precede the combobox input's own "
        "declaration — the input must be unconditionally rendered, gated only via "
        "disabled/aria-disabled (the listbox popup itself may still be conditionally rendered)"
    )


def test_no_unapproved_hex_colors_introduced() -> None:
    source = _source(RESOLVE_CARD_PATH)
    found = set(re.findall(r"#[0-9a-fA-F]{6}", source))
    unapproved = found - APPROVED_HEX_COLORS
    assert not unapproved, (
        f"UI-SPEC Color table: found hex colour(s) outside the approved palette: {unapproved}. "
        f"Approved set: {APPROVED_HEX_COLORS}"
    )


def _function_body(source: str, name: str) -> str:
    """Extract a script-level `function {name}(...) { ... }` body, matching the
    tab-indented-closing-brace convention `awk '/function name/,/^\\t}/'` relies on
    at execution time."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    assert match, f"could not find `function {name}(` in source"
    start = match.start()
    end_match = re.search(r"\n\t\}", source[start:])
    assert end_match, f"could not find end of function {name}"
    return source[start : start + end_match.end()]


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-03 — RESOLVE-02: segmented Bench/Advocate toggle, single submitted
# side value, flushed submit (D-07)
# ─────────────────────────────────────────────────────────────────────────────


def test_side_form_field_is_singular_and_lives_in_hidden_form() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count('name="side"') == 1, (
        "RESOLVE-02/T-44-11: exactly one element may carry the `side` form-field "
        "name — the always-present hidden input is the sole submitting control"
    )
    form_region = _region(source, r'action="\?/saveResolveRow"', r"</form>")
    assert form_region.count('name="side"') == 1, (
        "RESOLVE-02: the `side` field must sit inside the per-row hidden form region"
    )


def test_flush_sync_imported_and_called_inside_submit_row() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "import { flushSync } from 'svelte'" in source, (
        "RESOLVE-02: the svelte runtime flush must be imported"
    )
    submit_row_body = _function_body(source, "submitRow")
    assert "flushSync()" in submit_row_body, (
        "RESOLVE-02: flushSync() must be called inside submitRow, before requestSubmit(), "
        "so the just-set pendingSideOverrides value reaches the DOM before the form serializes"
    )


def test_side_toggle_snippet_has_two_pressed_segments_and_one_group() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#snippet sideToggle(" in source, "RESOLVE-02: the segmented toggle must be its own snippet"
    assert source.count("aria-pressed") == 2, "RESOLVE-02: exactly two segments carry aria-pressed"
    assert source.count('role="group"') == 1, "RESOLVE-02: exactly one grouping role wraps the toggle"
    assert source.count(">Bench<") == 1, "RESOLVE-02: the Bench segment label must appear exactly once"
    assert source.count(">Advocate<") == 1, "RESOLVE-02: the Advocate segment label must appear exactly once"


def test_toggle_side_handler_has_early_no_op_return() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function toggleSide(" in source, "RESOLVE-02: toggleSide must exist as the toggle's click handler"
    toggle_body = _function_body(source, "toggleSide")
    assert re.search(r"\breturn;", toggle_body), (
        "RESOLVE-02: toggleSide must return early (no state write, no submit) when the "
        "requested choice is already the active one — this is what stops a second "
        "Advocate click from resetting a stored PETITIONER back to UNKNOWN"
    )


def test_confirm_side_and_on_side_change_preserved_not_replaced() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function confirmSide(" in source, (
        "RESOLVE-02: confirmSide must be extended, not replaced (44-CONTEXT.md Established Patterns)"
    )
    assert "function onSideChange(" in source, (
        "RESOLVE-02: onSideChange must be extended, not replaced (44-CONTEXT.md Established Patterns)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-03 — RESOLVE-03: writable Argument Role dropdown (D-01, D-02)
# ─────────────────────────────────────────────────────────────────────────────


def test_argument_role_select_is_singular_and_carries_no_name_or_form() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("<select") == 1, "RESOLVE-03: exactly one <select> should exist in the file"
    select_region = _region(source, r"<select", r"</select>")
    assert not re.search(r"\bname=", select_region), (
        "RESOLVE-03: the Argument Role select must not submit directly — the hidden "
        "`side` input from Task 1 is the sole submitting element"
    )
    assert not re.search(r"\bform=", select_region), (
        "RESOLVE-03: the Argument Role select must not carry a form attribute"
    )


def test_argument_role_options_in_locked_order() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("<option value=") == 4, "RESOLVE-03: exactly four <option> declarations"
    order = [
        '<option value="UNKNOWN">',
        '<option value="PETITIONER">',
        '<option value="RESPONDENT">',
        '<option value="AMICUS">',
    ]
    indices = []
    for token in order:
        idx = source.find(token)
        assert idx != -1, f"RESOLVE-03: option {token!r} not found"
        indices.append(idx)
    assert indices == sorted(indices), (
        "RESOLVE-03: options must appear in order placeholder, petitioner, respondent, amicus"
    )


def test_argument_role_placeholder_is_real_unknown_value() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert '<option value="UNKNOWN">Select case role</option>' in source, (
        "D-02: the placeholder option's value must be the literal UNKNOWN enum member, "
        "with the user-locked copy 'Select case role'"
    )
    assert 'value=""' not in source, (
        "D-02: no empty-string sentinel value may exist anywhere in the file"
    )
    select_region = _region(source, r"<select", r"</select>")
    assert "disabled>" not in select_region, (
        "D-02: no option in the Argument Role select may be disabled — UNKNOWN is a "
        "real, already-supported value"
    )


def test_choose_argument_role_handler_exists() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function chooseArgumentRole(" in source, (
        "RESOLVE-03: chooseArgumentRole must exist as the Argument Role select's onchange handler"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-03 — RESOLVE-06: lock affordance / missing-tenure distinctness,
# and in-flight disabling across all three row controls
# ─────────────────────────────────────────────────────────────────────────────


def test_argument_role_cell_has_exactly_one_svg() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "argumentRoleCell")
    assert body.count("<svg") == 1, (
        "RESOLVE-06: the Argument Role snippet must render exactly one lock icon SVG "
        "(the locked bench branch), never one per branch"
    )


def test_missing_tenure_branch_shares_no_markup_with_locked_branch() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "argumentRoleCell")
    missing_tenure_region = _region(body, r"Missing tenure", r"\{:else if rowEditable\}")
    assert "<svg" not in missing_tenure_region, (
        "RESOLVE-06: the missing-tenure branch must carry NO lock icon — a real data "
        "gap must never read as a deliberate system-derived value"
    )
    assert "border-radius" not in missing_tenure_region, (
        "RESOLVE-06: the missing-tenure branch must carry NO bordered box — it shares "
        "no markup with the locked-bench branch"
    )


def test_missing_tenure_warning_and_lock_alternative_appear_exactly_once() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("⚠ Missing tenure") == 1, (
        "RESOLVE-06: the app-wide warning glyph + copy must appear exactly once"
    )
    assert source.count(">Edit person<") == 1, "RESOLVE-06: the Edit person link must appear exactly once"
    assert source.count("#fbbf24") >= 1, "RESOLVE-06: the amber warning color must still be present"
    assert source.count("Set from tenure, not editable") == 1, (
        "RESOLVE-06: the lock's visually-hidden a11y alternative must appear exactly once"
    )


def test_saving_flag_disables_all_three_row_controls() -> None:
    source = _source(RESOLVE_CARD_PATH)
    descriptor_body = _snippet_body(source, "descriptorCell")
    assert "disabled" in descriptor_body, "RESOLVE-02 concurrency: Descriptor input must disable while saving"
    toggle_body = _snippet_body(source, "sideToggle")
    assert "disabled" in toggle_body, "RESOLVE-02 concurrency: toggle segments must disable while saving"
    role_body = _snippet_body(source, "argumentRoleCell")
    assert "disabled" in role_body, "RESOLVE-02 concurrency: Argument Role select must disable while saving"
    assert source.count("saving") >= 3, (
        "RESOLVE-02 concurrency: the saving flag identifier must be threaded through all "
        "three controls, not just declared once"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-04 — RESOLVE-05: CopyableExtractedValue prefixLabel prop, the four
# "Imported:" hints, and the five untouched call sites (D-08, D-09)
# ─────────────────────────────────────────────────────────────────────────────

COPYABLE_PATH = ROOT / "app" / "src" / "lib" / "components" / "CopyableExtractedValue.svelte"
ARGUMENT_DETAILS_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ArgumentDetailsCard.svelte"
DOCKET_PILL_PATH = ROOT / "app" / "src" / "lib" / "components" / "DocketPillInput.svelte"
PIPELINE_JOB_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.svelte"
PEOPLE_DETAIL_PATH = ROOT / "app" / "src" / "routes" / "admin" / "people" / "[id]" / "+page.svelte"
ARGUMENT_EDIT_PATH = ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.svelte"

# The five pre-existing call sites that must keep rendering the default
# "Extracted:" prefix — asserted individually below, per the plan's explicit
# instruction ("assert per file with a message naming the file, not as one
# aggregate assertion").
UNTOUCHED_CALL_SITES = [
    ARGUMENT_DETAILS_CARD_PATH,
    DOCKET_PILL_PATH,
    PIPELINE_JOB_PATH,
    PEOPLE_DETAIL_PATH,
    ARGUMENT_EDIT_PATH,
]


def test_copyable_extracted_value_declares_prefix_label_prop_with_default() -> None:
    source = _source(COPYABLE_PATH)
    assert "prefixLabel?: string;" in source, (
        "D-09: CopyableExtractedValue must declare the optional prefixLabel prop"
    )
    assert "prefixLabel = 'Extracted'" in source, (
        "D-09: prefixLabel must default to the pre-existing wording so every "
        "untouched call site keeps rendering 'Extracted:'"
    )
    assert '<span class="prefix">{prefixLabel}:</span>' in source, (
        "D-09: the prefix element must render the interpolated prop, not a hardcoded string"
    )
    assert '<span class="prefix">Extracted:</span>' not in source, (
        "D-09: no hardcoded prefix text may remain in the markup"
    )


def test_copyable_extracted_value_stacked_derivation_is_unaltered() -> None:
    source = _source(COPYABLE_PATH)
    assert "let isStacked = $derived(confidence !== undefined || raw !== undefined);" in source, (
        "D-09: the back-compat stacked-mode derivation must be byte-identical — "
        "prefixLabel must not be part of what activates stacked mode"
    )


def test_each_untouched_call_site_passes_no_prefix_label() -> None:
    """Aggregate sweep over all five untouched call sites — see the five
    dedicated per-file tests below for individually-named regression proof."""
    for path in UNTOUCHED_CALL_SITES:
        source = _source(path)
        assert "prefixLabel" not in source, (
            f"D-09: {path.name} must not reference prefixLabel — it must keep rendering "
            f"the default 'Extracted:' prefix"
        )


def test_argument_details_card_passes_no_prefix_label() -> None:
    source = _source(ARGUMENT_DETAILS_CARD_PATH)
    assert "prefixLabel" not in source, (
        "D-09: ArgumentDetailsCard.svelte must not reference prefixLabel — it must keep "
        "rendering the default 'Extracted:' prefix"
    )


def test_docket_pill_input_passes_no_prefix_label() -> None:
    source = _source(DOCKET_PILL_PATH)
    assert "prefixLabel" not in source, (
        "D-09: DocketPillInput.svelte must not reference prefixLabel — it must keep "
        "rendering the default 'Extracted:' prefix"
    )


def test_pipeline_job_detail_page_passes_no_prefix_label() -> None:
    source = _source(PIPELINE_JOB_PATH)
    assert "prefixLabel" not in source, (
        "D-09: admin/pipeline/[job_id]/+page.svelte must not reference prefixLabel — it "
        "must keep rendering the default 'Extracted:' prefix"
    )


def test_people_detail_page_passes_no_prefix_label() -> None:
    source = _source(PEOPLE_DETAIL_PATH)
    assert "prefixLabel" not in source, (
        "D-09: admin/people/[id]/+page.svelte must not reference prefixLabel — it must "
        "keep rendering the default 'Extracted:' prefix"
    )


def test_argument_editor_page_passes_no_prefix_label() -> None:
    source = _source(ARGUMENT_EDIT_PATH)
    assert "prefixLabel" not in source, (
        "D-09: admin/arguments/[id]/+page.svelte must not reference prefixLabel — it must "
        "keep rendering the default 'Extracted:' prefix"
    )


def test_resolve_card_has_exactly_four_hint_usages() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("<CopyableExtractedValue") == 4, (
        "RESOLVE-05: exactly four CopyableExtractedValue usages must exist in ResolveCard.svelte"
    )
    assert source.count('prefixLabel="Imported"') == 4, (
        'RESOLVE-05: all four hints must pass prefixLabel="Imported"'
    )
    assert source.count("raw={null}") == 4, (
        "RESOLVE-05: all four hints must pass an explicitly-null raw prop"
    )
    assert not re.search(r"confidence=", source), "RESOLVE-05: no hint may pass a confidence prop"


def test_resolve_card_hint_copy_labels_each_appear_once() -> None:
    source = _source(RESOLVE_CARD_PATH)
    for label in ("Copy raw label", "Copy side", "Copy argument role", "Copy descriptor"):
        assert source.count(f'copyLabel="{label}"') == 1, f"expected exactly one copyLabel={label!r}"


def test_hint_value_helpers_exist_and_argument_role_helper_cannot_drift() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function resolvedAsHintValue(" in source, "RESOLVE-05: resolvedAsHintValue helper must exist"
    assert "function sideHintValue(" in source, "RESOLVE-05: sideHintValue helper must exist"
    assert "function argumentRoleHintValue(" in source, "RESOLVE-05: argumentRoleHintValue helper must exist"
    body = _function_body(source, "argumentRoleHintValue")
    assert "N/A - from tenure" in body, (
        "RESOLVE-05: the valid-tenure bench hint text must live inside the helper"
    )
    assert "N/A - tenure not found" in body, (
        "RESOLVE-05: the missing-tenure bench hint text must live inside the helper"
    )
    assert "missing_tenure" in body, (
        "RESOLVE-05: the helper must fork on the same missing_tenure field the control above it uses"
    )


def test_raw_label_column_has_no_hint() -> None:
    source = _source(RESOLVE_CARD_PATH)
    badge_body = _snippet_body(source, "rawLabelBadge")
    assert "CopyableExtractedValue" not in badge_body, (
        "RESOLVE-05: Raw Label is itself the raw source and must carry no hint"
    )


def test_resolve_card_contains_no_html_directive() -> None:
    """T-44-04: hint values are parse-derived text and must render as plain
    Svelte interpolation only — never {@html}."""
    source = _source(RESOLVE_CARD_PATH)
    assert "{@html" not in source


def test_palette_guard_still_passes_with_hint_additions() -> None:
    """Re-affirms the 44-02 palette test still holds over the same file after
    this plan's edits — no new colour was introduced by the hint markup."""
    source = _source(RESOLVE_CARD_PATH)
    found = set(re.findall(r"#[0-9a-fA-F]{6}", source))
    unapproved = found - APPROVED_HEX_COLORS
    assert not unapproved, f"found hex colour(s) outside the approved palette: {unapproved}"


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-05 — RESOLVE-07/08: four-column merge, dropdown-only Resolved As
# ─────────────────────────────────────────────────────────────────────────────


def _row_region(source: str) -> str:
    """Extract the body row's `<tr>...</tr>` region from inside `<tbody>` —
    distinct from the header row's own `<tr>` inside `<thead>`."""
    tbody_idx = source.index("<tbody>")
    body = source[tbody_idx:]
    return _region(body, r"<tr>", r"</tr>")


def _table_cells(row_region: str) -> list[str]:
    return re.findall(r"<td.*?</td>", row_region, re.DOTALL)


def _interface_body(source: str, name: str) -> str:
    """Extract a script-level `interface {name} { ... }` body, matching the
    tab-indented-closing-brace convention `_function_body` relies on."""
    match = re.search(rf"interface\s+{re.escape(name)}\s*\{{", source)
    assert match, f"could not find `interface {name} {{` in source"
    start = match.start()
    end_match = re.search(r"\n\t\}", source[start:])
    assert end_match, f"could not find end of interface {name}"
    return source[start : start + end_match.end()]


def _derived_body(source: str, name: str) -> str:
    """Extract a script-level `let {name} = $derived.by(() => { ... });` body."""
    match = re.search(rf"let\s+{re.escape(name)}\s*=\s*\$derived\.by\(", source)
    assert match, f"could not find `let {name} = $derived.by(` in source"
    start = match.start()
    end_match = re.search(r"\}\);", source[start:])
    assert end_match, f"could not find end of derived {name}"
    return source[start : start + end_match.end()]


def _effect_body(source: str, marker: str) -> str:
    """Extract the `$effect(() => { ... });` block whose body starts with `marker`
    (there is more than one $effect block in the file, e.g. inside comboOutsideClick)."""
    for match in re.finditer(r"\$effect\(\(\) => \{", source):
        start = match.start()
        end_match = re.search(r"\}\);", source[start:])
        assert end_match, "could not find end of $effect block"
        body = source[start : start + end_match.end()]
        if marker in body[:200]:
            return body
    raise AssertionError(f"could not find a $effect block whose body starts with {marker!r}")


def test_row_renders_exactly_four_data_cells() -> None:
    source = _source(RESOLVE_CARD_PATH)
    row_region = _row_region(source)
    count = row_region.count("<td")
    assert count == 4, f"RESOLVE-07: each row must render exactly four <td> cells, found {count}"


def test_side_toggle_and_person_control_share_the_resolved_as_cell() -> None:
    source = _source(RESOLVE_CARD_PATH)
    row_region = _row_region(source)
    cells = _table_cells(row_region)
    assert len(cells) == 4, f"expected 4 <td> cells in the row region, found {len(cells)}"
    resolved_as_cell = cells[1]
    toggle_idx = resolved_as_cell.find("{@render sideToggle(")
    dropdown_idx = resolved_as_cell.find("{@render personDropdown(")
    assert toggle_idx != -1, "RESOLVE-07: sideToggle must render inside the Resolved As cell"
    assert dropdown_idx != -1, "RESOLVE-07: personDropdown must render inside the Resolved As cell"
    assert toggle_idx < dropdown_idx, (
        "RESOLVE-07: the toggle must be stacked above the person control inside the merged cell"
    )


def test_row_match_state_has_no_confirm_correct_fields() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _interface_body(source, "RowMatchState")
    assert not re.search(r"\bdisposition\??:", body), (
        "RESOLVE-08: RowMatchState must not declare a disposition field — the confirm/correct "
        "distinction has no UI any more"
    )
    assert not re.search(r"\bcorrecting\??:", body), (
        "RESOLVE-08: RowMatchState must not declare a correcting field — the control is always rendered"
    )
    for field in ("personId", "extraCandidates", "comboQuery", "comboOpen", "comboHighlight"):
        assert field in body, f"RowMatchState must still declare {field}"


def test_all_dispositioned_gate_keys_on_person_id_only() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _derived_body(source, "allDispositioned")
    assert "personId" in body, "RESOLVE-08: allDispositioned must key on personId"
    assert not re.search(r"\.disposition\b", body), (
        "RESOLVE-08: allDispositioned must not reference a disposition member access — "
        "the gate is a single personId predicate now"
    )


def test_matches_payload_shape_is_unchanged() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _derived_body(source, "matchesJson")
    assert "raw_speaker_label" in body, (
        "the ?/resolve wire contract must still key on raw_speaker_label"
    )
    assert "person_id:" in body, "the ?/resolve wire contract must still key on person_id"
    assert not re.search(r"\bdisposition\b", body), (
        "RESOLVE-08: matchesJson must not reference disposition — proof the state-machine "
        "deletion did not touch the ?/resolve wire payload shape"
    )


def test_seeding_effect_falls_back_to_committed_person() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _effect_body(source, "if (!isPaused) return;")
    assert "auto_match_id" in body, "the seeding effect must still seed personId from auto_match_id"
    assert "person_id" in body, (
        "RESOLVE-08 delta 4: the seeding effect must fall back to the row's own committed "
        "person_id so an already-committed row does not seed as un-reviewed"
    )


def test_single_side_input_survives_the_column_merge() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count('name="side"') == 1, (
        "T-44-16: merging the toggle into the Resolved As cell must not drop or duplicate "
        "the single name=\"side\" submitting control"
    )
    form_region = _region(source, r'action="\?/saveResolveRow"', r"</form>")
    assert form_region.count('name="side"') == 1, (
        "T-44-16: the side field must still live inside the per-row hidden-form region "
        "after the column merge"
    )


def test_person_control_editable_predicate_exists() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function personControlEditable(" in source, (
        "T-44-17: personControlEditable must be a named function so the review-set scoping "
        "is in source rather than inline in markup"
    )
    body = _function_body(source, "personControlEditable")
    assert "discrepancy" in body, (
        "T-44-17: personControlEditable must reference the discrepancy field — the dropdown "
        "may only be editable for rows in the review set matchesJson serializes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-05, Task 3 checkpoint remediation — operator visual-acceptance defects
# fixed after the first Task 3 checkpoint was rejected: create-person moved
# inside the open popup, a combobox affordance icon, a neutral gated
# placeholder, and the Bench/Advocate toggle no longer discarding a
# previously-chosen specific advocate role.
# ─────────────────────────────────────────────────────────────────────────────


def _if_block(source: str, condition_literal: str) -> str:
    """Extract a nesting-aware `{#if {condition_literal}}...{/if}` block — mirrors
    `_snippet_body`'s brace-balanced approach but for #if blocks that may
    themselves contain nested #if blocks (e.g. per-candidate conditionals
    inside a listbox loop)."""
    start_token = "{#if " + condition_literal + "}"
    start = source.index(start_token)
    pos = start + len(start_token)
    depth = 1
    while depth > 0:
        next_if = source.find("{#if", pos)
        next_close = source.find("{/if}", pos)
        assert next_close != -1, f"unbalanced #if block for {condition_literal!r}"
        if next_if != -1 and next_if < next_close:
            depth += 1
            pos = next_if + len("{#if")
        else:
            depth -= 1
            pos = next_close + len("{/if}")
    return source[start:pos]


def test_create_person_trigger_lives_inside_the_open_listbox_popup() -> None:
    source = _source(RESOLVE_CARD_PATH)
    dropdown_body = _snippet_body(source, "personDropdown")
    assert dropdown_body.count("<CreatePersonPopover") == 1, (
        "exactly one create-person trigger should exist in the person control"
    )
    popup_block = _if_block(dropdown_body, "s!.comboOpen")
    assert "CreatePersonPopover" in popup_block, (
        "the create-person trigger must render inside the open listbox popup "
        "(Figma 4205:81 shows it as part of the combobox's own popup affordance) "
        "— not as a standalone element visible beneath the input regardless of "
        "whether the popup is open, which was the operator's checkpoint feedback"
    )


def test_person_combobox_has_a_dropdown_affordance_icon() -> None:
    source = _source(RESOLVE_CARD_PATH)
    dropdown_body = _snippet_body(source, "personDropdown")
    assert "<svg" in dropdown_body, (
        "the always-rendered person control must carry a visual combobox "
        "affordance (a chevron) so it reads as a dropdown rather than a plain "
        "text box — the operator's checkpoint feedback flagged the missing "
        "affordance against Figma node 4205:81"
    )
    svg_region = _region(dropdown_body, r"<svg", r"</svg>")
    assert 'aria-hidden="true"' in svg_region, (
        "the chevron is decorative and must not be exposed to the accessible name"
    )


def test_person_dropdown_placeholder_is_neutral_while_gated() -> None:
    source = _source(RESOLVE_CARD_PATH)
    dropdown_body = _snippet_body(source, "personDropdown")
    assert "Select person…" in dropdown_body, (
        "while a row's side has not yet been chosen, the placeholder must read "
        "as genuinely side-neutral rather than guessing Bench/Advocate from an "
        "unconfirmed, possibly ingestion-guessed side value"
    )
    placeholder_match = re.search(r"placeholder=\{gated", dropdown_body)
    assert placeholder_match, (
        "the placeholder expression must branch on the gated flag first, before "
        "falling back to the side-specific wording"
    )
    assert dropdown_body.count("Select bench…") == 1 and dropdown_body.count("Select advocate…") == 1, (
        "the side-specific placeholders must still exist for the non-gated case"
    )


def test_toggle_side_preserves_a_previously_chosen_advocate_role() -> None:
    """A real data-loss bug the operator hit while re-verifying this plan's
    checkpoint: `side` is the single stored column for both the Bench/Advocate
    toggle and the specific advocate role (PETITIONER/RESPONDENT/AMICUS)
    chosen via the Argument Role select. Before this fix, toggleSide's
    Advocate branch hardcoded 'UNKNOWN' on every click, so clicking
    Bench then Advocate silently discarded whatever specific role had already
    been chosen."""
    source = _source(RESOLVE_CARD_PATH)
    assert "lastAdvocateRole" in source, (
        "a per-row memory of the last specific advocate role must exist so "
        "toggling Bench then Advocate cannot silently discard it"
    )
    toggle_body = _function_body(source, "toggleSide")
    assert "lastAdvocateRole" in toggle_body, (
        "toggleSide's Advocate branch must consult the remembered role rather "
        "than unconditionally writing 'UNKNOWN'"
    )
    choose_body = _function_body(source, "chooseArgumentRole")
    assert "lastAdvocateRole" in choose_body, (
        "chooseArgumentRole must record the operator's specific role choice so "
        "a later Bench/Advocate toggle can restore it"
    )
