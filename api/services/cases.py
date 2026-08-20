"""
Business logic for case list queries.

Responsibilities:
  - Fetch all loaded cases joined to their lead argument via CaseArgument.is_lead
  - Filter by is_lead == True to return exactly one row per case (prevents
    duplicate rows for consolidated dockets such as Obergefell 14-556/562/571/574)
  - Order by argued_date DESC so most recent cases appear first

Returns a list of dicts shaped to match CaseItem (id, slug, case_name,
docket_number, term_year, argued_date, argument_id, question_number).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument


async def get_cases(db: AsyncSession) -> list[dict]:
    """
    Return all loaded cases with their lead argument metadata.

    Filters WHERE case_arguments.is_lead = TRUE to return exactly one row
    per case, preventing duplicate rows from consolidated dockets.

    Ordered by Argument.argued_date DESC (most recently argued first).
    """
    result = await db.execute(
        select(Case, Argument)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .join(Argument, CaseArgument.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712 — SQLAlchemy requires == True
        .where(Argument.published_at.isnot(None))  # hide unpublished arguments (D-06)
        # Phase 48 plan 10, Defect 2: unpublish_argument deliberately RETAINS
        # published_at (D-02, so the Status card can show the last publish
        # date) — so published_at alone no longer distinguishes PUBLISHED
        # from UNPUBLISHED. Gate on status too, in ADDITION to the
        # published_at predicate above (never in place of it — see
        # test_published_gate.py's exact-substring assertions).
        .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
        .order_by(Argument.argued_date.desc())
    )
    rows = result.all()
    return [
        {
            "id": case.id,
            "slug": case.slug,
            "case_name": case.case_name,
            "docket_number": case.docket_number,
            "term_year": case.term_year,
            "argued_date": argument.argued_date,
            "argument_id": argument.id,
            "question_number": argument.question_number,
        }
        for case, argument in rows
    ]
