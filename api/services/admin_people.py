"""
Business logic for admin people management.

Responsibilities:
  - Directory listing with missing-fields derivation (PEOPLE-01, PEOPLE-02, D-04, D-06)
  - Person detail query with tenure rows (PEOPLE-03, D-07, D-08)
  - Person update with delete-and-reinsert tenure strategy (D-09, Pattern 5)
  - Inline role find-or-create (D-10)
  - Resolved participants list for a completed job (PEOPLE-04, D-02)
  - Photo upload with dual-path storage (PADM-01)
  - Merge preview count query (PADM-04)
  - Atomic multi-table merge (PADM-03, D-10)
  - Orphan-only delete (PADM-02)

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

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    CaseAppearance,
    CourtTenure,
    Person,
    Role,
    SideEnum,
    SpeakerAlias,
    Utterance,
)
from api.schemas.admin_people import PersonCreateRequest, PersonUpdate, TenureRow
from api.services.speakers import ADVOCATE_LABEL_MAP


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_full_name(
    first: str, middle: str | None, last: str, suffix: str | None
) -> str:
    """Derive full_name from structured name parts (D-04).

    Joins non-blank parts with a single space.
    Middle and suffix are omitted when blank/None.
    Examples:
      first='Amy', middle='Coney', last='Barrett' -> 'Amy Coney Barrett'
      first='John', middle=None, last='Roberts', suffix='Jr.' -> 'John Roberts Jr.'
    """
    return " ".join(p for p in [first, middle or "", last, suffix or ""] if p)


def _missing_fields(person: Person, tenure_count: int) -> list[str]:
    """Return list of missing field labels, branched by is_justice (D-05, D-06).

    Person-level Role is no longer checked (D-10) — role now lives on
    argument_participants, not on Person.

    Advocate rows (is_justice is False, D-05): "first name"/"last name"/
    "photo"/"bio" only.
    Bench rows (is_justice is True, D-06): the same four, plus "birthdate"
    when birthdate is None, plus "no tenures" when tenure_count == 0.

    tenure_count is a pre-fetched count (built once by the caller across all
    rows in a single query) — this function never issues its own tenure
    query, keeping list_people N+1-free.

    Label vocabulary (lowercased, space-separated) is shared with the
    `missing` query-param filter in list_people so pill labels and filter
    values agree on one vocabulary (T-27-03).
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
    return missing


def _tenure_coverage(tenures: list[CourtTenure]) -> str | None:
    """Return a display string summarizing a person's tenure date range (PDIR-03).

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
    db: AsyncSession, person_id: int, tenures: list[TenureRow]
) -> None:
    """Delete all existing CourtTenure rows for person_id and insert the submitted rows.

    This implements the delete-and-reinsert strategy (D-09, Pattern 5).
    Only rows with a truthy seat or start_date are inserted — empty rows from
    the "Add tenure" button that were never filled in are silently discarded.

    Date strings are parsed with datetime.date.fromisoformat() (Pitfall 6).
    Raises ValueError on malformed date strings so the router can return 422.

    Does NOT commit — the caller (update_person) commits the full transaction.
    """
    await db.execute(
        delete(CourtTenure)
        .where(CourtTenure.person_id == person_id)
        .execution_options(synchronize_session=False)
    )
    for t in tenures:
        if not (t.seat or t.start_date):
            continue
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
                seat=t.seat or None,
                start_date=start_date,
                end_date=end_date,
                appointed_by=t.appointed_by or None,
                appointing_president_party=t.appointing_president_party or None,
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

    is_justice filters by tab (D-01/D-02): True = Bench, False = Advocate,
    None = no tab filter (defensive only — the frontend always passes a tab,
    defaulting to Bench per D-03).

    missing is a single field-label filter driven by the click-to-filter
    pills (D-04) — one of "first name"/"last name"/"photo"/"bio"/"birthdate"/
    "no tenures" (the exact vocabulary _missing_fields produces, T-27-03).
    Any other value (or None) applies no filter — never interpolated into SQL.

    tenure_gaps=True restricts to bench speakers who have at least one
    argument appearance where argued_date falls outside all their CourtTenure
    windows (D-15, Phase 15, PDIR-06) — Bench-tab-only; the frontend only
    sends this on the Bench tab.

    Person-level Role is no longer joined or returned (D-10) — role now
    lives on argument_participants.

    Returns a list of dicts with keys: id, full_name, missing, is_justice,
    argument_count, tenure_coverage, has_tenure_gap.
    - argument_count is a DISTINCT count of ArgumentParticipant.argument_id
      (distinct arguments, not participant rows, PDIR-04); populated for
      Advocate rows, None for Bench rows.
    - tenure_coverage is a display string ("1972–2005"/"1972–present")
      derived from the person's tenure rows, or None when they have zero
      tenures (PDIR-03).
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
    }
    if missing in missing_filters:
        q = q.where(missing_filters[missing])

    # Gap-detection subquery (D-15, PDIR-06): people who have at least one
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
            }
        )
    return rows


async def get_person_detail(db: AsyncSession, person_id: int) -> dict | None:
    """Return full person data for the edit form, including all tenure rows.

    Returns None if the person does not exist.
    Tenure rows are ordered by start_date ascending (nulls first) (D-08).
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
                "seat": t.seat,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "appointed_by": t.appointed_by,
                "appointing_president_party": t.appointing_president_party,
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
        # Phase 22 — migration 0013: appointment columns removed from Person (PEDIT-10)
        # Phase 18 addition — must be explicit to avoid silent default on reload (Pitfall 2)
        "is_justice": person.is_justice,
        # Phase 27 addition — migration 0016 (PEDIT-02); the person-level Role
        # foreign key and its display name have been dropped entirely (D-10) —
        # role now lives on argument_participants, not on Person.
        "birthdate": person.birthdate.isoformat() if person.birthdate else None,
    }


