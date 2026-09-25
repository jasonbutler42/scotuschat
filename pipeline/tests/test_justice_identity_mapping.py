"""
Permanent regression tests for data/corpus/justice_identity_mapping.csv
(Phase 52, D-02/D-03/D-05/D-06/D-07/D-08).

This is a CHECK on a hand-verified artifact, not a derivation rule. The
mapping CSV is produced once (by hand-verifying every row, with operator
confirmation of the 7 rows a mechanical middle-initial-abbreviation rule
cannot explain) and then pinned here so a future accidental edit — a
typo'd oyez_speaker_id, a dropped row, a re-introduced confidence column —
fails loudly. The structural assertion below reuses the SAME
middle-initial-abbreviation logic that
`.planning/notes/justice-identity-and-seeding.md` measured at 88%
accuracy (100 of 114) and explicitly rejected AS A SOURCE OF TRUTH for
generating oyez_speaker_id/display_name values. Reusing it here as a
verifier of an already-hand-verified artifact does not revive it as a
generator — if a future row fails this check, the correct fix is to
correct the row by hand (or add it to the named exception set below with
a reason), never to relax or repurpose this assertion to produce a value.

DB-independent: every test here reads only local CSV/JSON files, no
DATABASE_URL required. The whole module skips (naming the missing path)
when the gitignored corpus inputs are absent — an all-skipped run means
coverage was NOT verified, not "passed vacuously."
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths (repo-root-relative, matching pipeline/commands/import_justices_csv.py's
# own DEFAULT_CSV_PATH / DEFAULT_MAPPING_CSV_PATH convention)
# ---------------------------------------------------------------------------

SPEAKERS_JSON_PATH = Path("data/corpus/speakers.json")
SOURCE_CSV_PATH = Path("data/corpus/supreme_court_justices_sections.csv")
MAPPING_CSV_PATH = Path("data/corpus/justice_identity_mapping.csv")

_REQUIRED_PATHS = [SPEAKERS_JSON_PATH, SOURCE_CSV_PATH, MAPPING_CSV_PATH]
_MISSING_PATHS = [str(p) for p in _REQUIRED_PATHS if not p.exists()]

# Module-wide skip (behavior 6): a skip is a report that coverage was NOT
# verified — every test in this module carries this marker rather than
# each test separately guessing at file presence.
pytestmark = pytest.mark.skipif(
    bool(_MISSING_PATHS),
    reason=(
        "Missing required gitignored corpus/mapping file(s) — coverage NOT "
        f"verified: {', '.join(_MISSING_PATHS)}"
    ),
)

_EXPECTED_HEADER = [
    "oyez_speaker_id",
    "corpus_display_name",
    "first_name",
    "middle_name",
    "last_name",
    "name_suffix",
]

_EXPECTED_ROW_COUNT = 114

# D-02 (52-CONTEXT.md, confirmed 2026-09-24): the 7 rows the mechanical
# middle-initial-abbreviation check cannot explain, presented to the
# operator individually and confirmed correct. NOT a full 114-row manual
# read — an explicit, named allow-list so the structural test in
# test_corpus_display_name_reconstructs_from_name_parts stays strict for
# the other 107 rows rather than being loosened for all 114.
_D02_STRUCTURAL_EXCEPTIONS: dict[str, str] = {
    "j__harold_burton": "corpus form (Harold Burton) drops the middle name entirely",
    "j__lucius_qc_lamar": "corpus form (Lucius Q.C. Lamar) uses two-letter punctuation, not a single initial",
    "j__neil_gorsuch": "corpus form (Neil Gorsuch) drops the middle name entirely",
    "j__noah_swayne": "corpus form (Noah Swayne) drops the middle name entirely",
    "j__oliver_w_holmes_jr": "D-05 suffix disagreement — see test_holmes_is_the_only_suffix_disagreement",
    "j__rufus_peckham": "corpus form (Rufus Peckham) drops the middle name entirely",
    "j__stanley_reed": "corpus form (Stanley Reed) drops the middle name entirely",
}

# D-01 (52-CONTEXT.md): resolved by the CSV's own tenure dates, not by the
# D-02 mechanical-check-plus-operator-spot-check process, so kept as its
# own named exception rather than folded into the D-02 constant above.
# Henry Brockholst Livingston's corpus form prepends "Henry" — a token
# absent from every mapping name-part column (the CSV files him under the
# first name "Brockholst").
_D01_LIVINGSTON_ID = "j__brockholst_livingston"

_HOLMES_ID = "j__oliver_w_holmes_jr"

_ROMAN_NUMERAL_SUFFIXES = {"II", "III", "IV"}

_PUNCT_RE = re.compile(r"[^a-z0-9]")
_TRAILING_DIGIT_RE = re.compile(r"\d+$")
_SUFFIX_WORD_TOKENS = {"jr", "sr", "ii", "iii", "iv"}


# ---------------------------------------------------------------------------
# Fixtures — module-scoped, pure file reads (mirrors
# pipeline/tests/test_import_justices_csv.py's own CSV-fixture conventions,
# no DB session needed anywhere in this module)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mapping_rows() -> list[dict[str, str]]:
    with MAPPING_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def mapping_header() -> list[str]:
    with MAPPING_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


@pytest.fixture(scope="module")
def speakers_j_ids() -> set[str]:
    """The set of j__-prefixed (justice) speaker ids in speakers.json."""
    data = json.loads(SPEAKERS_JSON_PATH.read_text(encoding="utf-8"))
    return {k for k in data if k.startswith("j__")}


@pytest.fixture(scope="module")
def source_csv_name_part_rows() -> set[tuple[str, str, str, str]]:
    """
    Every (First Name, Middle Name or Initial, Last Name, Suffix) tuple
    present as an actual row in the two-section source CSV — mirrors
    pipeline/commands/import_justices_csv.py::_iter_csv_rows' section/
    header handling exactly, so this test reads the same rows the importer
    does, not a re-derived subset.
    """
    chief_header = "Supreme Court Chief Justices"
    associate_header = "Supreme Court Associate Justices"
    section_headers = {chief_header, associate_header}

    rows: set[tuple[str, str, str, str]] = set()
    header: list[str] | None = None
    with SOURCE_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        for raw_row in csv.reader(f):
            if not raw_row or not any(cell.strip() for cell in raw_row):
                continue
            first_cell = raw_row[0].strip()
            if first_cell in section_headers:
                header = None
                continue
            if header is None:
                header = raw_row
                continue
            row_dict = dict(zip(header, raw_row))
            rows.add(
                (
                    row_dict.get("First Name", "").strip(),
                    row_dict.get("Middle Name or Initial", "").strip(),
                    row_dict.get("Last Name", "").strip(),
                    row_dict.get("Suffix", "").strip(),
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    """NFKD-fold accents away, drop all non-alnum, lowercase. Used only for
    the id-slug structural comparison, which is inherently punctuation-free
    (oyez ids are already ascii_lowercase+underscore)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _PUNCT_RE.sub("", s.lower())


