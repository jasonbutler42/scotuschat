"""
Pipeline resolve command.

Resolves raw speaker labels in a parse run's utterances to Person records via
the speaker_alias lookup table.

JOB-DRIVEN MODE (--job-id set, Phase 7):
  Resolution flow per unique label:
    HIT  → auto-resolve: bulk UPDATE utterances.person_id, collect into resolved_map.
    MISS → collect a discrepancy dict for browser review; do NOT prompt terminal.

  After the loop:
    - If all labels auto-resolved: mark AdminJob COMPLETED; set resolve run COMPLETED.
    - If any labels missed: write discrepancies JSONB to AdminJob, set status=PAUSED,
      set resolve run NEEDS_REVIEW, then return. FastAPI will not spawn the next step;
      operator reviews misses in the browser via the Phase 7 admin UI.

  On any exception: mark AdminJob FAILED + error_message, then raise.

DIRECT CLI MODE (--job-id absent, legacy):
  Resolution flow per unique label:
    HIT  → auto-resolve as above.
    MISS → print the unresolved label and collect it for reporting.

  After the loop:
    - If all labels auto-resolved: set resolve run COMPLETED.
    - If any labels missed: print a summary of unresolved labels, set resolve run
      NEEDS_REVIEW, and exit cleanly. The operator re-seeds aliases and re-runs.
    On Ctrl+C: set resolve run NEEDS_REVIEW and exit (backward-compat interrupt).

Critical guards:
  - NEVER modify parse_run.status (Pitfall 1).
  - UPDATE utterances WHERE raw_speaker_label == raw_label (not normalized, Pitfall 2).
  - ALL update() calls use .execution_options(synchronize_session=False) (Pitfall 3).

Usage:
    # Job-driven (Phase 7 admin UI):
    python -m pipeline resolve --run-id <parse_pipeline_run_id> --job-id <admin_job_id>

    # Direct CLI (legacy):
    python -m pipeline resolve --run-id <parse_pipeline_run_id>
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
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
            - job_id (int | None): admin_jobs.id — when set, writes status to admin_jobs
    """
    try:
        await _run_resolve_inner(args)
    except Exception as exc:
        if args.job_id:
            try:
                async with get_session() as session:
                    await session.execute(
                        update(AdminJob)
                        .where(AdminJob.id == args.job_id)
                        .values(
                            status=AdminJobStatus.FAILED,
                            error_message=str(exc),
                        )
                        .execution_options(synchronize_session=False)
                    )
            except Exception as write_err:
                print(f"Warning: could not write FAILED status for job {args.job_id}: {write_err}")
        raise


