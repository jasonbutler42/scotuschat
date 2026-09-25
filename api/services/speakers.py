"""
Business logic for the speaker popover endpoint.

Assembles the complete speaker data set for a given argument in five async
queries, avoiding N+1 loops.  Returns a plain list[dict] — the router's
response_model=list[SpeakerPopoverEntry] validates and serializes the output.

appointing_president_party IS included in the assembled dict, per tenure.
Phase 14 originally kept this admin-only under the apolitical
framing constraint; Phase 39 (39-CONTEXT.md D-11/D-12) reverses that: the
value describes the *appointing president's* party — factual historical
record about a president, not the Justice — and is emitted identically for
every tenure entry, with no aggregation and no differential framing. The
Step 5 assembly dict remains an explicit, hand-written allow-list of named
keys (never an ORM-row spread or a schema-validate-from-object shortcut) so
this widening does not also leak an adjacent admin-only Person column
(T-39-13).
"""

import datetime
from collections import defaultdict

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.person_names import derive_initials
from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    CourtTenure,
    Person,
    Role,
    SideEnum,
    Utterance,
    office_title,
)


# ---------------------------------------------------------------------------
# Module-level constants and helpers (Phase 15 — ROLE-01/ROLE-02)
# ---------------------------------------------------------------------------


ADVOCATE_LABEL_MAP: dict[SideEnum, str] = {
    SideEnum.PETITIONER: "Petitioner's Counsel",
    SideEnum.RESPONDENT: "Respondent's Counsel",
    SideEnum.AMICUS: "Amicus Curiae",
    SideEnum.UNKNOWN: "Counsel",
    SideEnum.ADVOCATE: "Counsel",  # legacy — retained permanently (Pitfall 4)
}


def _tenure_role_name(
    tenures: list[dict],
    argued_date: datetime.date | None,
) -> str | None:
    """Return the formal title for the tenure covering argued_date,
    or the most-recent tenure's formal title as D-14 fallback.

    Args:
        tenures: List of dicts with keys ``office``, ``start_date``, ``end_date``.
                 ``office`` is the canonical storage value ("chief"/"associate");
                 this helper projects it to the formal display title via
                 ``office_title()`` — valid records never fall back to a
                 generic "Justice" label.
                 ``start_date`` and ``end_date`` must be ``datetime.date`` objects
                 (not strings) so direct date comparison works without parsing.
                 ``end_date=None`` means the tenure is open-ended (currently active).
        argued_date: The argument's argued_date as a ``datetime.date``.
                     When None, skip the window check and go straight to D-14 fallback
                     (Pitfall 5 — argument may not have an argued_date yet).

    Returns:
        The formal title (e.g. "Chief Justice") for the matching tenure, or
        None if tenures is empty or the matching tenure's office value isn't
        one of the two canonical values (see office_title()'s KeyError note —
        this can only happen mid-rollout, before migration 0021's CHECK
        constraint is applied; degrading to None here keeps one bad row from
        500ing every other speaker on the page).
    """
    if not tenures:
        return None

    if argued_date is not None:
        for t in tenures:
            start = t["start_date"]
            end = t["end_date"]
            if start is not None and argued_date >= start:
                if end is None or argued_date <= end:
                    try:
                        return office_title(t["office"])
                    except KeyError:
                        return None

    # D-14 fallback: argued_date is None OR outside all windows — use most-recent
    # tenure by start_date.  start_date=None is treated as datetime.date.min so a
    # tenure with no start_date is always the "oldest" and will lose ties.
    most_recent = max(
        tenures,
        key=lambda t: t["start_date"] or datetime.date.min,
    )
    try:
        return office_title(most_recent["office"])
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------


