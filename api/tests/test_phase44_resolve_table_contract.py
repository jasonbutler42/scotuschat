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

Plan 44-07 adds: side-scoped candidates (RESOLVE-09) and the source-aware hint
prefix (RESOLVE-10) — see its own banner section below. It also re-points the
44-04 section's `test_resolve_card_has_exactly_four_hint_usages` prefix assertion
at the new derived `sourcePrefix` expression rather than the retired hardcoded
"Imported" literal; the test's other assertions and the five untouched-call-site
guards are unchanged.

Plan 44-08 adds: the three mutually-exclusive bench Argument Role states with
their canonical copy, the new-tab Edit person link, and the bench-conditional
Descriptor hint (RESOLVE-11/12/13/14) — see its own banner section below. It
re-points the 44-04 section's `test_hint_value_helpers_exist_and_...` test
(renamed `test_hint_value_helpers_exist_and_bench_fork_left_the_hint_layer`):
the bench fork moved out of `argumentRoleHintValue` and into the cell itself,
so the retired "N/A - from tenure" / "N/A - tenure not found" hint strings no
longer live in that helper. It also widens the 44-02 section's descriptor-cell
test to allow the new bench-conditional hint wrapper while still guarding that
the data-carrying `<input>` itself stays unconditionally in the DOM.

Plan 44-09 adds: the persistent header progress line, the always-visible
reason-disabled Continue button, and the AUTO-MATCHED/NEEDS YOU row cue tags
(RESOLVE-15/16) — see its own banner section below. Both `rowCueTag` and the
two tag strings appear exactly once each in the source: `rowCueTag` carries no
explicit return-type annotation (TypeScript infers the two-literal union from
its return statements) precisely so each tag string is written once, not
twice, keeping this file's own single-occurrence contract satisfiable.

Plan 44-09's Task 4 second checkpoint remediation (see its own banner section
at the end of this file) fixes: a confirmed descriptor data-loss bug
(toggling Advocate -> Bench -> Advocate could submit an empty string over an
already-saved descriptor) and a person-selection-survives-a-side-switch bug,
and re-points every test this round's pill/position/structural fixes touched:
the progress indicator (now a pill), the row cue tags (now pills, in a
corrected position, with a fixed AUTO-MATCHED color), the Continue button's
disabled label (now the button's own text, not a separate aria-described
paragraph), and the Resolved As cell's hint (the Bench/Advocate hint and the
Name hint merge into one combined line, dropping the file's hint call-site
count from four to three).

Plan 44-09's Task 4 THIRD checkpoint round adds a MANUALLY MATCHED row cue
tag, requested by the operator after the second-round remediation above was
independently verified. This is a deliberate REVERSAL of RESOLVE-16's
originally-stated rule that "a row whose person the operator picked
themselves carries neither tag" (see 44-05-PLAN.md and the second-round
remediation banner's own exclusion note near the end of this file, both of
which record the now-superseded rule) — the operator's own reasoning,
recorded verbatim in 44-09-SUMMARY.md, is that provenance ("a human decided
this" vs. "the machine suggested this, untouched") is itself worth
disclosing, not omitting. `rowCueTag` now returns a three-literal union;
each of the three tag strings still appears exactly once in the source (one
declaration inside `rowCueTag`, no second literal anywhere else), preserving
this file's single-occurrence contract at three terms instead of two.

Plan 44-09's tenure-preview follow-up (raised by the operator immediately
after the hint-freeze fix above was confirmed as "a huge improvement") adds
a live preview of a bench pick's tenure-derived Argument Role before the
batch ?/resolve commit writes it — see its own banner section at the end of
this file, and api/tests/test_phase44_bench_role_preview.py for the backing
endpoint's own tests.
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
    # Plan 44-08 (RESOLVE-13) re-point: the hint block below the input is now
    # wrapped in `{#if side !== 'BENCH'}`, but the data-carrying <input> itself
    # must still render before and outside that wrapper — Phase 27 CR-01/CR-02
    # requires the input stay in the DOM unconditionally; only the hint may be
    # bench-gated.
    input_idx = body.index("<input")
    hint_condition_idx = body.index("{#if side !== 'BENCH'}")
    assert input_idx < hint_condition_idx, (
        "RESOLVE-04/RESOLVE-13: the data-carrying <input> must render before and outside "
        "the bench-conditional hint wrapper introduced by Plan 44-08"
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


def test_resolve_card_has_exactly_three_hint_usages() -> None:
    """Task 4 checkpoint remediation (44-09, item 5) re-point: the Resolved As
    cell's separate Bench/Advocate hint and Name hint (two call sites) merged
    into one combined hint, dropping the file's total from four call sites to
    three (Resolved As, Argument Role, Descriptor)."""
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("<CopyableExtractedValue") == 3, (
        "RESOLVE-05/checkpoint remediation: exactly three CopyableExtractedValue "
        "usages must exist in ResolveCard.svelte after the Resolved As hint merge"
    )
    # Plan 44-07 (RESOLVE-10) re-point: the hints pass the derived sourcePrefix
    # expression instead of a hardcoded "Imported" literal — see the Plan
    # 44-07 banner below for the dedicated sourcePrefix assertions.
    assert source.count("prefixLabel={sourcePrefix}") == 3, (
        "RESOLVE-05/RESOLVE-10: all three hints must pass the derived sourcePrefix expression"
    )
    assert not re.search(r'prefixLabel="[A-Za-z]+"', source), (
        "RESOLVE-10: no hardcoded prefix-label string may remain on any call site in this file"
    )
    assert source.count("raw={null}") == 3, (
        "RESOLVE-05: all three hints must pass an explicitly-null raw prop"
    )
    assert not re.search(r"confidence=", source), "RESOLVE-05: no hint may pass a confidence prop"


def test_resolve_card_hint_copy_labels_each_appear_once() -> None:
    """Task 4 checkpoint remediation (44-09, item 5) re-point: "Copy side" and
    "Copy raw label" no longer exist as separate call sites — the merged
    Resolved As hint uses a single "Copy resolved as" label."""
    source = _source(RESOLVE_CARD_PATH)
    for label in ("Copy resolved as", "Copy argument role", "Copy descriptor"):
        assert source.count(f'copyLabel="{label}"') == 1, f"expected exactly one copyLabel={label!r}"
    assert 'copyLabel="Copy side"' not in source, (
        "checkpoint remediation: the separate side-only hint call site is retired"
    )
    assert 'copyLabel="Copy raw label"' not in source, (
        "checkpoint remediation: the separate name-only hint call site is retired"
    )


def test_hint_value_helpers_exist_and_bench_fork_left_the_hint_layer() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function resolvedAsHintValue(" in source, "RESOLVE-05: resolvedAsHintValue helper must exist"
    assert "function sideHintValue(" in source, "RESOLVE-05: sideHintValue helper must exist"
    assert "function argumentRoleHintValue(" in source, "RESOLVE-05: argumentRoleHintValue helper must exist"
    body = _function_body(source, "argumentRoleHintValue")
    # Plan 44-08 (RESOLVE-12) re-point: the bench fork moved out of the hint
    # layer and into argumentRoleCell/benchRoleState — the bench role was
    # never an ingested value, so the helper no longer answers for bench at
    # all, and the retired "N/A - ..." hint strings must not live here.
    assert "missing_tenure" not in body, (
        "RESOLVE-12: argumentRoleHintValue must no longer fork on missing_tenure — that fork "
        "now lives in benchRoleState, not the hint layer"
    )
    assert "N/A - from tenure" not in body, (
        "RESOLVE-12: the retired valid-tenure bench hint text must not live inside this helper"
    )
    assert "N/A - tenure not found" not in body, (
        "RESOLVE-12: the retired missing-tenure bench hint text must not live inside this helper"
    )


def test_combined_resolved_as_hint_value_reuses_the_two_retired_call_sites_own_logic() -> None:
    """Task 4 checkpoint remediation (44-09, item 5, confirmed via Figma): the
    Bench/Advocate hint and the Name hint merge into one combined line —
    "{SideLabel} · {NameOrN/A}", or bare "N/A" while the side gate is still
    open. The per-field logic itself (sideHintValue's gated/label fork,
    resolvedAsHintValue's raw-label-or-null fork) must not change — only the
    combination is new."""
    source = _source(RESOLVE_CARD_PATH)
    assert "function combinedResolvedAsHintValue(" in source, (
        "a single combined hint-value helper must exist for the merged Resolved As hint"
    )
    body = _function_body(source, "combinedResolvedAsHintValue")
    assert "sideHintValue(" in body, (
        "the combined helper must reuse sideHintValue's own gated/label logic, not duplicate it"
    )
    assert "resolvedAsHintValue(" in body, (
        "the combined helper must reuse resolvedAsHintValue's own raw-label-or-null logic, "
        "not duplicate it"
    )
    assert "' · '" in body or '" · "' in body or "` · `" in body or "·" in body, (
        "the combined value must join side and name with the Figma-confirmed middle-dot separator"
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


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-07 — RESOLVE-09/10: side-scoped candidates, source-aware hint prefix
# ─────────────────────────────────────────────────────────────────────────────

PAGE_SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.server.ts"
PAGE_SVELTE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.svelte"


def test_side_scoped_candidates_filter_exists_and_wraps_the_merge() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function sideScopedCandidates(" in source, (
        "RESOLVE-09: sideScopedCandidates must exist as a named function"
    )
    body = _function_body(source, "sideScopedCandidates")
    assert body.count("getRowCandidates(") == 1, (
        "RESOLVE-09: sideScopedCandidates must wrap getRowCandidates exactly once — the "
        "merge/de-dupe contract is reused, not replaced"
    )


def test_side_scoped_candidates_filters_on_is_justice_not_labels() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "sideScopedCandidates")
    assert "is_justice" in body, "RESOLVE-09: the filter must reference is_justice"
    assert "role_name" not in body, (
        "RESOLVE-09: the filter must not reference role_name — no name/label heuristic"
    )
    assert "SIDE_LABEL" not in body, (
        "RESOLVE-09: the filter must not reference SIDE_LABEL — no name/label heuristic"
    )


def test_side_scoped_candidates_fails_open_on_unknown_side() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "sideScopedCandidates")
    assert re.search(r"is_justice\s*==\s*null|is_justice\s*===\s*undefined|is_justice\s*\?\?", body), (
        "RESOLVE-09 fail-open: a candidate whose is_justice is unknown (present only in a "
        "stale discrepancies snapshot) must be kept, not dropped from both sides"
    )


def test_side_scoped_candidates_skips_filtering_while_gated() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "sideScopedCandidates")
    assert "gated" in body, "RESOLVE-09: the filter must reference the gated parameter"
    assert re.search(r"if \(gated\)", body), (
        "RESOLVE-09: while the side gate is open, the list must be returned unfiltered — "
        "no side has been chosen, so filtering it would be filtering nothing"
    )


