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
    python scripts/cleanup_leaked_test_rows.py --execute      # deletes, with confirmation prompt
    python scripts/cleanup_leaked_test_rows.py --execute --yes  # deletes, no prompt

Dry-run is the default (D-04) -- no flag means report-only, zero DELETEs.
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

Whole-table wipe statements and schema-removal statements are never used
here. This script only DELETEs/UPDATEs specific identified candidate rows,
always inside a single transaction that commits only after every delete
succeeds (T-31-02).

HARD SAFETY GUARDS:
  - Connects to DATABASE_URL (the shared dev DB), NOT TEST_DATABASE_URL --
    this is deliberate; the leaked rows live in the dev DB, not the test DB.
  - Refuses to run if DATABASE_URL is unset or matches the same placeholder
    guard used throughout api/tests/conftest.py (T-31-10).
  - The --execute path re-runs detection immediately before deleting and
    aborts if the candidate set has changed since the dry-run report was
    printed, so it never deletes a stale set (T-31-02).
  - Deleting a non-survivor Person row reassigns its dependent rows
    (court_tenures, case_appearances, argument_participants, utterances,
    speaker_alias) to the survivor first -- it never cascade-destroys real
    dependent data (T-31-11).

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
# Deletion (D-04, D-08) -- only runs behind --execute
# ---------------------------------------------------------------------------

# Tables with a person_id FK that must be reassigned to the survivor before a
# non-survivor Person row can be deleted (T-31-11) -- never cascade-destroy
# real dependent data.
_PERSON_DEPENDENT_TABLES = (
    ("court_tenures", "person_id"),
    ("case_appearances", "person_id"),
    ("argument_participants", "person_id"),
    ("utterances", "person_id"),
    ("speaker_alias", "person_id"),
)


async def _delete_person_candidates(conn: AsyncConnection, person_report) -> None:
    for group in person_report:
        candidates = group["candidates"]
        if not candidates:
            continue
        survivor_id = group["survivor_id"]
        for table, column in _PERSON_DEPENDENT_TABLES:
            await conn.execute(
                text(f"UPDATE {table} SET {column} = :survivor WHERE {column} = ANY(:ids)"),
                {"survivor": survivor_id, "ids": candidates},
            )
        await conn.execute(
            text("DELETE FROM people WHERE id = ANY(:ids)"),
            {"ids": candidates},
        )
        print(f"Deleted Person ids {candidates} (dependents reassigned to survivor {survivor_id}).")


async def _delete_orphan_arguments(conn: AsyncConnection, orphan_arguments) -> None:
    # FK-ordered cascade mirroring api/services/admin_arguments.py::delete_argument,
    # plus argument_status_log (that function's cascade omits it -- out of scope
    # for this script to fix; logged in deferred-items.md).
    for arg in orphan_arguments:
        argument_id = arg["id"]

        case_ids_result = await conn.execute(
            text("SELECT case_id FROM case_arguments WHERE argument_id = :aid"),
            {"aid": argument_id},
        )
        linked_case_ids = [row.case_id for row in case_ids_result]

        await conn.execute(
            text("DELETE FROM utterances WHERE argument_id = :aid"), {"aid": argument_id}
        )
        await conn.execute(
            text("DELETE FROM pipeline_runs WHERE argument_id = :aid"), {"aid": argument_id}
        )
        await conn.execute(
            text("DELETE FROM argument_participants WHERE argument_id = :aid"),
            {"aid": argument_id},
        )
        await conn.execute(
            text("DELETE FROM argument_status_log WHERE argument_id = :aid"),
            {"aid": argument_id},
        )
        await conn.execute(
            text("DELETE FROM case_arguments WHERE argument_id = :aid"), {"aid": argument_id}
        )
        await conn.execute(
            text("UPDATE admin_jobs SET argument_id = NULL WHERE argument_id = :aid"),
            {"aid": argument_id},
        )
        await conn.execute(text("DELETE FROM arguments WHERE id = :aid"), {"aid": argument_id})

        # Clean up Case rows that are now orphaned as a direct result of this
        # deletion -- only if no other argument still links to them.
        for case_id in linked_case_ids:
            remaining = await conn.execute(
                text("SELECT COUNT(*) FROM case_arguments WHERE case_id = :cid"),
                {"cid": case_id},
            )
            if remaining.scalar_one() == 0:
                await conn.execute(text("DELETE FROM cases WHERE id = :cid"), {"cid": case_id})

        print(f"Deleted Argument id {argument_id} ({arg['reason']}).")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main_async(execute: bool, yes: bool) -> None:
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

        if not execute:
            print("\nDry-run complete -- no rows deleted. Pass --execute to delete the candidates above.")
            return

        total_candidates = len(_person_candidate_ids(person_report)) + len(orphan_arguments)
        if total_candidates == 0:
            print("\nNo deletion candidates found -- nothing to do.")
            return

        if not yes:
            confirm = input(
                f"\nType the exact number of total rows to delete ({total_candidates}) "
                "to proceed, or anything else to abort: "
            )
            if confirm.strip() != str(total_candidates):
                print("Confirmation did not match -- aborting. No rows deleted.")
                return

        expected_person_ids = _person_candidate_ids(person_report)
        expected_argument_ids = _argument_candidate_ids(orphan_arguments)

        async with engine.begin() as conn:
            # Re-run detection inside the transaction so the execute path
            # deletes exactly the candidates just reported -- never a stale set.
            fresh_person_report, fresh_orphan_arguments = await run_detection(conn)
            if (
                _person_candidate_ids(fresh_person_report) != expected_person_ids
                or _argument_candidate_ids(fresh_orphan_arguments) != expected_argument_ids
            ):
                print(
                    "\nABORTING: the candidate set changed between the dry-run report and "
                    "the execute pass -- refusing to delete a stale set. Re-run the script "
                    "to review the current candidates.",
                    file=sys.stderr,
                )
                sys.exit(1)

            await _delete_person_candidates(conn, fresh_person_report)
            await _delete_orphan_arguments(conn, fresh_orphan_arguments)
            # Transaction commits automatically on successful exit from
            # `engine.begin()` -- only after every delete above has succeeded.

        async with engine.connect() as conn:
            people_count = (await conn.execute(text("SELECT COUNT(*) FROM people"))).scalar_one()
            arguments_count = (
                await conn.execute(text("SELECT COUNT(*) FROM arguments"))
            ).scalar_one()

        print(f"\nDeletion committed. Final counts -- people: {people_count}, arguments: {arguments_count}.")
        print(
            "Compare against the pre-cleanup baseline noted in 31-CONTEXT.md "
            "(352 people, 211 arguments)."
        )
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
    parser.add_argument(
        "--yes",
        "--force",
        dest="yes",
        action="store_true",
        help="Skip the interactive confirmation prompt when used with --execute.",
    )
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    asyncio.run(main_async(execute=args.execute, yes=args.yes))


if __name__ == "__main__":
    main()
