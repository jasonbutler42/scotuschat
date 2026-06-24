"""
Pipeline CLI entry point.

Invoked as: python -m pipeline <command> [args]

Subcommands:
    ingest  — Download a PDF from supremecourt.gov and create case/argument/
              pipeline_run records in the database.
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

# asyncpg is incompatible with the Windows ProactorEventLoop (Python 3.8+ default).
# Guard with platform check so production Linux deployments are unaffected.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pipeline.commands.ingest import run_ingest
from pipeline.commands.parse import run_parse
from pipeline.commands.resolve import run_resolve
from pipeline.commands.seed_aliases import run_seed_aliases


def main() -> None:
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
            "case, argument, case_arguments, and pipeline_run records in the DB."
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
            "Additional consolidated docket numbers beyond the primary "
            "(e.g. --dockets 14-562 14-571 14-574)"
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
        help="pipeline_run.id from a prior ingest step",
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
        help="pipeline_run.id from a prior PARSE step (step='parse', status=COMPLETED)",
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

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
