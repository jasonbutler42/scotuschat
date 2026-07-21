"""
Pipeline import-justices command.

Step Zero (D-01) of Phase 29's historical corpus import: loads the historical
Supreme Court justices tenure CSV and seeds the full bench roster.

- Upgrades the 13 existing `pipeline/commands/seed_aliases.py` Person rows in
  place (`is_justice=True` + `court_tenures` backfill) rather than creating
  duplicates (D-02/D-03). `role_id` and `speaker_alias` rows tied to those
  13 people are never touched.
- Creates the remaining historical justices with tenure + appointment data.
- Justices appearing in both the CSV's Chief and Associate Justice sections
  (Rehnquist, Rutledge) get both `court_tenures` rows auto-created (D-04).
- Idempotent — safe to re-run without creating duplicate people or tenures.

Dedup key: exact `Person.full_name` string match (D-02) — same precedent as
`seed_aliases.py`. `Person.oyez_speaker_id` is left NULL here; the later
corpus importer (Plan 05/06) backfills it (D-11).

Usage:
    python -m pipeline import-justices
    python -m pipeline import-justices --csv path/to/justices_tenure.csv
"""

import csv
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import select

from api.models.models import CourtTenure, OFFICE_ASSOCIATE, OFFICE_CHIEF, Person
from pipeline.db import get_session

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Matches the data/corpus/ scaffolding created in Plan 01 (D-20/D-21) — the
# operator copies the source CSV here locally; it is gitignored, not tracked.
DEFAULT_CSV_PATH = Path("data/corpus/supreme_court_justices_sections.csv")

_CHIEF_SECTION_HEADER = "Supreme Court Chief Justices"
_ASSOCIATE_SECTION_HEADER = "Supreme Court Associate Justices"

# Section header text -> the canonical court_tenures.office value used for
# every row in that section (D-01, D-04, D-17 — binary chief/associate, no
# numbered-seat distinctions in the active model).
_SECTION_OFFICE_VALUES = {
    _CHIEF_SECTION_HEADER: OFFICE_CHIEF,
    _ASSOCIATE_SECTION_HEADER: OFFICE_ASSOCIATE,
}

# ---------------------------------------------------------------------------
# Manual overrides (Pitfall 1 guard)
#
# Every one of the 13 existing seed_aliases.py justices reconstructs
# byte-identically via reconstruct_full_name() below (verified directly
# against the real justices CSV rows during planning/execution). This
# mapping is kept — empty — as the explicit, documented escape hatch: any
# future justice name that fails to reconstruct correctly must be added
# here rather than silently mismatching (a mismatch means a duplicate
# Person row at dedup time, per D-02/D-03).
#
# Keyed by the raw (first, middle, last, suffix) CSV parts.
# ---------------------------------------------------------------------------
MANUAL_NAME_OVERRIDES: dict[tuple[str, str, str, str], str] = {}


def reconstruct_full_name(first: str, middle: str, last: str, suffix: str) -> str:
    """
    Reconstruct a Person.full_name string from CSV-shaped name parts.

    Rule (derived empirically by reconciling all 13 existing seed_aliases.py
    literals against the real justices tenure CSV data — see 29-RESEARCH.md
    Pitfall 1 / Open Question 1): plain concatenation —
    "{first} {middle} {last}" (middle omitted entirely, no extra space, when
    blank), followed by ", {suffix}" only when a suffix is present.

    The CSV's "Middle Name or Initial" column already embeds the trailing
    period for single-initial values (e.g. "G.", "M.", "A.", "H."), so no
    punctuation synthesis is needed here — this is intentionally a plain
    string join, not a name-formatting heuristic.

    Any CSV name that does not reconstruct correctly under this rule must be
    added to MANUAL_NAME_OVERRIDES rather than allowed to silently mismatch.
    """
    override_key = (first, middle, last, suffix)
    if override_key in MANUAL_NAME_OVERRIDES:
        return MANUAL_NAME_OVERRIDES[override_key]

    parts = [first]
    if middle:
        parts.append(middle)
    parts.append(last)
    full_name = " ".join(parts)
    if suffix:
        full_name = f"{full_name}, {suffix}"
    return full_name


