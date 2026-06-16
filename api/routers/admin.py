"""
FastAPI admin router — Phase 5 foundation for the v1.1 operator admin interface.

Endpoints:
  GET /api/admin/health
    Smoke-test target; verifies the 401 auth dependency is wired correctly.
    Returns {"status": "ok"} when X-Admin-Token matches settings.admin_token.

  POST /api/admin/jobs
    Create a new pipeline job from a supremecourt.gov PDF URL or a file upload.
    Spawns ingest subprocess immediately. Returns 202 + AdminJobResponse.

  GET /api/admin/jobs
    Return the 10 most recent AdminJob rows.

  GET /api/admin/jobs/{job_id}
    Poll endpoint — returns the full AdminJob row. As a side effect, advances
    the job to the next step when the current step is COMPLETED (atomic guard).

  POST /api/admin/jobs/{job_id}/resolve
    Write operator-confirmed speaker aliases and mark the job completed.

  POST /api/admin/jobs/{job_id}/people
    Create a new person inline during discrepancy review (D-13).

Auth:
  All routes are protected via the router-level verify_admin_token dependency
  (injected at APIRouter construction, not per-route). Phase 6 replaces
  verify_admin_token with HMAC session-cookie auth in a single location.

Prefix:
  /api/admin — full prefix (not bare /admin) to avoid collision with
  SvelteKit's /admin/* page routes (D-09).
"""

import asyncio
import hmac
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.database import get_db
from api.models.models import AdminJobStatus, AdminJobStep
from api.schemas.admin_jobs import (
    AdminJobResponse,
    PersonCreate,
    PersonResponse,
    ResolveRequest,
)
from api.services import admin_jobs as jobs_service
from api.services import spaces as spaces_service
from api.services.pipeline_spawn import spawn_pipeline_step


async def verify_admin_token(x_admin_token: str = Header(...)) -> None:
    """
    Throwaway token check — Phase 6 replaces this with HMAC session cookie auth.

    The dependency is injected at the router level so Phase 6 can swap it
    without touching individual route signatures (D-12).

    Security notes (T-05-01, T-05-05):
    - The inbound token value must never be logged or echoed in a response.
    - The settings.admin_token value must never be logged or echoed in a response.
    - The 401 response body is the constant string "Unauthorized" — no token
      information, no timing-revealing detail returned to the client.
    """
    if not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


def _validate_pdf_url(url: str) -> None:
    """
    Validate that the URL is a safe, https supremecourt.gov URL (T-07-01 SSRF mitigation).

    This is defense-in-depth at the route boundary — the pipeline's own
    _validate_url is the second layer. Raises HTTPException 422 on failure.

    Rules:
    - scheme must be 'https'
    - netloc must be exactly 'supremecourt.gov' or end with '.supremecourt.gov'
      (prevents bypass via 'xsupremecourt.gov' which ends with 'supremecourt.gov')
    """
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if parsed.scheme != "https" or not (
        netloc == "supremecourt.gov" or netloc.endswith(".supremecourt.gov")
    ):
        raise HTTPException(
            status_code=422,
            detail="Only https://...supremecourt.gov/... URLs are accepted",
        )


@router.get("/health")
async def admin_health() -> dict:
    """Smoke-test target — verifies the 401 dependency is wired before Phase 7 routes land."""
    return {"status": "ok"}


@router.post("/jobs", status_code=202, response_model=AdminJobResponse)
async def create_job(
    pdf_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """
    Create a new pipeline job and immediately spawn the ingest subprocess.

    Modes:
    - URL mode: pdf_url must be a valid https://...supremecourt.gov/... URL.
      Validated at the route boundary (T-07-01) before any job creation.
    - Upload mode: pdf_file must have content_type 'application/pdf' (T-07-04).
      Bytes are uploaded to DO Spaces; the spaces_key is stored on the job.

    Returns 202 + AdminJobResponse. The job starts in PENDING/INGEST state;
    the ingest subprocess will advance it to RUNNING and then COMPLETED/FAILED.
    """
    if pdf_url is not None:
        # URL mode: validate + create job + spawn ingest
        _validate_pdf_url(pdf_url)
        job = await jobs_service.create_job(db, pdf_url=pdf_url)
        spawn_pipeline_step("ingest", job.id, ["--url", pdf_url])
        return job  # type: ignore[return-value]

    elif pdf_file is not None:
        # Upload mode: validate content type (T-07-04)
        if pdf_file.content_type != "application/pdf":
            raise HTTPException(
                status_code=422,
                detail="Uploaded file must be a PDF (application/pdf).",
            )
        # Create job first to get its id, then upload with the id in the key
        job = await jobs_service.create_job(db, spaces_key=None)
        key = f"uploads/{job.id}.pdf"
        file_bytes = await pdf_file.read()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            spaces_service.upload_pdf_to_spaces,
            file_bytes,
            key,
        )
        # Update the job's spaces_key now that we have it
        from sqlalchemy import update as sa_update
        from api.models.models import AdminJob
        await db.execute(
            sa_update(AdminJob)
            .where(AdminJob.id == job.id)
            .values(spaces_key=key)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        await db.refresh(job)
        spawn_pipeline_step("ingest", job.id, ["--spaces-key", key])
        return job  # type: ignore[return-value]

    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a PDF URL or a file.",
        )


