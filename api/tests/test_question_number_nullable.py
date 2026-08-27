"""
`arguments.question_number` accepts NULL through the Pydantic layer.

Regression guard for the AEDIT-04 defect (30.1-UAT test 3): blanking the
Question number field raised an unhandled asyncpg IntegrityError instead of
persisting NULL, because the column was never migrated nullable (unlike
`argued_date`, migration 0011). Fixed by migration 0019.

Pure-Python schema construction: no DB, no async, no fixtures.

Trimmed 2026-08-27 (debridement pass): 8 static frontend-source assertions
about focus order and error copy removed. See CLAUDE.md -> Testing Policy.
"""

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