def test_person_dropdown_uses_the_side_scoped_list() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "personDropdown")
    assert "sideScopedCandidates(" in body, (
        "RESOLVE-09: personDropdown must call sideScopedCandidates for the rendered list"
    )
    assert "getRowCandidates(" not in body, (
        "RESOLVE-09: personDropdown must not call getRowCandidates directly any more — "
        "sideScopedCandidates is the sole entry point now"
    )


def test_candidate_interface_carries_is_justice() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _interface_body(source, "Candidate")
    assert "is_justice" in body, "RESOLVE-09: the Candidate interface must declare is_justice"


def test_created_person_is_enriched_with_a_side() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "handlePersonCreated")
    assert "is_justice" in body, (
        "RESOLVE-09: handlePersonCreated must enrich the created candidate with is_justice, "
        "derived from the side already known at creation time"
    )


def test_load_people_type_carries_is_justice_and_no_bogus_role_name() -> None:
    source = _source(PAGE_SERVER_PATH)
    match = re.search(r"let people: Array<\{[^}]*\}>", source)
    assert match, "could not find the `people` local's declared type in +page.server.ts"
    region = match.group(0)
    assert "is_justice" in region, "RESOLVE-09: the people local's type must carry is_justice"
    assert "role_name" not in region, (
        "RESOLVE-09: the people local's type must not carry role_name — it is not a real "
        "PersonListItem field and the annotation had been wrong since it was written"
    )


def test_create_person_trigger_is_side_scoped() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("Create new advocate") == 1, (
        "RESOLVE-09: the advocate-side create-person trigger label must appear exactly once"
    )
    assert source.count("Create new bench person") == 1, (
        "RESOLVE-09: the bench-side create-person trigger label must appear exactly once"
    )


def test_source_prefix_is_derived_from_the_source_prop() -> None:
    source = _source(RESOLVE_CARD_PATH)
    match = re.search(r"let sourcePrefix = \$derived\(([^;]*)\);", source)
    assert match, "RESOLVE-10: sourcePrefix must be declared as a derived value"
    assert "'corpus'" in match.group(1), (
        "RESOLVE-10: the sourcePrefix expression must branch on the 'corpus' literal"
    )


def test_resolve_card_props_declares_the_source_prop() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _interface_body(source, "ResolveCardProps")
    assert "source: 'pdf' | 'corpus';" in body, (
        "RESOLVE-10: ResolveCardProps must declare source as the two-literal union"
    )


def test_page_passes_source_from_load_data_not_the_polled_copy() -> None:
    source = _source(PAGE_SVELTE_PATH)
    region = _region(source, r"<ResolveCard", r"/>")
    assert "source={data.job.source" in region, (
        "RESOLVE-10: the <ResolveCard> call site must pass source from the load data (data.job)"
    )
    assert "source={liveJob" not in region, (
        "RESOLVE-10: the source prop must not read from the 1s-polled liveJob copy — a job's "
        "ingestion source is immutable for the life of the job"
    )


