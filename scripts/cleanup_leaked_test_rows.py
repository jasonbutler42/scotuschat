"""
One-time cleanup of leaked test rows in the shared dev database (D-04..D-08).

Confirmed live at time of writing (31-CONTEXT.md "Specific Ideas"): 5 duplicate
"Ketanji Brown Jackson" Person rows (ids 116, 959, 1097, 1204, 1285) plus
synthetic/orphaned Argument rows created by production service functions that
commit internally during test runs (see api/services/admin_jobs.py::create_person_for_job,
api/services/admin_arguments.py::publish_argument, and
pipeline/commands/import_convokit.py::run_import_convokit). Baseline row
counts at the time of the incident: 352 people, 211 arguments.

This script is standalone (D-07) -- not a pipeline CLI subcommand -- and is
run directly:

    python scripts/cleanup_leaked_test_rows.py               # dry-run (default)
    python scripts/cleanup_leaked_test_rows.py --execute      # deletes (Task 2)

Dry-run is the default (D-04) -- no flag means report-only, zero DELETEs.
This module currently implements detection + reporting only; the --execute
flag is defined but the deletion path itself is added in a follow-up task.

Detection does a broad sweep (D-05), not a hardcoded list of the 5 known
duplicate ids:
    1. Duplicate Person rows: any `full_name` with more than one row.
    2. Orphaned/test-fixture Argument rows: either (a) no linked utterances
       AND no linked pipeline_runs, or (b) case_name/docket_number matching
       known test-fixture conventions ("Synthetic..." case names, "...TEST..."
       docket numbers -- see api/tests/*.py fixtures). Does NOT flag
       `job-{id}` source_docket values -- that is a legitimate production
       placeholder written by pipeline/commands/ingest.py for in-progress
       admin-job arguments awaiting metadata, not test leakage.

Survivor selection for duplicate Person groups (D-06) prefers the row backed
by real data -- linked court_tenures rows, then non-null bio fields -- and
only falls back to the lowest id when a group is genuinely indistinguishable.
Never blindly keep-lowest-id.

HARD SAFETY GUARDS:
  - Connects to DATABASE_URL (the shared dev DB), NOT TEST_DATABASE_URL --
    this is deliberate; the leaked rows live in the dev DB, not the test DB.
  - Refuses to run if DATABASE_URL is unset or matches the same placeholder
    guard used throughout api/tests/conftest.py (T-31-10).

HARD CONSTRAINT (CLAUDE.md): asyncpg requires statement_cache_size=0 in
connect_args when behind Digital Ocean PgBouncer (Transaction mode).
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

# ---------------------------------------------------------------------------
# Placeholder guard -- identical to the one used throughout api/tests/*.py
# and scripts/provision_test_db.py (T-31-10).
# ---------------------------------------------------------------------------


def _db_configured(url: str) -> bool:
    """Same placeholder guard every DATABASE_URL-gated fixture/script uses."""
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Detection: duplicate Person groups + survivor selection (D-05, D-06)
# ---------------------------------------------------------------------------


async def find_duplicate_person_groups(conn: AsyncConnection):
    """Broad sweep: any `full_name` with more than one row -- not a hardcoded id list."""
    result = await conn.execute(
        text(
            """
            SELECT full_name, array_agg(id ORDER BY id) AS ids
            FROM people
            GROUP BY full_name
            HAVING COUNT(*) > 1
            ORDER BY full_name
            """
        )
    )
    return [(row.full_name, list(row.ids)) for row in result]


async def select_survivor(conn: AsyncConnection, ids: list[int]):
    """
    Choose the row to KEEP for a duplicate-Person group (D-06).

    Preference order:
      1. Highest count of linked court_tenures rows.
      2. Among ties, highest count of non-null bio fields (bio_text,
         photo_url, birthdate, first_name, last_name, middle_name, name_suffix).
      3. Only if still tied (genuinely indistinguishable), fall back to the
         lowest id -- documented fallback, never the default.

    Returns (survivor_id, reason, candidates) where candidates is `ids` minus
    the survivor.
    """
    result = await conn.execute(
        text(
            """
            SELECT
                p.id,
                COUNT(DISTINCT ct.id) AS tenure_count,
                (CASE WHEN p.bio_text IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.photo_url IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.birthdate IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.first_name IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.last_name IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.middle_name IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN p.name_suffix IS NOT NULL THEN 1 ELSE 0 END) AS bio_field_count
            FROM people p
            LEFT JOIN court_tenures ct ON ct.person_id = p.id
            WHERE p.id = ANY(:ids)
            GROUP BY p.id
            """
        ),
        {"ids": ids},
    )
    stats = {row.id: (row.tenure_count, row.bio_field_count) for row in result}

    best_id = None
    best_key = None
    for pid in ids:
        tenure_count, bio_count = stats.get(pid, (0, 0))
        # Higher tenure_count wins, then higher bio_count, then lowest id as
        # the last-resort, documented tie-break (D-06).
        key = (tenure_count, bio_count, -pid)
        if best_key is None or key > best_key:
            best_key = key
            best_id = pid

    tenure_count, bio_count = stats.get(best_id, (0, 0))
    if tenure_count > 0:
        reason = f"has {tenure_count} linked court_tenures row(s)"
    elif bio_count > 0:
        reason = f"has {bio_count} non-null bio field(s)"
    else:
        reason = "no distinguishing tenure/bio data on any row in group -- fell back to lowest id"

    candidates = [pid for pid in ids if pid != best_id]
    return best_id, reason, candidates


# ---------------------------------------------------------------------------
# Detection: orphaned / test-fixture Argument rows (D-05)
# ---------------------------------------------------------------------------


async def find_orphaned_arguments(conn: AsyncConnection):
    """
    Broad sweep (D-05): arguments with no linked utterances AND no linked
    pipeline_runs (orphan signal), OR whose linked case_name/docket_number
    matches known test-fixture patterns ("Synthetic..." case names,
    "...TEST..." docket numbers -- see api/tests/*.py fixture conventions).

    Deliberately does NOT match on `job-{id}` source_docket values -- that is
    a legitimate production placeholder for in-progress admin-job arguments
    (pipeline/commands/ingest.py), not test leakage.
    """
    result = await conn.execute(
        text(
            """
            SELECT
                a.id,
                string_agg(DISTINCT c.case_name, ' / ') AS case_names,
                string_agg(DISTINCT c.docket_number, ' / ') AS docket_numbers,
                bool_or(u.id IS NOT NULL) AS has_utterances,
                bool_or(pr.id IS NOT NULL) AS has_pipeline_runs,
                bool_or(c.case_name ILIKE '%synthetic%' OR c.docket_number ILIKE '%test%') AS pattern_match
            FROM arguments a
            LEFT JOIN case_arguments ca ON ca.argument_id = a.id
            LEFT JOIN cases c ON c.id = ca.case_id
            LEFT JOIN utterances u ON u.argument_id = a.id
            LEFT JOIN pipeline_runs pr ON pr.argument_id = a.id
            GROUP BY a.id
            HAVING
                (NOT bool_or(u.id IS NOT NULL) AND NOT bool_or(pr.id IS NOT NULL))
                OR bool_or(c.case_name ILIKE '%synthetic%' OR c.docket_number ILIKE '%test%')
            ORDER BY a.id
            """
        )
    )
    candidates = []
    for row in result:
        is_orphan = not row.has_utterances and not row.has_pipeline_runs
        reasons = []
        if is_orphan:
            reasons.append("orphan: no linked utterances and no linked pipeline_runs")
        if row.pattern_match:
            reasons.append("pattern-matched synthetic case_name/docket_number")
        candidates.append(
            {
                "id": row.id,
                "case_names": row.case_names,
                "docket_numbers": row.docket_numbers,
                "reason": " + ".join(reasons),
            }
        )
    return candidates


async def run_detection(conn: AsyncConnection):
    """Run both detection sweeps and attach survivor selection to each Person group."""
    duplicate_groups = await find_duplicate_person_groups(conn)
    person_report = []
    for full_name, ids in duplicate_groups:
        survivor_id, reason, candidates = await select_survivor(conn, ids)
        person_report.append(
            {
                "full_name": full_name,
                "ids": ids,
                "survivor_id": survivor_id,
                "reason": reason,
                "candidates": candidates,
            }
        )
    orphan_arguments = await find_orphaned_arguments(conn)
    return person_report, orphan_arguments


def _person_candidate_ids(person_report) -> set[int]:
    return {pid for group in person_report for pid in group["candidates"]}


def _argument_candidate_ids(orphan_arguments) -> set[int]:
    return {arg["id"] for arg in orphan_arguments}


# ---------------------------------------------------------------------------
# Reporting (dry-run output)
# ---------------------------------------------------------------------------


def print_report(person_report, orphan_arguments) -> None:
    print("=" * 70)
    print("DUPLICATE PERSON GROUPS")
    print("=" * 70)
    total_person_candidates = 0
    if not person_report:
        print("  (none found)")
    for group in person_report:
        print(f"\nfull_name={group['full_name']!r} ids={group['ids']}")
        print(f"  SURVIVOR: id={group['survivor_id']} ({group['reason']})")
        print(f"  DELETE CANDIDATES: {group['candidates']}")
        total_person_candidates += len(group["candidates"])

    print()
    print("=" * 70)
    print("ORPHANED / TEST-FIXTURE ARGUMENT CANDIDATES")
    print("=" * 70)
    if not orphan_arguments:
        print("  (none found)")
    for arg in orphan_arguments:
        print(
            f"\nargument id={arg['id']} case_name={arg['case_names']!r} "
            f"docket_number={arg['docket_numbers']!r}"
        )
        print(f"  REASON: {arg['reason']}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Duplicate Person groups found: {len(person_report)}")
    print(f"  Person rows marked for deletion: {total_person_candidates}")
    print(f"  Orphaned/test-fixture Argument candidates: {len(orphan_arguments)}")
    print(
        f"  Total rows marked for deletion: {total_person_candidates + len(orphan_arguments)}"
    )


# ---------------------------------------------------------------------------
# Entrypoint (dry-run only in this task -- Task 2 adds the --execute path)
# ---------------------------------------------------------------------------


async def main_async(execute: bool) -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not _db_configured(database_url):
        print(
            "ERROR: DATABASE_URL is not set or matches a placeholder value. "
            "Refusing to run against an unconfigured/misconfigured target.",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = create_async_engine(
        database_url,
        connect_args={"statement_cache_size": 0},  # REQUIRED for PgBouncer -- CLAUDE.md constraint
        pool_size=2,
        echo=False,
    )
    try:
        async with engine.connect() as conn:
            person_report, orphan_arguments = await run_detection(conn)

        print_report(person_report, orphan_arguments)

        if execute:
            print(
                "\n--execute was passed, but the deletion path is not yet implemented "
                "in this build -- ran dry-run only. No rows deleted."
            )
        else:
            print("\nDry-run complete -- no rows deleted. Pass --execute to delete the candidates above.")
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time cleanup of leaked test rows in the shared dev database: "
            "duplicate Person full_name groups and orphaned/test-fixture Argument "
            "rows. Dry-run by default -- pass --execute to actually delete."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Delete the detected candidate rows (default is dry-run: report only, no deletes).",
    )
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    asyncio.run(main_async(execute=args.execute))


if __name__ == "__main__":
    main()
