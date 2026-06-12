"""
Business logic for people queries.

Responsibilities:
  - Fetch a Person row by ID, joined to Role for role_name
  - Return a dict shaped to match PersonResponse
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Person, Role


async def get_person_by_id(db: AsyncSession, person_id: int) -> dict | None:
    """
    Return person metadata by ID, or None if not found.

    Returns a dict with shape:
        {
            "id": int,
            "full_name": str,
            "role_name": str | None,
        }

    role_name is None when the person has no role_id assigned.
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
    return {"id": person.id, "full_name": person.full_name, "role_name": role_name}
