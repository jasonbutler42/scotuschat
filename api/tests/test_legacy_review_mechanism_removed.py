"""
REVIEW-05 structural no-parallel-mechanism contract (Phase 49 plan 49-02).

Migration `0029` folded `Person.name_needs_review` /
`Person.name_extraction_metadata` (migration 0022, Phase 38) into the
unified `Person.review_state` / `Person.provenance_metadata` record
(D-08). REVIEW-05 is a DELETION requirement, not an addition requirement:
the two legacy names must not survive anywhere in the live codebase as a
parallel mechanism someone could accidentally resurrect.

Pure module: no DB, no fixtures, no skip markers — modeled structurally on
`api/tests/test_trust_public_leak_ban.py` (parametrized sweep + a Test-2
false-green guard proving the derivation is non-vacuous).

Walks every git-tracked `.py`, `.ts`, and `.svelte` file under `api/`,
`app/src/`, `pipeline/`, `scripts/`, and `tests/` (the exact site
inventory 49-02-PLAN.md named for the fold). `.py` files are checked via
`ast` — `ast.Attribute` attribute names, `ast.Name` ids, exact-match
string `ast.Constant` values (skipping module/class/function docstrings,
so a prose paragraph explaining this history does not produce a false
positive), and `ast.keyword` argument names — rather than a raw text grep.
No Python AST parser exists here for TypeScript/Svelte, so `.ts`/`.svelte`
files fall back to a plain text search.

Three REVIEW-05 policy exemptions, each a named module-level constant:
  1. `alembic/versions/` — migration history is the permanent record of
     the change (CLAUDE.md: raw history is immutable).
  2. A test module whose SUBJECT is a specific migration (`test_migration_`
     filename prefix) — it legitimately exercises the migration's own DDL
     against a scratch database at a pinned historical revision.
  3. A migration's own `downgrade()` function body — the reverse path
     legitimately re-creates the old columns; it is not a parallel
     mechanism.

A fourth, structural (not policy) exemption applies to exactly one file:
this module's own source, because the banned identifiers must be written
down somewhere as the literal data being searched for — the same
self-exclusion `api/tests/test_phase44_descriptor_rename.py` already
uses for its own needle ("the string appears here only as the thing
being searched for").
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]

# The two Phase 38 legacy Person columns migration 0029 folded into the
# unified review record (D-08). REVIEW-05 requires neither name to survive
# anywhere in the live codebase outside the exemptions below.
BANNED_IDENTIFIERS = {"name_needs_review", "name_extraction_metadata"}

# Directories this sweep walks — the exact site inventory 49-02-PLAN.md
# named for the fold (api/, app/src/, pipeline/, scripts/, tests/).
SWEEP_DIRS = ("api", "app/src", "pipeline", "scripts", "tests")

# Exemption 1: migration history is the permanent record of the change —
# every historical migration file that ever touched these columns keeps
# naming them verbatim (CLAUDE.md: raw history is immutable).
ALEMBIC_VERSIONS_PREFIX = "alembic/versions/"

# Exemption 2: a test module whose SUBJECT is a specific migration
# exercises that migration's real DDL/backfill against a scratch database
# pinned to a historical revision, and legitimately names these columns.
MIGRATION_TEST_FILENAME_PREFIX = "test_migration_"

# Exemption 3: a migration's own downgrade() function body legitimately
# re-creates the old columns on the reverse path — see
# `_iter_nodes_excluding_downgrade` below, which skips its entire subtree.
DOWNGRADE_FUNCTION_NAME = "downgrade"

# Structural (not policy) self-exemption: this module's own file name. The
# banned identifiers must appear here as literal data — the thing being
# searched for — exactly as test_phase44_descriptor_rename.py already
# excludes its own file from its analogous residual-name sweep.
SELF_EXEMPT_FILENAME = Path(__file__).name

EXEMPTION_CATEGORIES = (
    f"migration history under {ALEMBIC_VERSIONS_PREFIX}",
    f"migration-specific test modules ({MIGRATION_TEST_FILENAME_PREFIX}* filename prefix)",
    f"a migration's own {DOWNGRADE_FUNCTION_NAME}() function body",
)


def _tracked_files() -> list[Path]:
    """
    Every git-tracked .py/.ts/.svelte file under the sweep directories,
    resolved to absolute paths. `git ls-files` (not Path.rglob) so this
    sweep matches the repo's actual tracked-file set, not local
    scratch/generated output that happens to sit under one of these
    directories.
    """
    result = subprocess.run(
        ["git", "ls-files", *SWEEP_DIRS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for relpath in result.stdout.splitlines():
        if relpath.endswith((".py", ".ts", ".svelte")):
            paths.append(ROOT / relpath)
    return paths


def _is_exempt(relpath: str) -> bool:
    if relpath.startswith(ALEMBIC_VERSIONS_PREFIX):
        return True
    if Path(relpath).name.startswith(MIGRATION_TEST_FILENAME_PREFIX):
        return True
    if Path(relpath).name == SELF_EXEMPT_FILENAME:
        return True
    return False


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    """
    Collect id() of every module/class/function docstring Constant node so
    the string-constant check below can skip prose explaining this history
    without also skipping a genuine code-level string literal (a raw SQL
    fragment, a dict key) that happens to exactly equal a banned
    identifier.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _iter_nodes_excluding_downgrade(tree: ast.AST):
    """
    Yield every AST node in `tree` except the subtree of any function named
    `downgrade` (exemption 3) — at any nesting depth, not just top-level.
    """
    yield tree
    stack = [tree]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == DOWNGRADE_FUNCTION_NAME
            ):
                continue
            yield child
            stack.append(child)


