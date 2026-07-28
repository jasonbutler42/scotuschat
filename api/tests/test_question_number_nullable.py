"""
Targeted regression test for the arguments.question_number NOT-NULL-over-
nullable-column defect diagnosed in 30.1-UAT.md test 3 (AEDIT-04 gap):
blanking the Question number field in the Argument Details card and saving
raised an unhandled asyncpg IntegrityError instead of persisting NULL, since
the column was never migrated to nullable (unlike argued_date, migration
0011). Fixed by migration 0019 (nullable=True, no server default) plus
schema/router hardening in this plan.

Mirrors api/tests/test_case_item_argued_date_optional.py exactly: pure-Python
schema construction, no DB, no async, no fixtures — safe against the known
shared-dev-DB test-leak issue (see ROADMAP.md backlog Phase 999.19).
"""

import inspect
from pathlib import Path


def test_case_item_accepts_null_question_number() -> None:
    """Constructing CaseItem with question_number=None must not raise."""
    from api.schemas.cases import CaseItem

    item = CaseItem(
        id=1,
        slug="synthetic-case",
        case_name="Synthetic Case",
        docket_number="1955-71",
        term_year=1955,
        argument_id=1,
        question_number=None,
        argued_date=None,
    )
    assert item.question_number is None


def test_argument_metadata_response_accepts_null_question_number() -> None:
    """Constructing ArgumentMetadataResponse with question_number=None must not raise."""
    from api.schemas.utterance import ArgumentMetadataResponse

    item = ArgumentMetadataResponse(
        argument_id=1,
        case_name="Synthetic Case",
        docket_number="1955-71",
        question_number=None,
    )
    assert item.question_number is None


def _frontend_source(relative_path: str) -> str:
    return (Path(__file__).parents[2] / "app" / relative_path).read_text(encoding="utf-8")


def test_metadata_actions_validate_duplicate_contract_and_preserve_attempted_values() -> None:
    """Both SvelteKit actions expose the same sanitized duplicate contract."""
    action_paths = (
        "src/routes/admin/pipeline/[job_id]/+page.server.ts",
        "src/routes/admin/arguments/[id]/+page.server.ts",
    )

    for path in action_paths:
        source = _frontend_source(path)
        assert "detail.code === 'duplicate_argument'" in source
        assert "Number.isInteger(detail.conflicting_argument_id)" in source
        assert "conflict: detail" in source
        assert "question_number, argued_date" in source
        assert "saveError: 'Could not save. Try again.'" in source


def test_argument_actions_parse_required_locations_and_preserve_raw_attempts() -> None:
    source = _frontend_source("src/routes/admin/arguments/[id]/+page.server.ts")

    assert "function parseRequiredFieldErrors(value: unknown)" in source
    assert "if (!Array.isArray(detail)) return null" in source
    assert "if (!Array.isArray(loc)) continue" in source
    assert "field === 'case_name'" in source
    assert "field === 'docket_number' || field === 'source_docket' || field === 'source_dockets'" in source
    assert "const attemptedValues = { case_name, docket_number }" in source
    assert "const case_name = (formData.get('case_name') as string) ?? ''" in source
    assert "...required, ...attemptedValues" in source
    parser = source[source.index("function parseRequiredFieldErrors"):source.index("export const load")]
    assert ".msg" not in parser


def test_metadata_actions_share_loc_driven_required_recovery() -> None:
    action_paths = (
        "src/routes/admin/pipeline/[job_id]/+page.server.ts",
        "src/routes/admin/arguments/[id]/+page.server.ts",
    )

    for path in action_paths:
        source = _frontend_source(path)
        assert "function parseRequiredFieldErrors(value: unknown)" in source
        assert "if (!Array.isArray(detail)) return null" in source
        assert "if (!Array.isArray(loc)) continue" in source
        assert "field === 'source_docket' || field === 'source_dockets'" in source
        assert "const attemptedValues = { dockets, question_number, argued_date }" in source
        assert "...required, ...attemptedValues" in source
        parser = source[source.index("function parseRequiredFieldErrors"):source.index("export const load")]
        assert ".msg" not in parser


