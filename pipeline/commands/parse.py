"""
Pipeline parse command — full implementation.

Implements the parse step: pdfplumber extraction + rule-based state machine
parser + instructor/Claude LLM corrective pass → utterance rows written to DB.

State machine (PIPE-10):
  pending → running → completed (or failed with failure_reason)

Re-run behavior (PIPE-11):
  Re-running parse for a new pipeline_run_id creates new utterance rows.
  Prior run's utterance rows are NEVER deleted.

Failure classification (PIPE-06):
  - Structural (InstructorRetryException, BadRequestError): set status=failed,
    failure_reason, return early — do NOT retry
  - Transient (RateLimitError, APIConnectionError after all tenacity retries):
    same outcome — set failed + failure_reason

PIPE-04: Every utterance row has pipeline_run_id and strategy set.
person_id is NULL at parse time — Phase 2 (Resolve) populates it.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    ArgumentParticipant,
    Case,
    CaseArgument,
    PipelineRun,
    PipelineRunStatus,
    SideEnum,
    Utterance,
)
from pipeline.db import get_session
from pipeline.parser.cover_extractor import extract_cover_metadata, extract_advocate_sides
from pipeline.parser.extractor import extract_pages
from pipeline.parser.llm_pass import parse_with_llm
from pipeline.parser.state_machine import parse_transcript


def _normalize_dashes(text: str) -> str:
    # " -- " (interruption marker) → " — " (em dash with spaces)
    text = text.replace(' -- ', ' — ')
    # All remaining en dashes, em dashes, soft hyphens → plain hyphen
    text = text.replace('–', '-')
    text = text.replace('—', '-')
    text = text.replace('­', '-')
    return text


async def run_parse(args) -> None:
    """
    Parse a previously ingested transcript PDF into utterance rows.

    Args:
        args: argparse.Namespace with:
            - run_id (int): pipeline_run.id from a prior ingest step
            - dry_run (bool): if True, parse but do not write to DB
            - job_id (int | None): admin_jobs.id — when set, writes status to admin_jobs

    Sequence:
        0. (job-driven) Mark admin_jobs RUNNING / PARSE
        1. Load PipelineRun by run_id
        2. Transition: pending → running (PIPE-10)
        3. Extract pages via pdfplumber
        4. Rule-based parse pass (primary, ~95% coverage)
        5. LLM corrective pass (optional — falls back gracefully on failure)
        6. Write utterance rows (PIPE-03, PIPE-04, PIPE-11)
        7. Transition: running → completed (PIPE-10)
        8. (job-driven) Mark admin_jobs COMPLETED
    """
    try:
        await _run_parse_inner(args)
    except Exception as exc:
        if args.job_id is not None:
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


async def _run_parse_inner(args) -> None:
    """Core parse logic. Errors bubble up to run_parse for FAILED status write."""

    # ------------------------------------------------------------------
    # Step 0: Mark admin_jobs RUNNING (job-driven path only)
    # ------------------------------------------------------------------
    if args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.RUNNING,
                    current_step=AdminJobStep.PARSE,
                )
                .execution_options(synchronize_session=False)
            )

    # -------------------------------------------------------------------
    # Phase 16 PARSE-01: Hoist pdf_path resolution before the main session
    # so that synchronous pdfplumber I/O never runs inside the async DB
    # transaction (RESEARCH.md Pitfall 1).
    # -------------------------------------------------------------------
    async with get_session() as _pre_session:
        _source_pre: Optional[PipelineRun] = await _pre_session.get(PipelineRun, args.run_id)
        if _source_pre is None:
            raise ValueError(f"No pipeline_run with id={args.run_id}")
        if not _source_pre.pdf_path:
            raise ValueError("pdf_path is null on source pipeline_run — cannot parse")
        _pdf_path_str = _source_pre.pdf_path

    pdf_path = Path(_pdf_path_str)
    if not pdf_path.exists():
        raise ValueError(
            f"PDF not found at {_pdf_path_str} — was the file moved or deleted?"
        )

    # Cover metadata extraction (CPU-only, synchronous pdfplumber — runs before
    # the async DB session per Pitfall 1). Returns {} on any failure (D-05).
    cover_meta = extract_cover_metadata(pdf_path)
    advocate_sides = extract_advocate_sides(pdf_path)
    if cover_meta:
        print(f"Cover metadata extracted: {list(cover_meta.keys())}")

    async with get_session() as session:
        # -------------------------------------------------------------------
        # Step 1: Load the source run to get argument_id and pdf_path
        # -------------------------------------------------------------------
        source_run: Optional[PipelineRun] = await session.get(PipelineRun, args.run_id)
        if source_run is None:
            raise ValueError(f"No pipeline_run with id={args.run_id}")

        # -------------------------------------------------------------------
        # Step 3: Extract pages from PDF
        # CR-05: extraction uses source_run.pdf_path directly. The PipelineRun
        # for this attempt is NOT added to the session until after the dry-run
        # check (step 6) — this ensures dry-run never commits a row to the DB.
        # -------------------------------------------------------------------

        print(f"Extracting pages from {pdf_path} ...")
        pages = extract_pages(pdf_path)
        pages = [_normalize_dashes(p) for p in pages]
        print(f"Extracted {len(pages)} argument pages.")

        # -------------------------------------------------------------------
        # Step 4: Rule-based parse pass (primary)
        # -------------------------------------------------------------------
        print("Running rule-based state machine parser ...")
        utterances = parse_transcript(pages)
        print(f"Rule-based pass: {len(utterances)} utterances.")

        # -------------------------------------------------------------------
        # Step 5: LLM corrective pass (conditional)
        # -------------------------------------------------------------------
        pages_text = "\n\n".join(pages)
        # strategy is tracked locally until we create the PipelineRun row
        parse_strategy = "rule_based"

        try:
            print("Running LLM corrective pass ...")
            llm_response = await parse_with_llm(pages_text)

            # On success: LLM output replaces rule-based output for full accuracy.
            # Convert LLM ParsedUtterance objects to dicts matching the rule-based format.
            from pipeline.parser.state_machine import assign_side
            llm_utterances = [
                {
                    "sequence": u.sequence,
                    "raw_speaker_label": u.raw_speaker_label,
                    "text": u.text,
                    "is_stage_direction": u.is_stage_direction,
                    "section_hint": u.section_hint,
                    "side": assign_side(u.raw_speaker_label, u.is_stage_direction),
                }
                for u in llm_response.utterances
            ]
            utterances = llm_utterances
            parse_strategy = "llm_corrective"
            print(f"LLM pass: {len(utterances)} utterances. Strategy updated to 'llm_corrective'.")

        except Exception as exc:
            # Determine if structural or transient (for logging clarity)
            exc_name = type(exc).__name__
            print(
                f"LLM corrective pass failed ({exc_name}: {exc}). "
                f"Falling back to rule-based output. Strategy remains 'rule_based'."
            )
            # For structural failures (InstructorRetryException, BadRequestError),
            # log clearly that this is not retriable.
            import anthropic as _anthropic
            try:
                import instructor as _instructor
                _structural_types = (
                    _instructor.exceptions.InstructorRetryException,
                    _anthropic.BadRequestError,
                )
            except AttributeError:
                _structural_types = (_anthropic.BadRequestError,)

            if isinstance(exc, _structural_types):
                print(
                    f"Structural LLM failure — not retrying. "
                    f"Rule-based output will be used for this run."
                )
            # Keep rule-based utterances (no early return — write what we have)
            parse_strategy = "rule_based"

        # -------------------------------------------------------------------
        # Step 6: Dry-run exit — checked BEFORE creating PipelineRun row (CR-05)
        # The session has not had run added yet so __aexit__ commits nothing
        # meaningful (only the source_run read, which is read-only).
        # -------------------------------------------------------------------
        if args.dry_run:
            print(f"Dry-run mode: {len(utterances)} utterances parsed but NOT written to DB.")
            print(f"Parse dry-run complete.")
            return

        # -------------------------------------------------------------------
        # Step 2 (deferred): Create a fresh PipelineRun for this parse attempt
        # (PIPE-11). Placed after dry-run check so no row is ever written in
        # dry-run mode.
        # -------------------------------------------------------------------
        run = PipelineRun(
            argument_id=source_run.argument_id,
            step="parse",
            status=PipelineRunStatus.RUNNING,
            strategy=parse_strategy,
            pdf_path=source_run.pdf_path,
        )
        session.add(run)
        await session.flush()
        print(f"Created parse pipeline_run id={run.id} (argument_id={run.argument_id})")

        # -------------------------------------------------------------------
        # Step 7: Write utterance rows (PIPE-03, PIPE-04, PIPE-11)
        # -------------------------------------------------------------------
        print(f"Writing {len(utterances)} utterance rows ...")
        for u in utterances:
            utterance = Utterance(
                argument_id=run.argument_id,
                pipeline_run_id=run.id,           # PIPE-04: every row links to this run
                sequence=u["sequence"],
                raw_speaker_label=u.get("raw_speaker_label"),
                text=u["text"],
                is_stage_direction=u["is_stage_direction"],
                section_hint=u.get("section_hint"),
                side=SideEnum(u["side"]),
                person_id=None,                    # null at parse time; Phase 2 populates
                strategy=run.strategy,             # PIPE-04: strategy recorded on each row
            )
            session.add(utterance)

        await session.flush()

        # -------------------------------------------------------------------
        # Step 7b: Seed argument_participants (PEOPLE-04)
        # One row per unique speaker label so resolve.py UPDATE has rows to hit.
        # person_id stays NULL — Resolve step sets it via UPDATE.
        # Select-before-insert handles parse re-runs safely.
        # -------------------------------------------------------------------
        if run.argument_id is not None:
            participant_labels = {
                (u["raw_speaker_label"], SideEnum(u["side"]))
                for u in utterances
                if u.get("raw_speaker_label") and not u.get("is_stage_direction")
            }
            if participant_labels:
                existing_result = await session.execute(
                    select(ArgumentParticipant.raw_speaker_label).where(
                        ArgumentParticipant.argument_id == run.argument_id
                    )
                )
                existing = {row[0] for row in existing_result.all()}
                new_rows = [(lbl, side) for lbl, side in participant_labels if lbl not in existing]
                for raw_label, side in new_rows:
                    session.add(ArgumentParticipant(
                        argument_id=run.argument_id,
                        raw_speaker_label=raw_label,
                        side=side,
                        person_id=None,
                    ))
                await session.flush()
                print(f"Seeded {len(new_rows)} argument_participant row(s) ({len(existing)} already existed).")

        # -------------------------------------------------------------------
        # Step 8: Transition running → completed (PIPE-10)
        # -------------------------------------------------------------------
        run.status = PipelineRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)

        print(
            f"Parse complete. {len(utterances)} utterances written. "
            f"strategy={run.strategy}"
        )

    # ------------------------------------------------------------------
    # Step 9: Mark admin_jobs COMPLETED (job-driven path only)
    # Note: current_step stays PARSE — poll endpoint advances to RESOLVE
    # atomically using the step-advance guard (Pattern 3 / D-05).
    # ------------------------------------------------------------------
    if args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(status=AdminJobStatus.COMPLETED)
                .execution_options(synchronize_session=False)
            )
        print(f"Admin job {args.job_id} parse step marked completed")


async def _fail_run(
    session: AsyncSession,
    run: PipelineRun,
    failure_reason: str,
) -> None:
    """
    Transition a running PipelineRun to FAILED and record the failure reason.

    Called when a non-retryable error occurs during parse (e.g., missing PDF,
    structural LLM failure). The session is flushed but not committed here —
    the caller's context manager commits on exit.
    """
    run.status = PipelineRunStatus.FAILED
    run.failure_reason = failure_reason
    run.completed_at = datetime.now(timezone.utc)
    await session.flush()
    print(f"Parse failed: {failure_reason}")
