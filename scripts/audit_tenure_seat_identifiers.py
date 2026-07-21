#!/usr/bin/env python3
"""Repository-wide audit for stale `seat` identifiers (Phase 37, D-17).

Phase 37 renamed the free-text court_tenures.seat column/field to the
canonical two-value `office` model end to end — database column, ORM
attribute, Pydantic schemas, API payloads, the CSV importer, services,
SvelteKit form state/serialization, and every read-only consumer — with no
`seat` compatibility alias (D-17). This script proves that claim keeps
holding: it walks api/, pipeline/, app/, and tests/ for whole-word
`seat`/`Seat` occurrences and fails (nonzero exit) on any hit that is not an
exact, explicitly documented exception below.

Exception categories (37-CONTEXT.md "the agent's Discretion" — exact
mechanism left to the implementer provided the D-17 no-alias contract
holds):

  - migration-history: prose (comments/docstrings only — never a live
    identifier, column, payload key, or field name) that documents the
    historical seat -> office rename itself.
  - legacy-fixture: test code that intentionally constructs, asserts
    against, or documents a legacy `seat`-shaped input value (e.g. the
    numbered "Associate Justice Seat 3") to prove it is normalized,
    rejected, or tolerated for display-only correction — never a live
    production write or read path. This also covers a test's own negative
    assertion that no `seat` identifier is rendered/serialized.

Every exception is pinned to an exact (file, line number, line text) triple.
Any whole-word "seat" hit that does not match this list exactly — including
one on a *different* line of an already-exempted file — fails the audit.
This is deliberate: a legitimate new prose mention must be reviewed and
added here explicitly, the same way the ones below were.

Usage: python scripts/audit_tenure_seat_identifiers.py
Exit code 0: no unclassified hits. Exit code 1: unclassified hit(s) found,
a missing scan root, or a file that could not be read.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = ["api", "pipeline", "app", "tests"]

# Directories that never contain source we care about (build output,
# dependency trees, caches, generated types) — always excluded from the walk.
EXCLUDED_DIR_NAMES = {
    "node_modules",
    ".svelte-kit",
    "__pycache__",
    ".git",
    "build",
    "dist",
    ".venv",
    "venv",
}

# Source-code extensions this audit scans. Phase 37 touched exactly these
# languages; no seat-shaped identifier can hide in a generated/binary asset.
INCLUDED_SUFFIXES = {".py", ".ts", ".svelte", ".mjs", ".js"}

WORD_RE = re.compile(r"\bseat\b", re.IGNORECASE)

# (relative_path, line_number, exact_stripped_line_text)
#
# migration-history exceptions — prose documenting the D-17 rename itself:
_MIGRATION_HISTORY: set[tuple[str, int, str]] = {
    (
        "api/models/models.py",
        130,
        '# legacy free-text `seat` column (e.g. "Associate Justice Seat 3") was',
    ),
    (
        "api/models/models.py",
        133,
        "# (ck_court_tenures_office) + NOT NULL. There is no `seat` compatibility",
    ),
    (
        "api/schemas/admin_people.py",
        18,
        "free-text `seat` column end to end — there is no `seat` compatibility alias.",
    ),
    (
        "api/schemas/speakers.py",
        20,
        "here. There is no `seat` compatibility alias.",
    ),
    (
        "pipeline/commands/import_justices_csv.py",
        47,
        "# numbered-seat distinctions in the active model).",
    ),
    (
        "app/src/routes/admin/people/[id]/+page.svelte",
        34,
        "// seat field. A valid row always holds exactly one canonical value;",
    ),
    (
        "app/src/routes/admin/people/[id]/+page.svelte",
        630,
        "replacing the free-text seat field. Exactly one of the two",
    ),
    (
        "app/src/routes/admin/people/[id]/+page.server.ts",
        8,
        "// office (D-01..D-17, Phase 37) replaces the old free-text seat field.",
    ),
}

# legacy-fixture exceptions — legacy numbered-seat input values a test
# deliberately constructs/asserts against (normalization, rejection, or
# tolerant-read display), or a test's own negative assertion that no `seat`
# identifier is rendered/serialized:
_LEGACY_FIXTURE: set[tuple[str, int, str]] = {
    (
        "api/tests/test_admin_people_schemas_service.py",
        250,
        '"""Legacy numbered-seat strings and formal titles are rejected on write',
    ),
    (
        "api/tests/test_admin_people_schemas_service.py",
        257,
        '"Associate Justice Seat 3",',
    ),
    (
        "api/tests/test_admin_people_schemas_service.py",
        299,
        'row = TenureRow(office="Associate Justice Seat 3", start_date="2006-01-31")',
    ),
    (
        "api/tests/test_admin_people_schemas_service.py",
        300,
        'assert row.office == "Associate Justice Seat 3"',
    ),
    (
        "app/tests/tenure-office.browser.test.mjs",
        55,
        "assert.doesNotMatch(addRow, /seat\\s*:/);",
    ),
    (
        "app/tests/tenure-office.browser.test.mjs",
        84,
        "assert.doesNotMatch(officeMarkup(), /name=[\"']seat[\"']/);",
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        45,
        '("Associate Justice Seat 3", "associate"),',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        46,
        '("Associate Justice Seat 12", "associate"),',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        54,
        '@pytest.mark.parametrize("legacy", [None, "", "   ", "Unknown", "Associate-ish", "Seat 3"])',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        62,
        'assert "fullmatch" in source or "^Associate Justice Seat" in source',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        69,
        '{"id": 9, "original_office": "Associate Justice Seat 3"},',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        81,
        '9: "Associate Justice Seat 3",',
    ),
    (
        "tests/test_migrate_tenure_offices.py",
        187,
        'assert "new_column_name=\\"seat\\"" in source',
    ),
}

