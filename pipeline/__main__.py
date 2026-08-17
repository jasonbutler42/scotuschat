"""
Pipeline CLI entry point.

Invoked as: python -m pipeline <command> [args]

Subcommands:
    ingest  — Download a PDF from supremecourt.gov and create case/argument/
              import_run records in the database.
    parse   — Parse a previously ingested transcript into utterance rows.
              (Stub in Plan 03 — fully implemented in Plan 04.)

Usage examples:
    python -m pipeline ingest \\
        --url "https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf" \\
        --primary-docket 14-556 \\
        --dockets 14-562 14-571 14-574 \\
        --case-name "Obergefell v. Hodges" \\
        --argued-date 2015-04-28

    python -m pipeline parse --run-id 1
    python -m pipeline parse --run-id 1 --dry-run
"""

import argparse
import asyncio
import sys

from sqlalchemy import update

from api.models.models import AdminJob, AdminJobStatus
from pipeline.commands.ingest import run_ingest
from pipeline.commands.import_justices_csv import (
    DEFAULT_CSV_PATH,
    run_import_justices_csv,
)
from pipeline.commands.import_convokit import (
    DEFAULT_CORPUS_DIR,
    run_import_convokit,
)
from pipeline.commands.parse import run_parse
from pipeline.commands.resolve import run_resolve
from pipeline.commands.seed_aliases import run_seed_aliases
from pipeline.db import get_session


def _scrape_job_id(argv: list[str]) -> int | None:
    """
    Extract the integer following --job-id in argv, or None if absent/unparseable.

    T-24-10: only the integer job-id is trusted/used from argv here — no other
    operator-supplied token is echoed anywhere, so there is no log-injection
    surface from a rejected/malformed docket value.
    """
    try:
        idx = argv.index("--job-id")
        return int(argv[idx + 1])
    except (ValueError, IndexError):
        return None


def _write_early_failure(job_id: int | None, message: str) -> None:
    """
    Best-effort write of a bounded FAILED status for a job that crashed before
    run_ingest (or any other command) ever executed (T-24-09: startup guard).

    Mirrors the FAILED-write shape in pipeline/commands/ingest.py:201-218 (same
    columns, same execution_options). Never raises out of this function — a
    failure here must not mask or replace the original SystemExit being
    re-propagated by the caller.

    No-op when job_id is None (mirrors run_ingest's own args.job_id is not None
    guard) — there is nothing to write back to.
    """
    if job_id is None:
        return
    # T-24-10: bound the message before it reaches the DB — an argparse usage/
    # error string must never bloat the error_message Text column unbounded.
    bounded_message = message[:500]

    async def _write() -> None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == job_id)
                .values(
                    status=AdminJobStatus.FAILED,
                    error_message=bounded_message,
                )
                .execution_options(synchronize_session=False)
            )

    try:
        asyncio.run(_write())
    except Exception as write_err:
        print(f"Warning: could not write early-failure status for job {job_id}: {write_err}")


