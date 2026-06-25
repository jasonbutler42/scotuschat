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
    CaseAppearance,
    CourtTenure,
    Person,
    Role,
    SideEnum,
    SpeakerAlias,
    Utterance,
)
from api.schemas.admin_people import PersonUpdate, TenureRow


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


def _missing_fields(person: Person) -> list[str]:
    """Return list of missing field labels per D-04.

    A person is incomplete if role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL.
    Court tenure absence is NOT considered missing.
    Order: role, bio, photo (D-06).
    """
    missing: list[str] = []
    if person.role_id is None:
        missing.append("role")
    if person.bio_text is None:
        missing.append("bio")
    if person.photo_url is None:
        missing.append("photo")
    return missing


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
            )
        )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def list_people(
    db: AsyncSession,
    incomplete: bool = False,
    tenure_gaps: bool = False,
) -> list[dict]:
    """Return all Person rows joined with their Role name.

    Sorted by COALESCE(last_name, full_name) ascending so that people whose
    last_name is not yet populated (legacy rows, pre-Phase-9 backfill) are
    ordered by full_name as a fallback rather than being pushed to the bottom
    of the directory (which NULLS LAST on last_name alone would cause).

    When incomplete=True, only returns people where role_id OR bio_text OR
    photo_url is NULL (D-04, PEOPLE-02).

    When tenure_gaps=True, only returns bench speakers who have at least one
    argument appearance where argued_date falls outside all their CourtTenure
    windows (D-15, Phase 15).

    Returns a list of dicts with keys: id, full_name, role_id, role_name, missing.
    The missing list is derived server-side so the API response carries it directly (D-06).
    """
    q = (
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(sqlfunc.coalesce(Person.last_name, Person.full_name).asc())
    )
    if incomplete:
        q = q.where(
            or_(
                Person.role_id.is_(None),
                Person.bio_text.is_(None),
                Person.photo_url.is_(None),
            )
        )
    if tenure_gaps:
        # Subquery: people who have at least one BENCH appearance in an argument
        # where no CourtTenure covers the argued_date (Pattern 7).
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
        gap_person_ids = (
            select(ArgumentParticipant.person_id)
            .join(Argument, Argument.id == ArgumentParticipant.argument_id)
            .where(
                ArgumentParticipant.side == SideEnum.BENCH,
                ArgumentParticipant.person_id.isnot(None),
                not_(covering_tenure),
            )
            .distinct()
        )
        q = q.where(Person.id.in_(gap_person_ids))
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": person.id,
            "full_name": person.full_name,
            "role_id": person.role_id,
            "role_name": role_name,
            "missing": _missing_fields(person),
        }
        for person, role_name in rows
    ]


async def get_person_detail(db: AsyncSession, person_id: int) -> dict | None:
    """Return full person data for the edit form, including all tenure rows.

    Returns None if the person does not exist.
    Tenure rows are ordered by start_date ascending (nulls first) (D-08).
    """
    result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .where(Person.id == person_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    person, role_name = row

    tenure_result = await db.execute(
        select(CourtTenure)
        .where(CourtTenure.person_id == person_id)
        .order_by(CourtTenure.start_date.asc().nullsfirst())
    )
    tenures = tenure_result.scalars().all()

    return {
        "id": person.id,
        "full_name": person.full_name,
        "role_id": person.role_id,
        "role_name": role_name,
        "bio_text": person.bio_text,
        "photo_url": person.photo_url,
        "tenures": [
            {
                "seat": t.seat,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "end_date": t.end_date.isoformat() if t.end_date else None,
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
        "appointing_president": person.appointing_president,
        "appointing_president_party": person.appointing_president_party,
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
    # role_id may be explicitly set to None (remove role) or a new id
    person.role_id = body.role_id
    # Normalize empty strings to None (Pitfall 5) — ensures IS NULL filter works
    person.bio_text = body.bio_text if body.bio_text else None
    person.photo_url = body.photo_url if body.photo_url else None

    # Phase 9: normalize empty strings to None (same pattern as bio_text/photo_url)
    # Pitfall 4 — empty string must become NULL to keep IS NULL semantics correct
    person.first_name = body.first_name if body.first_name else None
    person.last_name = body.last_name if body.last_name else None
    person.middle_name = body.middle_name if body.middle_name else None
    person.name_suffix = body.name_suffix if body.name_suffix else None
    person.appointing_president = body.appointing_president if body.appointing_president else None
    person.appointing_president_party = body.appointing_president_party if body.appointing_president_party else None

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

    if body.tenures is not None:
        # May raise ValueError on malformed date — caller catches and returns 422
        await _replace_tenures(db, person_id, body.tenures)

    await db.commit()
    return await get_person_detail(db, person_id)


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
