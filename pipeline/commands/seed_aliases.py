"""
Pipeline seed-aliases command.

Pre-seeds the roles, people, and speaker_alias rows for all current and
relevant historical SCOTUS Justices. Idempotent — safe to re-run without
creating duplicate rows.

Justice list covers:
  - Current Court (Roberts through Jackson)
  - Recent historical (Scalia, Kennedy, Ginsburg, Breyer)

Label variants stored in speaker_alias follow D-02 normalization:
uppercase, no trailing colon. Each variant stored as-is (already normalized).

Usage:
    python -m pipeline seed-aliases
"""

from sqlalchemy import select

from api.models.models import Person, Role, SpeakerAlias
from pipeline.db import get_session

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_ROLES = [
    "Chief Justice",
    "Associate Justice",
    "Petitioner's Counsel",
    "Respondent's Counsel",
]

# Each tuple: (full_name, role_name, [label_variants])
_JUSTICES = [
    (
        "John G. Roberts, Jr.",
        "Chief Justice",
        ["CHIEF JUSTICE", "CHIEF JUSTICE ROBERTS"],
    ),
    (
        "Clarence Thomas",
        "Associate Justice",
        ["JUSTICE THOMAS"],
    ),
    (
        "Samuel A. Alito, Jr.",
        "Associate Justice",
        ["JUSTICE ALITO"],
    ),
    (
        "Sonia Sotomayor",
        "Associate Justice",
        ["JUSTICE SOTOMAYOR"],
    ),
    (
        "Elena Kagan",
        "Associate Justice",
        ["JUSTICE KAGAN"],
    ),
    (
        "Neil M. Gorsuch",
        "Associate Justice",
        ["JUSTICE GORSUCH"],
    ),
    (
        "Brett M. Kavanaugh",
        "Associate Justice",
        ["JUSTICE KAVANAUGH"],
    ),
    (
        "Amy Coney Barrett",
        "Associate Justice",
        ["JUSTICE BARRETT"],
    ),
    (
        "Ketanji Brown Jackson",
        "Associate Justice",
        ["JUSTICE JACKSON"],
    ),
    (
        "Antonin Scalia",
        "Associate Justice",
        ["JUSTICE SCALIA"],
    ),
    (
        "Anthony M. Kennedy",
        "Associate Justice",
        ["JUSTICE KENNEDY"],
    ),
    (
        "Ruth Bader Ginsburg",
        "Associate Justice",
        ["JUSTICE GINSBURG"],
    ),
    (
        "Stephen G. Breyer",
        "Associate Justice",
        ["JUSTICE BREYER"],
    ),
]


async def run_seed_aliases(args) -> None:
    """
    Seed roles, Justice people rows, and speaker_alias label variants.

    All inserts use check-before-insert idempotency (select → scalar_one_or_none →
    skip or add + flush). Safe to re-run any number of times.

    Args:
        args: argparse.Namespace (no arguments required by this command)
    """
    async with get_session() as session:
        # -------------------------------------------------------------------
        # Step 1: Seed roles (idempotent)
        # -------------------------------------------------------------------
        print("Seeding roles...")
        role_map: dict[str, Role] = {}

        for role_name in _ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_name)
            )
            existing_role = result.scalar_one_or_none()

            if existing_role is not None:
                role_map[role_name] = existing_role
            else:
                new_role = Role(name=role_name)
                session.add(new_role)
                await session.flush()
                role_map[role_name] = new_role

        # -------------------------------------------------------------------
        # Step 2: Seed 13 Justice people rows (idempotent)
        # -------------------------------------------------------------------
        print("Seeding 13 Justices...")
        person_map: dict[str, Person] = {}

        for full_name, role_name, _labels in _JUSTICES:
            result = await session.execute(
                select(Person).where(Person.full_name == full_name)
            )
            existing_person = result.scalar_one_or_none()

            if existing_person is not None:
                person_map[full_name] = existing_person
            else:
                role = role_map[role_name]
                new_person = Person(
                    full_name=full_name,
                    role_id=role.id,
                )
                session.add(new_person)
                await session.flush()
                person_map[full_name] = new_person

        # -------------------------------------------------------------------
        # Step 3: Seed alias variants (idempotent)
        # -------------------------------------------------------------------
        print("Seeding alias variants...")
        alias_rows_created = 0

        for full_name, _role_name, labels in _JUSTICES:
            person = person_map[full_name]

            for label in labels:
                result = await session.execute(
                    select(SpeakerAlias).where(
                        SpeakerAlias.normalized_label == label
                    )
                )
                existing_alias = result.scalar_one_or_none()

                if existing_alias is None:
                    new_alias = SpeakerAlias(
                        normalized_label=label,
                        person_id=person.id,
                    )
                    session.add(new_alias)
                    await session.flush()
                    alias_rows_created += 1

        # -------------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------------
        total_labels = sum(len(labels) for _name, _role, labels in _JUSTICES)
        print(
            f"Done — {alias_rows_created} alias rows created "
            f"({total_labels - alias_rows_created} already existed / verified)."
        )
