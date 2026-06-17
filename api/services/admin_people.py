"""
Business logic for admin people management.

Responsibilities:
  - Directory listing with missing-fields derivation (PEOPLE-01, PEOPLE-02, D-04, D-06)
  - Person detail query with tenure rows (PEOPLE-03, D-07, D-08)
  - Person update with delete-and-reinsert tenure strategy (D-09, Pattern 5)
  - Inline role find-or-create (D-10)
  - Resolved participants list for a completed job (PEOPLE-04, D-02)

Critical guards (project-wide pattern from admin_jobs.py):
  - EVERY update() / delete() statement includes .execution_options(synchronize_session=False)
  - Empty-string bio_text/photo_url normalized to None before write (Pitfall 5)
  - Date strings parsed with datetime.date.fromisoformat() (Pitfall 6)
  - Alembic is sole DDL authority (CLAUDE.md) — no direct schema creation calls
"""

import datetime
from typing import Optional

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    AdminJob,
    ArgumentParticipant,
    CourtTenure,
    Person,
    Role,
)
from api.schemas.admin_people import PersonUpdate, TenureRow


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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


async def list_people(db: AsyncSession, incomplete: bool = False) -> list[dict]:
    """Return all Person rows joined with their Role name, sorted by full_name.

    When incomplete=True, only returns people where role_id OR bio_text OR
    photo_url is NULL (D-04, PEOPLE-02).

    Returns a list of dicts with keys: id, full_name, role_id, role_name, missing.
    The missing list is derived server-side so the API response carries it directly (D-06).
    """
    q = (
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(Person.full_name)
    )
    if incomplete:
        q = q.where(
            or_(
                Person.role_id.is_(None),
                Person.bio_text.is_(None),
                Person.photo_url.is_(None),
            )
        )
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
            ArgumentParticipant.person_id,
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
            "person_id": row.person_id,
            "full_name": row.full_name,
            "role_name": row.role_name,
        }
        for row in rows
    ]