@router.get("/jobs", response_model=list[AdminJobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[AdminJobResponse]:
    """Return the 10 most recent pipeline jobs, newest first."""
    return await jobs_service.list_jobs(db, limit=10)  # type: ignore[return-value]


@router.get("/jobs/{job_id}", response_model=AdminJobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """
    Poll endpoint — return the full AdminJob row and advance the job if ready.

    Step-advance side effect (D-05):
    - If current_step=INGEST and status=COMPLETED: atomically advance to
      PARSE/RUNNING, derive the ingest run-id via get_run_id_for_step, and
      spawn the parse subprocess.
    - If current_step=PARSE and status=COMPLETED: atomically advance to
      RESOLVE/RUNNING, derive the parse run-id, and spawn resolve.

    The run-id is re-derived on every poll from pipeline_runs (PIPE-17) —
    no cached state, so a re-entrant poll after browser close/reopen works.

    NEVER advances a job that is PAUSED, FAILED, or COMPLETED (D-16 guard).
    """
    job = await jobs_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Step-advance side effects — only for forward-moving transitions
    if (
        job.current_step == AdminJobStep.INGEST
        and job.status == AdminJobStatus.COMPLETED
    ):
        won = await jobs_service.try_advance_ingest_to_parse(db, job_id)
        if won:
            run_id = await jobs_service.get_run_id_for_step(db, job_id, "ingest")
            if run_id is not None:
                spawn_pipeline_step("parse", job_id, ["--run-id", str(run_id)])
        # Re-read so the response reflects the new current_step
        job = await jobs_service.get_job(db, job_id)

    elif (
        job.current_step == AdminJobStep.PARSE
        and job.status == AdminJobStatus.COMPLETED
    ):
        won = await jobs_service.try_advance_parse_to_resolve(db, job_id)
        if won:
            run_id = await jobs_service.get_run_id_for_step(db, job_id, "parse")
            if run_id is not None:
                spawn_pipeline_step("resolve", job_id, ["--run-id", str(run_id)])
        # Re-read so the response reflects the new current_step
        job = await jobs_service.get_job(db, job_id)

    # PAUSED, FAILED, COMPLETED — do nothing (terminal for polling)

    return job  # type: ignore[return-value]


@router.post("/jobs/{job_id}/resolve", response_model=AdminJobResponse)
async def resolve_job(
    job_id: int,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """
    Apply operator-confirmed speaker-label mappings to a paused job.

    Calls jobs_service.resolve_job which validates all person_ids BEFORE any
    alias/utterance write (Pitfall 5). A bad person_id raises ValueError which
    is re-raised here as HTTPException 422, leaving the job paused for retry.
    """
    try:
        updated_job = await jobs_service.resolve_job(db, job_id, body.matches)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return updated_job  # type: ignore[return-value]


@router.post("/jobs/{job_id}/people", status_code=201, response_model=PersonResponse)
async def create_person_for_job(
    job_id: int,
    body: PersonCreate,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """
    Create a new person inline during discrepancy review (D-13).

    Used by the "Add new person" flow in the Resolve step card. The created
    person is immediately selectable as the corrected alias for a discrepancy.
    Bio, photo, and tenure dates are Phase 8 (People Editor).
    """
    person = await jobs_service.create_person_for_job(db, job_id, body)
    return person  # type: ignore[return-value]
