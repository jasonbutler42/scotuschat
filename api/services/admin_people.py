"""
Business logic for admin people management.

Responsibilities:
  - Directory listing with missing-fields derivation
  - Person detail query with tenure rows
  - Person update with delete-and-reinsert tenure strategy (D-09, Pattern 5)
  - Inline role find-or-create
  - Resolved participants list for a completed job
  - Photo upload with dual-path storage
  - Merge preview count query
  - Atomic multi-table merge
  - Orphan-only delete

Critical guards (project-wide pattern from admin_jobs.py):
  - EVERY update() / delete() statement includes .execution_options(synchronize_session=False)
  - Empty-string bio_text/photo_url normalized to None before write (Pitfall 5)
  - Date strings parsed with datetime.date.fromisoformat() (Pitfall 6)
  - Alembic is sole DDL authority (CLAUDE.md) — no direct schema creation calls
"""

import asyncio
import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, delete, exists, func as sqlfunc, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.authority import WriteDecision
from api.domain.person_names import format_full_name, prepare_person_name
from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    CaseAppearance,
    CourtTenure,
    Person,
    ReviewState,
    Role,
    SideEnum,
    SpeakerAlias,
    Utterance,
    VALID_OFFICES,
    office_title,
)
from api.schemas.admin_people import PersonCreateRequest, PersonUpdate, TenureWrite
from api.services.admin_review import apply_person_value_change, close_open_discrepancies
from api.services.speakers import ADVOCATE_LABEL_MAP


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _missing_fields(person: Person, tenure_count: int) -> list[str]:
    """Return list of missing field labels, branched by is_justice.

    Person-level Role is no longer checked — role now lives on
    argument_participants, not on Person.

    Advocate rows (is_justice is False, D-05): "first name"/"last name"/
    "photo"/"bio" only.
    Bench rows (is_justice is True, D-06): the same four, plus "birthdate"
    when birthdate is None, plus "no tenures" when tenure_count == 0.

    "name review" is appended for EITHER tab whenever person.review_state is
    NEEDS_REVIEW (Phase 49 D-08, D-11 — carrying Phase 38 D-12 forward
    unchanged) — unlike every other label here it does not indicate a NULL
    field, it flags an ambiguous legacy full_name this row's structured
    parts could not be confidently derived from (migration 0022/0029 or
    later extraction). Reusing this same list/pill mechanism (rather than a
    new UI surface) is the explicit Phase 38 D-12/D-13 decision: the
    existing People-directory attention pattern is tried first instead of a
    new cross-feature dashboard queue.

    tenure_count is a pre-fetched count (built once by the caller across all
    rows in a single query) — this function never issues its own tenure
    query, keeping list_people N+1-free.

    Label vocabulary (lowercased, space-separated) is shared with the
    `missing` query-param filter in list_people so pill labels and filter
    values agree on one vocabulary.
    """
    missing: list[str] = []
    if person.first_name is None:
        missing.append("first name")
    if person.last_name is None:
        missing.append("last name")
    if person.photo_url is None:
        missing.append("photo")
    if person.bio_text is None:
        missing.append("bio")
    if person.is_justice:
        if person.birthdate is None:
            missing.append("birthdate")
        if tenure_count == 0:
            missing.append("no tenures")
    if person.review_state == ReviewState.NEEDS_REVIEW:
        missing.append("name review")
    return missing


def _tenure_coverage(tenures: list[CourtTenure]) -> str | None:
    """Return a display string summarizing a person's tenure date range.

    Earliest tenure start year through latest tenure end year, e.g.
    "1972–2005". An open-ended tenure (end_date IS NULL — currently
    active) renders as "{start}–present". Zero tenures (or tenures with
    no start_date at all) returns None so the frontend can render its own
    "No tenure" copy.
    """
    starts = [t.start_date for t in tenures if t.start_date is not None]
    if not starts:
        return None
    start_year = min(starts).year
    if any(t.end_date is None for t in tenures):
        return f"{start_year}–present"
    end_dates = [t.end_date for t in tenures if t.end_date is not None]
    end_year = max(end_dates).year if end_dates else start_year
    return f"{start_year}–{end_year}"


