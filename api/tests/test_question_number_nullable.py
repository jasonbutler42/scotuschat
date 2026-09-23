"""
`arguments.question_number` accepts NULL through the Pydantic layer.

Regression guard for the AEDIT-04 defect (30.1-UAT test 3): blanking the
Question number field raised an unhandled asyncpg IntegrityError instead of
persisting NULL, because the column was never migrated nullable (unlike
`argued_date`, migration 0011). Fixed by migration 0019.

Pure-Python schema construction: no DB, no async, no fixtures.

Trimmed 2026-08-27 (debridement pass): 8 static frontend-source assertions
about focus order and error copy removed. See CLAUDE.md -> Testing Policy.

Retargeted 2026-08-28 (Phase 51 plan 51-08): the first test below
constructed CaseItem (the retired cases-list schema, GET /cases) —
retired once its last consumer was removed. Retargeted onto
ArgumentListItem (api/schemas/arguments.py, GET /arguments/term/
{term_year}), which carries the identical nullable-question_number
contract for the same reason.
"""

from pathlib import Path


def test_argument_list_item_accepts_null_question_number() -> None:
    """Constructing ArgumentListItem with question_number=None must not raise."""
    from api.schemas.arguments import ArgumentListItem

    item = ArgumentListItem(
        argument_id=1,
        slug="synthetic-case",
        case_name="Synthetic Case",
        docket_number="1955-71",
        term_year=1955,
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