def _join_name(first: str, middle: str, last: str, suffix: str) -> str:
    """
    Canonical `First Middle Last[, Suffix]` join — same shape as
    api.domain.person_names.format_full_name, with ONE deliberate
    deviation this module's own corpus-form data requires: a roman-numeral
    suffix (II/III/IV) is joined with a space, not a comma (the corpus's
    own convention for "John M. Harlan II" — no comma — differs from
    format_full_name's "Jr."-style comma join, which the corpus DOES use
    for "John G. Roberts, Jr."). Duplicated here (not imported) because
    this is a fixture of THIS test module's own two candidate
    reconstructions, not a production code path.
    """
    parts = [p for p in (first, middle, last) if p]
    full = " ".join(parts)
    if suffix:
        if suffix in _ROMAN_NUMERAL_SUFFIXES:
            full = f"{full} {suffix}"
        else:
            full = f"{full}, {suffix}"
    return full


# ---------------------------------------------------------------------------
# Behavior 1 (D-03): coverage, both directions
# ---------------------------------------------------------------------------


def test_coverage_matches_speakers_json_exactly(mapping_rows, speakers_j_ids):
    """
    The set of j__-prefixed ids in speakers.json equals the set of
    oyez_speaker_id values in the mapping — both directions, reporting the
    offending ids (not just a count) on failure.
    """
    mapping_ids = {row["oyez_speaker_id"] for row in mapping_rows}

    missing_from_mapping = speakers_j_ids - mapping_ids
    extra_in_mapping = mapping_ids - speakers_j_ids

    assert not missing_from_mapping, (
        f"{len(missing_from_mapping)} speaker(s) in speakers.json have no "
        f"mapping row: {sorted(missing_from_mapping)}"
    )
    assert not extra_in_mapping, (
        f"{len(extra_in_mapping)} mapping row(s) point at a non-existent "
        f"speaker: {sorted(extra_in_mapping)}"
    )


