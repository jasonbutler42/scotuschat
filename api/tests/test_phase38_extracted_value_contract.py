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
    source = _source(COPYABLE_PATH)
    assert '<span class="prefix">Extracted:</span>' in source
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
