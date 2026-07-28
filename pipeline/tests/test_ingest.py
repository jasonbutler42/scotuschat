"""
Unit tests for the pipeline ingest command.

Test categories:
    1. URL validation (no DB required) — test_url_validation_*
    2. DB record creation (requires DATABASE_URL) — test_ingest_*
    3. Consolidated dockets M:M join (requires DATABASE_URL) — test_consolidated_dockets
    4. Idempotency (requires DATABASE_URL) — test_ingest_idempotent

DB-dependent tests skip gracefully when DATABASE_URL is not configured
(via the conftest.py test_db_url / async_session fixtures).
"""

import argparse
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.domain.docket_values import DOCKET_VALUE_MAX_LENGTH
from pipeline.commands.ingest import (
    _run_ingest_inner,
    _validate_docket_value,
    _validate_url,
    run_ingest,
)


def test_ingest_duplicate_path_uses_named_constraint_classifier():
    source = inspect.getsource(_run_ingest_inner)
    assert "is_argument_pair_violation(exc)" in source
    assert "except IntegrityError as exc" in source
    assert "raise\n" in source


# ===========================================================================
# URL validation tests — NO database required
# These tests call _validate_url() directly; they never touch the DB or HTTP.
# ===========================================================================


def test_url_validation_rejects_non_scotus():
    """
    URL validation must reject URLs from non-supremecourt.gov hosts.

    This verifies SSRF mitigation (T-03-01): the URL host is checked before
    any httpx call. ValueError with "supremecourt.gov" in the message is expected.

    No database required.
    """
    with pytest.raises(ValueError, match="supremecourt.gov"):
        _validate_url("https://evil.com/transcript.pdf")


def test_url_validation_rejects_http():
    """
    URL validation must reject http:// URLs (only https:// is accepted).

    SSRF mitigation requires HTTPS. ValueError must be raised for any non-https scheme.

    No database required.
    """
    with pytest.raises(ValueError):
        _validate_url("http://www.supremecourt.gov/oral_arguments/transcript.pdf")


def test_url_validation_rejects_file_scheme():
    """
    URL validation must reject file:// URLs (local file read attempt).

    No database required.
    """
    with pytest.raises(ValueError):
        _validate_url("file:///etc/passwd")


def test_url_validation_rejects_subdomain_spoofing():
    """
    Subdomain spoofing must be rejected (e.g., supremecourt.gov.evil.com).

    The endswith("supremecourt.gov") check correctly rejects
    "supremecourt.gov.evil.com" because netloc ends with "evil.com".

    No database required.
    """
    with pytest.raises(ValueError, match="supremecourt.gov"):
        _validate_url("https://supremecourt.gov.evil.com/transcript.pdf")


def test_url_validation_accepts_valid_scotus_url():
    """
    A valid https://www.supremecourt.gov/... URL must pass validation without error.

    No database required.
    """
    # Must not raise
    _validate_url(
        "https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf"
    )


def test_url_validation_accepts_bare_domain():
    """
    A URL with bare supremecourt.gov (no www subdomain) must pass validation.

    No database required.
    """
    # Must not raise
    _validate_url("https://supremecourt.gov/oral_arguments/transcript.pdf")


# ===========================================================================
# Docket path-component guard tests (G-38-6) — NO database required
# These tests call _validate_docket_value() directly; the pipeline-side
# second enforcement point independent of api.routers.admin's boundary check.
# ===========================================================================


@pytest.mark.parametrize(
    "docket",
    [
        pytest.param("/etc/passwd", id="posix-absolute-path"),
        pytest.param("C:\\Windows\\evil.pdf", id="windows-drive-path"),
        pytest.param("../../../tmp/evil", id="traversal-path"),
        pytest.param("..", id="bare-double-dot"),
        pytest.param("14/556", id="forward-slash"),
        pytest.param("14\\556", id="backslash"),
        pytest.param('14-556"', id="double-quote"),
        pytest.param("x" * (DOCKET_VALUE_MAX_LENGTH + 1), id="over-length"),
    ],
)
def test_docket_guard_rejects_path_hazards(docket):
    """
    Every path-hazard docket class must raise ValueError before it ever
    reaches pdf_filename or case_slug construction.

    No database required.
    """
    with pytest.raises(ValueError):
        _validate_docket_value(docket, "test context")


@pytest.mark.parametrize(
    "docket",
    ["22-915", "14-556", "1955-71", "22O141", "job-1120", "bananas"],
)
def test_docket_guard_accepts_real_shapes(docket):
    """
    No-regression coverage: real docket shapes and the server-generated
    job-{id} fallback must all pass the guard unchanged.

    No database required.
    """
    # Must not raise
    _validate_docket_value(docket, "test context")


