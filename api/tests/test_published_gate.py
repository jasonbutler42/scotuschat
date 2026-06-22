"""
Tests asserting the public visibility gate in get_cases() uses published_at, not resolved_at.

These are source-level assertion tests that verify the correct filter is used in
api/services/cases.py — they run without a live database.

The key security requirement (T-11-01 STRIDE threat): the public /cases/ endpoint
must never return unpublished (resolved-but-not-published) arguments. The gate
is enforced by the SQLAlchemy filter in get_cases().
"""

import ast
import os
import textwrap


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _get_cases_source_lines() -> list[str]:
    """Read api/services/cases.py and return non-comment, non-blank lines from get_cases()."""
    import pathlib
    source_path = pathlib.Path(__file__).parent.parent / "services" / "cases.py"
    source = source_path.read_text(encoding="utf-8")

    # Parse AST to extract the get_cases function body as source text
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_cases":
            # Get line range of the function body
            start = node.lineno
            end = node.end_lineno
            lines = source.splitlines()[start - 1 : end]
            # Strip comment-only lines before returning
            non_comment = [
                line for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            return non_comment

    return []


class TestPublishedGate:
    """Source-level assertions ensuring the published_at gate is in place (T-11-01)."""

    def test_get_cases_uses_published_at_filter(self):
        """
        get_cases() must filter on Argument.published_at.isnot(None).

        This ensures unpublished (resolved-but-not-published) arguments are hidden
        from the public /cases/ endpoint.
        """
        lines = _get_cases_source_lines()
        assert lines, "Could not extract get_cases() body from api/services/cases.py"

        combined = "\n".join(lines)
        assert "Argument.published_at.isnot" in combined, (
            "get_cases() must filter on Argument.published_at.isnot(None) "
            "(D-06 visibility gate). "
            f"Actual get_cases body (non-comment lines):\n{combined}"
        )

    def test_get_cases_does_not_use_resolved_at_filter(self):
        """
        get_cases() must NOT filter on Argument.resolved_at.isnot(None).

        The visibility gate was changed from resolved_at to published_at (D-06).
        Using resolved_at would expose arguments that are resolved but not yet
        approved for publication.
        """
        lines = _get_cases_source_lines()
        assert lines, "Could not extract get_cases() body from api/services/cases.py"

        combined = "\n".join(lines)
        assert "Argument.resolved_at.isnot" not in combined, (
            "get_cases() must not filter on Argument.resolved_at.isnot(None) — "
            "the visibility gate was changed to published_at (D-06). "
            f"Actual get_cases body (non-comment lines):\n{combined}"
        )

    def test_get_cases_preserves_is_lead_filter(self):
        """
        Changing the visibility gate must not remove the CaseArgument.is_lead filter.

        The is_lead filter prevents duplicate rows for consolidated dockets.
        """
        lines = _get_cases_source_lines()
        assert lines, "Could not extract get_cases() body from api/services/cases.py"

        combined = "\n".join(lines)
        assert "is_lead" in combined, (
            "get_cases() must still filter on CaseArgument.is_lead == True "
            "(prevents duplicate rows for consolidated dockets). "
            f"Actual get_cases body (non-comment lines):\n{combined}"
        )

    def test_get_cases_preserves_return_keys(self):
        """
        The returned dict keys from get_cases() must be unchanged:
        id, slug, case_name, docket_number, term_year, argued_date,
        argument_id, question_number.
        """
        import pathlib
        source_path = pathlib.Path(__file__).parent.parent / "services" / "cases.py"
        source = source_path.read_text(encoding="utf-8")

        required_keys = [
            "id", "slug", "case_name", "docket_number", "term_year",
            "argued_date", "argument_id", "question_number",
        ]
        for key in required_keys:
            assert f'"{key}"' in source or f"'{key}'" in source, (
                f"get_cases() return dict must include key '{key}'"
            )
