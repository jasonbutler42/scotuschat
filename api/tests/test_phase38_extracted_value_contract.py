"""Structural regression coverage for the Phase 38 stacked extracted-value contract.

No frontend test harness exists in app/package.json (see 36-PATTERNS.md /
38-RESEARCH.md) — this file follows the established static source-contract
pattern (test_admin_jobs_phase35_frontend.py) to lock the shared
CopyableExtractedValue/DocketPillInput contract and its consumers without a
Svelte component test runner.

Task 1 (this file's first section): CopyableExtractedValue.svelte gains
optional stacked provenance (confidence + raw) while remaining a strict
superset of the Phase 36 value-only/pill contract.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
COPYABLE_PATH = ROOT / "app" / "src" / "lib" / "components" / "CopyableExtractedValue.svelte"
DOCKET_PILL_PATH = ROOT / "app" / "src" / "lib" / "components" / "DocketPillInput.svelte"
RESOLVE_CARD_PATH = ROOT / "app" / "src" / "lib" / "components" / "ResolveCard.svelte"
PIPELINE_JOB_PATH = (
    ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.svelte"
)
ARGUMENT_EDIT_PATH = (
    ROOT / "app" / "src" / "routes" / "admin" / "arguments" / "[id]" / "+page.svelte"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: CopyableExtractedValue.svelte — backward-compatible stacked primitive
# ─────────────────────────────────────────────────────────────────────────────


def test_component_declares_confidence_band_and_optional_stacked_props() -> None:
    source = _source(COPYABLE_PATH)
    assert "type ConfidenceBand = 'High' | 'Medium' | 'Low';" in source
    assert "confidence?: ConfidenceBand | null;" in source
    assert "raw?: string | null;" in source


def test_stacked_mode_activates_only_when_confidence_or_raw_supplied() -> None:
    """Legacy value-only/pill consumers that never pass confidence/raw must keep
    rendering exactly as before (Phase 36 contract preserved as a strict subset)."""
    source = _source(COPYABLE_PATH)
    assert "let isStacked = $derived(confidence !== undefined || raw !== undefined);" in source


def _strip_svelte_comments(source: str) -> str:
    return re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL)


def test_confidence_band_is_runtime_validated_never_a_fabricated_figure() -> None:
    source = _source(COPYABLE_PATH)
    assert "function isValidConfidenceBand(input: unknown): input is ConfidenceBand {" in source
    assert "input === 'High' || input === 'Medium' || input === 'Low'" in source
    # No calibrated percentage anywhere near the confidence band text (D-22) —
    # excludes unrelated CSS percentages like `width: 100%;`.
    assert "% confidence" not in source
    assert "{effectiveBand}%" not in source


def test_empty_interpretation_with_raw_forces_low_confidence() -> None:
    """38-UI-SPEC: raw-with-no-interpretation always shows Low, regardless of the
    confidence value a caller supplied."""
    source = _source(COPYABLE_PATH)
    assert "if (isEmpty) return 'Low';" in source


def test_provenance_line_omitted_when_raw_is_absent() -> None:
    source = _source(COPYABLE_PATH)
    assert "let hasRaw = $derived(raw !== null && raw !== undefined && raw !== '');" in source
    assert "let showProvenanceLine = $derived(isStacked && hasRaw);" in source


def test_stacked_layout_renders_extracted_prefix_and_confidence_raw_line() -> None:
    """Phase 44 D-09: the prefix is now the interpolated `prefixLabel` prop
    (default 'Extracted'), not a hardcoded string, so every pre-existing
    consumer that omits the prop still renders "Extracted:" — the default
    value is the back-compat mechanism, not this markup line."""
    source = _source(COPYABLE_PATH)
    assert "<span class=\"prefix\">{prefixLabel}:</span>" in source
    assert "prefixLabel = 'Extracted'" in source
    assert "{effectiveBand} confidence · Raw: {raw}" in source


def test_legacy_non_stacked_branch_never_forces_extracted_prefix() -> None:
    source = _source(COPYABLE_PATH)
    assert "{:else}" in source
    legacy_branch = source.split("{:else}", 1)[1].split("{/if}")[0]
    assert '<span class="prefix">' not in legacy_branch


def test_raw_and_value_are_never_rendered_via_html_directive() -> None:
    """T-38-14: raw is untrusted extracted text — plain Svelte interpolation only."""
    source = _strip_svelte_comments(_source(COPYABLE_PATH))
    assert "{@html" not in source


def test_clipboard_copies_only_the_interpreted_value_never_raw() -> None:
    """T-38-13: copy payload must remain exactly the interpreted value."""
    source = _source(COPYABLE_PATH)
    assert "await navigator.clipboard.writeText(value);" in source
    assert "writeText(raw" not in source
    assert "writeText(`" not in source


def test_feedback_generation_invalidates_on_confidence_and_raw_change() -> None:
    """T-38-15: stale clipboard/timer generations must not leak across a changed
    payload, including the new provenance props."""
    source = _source(COPYABLE_PATH)
    effect_block = source.split("$effect(() => {", 1)[1].split("});", 1)[0]
    assert "value;" in effect_block
    assert "copyLabel;" in effect_block
    assert "confidence;" in effect_block
    assert "raw;" in effect_block
    assert "invalidateFeedback();" in effect_block
    assert "return invalidateFeedback;" in effect_block


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: DocketPillInput.svelte — approved Docket Pill provenance states
# (38-FIGMA.md component set 3:140 / review sheet 3:2)
# ─────────────────────────────────────────────────────────────────────────────


def test_docket_pill_input_accepts_backward_compatible_string_entries() -> None:
    source = _source(DOCKET_PILL_PATH)
    assert "type ConfidenceBand = 'High' | 'Medium' | 'Low';" in source
    assert "type DocketPillValue = string | DocketProvenance;" in source
    assert "initialValues?: DocketPillValue[];" in source


def test_docket_pill_input_normalizes_and_builds_provenance_map_once() -> None:
    source = _source(DOCKET_PILL_PATH)
    assert "function normalizeEntry(entry: DocketPillValue): DocketProvenance {" in source
    assert "const provenanceMap = new Map<string, DocketProvenance>(" in source


def test_docket_pill_input_uses_shared_copy_primitive_for_provenance_pills() -> None:
    source = _source(DOCKET_PILL_PATH)
    assert "import CopyableExtractedValue from '$lib/components/CopyableExtractedValue.svelte';" in source
    assert "<CopyableExtractedValue" in source
    assert 'copyLabel="Copy docket"' in source
    assert "confidence={provenance.confidence}" in source
    assert "raw={provenance.raw}" in source


def test_docket_pill_input_remove_is_editable_mode_only() -> None:
    source = _source(DOCKET_PILL_PATH)
    assert source.count("{#if !readonly}") >= 2


def test_docket_pill_input_preserves_form_serialization_and_public_api() -> None:
    """Preserve existing form serialization/removal behavior (Task 2 action)."""
    source = _source(DOCKET_PILL_PATH)
    assert '<input type="hidden" {name} value={pill} />' in source
    assert "export function hasPills() {" in source
    assert "export function focus() {" in source


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: every current editable-destination consumer adopts the stacked
# contract (D-19/D-20). Legacy metadata with no independently stored
# confidence/raw is adapted at the caller boundary with an explicit
# qualitative fallback ("Medium") and the original field as the raw text —
# never a fabricated percentage.
#
# Phase 44 Plan 04 (RESOLVE-05, D-08/D-09) superseded ResolveCard.svelte's four
# hint call sites for THIS FILE ONLY: they now pass prefixLabel="Imported" and
# raw={null} with no confidence prop at all, opting out of the two-line stacked
# treatment below in favor of a single "Imported: …" line. The argument editor
# (ARGUMENT_EDIT_PATH) did NOT change and still uses the original
# confidence="Medium"/raw stacked pattern — a future reader must not "restore"
# ResolveCard to that pattern; the opt-out is intentional and UI-SPEC-locked.
# See api/tests/test_phase44_resolve_table_contract.py's RESOLVE-05 section for
# the positive contract on the four new hints.
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_card_hints_opted_out_of_stacked_confidence_raw_per_phase_44() -> None:
    """Phase 44 (RESOLVE-05, D-08/D-09) superseded this file's four hint call
    sites with a single-line "Imported: …" treatment — no confidence band, no
    mirrored raw prop. See the section banner above."""
    source = _source(RESOLVE_CARD_PATH)
    assert source.count('prefixLabel="Imported"') == 4
    assert source.count("raw={null}") == 4
    assert "confidence=" not in source
    # The component now owns the "Extracted:"/"Imported:" prefix in stacked
    # mode — no leftover caller-owned duplicate prefix.
    assert "Extracted: <CopyableExtractedValue" not in source
    assert "Imported: <CopyableExtractedValue" not in source


def test_argument_editor_descriptor_hint_uses_stacked_provenance() -> None:
    source = _source(ARGUMENT_EDIT_PATH)
    assert 'copyLabel="Copy descriptor"' in source
    assert 'confidence="Medium"' in source
    assert "raw={speaker.descriptor_hint}" in source
    assert "Extracted: <CopyableExtractedValue" not in source


def test_pipeline_job_detail_parsed_readouts_use_stacked_provenance() -> None:
    source = _source(PIPELINE_JOB_PATH)
    assert 'copyLabel="Copy case name" confidence="Medium" raw={ps.case_name}' in source
    assert 'copyLabel="Copy argued date" confidence="Medium" raw={ps.argued_date}' in source
    assert 'copyLabel="Copy docket" variant="pill" confidence="Medium" raw={ps.primary_docket}' in source
    assert 'copyLabel="Copy question number" confidence="Medium"' in source


def test_pipeline_job_detail_argued_date_raw_is_exact_iso_not_formatted() -> None:
    """D-20/D-21: raw must be the exact source text, which genuinely differs
    from the displayed interpretation for argued date (ISO vs. formatted)."""
    source = _source(PIPELINE_JOB_PATH)
    assert "raw={ps.argued_date}" in source
    assert "raw={formatDate(ps.argued_date)}" not in source


def test_no_fabricated_confidence_percentages_in_any_converted_consumer() -> None:
    for path in (RESOLVE_CARD_PATH, ARGUMENT_EDIT_PATH, PIPELINE_JOB_PATH):
        source = _source(path)
        assert "% confidence" not in source
        assert "Confidence:" not in source  # locked copy is "{Band} confidence", not "Confidence:"


def test_every_known_editable_destination_consumer_supplies_confidence_and_raw() -> None:
    """Enumerates every current CopyableExtractedValue call site across the
    Phase 38 Plan 05 consumer files that still use the stacked confidence/raw
    treatment. RESOLVE_CARD_PATH is deliberately excluded here — Phase 44 Plan
    04 (RESOLVE-05, D-08/D-09) opted its four hint call sites out of
    confidence/raw entirely (see the section banner above and
    test_resolve_card_hints_opted_out_of_stacked_confidence_raw_per_phase_44,
    plus the positive RESOLVE-05 contract in
    test_phase44_resolve_table_contract.py). A future usage added to one of
    the two remaining files without confidence/raw fails this test loudly
    (Task 3 action)."""
    for path in (ARGUMENT_EDIT_PATH, PIPELINE_JOB_PATH):
        source = _source(path)
        calls = re.findall(r"<CopyableExtractedValue\b.*?/>", source, flags=re.DOTALL)
        assert calls, f"expected at least one CopyableExtractedValue usage in {path}"
        for call in calls:
            assert "confidence=" in call, f"missing confidence in {path}: {call}"
            assert "raw=" in call, f"missing raw in {path}: {call}"
