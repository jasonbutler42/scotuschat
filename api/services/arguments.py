"""
Business logic for argument and utterance queries.

Responsibilities:
  - Fetch an Argument row by ID
  - Find the lead Case for that argument (via case_arguments.is_lead)
  - Filter utterances to the latest import_run_id (PIPE-11: re-running
    parse produces new rows; we show only the most recent run)
  - Return a dict shaped to match ArgumentUtterancesResponse

PIPE-11 policy:
  Prior import_run rows are never deleted after a new run — the DB accumulates
  utterances from all runs. The API always shows only the latest completed parse
  by filtering WHERE import_run_id = (SELECT MAX(import_run_id) ...).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    Argument,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportRun,
    ImportRunStatus,
    Person,
    Role,
    Utterance,
)


async def list_terms(db: AsyncSession) -> list[dict]:
    """
    Return one row per October Term that has at least one published
    argument, with a count of that term's published arguments.

    Phase 51 plan 51-04 (D-14/D-15): the term-grouped replacement for the
    old flat, ungrouped case-listing endpoint (retired in plan 51-08 once
    its last consumer was removed).

    Extends the same base query shape that retired endpoint's `get_cases()`
    used — the `CaseArgument.is_lead == True` join (so a consolidated
    docket such as Obergefell 14-556/562/571/574 contributes one row, not
    four) plus both published predicates, in ADDITION to each other, never
    in place of each other: `unpublish_argument` deliberately retains
    `published_at` (Phase 48 plan 10, Defect 2), so `published_at` alone no
    longer distinguishes PUBLISHED from UNPUBLISHED — see
    test_published_gate.py's exact-substring assertions.

    `term_year` lives on `Case`, not `Argument` — the grouping key is
    reached through the `is_lead` join, never assumed to exist on
    `Argument` directly. Counting `Argument.id` distinct means the join can
    never inflate a term's count. The WHERE predicates give "a term with
    zero published arguments does not appear at all" for free — no outer
    join is used, which would resurrect empty terms.

    Ordered by `Case.term_year` descending (most recent term first),
    matching `get_cases()`'s `argued_date DESC` intent.
    """
    result = await db.execute(
        select(Case.term_year, func.count(func.distinct(Argument.id)))
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .join(Argument, CaseArgument.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712 — SQLAlchemy requires == True
        .where(Argument.published_at.isnot(None))  # hide unpublished arguments
        .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
        # An argument with no slug has no reachable public URL (TermRow builds
        # href="/arguments/{slug}" unconditionally), so it must not be counted
        # here either — otherwise the term index advertises a count the detail
        # page cannot produce links for. Both production write paths mint a slug;
        # this is the fail-closed guard for a pre-0031 row that was never
        # reseeded. Migration 0031 deliberately backfills nothing.
        .where(Argument.slug.isnot(None))
        .group_by(Case.term_year)
        .order_by(Case.term_year.desc())
    )
    rows = result.all()
    return [
        {"term_year": term_year, "argument_count": argument_count}
        for term_year, argument_count in rows
    ]


async def list_arguments_for_term(db: AsyncSession, term_year: int) -> list[dict]:
    """
    Return a term's published arguments, one row per consolidated docket
    (via the same `is_lead` join `list_terms()` and `get_cases()` use).

    Same base query as `list_terms()` — `is_lead` join plus both published
    predicates — with `Case.term_year == term_year` added. D-16 (51-01
    checkpoint, Variant A selected): no `argument_participants` -> `people`
    join is built; that join is deferred, not discarded (see
    `51-DESIGN-DECISIONS.md` "Term-row variant (D-16)").

    Ordered by `Argument.argued_date` descending with `Argument.id` as a
    stable tiebreaker, so a term whose arguments share an argued date does
    not reorder between requests.
    """
    result = await db.execute(
        select(Case, Argument)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .join(Argument, CaseArgument.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712 — SQLAlchemy requires == True
        .where(Case.term_year == term_year)
        .where(Argument.published_at.isnot(None))  # hide unpublished arguments
        .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
        # Same fail-closed guard as list_terms(): a NULL slug would render as
        # href="/arguments/null" in TermRow rather than being omitted. Kept in
        # both queries so the term index count and this list agree.
        .where(Argument.slug.isnot(None))
        .order_by(Argument.argued_date.desc(), Argument.id.desc())
    )
    rows = result.all()
    return [
        {
            "argument_id": argument.id,
            "slug": argument.slug,
            "case_name": case.case_name,
            "docket_number": case.docket_number,
            "term_year": case.term_year,
            "argued_date": argument.argued_date,
            "question_number": argument.question_number,
        }
        for case, argument in rows
    ]


async def get_argument_by_slug(db: AsyncSession, slug: str) -> int | None:
    """
    Resolve a public `Argument.slug` to its `id`, under the SAME
    two-predicate published gate `get_argument_with_utterances` uses below
    (`published_at IS NOT NULL` AND `status == PUBLISHED`) — never one
    predicate instead of the other (T-51-02-02: a single-predicate gate
    would let an UNPUBLISHED-but-previously-published argument leak
    through `published_at`, which `unpublish_argument` deliberately
    retains, Phase 48 plan 10 Defect 2).

    Returns None when the slug does not resolve to a published argument —
    the caller (router) turns that into a 404 identical to the
    integer-id 404, never distinguishing "slug does not exist" from
    "slug exists but is not published" (same non-disclosure precedent as
    the integer-id routes).
    """
    result = await db.execute(
        select(Argument.id)
        .where(Argument.slug == slug)
        .where(Argument.published_at.isnot(None))
        .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
    )
    return result.scalar_one_or_none()


async def get_argument_with_utterances(
    db: AsyncSession,
    argument_id: int,
) -> dict | None:
    """
    Return argument metadata + latest-run utterances, or None if not found
    or not published.

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
    maximum import_run_id so callers always see the most recent parse results.
    """
    # --- Step 1: Verify the argument exists and is published ---------------
    arg_result = await db.execute(
        select(Argument)
        .where(Argument.id == argument_id)
        .where(Argument.published_at.isnot(None))  # hide unpublished arguments
        # Phase 48 plan 10, Defect 2: unpublish_argument deliberately RETAINS
        # published_at — gate on status too, in ADDITION to the
        # published_at predicate above (never in place of it — see
        # test_published_gate.py's exact-substring assertions).
        .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
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

    # --- Step 3: Find the latest completed parse run for this argument ------
    # Users always see the output of the most recent COMPLETED parse run.
    # Use the import_run table (not MAX on utterances) to avoid surfacing
    # partial writes from a crashed run with a higher ID.
    max_run_result = await db.execute(
        select(func.max(ImportRun.id)).where(
            ImportRun.argument_id == argument_id,
            ImportRun.step == "parse",
            ImportRun.status == ImportRunStatus.COMPLETED,
        )
    )
    max_run_id = max_run_result.scalar_one_or_none()

    # --- Step 4: Fetch utterances for that run, ordered by sequence --------
    # JOIN to people + roles to embed speaker_name and speaker_role.
    # Returns Row tuples (Utterance, speaker_name, speaker_role) — not scalars.
    # Build dicts explicitly: from_attributes=True cannot pull labeled columns
    # from SQLAlchemy Row tuples (Pitfall 6).
    utterances: list[dict] = []
    if max_run_id is not None:
        utterances_result = await db.execute(
            select(
                Utterance,
                func.coalesce(Person.display_name, Person.full_name).label("speaker_name"),
                Role.name.label("speaker_role"),
            )
            .outerjoin(Person, Utterance.person_id == Person.id)
            .outerjoin(Role, Person.role_id == Role.id)
            .where(
                Utterance.argument_id == argument_id,
                Utterance.import_run_id == max_run_id,
            )
            .order_by(Utterance.sequence.asc())
        )
        rows = utterances_result.all()
        utterances = [
            {
                **{c.key: getattr(utterance, c.key) for c in utterance.__table__.columns},
                "speaker_name": speaker_name,
                "speaker_role": speaker_role,
            }
            for utterance, speaker_name, speaker_role in rows
        ]

    # --- Step 5: Assemble the response dict --------------------------------
    return {
        "argument": {
            "argument_id": argument.id,
            "case_name": lead_case.case_name,
            "docket_number": lead_case.docket_number,
            "argued_date": argument.argued_date,
            "question_number": argument.question_number,
            "oyez_transcript_id": argument.oyez_transcript_id,
        },
        "utterances": utterances,
    }
