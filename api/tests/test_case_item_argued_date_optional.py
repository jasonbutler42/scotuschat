"""
Targeted regression test for the CaseItem.argued_date non-optional-over-nullable-
column defect fixed alongside ArgumentMetadataResponse's identical defect (see
api/tests/test_argument_oyez_field.py, 29-VERIFICATION.md gap #13 / 29-REVIEW.md
CR-01).

Scoped separately because CaseItem / get_cases() is a different schema and
endpoint (GET /cases) currently gated unreachable by get_cases()'s
WHERE Argument.published_at.isnot(None) filter (drafts never appear on the
public /cases list) — but it will 500 the entire public case list the moment
any corpus-imported draft with a null argued_date is published, so it is
fixed and regression-tested now rather than deferred to a second round.
"""


def test_case_item_accepts_null_argued_date() -> None:
    """Constructing CaseItem with argued_date=None must not raise."""
    from api.schemas.cases import CaseItem

    item = CaseItem(
        id=1,
        slug="synthetic-case",
        case_name="Synthetic Case",
        docket_number="1955-71",
        term_year=1955,
        argument_id=1,
        question_number=1,
        argued_date=None,
    )
    assert item.argued_date is None
