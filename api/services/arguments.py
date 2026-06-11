"""
Business logic for argument and utterance queries.

Responsibilities:
  - Fetch an Argument row by ID
  - Find the lead Case for that argument (via case_arguments.is_lead)
  - Filter utterances to the latest pipeline_run_id (PIPE-11: re-running
    parse produces new rows; we show only the most recent run)
  - Return a dict shaped to match ArgumentUtterancesResponse

PIPE-11 policy:
  Prior pipeline_run rows are never deleted after a new run — the DB accumulates
  utterances from all runs. The API always shows only the latest completed parse
  by filtering WHERE pipeline_run_id = (SELECT MAX(pipeline_run_id) ...).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument, Case, CaseArgument, Utterance


async def get_argument_with_utterances(
    db: AsyncSession,
    argument_id: int,
) -> dict | None:
    """
    Return argument metadata + latest-run utterances, or None if not found.

    Returns a dict with shape:
        {
            "argument": {
                "argument_id": int,
                "case_name": str,
                "docket_number": str,
                "argued_date": date,
                "question_number": int,
            },
            "utterances": [<Utterance ORM rows>],
        }

    The utterances list is ordered by sequence ASC and filtered to the
    maximum pipeline_run_id so callers always see the most recent parse results.
    """
    # --- Step 1: Verify the argument exists --------------------------------
    arg_result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        return None

    # --- Step 2: Find the lead case ----------------------------------------
    # The lead case is the one with is_lead=True in the case_arguments join table.
    # For Obergefell, that is docket 14-556.
    lead_case_result = await db.execute(
        select(Case)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(
            CaseArgument.argument_id == argument_id,
            CaseArgument.is_lead == True,  # noqa: E712 — SQLAlchemy requires == True
        )
    )
    lead_case = lead_case_result.scalar_one_or_none()

    # Fallback: if no is_lead row exists, grab any linked case
    if lead_case is None:
        any_case_result = await db.execute(
            select(Case)
            .join(CaseArgument, CaseArgument.case_id == Case.id)
            .where(CaseArgument.argument_id == argument_id)
            .limit(1)
        )
        lead_case = any_case_result.scalar_one_or_none()

    # If there are truly no linked cases we cannot build the metadata heading
    if lead_case is None:
        return None

    # --- Step 3: Find the latest pipeline_run_id for this argument ----------
    # Users always see the output of the most recent parse run (PIPE-11).
    max_run_result = await db.execute(
        select(func.max(Utterance.pipeline_run_id)).where(
            Utterance.argument_id == argument_id
        )
    )
    max_run_id = max_run_result.scalar_one_or_none()

    # --- Step 4: Fetch utterances for that run, ordered by sequence --------
    utterances: list[Utterance] = []
    if max_run_id is not None:
        utterances_result = await db.execute(
            select(Utterance)
            .where(
                Utterance.argument_id == argument_id,
                Utterance.pipeline_run_id == max_run_id,
            )
            .order_by(Utterance.sequence.asc())
        )
        utterances = list(utterances_result.scalars().all())

    # --- Step 5: Assemble the response dict --------------------------------
    return {
        "argument": {
            "argument_id": argument.id,
            "case_name": lead_case.case_name,
            "docket_number": lead_case.docket_number,
            "argued_date": argument.argued_date,
            "question_number": argument.question_number,
        },
        "utterances": utterances,
    }
