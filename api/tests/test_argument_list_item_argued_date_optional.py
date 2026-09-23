"""
Targeted regression test for the non-optional-over-nullable-column defect
class fixed alongside ArgumentMetadataResponse's identical defect (see
api/tests/test_argument_oyez_field.py, 29-VERIFICATION.md gap #13 / 29-REVIEW.md
CR-01).

Retargeted from CaseItem (the retired cases-list schema, GET /cases) onto
ArgumentListItem (api/schemas/arguments.py, GET /arguments/term/{term_year})
in Phase 51 plan 51-08 — the old schema module and its endpoint were
retired once their last consumer was removed, but the nullable-argued_date
guarantee did not retire with them: ArgumentListItem.argued_date is
optional for the exact same nullable-DB-column reason
(Argument.argued_date, models.py) and would 500 the term-detail listing the
moment a corpus-imported draft with a null argued_date is published,
exactly as CaseItem once could for the flat /cases listing. Renamed from
test_case_item_argued_date_optional.py so the module name matches the unit
under test, per CLAUDE.md's Testing Policy.
"""


def test_argument_list_item_accepts_null_argued_date() -> None:
    """Constructing ArgumentListItem with argued_date=None must not raise."""
    from api.schemas.arguments import ArgumentListItem

    item = ArgumentListItem(
        argument_id=1,
        slug="synthetic-case",
        case_name="Synthetic Case",
        docket_number="1955-71",
        term_year=1955,
        question_number=1,
        argued_date=None,
    )
    assert item.argued_date is None
