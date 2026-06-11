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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.commands.ingest import _validate_url, run_ingest


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
    """Create a mock Path("data/pdfs") that writes to tmp_path."""
    mock_pdf_dir = MagicMock()
    mock_pdf_dir.mkdir = MagicMock()

    mock_pdf_path = MagicMock()
    mock_pdf_path.exists.return_value = exists
    mock_pdf_path.write_bytes = MagicMock()
    mock_pdf_path.__str__ = MagicMock(return_value=str(tmp_path / "14-556-q1.pdf"))

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
    Running ingest twice with the same primary docket creates exactly 1 Case row.

    Verifies idempotency: SELECT-first prevents duplicate case rows when ingest is re-run.

    Requires DATABASE_URL.
    """
    from sqlalchemy import select

    from api.models.models import Case

    args = argparse.Namespace(
        url="https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf",
        primary_docket="14-556",
        dockets=[],
        case_name="Obergefell v. Hodges",
        argued_date="2015-04-28",
        question=1,
    )

    session_cm = _make_session_cm(async_session)

    # Run ingest twice with the same arguments
    for _ in range(2):
        with (
            patch("pipeline.commands.ingest.httpx.AsyncClient", return_value=_make_mock_client()),
            patch("pipeline.commands.ingest.get_session", new=session_cm),
            patch("pipeline.commands.ingest.Path", return_value=_make_mock_path(tmp_path)),
        ):
            await run_ingest(args)

    result = await async_session.execute(
        select(Case).where(Case.docket_number == "14-556")
    )
    cases = result.scalars().all()
    assert len(cases) == 1, (
        f"Expected exactly 1 Case row for 14-556 after 2 ingest runs, "
        f"got {len(cases)} — idempotency failure"
    )
