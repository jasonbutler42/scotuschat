"""
Pipeline resolve command.

Interactively resolves raw speaker labels in a parse run's utterances to
Person records via the speaker_alias lookup table.

Resolution flow per unique label:
  1. Normalize the raw label (uppercase, strip trailing colon, trim whitespace).
  2. Lookup speaker_alias by normalized_label.
     HIT  → auto-resolve: bulk UPDATE utterances.person_id, print confirmation.
     MISS → prompt operator with numbered list of existing people + "Create new".
            Save chosen mapping to speaker_alias for future auto-resolution (D-06).
  3. Also UPDATE argument_participants.person_id for the same label (Pitfall 7).

Interrupt handling (D-09 / PIPE-09):
  Ctrl+C mid-run sets resolve_run.status = NEEDS_REVIEW and exits cleanly.
  Re-running with the same parse --run-id will skip already-resolved utterances.

Critical guards:
  - NEVER modify parse_run.status (Pitfall 1).
  - UPDATE utterances WHERE raw_speaker_label == raw_label (not normalized, Pitfall 2).
  - ALL update() calls use .execution_options(synchronize_session=False) (Pitfall 3).

Usage:
    python -m pipeline resolve --run-id <parse_pipeline_run_id>
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update

from api.models.models import (
    ArgumentParticipant,
    Person,
    PipelineRun,
    PipelineRunStatus,
    Role,
    SpeakerAlias,
    Utterance,
)
from pipeline.db import get_session


def normalize_label(raw: str) -> str:
    """Normalize a raw speaker label for alias table lookup.

    Implements D-02: uppercase + strip trailing colon + trim whitespace.

    Examples:
        "Justice Kagan:"  -> "JUSTICE KAGAN"
        "CHIEF JUSTICE:"  -> "CHIEF JUSTICE"
        "  MR. JONES  "   -> "MR. JONES"
    """
    return raw.strip().rstrip(":").strip().upper()


async def run_resolve(args) -> None:
    """
    Resolve speaker labels for a given parse pipeline run.

    Args:
        args: argparse.Namespace with:
            - run_id (int): pipeline_run.id from a prior PARSE step

    Steps:
        1. Load the parse PipelineRun (read-only — never mutated).
        2. Create a new resolve PipelineRun (step="resolve", status=RUNNING).
        3. Collect unique non-null, non-stage-direction raw_speaker_labels
           for this parse run's argument and pipeline_run_id.
        4. For each label: alias lookup → auto-resolve or interactive prompt.
        5. Bulk UPDATE utterances.person_id and argument_participants.person_id.
        6. Set resolve_run.status = COMPLETED.
        On KeyboardInterrupt: set resolve_run.status = NEEDS_REVIEW and return.
    """
    async with get_session() as session:
        # -------------------------------------------------------------------
        # Step 1: Load the parse run (read-only input)
        # -------------------------------------------------------------------
        parse_run: Optional[PipelineRun] = await session.get(
            PipelineRun, args.run_id
        )
        if parse_run is None:
            raise ValueError(f"No pipeline_run with id={args.run_id}")

        if parse_run.step != "parse":
            raise ValueError(
                f"pipeline_run {args.run_id} has step='{parse_run.step}'; "
                "expected step='parse'. Pass the ID of a parse run."
            )

        # -------------------------------------------------------------------
        # Step 2: Create a new resolve PipelineRun
        # NEVER mutate parse_run.status (Pitfall 1)
        # -------------------------------------------------------------------
        resolve_run = PipelineRun(
            argument_id=parse_run.argument_id,
            step="resolve",
            status=PipelineRunStatus.RUNNING,
        )
        session.add(resolve_run)
        await session.flush()  # get resolve_run.id

        # Track which person_id was assigned to each raw_label
        # for the argument_participants update (Step 5)
        resolved_map: dict[str, int] = {}  # raw_label -> person_id

        # -------------------------------------------------------------------
        # Steps 3–5: Collect labels and resolve (wrapped for KeyboardInterrupt)
        # The entire resolve loop — including the labels query — is inside
        # the try block so that Ctrl+C at any point sets NEEDS_REVIEW.
        # -------------------------------------------------------------------
        try:
            # Step 3: Collect unique raw labels for this parse run
            labels_result = await session.execute(
                select(Utterance.raw_speaker_label)
                .distinct()
                .where(
                    Utterance.argument_id == parse_run.argument_id,
                    Utterance.pipeline_run_id == args.run_id,
                    Utterance.is_stage_direction == False,  # noqa: E712
                    Utterance.raw_speaker_label != None,  # noqa: E711
                )
            )
            raw_labels: list[str] = [row[0] for row in labels_result.all()]

            print(
                f"Resolving {len(raw_labels)} unique labels — "
                "checking alias table..."
            )

            # Step 4: Resolve each unique label
            for raw_label in raw_labels:
                normalized = normalize_label(raw_label)

                # ---- Alias lookup (always use normalized for lookup) ----
                alias_result = await session.execute(
                    select(SpeakerAlias).where(
                        SpeakerAlias.normalized_label == normalized
                    )
                )
                alias: Optional[SpeakerAlias] = alias_result.scalar_one_or_none()

                if alias is not None:
                    # ---- HIT: auto-resolve ----
                    person: Optional[Person] = await session.get(
                        Person, alias.person_id
                    )
                    print(f"Auto-resolved: {raw_label!r} -> {person.full_name}")
                    person_id = alias.person_id

                else:
                    # ---- MISS: interactive prompt ----
                    person_id = await _prompt_operator(
                        session, raw_label, normalized
                    )

                # ---- Bulk UPDATE utterances (Pitfall 2: use raw_label) ----
                await session.execute(
                    update(Utterance)
                    .where(
                        Utterance.argument_id == parse_run.argument_id,
                        Utterance.pipeline_run_id == args.run_id,
                        Utterance.raw_speaker_label == raw_label,
                    )
                    .values(person_id=person_id)
                    .execution_options(synchronize_session=False)  # Pitfall 3
                )

                resolved_map[raw_label] = person_id

            # ----------------------------------------------------------------
            # Step 5: Update argument_participants.person_id (Pitfall 7)
            # ----------------------------------------------------------------
            for raw_label, person_id in resolved_map.items():
                await session.execute(
                    update(ArgumentParticipant)
                    .where(
                        ArgumentParticipant.argument_id == parse_run.argument_id,
                        ArgumentParticipant.raw_speaker_label == raw_label,
                    )
                    .values(person_id=person_id)
                    .execution_options(synchronize_session=False)  # Pitfall 3
                )

            # ----------------------------------------------------------------
            # Step 6: Mark resolve run COMPLETED
            # ----------------------------------------------------------------
            resolve_run.status = PipelineRunStatus.COMPLETED
            resolve_run.completed_at = datetime.now(timezone.utc)
            print(
                f"Resolve complete. {len(resolved_map)} labels resolved. "
                f"resolve pipeline_run.id = {resolve_run.id}"
            )

        except KeyboardInterrupt:
            resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
            await session.flush()
            print(
                "\nInterrupted — resolve run status set to needs_review. "
                "Re-run with the same --run-id to continue."
            )
            return


async def _prompt_operator(session, raw_label: str, normalized: str) -> int:
    """
    Display a numbered list of existing people and prompt the operator to
    select a match or create a new person.

    Saves the chosen mapping to speaker_alias for future auto-resolution (D-06).

    Returns:
        person_id (int) of the resolved person.
    """
    print(f"\nUnknown label: {raw_label!r} (normalized: {normalized!r})")

    # Query all people with their role names
    people_result = await session.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(Person.full_name)
    )
    people_rows = people_result.all()

    # Display numbered list
    for i, (person, role_name) in enumerate(people_rows, start=1):
        role_display = role_name if role_name else "no role"
        print(f"  [{i}] {person.full_name} ({role_display})")
    create_idx = len(people_rows) + 1
    print(f"  [{create_idx}] Create new person")

    while True:
        choice_str = input("Select a number: ").strip()
        try:
            choice = int(choice_str)
        except ValueError:
            print("  Please enter a number.")
            continue

        if choice == create_idx:
            # ---- Create new person ----
            person_id = await _create_new_person(session)
            break
        elif 1 <= choice <= len(people_rows):
            chosen_person, _ = people_rows[choice - 1]
            person_id = chosen_person.id
            break
        else:
            print(f"  Please enter a number between 1 and {create_idx}.")

    # Save mapping to alias table for future auto-resolution (D-06)
    new_alias = SpeakerAlias(
        normalized_label=normalized,
        person_id=person_id,
    )
    session.add(new_alias)
    await session.flush()

    return person_id


async def _create_new_person(session) -> int:
    """
    Interactively create a new Person (and optionally a new Role).

    Returns:
        person_id (int) of the newly created person.
    """
    full_name = input("Full name: ").strip()
    if not full_name:
        raise ValueError("Full name cannot be empty.")

    # Display existing roles + create-new option
    roles_result = await session.execute(select(Role).order_by(Role.name))
    roles = roles_result.scalars().all()

    print("Select a role:")
    for i, role in enumerate(roles, start=1):
        print(f"  [{i}] {role.name}")
    create_role_idx = len(roles) + 1
    print(f"  [{create_role_idx}] Create new role")

    role_id: Optional[int] = None
    while True:
        choice_str = input("Select a number: ").strip()
        try:
            choice = int(choice_str)
        except ValueError:
            print("  Please enter a number.")
            continue

        if choice == create_role_idx:
            role_name = input("New role name: ").strip()
            if not role_name:
                raise ValueError("Role name cannot be empty.")
            new_role = Role(name=role_name)
            session.add(new_role)
            await session.flush()
            role_id = new_role.id
            break
        elif 1 <= choice <= len(roles):
            role_id = roles[choice - 1].id
            break
        else:
            print(f"  Please enter a number between 1 and {create_role_idx}.")

    new_person = Person(full_name=full_name, role_id=role_id)
    session.add(new_person)
    await session.flush()

    print(f"Created new person: {full_name} (id={new_person.id})")
    return new_person.id