# ---------------------------------------------------------------------------
# Behavior 2 (D-02): structural agreement
# ---------------------------------------------------------------------------


def test_oyez_speaker_id_agrees_with_first_and_last_name(mapping_rows):
    """
    For every mapping row, the oyez_speaker_id slug's leading token
    matches first_name (or its first initial) and its trailing token
    matches last_name, case-insensitively, after stripping the j__ prefix,
    any trailing disambiguation digit (the "2" in john_m_harlan2), a
    trailing suffix WORD token (jr/sr/ii/iii/iv — e.g. the "jr" in
    samuel_a_alito_jr), and comparing against only the LAST whitespace
    word of a multi-word last_name (e.g. "devanter" in
    willis_van_devanter matches the last word of "Van Devanter").

    No exceptions — this holds for all 114 rows, including the 7 D-02
    rows and the D-01 Livingston row, which only disagree on the SEPARATE
    corpus_display_name reconstruction checked below.
    """
    failures = []
    for row in mapping_rows:
        oid = row["oyez_speaker_id"]
        assert oid.startswith("j__"), f"{oid} does not start with j__"
        tokens = oid[3:].split("_")

        first_tok = tokens[0]
        first_name = _norm(row["first_name"])
        first_ok = first_tok == first_name or (
            len(first_tok) == 1 and first_name.startswith(first_tok)
        )

        last_tok = _TRAILING_DIGIT_RE.sub("", tokens[-1])
        if last_tok in _SUFFIX_WORD_TOKENS and len(tokens) >= 2:
            last_tok = tokens[-2]
        last_words = row["last_name"].strip().split()
        last_name_last_word = _norm(last_words[-1]) if last_words else ""
        last_ok = last_tok == last_name_last_word

        if not (first_ok and last_ok):
            failures.append(
                f"{oid}: first_tok={tokens[0]!r} vs first_name={row['first_name']!r}, "
                f"last_tok={tokens[-1]!r} vs last_name={row['last_name']!r}"
            )

    assert not failures, "Structural id/name mismatch:\n" + "\n".join(failures)


def test_corpus_display_name_reconstructs_from_name_parts(mapping_rows):
    """
    For every mapping row NOT in the named exception sets above,
    corpus_display_name equals EITHER the full "First Middle Last[,
    Suffix]" join OR the middle-initial-abbreviated "First M. Last[,
    Suffix]" join of the row's own first/middle/last/suffix columns — the
    same rule .planning/notes/justice-identity-and-seeding.md measured at
    88% accuracy (100/114) and rejected AS A GENERATOR. Reused here only
    as a verifier of the hand-verified artifact (D-02); a future failure
    here means correct the row by hand, never relax this assertion.
    """
    exceptions = set(_D02_STRUCTURAL_EXCEPTIONS) | {_D01_LIVINGSTON_ID}

    failures = []
    for row in mapping_rows:
        oid = row["oyez_speaker_id"]
        if oid in exceptions:
            continue

        first = row["first_name"].strip()
        middle = row["middle_name"].strip()
        last = row["last_name"].strip()
        suffix = row["name_suffix"].strip()
        corpus = row["corpus_display_name"].strip()

        full_form = _join_name(first, middle, last, suffix)
        abbrev_middle = f"{middle[0]}." if middle else ""
        abbrev_form = _join_name(first, abbrev_middle, last, suffix)

        if corpus not in (full_form, abbrev_form):
            failures.append(
                f"{oid}: corpus_display_name={corpus!r} matches neither the "
                f"full form {full_form!r} nor the abbreviated form {abbrev_form!r}"
            )

    assert not failures, (
        "corpus_display_name does not reconstruct from name parts for:\n"
        + "\n".join(failures)
    )


