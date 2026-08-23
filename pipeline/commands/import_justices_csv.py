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

from api.domain.person_names import prepare_name_provenance, prepare_person_name
from api.models.models import (
    CourtTenure,
    OFFICE_ASSOCIATE,
    OFFICE_CHIEF,
    Person,
    ReviewState,
)
from pipeline.db import get_session

# Phase 39 (D-01 through D-07): CSV "Reason Left" raw cell value -> canonical
# court_tenures.reason_left value (or None for an open tenure / unrecognised
# vocabulary). Verified per-value counts against the real
# data/corpus/supreme_court_justices_sections.csv during planning (39-02-PLAN.md
# <verified_csv_facts>, re-censused with this file's own _iter_csv_rows()
# section/header logic, not a naive line-based scan):
#
#   Reason Left value            | chief | associate | total
#   ------------------------------|-------|-----------|------
#   Retired                      |     7 |        51 |    58
#   Died                         |     9 |        42 |    51
#   Still in Office              |     1 |         8 |     9
#   Promoted to Chief Justice    |     0 |         3 |     3
#   (blank)                      |     0 |         0 |     0
#
# 121 data rows total. There are zero blank Reason Left cells in the real
# file today — the "" entry below is a defensive default, not a case the
# current file exercises. "Still in Office" maps to None (D-02: an open
# tenure never carries a reason), not to a stored value.
_REASON_LEFT_CSV_MAP: dict[str, str | None] = {
    "Died": "died",
    "Retired": "retired",
    "Promoted to Chief Justice": "promoted",
    "Still in Office": None,
    "": None,
}