async def _replace_tenures(
    db: AsyncSession, person_id: int, tenures: list[TenureWrite]
) -> None:
    """Delete all existing CourtTenure rows for person_id and insert the submitted rows.

    This implements the delete-and-reinsert strategy (D-09, Pattern 5).
    Every submitted row is inserted — there is no blank-row skip. TenureWrite
    already requires a canonical office (Literal["chief", "associate"]), so a
    caller that wants zero tenures submits an empty list; that is a
    deliberate "no tenures" state, not something this function infers from a
    row's other fields.

    All rows' office values are validated up front, before the delete
    executes — this is defense-in-depth alongside the
    TenureWrite Pydantic schema and the DB CHECK constraint
    (ck_court_tenures_office): no row is deleted or inserted until every
    row in the list is confirmed canonical.

    Date strings are parsed with datetime.date.fromisoformat() (Pitfall 6).
    Raises ValueError on malformed date strings or an invalid office so the
    router can return 422 before any DB write completes.

    Does NOT commit — the caller (update_person) commits the full transaction.
    """
    for t in tenures:
        if t.office not in VALID_OFFICES:
            raise ValueError(
                f"Invalid tenure office: {t.office!r} — must be 'chief' or 'associate'."
            )

    await db.execute(
        delete(CourtTenure)
        .where(CourtTenure.person_id == person_id)
        .execution_options(synchronize_session=False)
    )
    for t in tenures:
        # Parse date strings — raises ValueError on malformed input (Pitfall 6)
        start_date: Optional[datetime.date] = None
        end_date: Optional[datetime.date] = None
        if t.start_date:
            start_date = datetime.date.fromisoformat(t.start_date)
        if t.end_date:
            end_date = datetime.date.fromisoformat(t.end_date)
        db.add(
            CourtTenure(
                person_id=person_id,
                office=t.office,
                start_date=start_date,
                end_date=end_date,
                appointed_by=t.appointed_by or None,
                appointing_president_party=t.appointing_president_party or None,
                reason_left=t.reason_left or None,
            )
        )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def list_people(
    db: AsyncSession,
    is_justice: bool | None = None,
    missing: str | None = None,
    tenure_gaps: bool = False,
) -> list[dict]:
    """Return Person rows for the Bench/Advocate directory tabs (D-01 through D-06).

    Sorted by COALESCE(last_name, full_name) ascending so that people whose
    last_name is not yet populated (legacy rows, pre-Phase-9 backfill) are
    ordered by full_name as a fallback rather than being pushed to the bottom
    of the directory (which NULLS LAST on last_name alone would cause).

    is_justice filters by tab: True = Bench, False = Advocate,
    None = no tab filter (defensive only — the frontend always passes a tab,
    defaulting to Bench per D-03).

    missing is a single field-label filter driven by the click-to-filter
    pills — one of "first name"/"last name"/"photo"/"bio"/"birthdate"/
    "no tenures" (the exact vocabulary _missing_fields produces, T-27-03).
    Any other value (or None) applies no filter — never interpolated into SQL.

    tenure_gaps=True restricts to bench speakers who have at least one
    argument appearance where argued_date falls outside all their CourtTenure
    windows — Bench-tab-only; the frontend only
    sends this on the Bench tab.

    Person-level Role is no longer joined or returned — role now
    lives on argument_participants.

    Returns a list of dicts with keys: id, full_name, missing, is_justice,
    argument_count, tenure_coverage, has_tenure_gap.
    - argument_count is a DISTINCT count of ArgumentParticipant.argument_id
      (distinct arguments, not participant rows, PDIR-04); populated for
      Advocate rows, None for Bench rows.
    - tenure_coverage is a display string ("1972–2005"/"1972–present")
      derived from the person's tenure rows, or None when they have zero
      tenures.
    - has_tenure_gap mirrors the tenure_gaps filter logic per person (True
      only for Justices with an argued_date not covered by any tenure).
    All three are computed from a single tenure prefetch per call (no
    per-person N+1 query, mirroring the tenures_by_person idiom in
    list_resolve_rows_for_job, lines 647-660).
    """
    q = select(Person).order_by(
        sqlfunc.coalesce(Person.last_name, Person.full_name).asc()
    )

    if is_justice is not None:
        q = q.where(Person.is_justice.is_(is_justice))

    missing_filters = {
        "first name": Person.first_name.is_(None),
        "last name": Person.last_name.is_(None),
        "photo": Person.photo_url.is_(None),
        "bio": Person.bio_text.is_(None),
        "birthdate": Person.birthdate.is_(None),
        "no tenures": not_(exists().where(CourtTenure.person_id == Person.id)),
        # Fixed, non-interpolated predicate for the
        # "Name review" filter pill, re-pointed from the Phase 38 boolean
        # to the unified review_state enum; applies to either tab (unlike
        # "birthdate"/"no tenures", which are bench-only in practice via
        # _missing_fields). The dictionary key and operator-visible label
        # stay the literal string "name review" — unchanged.
        "name review": Person.review_state == ReviewState.NEEDS_REVIEW,
    }
    if missing in missing_filters:
        q = q.where(missing_filters[missing])

    # Gap-detection subquery: people who have at least one
    # BENCH appearance in an argument where no CourtTenure covers the
    # argued_date (Pattern 7). Reused both as the tenure_gaps filter below
    # and to compute has_tenure_gap on every row further down.
    covering_tenure = exists(
        select(CourtTenure.id).where(
            and_(
                CourtTenure.person_id == ArgumentParticipant.person_id,
                CourtTenure.start_date <= Argument.argued_date,
                or_(
                    CourtTenure.end_date.is_(None),
                    CourtTenure.end_date >= Argument.argued_date,
                ),
            )
        )
    )
    gap_person_ids_query = (
        select(ArgumentParticipant.person_id)
        .join(Argument, Argument.id == ArgumentParticipant.argument_id)
        .where(
            ArgumentParticipant.side == SideEnum.BENCH,
            ArgumentParticipant.person_id.isnot(None),
            # Argued_date is nullable (job-driven ingest leaves NULL
            # instead of a synthetic date). Any comparison against NULL is
            # NULL in SQL, so covering_tenure can never match for a dateless
            # argument and not_(covering_tenure) would always be true —
            # falsely flagging a gap that can't actually be determined.
            Argument.argued_date.isnot(None),
            not_(covering_tenure),
        )
        .distinct()
    )
    if tenure_gaps:
        q = q.where(Person.id.in_(gap_person_ids_query))

    result = await db.execute(q)
    people = result.scalars().all()
    person_ids = [person.id for person in people]

    # Prefetch full tenure rows per person in one query (mirrors the
    # tenures_by_person idiom in list_resolve_rows_for_job) — feeds
    # _missing_fields' tenure_count, tenure_coverage, and has_tenure_gap
    # without a per-person query.
    tenures_by_person: dict[int, list[CourtTenure]] = {}
    if person_ids:
        tenure_result = await db.execute(
            select(CourtTenure).where(CourtTenure.person_id.in_(person_ids))
        )
        for t in tenure_result.scalars().all():
            tenures_by_person.setdefault(t.person_id, []).append(t)

    # Prefetch distinct-argument counts per person (PDIR-04 — distinct
    # arguments, not participant rows).
    argument_counts: dict[int, int] = {}
    if person_ids:
        arg_count_result = await db.execute(
            select(
                ArgumentParticipant.person_id,
                sqlfunc.count(sqlfunc.distinct(ArgumentParticipant.argument_id)),
            )
            .where(ArgumentParticipant.person_id.in_(person_ids))
            .group_by(ArgumentParticipant.person_id)
        )
        argument_counts = dict(arg_count_result.all())

    # Restrict the gap-detection query to the current result set so
    # has_tenure_gap is annotated for exactly the rows being returned.
    gap_person_ids: set[int] = set()
    if person_ids:
        gap_result = await db.execute(
            gap_person_ids_query.where(
                ArgumentParticipant.person_id.in_(person_ids)
            )
        )
        gap_person_ids = {row[0] for row in gap_result.all()}

    rows: list[dict] = []
    for person in people:
        person_tenures = tenures_by_person.get(person.id, [])
        rows.append(
            {
                "id": person.id,
                "full_name": person.full_name,
                "missing": _missing_fields(person, len(person_tenures)),
                "is_justice": person.is_justice,
                "argument_count": (
                    argument_counts.get(person.id) if not person.is_justice else None
                ),
                "tenure_coverage": _tenure_coverage(person_tenures),
                "has_tenure_gap": person.id in gap_person_ids,
                # Phase 49 addition
                "review_state": person.review_state.value,
            }
        )
    return rows


