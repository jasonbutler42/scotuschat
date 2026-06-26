"""
Unit tests for pipeline/parser/cover_extractor.py.

These tests do NOT require a database or real PDFs — they exercise
cover_extractor.py directly using in-memory string data and synthetic
re.Match objects constructed from the module's own regex patterns.

Test IDs covered:
  - PARSE-01: Extract argued_date and case_name from cover pages

Transcript range tested against: Obergefell 2015 (Alderson) through Rahimi 2023 (Heritage).
"""

import pytest


# ---------------------------------------------------------------------------
# Test 1: _extract_case_name — Alderson format (separator + petitioner lines)
# ---------------------------------------------------------------------------


def test_extract_case_name_alderson_basic():
    """_extract_case_name on Alderson-format lines returns name up to 'Petitioners,'."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "\xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad x",
        "JAMES OBERGEFELL, ET AL.,",
        "Petitioners,",
    ]
    result = _extract_case_name(lines)
    assert result == "JAMES OBERGEFELL, ET AL.", (
        f"Expected 'JAMES OBERGEFELL, ET AL.' but got: {result!r}"
    )


def test_extract_case_name_no_header_returns_none():
    """_extract_case_name on lines with no SCOTUS header returns None."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "JAMES OBERGEFELL, ET AL.,",
        "Petitioners,",
        "v.",
        "RICHARD HODGES, ET AL.,",
        "Respondents.",
    ]
    result = _extract_case_name(lines)
    assert result is None, (
        f"Expected None when no SCOTUS header is present, got: {result!r}"
    )


