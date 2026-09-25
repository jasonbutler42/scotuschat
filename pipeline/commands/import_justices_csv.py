"""
Pipeline import-justices command.

Step Zero of Phase 29's historical corpus import: loads the historical
Supreme Court justices tenure CSV and seeds the full bench roster.

- Upgrades the 13 existing `pipeline/commands/seed_aliases.py` Person rows in
  place (`is_justice=True` + `court_tenures` backfill) rather than creating
  duplicates. `role_id` and `speaker_alias` rows tied to those
  13 people are never touched.
- Creates the remaining historical justices with tenure + appointment data.
- Justices appearing in both the CSV's Chief and Associate Justice sections
  (Rehnquist, Rutledge) get both `court_tenures` rows auto-created.
- Idempotent — safe to re-run without creating duplicate people or tenures.

Dedup key (Phase 52, JUSTICE-01/02): `Person.oyez_speaker_id` from the
verified `data/corpus/justice_identity_mapping.csv` mapping, keyed by the
CSV row's normalized name-part tuple. Person-name (`full_name`) equality is
the fallback dedup key, used only for CSV rows with no mapping entry
(currently Amy Coney Barrett and Ketanji Brown Jackson — seated after the
corpus's 2019 cutoff, D-04 of 52-CONTEXT.md). `Person.display_name` is
written from the mapping's corpus display form alongside `oyez_speaker_id`.
No derivation rule is ever used to invent an id for an unmapped row — a
rejected first-initial abbreviation rule was only 88% accurate
(.planning/notes/justice-identity-and-seeding.md).

Usage:
    python -m pipeline import-justices
    python -m pipeline import-justices --csv path/to/justices_tenure.csv
    python -m pipeline import-justices --mapping-csv path/to/mapping.csv
"""

import csv
import unicodedata
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import select

from api.domain.authority import WriteDecision
from api.domain.person_names import prepare_name_provenance, prepare_person_name
from api.models.models import (
    CourtTenure,
    ImportMethod,
    ImportSource,
    OFFICE_ASSOCIATE,
    OFFICE_CHIEF,
    Person,
    ReviewState,
)
from api.services.admin_review import apply_person_value_change
from pipeline.db import get_session

# Phase 39 (D-01 through D-07): CSV "Reason Left" raw cell value -> canonical
# court_tenures.reason_left value (or None for an open tenure / unrecognised
# vocabulary). Verified per-value counts against the real
# data/corpus/supreme_court_justices_sections.csv during planning (39
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

# Matches the data/corpus/ scaffolding created in Plan 01 — the
# operator copies the source CSV here locally; it is gitignored, not tracked.
DEFAULT_CSV_PATH = Path("data/corpus/supreme_court_justices_sections.csv")

# Phase 52 (D-06): the verified justice identity mapping — 114 rows joining
# every corpus j__-prefixed speaker id to its CSV name parts. Same
# gitignored data/corpus/ scaffolding pattern as DEFAULT_CSV_PATH above; a
# hand-verified data artifact, not a tracked source mirror.
DEFAULT_MAPPING_CSV_PATH = Path("data/corpus/justice_identity_mapping.csv")

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

    Delegates to the shared
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
    justice row, matching the exact shape
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


def _normalize_mapping_name_part(value: str | None) -> str:
    """
    Normalize one name-part cell for the mapping-CSV join key
    (JUSTICE-01 / encoding invariant).

    NFC-normalizes and strips whitespace only — no casefold, no accent
    folding, no punctuation rewriting. A missing cell (None) and an empty
    cell ("") both normalize to the same empty string, so a blank middle
    name/suffix compares equal on both sides of the join.
    """
    if value is None:
        return ""
    return unicodedata.normalize("NFC", value).strip()


def _load_justice_mapping(
    mapping_csv_path: Path,
) -> dict[tuple[str, str, str, str], dict[str, str]]:
    """
    Load the verified justice identity mapping CSV into a dict keyed by the
    normalized (first, middle, last, suffix) name-part tuple.

    Raises FileNotFoundError when the file is missing (mirrors the
    DEFAULT_CSV_PATH pre-flight below) and ValueError when it parses to
    zero data rows — an empty mapping must be a hard error, never a silent
    degradation to the legacy full_name dedup key (JUSTICE-01).
    """
    if not mapping_csv_path.exists():
        raise FileNotFoundError(
            f"Justice identity mapping CSV not found: {mapping_csv_path}"
        )

    mapping: dict[tuple[str, str, str, str], dict[str, str]] = {}
    # "utf-8-sig" strips a leading UTF-8 byte-order mark if present and is
    # byte-identical to "utf-8" when there is none — an operator-supplied
    # BOM-prefixed CSV must not silently yield zero mapped rows (JUSTICE-04
    # / encoding).
    with mapping_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                _normalize_mapping_name_part(row.get("first_name")),
                _normalize_mapping_name_part(row.get("middle_name")),
                _normalize_mapping_name_part(row.get("last_name")),
                _normalize_mapping_name_part(row.get("name_suffix")),
            )
            mapping[key] = {
                "oyez_speaker_id": (row.get("oyez_speaker_id") or "").strip(),
                "corpus_display_name": (row.get("corpus_display_name") or "").strip(),
            }

    if not mapping:
        raise ValueError(
            f"Justice identity mapping CSV parsed to zero data rows: "
            f"{mapping_csv_path} — refusing to import with an empty "
            f"mapping (JUSTICE-01: an empty mapping must be a hard error, "
            f"never a silent fallback to full_name-only dedup)."
        )
    return mapping