def main() -> None:
    # asyncpg is incompatible with the Windows ProactorEventLoop (Python 3.8+
    # default). Guarded with a platform check so production Linux deployments
    # are unaffected. Set here (inside main(), not at module import time) so
    # merely importing this module — e.g. pipeline/tests/test_ingest_startup_guard.py
    # imports _scrape_job_id/_write_early_failure without invoking main() —
    # does not mutate the process-wide asyncio event loop policy. That
    # import-time mutation previously leaked into every test that ran later
    # in the same pytest session (Phase 31, T-31-18): it silently changed the
    # behavior of unrelated asyncio.run() calls (e.g.
    # pipeline/commands/resolve.py's KeyboardInterrupt handling). A real CLI
    # invocation (`python -m pipeline ...`) still sets __name__ == "__main__"
    # and calls main() exactly as before — this only removes the side effect
    # for callers that merely import the module without invoking main().
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="SCOTUS Chat pipeline — offline operator CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -----------------------------------------------------------------------
    # ingest subcommand
    # -----------------------------------------------------------------------
    ingest_p = sub.add_parser(
        "ingest",
        help="Download PDF and create pipeline records",
        description=(
            "Download a transcript PDF from supremecourt.gov and create "
            "case, argument, case_arguments, and import_run records in the DB."
        ),
    )
    ingest_p.add_argument(
        "--url",
        required=False,
        default=None,
        help="URL of the transcript PDF (must be https://...supremecourt.gov/...)",
    )
    ingest_p.add_argument(
        "--spaces-key",
        required=False,
        default=None,
        help="DO Spaces object key for an operator-uploaded PDF (alternative to --url)",
    )
    ingest_p.add_argument(
        "--primary-docket",
        required=False,
        default=None,
        help="Primary docket number (e.g. 14-556)",
    )
    ingest_p.add_argument(
        "--dockets",
        nargs="+",
        default=[],
        help=(
            "Additional consolidated docket numbers beyond --primary-docket "
            "(e.g. --dockets 14-562 14-571 14-574). Ingest persists the full "
            "ordered list (primary + these) to Argument.source_dockets."
        ),
    )
    ingest_p.add_argument(
        "--case-name",
        required=False,
        default=None,
        help='Human-readable case name (e.g. "Obergefell v. Hodges")',
    )
    ingest_p.add_argument(
        "--argued-date",
        required=False,
        default=None,
        help="Argument date in YYYY-MM-DD format (e.g. 2015-04-28)",
    )
    ingest_p.add_argument(
        "--question",
        type=int,
        default=1,
        help="Question number — Q1 or Q2 (default: 1)",
    )
    ingest_p.add_argument(
        "--local-file",
        required=False,
        default=None,
        help="Absolute path to a locally saved PDF (dev fallback when object storage is not configured)",
    )
    ingest_p.add_argument(
        "--job-id",
        type=int,
        required=False,
        default=None,
        help="admin_jobs.id — when set, subprocess writes status to admin_jobs (Phase 7)",
    )

    # -----------------------------------------------------------------------
    # parse subcommand (stub — fully implemented in Plan 04)
    # -----------------------------------------------------------------------
    parse_p = sub.add_parser(
        "parse",
        help="Parse transcript into utterances (Plan 04)",
        description=(
            "Parse a previously ingested transcript PDF into utterance rows "
            "using pdfplumber + rule-based state machine + Claude corrective pass."
        ),
    )
    parse_p.add_argument(
        "--run-id",
        required=True,
        type=int,
        help="import_run.id from a prior ingest step",
    )
    parse_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse but do not write utterance rows to the DB",
    )
    parse_p.add_argument(
        "--job-id",
        type=int,
        required=False,
        default=None,
        help="admin_jobs.id — when set, subprocess writes status to admin_jobs (Phase 7)",
    )

    # -----------------------------------------------------------------------
    # resolve subcommand
    # -----------------------------------------------------------------------
    resolve_p = sub.add_parser(
        "resolve",
        help="Interactively resolve speaker labels for a parse run",
        description=(
            "For each unique speaker label in a parse run, look up the alias table "
            "or prompt the operator to map it to a Person record."
        ),
    )
    resolve_p.add_argument(
        "--run-id",
        required=True,
        type=int,
        help="import_run.id from a prior PARSE step (step='parse', status=COMPLETED)",
    )
    resolve_p.add_argument(
        "--job-id",
        type=int,
        required=False,
        default=None,
        help="admin_jobs.id — when set, subprocess writes status to admin_jobs (Phase 7)",
    )

    # -----------------------------------------------------------------------
    # seed-aliases subcommand
    # -----------------------------------------------------------------------
    sub.add_parser(
        "seed-aliases",
        help="Pre-seed Justice people records and speaker_alias rows",
        description=(
            "Insert roles, people, and speaker_alias rows for all current and "
            "relevant historical SCOTUS Justices. Idempotent — safe to re-run."
        ),
    )

    # -----------------------------------------------------------------------
    # import-justices subcommand (Phase 29 Step Zero, D-01)
    # -----------------------------------------------------------------------
    import_justices_p = sub.add_parser(
        "import-justices",
        help="Bulk-import historical justices from the tenure CSV",
        description=(
            "Load the historical Supreme Court justices tenure CSV and seed "
            "the full bench roster — upgrading the 13 existing "
            "seed_aliases.py Person rows in place (is_justice=True + "
            "court_tenures) and creating the rest, with both court_tenures "
            "rows auto-created for justices elevated from Associate to "
            "Chief (e.g. Rehnquist, Rutledge). Idempotent — safe to re-run."
        ),
    )
    import_justices_p.add_argument(
        "--csv",
        required=False,
        default=None,
        help=f"Path to the justices tenure CSV (default: {DEFAULT_CSV_PATH})",
    )

    # -----------------------------------------------------------------------
    # import-convokit subcommand (Phase 29, D-07)
    # -----------------------------------------------------------------------
    import_convokit_p = sub.add_parser(
        "import-convokit",
        help="Bulk-import historical arguments from the ConvoKit supreme-corpus",
        description=(
            "Import oral arguments for one October Term, a term range, or "
            "exactly one conversation from the Cornell ConvoKit supreme-"
            "corpus dataset, bypassing PDF/LLM parsing. Scaffolds Case/"
            "Argument/CaseArgument/ImportRun rows and resolves bench/"
            "advocate speakers into Person/ArgumentParticipant rows. "
            "Arguments land at status=pipeline, paired with a paused "
            "resolve admin job. Idempotent -- safe to re-run any term or "
            "conversation."
        ),
    )
    import_convokit_term_group = import_convokit_p.add_mutually_exclusive_group(
        required=True
    )
    import_convokit_term_group.add_argument(
        "--term", type=int, help="Single October Term year, e.g. 1955"
    )
    import_convokit_term_group.add_argument(
        "--term-range",
        type=str,
        help="Inclusive October Term range, e.g. 1955-1960",
    )
    import_convokit_term_group.add_argument(
        "--conversation-id",
        type=str,
        help=(
            "Import exactly one ConvoKit conversation by its id (e.g. "
            "15169). Its October Term is derived automatically from the "
            "conversation's own case_id -- never supplied by the operator."
        ),
    )
    import_convokit_p.add_argument(
        "--corpus-dir",
        required=False,
        default=None,
        help=(
            "Directory containing conversations.json/cases.jsonl/speakers.json "
            f"(default: {DEFAULT_CORPUS_DIR})"
        ),
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # T-24-09: argparse raises SystemExit before any command logic runs
        # (e.g. a flag-like docket value rejected as an unrecognized option).
        # Because pipeline_spawn.py launches this subprocess with stdout/stderr
        # DEVNULL, this failure would otherwise be completely invisible — the
        # admin_jobs row would stay stuck at PENDING/INGEST forever. Scrape
        # --job-id and write a best-effort FAILED status before re-raising so
        # the process still exits non-zero (exit code 0, e.g. --help, is left
        # alone — only a truthy non-zero exit code indicates a real failure).
        if exc.code:
            job_id = _scrape_job_id(sys.argv[1:])
            _write_early_failure(
                job_id,
                f"Pipeline failed at argument parsing (exit {exc.code}). "
                "Argv rejected before ingest logic ran.",
            )
        raise

    if args.command == "ingest":
        asyncio.run(run_ingest(args))
    elif args.command == "parse":
        asyncio.run(run_parse(args))
    elif args.command == "resolve":
        try:
            asyncio.run(run_resolve(args))
        except KeyboardInterrupt:
            print("Resolve interrupted.")
    elif args.command == "seed-aliases":
        asyncio.run(run_seed_aliases(args))
    elif args.command == "import-justices":
        asyncio.run(run_import_justices_csv(args))
    elif args.command == "import-convokit":
        asyncio.run(run_import_convokit(args))


if __name__ == "__main__":
    main()
