"""
Business logic for the speaker popover endpoint.

Assembles the complete speaker data set for a given argument in three async
queries, avoiding N+1 loops.  Returns a plain list[dict] — the router's
response_model=list[SpeakerPopoverEntry] validates and serializes the output.

CRITICAL: appointing_president_party is intentionally never included in the
assembled dict — admin-only field, apolitical framing constraint (T-14-02).
"""

from collections import defaultdict

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import CourtTenure, Person, Role, Utterance


async def get_argument_speakers(
    db: AsyncSession,
    argument_id: int,
) -> list[dict]:
    """
    Return speaker popover data for all resolved speakers in an argument.

    Three-step async subquery pattern:
      1. Collect distinct person_ids from utterances for this argument.
      2. Fetch Person + Role.name for those person_ids in one query.
      3. Fetch all CourtTenure rows for those person_ids in one query.

    Returns [] immediately when no utterances have a resolved person_id
    (e.g. resolve step has not run yet) — never raises 404.

    Returns list[dict] shaped to match SpeakerPopoverEntry (validated by
    the router's response_model).
    """
    # Step 1 — Collect distinct person_ids (ignore unresolved utterances) ----
    person_ids_result = await db.execute(
        select(distinct(Utterance.person_id)).where(
            Utterance.argument_id == argument_id,
            Utterance.person_id.isnot(None),
        )
    )
    person_ids: list[int] = [row[0] for row in person_ids_result.all()]

    if not person_ids:
        return []

    # Step 2 — Fetch people + roles in one query ----------------------------
    people_result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .where(Person.id.in_(person_ids))
    )
    people_rows = people_result.all()

    # Step 3 — Fetch all court_tenures for these person_ids in one query ----
    tenures_result = await db.execute(
        select(CourtTenure)
        .where(CourtTenure.person_id.in_(person_ids))
        .order_by(CourtTenure.person_id.asc(), CourtTenure.start_date.asc())
    )
    tenure_rows = tenures_result.scalars().all()

    # Step 4 — Group tenures by person_id -----------------------------------
    tenures_by_person: dict[int, list[dict]] = defaultdict(list)
    for t in tenure_rows:
        tenures_by_person[t.person_id].append(
            {
                "seat": t.seat,
                "start_date": str(t.start_date) if t.start_date else None,
                "end_date": str(t.end_date) if t.end_date else None,
            }
        )

    # Step 5 — Assemble result ----------------------------------------------
    result: list[dict] = []
    for person, role_name in people_rows:
        result.append(
            {
                "person_id": person.id,
                "full_name": person.full_name,
                "role_name": role_name,
                "photo_url": person.photo_url,
                "appointing_president": person.appointing_president,
                # appointing_president_party intentionally excluded (T-14-02)
                "tenure": tenures_by_person[person.id],
            }
        )

    return result