def _iter_csv_rows(csv_path: Path):
    """
    Yield (office, row_dict) tuples for every justice data row in the CSV.

    The CSV has two sections (Chief Justices, then Associate Justices), each
    introduced by a single-cell section-header line followed by its own
    column-header row. Blank lines between/around sections are skipped.
    """
    current_office = None
    header: list[str] | None = None

    # "utf-8-sig" strips a leading UTF-8 byte-order mark if present, same
    # rationale as _load_justice_mapping above (JUSTICE-04 / encoding).
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
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
    court_tenures rows for justices elevated from Associate to Chief.

    Idempotent — dedups mapped justices by `Person.oyez_speaker_id` (from
    the verified mapping CSV) and unmapped rows by exact `Person.full_name`
    (D-04's fallback branch); tenures dedup by
    (person_id, office, start_date). Safe to re-run any number of times,
    including for the five dual-service justices whose two CSV rows (one
    per office section) resolve to the SAME oyez_speaker_id and so land on
    the same Person row without tripping the partial unique index.

    Args:
        args: argparse.Namespace with an optional `csv` attribute (path to
            the justices tenure CSV; defaults to DEFAULT_CSV_PATH) and an
            optional `mapping_csv` attribute (path to the verified justice
            identity mapping CSV; defaults to DEFAULT_MAPPING_CSV_PATH).
    """
    csv_path = Path(args.csv) if getattr(args, "csv", None) else DEFAULT_CSV_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Justices CSV not found: {csv_path}")

    mapping_csv_path = (
        Path(args.mapping_csv)
        if getattr(args, "mapping_csv", None)
        else DEFAULT_MAPPING_CSV_PATH
    )
    justice_mapping = _load_justice_mapping(mapping_csv_path)

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
            # The row's structured parts, normalized through
            # the same shared helper `reconstruct_full_name` now delegates
            # to — used below for both the brand-new-row assignment and the
            # existing-row blank-only prefill.
            prepared = prepare_person_name(
                first or None, middle or None, last or None, suffix or None
            )
            extraction_metadata = _build_extraction_metadata(full_name)

            # Read here, per-row, before the person
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

            # JUSTICE-01/02: dedup on oyez_speaker_id from the verified
            # mapping when this row's name parts are mapped; fall back to
            # the legacy full_name-equality lookup only for an unmapped row
            # (D-04 — Barrett and Jackson, seated after the corpus's 2019
            # cutoff). Never synthesize an oyez_speaker_id for an unmapped
            # row — no derivation rule, no abbreviation heuristic, no
            # surname match (rejected at 88% accuracy).
            mapping_key = (
                _normalize_mapping_name_part(first),
                _normalize_mapping_name_part(middle),
                _normalize_mapping_name_part(last),
                _normalize_mapping_name_part(suffix),
            )
            mapping_entry = justice_mapping.get(mapping_key)

            if mapping_entry is not None:
                result = await session.execute(
                    select(Person).where(
                        Person.oyez_speaker_id == mapping_entry["oyez_speaker_id"]
                    )
                )
            else:
                result = await session.execute(
                    select(Person).where(Person.full_name == full_name)
                )
            person = result.scalar_one_or_none()

            if person is not None:
                # Upgrade in place — is_justice + tenures only. Never
                # touch role_id, aliases, or speaker_alias rows.
                if not person.is_justice:
                    person.is_justice = True
                    people_upgraded += 1
                # Phase 50 (Task 3, D-21/D-22): each part now routes
                # through the ONE authority gate (apply_person_value_change)
                # instead of a raw blank-only Python assignment.
                # incoming_source="seed" ranks with "corpus" in the ladder
                # (authority_rank rule 3) — the correct rung for this tool.
                # PD-13's gap-fill pre-check means the common case (a
                # currently-blank part) is unchanged in effect: write, no
                # discrepancy recorded. Only a part an operator has
                # genuinely reviewed/edited (review_state carries that, not
                # a bare non-None column value — D-22) newly refuses a
                # disagreeing CSV value instead of relying on "the column
                # happens to be non-None" as an implicit authority signal.
                # A blank incoming part (CSV cell empty) is skipped
                # entirely, same as the former `prepared.X is not None`
                # guard — apply_person_value_change has no D-03 "no
                # opinion" pre-check of its own, so a blank incoming value
                # against a populated existing one must never reach it.
                # Every gate call issues its own execution_options(
                # synchronize_session=False) UPDATE, so the in-memory
                # attribute is synced via a plain assignment on any
                # accepted decision (mirrors import_convokit.py's
                # _apply_extracted_name_provenance) -- a later reader of
                # `person` in this same transaction must see the fresh
                # value, not a stale pre-write one. Four explicit calls
                # (not a loop) so each is independently visible in source.
                if prepared.first_name is not None:
                    decision = await apply_person_value_change(
                        session,
                        person=person,
                        field="first_name",
                        incoming_value=prepared.first_name,
                        incoming_source=ImportSource.SEED.value,
                        incoming_method=ImportMethod.DIRECT.value,
                        import_run_id=None,
                    )
                    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                        setattr(person, "first_name", prepared.first_name)
                if prepared.middle_name is not None:
                    decision = await apply_person_value_change(
                        session,
                        person=person,
                        field="middle_name",
                        incoming_value=prepared.middle_name,
                        incoming_source=ImportSource.SEED.value,
                        incoming_method=ImportMethod.DIRECT.value,
                        import_run_id=None,
                    )
                    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                        setattr(person, "middle_name", prepared.middle_name)
                if prepared.last_name is not None:
                    decision = await apply_person_value_change(
                        session,
                        person=person,
                        field="last_name",
                        incoming_value=prepared.last_name,
                        incoming_source=ImportSource.SEED.value,
                        incoming_method=ImportMethod.DIRECT.value,
                        import_run_id=None,
                    )
                    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                        setattr(person, "last_name", prepared.last_name)
                if prepared.name_suffix is not None:
                    decision = await apply_person_value_change(
                        session,
                        person=person,
                        field="name_suffix",
                        incoming_value=prepared.name_suffix,
                        incoming_source=ImportSource.SEED.value,
                        incoming_method=ImportMethod.DIRECT.value,
                        import_run_id=None,
                    )
                    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                        setattr(person, "name_suffix", prepared.name_suffix)
                # Blank-only prefill for birthdate/death_date,
                # same shape as the name-part prefills above — never overwrite
                # a non-None operator-set value.
                if person.birthdate is None and birthdate is not None:
                    person.birthdate = birthdate
                    people_birthdates_backfilled += 1
                if person.death_date is None and death_date is not None:
                    person.death_date = death_date
                    people_death_dates_backfilled += 1
                # Phase 52 (JUSTICE-02/03): blank-only prefill for
                # oyez_speaker_id — never overwrite an id a prior pass (or
                # the corpus importer) already wrote. display_name is a
                # plain, unconditional assignment rather than a
                # apply_person_value_change ladder call: D-09
                # (52-CONTEXT.md) keeps display_name off PersonUpdate's
                # allow-list, so no operator edit can ever exist for the
                # ladder to arbitrate against — there is no adversary here,
                # so a third write-gating mechanism would protect nothing
                # (RESEARCH.md Pitfall 2). Only runs when this CSV row is
                # mapped; an unmapped row (D-04) leaves both fields
                # untouched.
                if mapping_entry is not None:
                    if person.oyez_speaker_id is None:
                        person.oyez_speaker_id = mapping_entry["oyez_speaker_id"]
                    person.display_name = mapping_entry["corpus_display_name"]
                # Phase 38, carried forward unchanged: every rerun
                # refreshes the extraction provenance envelope, regardless
                # of whether any part was actually blank this time — the
                # reference metadata always reflects the latest extraction
                # pass.
                person.provenance_metadata = extraction_metadata
                # This row is now backed by confident, structured CSV data.
                # This is UNREVIEWED, not a
                # human-only operator review state — only a human action
                # ever produces one; an importer must never mint one.
                # An importer must also never
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
                # A CREATE, not an overwrite — there
                # is no stored value to arbitrate, so this stays deliberately
                # ungated (matching parse.py's participant seeding).
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
                    # Phase 52 (JUSTICE-02/03): both sourced from the
                    # verified mapping; None/None for an unmapped row
                    # (D-04 — Barrett, Jackson).
                    oyez_speaker_id=(
                        mapping_entry["oyez_speaker_id"] if mapping_entry else None
                    ),
                    display_name=(
                        mapping_entry["corpus_display_name"] if mapping_entry else None
                    ),
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
                # The existing-tenure case previously
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