def test_source_is_not_rederived_client_side() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "ImportRun" not in source, (
        "RESOLVE-10: the component must not reference the internal ImportRun identifier"
    )
    assert "convokit" not in source, (
        "RESOLVE-10: the component must not reference the internal import-strategy vocabulary"
    )


def test_copyable_extracted_value_default_prefix_unchanged() -> None:
    source = _source(COPYABLE_PATH)
    assert "prefixLabel = 'Extracted'" in source, (
        "RESOLVE-10: CopyableExtractedValue's app-wide default prefix must be unchanged — "
        "44-07 did not quietly move the default"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-08 — RESOLVE-11/12/13/14: bench copy, new-tab link, read-only parity
# ─────────────────────────────────────────────────────────────────────────────


def test_calculated_from_tenure_copy_present_once() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("Calculated from tenure") == 1, (
        "RESOLVE-12: the calculated-bench-role copy must appear exactly once"
    )


def test_tenure_not_found_copy_present_once() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("Tenure not found") == 1, (
        "RESOLVE-12: the missing-tenure copy must appear exactly once"
    )


def test_retired_bench_hint_strings_are_gone() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "N/A - from tenure" not in source, (
        "RESOLVE-12: the retired ingestion-prefixed valid-tenure bench hint must not exist anywhere"
    )
    assert "N/A - tenure not found" not in source, (
        "RESOLVE-12: the retired ingestion-prefixed missing-tenure bench hint must not exist anywhere"
    )


def test_argument_role_hint_is_bench_conditional() -> None:
    source = _source(RESOLVE_CARD_PATH)
    row_region = _row_region(source)
    cells = _table_cells(row_region)
    argument_role_cell = cells[2]
    condition_idx = argument_role_cell.find("{#if side !== 'BENCH'}")
    call_idx = argument_role_cell.find("<CopyableExtractedValue")
    assert condition_idx != -1, (
        "RESOLVE-12: the Argument Role <td> must guard its hint with a non-bench condition"
    )
    assert call_idx != -1, "RESOLVE-12: the Argument Role <td> must still call the hint component"
    assert condition_idx < call_idx, (
        "RESOLVE-12: the non-bench condition must wrap the hint call, not follow it"
    )


def test_unresolved_bench_copy_present_once_and_carries_no_dash() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("(resolve person first)") == 1, (
        "RESOLVE-14: the unresolved-bench copy must appear exactly once"
    )
    body = _snippet_body(source, "argumentRoleCell")
    region = _region(
        body,
        r"\(resolve person first\)",
        r"\{:else if benchState === 'calculated'\}",
    )
    assert "–" not in region, (
        "RESOLVE-14: the unresolved bench branch must carry no en dash — the truth is 'not yet "
        "computable', not 'does not apply'"
    )
    assert "CopyableExtractedValue" not in region, (
        "RESOLVE-14: the unresolved bench branch must carry no hint call"
    )


def test_bench_role_state_predicate_exists_and_orders_unresolved_first() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function benchRoleState(" in source, (
        "RESOLVE-11/12/14: benchRoleState must exist as a single named predicate driving all "
        "three bench branches"
    )
    body = _function_body(source, "benchRoleState")
    assert "person_id" in body, "RESOLVE-14: benchRoleState must fork on row.person_id"
    unresolved_idx = body.index("'unresolved'")
    calculated_idx = body.index("'calculated'")
    assert unresolved_idx < calculated_idx, (
        "RESOLVE-14: the unresolved return must be checked before the calculated return — the "
        "service reports missing_tenure=false for an unresolved bench row, so checking "
        "calculated first would render an empty locked box"
    )


def test_bench_role_state_ignores_editability() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "benchRoleState")
    assert "rowEditable" not in body, (
        "RESOLVE-11: benchRoleState must not reference the editability flag — this is what "
        "makes the read-only card render the same three bench states as the editable card"
    )


# Both anchor-region tests below are re-pointed for the tenure-preview
# follow-up: the if-condition legitimately grew a second disjunct
# (`|| previewedPersonId != null`) so the Edit person link still renders for
# an uncommitted preview pick, not only a committed row's own
# person_edit_href. The anchor markup itself (new-tab target, noopener,
# aria-hidden glyph) is unchanged — only the region's start pattern moved.
def test_edit_person_link_opens_in_a_new_tab_with_noopener() -> None:
    source = _source(RESOLVE_CARD_PATH)
    anchor_region = _region(source, r"\{#if row\.person_edit_href \|\| previewedPersonId != null\}", r"</a>")
    assert 'target="_blank"' in anchor_region, (
        "RESOLVE-11: the Edit person link must open in a new tab"
    )
    assert 'rel="noopener"' in anchor_region, (
        "T-44-31: the Edit person link must carry rel=\"noopener\" to sever the opened tab's "
        "window.opener handle back to this admin page"
    )


def test_edit_person_accessible_name_excludes_the_glyph() -> None:
    source = _source(RESOLVE_CARD_PATH)
    anchor_region = _region(source, r"\{#if row\.person_edit_href \|\| previewedPersonId != null\}", r"</a>")
    assert re.search(r'>Edit person<span aria-hidden="true">[^<]*↗</span></a>', anchor_region), (
        "RESOLVE-11: the ↗ glyph must sit inside its own aria-hidden span, after the anchor's "
        "own text run, so the accessible name stays exactly 'Edit person'"
    )


def test_descriptor_hint_is_bench_conditional() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "descriptorCell")
    assert body.count("<CopyableExtractedValue") == 1, (
        "RESOLVE-13: exactly one hint call site must exist in descriptorCell"
    )
    condition_idx = body.index("{#if side !== 'BENCH'}")
    call_idx = body.index("<CopyableExtractedValue")
    assert condition_idx < call_idx, (
        "RESOLVE-13: the non-bench condition must wrap the hint call, not follow it"
    )


def test_bench_descriptor_branch_renders_only_a_dash() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "descriptorCell")
    bench_branch = _region(body, r"\{#if side === 'BENCH'\}", r"\{:else if rowEditable\}")
    assert "–" in bench_branch, "RESOLVE-13: the bench branch must render the muted en dash"
    assert "CopyableExtractedValue" not in bench_branch, (
        "RESOLVE-13: the bench branch itself must carry no hint call"
    )