async def get_people_stats(db: AsyncSession) -> dict:
    """Aggregate counts for the People stat card — total + incomplete.

    Reuses list_people(db) unfiltered (both tabs) and counts/filters in Python
    (D-05 — this must NOT add a new SQL "any missing field" filter mode to
    list_people; the People directory is a small/bounded table so a Python
    filter over the full result set is acceptable).
    """
    rows = await list_people(db)
    total = len(rows)
    incomplete = sum(1 for r in rows if r["missing"])
    return {"total": total, "incomplete": incomplete}


async def get_incomplete_people(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Top-``limit`` incomplete people across both tabs (DASH-03 Needs Attention).

    One combined People sub-list spanning both Bench and Advocate tabs —
    reuses list_people(db) unfiltered and slices in Python; no new SQL filter
    mode is added.
    """
    rows = await list_people(db)
    return [r for r in rows if r["missing"]][:limit]


async def get_tenure_gap_justices(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Top-``limit`` tenure-gap Justices (DASH-03 Needs Attention, D-06).

    Delegates to the existing public list_people(is_justice=True, tenure_gaps=True)
    rather than duplicating the private gap_person_ids_query subquery defined
    inside list_people (that local variable is not importable/exported).
    """
    rows = await list_people(db, is_justice=True, tenure_gaps=True)
    return rows[:limit]


async def get_person_detail(db: AsyncSession, person_id: int) -> dict | None:
    """Return full person data for the edit form, including all tenure rows.

    Returns None if the person does not exist.
    Tenure rows are ordered by start_date ascending (nulls first).
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    tenure_result = await db.execute(
        select(CourtTenure)
        .where(CourtTenure.person_id == person_id)
        .order_by(CourtTenure.start_date.asc().nullsfirst())
    )
    tenures = tenure_result.scalars().all()

    return {
        "id": person.id,
        "full_name": person.full_name,
        "bio_text": person.bio_text,
        "photo_url": person.photo_url,
        "tenures": [
            {
                "office": t.office,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "appointed_by": t.appointed_by,
                "appointing_president_party": t.appointing_president_party,
                "reason_left": t.reason_left,
            }
            for t in tenures
        ],
        # Phase 9 additions — all six new fields must be explicitly included so
        # PersonDetail(**p) in the router does not silently default them to None
        # on page reload (Pitfall 2)
        "first_name": person.first_name,
        "last_name": person.last_name,
        "middle_name": person.middle_name,
        "name_suffix": person.name_suffix,
        # Appointment columns removed from Person
        # Phase 18 addition — must be explicit to avoid silent default on reload (Pitfall 2)
        "is_justice": person.is_justice,
        # Phase 27 addition — migration 0016; the person-level Role
        # foreign key and its display name have been dropped entirely —
        # role now lives on argument_participants, not on Person.
        "birthdate": person.birthdate.isoformat() if person.birthdate else None,
        # Phase 49 additions — migration 0029: must be
        # explicit so PersonDetail(**p) in the router does not silently
        # default them on reload (same Pitfall 2 discipline as the fields
        # above). provenance_metadata is returned as-is (already a plain
        # dict from JSONB) — PersonDetail's typed PersonProvenanceMetadata
        # field validates/coerces it at the response boundary.
        "review_state": person.review_state.value,
        "provenance_metadata": person.provenance_metadata,
        # Phase 39 addition — migration 0023: must be explicit, same
        # Pitfall 2 discipline as birthdate above.
        "death_date": person.death_date.isoformat() if person.death_date else None,
    }


async def update_person(
    db: AsyncSession, person_id: int, body: PersonUpdate
) -> dict | None:
    """Update a person record and optionally replace their tenure rows.

    Returns None if the person does not exist (router → 404 IDOR guard T-08-IDOR).
    Normalizes empty-string bio_text/photo_url to None (Pitfall 5) so the
    incomplete filter IS NULL check remains accurate.
    If body.tenures is not None, replaces all tenure rows atomically.
    Returns the refreshed person detail dict after committing.

    Raises ValueError (including api.domain.person_names.PersonNameError) on
    malformed date strings, an invalid tenure office, or a name-part edit
    that would leave the person with neither first_name nor last_name — the
    router catches this and returns 422 before any DB write completes.

    Phase 38 name-authority contract: there is
    no writable `full_name` field on PersonUpdate at all — the
    client can never author it directly. Whenever a name-part field
    (first_name/middle_name/last_name/name_suffix) is present in the request
    body — omitted vs. explicitly cleared distinguished via
    `model_fields_set`, exactly like bio_text/photo_url/birthdate above —
    the submitted parts are merged with the person's currently stored parts
    (an omitted part keeps its stored value; an explicitly-null/blank part
    is cleared) before calling the single shared
    `api.domain.person_names.prepare_person_name` helper. That helper
    normalizes every part, rejects a merged result with neither first nor
    last (PersonNameError -> 422, D-09), and derives the canonical
    `full_name` — assigned atomically alongside the four structured columns
    in the same in-memory Person object, committed together with everything
    else below. A successful authoritative name edit sets
    `review_state = OPERATOR_EDITED` (Phase 49 D-11 — an edit always means
    *edited*; no value-diffing, no normalization guesswork) — but
    `provenance_metadata` is deliberately left untouched: it is an
    independent audit trail of a prior extraction/migration decision
    (D-12, carrying Phase 38 D-15 forward unchanged), not something an
    edit erases.
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    # The person-level Role foreign key write has been
    # dropped entirely — role now lives on argument_participants, not on
    # Person.
    # Only write a field when the request explicitly included it.
    # These fields are split across two separate frontend forms (Identity+Person
    # Type via `save`, Bio+Photo via `photo`); each submits only its own subset
    # of PersonUpdate, leaving the rest at the Optional default of None. Writing
    # unconditionally wiped whichever fields the other form owns on every
    # alternating save. `model_fields_set` (not `is not None`) is required here —
    # the frontend represents "operator cleared this input" as an explicit
    # `null`/`""` in the JSON body, indistinguishable from "omitted" once it
    # becomes a plain None attribute; only model_fields_set still knows the key
    # was present. Mirrors the original guard for these exact fields,
    # which a later, unrelated commit accidentally reverted.
    fields_set = body.model_fields_set
    if "bio_text" in fields_set:
        person.bio_text = body.bio_text or None
    if "photo_url" in fields_set:
        person.photo_url = body.photo_url or None

    # Merge omitted-vs-cleared name
    # parts against stored state, then re-derive first/middle/last/suffix +
    # full_name atomically through the one shared helper. Only touches the
    # Person row when at least one name-part field was present in the
    # request — a PATCH that never mentions any of the four fields leaves
    # the name entirely untouched (same omitted-field discipline as every
    # other field in this function).
    name_fields_touched = fields_set & {
        "first_name",
        "middle_name",
        "last_name",
        "name_suffix",
    }
    if name_fields_touched:
        merged_first = (
            body.first_name if "first_name" in fields_set else person.first_name
        )
        merged_middle = (
            body.middle_name if "middle_name" in fields_set else person.middle_name
        )
        merged_last = (
            body.last_name if "last_name" in fields_set else person.last_name
        )
        merged_suffix = (
            body.name_suffix if "name_suffix" in fields_set else person.name_suffix
        )
        # May raise PersonNameError (a ValueError) — caller/router returns 422
        # before any DB write completes; nothing has been assigned yet.
        prepared = prepare_person_name(
            merged_first, merged_middle, merged_last, merged_suffix
        )
        # Each structured name-part column routes
        # through the ONE authority-gated writer — no second, ungated write
        # path to these columns survives. incoming_source/incoming_method
        # are "operator"/"manual": this is an operator-facing edit path.
        # A field whose write is REJECT_AND_RECORD (equal-or-lower incoming
        # authority disagreeing with an already-authoritative value) keeps
        # its ORIGINAL stored value — final_parts tracks the ACTUAL
        # post-gate value per field so full_name is re-derived from what
        # was really persisted, never from the caller's raw request.
        final_parts: dict[str, str | None] = {}
        for field, incoming_value in (
            ("first_name", prepared.first_name),
            ("middle_name", prepared.middle_name),
            ("last_name", prepared.last_name),
            ("name_suffix", prepared.name_suffix),
        ):
            decision = await apply_person_value_change(
                db,
                person=person,
                field=field,
                incoming_value=incoming_value,
                incoming_source="operator",
                incoming_method="manual",
            )
            if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                final_parts[field] = incoming_value
            else:
                final_parts[field] = getattr(person, field)

        # full_name is server-derived from the accepted parts (never
        # client-authored, T-38-07) — assigned directly rather than gated
        # separately, since it is not an independently-authored value.
        # Also re-assigned onto the structured columns so the in-memory
        # object (whose attributes the gate's own raw UPDATEs never sync,
        # execution_options(synchronize_session=False)) matches what was
        # actually persisted.
        person.first_name = final_parts["first_name"]
        person.middle_name = final_parts["middle_name"]
        person.last_name = final_parts["last_name"]
        person.name_suffix = final_parts["name_suffix"]
        person.full_name = format_full_name(
            final_parts["first_name"],
            final_parts["middle_name"],
            final_parts["last_name"],
            final_parts["name_suffix"],
        )
        # An authoritative edit always means *edited* — no
        # value-diffing, no normalization guesswork — but never touches
        # provenance_metadata, which stays as an independent, durable audit
        # trail (D-12, carrying Phase 38 D-15 forward unchanged).
        person.review_state = ReviewState.OPERATOR_EDITED

    # Appointment writes removed from Person
    # Phase 27 addition — migration 0016: normalize empty string to
    # None (Pitfall 5) so the "birthdate" missing-field check stays accurate.
    # ValueError from a malformed date string propagates to the router → 422
    # (Pitfall 6), before any DB write completes.
    if "birthdate" in fields_set:
        person.birthdate = (
            datetime.date.fromisoformat(body.birthdate) if body.birthdate else None
        )

    # Phase 39 addition — migration 0023: identical model_fields_set
    # guard as birthdate above, NOT the older `is not None` guard style used
    # below for is_justice. death_date is submitted only by the save-form
    # (Identity+Person Type); the separate photo/bio form never includes it
    # in its request body, so an unconditional write here would silently
    # wipe a stored death date on every photo/bio save (39-RESEARCH.md
    # Pitfall 5). ValueError from a malformed date string propagates to the
    # router → 422 (Pitfall 6), before any DB write completes.
    if "death_date" in fields_set:
        person.death_date = (
            datetime.date.fromisoformat(body.death_date) if body.death_date else None
        )

    # Write is_justice only when body supplies a non-None value
    # None = "leave unchanged" — consistent with other Optional fields on PersonUpdate.
    # Does NOT delete tenure rows when is_justice is False.
    if body.is_justice is not None:
        person.is_justice = body.is_justice

    if body.tenures is not None:
        # May raise ValueError on malformed date — caller catches and returns 422
        await _replace_tenures(db, person_id, body.tenures)

    await close_open_discrepancies(db, target_type="person", target_id=person_id)
    await db.commit()
    return await get_person_detail(db, person_id)


async def create_person(db: AsyncSession, body: PersonCreateRequest) -> dict:
    """Create a standalone Person from the minimum required fields.

    This is a general, unscoped create used by the People directory's
    "Create person" flow — no pipeline-run lookup, no status-paused guard,
    and no raw_speaker_label / participant-row linkage of any kind.

    There is no client-supplied `full_name` on
    PersonCreateRequest at all — it is always derived from the submitted
    structured parts through the same shared
    `api.domain.person_names.prepare_person_name` helper `update_person`
    uses. `prepare_person_name` normalizes each part and raises
    PersonNameError (a ValueError, translated to 422 by the router) when
    neither first_name nor last_name is present after normalization — the
    minimum-data invariant — so a blank/whitespace-only submission is
    rejected the same deterministic way a bad PATCH is, not via a bespoke
    `full_name`-blank check. is_justice is a required bool on
    PersonCreateRequest, so no additional server-side guard is needed for it.

    A freshly operator-created person is never ambiguous by construction —
    review_state defaults to `unreviewed` and provenance_metadata defaults
    to NULL (column defaults), matching every other never-migrated row.
    bio_text, photo_url, and birthdate remain unset at create (column
    defaults / None), and no tenure rows are created — those are filled in
    later via the existing PATCH /people/{id} update flow.

    Returns the full person detail dict via get_person_detail, matching the
    detail-refetch-after-mutation idiom every other mutation in this module
    follows (update_person, merge_people, update_photo_url, upload_photo).
    """
    # May raise PersonNameError (a ValueError) — router returns 422 before
    # any DB write completes.
    prepared = prepare_person_name(
        body.first_name, body.middle_name, body.last_name, body.name_suffix
    )

    person = Person(full_name=prepared.full_name, is_justice=body.is_justice)
    person.first_name = prepared.first_name
    person.middle_name = prepared.middle_name
    person.last_name = prepared.last_name
    person.name_suffix = prepared.name_suffix
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return await get_person_detail(db, person.id)


# TODO: orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. Plan 27-05 deletes this function's only caller (the
# createRole form action); flagged here rather than deleted to avoid
# breaking imports mid-phase.
async def create_role(db: AsyncSession, name: str) -> dict:
    """Find-or-create a Role by name.

    If a role with the given name already exists, returns its dict.
    Otherwise creates a new Role, flushes, commits, and returns {id, name}.
    Role.name has a unique constraint — this avoids IntegrityError by checking first.
    """
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is not None:
        return {"id": role.id, "name": role.name}
    role = Role(name=name)
    db.add(role)
    await db.flush()
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}