ALLOWED_EXCEPTIONS: set[tuple[str, int, str]] = _MIGRATION_HISTORY | _LEGACY_FIXTURE


def _iter_scanned_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in INCLUDED_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        yield path


def main() -> int:
    missing_roots = [name for name in SCAN_ROOTS if not (ROOT / name).is_dir()]
    if missing_roots:
        print(
            f"ERROR: expected scan root(s) not found: {missing_roots}",
            file=sys.stderr,
        )
        return 1

    unclassified: list[tuple[str, int, str]] = []
    seen_exceptions: set[tuple[str, int, str]] = set()

    for root_name in SCAN_ROOTS:
        for path in _iter_scanned_files(ROOT / root_name):
            rel = path.relative_to(ROOT).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError) as exc:
                print(f"ERROR: could not read {rel}: {exc}", file=sys.stderr)
                return 1
            for lineno, line in enumerate(text.splitlines(), start=1):
                if not WORD_RE.search(line):
                    continue
                stripped = line.strip()
                key = (rel, lineno, stripped)
                if key in ALLOWED_EXCEPTIONS:
                    seen_exceptions.add(key)
                    continue
                unclassified.append(key)

    if unclassified:
        print(
            f"FAIL: {len(unclassified)} unclassified active `seat` identifier(s) found "
            "(not in the documented exception list):",
            file=sys.stderr,
        )
        for rel, lineno, stripped in unclassified:
            print(f"  {rel}:{lineno}: {stripped}", file=sys.stderr)
        print(
            "\nIf this is a genuine new migration-history or legacy-fixture "
            "reference, add its exact (path, line, text) to "
            "scripts/audit_tenure_seat_identifiers.py's exception list. If it "
            "is a real regression, rename the identifier to `office` (D-17).",
            file=sys.stderr,
        )
        return 1

    stale_exceptions = sorted(ALLOWED_EXCEPTIONS - seen_exceptions)
    if stale_exceptions:
        print(
            f"FAIL: {len(stale_exceptions)} documented exception(s) no longer "
            "match the repository (moved, edited, or removed) — update the "
            "exception list to stay exact:",
            file=sys.stderr,
        )
        for rel, lineno, stripped in stale_exceptions:
            print(f"  {rel}:{lineno}: {stripped}", file=sys.stderr)
        return 1

    print(
        "PASS: no unclassified `seat` identifiers found "
        f"(scanned {', '.join(SCAN_ROOTS)}; "
        f"{len(ALLOWED_EXCEPTIONS)} documented exception(s), all matched)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
