"""Audit and atomically normalize court tenure offices.

Dry-run creates an immutable review report. Execution consumes that exact
report, revalidates every original value under row locks, and commits once.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

SCHEMA_VERSION = 1
EXPECTED_REVISION = "0020"
CANONICAL_OFFICES = frozenset({"chief", "associate"})
_NUMBERED_ASSOCIATE = re.compile(r"Associate Justice Seat [1-9][0-9]*")


def _db_configured(url: str) -> bool:
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def classify_office(value: object) -> str | None:
    if value in CANONICAL_OFFICES:
        return str(value)
    if value == "Chief Justice":
        return "chief"
    if value == "Associate Justice" or (
        isinstance(value, str) and _NUMBERED_ASSOCIATE.fullmatch(value)
    ):
        return "associate"
    return None


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def build_report(rows: list[dict], database_identity: str) -> dict:
    audited = []
    for row in sorted(rows, key=lambda item: int(item["id"])):
        original = row["original_office"]
        proposed = classify_office(original)
        audited.append(
            {
                "id": int(row["id"]),
                "original_office": original,
                "classification": proposed or "unresolved",
                "proposed_office": proposed,
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "database_identity": database_identity,
        "expected_revision": EXPECTED_REVISION,
        "rows": audited,
        "unresolved_ids": [row["id"] for row in audited if row["proposed_office"] is None],
    }
    return {**payload, "sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}


def write_report(path: Path, report: dict) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Report already exists; refusing to overwrite: {path}")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_reviewed_report(path: Path, database_identity: str) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Reviewed report does not exist: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Reviewed report must be a JSON object")
    digest = report.get("sha256")
    payload = {key: value for key, value in report.items() if key != "sha256"}
    expected_digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    if not isinstance(digest, str) or not hmac.compare_digest(digest, expected_digest):
        raise ValueError("Reviewed report digest is missing or modified")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Reviewed report schema version is unsupported")
    if report.get("expected_revision") != EXPECTED_REVISION:
        raise ValueError("Reviewed report targets the wrong rename revision")
    if report.get("database_identity") != database_identity:
        raise ValueError("Reviewed report belongs to a different database")
    rows = report.get("rows")
    if not isinstance(rows, list) or [r.get("id") for r in rows] != sorted(r.get("id") for r in rows):
        raise ValueError("Reviewed report rows are malformed or not stably ordered")
    return report


def load_resolutions(path: Path | None, unresolved_ids: list[int]) -> dict[int, str]:
    expected = set(unresolved_ids)
    if not expected:
        if path is None:
            return {}
    elif path is None:
        raise ValueError("Explicit --resolutions JSON is required for unresolved rows")
    raw = json.loads(Path(path).read_text(encoding="utf-8")) if path is not None else {}
    if not isinstance(raw, dict):
        raise ValueError("Resolutions must be a JSON object keyed by tenure id")
    try:
        resolutions = {int(key): value for key, value in raw.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError("Resolution keys must be integer tenure ids") from exc
    if set(resolutions) != expected:
        raise ValueError("Resolutions must exactly match every unresolved id")
    if any(value not in CANONICAL_OFFICES for value in resolutions.values()):
        raise ValueError("Every resolution must be either chief or associate")
    return resolutions


async def _database_identity(conn: AsyncConnection) -> str:
    value = (await conn.execute(text("SELECT current_database()"))).scalar_one()
    return hashlib.sha256(f"postgres-database:{value}".encode()).hexdigest()


async def _read_rows(conn: AsyncConnection, *, lock: bool = False) -> list[dict]:
    suffix = " FOR UPDATE" if lock else ""
    result = await conn.execute(text("SELECT id, office FROM court_tenures ORDER BY id" + suffix))
    return [{"id": row.id, "original_office": row.office} for row in result]


async def run_dry_run(engine: AsyncEngine, report_path: Path) -> dict:
    async with engine.connect() as conn:
        identity = await _database_identity(conn)
        report = build_report(await _read_rows(conn), identity)
    write_report(report_path, report)
    return report


async def run_execute(
    engine: AsyncEngine, report_path: Path, resolutions_path: Path | None = None
) -> int:
    async with engine.begin() as conn:
        identity = await _database_identity(conn)
        report = load_reviewed_report(report_path, identity)
        resolutions = load_resolutions(resolutions_path, report["unresolved_ids"])
        reviewed = {row["id"]: row for row in report["rows"]}
        current_rows = await _read_rows(conn, lock=True)  # SELECT ... FOR UPDATE
        current = {row["id"]: row["original_office"] for row in current_rows}
        missing = sorted(set(reviewed) - set(current))
        added = sorted(set(current) - set(reviewed))
        drift = sorted(
            row_id for row_id in set(reviewed) & set(current)
            if current[row_id] != reviewed[row_id]["original_office"]
        )
        if missing or added or drift:
            raise ValueError(
                f"Reviewed report drift detected (missing={missing}, added={added}, drift={drift})"
            )

        targets = {
            row_id: resolutions.get(row_id, row["proposed_office"])
            for row_id, row in reviewed.items()
        }
        if any(value not in CANONICAL_OFFICES for value in targets.values()):
            raise ValueError("Noncanonical target remains; provide explicit chief/associate resolutions")

        # All originals are compared above before the first UPDATE COURT_TENURES.
        for row_id in sorted(targets):
            await conn.execute(
                text("UPDATE court_tenures SET office = :office WHERE id = :id"),
                {"office": targets[row_id], "id": row_id},
            )

        invalid = (
            await conn.execute(
                text(
                    "SELECT COUNT(*) FROM court_tenures "
                    "WHERE office IS NULL OR office NOT IN ('chief', 'associate')"
                )
            )
        ).scalar_one()
        if invalid:
            raise ValueError(f"Whole-table postcondition failed for {invalid} row(s)")
    return len(targets)


async def main_async(args: argparse.Namespace) -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not _db_configured(database_url):
        raise ValueError("DATABASE_URL is unset or is a placeholder; refusing to run")
    engine = create_async_engine(
        database_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    try:
        if args.execute:
            changed = await run_execute(engine, args.report, args.resolutions)
            print(f"Atomic tenure-office migration completed for {changed} row(s).")
        else:
            report = await run_dry_run(engine, args.report)
            print(
                f"Dry-run report written for {len(report['rows'])} row(s); "
                f"unresolved ids: {report['unresolved_ids']}. No rows changed."
            )
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit and normalize court tenure Office values")
    parser.add_argument("--report", type=Path, required=True, help="Immutable reviewed JSON report")
    parser.add_argument("--execute", action="store_true", help="Execute an existing reviewed report")
    parser.add_argument("--resolutions", type=Path, help="JSON mapping unresolved ids to chief/associate")
    return parser


def main() -> None:
    load_dotenv()
    try:
        asyncio.run(main_async(build_parser().parse_args()))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