async def _run_resolve_inner(args) -> None:
    """Core resolve logic. Errors bubble up to run_resolve for FAILED status write."""

    # ------------------------------------------------------------------
    # Step 0: Mark admin_jobs RUNNING (job-driven path only)
    # ------------------------------------------------------------------
    if args.job_id:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.RUNNING,
                    current_step=AdminJobStep.RESOLVE,
                )
                .execution_options(synchronize_session=False)
            )

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

        # Capture argument_id for post-session resolved_at update (Gap 3 gate)
        resolved_argument_id: int = parse_run.argument_id

        # Track which person_id was assigned to each raw_label
        # for the argument_participants update (Step 5)
        resolved_map: dict[str, int] = {}  # raw_label -> person_id

        # Collect ALL rows (HITs + MISSes) for browser UI JSONB
        discrepancies: list[dict] = []
        # Collect only MISS raw labels — gate for PAUSED vs COMPLETED
        misses: list[str] = []

        # -------------------------------------------------------------------
        # Steps 3–5: Collect labels and resolve
        # Direct CLI mode: wrapped for KeyboardInterrupt.
        # Job-driven mode: KeyboardInterrupt is not expected (no terminal),
        # but the try/except remains for safety.
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

            # Pre-fetch all people for candidate lists (used on MISS)
            people_result = await session.execute(
                select(Person, Role.name.label("role_name"))
                .outerjoin(Role, Person.role_id == Role.id)
                .order_by(Person.full_name)
            )
            people_rows = people_result.all()

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
                    if person is None:
                        raise ValueError(
                            f"SpeakerAlias for '{normalized}' references "
                            f"person_id={alias.person_id} which no longer exists. "
                            "Re-seed aliases before re-running."
                        )
                    print(f"Auto-resolved: {raw_label!r} -> {person.full_name}")
                    person_id = alias.person_id

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

                    # ---- Append HIT row to discrepancies for browser review ----
                    # Operator must confirm auto-matches before the job advances.
                    role_result = await session.execute(
                        select(Role.name).where(Role.id == person.role_id)
                    )
                    auto_match_role = role_result.scalar_one_or_none() if person.role_id else None

                    discrepancies.append(
                        {
                            "raw_speaker_label": raw_label,
                            "normalized": normalized,
                            "candidates": [],  # HIT rows need no candidates — operator confirms or overrides
                            "auto_match_id": person_id,
                            "auto_match_name": person.full_name,
                            "auto_match_role": auto_match_role,
                            "auto_resolved": True,
                        }
                    )

                else:
                    # ---- MISS: collect discrepancy ----
                    print(f"Alias miss: {raw_label!r} (normalized: {normalized!r})")

                    # Build candidates list from pre-fetched people
                    candidates = [
                        {
                            "id": person.id,
                            "full_name": person.full_name,
                            "role_name": role_name,
                        }
                        for person, role_name in people_rows
                    ]

                    misses.append(raw_label)
                    discrepancies.append(
                        {
                            "raw_speaker_label": raw_label,
                            "normalized": normalized,
                            "candidates": candidates,
                            "auto_match_id": None,
                            "auto_match_name": None,
                            "auto_match_role": None,
                            "auto_resolved": None,
                        }
                    )

            # ----------------------------------------------------------------
            # Step 5: Update argument_participants.person_id (Pitfall 7)
            # Only for labels that were auto-resolved (resolved_map)
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
            # Step 6: Handle outcome — paused (misses) or completed (all hit)
            # Gate on misses (labels with no alias), not discrepancies (which
            # includes HITs). This ensures all-HIT transcripts reach COMPLETED.
            # ----------------------------------------------------------------
            if misses:
                # --- Paused: write discrepancies and set NEEDS_REVIEW ---
                resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
                resolve_run.completed_at = datetime.now(timezone.utc)
                await session.flush()

                if args.job_id:
                    # Job-driven: write discrepancies to admin_jobs, then exit
                    # Flush/commit the resolve run update first
                    # (session commits on clean __aexit__ below)
                    pass  # commit happens on get_session().__aexit__

                else:
                    # Direct CLI: print only MISS labels (not HITs)
                    print(
                        f"\n{len(misses)} unresolved label(s):"
                    )
                    for label in misses:
                        print(f"  - {label!r}")
                    print(
                        "Resolve run status set to needs_review. "
                        "Seed aliases for these labels and re-run."
                    )

            else:
                # --- All auto-resolved: mark COMPLETED ---
                resolve_run.status = PipelineRunStatus.COMPLETED
                resolve_run.completed_at = datetime.now(timezone.utc)
                print(
                    f"Resolve complete. {len(resolved_map)} labels auto-resolved. "
                    f"resolve pipeline_run.id = {resolve_run.id}"
                )

        except KeyboardInterrupt:
            # Direct CLI interrupt — set NEEDS_REVIEW and exit cleanly
            # (job-driven subprocesses won't receive KeyboardInterrupt in normal flow)
            resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
            await session.flush()
            print(
                "\nInterrupted — resolve run status set to needs_review. "
                "Re-run with the same --run-id to continue."
            )
            return

    # session commits on clean __aexit__

    # ----------------------------------------------------------------
    # Post-session: write discrepancies to admin_jobs (job-driven only)
    # Done after the session commit so the resolve_run status is durable
    # before we set admin_jobs to PAUSED.
    # Gate on misses (labels with no alias). When misses is non-empty the full
    # discrepancies list (HITs + MISSes) is written to JSONB so the browser
    # can show auto-resolved labels for confirmation alongside the MISSes.
    # ----------------------------------------------------------------
    if misses and args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.PAUSED,
                    discrepancies=discrepancies,
                )
                .execution_options(synchronize_session=False)
            )
        print(
            f"Admin job {args.job_id} paused with {len(misses)} miss(es) "
            f"({len(discrepancies)} total discrepancy row(s)) — operator reviews in browser."
        )
        return  # FastAPI will NOT advance; operator acts via browser

    # ----------------------------------------------------------------
    # Mark admin_jobs COMPLETED when all labels auto-resolved (job-driven)
    # Also stamp arguments.resolved_at so the case becomes visible in /cases/
    # ----------------------------------------------------------------
    if not misses and args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.COMPLETED,
                    # Write full discrepancies (all HITs) so browser can show
                    # confirmed auto-matches even on the all-resolved path
                    discrepancies=discrepancies if discrepancies else None,
                )
                .execution_options(synchronize_session=False)
            )
            # Stamp resolved_at — Gap 3 gate (argument visible in /cases/ only after resolve)
            await session.execute(
                update(Argument)
                .where(Argument.id == resolved_argument_id)
                .values(resolved_at=datetime.now(timezone.utc))
                .execution_options(synchronize_session=False)  # Pitfall 3
            )
        print(f"Admin job {args.job_id} resolve step marked completed (all labels auto-resolved)")