def test_docket_containment_rejects_traversal_join():
    """
    Path("data/pdfs") joined with a traversal filename must resolve outside
    the base directory — the exact join the module performs before its
    containment assertion.

    Filesystem-read-only: resolve()/compare only, writes nothing.
    """
    pdf_dir = Path("data/pdfs")
    pdf_path = pdf_dir / "../../../../tmp/evil-q1.pdf"

    resolved_pdf_dir = pdf_dir.resolve()
    resolved_pdf_path = pdf_path.resolve()

    assert resolved_pdf_path.parent != resolved_pdf_dir


def test_docket_containment_rejects_absolute_join():
    """
    Path("data/pdfs") joined with an absolute-path filename must resolve
    outside the base directory — pathlib's `/` operator silently discards
    the left operand when the right operand is absolute.

    Filesystem-read-only: resolve()/compare only, writes nothing.
    """
    pdf_dir = Path("data/pdfs")
    pdf_path = pdf_dir / "/tmp/evil-q1.pdf"

    resolved_pdf_dir = pdf_dir.resolve()
    resolved_pdf_path = pdf_path.resolve()

    assert resolved_pdf_path.parent != resolved_pdf_dir


def test_docket_guard_invoked_inside_run_ingest_inner():
    """
    Static proof that the docket guard helper is actually invoked inside
    _run_ingest_inner — fails loudly if a future refactor removes the call
    while leaving the helper defined.
    """
    source = inspect.getsource(_run_ingest_inner)
    assert "_validate_docket_value(" in source


def test_containment_assertion_present_inside_run_ingest_inner():
    """
    Static proof that the resolved-path containment assertion is present and
    references the resolved pdf directory — fails loudly if a future
    refactor removes the containment check while leaving pdf_dir/pdf_path
    construction intact.
    """
    source = inspect.getsource(_run_ingest_inner)
    assert "resolved_pdf_dir" in source
    assert "resolved_pdf_path" in source
    assert "resolved_pdf_path.parent != resolved_pdf_dir" in source


# ===========================================================================
# DB-dependent tests
# These require DATABASE_URL / TEST_DATABASE_URL configured in .env.
# They skip gracefully via the async_session fixture → test_db_url → pytest.skip.
# ===========================================================================