async def get_argument_speakers(
    db: AsyncSession,
    argument_id: int,
) -> list[dict] | None:
    """
    Return speaker popover data for all resolved speakers in an argument.

    Five-step async subquery pattern (Phase 15 extends the original three steps):
      0. Fetch the argument's argued_date and published_at (date-range tenure
         lookup; published_at gates public visibility per BUG-01/D-02).
      1. Collect distinct person_ids from utterances for this argument.
      2. Fetch Person + Role.name for those person_ids in one query.
      3. Fetch all CourtTenure rows for those person_ids in one query.
      4. Fetch argument_participants.side per person for this argument.

    Returns None when the argument row is absent or its published_at IS NULL
    (BUG-01/D-02) — the router maps None to a plain 404 (D-01). Returns []
    (not None) for a published argument with no resolved speakers (e.g. resolve
    step has not run yet) — an empty roster is never converted into a 404.

    Returns list[dict] shaped to match SpeakerPopoverEntry (validated by
    the router's response_model), or None per the publish gate above.
    """
    # Step 0 — Fetch the argument's argued_date + published_at + status ------
    # Gate on published_at: an absent row or a NULL publish
    # timestamp both return None here, distinct from the legitimate [] case
    # below (published argument, zero resolved speakers). Phase 48 plan 10,
    # Defect 2: published_at alone is insufficient — unpublish_argument
    # deliberately RETAINS published_at, so an UNPUBLISHED argument
    # also gates to None via the status check below, in ADDITION to the
    # published_at check above (never in place of it — see
    # test_published_gate.py's exact-substring assertions).
    arg_result = await db.execute(
        select(Argument.argued_date, Argument.published_at, Argument.status).where(
            Argument.id == argument_id
        )
    )
    arg_row = arg_result.one_or_none()
    if (
        arg_row is None
        or arg_row.published_at is None
        or arg_row.status != ArgumentStatusEnum.PUBLISHED
    ):
        return None
    argued_date = arg_row.argued_date

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

    # Step 3a — Group tenures by person_id (keep date objects for lookup) ---
    # We maintain TWO representations for each tenure:
    #   - date_tenures_by_person: datetime.date objects for _tenure_role_name lookup
    #   - str_tenures_by_person:  stringified dates for SpeakerPopoverEntry.tenure output
    date_tenures_by_person: dict[int, list[dict]] = defaultdict(list)
    str_tenures_by_person: dict[int, list[dict]] = defaultdict(list)
    for t in tenure_rows:
        date_tenures_by_person[t.person_id].append(
            {
                "office": t.office,
                "start_date": t.start_date,        # datetime.date for comparison
                "end_date": t.end_date,             # datetime.date or None
            }
        )
        str_tenures_by_person[t.person_id].append(
            {
                "office": t.office,
                "start_date": str(t.start_date) if t.start_date else None,
                "end_date": str(t.end_date) if t.end_date else None,
                # Raw canonical value, carried end to end.
                "reason_left": t.reason_left,
                # Phase 39 (D-13, promote): the per-tenure appointing
                # president, replacing the retired top-level Step 5 field.
                "appointed_by": t.appointed_by,
                # Phase 39 (D-11/D-12, reverses T-14-02): the appointing
                # president's party, serialised identically for every entry.
                "appointing_president_party": t.appointing_president_party,
            }
        )

    # Step 4 — Fetch argument_participants.side per person for this argument -
    sides_result = await db.execute(
        select(ArgumentParticipant.person_id, ArgumentParticipant.side)
        .where(
            ArgumentParticipant.argument_id == argument_id,
            ArgumentParticipant.person_id.in_(person_ids),
        )
    )
    side_by_person: dict[int, SideEnum] = {
        row.person_id: row.side for row in sides_result.all()
    }

    # Step 5 — Assemble result ----------------------------------------------
    result: list[dict] = []
    for person, _legacy_role_name in people_rows:
        side = side_by_person.get(person.id)

        # Resolve role_name via tenure date-range lookup for bench speakers,
        # or via the label map for advocates.
        if side == SideEnum.BENCH:
            role_name = _tenure_role_name(
                date_tenures_by_person.get(person.id) or [],
                argued_date,
            )
        else:
            role_name = ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)

        result.append(
            {
                "person_id": person.id,
                "full_name": person.full_name,
                "role_name": role_name,
                "photo_url": person.photo_url,
                # Phase 39 (D-13, promote): the top-level appointing-president
                # field retired from here since Phase 22 (hardcoded null) is
                # fully gone — the data now lives per-tenure as
                # str_tenures_by_person[...]["appointed_by"] above.
                "birthdate": str(person.birthdate) if person.birthdate else None,
                "death_date": str(person.death_date) if person.death_date else None,
                "bio_text": person.bio_text,
                "tenure": str_tenures_by_person[person.id],
                "side": side.value if side is not None else None,
                # D-12: server-computed avatar-initials glyph from the same
                # Person row already in hand — no second query.
                "initials": derive_initials(
                    first_name=person.first_name,
                    last_name=person.last_name,
                    name_suffix=person.name_suffix,
                    full_name=person.full_name,
                ),
            }
        )

    return result
