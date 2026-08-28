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

        Phase 51 plan 51-02 added two by-slug peer routes
        (GET /arguments/by-slug/{slug}/utterances and .../speakers), each of
        which raises the SAME literal detail string twice (once for "slug
        does not resolve", once for "result is None") — extending the
        byte-identical-404 contract across all four routes rather than
        narrowing it. 2 (original routes) + 4 (two by-slug routes x 2 raise
        sites each) = 6.
        """
        import pathlib
        source_path = pathlib.Path(__file__).parent.parent / "routers" / "arguments.py"
        source = source_path.read_text(encoding="utf-8")

        detail_line = 'raise HTTPException(status_code=404, detail="Argument not found")'
        occurrences = source.count(detail_line)
        assert occurrences == 6, (
            "api/routers/arguments.py must raise the identical "
            f"{detail_line!r} exactly six times — get_utterances, get_speakers, "
            "and their by-slug peers (each raising it twice) (D-01, Phase 51 "
            f"plan 51-02). Found {occurrences} occurrence(s)."
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

    # test_page_server_loader_throws_on_non_ok_and_has_no_publish_branch
    # (Phase 45 BUG-01) DELETED here, not path-updated: Phase 51 plan 51-02
    # moved and rewrote the file this test read
    # (app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts ->
    # app/src/routes/arguments/[slug]/+page.server.ts). CLAUDE.md's Testing
    # Policy bans static source-text contract tests for frontend behavior
    # and requires tests to retire with the behavior they pinned, rather
    # than be re-pointed at a new file path — updating the path here would
    # perpetuate exactly the anti-pattern the policy names. The behavior
    # itself (throw error(res.status, ...) on a non-OK response, no
    # publish-status branch) is preserved verbatim in the new loader and
    # was verified live: a curl against the running dev server confirmed
    # both an unknown slug and a non-published argument 404 through
    # /arguments/{slug} (see 51-02-SUMMARY.md).

class TestPublishOverrideGateSourceLevel:
    """
    Source-level assertions for the two-gate publish + overridable trust gate
    (Phase 48 D-14/D-15/D-20). No live database is required for this class —
    it reuses the module's own _service_function_source_lines AST-extraction
    helper (comment-stripped, so a docstring/comment mentioning either
    string cannot satisfy the assertion).
    """

    def test_resolve_gate_precedes_trust_gate_in_publish_argument(self):
        """
        D-14: the non-overridable resolved_at gate must be evaluated before
        the overridable trust gate, so an incomplete argument is rejected at
        the wall the operator cannot argue with.
        """
        lines = _service_function_source_lines("admin_arguments.py", "publish_argument")
        assert lines, "Could not extract publish_argument() body from api/services/admin_arguments.py"

        resolve_idx = next(
            (i for i, line in enumerate(lines) if "resolve step not yet complete" in line),
            None,
        )
        trust_gate_idx = next(
            (i for i, line in enumerate(lines) if "TrustGateBlocked" in line),
            None,
        )
        assert resolve_idx is not None, (
            "publish_argument() must still raise the resolve-gate ValueError "
            f"(T-11-PUBGATE). Actual body:\n{chr(10).join(lines)}"
        )
        assert trust_gate_idx is not None, (
            "publish_argument() must raise TrustGateBlocked for the UNCERTAIN "
            f"trust gate (D-14/D-20). Actual body:\n{chr(10).join(lines)}"
        )
        assert resolve_idx < trust_gate_idx, (
            "The resolve gate must be evaluated before the trust gate (D-14) "
            f"— found resolve gate at line index {resolve_idx}, trust gate "
            f"at {trust_gate_idx}. Actual body:\n{chr(10).join(lines)}"
        )

    def test_publish_argument_recomputes_tier_before_committing(self):
        """
        The trust tier must be recomputed before the transaction commits, so
        the gate judges a tier consistent with the row's current
        constituents rather than a possibly stale stored value, and so the
        tier update lands atomically with the status/published_at change.
        """
        lines = _service_function_source_lines("admin_arguments.py", "publish_argument")
        assert lines, "Could not extract publish_argument() body from api/services/admin_arguments.py"

        recompute_idx = next(
            (i for i, line in enumerate(lines) if "recompute_argument_tier" in line),
            None,
        )
        commit_idx = next(
            (i for i, line in enumerate(lines) if "db.commit" in line),
            None,
        )
        assert recompute_idx is not None, (
            f"publish_argument() must call recompute_argument_tier(). Actual body:\n{chr(10).join(lines)}"
        )
        assert commit_idx is not None, (
            f"publish_argument() must call db.commit(). Actual body:\n{chr(10).join(lines)}"
        )
        assert recompute_idx < commit_idx, (
            "recompute_argument_tier() must run before db.commit() so the "
            "gate reads a fresh tier and the recompute lands in the same "
            f"transaction as the publish. Actual body:\n{chr(10).join(lines)}"
        )

    def test_unpublish_and_participant_side_update_recompute_before_committing(self):
        """
        D-08: the tier stays live after unpublish and after a participant
        edit too — both call sites recompute before their own commit.
        """
        for function_name in ("unpublish_argument", "update_participant_side"):
            lines = _service_function_source_lines("admin_arguments.py", function_name)
            assert lines, f"Could not extract {function_name}() body from api/services/admin_arguments.py"

            recompute_idx = next(
                (i for i, line in enumerate(lines) if "recompute_argument_tier" in line),
                None,
            )
            commit_idx = next(
                (i for i, line in enumerate(lines) if "db.commit" in line),
                None,
            )
            assert recompute_idx is not None, (
                f"{function_name}() must call recompute_argument_tier() (D-08). "
                f"Actual body:\n{chr(10).join(lines)}"
            )
            assert commit_idx is not None, (
                f"{function_name}() must call db.commit(). Actual body:\n{chr(10).join(lines)}"
            )
            assert recompute_idx < commit_idx, (
                f"{function_name}() must recompute the tier before its own "
                f"commit (D-08). Actual body:\n{chr(10).join(lines)}"
            )


# ---------------------------------------------------------------------------
# DB-gated behavioral coverage — the trust-gate publish/override/audit/
# non-stickiness rules (Phase 48 D-14/D-15/D-16/D-17/D-20, Task 3).
# ---------------------------------------------------------------------------


async def _mark_resolved(argument_id: int) -> None:
    """Stamp resolved_at = now() on an already-seeded argument, in its own
    committed transaction, so a subsequent publish_argument() call clears
    the non-overridable resolve gate (test_trust_recompute._seed_argument
    always seeds resolved_at=None, since that module tests recompute, not
    the publish gate)."""
    import datetime

    from sqlalchemy import update

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Argument)
            .where(Argument.id == argument_id)
            .values(resolved_at=datetime.datetime.now(datetime.timezone.utc))
        )
        await db.commit()


async def _seed_argument_with_lead_case(source, method, utterance_specs, participant_specs=()):
    """
    Wrap test_trust_recompute._seed_argument with a lead Case + CaseArgument
    (unique docket per call), since get_argument_detail — which
    publish_argument's return value delegates to — returns None when no
    lead case exists, and these tests assert on publish_argument's return
    value, not just the raw Argument row.
    """
    import uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import Case, CaseArgument
    from api.tests.test_trust_recompute import _seed_argument

    ids = await _seed_argument(source, method, utterance_specs, participant_specs)
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        case = Case(
            docket_number=f"PG-OVR-{suffix}",
            docket_number_norm=f"pg-ovr-{suffix}",
            case_name="Trust Gate Override Fixture v. Test Harness",
            term_year=2026,
            slug=f"trust-gate-override-fixture-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=ids["argument_id"], is_lead=True))
        await db.commit()
        ids["case_id"] = case.id
    return ids


async def _teardown_argument_with_lead_case(ids: dict) -> None:
    """Delete the status-log rows and lead case this module adds on top of
    test_trust_recompute._teardown_argument's own FK-ordered cleanup —
    ArgumentStatusLog has a NOT NULL FK with no ondelete (Phase 48 D-22), so
    every publish/unpublish call in these tests leaves a row that must be
    removed before the Argument itself can be deleted."""
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusLog, Case, CaseArgument
    from api.tests.test_trust_recompute import _teardown_argument

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentStatusLog).where(
                ArgumentStatusLog.argument_id == ids["argument_id"]
            )
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        if ids.get("case_id") is not None:
            await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.commit()
    await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_publish_blocked_when_resolve_incomplete_even_with_override_reason():
    """
    TRUST-04 unclassified edge: when both gates would fail at once (resolve
    incomplete AND tier uncertain), the non-overridable resolve gate is the
    one that reports — an override reason supplied in that state changes
    nothing (D-14).
    """
    from api.core.database import AsyncSessionLocal
    from api.services.admin_arguments import publish_argument

    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(False, False, "PETITIONER")]
    )
    try:
        # _seed_argument always seeds resolved_at=None — do NOT call
        # _mark_resolved here; that is the point of this test.
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError) as exc_info:
                await publish_argument(
                    db, ids["argument_id"], override_reason="a perfectly good reason"
                )
        assert str(exc_info.value) == "Cannot publish: resolve step not yet complete"
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_publish_blocked_when_uncertain_without_reason():
    """
    D-19/D-20: a blocked publish carries the tier plus a structured
    blocker breakdown — not a bare tier name — and writes nothing.
    """
    from sqlalchemy import func, select

    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument
    from api.services.trust import TrustGateBlocked

    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(False, False, "PETITIONER")]
    )
    try:
        await _mark_resolved(ids["argument_id"])
        async with AsyncSessionLocal() as db:
            with pytest.raises(TrustGateBlocked) as exc_info:
                await publish_argument(db, ids["argument_id"])
        exc = exc_info.value
        assert exc.tier is TrustTier.UNCERTAIN
        assert exc.blockers, "blocked publish must carry a non-empty blocker breakdown (D-19)"
        assert any(
            b["code"] == "unresolved_utterance_speaker" and b["count"] == 1
            for b in exc.blockers
        ), f"expected an unresolved_utterance_speaker blocker with count 1, got {exc.blockers}"

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.published_at is None
            assert arg.status == ArgumentStatusEnum.CANDIDATE
            log_count = (
                await db.execute(
                    select(func.count())
                    .select_from(ArgumentStatusLog)
                    .where(ArgumentStatusLog.argument_id == ids["argument_id"])
                )
            ).scalar()
            assert log_count == 0, "a blocked publish must not write a status-log row"
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
@pytest.mark.parametrize(
    "blank_reason",
    ["   ", "\t\n", " ", "  \t\n"],
    ids=["spaces", "tab-newline", "nbsp", "nbsp-mixed"],
)
async def test_publish_blocked_when_override_reason_is_whitespace_only(blank_reason):
    """
    D-17: a whitespace-only reason (including a non-breaking space, which is
    not visually distinguishable from a real space) is rejected server-side
    after .strip() — distinguishably from the no-reason-at-all case.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument
    from api.services.admin_arguments import publish_argument

    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(False, False, "PETITIONER")]
    )
    try:
        await _mark_resolved(ids["argument_id"])
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError) as exc_info:
                await publish_argument(db, ids["argument_id"], override_reason=blank_reason)
        assert str(exc_info.value) == "blank_override_reason"

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, ids["argument_id"])
            assert arg.published_at is None
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_publish_succeeds_with_override_and_logs_reason_and_tier():
    """
    D-15: a successful override writes its ArgumentStatusLog row with
    override_reason set to the stripped text and trust_tier_at_transition
    set to the tier at that moment.
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument

    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(False, False, "PETITIONER")]
    )
    try:
        await _mark_resolved(ids["argument_id"])
        async with AsyncSessionLocal() as db:
            result = await publish_argument(
                db,
                ids["argument_id"],
                override_reason="  Publishing despite an unresolved speaker for test coverage.  ",
            )
        assert result is not None
        assert result["status"] == ArgumentStatusEnum.PUBLISHED
        assert result["published_at"] is not None

        async with AsyncSessionLocal() as db:
            log_result = await db.execute(
                select(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == ids["argument_id"])
                .order_by(ArgumentStatusLog.id.desc())
            )
            newest = log_result.scalars().first()
            assert newest is not None
            assert newest.status == ArgumentStatusEnum.PUBLISHED
            assert newest.override_reason == "Publishing despite an unresolved speaker for test coverage."
            assert newest.trust_tier_at_transition == TrustTier.UNCERTAIN
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_publish_without_override_leaves_audit_columns_null():
    """
    TRUST-05 unclassified edge: a normal publish of an argument that is NOT
    uncertain succeeds with no reason supplied, and its status-log row
    leaves both override columns NULL — the override path is not
    accidentally mandatory (D-16).
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument

    # A single resolved utterance under (corpus, direct) derives TRUSTED
    # (test_trust_recompute.SINGLE_PROVENANCE_CASES) — not UNCERTAIN.
    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(True, False, "PETITIONER")]
    )
    try:
        await _mark_resolved(ids["argument_id"])
        async with AsyncSessionLocal() as db:
            result = await publish_argument(db, ids["argument_id"])
        assert result is not None
        assert result["status"] == ArgumentStatusEnum.PUBLISHED

        async with AsyncSessionLocal() as db:
            log_result = await db.execute(
                select(ArgumentStatusLog).where(
                    ArgumentStatusLog.argument_id == ids["argument_id"]
                )
            )
            row = log_result.scalars().one()
            assert row.override_reason is None
            assert row.trust_tier_at_transition is None
    finally:
        await _teardown_argument_with_lead_case(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_override_is_not_sticky_across_republish():
    """
    D-16: the override is per publish attempt, never sticky. After an
    override publish, unpublishing and republishing the still-uncertain
    argument is blocked again and requires a fresh reason; each override
    writes its own distinct log row.
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentStatusEnum, ArgumentStatusLog
    from api.services.admin_arguments import publish_argument, unpublish_argument
    from api.services.trust import TrustGateBlocked

    ids = await _seed_argument_with_lead_case(
        "corpus", "direct", utterance_specs=[(False, False, "PETITIONER")]
    )
    try:
        await _mark_resolved(ids["argument_id"])

        async with AsyncSessionLocal() as db:
            await publish_argument(db, ids["argument_id"], override_reason="first override reason")

        async with AsyncSessionLocal() as db:
            await unpublish_argument(db, ids["argument_id"])

        # Still UNCERTAIN, no reason carried over — blocked again.
        async with AsyncSessionLocal() as db:
            with pytest.raises(TrustGateBlocked):
                await publish_argument(db, ids["argument_id"])

        # A fresh, different reason succeeds and writes its own row.
        async with AsyncSessionLocal() as db:
            result = await publish_argument(
                db, ids["argument_id"], override_reason="second, different override reason"
            )
        assert result is not None
        assert result["status"] == ArgumentStatusEnum.PUBLISHED

        async with AsyncSessionLocal() as db:
            log_result = await db.execute(
                select(ArgumentStatusLog)
                .where(
                    ArgumentStatusLog.argument_id == ids["argument_id"],
                    ArgumentStatusLog.override_reason.isnot(None),
                )
                .order_by(ArgumentStatusLog.id.asc())
            )
            override_rows = log_result.scalars().all()
        assert len(override_rows) == 2, (
            "each override publish attempt must write its own distinct log "
            f"row (D-16) — found {len(override_rows)}"
        )
        assert override_rows[0].override_reason == "first override reason"
        assert override_rows[1].override_reason == "second, different override reason"
    finally:
        await _teardown_argument_with_lead_case(ids)


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


@pytest_asyncio.fixture
async def publish_state_arguments():
    """
    Seed one PUBLISHED and one UNPUBLISHED argument, committed, and delete both
    afterwards. Yields ``{"published": <id>, "unpublished": <id>}``.

    Replaces an earlier discover-a-row helper that called `pytest.skip()` when
    the configured DB held no argument of the needed publish state. That was
    written when the suite ran against the shared dev DB, where Phase 41/43 had
    seeded publish-state variety. Once Phase 31/46 moved the suite onto the
    dedicated `TEST_DATABASE_URL` database no such rows existed there, and all
    six live tests in this module skipped silently — the 2026-08-18 cross-phase
    UAT audit (finding N-2) caught 45-VERIFICATION.md citing "TestPublishedGate
    (4 tests, all pass)" as evidence for BUG-01 while the tests were not in fact
    executing. A publish gate is a public-exposure control; its integration
    coverage must not evaporate along with the seed data.

    Seeding commits rather than relying on the rolled-back `db_session` fixture:
    the ASGI client reaches the app through its own `AsyncSessionLocal()`
    session, which cannot see another session's uncommitted rows. This follows
    the seed-commit-then-delete-in-`finally` pattern already used by
    `test_phase44_argument_role_roundtrip.py` and `test_admin_jobs_phase25.py`.
    The rootdir conftest.py's row-count tripwire guards the real dev DB, not
    `TEST_DATABASE_URL`, and every row created here is removed in teardown.

    The PUBLISHED argument needs a linked lead Case:
    `get_argument_with_utterances` returns None (→ 404) when no case is joined,
    which would make the 200 assertions fail for a bare Argument row.
    Utterances are deliberately NOT seeded — with no parse `import_run` the
    service returns an empty utterance list, which is still a 200, and the
    publish gate is what these tests assert.
    """
    from datetime import datetime, timezone

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
    )

    async with AsyncSessionLocal() as db:
        case = Case(
            docket_number="PG-GATE-1",
            docket_number_norm="pg-gate-1",
            case_name="Published Gate Fixture v. Test Harness",
            term_year=2026,
            slug="published-gate-fixture-v-test-harness",
        )
        db.add(case)
        await db.flush()

        published = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            question_number=1,
            published_at=datetime.now(timezone.utc),
        )
        unpublished = Argument(
            status=ArgumentStatusEnum.DRAFT,
            question_number=2,
            published_at=None,
        )
        db.add_all([published, unpublished])
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=published.id, is_lead=True))
        await db.commit()

        case_id = case.id
        published_id = published.id
        unpublished_id = unpublished.id

    try:
        yield {"published": published_id, "unpublished": unpublished_id}
    finally:
        from sqlalchemy import delete

        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(CaseArgument).where(
                    CaseArgument.argument_id.in_([published_id, unpublished_id])
                )
            )
            await db.execute(
                delete(Argument).where(Argument.id.in_([published_id, unpublished_id]))
            )
            await db.execute(delete(Case).where(Case.id == case_id))
            await db.commit()


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

    async def test_unpublished_argument_utterances_returns_404(self, client, publish_state_arguments):
        argument_id = publish_state_arguments["unpublished"]
        response = await client.get(f"/arguments/{argument_id}/utterances")
        assert response.status_code == 404
        assert response.json() == {"detail": "Argument not found"}

    async def test_published_argument_utterances_returns_200(self, client, publish_state_arguments):
        argument_id = publish_state_arguments["published"]
        response = await client.get(f"/arguments/{argument_id}/utterances")
        assert response.status_code == 200

    async def test_unpublished_utterances_404_body_matches_nonexistent_id(self, client, publish_state_arguments):
        """D-01: the 404 for an unpublished argument must be body-identical to
        the 404 for a definitely-nonexistent ID."""
        argument_id = publish_state_arguments["unpublished"]
        unpublished_response = await client.get(f"/arguments/{argument_id}/utterances")
        nonexistent_response = await client.get("/arguments/987654321/utterances")

        assert unpublished_response.status_code == 404
        assert nonexistent_response.status_code == 404
        assert unpublished_response.json() == {"detail": "Argument not found"}
        assert nonexistent_response.json() == {"detail": "Argument not found"}

    async def test_unpublished_argument_speakers_returns_404(self, client, publish_state_arguments):
        """BUG-01/D-02 (Task 2): the speakers endpoint gates on published_at
        exactly like the utterances endpoint."""
        argument_id = publish_state_arguments["unpublished"]
        response = await client.get(f"/arguments/{argument_id}/speakers")
        assert response.status_code == 404
        assert response.json() == {"detail": "Argument not found"}

    async def test_published_argument_speakers_returns_200(self, client, publish_state_arguments):
        argument_id = publish_state_arguments["published"]
        response = await client.get(f"/arguments/{argument_id}/speakers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_unpublished_speakers_404_body_matches_nonexistent_id(self, client, publish_state_arguments):
        """D-01: the 404 for an unpublished argument's speakers must be
        body-identical to the 404 for a definitely-nonexistent ID — the same
        equality property already proven for the utterances endpoint."""
        argument_id = publish_state_arguments["unpublished"]
        unpublished_response = await client.get(f"/arguments/{argument_id}/speakers")
        nonexistent_response = await client.get("/arguments/987654321/speakers")

        assert unpublished_response.status_code == 404
        assert nonexistent_response.status_code == 404
        assert unpublished_response.json() == {"detail": "Argument not found"}
        assert nonexistent_response.json() == {"detail": "Argument not found"}
