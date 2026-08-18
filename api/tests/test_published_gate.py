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
import re
import textwrap

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


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


def _service_function_source_lines(module_filename: str, function_name: str) -> list[str]:
    """
    Read api/services/<module_filename> and return non-comment, non-blank lines
    from the named async function's body.

    Generalizes _get_cases_source_lines() above to any (module, function) pair
    in api/services/, so the argument-detail publish-gate tests (BUG-01) can
    reuse the same AST-extraction shape without duplicating it per function.
    """
    import pathlib
    source_path = pathlib.Path(__file__).parent.parent / "services" / module_filename
    source = source_path.read_text(encoding="utf-8")

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            start = node.lineno
            end = node.end_lineno
            lines = source.splitlines()[start - 1 : end]
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


class TestArgumentDetailPublishedGate:
    """
    Source-level assertions ensuring the publish gate (BUG-01/D-02) covers both
    public argument-detail endpoints, mirroring TestPublishedGate's style for
    get_cases(). No live database is required for this class.
    """

    def test_get_argument_with_utterances_uses_published_at_filter(self):
        """
        get_argument_with_utterances() must filter on Argument.published_at.isnot(None).

        This closes BUG-01: direct access to GET /arguments/{id}/utterances must not
        leak an unpublished argument's transcript.
        """
        lines = _service_function_source_lines("arguments.py", "get_argument_with_utterances")
        assert lines, (
            "Could not extract get_argument_with_utterances() body from "
            "api/services/arguments.py"
        )

        combined = "\n".join(lines)
        assert "Argument.published_at.isnot" in combined, (
            "get_argument_with_utterances() must filter on Argument.published_at.isnot(None) "
            "(BUG-01/D-02 visibility gate). "
            f"Actual body (non-comment lines):\n{combined}"
        )

    def test_get_argument_with_utterances_does_not_use_resolved_at_filter(self):
        """
        get_argument_with_utterances() must NOT filter on Argument.resolved_at.isnot(None).

        The gate must key on published_at only, never resolved_at (D-02).
        """
        lines = _service_function_source_lines("arguments.py", "get_argument_with_utterances")
        assert lines, (
            "Could not extract get_argument_with_utterances() body from "
            "api/services/arguments.py"
        )

        combined = "\n".join(lines)
        assert "Argument.resolved_at.isnot" not in combined, (
            "get_argument_with_utterances() must not filter on "
            "Argument.resolved_at.isnot(None) — the visibility gate must key on "
            "published_at only (BUG-01/D-02). "
            f"Actual body (non-comment lines):\n{combined}"
        )

    def test_get_argument_speakers_uses_published_at_filter(self):
        """
        get_argument_speakers() must gate on Argument.published_at.

        This closes BUG-01's second leak path (D-02, T-45-02): direct access to
        GET /arguments/{id}/speakers must not leak an unpublished argument's
        speaker roster.
        """
        lines = _service_function_source_lines("speakers.py", "get_argument_speakers")
        assert lines, (
            "Could not extract get_argument_speakers() body from api/services/speakers.py"
        )

        combined = "\n".join(lines)
        assert "Argument.published_at" in combined, (
            "get_argument_speakers() must filter/gate on Argument.published_at "
            "(BUG-01/D-02 visibility gate). "
            f"Actual body (non-comment lines):\n{combined}"
        )

    def test_get_argument_speakers_does_not_use_resolved_at_filter(self):
        """
        get_argument_speakers() must NOT gate on Argument.resolved_at.

        The gate must key on published_at only, never resolved_at (D-02).
        """
        lines = _service_function_source_lines("speakers.py", "get_argument_speakers")
        assert lines, (
            "Could not extract get_argument_speakers() body from api/services/speakers.py"
        )

        combined = "\n".join(lines)
        assert "Argument.resolved_at" not in combined, (
            "get_argument_speakers() must not gate on Argument.resolved_at — the "
            "visibility gate must key on published_at only (BUG-01/D-02). "
            f"Actual body (non-comment lines):\n{combined}"
        )

    def test_get_argument_speakers_preserves_empty_list_short_circuit(self):
        """
        The legitimate empty-list path (published argument, zero resolved
        speakers) must survive the publish gate unchanged — an empty list must
        never be converted into a 404 (EDGE empty, BUG-01).
        """
        lines = _service_function_source_lines("speakers.py", "get_argument_speakers")
        assert lines, (
            "Could not extract get_argument_speakers() body from api/services/speakers.py"
        )

        combined = "\n".join(lines)
        assert "if not person_ids" in combined, (
            "get_argument_speakers() must preserve the 'if not person_ids: return []' "
            "short-circuit — a published argument with zero resolved speakers must "
            f"return 200/[] , never 404 (EDGE empty, BUG-01). Actual body:\n{combined}"
        )

    def test_speakers_router_404_detail_matches_utterances_router(self):
        """
        D-01: the speakers endpoint's 404 must be byte-identical (same detail
        string, same status) to the utterances endpoint's 404 for the same
        absent/unpublished argument.
        """
        import pathlib
        source_path = pathlib.Path(__file__).parent.parent / "routers" / "arguments.py"
        source = source_path.read_text(encoding="utf-8")

        detail_line = 'raise HTTPException(status_code=404, detail="Argument not found")'
        occurrences = source.count(detail_line)
        assert occurrences == 2, (
            "api/routers/arguments.py must raise the identical "
            f'{detail_line!r} exactly twice — once in get_utterances, once in '
            f"get_speakers (D-01). Found {occurrences} occurrence(s)."
        )

    def test_publish_gate_adjacency_across_gated_functions(self):
        """
        EDGE adjacency (BUG-01): all public publish gates key on
        Argument.published_at (never a clock comparison against it) — so
        publishing introduces no embargo or scheduled-publish semantics.

        get_cases() and get_argument_with_utterances() use the exact
        Argument.published_at.isnot(None) predicate at the SQL layer;
        get_argument_speakers() gates on the same column via a Python-side
        None check on the fetched value (per 45-PATTERNS.md's recommendation),
        which is asserted for substring presence rather than the exact SQL
        predicate text.
        """
        cases_lines = _get_cases_source_lines()
        arguments_lines = _service_function_source_lines(
            "arguments.py", "get_argument_with_utterances"
        )
        speakers_lines = _service_function_source_lines(
            "speakers.py", "get_argument_speakers"
        )

        cases_combined = "\n".join(cases_lines)
        arguments_combined = "\n".join(arguments_lines)
        speakers_combined = "\n".join(speakers_lines)

        assert "Argument.published_at.isnot(None)" in cases_combined, (
            "get_cases() must use the exact predicate Argument.published_at.isnot(None) "
            "(BUG-01 EDGE adjacency)."
        )
        assert "Argument.published_at.isnot(None)" in arguments_combined, (
            "get_argument_with_utterances() must use the exact predicate "
            "Argument.published_at.isnot(None) (BUG-01 EDGE adjacency)."
        )
        assert "Argument.published_at" in speakers_combined, (
            "get_argument_speakers() must gate on Argument.published_at "
            "(BUG-01 EDGE adjacency)."
        )

        clock_markers = ("func.now", "datetime.now", "utcnow")
        clock_regex = re.compile(r"published_at\s*[<>]=?")
        for label, combined in (
            ("get_cases", cases_combined),
            ("get_argument_with_utterances", arguments_combined),
            ("get_argument_speakers", speakers_combined),
        ):
            for marker in clock_markers:
                assert marker not in combined, (
                    f"{label}() must not compare published_at to a clock value "
                    f"(found '{marker}') — no embargo or scheduled-publish semantics "
                    f"are introduced by BUG-01 (EDGE adjacency). Actual body:\n{combined}"
                )
            assert not clock_regex.search(combined), (
                f"{label}() must not contain a relational comparison against "
                f"published_at (BUG-01 EDGE adjacency). Actual body:\n{combined}"
            )

    def test_ordering_preserved_after_publish_gate(self):
        """
        EDGE ordering (BUG-01): the gate adds WHERE clauses only — existing
        ordering-relevant clauses in get_argument_with_utterances() and
        get_cases() must survive unchanged.
        """
        arguments_lines = _service_function_source_lines(
            "arguments.py", "get_argument_with_utterances"
        )
        cases_lines = _get_cases_source_lines()

        arguments_combined = "\n".join(arguments_lines)
        cases_combined = "\n".join(cases_lines)

        assert "Utterance.sequence.asc()" in arguments_combined, (
            "get_argument_with_utterances() must preserve the Utterance.sequence.asc() "
            "ordering clause (BUG-01 EDGE ordering). "
            f"Actual body:\n{arguments_combined}"
        )
        assert "func.max(ImportRun.id)" in arguments_combined, (
            "get_argument_with_utterances() must preserve the max-import_run_id "
            "filter (BUG-01 EDGE ordering). "
            f"Actual body:\n{arguments_combined}"
        )
        assert "Argument.argued_date.desc()" in cases_combined, (
            "get_cases() must preserve the Argument.argued_date.desc() ordering "
            "clause (BUG-01 EDGE ordering). "
            f"Actual body:\n{cases_combined}"
        )

    def test_page_server_loader_throws_on_non_ok_and_has_no_publish_branch(self):
        """
        Confirms no frontend change is needed for BUG-01 (45-CONTEXT.md Claude's
        Discretion): the SvelteKit loader already converts a non-OK utterances
        response into error(res.status, ...) — which SvelteKit renders as its
        default error page on both client-side navigation and hard SSR refresh —
        and adds no publish-status-specific branch of its own.
        """
        import pathlib
        source_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "app" / "src" / "routes" / "cases" / "[slug]" / "arguments" / "[id]"
            / "+page.server.ts"
        )
        source = source_path.read_text(encoding="utf-8")

        assert "if (!res.ok) throw error(res.status" in source, (
            "+page.server.ts must still throw error(res.status, ...) on a non-OK "
            "utterances response — this is what turns the API's 404 into "
            "SvelteKit's default error page (D-01/D-02, no frontend change needed)."
        )
        assert "published" not in source.lower(), (
            "+page.server.ts must not add any publish-status-specific branch of "
            "its own — the API's plain 404 is the sole signal an unauthenticated "
            "visitor ever sees (D-01)."
        )


