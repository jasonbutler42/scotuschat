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


def test_duplicate_message_and_component_compose_one_recovery_phrase() -> None:
    """The API owns facts while the shared card owns the recovery-link copy."""
    api_message = "An argument already uses docket 24-1, question 2."
    recovery_label = "Open conflicting argument"
    source = _frontend_source("src/lib/components/ArgumentDetailsCard.svelte")

    assert recovery_label not in api_message
    assert source.count(recovery_label) == 1
    assert f"{api_message} {recovery_label}.".count(recovery_label) == 1