def _parse_optional_date(value: str):
    """Parse a CSV date cell; blank/whitespace-only values return None."""
    value = value.strip()
    if not value:
        return None
    return dateutil_parser.parse(value).date()


def _iter_csv_rows(csv_path: Path):
    """
    Yield (office, row_dict) tuples for every justice data row in the CSV.

    The CSV has two sections (Chief Justices, then Associate Justices), each
    introduced by a single-cell section-header line followed by its own
    column-header row. Blank lines between/around sections are skipped.
    """
    current_office = None
    header: list[str] | None = None

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for raw_row in reader:
            if not raw_row or not any(cell.strip() for cell in raw_row):
                continue  # blank line

            first_cell = raw_row[0].strip()
            if first_cell in _SECTION_OFFICE_VALUES:
                current_office = _SECTION_OFFICE_VALUES[first_cell]
                header = None  # next non-blank row is this section's column header
                continue

            if header is None:
                header = raw_row
                continue

            row_dict = dict(zip(header, raw_row))
            yield current_office, row_dict


async def run_import_justices_csv(args) -> None:
    """
    Import the historical justices tenure CSV.

    Upgrades the 13 existing seed_aliases.py Person rows in place
    (is_justice=True + court_tenures backfill, D-03), creates the remaining
    justices with tenure + appointment data, and auto-creates both
    court_tenures rows for justices elevated from Associate to Chief (D-04).

    Idempotent — dedups people by exact Person.full_name (D-02) and tenures
    by (person_id, office, start_date); safe to re-run any number of times.

    Args:
        args: argparse.Namespace with an optional `csv` attribute (path to
            the justices tenure CSV; defaults to DEFAULT_CSV_PATH).
    """
    csv_path = Path(args.csv) if getattr(args, "csv", None) else DEFAULT_CSV_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Justices CSV not found: {csv_path}")

    people_created = 0
    people_upgraded = 0
    tenures_created = 0
    rows_skipped = 0

    async with get_session() as session:
        for office, row in _iter_csv_rows(csv_path):
            first = row.get("First Name", "").strip()
            middle = row.get("Middle Name or Initial", "").strip()
            last = row.get("Last Name", "").strip()
            suffix = row.get("Suffix", "").strip()

            if not first or not last:
                rows_skipped += 1
                continue

            full_name = reconstruct_full_name(first, middle, last, suffix)

            result = await session.execute(
                select(Person).where(Person.full_name == full_name)
            )
            person = result.scalar_one_or_none()

            if person is not None:
                # D-03: upgrade in place — is_justice + tenures only. Never
                # touch role_id, aliases, or speaker_alias rows.
                if not person.is_justice:
                    person.is_justice = True
                    people_upgraded += 1
            else:
                person = Person(
                    full_name=full_name,
                    first_name=first or None,
                    middle_name=middle or None,
                    last_name=last or None,
                    name_suffix=suffix or None,
                    is_justice=True,
                    # oyez_speaker_id intentionally left NULL — the corpus
                    # importer backfills it later (D-11).
                )
                session.add(person)
                await session.flush()
                people_created += 1

            start_date = _parse_optional_date(row.get("Judicial Oath Taken", ""))
            end_date = _parse_optional_date(row.get("Date Service Terminated", ""))
            appointed_by = row.get("Appointed by", "").strip() or None
            appointing_party = row.get("Party", "").strip() or None

            tenure_result = await session.execute(
                select(CourtTenure).where(
                    CourtTenure.person_id == person.id,
                    CourtTenure.office == office,
                    CourtTenure.start_date == start_date,
                )
            )
            existing_tenure = tenure_result.scalar_one_or_none()

            if existing_tenure is None:
                tenure = CourtTenure(
                    person_id=person.id,
                    office=office,
                    start_date=start_date,
                    end_date=end_date,
                    appointed_by=appointed_by,
                    appointing_president_party=appointing_party,
                )
                session.add(tenure)
                await session.flush()
                tenures_created += 1

    print(
        f"Done — {people_created} people created, {people_upgraded} people "
        f"upgraded to is_justice=True, {tenures_created} court_tenures "
        f"created ({rows_skipped} rows skipped)."
    )
