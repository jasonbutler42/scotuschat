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

from pipeline.commands.ingest import run_ingest
from pipeline.commands.parse import run_parse


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
        required=True,
        help="URL of the transcript PDF (must be https://...supremecourt.gov/...)",
    )
    ingest_p.add_argument(
        "--primary-docket",
        required=True,
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
        required=True,
        help='Human-readable case name (e.g. "Obergefell v. Hodges")',
    )
    ingest_p.add_argument(
        "--argued-date",
        required=True,
        help="Argument date in YYYY-MM-DD format (e.g. 2015-04-28)",
    )
    ingest_p.add_argument(
        "--question",
        type=int,
        default=1,
        help="Question number — Q1 or Q2 (default: 1)",
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

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(run_ingest(args))
    elif args.command == "parse":
        asyncio.run(run_parse(args))


if __name__ == "__main__":
    main()
