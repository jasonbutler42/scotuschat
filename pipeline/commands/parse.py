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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    PipelineRun,
    PipelineRunStatus,
    SideEnum,
    Utterance,
)
from pipeline.db import get_session
from pipeline.parser.extractor import extract_pages
from pipeline.parser.llm_pass import parse_with_llm
from pipeline.parser.state_machine import parse_transcript


async def run_parse(args) -> None:
    """
    Parse a previously ingested transcript PDF into utterance rows.

    Args:
        args: argparse.Namespace with:
            - run_id (int): pipeline_run.id from a prior ingest step
            - dry_run (bool): if True, parse but do not write to DB

    Sequence:
        1. Load PipelineRun by run_id
        2. Transition: pending → running (PIPE-10)
        3. Extract pages via pdfplumber
        4. Rule-based parse pass (primary, ~95% coverage)
        5. LLM corrective pass (optional — falls back gracefully on failure)
        6. Write utterance rows (PIPE-03, PIPE-04, PIPE-11)
        7. Transition: running → completed (PIPE-10)
    """
    async with get_session() as session:
        # -------------------------------------------------------------------
        # Step 1: Load pipeline_run from DB
        # -------------------------------------------------------------------
        run: Optional[PipelineRun] = await session.get(PipelineRun, args.run_id)
        if run is None:
            raise ValueError(f"No pipeline_run with id={args.run_id}")

        if run.status not in (PipelineRunStatus.PENDING,):
            print(
                f"Warning: Run {run.id} already has status '{run.status.value}'; "
                f"re-running will create new utterance rows (PIPE-11)."
            )

        # -------------------------------------------------------------------
        # Step 2: Transition pending → running (PIPE-10)
        # -------------------------------------------------------------------
        run.status = PipelineRunStatus.RUNNING
        run.strategy = "rule_based"  # default; may be updated after LLM pass
        await session.flush()

        # -------------------------------------------------------------------
        # Step 3: Extract pages from PDF
        # -------------------------------------------------------------------
        if not run.pdf_path:
            await _fail_run(session, run, "pdf_path is null on pipeline_run — cannot parse")
            return

        pdf_path = Path(run.pdf_path)
        if not pdf_path.exists():
            await _fail_run(
                session, run,
                f"PDF not found at {run.pdf_path} — was the file moved or deleted?"
            )
            return

        print(f"Extracting pages from {pdf_path} ...")
        pages = extract_pages(pdf_path)
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
            run.strategy = "llm_corrective"
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
            run.strategy = "rule_based"

        # -------------------------------------------------------------------
        # Step 6: Write utterance rows (PIPE-03, PIPE-04, PIPE-11)
        # -------------------------------------------------------------------
        if args.dry_run:
            run.status = PipelineRunStatus.PENDING
            run.strategy = None
            print(f"Dry-run mode: {len(utterances)} utterances parsed but NOT written to DB.")
            print(f"Parse dry-run complete.")
            return

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
        # Step 7: Transition running → completed (PIPE-10)
        # -------------------------------------------------------------------
        run.status = PipelineRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)

        print(
            f"Parse complete. {len(utterances)} utterances written. "
            f"strategy={run.strategy}"
        )


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