def test_all_bench_branches_are_independent_of_editability() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "argumentRoleCell")
    unresolved_region = _region(
        body, r"benchState === 'unresolved'", r"\{:else if benchState === 'calculated'\}"
    )
    calculated_region = _region(
        body, r"benchState === 'calculated'", r"\{:else if benchState === 'missing-tenure'\}"
    )
    missing_tenure_region = _region(
        body, r"benchState === 'missing-tenure'", r"\{:else if rowEditable\}"
    )
    for name, region in (
        ("unresolved", unresolved_region),
        ("calculated", calculated_region),
        ("missing-tenure", missing_tenure_region),
    ):
        # Trim the trailing `{:else if ...}` boundary marker itself — for the
        # missing-tenure branch that boundary is literally `{:else if
        # rowEditable}`, which is the *next* branch's own guard, not a
        # reference made by this branch.
        content = region[: region.rfind("{:else if")]
        assert "rowEditable" not in content, (
            f"RESOLVE-11: the {name} bench branch must not reference the editability flag — "
            "this is what makes the read-only card render it identically"
        )


def test_four_headers_render_in_readonly_too() -> None:
    source = _source(RESOLVE_CARD_PATH)
    thead_region = _region(source, r"<thead>", r"</thead>")
    assert "rowEditable" not in thead_region, (
        "RESOLVE-11/canonical point 10: the table headers must not be gated by editability — "
        "the read-only card keeps its four headers"
    )
    assert "readonlyMode" not in thead_region, (
        "RESOLVE-11/canonical point 10: the table headers must not reference readonlyMode"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-09 — RESOLVE-15/16: progress indicator, reason-disabled Continue,
# row cue tags
# ─────────────────────────────────────────────────────────────────────────────


def test_progress_copy_present_for_both_states() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("still need review") == 1, (
        "RESOLVE-15: the countdown progress string must appear exactly once"
    )
    assert source.count("speakers reviewed") == 1, (
        "RESOLVE-15: the all-reviewed progress string must appear exactly once"
    )


def test_progress_indicator_is_a_pill_with_a_status_colored_dot() -> None:
    """Task 4 checkpoint remediation (44-09, item 4, confirmed via Figma
    get_design_context on node 4207:116; dot fills confirmed via raw SVG):
    a pill (dark fill, bordered, rounded) containing a 6x6px colored dot
    (amber while rows remain, green once all are reviewed) plus the existing
    text — not a bare paragraph."""
    source = _source(RESOLVE_CARD_PATH)
    region = _region(source, r'id="resolve-progress"', r"</div>")
    assert "border-radius: 12px" in region, "the progress pill must be rounded per Figma node 4207:116"
    assert "width: 6px" in region and "height: 6px" in region, (
        "the status dot must be exactly 6x6px per Figma node 4207:116"
    )
    assert "border-radius: 50%" in region, "the status dot must be a circle"
    assert "#fbbf24" in region and "#4ade80" in region, (
        "the dot must fork between the amber (remaining > 0) and green (all resolved) fills "
        "confirmed against the live mockup's raw SVG"
    )


def test_progress_indicator_is_positioned_inline_with_the_heading() -> None:
    """Task 4 checkpoint remediation (44-09, item 4): per Figma, the pill sits
    right-aligned in the same row as the "Resolve" heading, not stacked
    beneath it."""
    source = _source(RESOLVE_CARD_PATH)
    heading_match = re.search(r"<h2[^>]*>\s*Resolve\s*</h2>", source)
    assert heading_match, "the Resolve heading must exist"
    heading_idx = heading_match.start()
    pill_idx = source.find('id="resolve-progress"')
    assert pill_idx != -1, "the progress pill must exist"
    assert heading_idx < pill_idx, (
        "the heading must precede the pill in source order, consistent with the pill "
        "rendering to the right of the heading in the shared flex row"
    )
    between = source[heading_idx:pill_idx]
    assert "</h2>" in between, (
        "the heading and the pill must share one flex row (the heading closes before the "
        "pill's own conditional block begins, both inside the same wrapping row element)"
    )


def test_progress_derives_from_the_same_person_id_predicate() -> None:
    source = _source(RESOLVE_CARD_PATH)
    progress_body = _derived_body(source, "reviewProgress")
    disposition_body = _derived_body(source, "allDispositioned")
    shared_predicate = "rowMatchStates[d.raw_speaker_label]?.personId"
    assert shared_predicate in progress_body, (
        "RESOLVE-15/T-44-36: reviewProgress must read the exact same "
        "rowMatchStates[...].personId predicate allDispositioned uses"
    )
    assert shared_predicate in disposition_body, (
        "RESOLVE-15/T-44-36: allDispositioned must still read that same predicate — "
        "if either body drifts to a different field, the count and the gate can disagree"
    )


def test_continue_footer_is_not_gated_on_completeness() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "{#if isPaused && allDispositioned}" not in source, (
        "RESOLVE-15: the retired combined condition must not exist anywhere — the footer "
        "renders whenever the job is paused, not only once every row is dispositioned"
    )


def test_continue_button_is_disabled_by_completeness_inside_the_form() -> None:
    source = _source(RESOLVE_CARD_PATH)
    form_region = _region(source, r'action="\?/resolve"', r"</form>")
    assert re.search(r"disabled=\{[^}]*allDispositioned[^}]*\}", form_region), (
        "RESOLVE-15: the ?/resolve form region must contain a disabled= attribute "
        "referencing allDispositioned"
    )
    assert 'name="matches"' in form_region, (
        "RESOLVE-15: the ?/resolve payload input must still exist inside the form region"
    )


def test_disabled_reason_is_the_buttons_own_visible_text() -> None:
    """Task 4 checkpoint remediation (44-09, item 3, confirmed via Figma nodes
    4207:119/4210:218): both button states are ONE <button> with ONE text
    node — the reason replaces the label entirely rather than living beside
    it in a separate paragraph. Since the reason is now the button's own
    visible text, it is already part of the accessible name — no
    aria-describedby wiring is needed, and the old separate paragraph is
    retired along with it."""
    source = _source(RESOLVE_CARD_PATH)
    form_region = _region(source, r'action="\?/resolve"', r"</form>")
    assert "aria-describedby" not in form_region, (
        "checkpoint remediation: no separate reason paragraph exists any more to describe"
    )
    assert "resolve-continue-reason" not in form_region, (
        "checkpoint remediation: the retired standalone reason paragraph's id must be gone"
    )
    button_region = _region(form_region, r"<button", r"</button>")
    assert "more to continue" in button_region, (
        "the disabled reason must be the button's own template-literal text content"
    )
    assert "Continue Resolve" in button_region, (
        "the enabled label must still be the button's own text content"
    )


def test_continue_enabled_label_unchanged() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("Continue Resolve") == 1, (
        "RESOLVE-15: the enabled Continue label must be unchanged and appear exactly once"
    )


def test_progress_line_carries_no_speaker_characterisation() -> None:
    """Task 4 checkpoint remediation (44-09, item 4) re-point: the progress
    line is now a `<div id="resolve-progress">` pill (Figma node 4207:116),
    not a bare `<p>`."""
    source = _source(RESOLVE_CARD_PATH)
    region = _region(source, r'id="resolve-progress"', r"</div>")
    assert "Bench" not in region and "Advocate" not in region, (
        "RESOLVE-15/CLAUDE.md apolitical constraint: the progress line must report a single "
        "count of rows needing review, never a count split by kind of speaker"
    )


def test_all_three_cue_tag_labels_present_once() -> None:
    """RESOLVE-16, superseded rule (Task 4, third checkpoint round): the
    operator explicitly requested a third tag for a self-picked row, reversing
    44-05's original "carries neither tag" rule for provenance-disclosure
    reasons (see 44-09-SUMMARY.md). All three tag strings must each still
    appear exactly once in the source — one declaration per literal, no
    duplicate quoting anywhere else."""
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("AUTO-MATCHED") == 1, "RESOLVE-16: the auto-matched tag string must appear exactly once"
    assert source.count("NEEDS YOU") == 1, "RESOLVE-16: the needs-attention tag string must appear exactly once"
    assert source.count("MANUALLY MATCHED") == 1, (
        "RESOLVE-16 (superseded): the manually-matched tag string must appear exactly once"
    )


def test_row_cue_tag_predicate_exists_and_orders_needs_attention_first() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function rowCueTag(" in source, "RESOLVE-16: rowCueTag must exist as a named predicate"
    body = _function_body(source, "rowCueTag")
    needs_idx = body.index("'NEEDS YOU'")
    auto_idx = body.index("'AUTO-MATCHED'")
    assert needs_idx < auto_idx, (
        "RESOLVE-16/T-44-35: the needs-attention return must precede the auto-matched return — "
        "that ordering is what makes a suggested-but-still-gated row read as needing the "
        "operator rather than as already handled"
    )


def test_row_cue_tag_manually_matched_is_the_third_and_final_fallback() -> None:
    """RESOLVE-16, superseded rule (Task 4, third checkpoint round): the
    manually-matched branch must come after BOTH the needs-attention and the
    auto-matched checks in source order (so it is only reachable once neither
    of those has already returned), and must reference `personId` — the same
    field the needs-attention check reads — so it is legible as "this row
    has a chosen person that isn't the untouched suggestion", not an
    independent, possibly-overlapping condition."""
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "rowCueTag")
    needs_idx = body.index("'NEEDS YOU'")
    auto_idx = body.index("'AUTO-MATCHED'")
    manual_idx = body.index("'MANUALLY MATCHED'")
    assert needs_idx < manual_idx and auto_idx < manual_idx, (
        "RESOLVE-16 (superseded): the manually-matched return must be the last of the three, "
        "reached only when neither the needs-attention nor the auto-matched check has already "
        "returned — this is what keeps the three states mutually exclusive by construction"
    )
    assert "personId" in body[auto_idx:manual_idx] or "personId" in body[:needs_idx], (
        "RESOLVE-16 (superseded): the manually-matched branch's reachability must depend on "
        "personId (via the needs-attention check above it already having required it to be "
        "non-null) — the branch is an operator pick precisely because it survived that check"
    )


def test_row_cue_tag_excludes_readonly_and_non_review_rows() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "rowCueTag")
    assert "interactive" in body, (
        "RESOLVE-16: rowCueTag must reference the interactive flag — the read-only card "
        "renders no cue tags"
    )
    assert "discrepancy" in body, (
        "RESOLVE-16: rowCueTag must reference the discrepancy field — a row outside the "
        "review set carries no tag"
    )


