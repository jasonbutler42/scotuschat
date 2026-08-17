"""Focused public-contract regressions for Phase 35 capability retirement."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _admin_headers() -> dict[str, str]:
    from api.core.config import settings

    return {"X-Admin-Token": settings.admin_token}


@pytest_asyncio.fixture
async def client():
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_authenticated_retired_rerun_route_returns_framework_404(client: AsyncClient) -> None:
    response = await client.post("/api/admin/jobs/1/rerun", headers=_admin_headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_job_service_persists_supported_source_fields() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import create_job

    async with AsyncSessionLocal() as db:
        job = await create_job(
            db,
            pdf_url="https://www.supremecourt.gov/oral_arguments/argument_audio/23-1.pdf",
            original_filename="source.pdf",
            source_dockets=["23-1", "23-2"],
        )
        job_id = job.id
    try:
        async with AsyncSessionLocal() as db:
            stored = await db.get(AdminJob, job_id)
            assert stored is not None
            assert stored.pdf_url == "https://www.supremecourt.gov/oral_arguments/argument_audio/23-1.pdf"
            assert stored.original_filename == "source.pdf"
            assert stored.source_dockets == ["23-1", "23-2"]
            assert stored.status == AdminJobStatus.PENDING
            assert stored.current_step == AdminJobStep.INGEST
    finally:
        async with AsyncSessionLocal() as db:
            stored = await db.get(AdminJob, job_id)
            if stored is not None:
                await db.delete(stored)
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_ordinary_create_route_spawns_exactly_one_ingest(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import AdminJob
    from api.routers import admin as admin_router

    calls: list[tuple[str, int, list[str]]] = []
    monkeypatch.setattr(admin_router, "spawn_pipeline_step", lambda step, job_id, args: calls.append((step, job_id, args)))
    pdf_url = "https://www.supremecourt.gov/oral_arguments/argument_audio/23-1.pdf"
    response = await client.post(
        "/api/admin/jobs",
        headers=_admin_headers(),
        data={"pdf_url": pdf_url, "primary_docket": "23-1", "source_dockets": "23-2", "question_number": "2"},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    assert calls == [("ingest", job_id, ["--url", pdf_url, "--question", "2", "--primary-docket", "23-1", "--dockets", "23-2"])]
    async with AsyncSessionLocal() as db:
        stored = await db.get(AdminJob, job_id)
        if stored is not None:
            await db.delete(stored)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_failed_recovery_neighbor_remains_available(client: AsyncClient) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep

    async with AsyncSessionLocal() as db:
        job = AdminJob(status=AdminJobStatus.FAILED, current_step=AdminJobStep.PARSE, error_message="unsupported transcript layout")
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id
    try:
        response = await client.get(f"/api/admin/jobs/{job_id}/failed-recovery", headers=_admin_headers())
        assert response.status_code == 200
        body = response.json()
        assert body["step"] == "parse"
        assert "transcript" in body["guidance"].lower()
        assert "new run" in body["guidance"].lower()
        assert body["href"] == "/admin/pipeline/"
        assert body["raw_error"] == "unsupported transcript layout"
    finally:
        async with AsyncSessionLocal() as db:
            stored = await db.get(AdminJob, job_id)
            if stored is not None:
                await db.delete(stored)
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_disk_backed_job_pdf_returns_exact_stored_bytes(client: AsyncClient, tmp_path) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
    )

    pdf_bytes = b"%PDF-1.4\nphase-35-source\n%%EOF\n"
    pdf_path = tmp_path / "server-only-name.pdf"
    pdf_path.write_bytes(pdf_bytes)
    async with AsyncSessionLocal() as db:
        argument = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(argument)
        await db.flush()
        run = ImportRun(
            argument_id=argument.id,
            step="ingest",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.NORMALIZED,
            pdf_path=str(pdf_path),
        )
        db.add(run)
        job = AdminJob(status=AdminJobStatus.COMPLETED, current_step=AdminJobStep.RESOLVE, argument_id=argument.id, original_filename='source "brief".pdf')
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id
        argument_id = argument.id
        run_id = run.id
    try:
        response = await client.get(f"/api/admin/jobs/{job_id}/pdf", headers=_admin_headers())
        assert response.status_code == 200
        assert response.content == pdf_bytes
        assert response.headers["content-type"] == "application/pdf"
        disposition = response.headers["content-disposition"]
        assert 'filename="source _brief_.pdf"' in disposition
        assert "server-only-name" not in disposition
    finally:
        async with AsyncSessionLocal() as db:
            stored_run = await db.get(ImportRun, run_id)
            if stored_run is not None:
                await db.delete(stored_run)
            stored_job = await db.get(AdminJob, job_id)
            if stored_job is not None:
                await db.delete(stored_job)
            stored_argument = await db.get(Argument, argument_id)
            if stored_argument is not None:
                await db.delete(stored_argument)
            await db.commit()