# Phase 38 (D-14-D-18), carried forward unchanged by Phase 49 D-08: every
# Person row this command creates or upgrades gets a
# Person.provenance_metadata envelope stamped with this source tag,
# matching the shape alembic/versions/0022_person_name_authority.py already
# established: {source, raw, confidence, reason, auto_applied}.
_EXTRACTION_SOURCE = "import_justices_csv"

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

    Phase 38 (D-03/D-05): delegates to the shared
    `api.domain.person_names.prepare_person_name` derivation rule instead of
    an independent local join — "{first} {middle} {last}" (middle omitted
    entirely, no extra space, when blank), followed by ", {suffix}" only
    when a suffix is present. This reproduces the exact same string every
    one of the 13 existing seed_aliases.py literals already used (see
    29-RESEARCH.md Pitfall 1 / Open Question 1) because
    `api.domain.person_names.format_full_name` implements the identical
    join rule; the CSV's "Middle Name or Initial" column already embeds the
    trailing period for single-initial values (e.g. "G.", "M.", "A.", "H."),
    so no additional punctuation synthesis happens here.

    Any CSV name that does not reconstruct correctly under this rule must be
    added to MANUAL_NAME_OVERRIDES rather than allowed to silently mismatch.
    """
    override_key = (first, middle, last, suffix)
    if override_key in MANUAL_NAME_OVERRIDES:
        return MANUAL_NAME_OVERRIDES[override_key]

    prepared = prepare_person_name(first or None, middle or None, last or None, suffix or None)
    return prepared.full_name


def _build_extraction_metadata(full_name: str) -> dict:
    """
    Build a `Person.provenance_metadata` envelope for a CSV-derived
    justice row (D-14, D-18), matching the exact shape
    alembic/versions/0022_person_name_authority.py's legacy backfill already
    persists — {source, raw, confidence, reason, auto_applied} — so both the
    migration and this import path write one consistent, mergeable audit
    trail. `value` is intentionally validated as None here (whole-record
    envelope, not a per-part value — see api/schemas/admin_people.py's
    PersonProvenanceMetadata docstring); `raw` is the exact reconstructed
    full_name text CSV columns produced. Every CSV row is structured,
    per-column ground truth (not an inferred split), so confidence is always
    "High" and auto_applied is always True.
    """
    provenance = prepare_name_provenance(None, full_name, "high")
    return {
        "source": _EXTRACTION_SOURCE,
        "raw": provenance.raw,
        "confidence": provenance.confidence,
        "reason": "structured CSV columns (First/Middle/Last/Suffix)",
        "auto_applied": True,
    }


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
    people_birthdates_backfilled = 0
    people_death_dates_backfilled = 0
    tenure_reasons_backfilled = 0
    reasons_unmatched = 0
    unmatched_reason_values: set[str] = set()

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
            # Phase 38 (D-03): the row's structured parts, normalized through
            # the same shared helper `reconstruct_full_name` now delegates
            # to — used below for both the brand-new-row assignment and the
            # existing-row blank-only prefill.
            prepared = prepare_person_name(
                first or None, middle or None, last or None, suffix or None
            )
            extraction_metadata = _build_extraction_metadata(full_name)

            # Phase 39 (D-04/D-05): read here, per-row, before the person
            # branch runs — birthdate is consumed by both the upgrade and
            # create branches below.
            birthdate = _parse_optional_date(row.get("Birthdate", ""))
            death_date = _parse_optional_date(row.get("Death Date", ""))
            reason_left_raw = row.get("Reason Left", "").strip()
            # Explicit membership check, not `.get()` — a recognised value
            # that maps to None ("Still in Office", D-02) must stay
            # distinguishable from a value nobody has ever seen. `.get()`
            # would silently collapse both to None.
            if reason_left_raw in _REASON_LEFT_CSV_MAP:
                resolved_reason_left = _REASON_LEFT_CSV_MAP[reason_left_raw]
            else:
                resolved_reason_left = None
                reasons_unmatched += 1
                unmatched_reason_values.add(reason_left_raw)

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
                # Phase 38 (D-16/T-38-11): blank-only prefill — never
                # overwrite a part an operator has already saved. Each part
                # is checked independently so a partially-completed row
                # (e.g. an operator-added middle initial) still gets its
                # remaining blank parts filled from this authoritative CSV
                # row.
                if person.first_name is None and prepared.first_name is not None:
                    person.first_name = prepared.first_name
                if person.middle_name is None and prepared.middle_name is not None:
                    person.middle_name = prepared.middle_name
                if person.last_name is None and prepared.last_name is not None:
                    person.last_name = prepared.last_name
                if person.name_suffix is None and prepared.name_suffix is not None:
                    person.name_suffix = prepared.name_suffix
                # Phase 39 (D-06): blank-only prefill for birthdate/death_date,
                # same shape as the name-part prefills above — never overwrite
                # a non-None operator-set value.
                if person.birthdate is None and birthdate is not None:
                    person.birthdate = birthdate
                    people_birthdates_backfilled += 1
                if person.death_date is None and death_date is not None:
                    person.death_date = death_date
                    people_death_dates_backfilled += 1
                # Phase 38 (D-17), carried forward unchanged: every rerun
                # refreshes the extraction provenance envelope, regardless
                # of whether any part was actually blank this time — the
                # reference metadata always reflects the latest extraction
                # pass.
                person.provenance_metadata = extraction_metadata
                # This row is now backed by confident, structured CSV data.
                # Phase 49 (D-08, D-11, D-24): this is UNREVIEWED, not a
                # human-only operator review state — only a human action
                # ever produces one; an importer must never mint one.
                # CR-03 fix (49-REVIEW.md): an importer must also never
                # ERASE a human-only review state. Every other field this
                # branch touches is a blank-only prefill (never overwrite a
                # part an operator has already saved) — mirroring
                # pipeline/commands/import_convokit.py's
                # _apply_extracted_name_provenance, which returns before
                # touching review_state whenever the person already carries
                # any saved data. review_state was the one exception here,
                # unconditionally resetting to UNREVIEWED on every rerun and
                # silently discarding OPERATOR_CONFIRMED/OPERATOR_EDITED.
                # Guard it the same way: only set UNREVIEWED when the row
                # does not already carry an operator-authored state.
                if person.review_state not in (
                    ReviewState.OPERATOR_CONFIRMED,
                    ReviewState.OPERATOR_EDITED,
                ):
                    person.review_state = ReviewState.UNREVIEWED
            else:
                person = Person(
                    full_name=full_name,
                    first_name=prepared.first_name,
                    middle_name=prepared.middle_name,
                    last_name=prepared.last_name,
                    name_suffix=prepared.name_suffix,
                    is_justice=True,
                    birthdate=birthdate,
                    death_date=death_date,
                    provenance_metadata=extraction_metadata,
                    review_state=ReviewState.UNREVIEWED,
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
                    reason_left=resolved_reason_left,
                )
                session.add(tenure)
                await session.flush()
                tenures_created += 1
            else:
                # Phase 39 (D-06): the existing-tenure case previously
                # silently no-op'd on every field. This is the one write it
                # now performs, blank-only: fill reason_left only when the
                # stored value is currently None and the resolved CSV value
                # is not None. end_date/appointed_by/appointing_president_party
                # are intentionally left untouched here — out of this
                # phase's scope (Phase 29/27 behaviour for those fields is
                # unchanged).
                if (
                    existing_tenure.reason_left is None
                    and resolved_reason_left is not None
                ):
                    existing_tenure.reason_left = resolved_reason_left
                    tenure_reasons_backfilled += 1

    unmatched_summary = ""
    if reasons_unmatched:
        unmatched_summary = (
            f"\n{reasons_unmatched} unrecognised Reason Left value(s) found "
            f"(stored as NULL): {sorted(unmatched_reason_values)}"
        )

    print(
        f"Done — {people_created} people created, {people_upgraded} people "
        f"upgraded to is_justice=True, {tenures_created} court_tenures "
        f"created ({rows_skipped} rows skipped). Backfilled "
        f"{people_birthdates_backfilled} birthdate(s), "
        f"{people_death_dates_backfilled} death date(s), "
        f"{tenure_reasons_backfilled} tenure reason(s)."
        f"{unmatched_summary}"
    )