def test_row_cue_tag_requires_an_untouched_suggestion() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "rowCueTag")
    assert "auto_match_id" in body, "RESOLVE-16: rowCueTag must reference auto_match_id"
    assert "s.personId === row.discrepancy.auto_match_id" in body, (
        "RESOLVE-16/T-44-35: rowCueTag must compare the current personId against the "
        "suggestion's own id, so an operator-changed row loses the auto-matched tag"
    )


def test_cue_tag_renders_between_the_person_dropdown_and_the_hint() -> None:
    """Task 4 checkpoint remediation (44-09, item 2) re-point: per the actual
    Figma frame (node 4205:81, confirmed via get_metadata), the corrected
    order inside the Resolved As cell is (1) toggle, (2) person control, (3)
    the tag, (4) the combined hint — the tag no longer renders above the
    toggle."""
    source = _source(RESOLVE_CARD_PATH)
    row_region = _row_region(source)
    cells = _table_cells(row_region)
    resolved_as_cell = cells[1]
    dropdown_idx = resolved_as_cell.find("{@render personDropdown(")
    tag_idx = resolved_as_cell.find("{#if cueTag}")
    hint_idx = resolved_as_cell.find("<CopyableExtractedValue")
    assert dropdown_idx != -1, "the person control must still render inside the Resolved As cell"
    assert tag_idx != -1, "RESOLVE-16: the cue tag conditional must render inside the Resolved As cell"
    assert hint_idx != -1, "the combined hint must still render inside the Resolved As cell"
    assert dropdown_idx < tag_idx < hint_idx, (
        "the tag must render after the person control and before the combined hint, per the "
        "corrected Figma read of node 4205:81"
    )


def test_cue_tag_is_a_pill_with_correct_colors() -> None:
    """Task 4 checkpoint remediation (44-09, item 2, confirmed via Figma
    get_design_context on nodes 4183:23/4183:25 and instance 4205:111):
    border + rounded corners + padding + typography, no background fill.
    AUTO-MATCHED must use the approved Success/Bench-active token (#4ade80)
    rather than the muted token (#94a3b8) the prior plain-text treatment
    wrongly used for it. Third checkpoint round: the new MANUALLY MATCHED
    state legitimately DOES use the muted token (#94a3b8) — it is neither a
    warning nor a success signal, so the accent token stays reserved for
    interactive elements only, per UI-SPEC."""
    source = _source(RESOLVE_CARD_PATH)
    tag_region = _region(source, r"\{#if cueTag\}", r"</span>")
    assert "border: 1px solid" in tag_region, "the cue tag must carry a 1px solid border"
    assert "border-radius: 4px" in tag_region, "the cue tag must carry a 4px border radius"
    assert "padding: 2px 8px" in tag_region, "the cue tag must carry the confirmed pill padding"
    assert "font-size: 11px" in tag_region, "the cue tag must carry the confirmed 11px type size"
    assert "letter-spacing: 0.22px" in tag_region, (
        "the cue tag must carry the confirmed 0.22px letter spacing (not the old 0.04em)"
    )
    assert "#4ade80" in tag_region, (
        "the AUTO-MATCHED state must use the approved Success/Bench-active token (#4ade80), "
        "not the muted token — this was a confirmed color bug, not just a missing border"
    )
    assert "#fbbf24" in tag_region, (
        "the NEEDS YOU state must keep the approved warning token (#fbbf24)"
    )
    assert "#94a3b8" in tag_region, (
        "RESOLVE-16 (superseded): the MANUALLY MATCHED state must use the muted token "
        "(#94a3b8) — neutral, since it is neither a warning nor a success signal"
    )
    assert "#93c5fd" not in tag_region, (
        "UI-SPEC Color table: the accent token is reserved for interactive elements — a "
        "cue tag is non-interactive text"
    )
    assert not re.search(r"background\s*:", tag_region), (
        "RESOLVE-16: the cue tag must use no background fill, only a border and a text color"
    )


