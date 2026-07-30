#!/usr/bin/env python3
"""
Offline, operator-run fixture delete routine for `import-convokit` (Phase 42,
CORPUS-14).

Why this exists (and why the admin API's argument-delete service function
cannot be reused): corpus import is idempotent-SKIP, not idempotent-upsert --
`_import_conversation` returns early whenever an `Argument.oyez_transcript_id`
match already exists, so re-running the importer after a fix silently no-ops
unless the fixture's rows are cleared first. The admin API's `delete_argument`
looks like the obvious tool for that, but it hard-gates on `status == DRAFT`
(see its own docstring), and every corpus-imported argument starts at
`status == pipeline` and never reaches DRAFT through any normal flow -- so
that service always refuses to delete a corpus fixture. Weakening that gate
to accommodate this one dev/audit use case would reopen a production safety
hole for an unrelated reason, so this script is a separate, narrowly-scoped
routine instead: it mirrors `delete_argument`'s FK-ordered cascade order, but
without the DRAFT-only gate, plus one extra defensive step (see below).

Cascade order (single transaction, one session block):
    1. utterances            (references pipeline_runs.id -- must go first)
    2. pipeline_runs
    3. argument_participants
    4. case_arguments
    5. argument_status_log   (defensive -- delete_argument never needed this
                               step since a DRAFT argument can never have one;
                               this routine has no status gate protecting it
                               the way delete_argument does, so it deletes
                               these rows too, just in case)
    6. admin_jobs.argument_id set NULL (FK nullable, no ondelete -- RESTRICT
       would otherwise raise)
    7. the argument row itself
    8. (only with --delete-case) the fixture's case row, but only when no
       *other* argument still links to it via case_arguments

Every delete/update statement is scoped by the integer argument id (or a case
id) resolved by an explicit lookup first -- never by docket number, term
year, or the conversation id string, and never by any bulk predicate that
could reach a row belonging to a different argument or case.

The advocate people rows created by the first import attempt are
deliberately left untouched -- re-import re-matches them idempotently by
their external speaker id, then by full name, so there is nothing to clean
up between attempts. Likewise, judges' tenure history is out of scope for
this routine entirely; it is maintained by a separate tool.

Usage:
    python -m scripts.delete_fixture_argument --conversation-id 15169
    python -m scripts.delete_fixture_argument --conversation-id 15169 --delete-case --yes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, func, select, update

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models.models import (  # noqa: E402
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusLog,
    Case,
    CaseArgument,
    PipelineRun,
    Utterance,
)
from pipeline.db import get_session  # noqa: E402

# One entry per dependent table, in the exact FK-safe delete order this
# routine's cascade must follow. Every model here has an `argument_id`
# column that is used to both report (count) and, in destructive mode,
# delete/scope every statement.
DEPENDENT_MODELS: list[tuple[str, type]] = [
    ("utterances", Utterance),
    ("pipeline_runs", PipelineRun),
    ("argument_participants", ArgumentParticipant),
    ("case_arguments", CaseArgument),
    ("argument_status_log", ArgumentStatusLog),
]


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--conversation-id",
        required=True,
        help=(
            "The ConvoKit conversation id to delete, matched against "
            "Argument.oyez_transcript_id."
        ),
    )
    parser.add_argument(
        "--delete-case",
        action="store_true",
        default=False,
        help=(
            "Also remove the fixture's case row (when no other argument "
            "still links to it), so a later re-import exercises the "
            "case-create branch instead of the case-reuse branch."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help=(
            "Destructive opt-in. Without this flag the script only reports "
            "what it would delete and deletes nothing."
        ),
    )
    return parser.parse_args(argv)


async def _run(conversation_id: str, delete_case: bool, destructive: bool) -> int:
    """
    Resolve, report, and (only when destructive) delete the one fixture
    argument matching conversation_id. Everything happens inside exactly one
    session block, so a mid-cascade exception rolls the whole thing back and
    no partial deletion is ever left behind.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
        arguments = result.scalars().all()

        if len(arguments) == 0:
            print(
                f"No argument found with conversation id {conversation_id!r}; "
                "nothing to delete."
            )
            return 1
        if len(arguments) > 1:
            print(
                f"Refusing to proceed: {len(arguments)} argument rows match "
                f"conversation id {conversation_id!r}; expected exactly 1 "
                "(zero and multi matches both refuse rather than guessing)."
            )
            return 1

        argument = arguments[0]
        argument_id = argument.id

        print(
            f"Resolved argument_id={argument_id} status={argument.status.value} "
            f"source_docket={argument.source_docket!r} "
            f"conversation_id={conversation_id!r}"
        )

        # Reporting: identical inventory in both report-only and destructive
        # mode, printed BEFORE any delete statement runs.
        for label, model in DEPENDENT_MODELS:
            count_result = await session.execute(
                select(func.count()).select_from(model).where(model.argument_id == argument_id)
            )
            print(f"  {label}: {count_result.scalar_one()}")

        case_ids: list[int] = []
        if delete_case:
            case_id_result = await session.execute(
                select(CaseArgument.case_id).where(CaseArgument.argument_id == argument_id)
            )
            case_ids = [row[0] for row in case_id_result.all()]
            print(f"  --delete-case: linked case id(s): {case_ids or '(none)'}")

        if not destructive:
            print("Report-only mode (pass --yes to actually delete). Database unchanged.")
            return 0

        # Destructive cascade -- FK-ordered, every statement scoped strictly
        # by the looked-up argument_id, no intermediate commit.
        await session.execute(
            delete(Utterance)
            .where(Utterance.argument_id == argument_id)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(PipelineRun)
            .where(PipelineRun.argument_id == argument_id)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(ArgumentParticipant)
            .where(ArgumentParticipant.argument_id == argument_id)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(CaseArgument)
            .where(CaseArgument.argument_id == argument_id)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(ArgumentStatusLog)
            .where(ArgumentStatusLog.argument_id == argument_id)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            update(AdminJob)
            .where(AdminJob.argument_id == argument_id)
            .values(argument_id=None)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Argument)
            .where(Argument.id == argument_id)
            .execution_options(synchronize_session=False)
        )

        if delete_case:
            for case_id in case_ids:
                other_links_result = await session.execute(
                    select(func.count())
                    .select_from(CaseArgument)
                    .where(
                        CaseArgument.case_id == case_id,
                        CaseArgument.argument_id != argument_id,
                    )
                )
                other_links = other_links_result.scalar_one()
                if other_links > 0:
                    print(
                        f"  Retaining case id {case_id}: {other_links} other "
                        "case_arguments row(s) still link to it."
                    )
                    continue
                print(f"  Deleting case id {case_id} (no other links).")
                await session.execute(
                    delete(Case)
                    .where(Case.id == case_id)
                    .execution_options(synchronize_session=False)
                )

        print(f"Deleted argument_id={argument_id} and its dependent rows.")
        return 0


def main(argv=None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args.conversation_id, args.delete_case, args.yes))


if __name__ == "__main__":
    sys.exit(main())