def test_extract_case_name_stops_at_v_line():
    """_extract_case_name stops accumulating at a 'v.' line."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "\xad \xad \xad x",
        "DOBBS,",
        "v.",
        "JACKSON WOMEN'S HEALTH ORGANIZATION,",
        "Respondents.",
    ]
    result = _extract_case_name(lines)
    assert result == "DOBBS", (
        f"Expected 'DOBBS' (stops at 'v.' line), got: {result!r}"
    )


def test_extract_case_name_multiline():
    """_extract_case_name joins multi-line petitioner names with a space."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "- - - - - - - - - - - - - - - -",
        "MIKE MOYLE, SPEAKER OF THE IDAHO",
        "HOUSE OF REPRESENTATIVES, ET AL.,",
        "Petitioners,",
    ]
    result = _extract_case_name(lines)
    assert result == "MIKE MOYLE, SPEAKER OF THE IDAHO HOUSE OF REPRESENTATIVES, ET AL.", (
        f"Expected joined multi-line name, got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: _parse_date — weekday format and Heritage "Date:" format
# ---------------------------------------------------------------------------


def test_parse_date_weekday_format():
    """_parse_date on a match from DATE_LINE_RE returns the correct date."""
    import re
    from datetime import date
    from pipeline.parser.cover_extractor import DATE_LINE_RE, _parse_date

    m = DATE_LINE_RE.search("Tuesday, April 28, 2015")
    assert m is not None, "DATE_LINE_RE should match 'Tuesday, April 28, 2015'"
    result = _parse_date(m)
    assert result == date(2015, 4, 28), (
        f"Expected date(2015, 4, 28), got: {result!r}"
    )


def test_parse_date_heritage_format():
    """_parse_date on a match from HERITAGE_DATE_RE (no weekday) returns the correct date."""
    import re
    from datetime import date
    from pipeline.parser.cover_extractor import HERITAGE_DATE_RE, _parse_date

    m = HERITAGE_DATE_RE.search("Date: April 24, 2024")
    assert m is not None, "HERITAGE_DATE_RE should match 'Date: April 24, 2024'"
    result = _parse_date(m)
    assert result == date(2024, 4, 24), (
        f"Expected date(2024, 4, 24), got: {result!r}"
    )


def test_parse_date_case_insensitive():
    """_parse_date handles mixed-case month names."""
    import re
    from datetime import date
    from pipeline.parser.cover_extractor import DATE_LINE_RE, _parse_date

    m = DATE_LINE_RE.search("wednesday, october 5, 2022")
    assert m is not None, "DATE_LINE_RE should be case-insensitive"
    result = _parse_date(m)
    assert result == date(2022, 10, 5), (
        f"Expected date(2022, 10, 5), got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: _clean_lines — strips headers, page numbers, and line numbers
# ---------------------------------------------------------------------------


def test_clean_lines_drops_header_lines():
    """_clean_lines drops lines matched by HEADER_RE."""
    from pipeline.parser.cover_extractor import _clean_lines

    raw = "\n".join([
        "ALDERSON REPORTING COMPANY",
        "Official Reporters",
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "Heritage Reporting Corporation",
    ])
    result = _clean_lines(raw)
    # Only the SCOTUS line should remain (ALDERSON, Official, Heritage are filtered)
    assert "IN THE SUPREME COURT OF THE UNITED STATES" in result, (
        f"Expected SCOTUS line to survive _clean_lines, got: {result!r}"
    )
    for dropped in ("ALDERSON REPORTING COMPANY", "Official Reporters", "Heritage Reporting Corporation"):
        assert dropped not in result, (
            f"Expected '{dropped}' to be filtered by _clean_lines, got: {result!r}"
        )


def test_clean_lines_drops_bare_page_numbers():
    """_clean_lines drops bare page number lines (single integer)."""
    from pipeline.parser.cover_extractor import _clean_lines

    raw = "\n".join([
        "2",
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "42",
    ])
    result = _clean_lines(raw)
    assert "2" not in result, f"Bare page number '2' should be dropped, got: {result!r}"
    assert "42" not in result, f"Bare page number '42' should be dropped, got: {result!r}"
    assert "IN THE SUPREME COURT OF THE UNITED STATES" in result, (
        f"Content line should survive, got: {result!r}"
    )


def test_clean_lines_strips_line_numbers():
    """_clean_lines strips left-margin transcript line numbers via strip_line_number."""
    from pipeline.parser.cover_extractor import _clean_lines

    # Alderson format: "  1 IN THE SUPREME COURT..."
    raw = "  1 IN THE SUPREME COURT OF THE UNITED STATES"
    result = _clean_lines(raw)
    assert result == ["IN THE SUPREME COURT OF THE UNITED STATES"], (
        f"Expected line number stripped, got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: extract_cover_metadata — silent fail on missing path (D-05)
# ---------------------------------------------------------------------------


def test_extract_cover_metadata_missing_pdf_returns_empty():
    """extract_cover_metadata on a non-existent path returns {} and never raises (D-05)."""
    from pathlib import Path
    from pipeline.parser.cover_extractor import extract_cover_metadata

    result = extract_cover_metadata(Path("does-not-exist-at-all.pdf"))
    assert result == {}, (
        f"Expected {{}} for missing PDF (D-05 silent-fail contract), got: {result!r}"
    )


def test_extract_cover_metadata_returns_dict():
    """extract_cover_metadata always returns a dict (never raises, never returns None)."""
    from pathlib import Path
    from pipeline.parser.cover_extractor import extract_cover_metadata

    # Even with a completely nonsense path, must return a dict
    result = extract_cover_metadata(Path("/nonexistent/path/fake.pdf"))
    assert isinstance(result, dict), (
        f"Expected dict, got: {type(result)!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: Regex constants are imported from extractor.py, not redefined
# ---------------------------------------------------------------------------


def test_header_re_and_page_num_re_are_not_redefined():
    """HEADER_RE and PAGE_NUM_RE are imported from extractor.py, not defined in cover_extractor."""
    import pipeline.parser.cover_extractor as ce
    import pipeline.parser.extractor as ext

    # They should be the exact same object (identity check — both point to the same compiled regex)
    assert ce.HEADER_RE is ext.HEADER_RE, (
        f"HEADER_RE in cover_extractor should be the same object as in extractor.py"
    )
    assert ce.PAGE_NUM_RE is ext.PAGE_NUM_RE, (
        f"PAGE_NUM_RE in cover_extractor should be the same object as in extractor.py"
    )