@pytest_asyncio.fixture
async def client():
    """
    Module-local async test client for the FastAPI app.

    Copied in shape from api/tests/test_arguments.py's client fixture: uses
    ASGITransport so tests run without a real network socket.
    """
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


async def _find_argument_id_by_publish_state(db, published: bool) -> int | None:
    """
    Return the id of an Argument row matching the requested publish state,
    or skip the calling test with an explicit reason if no such row exists.

    Phase 41/43 seeded publish-state variety into the dev DB, but this must
    not hard-fail if the operator's DB lacks a row of the needed state.
    """
    from sqlalchemy import select

    from api.models.models import Argument

    condition = (
        Argument.published_at.isnot(None) if published else Argument.published_at.is_(None)
    )
    result = await db.execute(select(Argument.id).where(condition).limit(1))
    argument_id = result.scalar_one_or_none()
    if argument_id is None:
        state = "published" if published else "unpublished"
        pytest.skip(
            f"No {state} argument found in the configured DB — seed data "
            "required for this integration test."
        )
    return argument_id


@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
class TestArgumentDetailPublishedGateLive:
    """
    Live-HTTP integration assertions for the argument-detail publish gate
    (BUG-01/D-02), run through the ASGI app when DATABASE_URL is configured.

    Uses discovered rows (not hardcoded IDs) so this class runs correctly
    against any DB state that has at least one published and one unpublished
    argument — skipping (not failing) individual tests when a row of the
    needed publish state isn't present.
    """

    async def test_unpublished_argument_utterances_returns_404(self, client, db_session):
        argument_id = await _find_argument_id_by_publish_state(db_session, published=False)
        response = await client.get(f"/arguments/{argument_id}/utterances")
        assert response.status_code == 404
        assert response.json() == {"detail": "Argument not found"}

    async def test_published_argument_utterances_returns_200(self, client, db_session):
        argument_id = await _find_argument_id_by_publish_state(db_session, published=True)
        response = await client.get(f"/arguments/{argument_id}/utterances")
        assert response.status_code == 200

    async def test_unpublished_utterances_404_body_matches_nonexistent_id(self, client, db_session):
        """D-01: the 404 for an unpublished argument must be body-identical to
        the 404 for a definitely-nonexistent ID."""
        argument_id = await _find_argument_id_by_publish_state(db_session, published=False)
        unpublished_response = await client.get(f"/arguments/{argument_id}/utterances")
        nonexistent_response = await client.get("/arguments/987654321/utterances")

        assert unpublished_response.status_code == 404
        assert nonexistent_response.status_code == 404
        assert unpublished_response.json() == {"detail": "Argument not found"}
        assert nonexistent_response.json() == {"detail": "Argument not found"}

    async def test_unpublished_argument_speakers_returns_404(self, client, db_session):
        """BUG-01/D-02 (Task 2): the speakers endpoint gates on published_at
        exactly like the utterances endpoint."""
        argument_id = await _find_argument_id_by_publish_state(db_session, published=False)
        response = await client.get(f"/arguments/{argument_id}/speakers")
        assert response.status_code == 404
        assert response.json() == {"detail": "Argument not found"}

    async def test_published_argument_speakers_returns_200(self, client, db_session):
        argument_id = await _find_argument_id_by_publish_state(db_session, published=True)
        response = await client.get(f"/arguments/{argument_id}/speakers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_unpublished_speakers_404_body_matches_nonexistent_id(self, client, db_session):
        """D-01: the 404 for an unpublished argument's speakers must be
        body-identical to the 404 for a definitely-nonexistent ID — the same
        equality property already proven for the utterances endpoint."""
        argument_id = await _find_argument_id_by_publish_state(db_session, published=False)
        unpublished_response = await client.get(f"/arguments/{argument_id}/speakers")
        nonexistent_response = await client.get("/arguments/987654321/speakers")

        assert unpublished_response.status_code == 404
        assert nonexistent_response.status_code == 404
        assert unpublished_response.json() == {"detail": "Argument not found"}
        assert nonexistent_response.json() == {"detail": "Argument not found"}
