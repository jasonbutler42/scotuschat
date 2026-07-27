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

from api.domain.person_names import prepare_person_name
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

# Phase 38 (D-03/D-04): each justice is now authored as explicit structured
# parts (first, middle, last, suffix) rather than a hand-typed full_name
# literal -- full_name is derived at seed time through the same shared
# api.domain.person_names.prepare_person_name helper every other
# create/update/import path uses. These 13 (first, middle, last, suffix)
# tuples are exactly the values pipeline/tests/test_import_justices_csv.py's
# _SEEDED_JUSTICE_CASES fixture corpus already establishes and verifies
# reconstruct byte-identically -- pipeline/tests/test_seed_aliases.py ties
# this module's derived full_name values back to that same shared corpus.
#
# Each tuple: (first, middle, last, suffix, role_name, [label_variants])
_JUSTICES = [
    (
        "John",
        "G.",
        "Roberts",
        "Jr.",
        "Chief Justice",
        ["CHIEF JUSTICE", "CHIEF JUSTICE ROBERTS"],
    ),
    (
        "Clarence",
        "",
        "Thomas",
        "",
        "Associate Justice",
        ["JUSTICE THOMAS"],
    ),
    (
        "Samuel",
        "A.",
        "Alito",
        "Jr.",
        "Associate Justice",
        ["JUSTICE ALITO"],
    ),
    (
        "Sonia",
        "",
        "Sotomayor",
        "",
        "Associate Justice",
        ["JUSTICE SOTOMAYOR"],
    ),
    (
        "Elena",
        "",
        "Kagan",
        "",
        "Associate Justice",
        ["JUSTICE KAGAN"],
    ),
    (
        "Neil",
        "M.",
        "Gorsuch",
        "",
        "Associate Justice",
        ["JUSTICE GORSUCH"],
    ),
    (
        "Brett",
        "M.",
        "Kavanaugh",
        "",
        "Associate Justice",
        ["JUSTICE KAVANAUGH"],
    ),
    (
        "Amy",
        "Coney",
        "Barrett",
        "",
        "Associate Justice",
        ["JUSTICE BARRETT"],
    ),
    (
        "Ketanji",
        "Brown",
        "Jackson",
        "",
        "Associate Justice",
        ["JUSTICE JACKSON"],
    ),
    (
        "Antonin",
        "",
        "Scalia",
        "",
        "Associate Justice",
        ["JUSTICE SCALIA"],
    ),
    (
        "Anthony",
        "M.",
        "Kennedy",
        "",
        "Associate Justice",
        ["JUSTICE KENNEDY"],
    ),
    (
        "Ruth",
        "Bader",
        "Ginsburg",
        "",
        "Associate Justice",
        ["JUSTICE GINSBURG"],
    ),
    (
        "Stephen",
        "G.",
        "Breyer",
        "",
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

        for first, middle, last, suffix, role_name, _labels in _JUSTICES:
            # Phase 38 (D-03/D-04): full_name is always derived from the
            # authored structured parts through the one shared helper --
            # never an independent local formatter.
            prepared = prepare_person_name(
                first or None, middle or None, last or None, suffix or None
            )
            full_name = prepared.full_name

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
                    first_name=prepared.first_name,
                    middle_name=prepared.middle_name,
                    last_name=prepared.last_name,
                    name_suffix=prepared.name_suffix,
                )
                session.add(new_person)
                await session.flush()
                person_map[full_name] = new_person

        # -------------------------------------------------------------------
        # Step 3: Seed alias variants (idempotent)
        # -------------------------------------------------------------------
        print("Seeding alias variants...")
        alias_rows_created = 0

        for first, middle, last, suffix, _role_name, labels in _JUSTICES:
            full_name = prepare_person_name(
                first or None, middle or None, last or None, suffix or None
            ).full_name
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
        total_labels = sum(len(labels) for *_parts, labels in _JUSTICES)
        print(
            f"Done — {alias_rows_created} alias rows created "
            f"({total_labels - alias_rows_created} already existed / verified)."
        )