def test_name_parts_correspond_to_source_csv_rows(mapping_rows, source_csv_name_part_rows):
    """
    Every mapping row's (first_name, middle_name, last_name, name_suffix)
    tuple is an ACTUAL row in supreme_court_justices_sections.csv — never
    a re-split or re-typed string. Catches a hand-edit typo in the mapping
    CSV that the coverage/structural checks above wouldn't otherwise see
    (they only compare the mapping against itself and against
    speakers.json, never against the source CSV's own cells).
    """
    failures = []
    for row in mapping_rows:
        key = (
            row["first_name"].strip(),
            row["middle_name"].strip(),
            row["last_name"].strip(),
            row["name_suffix"].strip(),
        )
        if key not in source_csv_name_part_rows:
            failures.append(f"{row['oyez_speaker_id']}: {key!r} not found in source CSV rows")

    assert not failures, (
        "Mapping row name parts not found in the source CSV:\n" + "\n".join(failures)
    )


def test_holmes_is_the_only_suffix_disagreement(mapping_rows):
    """
    D-05: Holmes is the SINGLE tolerated suffix disagreement across all
    114 rows — his corpus_display_name carries "Jr." while his name_suffix
    cell is deliberately empty (his CSV/tenure-era form, per the operator's
    own decision not to add a suffix that would misrepresent his time on
    the bench). Named explicitly here rather than tolerated by a general
    suffix-mismatch rule, so a future SECOND suffix disagreement fails
    loudly instead of silently joining an already-broad allowance.

    `test_corpus_display_name_reconstructs_from_name_parts` above already
    proves no OTHER non-exception row disagrees on suffix (a suffix
    mismatch would make neither of that test's two candidate
    reconstructions match, since `_join_name` only ever adds a suffix
    marker when `name_suffix` is populated) — this test only needs to pin
    Holmes's own specific, expected disagreement by name.
    """
    holmes_rows = [row for row in mapping_rows if row["oyez_speaker_id"] == _HOLMES_ID]
    assert len(holmes_rows) == 1, f"Expected exactly one Holmes row, found {len(holmes_rows)}"
    holmes = holmes_rows[0]

    assert holmes["name_suffix"].strip() == "", (
        f"Holmes's name_suffix is {holmes['name_suffix']!r}, expected empty (D-05)"
    )
    assert "Jr." in holmes["corpus_display_name"], (
        f"Holmes's corpus_display_name is {holmes['corpus_display_name']!r}, "
        "expected it to carry 'Jr.' (D-05)"
    )


# ---------------------------------------------------------------------------
# Behavior 3: row count + uniqueness
# ---------------------------------------------------------------------------


def test_row_count_is_114_and_every_id_unique(mapping_rows):
    assert len(mapping_rows) == _EXPECTED_ROW_COUNT, (
        f"Expected {_EXPECTED_ROW_COUNT} rows, found {len(mapping_rows)}"
    )
    ids = [row["oyez_speaker_id"] for row in mapping_rows]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"Duplicate oyez_speaker_id value(s): {sorted(duplicates)}"


# ---------------------------------------------------------------------------
# Behavior 4: header shape, confidence absent
# ---------------------------------------------------------------------------


def test_header_is_exactly_six_columns_no_confidence(mapping_header):
    assert mapping_header == _EXPECTED_HEADER, (
        f"Header is {mapping_header}, expected {_EXPECTED_HEADER}"
    )
    assert "confidence" not in mapping_header, "confidence column must be absent (D-08)"