def _python_violations(path: Path) -> list[str]:
    # utf-8-sig transparently strips a leading BOM (present on at least one
    # tracked file in this repo) while behaving identically to utf-8 for
    # every BOM-less file — plain utf-8 raises SyntaxError on ast.parse.
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    docstring_ids = _docstring_constant_ids(tree)
    relpath = str(path.relative_to(ROOT))
    violations: list[str] = []
    for node in _iter_nodes_excluding_downgrade(tree):
        hit = None
        if isinstance(node, ast.Attribute) and node.attr in BANNED_IDENTIFIERS:
            hit = node.attr
        elif isinstance(node, ast.Name) and node.id in BANNED_IDENTIFIERS:
            hit = node.id
        elif isinstance(node, ast.keyword) and node.arg in BANNED_IDENTIFIERS:
            hit = node.arg
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in BANNED_IDENTIFIERS
            and id(node) not in docstring_ids
        ):
            hit = node.value
        if hit is not None:
            lineno = getattr(node, "lineno", "?")
            violations.append(
                f"{relpath}:{lineno} references '{hit}' — REVIEW-05 forbids "
                "the Phase 38 legacy review mechanism outside migration history"
            )
    return violations


def _text_violations(path: Path) -> list[str]:
    """Plain text search for .ts/.svelte — no Python AST parser exists here
    for TypeScript/Svelte, so this checks for the identifier substring
    directly, line by line, so the message can still point at a line."""
    source = path.read_text(encoding="utf-8")
    relpath = str(path.relative_to(ROOT))
    violations: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        for banned in BANNED_IDENTIFIERS:
            if banned in line:
                violations.append(
                    f"{relpath}:{lineno} references '{banned}' — REVIEW-05 forbids "
                    "the Phase 38 legacy review mechanism outside migration history"
                )
    return violations


def _all_violations() -> list[str]:
    violations: list[str] = []
    for path in _tracked_files():
        relpath = str(path.relative_to(ROOT))
        if _is_exempt(relpath):
            continue
        if path.suffix == ".py":
            violations.extend(_python_violations(path))
        else:
            violations.extend(_text_violations(path))
    return violations


# ---------------------------------------------------------------------------
# Test 1: the structural ban itself
# ---------------------------------------------------------------------------


def test_legacy_review_mechanism_does_not_survive_outside_migration_history() -> None:
    """
    REVIEW-05: neither `name_needs_review` nor `name_extraction_metadata`
    may appear anywhere under api/, app/src/, pipeline/, scripts/, or
    tests/ — outside migration history, a migration-specific test module,
    or a migration's own downgrade() body (the reverse path legitimately
    re-creates the old columns).
    """
    violations = _all_violations()
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Test 2: the false-green guard — exemptions are real, non-vacuous, and at
# least one exempted migration file genuinely contains the banned names.
# ---------------------------------------------------------------------------


def test_exemption_categories_are_non_empty_and_migrations_genuinely_contain_them() -> None:
    """
    Guards against the sweep above passing vacuously — e.g. if
    `_tracked_files()` silently returned nothing, or if the exemption
    predicate were accidentally too broad and swallowed every file. Proves
    there IS something to ban: at least one exempted Alembic migration
    file genuinely contains both banned identifiers.
    """
    assert EXEMPTION_CATEGORIES, "Exemption categories must not be empty"

    tracked = _tracked_files()
    assert tracked, (
        "`git ls-files` returned no .py/.ts/.svelte files under the sweep "
        "directories — the ban above would pass vacuously."
    )

    migration_0022 = ROOT / "alembic" / "versions" / "0022_person_name_authority.py"
    migration_0029 = ROOT / "alembic" / "versions" / "0029_person_review_state_fold.py"
    assert migration_0022.is_file()
    assert migration_0029.is_file()

    combined_source = (
        migration_0022.read_text(encoding="utf-8")
        + migration_0029.read_text(encoding="utf-8")
    )
    for banned in BANNED_IDENTIFIERS:
        assert banned in combined_source, (
            f"Neither migration 0022 nor 0029 mentions '{banned}' — the "
            "exemption sweep guard cannot prove it is testing a real ban "
            "(false-green risk)."
        )