async def get_merge_preview(db: AsyncSession, source_id: int) -> dict | None:
    """Return row counts for the 5 FK tables that would transfer from source to target.

    Returns None if source person does not exist.
    Returns dict with keys: utterances, aliases, appearances, argument_participants, tenures.
    target_id is not required for counts — the source's rows are what transfer.
    """
    result = await db.execute(select(Person).where(Person.id == source_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    counts: dict[str, int] = {}
    for key, model, col in [
        ("utterances", Utterance, Utterance.person_id),
        ("aliases", SpeakerAlias, SpeakerAlias.person_id),
        ("appearances", CaseAppearance, CaseAppearance.person_id),
        ("argument_participants", ArgumentParticipant, ArgumentParticipant.person_id),
        ("tenures", CourtTenure, CourtTenure.person_id),
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == source_id)
        )).scalar_one()
        counts[key] = count
    return counts


async def merge_people(
    db: AsyncSession, source_id: int, target_id: int
) -> dict | None:
    """Transfer all FK rows from source to target, then delete the source Person.

    Returns the refreshed target person dict on success.
    Returns None if either source or target does not exist (router → 404).
    Raises ValueError if source_id == target_id (T-12-SELF guard).

    All 5 UPDATEs and the DELETE execute on the active implicit transaction started
    by the fetch-guard SELECTs above. db.commit() is called once after all statements
    complete — any failure rolls back all steps atomically (D-10, T-12-ATOMIC).
    Every bulk statement carries .execution_options(synchronize_session=False) (T-12-SYNC).
    """
    # T-12-SELF: merge-to-self guard — raise before any DB operation
    if source_id == target_id:
        raise ValueError("Source and target must be different people.")

    # Fetch-guard: both must exist before starting the transaction
    source = (await db.execute(select(Person).where(Person.id == source_id))).scalar_one_or_none()
    if source is None:
        return None
    target = (await db.execute(select(Person).where(Person.id == target_id))).scalar_one_or_none()
    if target is None:
        return None

    # Atomic transfer using the session's active implicit transaction
    for model, col in [
        (Utterance, Utterance.person_id),
        (SpeakerAlias, SpeakerAlias.person_id),
        (CaseAppearance, CaseAppearance.person_id),
        (ArgumentParticipant, ArgumentParticipant.person_id),
        (CourtTenure, CourtTenure.person_id),
    ]:
        await db.execute(
            update(model)
            .where(col == source_id)
            .values({col.key: target_id})
            .execution_options(synchronize_session=False)
        )
    await db.execute(
        delete(Person)
        .where(Person.id == source_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    # Transaction committed — fetch refreshed target
    return await get_person_detail(db, target_id)


async def delete_person_if_orphan(db: AsyncSession, person_id: int) -> bool | None:
    """Delete a person only if they have zero rows across all 5 FK tables.

    Returns True on successful deletion.
    Returns False if any FK row exists (router → 409 Conflict); person row is NOT deleted.
    Returns None if the person does not exist (router → 404).

    Server-side orphan check is authoritative — client disabled state is defense-in-depth
    only (D-06, T-12-ORPHAN). COUNT check covers all 5 FK tables.
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    # Delete name-variant aliases first — they are intrinsic to the person (Gap B fix).
    await db.execute(
        delete(SpeakerAlias)
        .where(SpeakerAlias.person_id == person_id)
        .execution_options(synchronize_session=False)
    )

    for model, col in [
        (Utterance, Utterance.person_id),
        (CaseAppearance, CaseAppearance.person_id),
        (ArgumentParticipant, ArgumentParticipant.person_id),
        (CourtTenure, CourtTenure.person_id),
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == person_id)
        )).scalar_one()
        if count > 0:
            return False  # Not orphaned — caller returns 409

    await db.execute(
        delete(Person)
        .where(Person.id == person_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return True


async def update_photo_url(db: AsyncSession, person_id: int, photo_url: str) -> dict | None:
    """Set photo_url directly without touching Spaces (URL-only update path, D-03).

    Returns refreshed PersonDetail dict, or None if person does not exist.
    Normalizes empty/whitespace-only URL to None (Pitfall 5 convention).
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    person.photo_url = photo_url.strip() or None
    await db.commit()
    return await get_person_detail(db, person_id)


async def upload_photo(
    db: AsyncSession,
    person_id: int,
    file_bytes: bytes,
    ext: str,
    content_type: str,
) -> dict | None:
    """Store image bytes via Spaces (if configured) or local disk, then update photo_url.

    Dual-path storage:
    - If settings.do_spaces_bucket is set: upload to Spaces via run_in_executor,
      set photo_url to the full public URL.
    - Else (local fallback): write to data/uploads/people/{person_id}.{ext},
      set photo_url to the relative path /uploads/people/{person_id}.{ext}.
      The full URL is reconstructed in +page.server.ts load by prepending FASTAPI_BASE_URL.

    Returns None if person does not exist (T-12-IDOR guard).
    Returns refreshed PersonDetail dict on success.
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    from api.core.config import settings
    from api.services import spaces as spaces_service

    if settings.do_spaces_bucket:
        key = f"people/{person_id}.{ext}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, spaces_service.upload_photo_to_spaces, file_bytes, key, content_type
        )
        photo_url = f"{settings.do_spaces_endpoint}/{settings.do_spaces_bucket}/{key}"
    else:
        # Local fallback — create directory on demand (pathlib mkdir parents=True)
        uploads_dir = Path("data/uploads/people")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        local_path = uploads_dir / f"{person_id}.{ext}"
        local_path.write_bytes(file_bytes)
        photo_url = f"/uploads/people/{person_id}.{ext}"

    person.photo_url = photo_url
    await db.commit()
    return await get_person_detail(db, person_id)


async def list_participants_for_job(
    db: AsyncSession, job_id: int
) -> list[dict] | None:
    """Return resolved participants for the argument linked to a job.

    Returns None if the job is not found or has no argument_id (no argument linked yet).
    Only includes ArgumentParticipant rows where person_id IS NOT NULL (resolved).
    Joins to Person and Role for display names, ordered by full_name.
    """
    job_result = await db.execute(select(AdminJob).where(AdminJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None or job.argument_id is None:
        return None

    result = await db.execute(
        select(
            ArgumentParticipant.id.label("participant_id"),
            ArgumentParticipant.person_id,
            ArgumentParticipant.side,
            Person.full_name,
            Role.name.label("role_name"),
        )
        .join(Person, ArgumentParticipant.person_id == Person.id)
        .outerjoin(Role, Person.role_id == Role.id)
        .where(
            ArgumentParticipant.argument_id == job.argument_id,
            ArgumentParticipant.person_id.isnot(None),
        )
        .order_by(Person.full_name)
    )
    rows = result.all()
    return [
        {
            "participant_id": row.participant_id,
            "person_id": row.person_id,
            "full_name": row.full_name,
            "role_name": row.role_name,
            "side": row.side.value if row.side is not None else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Resolve card row shape (D-10 through D-19, PJOB-14/15/16/18/19/21)
# ---------------------------------------------------------------------------


def _bench_role_and_missing_tenure(
    tenures: list[CourtTenure],
    argued_date: Optional[datetime.date],
) -> tuple[Optional[str], bool]:
    """Return (bench_role, missing_tenure) for a BENCH participant.

    Unlike speakers._tenure_role_name (which falls back to the most-recent
    tenure per D-14 for the public speaker popover), the Resolve card must show
    an EXPLICIT "Missing tenure" state when no tenure covers argued_date — no
    fallback is applied here. This intentionally diverges from the
    speaker-popover helper's behavior; do not reuse it for this purpose.

    bench_role is the formal office title (office_title(t.office) — "Chief
    Justice"/"Associate Justice", D-15), not the canonical "chief"/"associate"
    storage value.

    missing_tenure is also true when argued_date is None or tenures is empty,
    since coverage cannot be determined without both.

    A covering tenure whose office value isn't one of the two canonical
    values (see office_title()'s KeyError note — this can only happen
    mid-rollout, before migration 0021's CHECK constraint is applied) is
    treated as missing_tenure=True rather than raising, so one bad row
    doesn't 500 the whole Resolve card.
    """
    if argued_date is not None:
        for t in tenures:
            if t.start_date is not None and argued_date >= t.start_date:
                if t.end_date is None or argued_date <= t.end_date:
                    try:
                        return office_title(t.office), False
                    except KeyError:
                        return None, True
    return None, True


async def list_resolve_rows_for_job(db: AsyncSession, job_id: int) -> list[dict]:
    """Return Resolve card rows for the argument linked to a job (D-10 through D-19).

    Unlike list_participants_for_job (D-02, resolved-only), this returns EVERY
    ArgumentParticipant row for the job's linked argument, including rows where
    person_id IS NULL — raw_speaker_label must always be preserved so the
    Resolve card can render rows that still need operator intervention (D-10,
    D-11). list_participants_for_job's older behavior is left intact for any
    existing callers (per Task 1 direction).

    Raises ValueError if the job does not exist or has no linked argument, or
    if the linked argument row is somehow missing — the router (Task 3) maps
    this to a 4xx response rather than a 500 (T-25-06 IDOR/scoping guard:
    argument_id is always derived from job_id, never trusted from the client).

    editable is False only once the linked argument has been PUBLISHED —
    every other lifecycle state (candidate, draft, unpublished) renders
    editable, matching the write-side guard in
    api.services.admin_jobs.update_resolve_row_for_job (Phase 49 folded
    todo: 2026-08-21-widen-participant-editability-to-all-unpublished-
    states; supersedes the prior candidate-only guard, D-18/D-19).

    Bench rows (side == BENCH) get bench_role/missing_tenure/person_edit_href
    from a CourtTenure date-window lookup against Argument.argued_date
    (_bench_role_and_missing_tenure); argument_role mirrors bench_role for
    these rows. descriptor/descriptor_hint are always None (PJOB-15 —
    Descriptor column is advocate-only). person_edit_href is only set when
    person_id is known (there is nothing to edit for an unresolved row).

    Non-bench rows get argument_role from ADVOCATE_LABEL_MAP; descriptor/
    descriptor_hint are sourced from ArgumentParticipant.descriptor (there is
    no separate stored "originally extracted" value for descriptor — unlike
    cover_metadata for argued date/docket, ArgumentParticipant.descriptor is
    written once by the parse-time TOC extraction and is the same column the
    operator edits). bench_role, missing_tenure, and person_edit_href are
    always None/False for these rows.
    """
    job_result = await db.execute(select(AdminJob).where(AdminJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.argument_id is None:
        raise ValueError(f"AdminJob {job_id} has no linked argument")

    arg_result = await db.execute(
        select(Argument).where(Argument.id == job.argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        raise ValueError(f"Argument not found for job {job_id}")

    editable = argument.status != ArgumentStatusEnum.PUBLISHED

    participants_result = await db.execute(
        select(
            ArgumentParticipant,
            Person.full_name,
            Person.photo_url,
        )
        .outerjoin(Person, ArgumentParticipant.person_id == Person.id)
        .where(ArgumentParticipant.argument_id == argument.id)
        .order_by(ArgumentParticipant.id.asc())
    )
    participant_rows = participants_result.all()

    # Pre-fetch tenures for every resolved BENCH participant in one query,
    # avoiding an N+1 lookup per row (mirrors speakers.get_argument_speakers).
    bench_person_ids = [
        p.person_id
        for p, _full_name, _photo_url in participant_rows
        if p.side == SideEnum.BENCH and p.person_id is not None
    ]
    tenures_by_person: dict[int, list[CourtTenure]] = {}
    if bench_person_ids:
        tenures_result = await db.execute(
            select(CourtTenure).where(CourtTenure.person_id.in_(bench_person_ids))
        )
        for t in tenures_result.scalars().all():
            tenures_by_person.setdefault(t.person_id, []).append(t)

    rows: list[dict] = []
    for participant, full_name, photo_url in participant_rows:
        if participant.side == SideEnum.BENCH:
            bench_role, missing_tenure = (
                _bench_role_and_missing_tenure(
                    tenures_by_person.get(participant.person_id, []),
                    argument.argued_date,
                )
                if participant.person_id is not None
                else (None, False)
            )
            person_edit_href = (
                f"/admin/people/{participant.person_id}"
                if missing_tenure and participant.person_id is not None
                else None
            )
            rows.append(
                {
                    "participant_id": participant.id,
                    "raw_speaker_label": participant.raw_speaker_label,
                    "person_id": participant.person_id,
                    "full_name": full_name,
                    "photo_url": photo_url,
                    "side": participant.side.value,
                    "argument_role": bench_role,
                    "descriptor": None,
                    "descriptor_hint": None,
                    "bench_role": bench_role,
                    "missing_tenure": missing_tenure,
                    "person_edit_href": person_edit_href,
                    "editable": editable,
                }
            )
        else:
            rows.append(
                {
                    "participant_id": participant.id,
                    "raw_speaker_label": participant.raw_speaker_label,
                    "person_id": participant.person_id,
                    "full_name": full_name,
                    "photo_url": photo_url,
                    "side": participant.side.value,
                    "argument_role": ADVOCATE_LABEL_MAP.get(participant.side),
                    "descriptor": participant.descriptor,
                    "descriptor_hint": participant.descriptor,
                    "bench_role": None,
                    "missing_tenure": False,
                    "person_edit_href": None,
                    "editable": editable,
                }
            )
    return rows


async def bench_role_preview_for_job(
    db: AsyncSession, job_id: int, person_id: int
) -> tuple[Optional[str], bool]:
    """Preview (bench_role, missing_tenure) for a candidate BENCH pick that has
    not yet been committed to ArgumentParticipant.person_id (Plan 44-09
    tenure-preview follow-up).

    Reuses _bench_role_and_missing_tenure — the identical derivation
    list_resolve_rows_for_job (above) and admin_arguments.list_argument_speakers
    already call — against the job's linked argument's argued_date, so the
    preview can never drift from what the committed row would eventually show.
    person_id need not already be a participant on this argument: a preview by
    definition previews a pick the operator has not committed yet.

    Scoped by job_id rather than a client-supplied argument_id, matching the
    IDOR guard already established for the sibling resolve-rows routes
    (T-25-06/T-25-14) — the argument is always derived from the job, never
    trusted directly from the client.

    Raises ValueError if the job does not exist, has no linked argument, or
    person_id does not refer to an existing Person — mirroring
    list_resolve_rows_for_job's job/argument guards and matching every
    sibling person-scoped route's existence check (get_person, update_person,
    upload_person_photo, etc.), all mapped to a 422 by the router.
    """
    job_result = await db.execute(select(AdminJob).where(AdminJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.argument_id is None:
        raise ValueError(f"AdminJob {job_id} has no linked argument")

    arg_result = await db.execute(
        select(Argument).where(Argument.id == job.argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        raise ValueError(f"Argument not found for job {job_id}")

    person_result = await db.execute(select(Person).where(Person.id == person_id))
    if person_result.scalar_one_or_none() is None:
        raise ValueError(f"Person {person_id} not found")

    tenures_result = await db.execute(
        select(CourtTenure).where(CourtTenure.person_id == person_id)
    )
    tenures = list(tenures_result.scalars().all())

    return _bench_role_and_missing_tenure(tenures, argument.argued_date)