async def update_person(
    db: AsyncSession, person_id: int, body: PersonUpdate
) -> dict | None:
    """Update a person record and optionally replace their tenure rows.

    Returns None if the person does not exist (router → 404 IDOR guard T-08-IDOR).
    Normalizes empty-string bio_text/photo_url to None (Pitfall 5) so the
    incomplete filter IS NULL check remains accurate.
    If body.tenures is not None, replaces all tenure rows atomically (D-09).
    Returns the refreshed person detail dict after committing.

    Raises ValueError on malformed date strings in tenures (Pitfall 6) — the
    router catches this and returns 422 before any DB write completes.
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    if body.full_name is not None:
        person.full_name = body.full_name
    # Phase 27 (D-10): the person-level Role foreign key write has been
    # dropped entirely — role now lives on argument_participants, not on
    # Person.
    # Normalize empty strings to None (Pitfall 5) — ensures IS NULL filter works
    person.bio_text = body.bio_text if body.bio_text else None
    person.photo_url = body.photo_url if body.photo_url else None

    # Phase 9: normalize empty strings to None (same pattern as bio_text/photo_url)
    # Pitfall 4 — empty string must become NULL to keep IS NULL semantics correct
    person.first_name = body.first_name if body.first_name else None
    person.last_name = body.last_name if body.last_name else None
    person.middle_name = body.middle_name if body.middle_name else None
    person.name_suffix = body.name_suffix if body.name_suffix else None
    # Phase 22 — migration 0013: appointment writes removed from Person (PEDIT-10)
    # Phase 27 addition — migration 0016 (PEDIT-02): normalize empty string to
    # None (Pitfall 5) so the "birthdate" missing-field check stays accurate.
    # ValueError from a malformed date string propagates to the router → 422
    # (Pitfall 6), before any DB write completes.
    person.birthdate = (
        datetime.date.fromisoformat(body.birthdate) if body.birthdate else None
    )

    # Derivation: overwrite full_name only when BOTH first_name and last_name are non-empty (D-04/D-05)
    # Note: D-04 says "when first_name is non-empty" but requiring both first_name AND last_name
    # prevents overwriting a valid full_name anchor with a single-word partial value (Pitfall 3, D-05)
    if body.first_name and body.last_name:
        person.full_name = _derive_full_name(
            body.first_name,
            body.middle_name,
            body.last_name,
            body.name_suffix,
        )

    # Phase 18: write is_justice only when body supplies a non-None value (D-08)
    # None = "leave unchanged" — consistent with other Optional fields on PersonUpdate.
    # Does NOT delete tenure rows when is_justice is False (D-06, D-07).
    if body.is_justice is not None:
        person.is_justice = body.is_justice

    if body.tenures is not None:
        # May raise ValueError on malformed date — caller catches and returns 422
        await _replace_tenures(db, person_id, body.tenures)

    await db.commit()
    return await get_person_detail(db, person_id)


async def create_person(db: AsyncSession, body: PersonCreateRequest) -> dict:
    """Create a standalone Person from the minimum required fields (D-08, D-09).

    This is a general, unscoped create used by the People directory's
    "Create person" flow — no pipeline-run lookup, no status-paused guard,
    and no raw_speaker_label / participant-row linkage of any kind.

    Validation (D-08): raises ValueError when body.full_name (stripped) is
    empty. is_justice is a required bool on PersonCreateRequest, so no
    additional server-side guard is needed for it.

    Only full_name and is_justice are set on the new row — first_name,
    last_name, middle_name, name_suffix, bio_text, photo_url, and birthdate
    are left at their column defaults (None), and no tenure rows are created.
    Everything else is filled in later via the existing PATCH /people/{id}
    update flow (D-08).

    Returns the full person detail dict via get_person_detail, matching the
    detail-refetch-after-mutation idiom every other mutation in this module
    follows (update_person, merge_people, update_photo_url, upload_photo).
    """
    if not body.full_name.strip():
        raise ValueError("Full name is required.")

    person = Person(full_name=body.full_name.strip(), is_justice=body.is_justice)
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return await get_person_detail(db, person.id)


# TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. Plan 27-05 deletes this function's only caller (the
# createRole form action); flagged here rather than deleted to avoid
# breaking imports mid-phase.
async def create_role(db: AsyncSession, name: str) -> dict:
    """Find-or-create a Role by name (D-10).

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
    """Return row counts for the 4 FK tables that would transfer from source to target.

    Returns None if source person does not exist.
    Returns dict with keys: utterances, aliases, appearances, argument_participants.
    target_id is not required for counts — the source's rows are what transfer (D-09, PADM-04).
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

    All 4 UPDATEs and the DELETE execute on the active implicit transaction started
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
    """Delete a person only if they have zero rows across all 4 FK tables.

    Returns True on successful deletion.
    Returns False if any FK row exists (router → 409 Conflict); person row is NOT deleted.
    Returns None if the person does not exist (router → 404).

    Server-side orphan check is authoritative — client disabled state is defense-in-depth
    only (D-06, T-12-ORPHAN). COUNT check covers all 4 FK tables.
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
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == person_id)
        )).scalar_one()
        if count > 0:
            return False  # Not orphaned — caller returns 409 (D-06)

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

    Dual-path storage (D-01):
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
    """Return resolved participants for the argument linked to a job (D-02, PEOPLE-04).

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
# Phase 25: Resolve card row shape (D-10 through D-19, PJOB-14/15/16/18/19/21)
# ---------------------------------------------------------------------------


def _bench_role_and_missing_tenure(
    tenures: list[CourtTenure],
    argued_date: Optional[datetime.date],
) -> tuple[Optional[str], bool]:
    """Return (bench_role, missing_tenure) for a BENCH participant (D-15, D-16, PJOB-16).

    Unlike speakers._tenure_role_name (which falls back to the most-recent
    tenure per D-14 for the public speaker popover), the Resolve card must show
    an EXPLICIT "Missing tenure" state when no tenure covers argued_date — no
    fallback is applied here (D-15). This intentionally diverges from the
    speaker-popover helper's behavior; do not reuse it for this purpose.

    missing_tenure is also true when argued_date is None or tenures is empty,
    since coverage cannot be determined without both.
    """
    if argued_date is not None:
        for t in tenures:
            if t.start_date is not None and argued_date >= t.start_date:
                if t.end_date is None or argued_date <= t.end_date:
                    return t.seat, False
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

    editable is False for every row once the linked argument has left the
    'pipeline' status (D-18, D-19) — the Resolve card renders read-only.

    Bench rows (side == BENCH) get bench_role/missing_tenure/person_edit_href
    from a CourtTenure date-window lookup against Argument.argued_date
    (_bench_role_and_missing_tenure); argument_role mirrors bench_role for
    these rows. title/title_hint are always None (PJOB-15 — Title column is
    advocate-only). person_edit_href is only set when person_id is known
    (there is nothing to edit for an unresolved row).

    Non-bench rows get argument_role from ADVOCATE_LABEL_MAP; title/title_hint
    are sourced from ArgumentParticipant.title (there is no separate stored
    "originally extracted" value for title — unlike cover_metadata for argued
    date/docket, ArgumentParticipant.title is written once by the parse-time
    TOC extraction and is the same column the operator edits). bench_role,
    missing_tenure, and person_edit_href are always None/False for these rows.
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

    editable = argument.status == ArgumentStatusEnum.PIPELINE

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
                    "title": None,
                    "title_hint": None,
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
                    "title": participant.title,
                    "title_hint": participant.title,
                    "bench_role": None,
                    "missing_tenure": False,
                    "person_edit_href": None,
                    "editable": editable,
                }
            )
    return rows
