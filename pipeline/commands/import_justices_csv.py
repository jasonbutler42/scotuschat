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
