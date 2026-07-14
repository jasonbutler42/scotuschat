"""Shared primitives for the authoritative Argument docket/question key."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument


ARGUMENT_PAIR_CONSTRAINT = "uq_arguments_source_docket_question"


async def find_argument_by_pair(
    db: AsyncSession,
    docket: str | None,
    question: int | None,
    *,
    exclude_argument_id: int | None = None,
) -> int | None:
    """Return the matching Argument id; PostgreSQL NULL uniqueness never collides."""
    if docket is None or question is None:
        return None
    query = select(Argument.id).where(
        Argument.source_docket == docket,
        Argument.question_number == question,
    )
    if exclude_argument_id is not None:
        query = query.where(Argument.id != exclude_argument_id)
    return (await db.execute(query)).scalar_one_or_none()


def is_argument_pair_violation(error: BaseException) -> bool:
    """Classify the named constraint using structured driver data, cycle-safely."""
    pending: list[object] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if getattr(current, "constraint_name", None) == ARGUMENT_PAIR_CONSTRAINT:
            return True
        diag = getattr(current, "diag", None)
        if getattr(diag, "constraint_name", None) == ARGUMENT_PAIR_CONSTRAINT:
            return True
        for attr in ("orig", "__cause__", "__context__"):
            nested = getattr(current, attr, None)
            if nested is not None:
                pending.append(nested)
    return False