def test_argument_details_card_restores_values_and_focuses_one_safe_alert() -> None:
    """The shared card owns value recovery, focus order, and safe navigation."""
    source = _frontend_source("src/lib/components/ArgumentDetailsCard.svelte")

    assert "value={form?.question_number ?? savedValues.question_number}" in source
    assert "form && 'argued_date' in form" in source
    assert source.count('role="alert"') == 1
    assert 'tabindex="-1"' in source
    assert source.index("await update();") < source.index("await tick();") < source.index("alertElement?.focus();")
    assert "`/admin/arguments/${form.conflict.conflicting_argument_id}`" in source
    assert 'target="_blank"' in source
    assert 'rel="noopener noreferrer"' in source


def test_case_form_required_contract_preserves_attempts_and_focus_order() -> None:
    source = _frontend_source("src/routes/admin/arguments/[id]/+page.svelte")

    assert source.count("\n\t\t\t\t\t\trequired") >= 2
    assert "event.preventDefault()" in source
    assert "elements.namedItem('case_name')" in source
    assert "elements.namedItem('docket_number')" in source
    assert source.index("elements.namedItem('case_name')") < source.index("elements.namedItem('docket_number')")
    assert "form && 'case_name' in form ? form.case_name" in source
    assert "form && 'docket_number' in form ? form.docket_number" in source
    assert "Case name is required." in source
    assert "Add at least one docket." in source
    assert "aria-invalid={caseNameRequired ? 'true' : undefined}" in source
    assert "aria-describedby={docketRequired ? 'case-form-alert' : undefined}" in source
    assert source.index("caseNameInput?.focus()") < source.index("docketNumberInput?.focus()")


def test_case_form_clears_native_required_state_before_enhanced_save() -> None:
    source = _frontend_source("src/routes/admin/arguments/[id]/+page.svelte")

    case_reset = source.index("nativeCaseNameRequired = false;", source.index('action="?/save"'))
    docket_reset = source.index("nativeDocketRequired = false;", case_reset)
    saving = source.index("savingState = true;", docket_reset)

    assert case_reset < docket_reset < saving


def test_duplicate_message_and_component_compose_one_recovery_phrase() -> None:
    """The API owns facts while the shared card owns the recovery-link copy."""
    api_message = "An argument already uses docket 24-1, question 2."
    recovery_label = "Open conflicting argument"
    source = _frontend_source("src/lib/components/ArgumentDetailsCard.svelte")

    assert recovery_label not in api_message
    assert source.count(recovery_label) == 1
    assert f"{api_message} {recovery_label}.".count(recovery_label) == 1


def test_docket_pill_required_contract_blocks_empty_and_exposes_focus() -> None:
    card = _frontend_source("src/lib/components/ArgumentDetailsCard.svelte")
    pill = _frontend_source("src/lib/components/DocketPillInput.svelte")

    assert "form && 'dockets' in form" in card
    assert "!docketControl?.hasPills()" in card
    assert "cancel();" in card
    assert "Add at least one docket." in card
    assert "if (form?.docketRequired) docketControl?.focus()" in card
    assert 'descriptionId="argument-details-alert"' in card
    assert "export function focus()" in pill
    assert "export function hasPills()" in pill
    # Phase 38 gap closure (G-38-6) composed shapeError into the invalid/
    # descriptionId contract rather than replacing it — hasError/describedByIds
    # reduce to the original !readonly && invalid behavior whenever shapeError
    # is inactive (i.e. for every caller, like ArgumentDetailsCard, that never
    # sets enforceShape and so never populates shapeError).
    assert "let hasError = $derived(!readonly && (invalid || Boolean(shapeError)));" in pill
    assert "aria-invalid={hasError ? 'true' : undefined}" in pill
    assert "if (!readonly && invalid && descriptionId) ids.push(descriptionId);" in pill
    assert "aria-describedby={describedByIds}" in pill
    assert "e.preventDefault();" in pill