def test_cue_tag_evaluated_once_per_row() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert source.count("rowCueTag(") == 2, (
        "RESOLVE-16: rowCueTag must be referenced exactly twice — one declaration, one call — "
        "so the predicate is evaluated once per row, not once to test and once to render"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-09, Task 4 second checkpoint remediation — operator visual-acceptance
# defects fixed after the second Task 4 checkpoint (full 44-05..44-09 Figma
# reconciliation acceptance) was rejected with specific, Figma-confirmed
# feedback: a confirmed descriptor data-loss bug (toggling Advocate -> Bench
# -> Advocate could submit an empty string over an already-saved descriptor),
# a person selection surviving a Bench<->Advocate side switch despite the two
# candidate pools being disjoint, plus the pill/position/structural fixes
# covered by the re-pointed tests above (progress pill, cue tag pill and
# position, the combined Resolved As hint, and the Continue button's
# self-describing disabled label). Explicitly out of scope and untouched by
# this remediation: the dedicated typeahead redesign, the
# dropdown-open-causes-card-scrollbar layout issue, and the hint-mirrors-
# live-value finding (confirmed pre-existing from 44-04, already tracked as
# backlog).
#
# UPDATE (Task 4, third checkpoint round): the "manually-matched" third tag
# state noted above as out-of-scope/contradicts-RESOLVE-16 was requested by
# the operator immediately after this remediation round was independently
# verified. RESOLVE-16's "neither tag" rule is deliberately superseded — see
# the module docstring's own note above and 44-09-SUMMARY.md for the
# operator's stated provenance rationale. See the dedicated banner section
# further below for that state's own tests.
# ─────────────────────────────────────────────────────────────────────────────


def test_descriptor_input_uses_a_client_memory_that_survives_side_toggles() -> None:
    """Confirmed root cause: `list_resolve_rows_for_job` (44-06) correctly
    reports descriptor: null while a row is on BENCH (by design — "hidden,
    not shown"). Without a client-side memory, toggling
    Advocate -> Bench -> Advocate destroys an already-saved descriptor: the
    moment the Advocate branch re-renders, the descriptor <input> reappears
    bound to the now-null row.descriptor prop (''), and because toggleSide's
    own submitRow() fires synchronously in the same click (flushSync() then
    requestSubmit()), that empty string is submitted in the SAME request as
    the side change — and since side is no longer BENCH, the server writes
    descriptor="". This mirrors the pre-existing lastAdvocateRole pattern: a
    per-participant client-side memory that survives the row's own prop
    going null while hidden."""
    source = _source(RESOLVE_CARD_PATH)
    assert "lastDescriptorValue" in source, (
        "a per-participant client-side memory of the last-typed descriptor must exist so "
        "toggling Advocate -> Bench -> Advocate cannot submit an empty string over an "
        "already-saved value"
    )
    body = _snippet_body(source, "descriptorCell")
    assert re.search(
        r"value=\{lastDescriptorValue\[row\.participant_id\]\s*\?\?\s*row\.descriptor\s*\?\?\s*''\}",
        body,
    ), (
        "the descriptor input's value must prefer the client memory over the nullable "
        "server-reported prop, falling back to the prop only when no memory exists yet — "
        "so a row that already has a committed descriptor still shows it correctly on first "
        "render, with no separate seeding step needed"
    )
    assert re.search(r"oninput=\{", body), (
        "the memory must be captured via oninput, not only onblur — a side toggle auto-"
        "submits synchronously (flushSync() + requestSubmit()) and can fire before blur, so "
        "blur alone would miss an in-progress edit"
    )


def test_side_bucket_change_clears_the_previously_selected_person() -> None:
    """Confirmed real bug (item 6): when an operator selects Bench, picks a
    person, then switches to Advocate (or vice versa), the person selection
    must clear/reset rather than carry over — a person matched under one
    side must not silently remain selected after the side changes, since the
    candidate pools are disjoint (sideScopedCandidates, RESOLVE-09). Keyed on
    the BENCH/non-BENCH bucket (not the raw side value) so switching among
    the three specific advocate roles never clears the pick — only a real
    Bench<->Advocate flip does — and never on the first bucket recorded for a
    participant, so initial load/seeding is never mistaken for an
    operator-driven switch."""
    source = _source(RESOLVE_CARD_PATH)
    assert "function clearPersonOnSideBucketChange(" in source, (
        "a named function must own the side-bucket-change clearing rule"
    )
    body = _function_body(source, "clearPersonOnSideBucketChange")
    assert "personId = null" in body, "the clearing rule must reset personId"
    assert "comboQuery = ''" in body, "the clearing rule must reset comboQuery"
    assert "previousBucket !== undefined" in body, (
        "the rule must not fire on the first bucket ever recorded for a participant — "
        "initial load/seeding must never be mistaken for an operator-driven switch"
    )
    on_side_change_body = _function_body(source, "onSideChange")
    assert "clearPersonOnSideBucketChange(" in on_side_change_body, (
        "onSideChange (the toggle's and the non-gated argument-role select's shared write "
        "path) must invoke the clearing rule"
    )
    confirm_side_body = _function_body(source, "confirmSide")
    assert "clearPersonOnSideBucketChange(" in confirm_side_body, (
        "confirmSide (the gated toggle's own write path) must invoke the clearing rule too"
    )


def test_side_bucket_helper_treats_all_advocate_roles_as_one_bucket() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "function sideBucket(" in source, (
        "a named helper must map any side value onto the two-value BENCH/ADVOCATE bucket"
    )
    body = _function_body(source, "sideBucket")
    assert "'BENCH'" in body, "sideBucket must special-case the literal BENCH value"
    assert "'ADVOCATE'" in body, (
        "every other side value (UNKNOWN/PETITIONER/RESPONDENT/AMICUS) must collapse to the "
        "single ADVOCATE bucket, so switching among specific advocate roles never clears "
        "the person selection"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint remediation (44-09, third round) — the toggle's highlight must not
# disagree with the row's other cells about which side is active, and a
# refreshed page must not re-seed a person from the wrong side.
# ─────────────────────────────────────────────────────────────────────────────


def test_side_toggle_highlight_stays_gated_but_the_gate_is_seeded_correctly() -> None:
    # Corrected after a real regression: removing the gate check from the
    # highlight (so it read `side` alone) made an untouched row's default
    # 'UNKNOWN' side render as "Advocate active" — the toggle looked decided
    # while the person dropdown correctly stayed locked behind an explicit
    # click. The gate belongs in the highlight; the actual bug was that the
    # gate itself (sideGateConfirmed) was untrustworthy on a fresh page load.
    # See test_seeding_effect_seeds_side_gate_confirmed_from_unambiguous_evidence.
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "sideToggle")
    bench_active = _region(body, r"benchActive\s*=", r"\n")
    advocate_active = _region(body, r"advocateActive\s*=", r"\n")
    assert "!gated" in bench_active, (
        "benchActive must stay gated — an unconfirmed row's side defaults to 'UNKNOWN', "
        "and a bare `side === 'BENCH'` check would never falsely activate Bench for that "
        "case, but the mirror bug (below) does apply to the Advocate segment"
    )
    assert "!gated" in advocate_active, (
        "advocateActive must stay gated — without this, an untouched row's default "
        "'UNKNOWN' side satisfies `side !== 'BENCH'` and the toggle shows Advocate active "
        "while the person dropdown is still (correctly) locked behind an explicit click"
    )
    assert "side === 'BENCH'" in bench_active
    assert "side !== 'BENCH'" in advocate_active


def test_seeding_effect_seeds_side_gate_confirmed_from_unambiguous_evidence() -> None:
    # sideGateConfirmed is otherwise pure client memory that resets to
    # "locked" on every page load, even for a row explicitly confirmed in a
    # past session — this seeds it from server-side evidence a side was
    # already dealt with, so the gate (and therefore the toggle's highlight)
    # survives a refresh without guessing at the genuinely ambiguous case
    # (bare generic Advocate, no role picked yet — indistinguishable from a
    # truly untouched row, since both store side='UNKNOWN').
    source = _source(RESOLVE_CARD_PATH)
    assert "sideGateConfirmed[committedRow.participant_id] = true" in source, (
        "the seeding effect must set sideGateConfirmed for a row with unambiguous "
        "evidence of a prior confirmation"
    )
    marker = source.index("sideGateConfirmed[committedRow.participant_id] = true")
    seed_condition = source[source.rindex("if (", 0, marker) : marker]
    assert "committedRow.side !== 'UNKNOWN'" in seed_condition, (
        "a specific advocate role already saved is unambiguous proof of a prior "
        "confirmation and must unlock the gate on load"
    )
    assert "committedRow.person_id != null" in seed_condition, (
        "an already-committed person proves the full resolve flow (which requires a "
        "side) already ran for this row, and must also unlock the gate on load"
    )


def test_seeding_effect_drops_a_side_mismatched_auto_match() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "peopleIsJusticeById" in source, (
        "the seeding effect must build an is_justice lookup from the people prop so it can "
        "tell whether a candidate actually belongs to the row's current side"
    )
    assert "sideMismatch" in source, (
        "a bare `d.auto_match_id ?? committedRow?.person_id ?? null` fallback ignores which "
        "side the candidate belongs to, so a person cleared by a side switch silently "
        "reappeared on the next page load, still seeded from the pipeline's original "
        "(now wrong-side) auto-match"
    )
    assert "candidateIsJustice != null" in source, (
        "the mismatch check must fail open (RESOLVE-09 convention) when a candidate's "
        "is_justice is unknown — only a positively-confirmed mismatch drops the seed"
    )


def test_combined_hint_freezes_the_extracted_side_not_the_live_toggle() -> None:
    # Live operator testing found that combinedResolvedAsHintValue passed the
    # live `side` prop straight into sideHintValue, so the hint's text
    # changed every time Bench/Advocate was toggled — defeating its purpose
    # (comparing the operator's current decision against what the source
    # document actually said). Fixed by feeding it
    # `row.discrepancy?.extracted_side` — a value the pipeline now freezes
    # into the discrepancy blob before any operator edit can touch it.
    source = _source(RESOLVE_CARD_PATH)
    assert "extracted_side" in source, (
        "the Discrepancy interface and the combined hint must reference extracted_side"
    )
    body = _function_body(source, "combinedResolvedAsHintValue")
    assert "row.discrepancy?.extracted_side" in body, (
        "the combined hint must read the frozen extracted_side, not the live `side` "
        "parameter, for the value it feeds into sideHintValue"
    )
    assert "sideHintValue(extractedSide" in body, (
        "sideHintValue must be called with the frozen extractedSide, not the bare `side` "
        "prop — this is the exact regression the operator reported"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plan 44-09 tenure-preview follow-up (operator-approved during Task 4
# remediation) — a bench candidate's tenure-derived Argument Role must appear
# the moment the operator picks them, not only after the batch ?/resolve
# commit writes ArgumentParticipant.person_id. Backed by a new read-only
# endpoint (GET /api/admin/jobs/{job_id}/people/{person_id}/bench-role-preview,
# see api/tests/test_phase44_bench_role_preview.py) that reuses
# _bench_role_and_missing_tenure — never a client-side reimplementation of the
# tenure derivation (44-06's explicit prohibition).
# ─────────────────────────────────────────────────────────────────────────────


def test_job_id_prop_added_for_the_preview_fetch_only() -> None:
    source = _source(RESOLVE_CARD_PATH)
    props_body = _interface_body(source, "ResolveCardProps")
    assert "jobId: number" in props_body, (
        "the component needs the job id to call the job-scoped bench-role-preview "
        "endpoint — it must arrive as a prop, not be derived or guessed client-side"
    )
    assert re.search(r"\bjobId\b", _function_body(source, "fetchBenchRolePreview")), (
        "jobId must actually be used by the preview fetch, not merely declared"
    )


def test_fetch_bench_role_preview_calls_the_job_scoped_endpoint() -> None:
    source = _source(RESOLVE_CARD_PATH)
    assert "async function fetchBenchRolePreview(" in source
    body = _function_body(source, "fetchBenchRolePreview")
    assert "/admin/pipeline/${jobId}/bench-role-preview" in body, (
        "must call the SvelteKit proxy route (never FASTAPI_BASE_URL directly from "
        "client code — Architecture Rule 2)"
    )
    assert "person_id=${personId}" in body
    assert "benchRolePreview[participantId] = {" in body
    assert "personId," in body, (
        "the stored preview must carry the personId it was computed for, so a stale "
        "response can be told apart from the row's current pick"
    )


def test_preview_fetch_effect_skips_committed_rows_and_dedupes_by_pick() -> None:
    source = _source(RESOLVE_CARD_PATH)
    # Marker must be unique to this effect, not just its shared opening line —
    # the CR-01/CR-02 seeding effect (added after this test) also opens with
    # "for (const row of mergedRows) {", so a bare-loop marker would grab
    # whichever of the two effects appears first in the file instead of this one.
    body = _effect_body(source, "effectiveSide(row) !== 'BENCH'")
    assert "effectiveSide(row) !== 'BENCH'" in body, (
        "only a BENCH row's uncommitted pick needs a tenure preview — an advocate row "
        "never has a bench role to preview"
    )
    assert "row.person_id != null" in body, (
        "once the pick is committed, list_resolve_rows_for_job's own bench_role/"
        "missing_tenure are authoritative and must not be shadowed by a preview"
    )
    assert "benchRolePreviewFetched" in body, (
        "without a dedup cache, this effect (which re-scans every row on any row's "
        "rowMatchStates change) would re-fetch every already-previewed row on every "
        "unrelated edit"
    )
    assert "fetchBenchRolePreview(" in body


def test_bench_role_state_only_trusts_a_preview_for_the_currently_picked_person() -> None:
    # 44-06's prohibition: a tenure-derived role must never be older than the
    # request that rendered it. Without this guard, picking candidate A (preview
    # fetched), then quickly picking candidate B, could render A's still-cached
    # preview under B's name until A's response is overwritten.
    source = _source(RESOLVE_CARD_PATH)
    body = _function_body(source, "benchRoleState")
    assert "benchRolePreview[row.participant_id]" in body
    assert "preview?.personId === personId" in body, (
        "a preview must only be trusted when it was computed for the exact personId "
        "currently picked for this row — a mismatch must fall through to 'unresolved', "
        "never render a stale candidate's role under the current pick"
    )


def test_bench_role_cell_falls_back_to_the_preview_for_role_text_and_edit_link() -> None:
    source = _source(RESOLVE_CARD_PATH)
    body = _snippet_body(source, "argumentRoleCell")
    assert "previewedBenchRole" in body, (
        "the calculated-state role text must fall back to the preview's bench_role when "
        "row.bench_role is still null (uncommitted pick)"
    )
    assert "row.bench_role ?? previewedBenchRole ?? row.argument_role" in body
    assert "previewedPersonId" in body, (
        "the missing-tenure state's Edit person link must still render for an "
        "uncommitted pick — row.person_edit_href alone is null until commit"
    )
    assert "row.person_edit_href ?? `/admin/people/${previewedPersonId}`" in body, (
        "the fallback link must reuse the same /admin/people/{id} path the service "
        "constructs — not a different shape"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint remediation (44-09, sixth round) — a real pre-existing bug found
# during operator live-testing of the tenure-preview feature: CreatePersonPopover
# (nested inside this combobox's own open dropdown since an earlier round moved
# it there) uses bits-ui's Popover.Portal, which mounts to document.body by
# default — outside comboOutsideClick's `container`. Any click inside the
# nested popover read as "outside the combobox" and closed it mid-interaction.
# ─────────────────────────────────────────────────────────────────────────────


def test_combo_outside_click_does_not_close_on_a_click_inside_a_nested_popover() -> None:
    source = _source(RESOLVE_CARD_PATH)
    # handleClick is nested inside comboOutsideClick (2-tab indent) — _function_body's
    # single-tab-closing-brace convention only holds for top-level functions, so this
    # scopes to the enclosing comboOutsideClick instead; handleClick's body is a subset.
    body = _function_body(source, "comboOutsideClick")
    assert "container.contains(target)" in body, (
        "the original in-container check must remain — this is an additional "
        "guard, not a replacement"
    )
    assert "data-popover-content" in body, (
        "a click inside any bits-ui Popover.Content (e.g. CreatePersonPopover's "
        "portalled content) must not be treated as outside the combobox — "
        "checked via bits-ui's own data-popover-content attribute, present on "
        "every Popover.Content regardless of its portal target"
    )
    container_check_idx = body.index("container.contains(target)")
    popover_check_idx = body.index("data-popover-content")
    assert container_check_idx < popover_check_idx, (
        "the in-container check must run first (cheapest, most common case); "
        "the popover-content check is the fallback for content the portal "
        "relocated outside container"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Code review findings CR-01/CR-02 (44-09, confirmed real bugs, found by
# gsd-code-reviewer and independently verified against the actual source):
# lastDescriptorValue and lastAdvocateRole were only ever written from their
# own input/select's event handler, never seeded from the row's already-
# committed server value — so a descriptor or specific advocate role that was
# correct BEFORE the current session, and never retyped/repicked in it, was
# silently destroyed by an Advocate->Bench->Advocate round trip (the first
# toggle's own save reloads the page, after which row.descriptor is null and
# row.side is 'BENCH' — exactly the values both fallbacks read from).
# ─────────────────────────────────────────────────────────────────────────────


def test_last_descriptor_and_advocate_role_are_seeded_from_committed_state() -> None:
    source = _source(RESOLVE_CARD_PATH)
    # Marker must be unique to this effect for the same reason the tenure-preview
    # effect's own test above needed one — both open with the identical
    # "for (const row of mergedRows) {" line.
    body = _effect_body(source, "lastDescriptorValue[row.participant_id] === undefined")
    assert "row.descriptor != null" in body, (
        "must only seed from a real, non-null committed descriptor — never seed a "
        "blank/null value over whatever (possibly already-correct) memory exists"
    )
    assert "specificAdvocateRole(row.side)" in body, (
        "lastAdvocateRole must be seeded from the row's own committed side via the "
        "same specificAdvocateRole helper toggleSide's restore path already uses — "
        "not a second, independently-maintained specific-role check"
    )
    assert "lastAdvocateRole[row.participant_id] === undefined" in body, (
        "must check for 'never seeded yet' before writing, the same seed-once "
        "guard used for lastDescriptorValue in this same effect"
    )


def test_seeding_effect_never_overwrites_an_already_seeded_value() -> None:
    # The seed-once guard is what makes this safe: once seeded (either by this
    # effect on first render, or by a real operator edit via oninput/onchange),
    # a later re-run of this effect (e.g. after the very reload that nulls
    # row.descriptor/flips row.side to BENCH) must never clobber it back to
    # null/UNKNOWN.
    source = _source(RESOLVE_CARD_PATH)
    body = _effect_body(source, "lastDescriptorValue[row.participant_id] === undefined")
    assert body.count("lastDescriptorValue[row.participant_id]") >= 2, (
        "must both check (=== undefined) and assign lastDescriptorValue by the same key"
    )
    # The assignment must be inside the `=== undefined` guard, not a bare
    # unconditional write — verified structurally: the guard's own `{` opens
    # before the assignment appears.
    guard_idx = body.index("lastDescriptorValue[row.participant_id] === undefined")
    assign_idx = body.index("lastDescriptorValue[row.participant_id] = row.descriptor")
    assert guard_idx < assign_idx, (
        "the undefined-check must precede the assignment it guards"
    )


def test_seeding_effect_is_not_gated_on_ispaused() -> None:
    # Unlike the rowMatchStates/lastSideBucket/sideGateConfirmed seeding effect
    # above (which returns immediately `if (!isPaused) return;`), the toggle and
    # descriptor input are NOT gated on isPaused — an operator can flip
    # Bench/Advocate and edit Descriptor on an already-resolved (non-paused)
    # editable row too, so this seeding must run unconditionally.
    source = _source(RESOLVE_CARD_PATH)
    body = _effect_body(source, "lastDescriptorValue[row.participant_id] === undefined")
    assert "if (!isPaused) return" not in body, (
        "this seeding effect must not be gated on isPaused — the bug it fixes "
        "reproduces on non-paused editable rows too"
    )