def _make_mock_client(content: bytes = b"%PDF-1.4 fake"):
    """Create a mock httpx.AsyncClient that returns a fake PDF response."""
    fake_resp = MagicMock()
    fake_resp.content = content
    fake_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=fake_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def _make_mock_path(tmp_path: Path, exists: bool = False):
    """
    Create a mock Path("data/pdfs") that writes to tmp_path.

    .resolve() is mocked on both the directory and the joined file path so
    the G-38-6 containment assertion in ingest.py (resolved_pdf_path.parent
    == resolved_pdf_dir) holds under a mocked Path — without this, both
    .resolve() calls would return unrelated auto-generated MagicMock objects
    that never compare equal, breaking every ingest test that patches Path.
    """
    resolved_dir = (tmp_path / "data" / "pdfs").resolve()

    mock_pdf_dir = MagicMock()
    mock_pdf_dir.mkdir = MagicMock()
    mock_pdf_dir.resolve = MagicMock(return_value=resolved_dir)

    mock_pdf_path = MagicMock()
    mock_pdf_path.exists.return_value = exists
    mock_pdf_path.write_bytes = MagicMock()
    mock_pdf_path.__str__ = MagicMock(return_value=str(tmp_path / "14-556-q1.pdf"))
    mock_pdf_path.resolve = MagicMock(return_value=resolved_dir / "14-556-q1.pdf")

    mock_pdf_dir.__truediv__ = MagicMock(return_value=mock_pdf_path)
    return mock_pdf_dir


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Used to patch pipeline.db.get_session so tests inject the
    test async_session instead of opening a real DB connection.
    """
    from contextlib import asynccontextmanager

    # get_session is called as: async with get_session() as session: ...
    # So we need get_session to be a callable that returns an async context manager.
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.mark.asyncio
async def test_ingest_creates_pipeline_run(async_session, tmp_path):
    """
    Ingest creates exactly 1 PipelineRun row with step='ingest' and status=COMPLETED.

    Requires DATABASE_URL (skipped if not configured via conftest.py test_db_url fixture).
    """
    from sqlalchemy import select

    from api.models.models import PipelineRun, PipelineRunStatus

    args = argparse.Namespace(
        url="https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf",
        primary_docket="14-556",
        dockets=[],
        case_name="Obergefell v. Hodges",
        argued_date="2015-04-28",
        question=1,
        job_id=None,
    )

    with (
        patch("pipeline.commands.ingest.httpx.AsyncClient", return_value=_make_mock_client()),
        patch("pipeline.commands.ingest.get_session", new=_make_session_cm(async_session)),
        patch("pipeline.commands.ingest.Path", return_value=_make_mock_path(tmp_path)),
    ):
        await run_ingest(args)

    result = await async_session.execute(
        select(PipelineRun).where(PipelineRun.step == "ingest")
    )
    runs = result.scalars().all()
    assert len(runs) == 1, f"Expected 1 PipelineRun, got {len(runs)}"
    assert runs[0].status == PipelineRunStatus.COMPLETED
    assert runs[0].step == "ingest"


@pytest.mark.asyncio
async def test_consolidated_dockets(async_session, tmp_path):
    """
    Ingest with 3 consolidated dockets alongside primary docket creates:
    - 4 CaseArgument rows (1 per docket)
    - Exactly 1 row with is_lead=True (the primary docket 14-556)

    Verifies INFRA-02 (M:M case-argument join table for consolidated dockets).

    Requires DATABASE_URL.
    """
    from sqlalchemy import select

    from api.models.models import CaseArgument

    args = argparse.Namespace(
        url="https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf",
        primary_docket="14-556",
        dockets=["14-562", "14-571", "14-574"],
        case_name="Obergefell v. Hodges",
        argued_date="2015-04-28",
        question=1,
        job_id=None,
    )

    with (
        patch("pipeline.commands.ingest.httpx.AsyncClient", return_value=_make_mock_client()),
        patch("pipeline.commands.ingest.get_session", new=_make_session_cm(async_session)),
        patch("pipeline.commands.ingest.Path", return_value=_make_mock_path(tmp_path)),
    ):
        await run_ingest(args)

    result = await async_session.execute(select(CaseArgument))
    links = result.scalars().all()
    assert len(links) == 4, f"Expected 4 CaseArgument rows, got {len(links)}"

    lead_links = [link for link in links if link.is_lead]
    assert len(lead_links) == 1, f"Expected 1 is_lead=True row, got {len(lead_links)}"


@pytest.mark.asyncio
async def test_ingest_idempotent(async_session, tmp_path):
    """
    Running ingest twice with the same primary docket + question reuses the
    existing Case row (SELECT-first) and rejects the duplicate Argument.

    Schema-drift note: this test originally expected the second run_ingest()
    call to complete silently. Current ingest.py (D-01) enforces the
    UNIQUE(source_docket, question_number) constraint on Argument by
    attempting a fresh INSERT and converting the resulting IntegrityError
    into a ValueError("Duplicate argument: ...") — it does NOT silently
    no-op on a duplicate docket+question the way Case creation does. The
    dedup guarantee this test verifies is now "duplicate submissions are
    rejected with a clear error", not "duplicate submissions are silently
    absorbed" — Case-level idempotency (SELECT-first) is unchanged and still
    holds because the Case row is looked up/reused before the Argument
    insert is attempted.

    Requires DATABASE_URL.
    """
    from sqlalchemy import select

    from api.models.models import Argument, Case

    args = argparse.Namespace(
        url="https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf",
        primary_docket="14-556",
        dockets=[],
        case_name="Obergefell v. Hodges",
        argued_date="2015-04-28",
        question=1,
        job_id=None,
    )

    session_cm = _make_session_cm(async_session)

    with (
        patch("pipeline.commands.ingest.httpx.AsyncClient", return_value=_make_mock_client()),
        patch("pipeline.commands.ingest.get_session", new=session_cm),
        patch("pipeline.commands.ingest.Path", return_value=_make_mock_path(tmp_path)),
    ):
        # First run: creates the Case + Argument rows.
        await run_ingest(args)

        # Second run with identical primary_docket + question: Case is reused
        # (SELECT-first), but the Argument insert hits the UNIQUE constraint
        # and ingest.py raises ValueError rather than silently succeeding.
        # `_make_session_cm` never commits (unlike the real get_session()),
        # so both calls share one transaction — wrap the expected-to-fail
        # second call in a SAVEPOINT so its rollback doesn't also undo the
        # first call's Case/Argument rows.
        with pytest.raises(ValueError, match="Duplicate argument"):
            async with async_session.begin_nested():
                await run_ingest(args)

    result = await async_session.execute(
        select(Case).where(Case.docket_number == "14-556")
    )
    cases = result.scalars().all()
    assert len(cases) == 1, (
        f"Expected exactly 1 Case row for 14-556 after 2 ingest attempts, "
        f"got {len(cases)} — Case-level idempotency failure"
    )

    result_args = await async_session.execute(
        select(Argument).where(
            Argument.source_docket == "14-556", Argument.question_number == 1
        )
    )
    arguments = result_args.scalars().all()
    assert len(arguments) == 1, (
        f"Expected exactly 1 Argument row for 14-556 Q1 after 2 ingest attempts, "
        f"got {len(arguments)} — duplicate rejection failure"
    )
