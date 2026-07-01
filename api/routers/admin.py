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
import os
import re
import urllib.parse
from urllib.parse import quote

import httpx
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse, RedirectResponse, Response

from api.core.config import settings
from api.core.database import get_db
from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, PipelineRun
from api.schemas.admin_jobs import (
    AdminJobResponse,
    PersonCreate,
    PersonResponse,
    ResolveRequest,
)
from api.schemas.admin_arguments import (
    ArgumentDetail,
    ArgumentListItem,
    ArgumentUpdate,
    MetadataUpdate,
    ParticipantSideUpdate,
)
from api.schemas.admin_people import (
    MergePreview,
    MergeRequest,
    ParticipantItem,
    PersonDetail,
    PersonListItem,
    PersonUpdate,
    RoleCreate,
    RoleResponse,
)
from api.services import admin_arguments as arguments_service
from api.services import admin_jobs as jobs_service
from api.services import admin_people as people_service
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
    primary_docket: Optional[str] = Form(None),  # CR-01: pass through to ingest for D-01 deduplication
    question_number: int = Form(1),              # CR-01: pass through to ingest for D-01 deduplication
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
        # CR-01: include --primary-docket and --question so D-01 deduplication fires
        ingest_args = ["--url", pdf_url, "--question", str(question_number)]
        if primary_docket:
            ingest_args += ["--primary-docket", primary_docket]
        spawn_pipeline_step("ingest", job.id, ingest_args)
        return job  # type: ignore[return-value]

    elif pdf_file is not None:
        # Upload mode: validate content type (T-07-04)
        if pdf_file.content_type != "application/pdf":
            raise HTTPException(
                status_code=422,
                detail="Uploaded file must be a PDF (application/pdf).",
            )
        # WR-04: content_type is client-supplied — verify PDF magic bytes as a
        # second layer so a non-PDF payload with a spoofed content-type is rejected.
        header = await pdf_file.read(4)
        await pdf_file.seek(0)
        if header != b"%PDF":
            raise HTTPException(status_code=422, detail="Uploaded file must be a PDF.")

        file_bytes = await pdf_file.read()
        job = await jobs_service.create_job(
            db,
            spaces_key=None,
            original_filename=pdf_file.filename,
        )

        if settings.do_spaces_bucket:
            # Object storage configured — upload and pass the key to ingest.
            key = f"uploads/{job.id}.pdf"
            loop = asyncio.get_running_loop()
            # WR-06: wrap upload in try/except so a storage failure marks the job
            # FAILED rather than leaving an orphaned PENDING job row with no subprocess.
            try:
                await loop.run_in_executor(
                    None,
                    spaces_service.upload_pdf_to_spaces,
                    file_bytes,
                    key,
                )
            except Exception as upload_exc:
                await db.execute(
                    update(AdminJob)
                    .where(AdminJob.id == job.id)
                    .values(
                        status=AdminJobStatus.FAILED,
                        error_message=f"Storage upload failed: {upload_exc}",
                    )
                    .execution_options(synchronize_session=False)
                )
                await db.commit()
                raise HTTPException(
                    status_code=502, detail="File upload failed. Please try again."
                ) from upload_exc
            await db.execute(
                update(AdminJob)
                .where(AdminJob.id == job.id)
                .values(spaces_key=key)
                .execution_options(synchronize_session=False)
            )
            await db.commit()
            await db.refresh(job)
            # CR-01: pass --primary-docket and --question through upload path too
            spaces_ingest_args = ["--spaces-key", key, "--question", str(question_number)]
            if primary_docket:
                spaces_ingest_args += ["--primary-docket", primary_docket]
            spawn_pipeline_step("ingest", job.id, spaces_ingest_args)
        else:
            # No object storage configured — save locally for dev use.
            uploads_dir = Path("data/uploads")
            uploads_dir.mkdir(parents=True, exist_ok=True)
            local_path = uploads_dir / f"{job.id}.pdf"
            local_path.write_bytes(file_bytes)
            await db.commit()
            await db.refresh(job)
            # CR-01: pass --primary-docket and --question through local-file path too
            local_ingest_args = ["--local-file", str(local_path.resolve()), "--question", str(question_number)]
            if primary_docket:
                local_ingest_args += ["--primary-docket", primary_docket]
            spawn_pipeline_step("ingest", job.id, local_ingest_args)

        return job  # type: ignore[return-value]

    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a PDF URL or a file.",
        )


@router.get("/jobs", response_model=list[AdminJobResponse])
async def list_jobs(
    incomplete: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[AdminJobResponse]:
    """Return the 10 most recent pipeline jobs, newest first.

    Query param:
    - incomplete=false (default): return all jobs regardless of status
    - incomplete=true: return only PAUSED and FAILED jobs (require operator action, PIPE-20)
    """
    return await jobs_service.list_jobs(db, limit=10, incomplete=incomplete)  # type: ignore[return-value]


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


@router.get("/jobs/{job_id}/pdf")
async def get_job_pdf(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve the source PDF for a pipeline job.

    Branches on job.spaces_key FIRST (Pitfall 2 — spaces_key short-circuit):
    - Spaces-backed (spaces_key set): 302 redirect to a pre-signed DO Spaces URL
      with 15-minute TTL. The redirect is generated synchronously via boto3 and
      wrapped in run_in_executor so it does not block the event loop.
    - Disk-backed (no spaces_key): stream the PDF from PipelineRun.pdf_path via
      FileResponse with Content-Disposition: inline.

    Auth: inherited from router-level verify_admin_token dependency (T-17-01 mitigated).
    The route return annotation is Response with NO response_model — the handler
    returns either RedirectResponse or FileResponse, not a Pydantic model (Pitfall 6).

    404 raised for: unknown job, missing ingest run, missing pdf_path.
    """
    job = await jobs_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.spaces_key:
        # Spaces-backed: generate a pre-signed URL and redirect (302)
        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None,
            spaces_service.generate_pdf_presigned_url,
            job.spaces_key,
        )
        return RedirectResponse(url=url, status_code=302)
    else:
        # Disk-backed: read pdf_path from the ingest PipelineRun row
        run_id = await jobs_service.get_run_id_for_step(db, job_id, "ingest")
        if run_id is None:
            raise HTTPException(status_code=404, detail="PDF not available")
        run_result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = run_result.scalar_one_or_none()
        if run is None or run.pdf_path is None:
            raise HTTPException(status_code=404, detail="PDF path not recorded")
        if not os.path.isfile(run.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        # Use original_filename if captured; fall back to a derived name (T-17-04:
        # original_filename is display-only, never used as a server-side path)
        filename = job.original_filename or f"argument-{job_id}.pdf"
        # Sanitize filename for Content-Disposition header to prevent header injection.
        # Strip CR, LF, NUL, backslash, and double-quote which break RFC 6266 syntax
        # or allow response splitting (CR-01).
        safe_filename = re.sub(r'[\r\n"\x00-\x1f\\]', '_', filename)
        headers = {
            "Content-Disposition": (
                f"inline; filename=\"{safe_filename}\"; "
                f"filename*=UTF-8''{quote(filename, safe='')}"
            )
        }
        return FileResponse(
            path=run.pdf_path,
            media_type="application/pdf",
            headers=headers,
        )


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


@router.get("/people", response_model=list[PersonListItem])
async def list_people(
    incomplete: bool = False,
    tenure_gaps: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[PersonListItem]:
    """
    Return all Person rows with role name and missing-fields list (PEOPLE-01, PEOPLE-02).

    Query params:
    - incomplete=false (default): return all people
    - incomplete=true: return only people where role_id OR bio_text OR photo_url is NULL
    - tenure_gaps=true: return only bench speakers with at least one argued_date outside
      all their CourtTenure windows (D-15, Phase 15)

    PersonListItem is a superset of the old PersonResponse (adds role_id + missing),
    so Phase 7 typeahead consumers (which read id/full_name/role_name) still work.
    """
    people = await people_service.list_people(db, incomplete=incomplete, tenure_gaps=tenure_gaps)
    return [PersonListItem(**p) for p in people]


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
    try:
        person = await jobs_service.create_person_for_job(db, job_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return person  # type: ignore[return-value]


@router.get("/people/{person_id}", response_model=PersonDetail)
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> PersonDetail:
    """
    Return full person data for the edit form (PEOPLE-03, D-07, D-08).

    Includes all tenure rows for the person ordered by start_date.
    Returns 404 if the person does not exist (T-08-IDOR).
    """
    person = await people_service.get_person_detail(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**person)


@router.patch("/people/{person_id}", response_model=PersonDetail)
async def update_person(
    person_id: int,
    body: PersonUpdate,
    db: AsyncSession = Depends(get_db),
) -> PersonDetail:
    """
    Update a person's name, role, bio, photo, and tenure rows (PEOPLE-03, D-09).

    Mass-assignment guard: PersonUpdate ONLY exposes full_name, role_id, bio_text,
    photo_url, tenures — no other Person columns can be set (T-08-MASS).
    Returns 404 if the person does not exist (T-08-IDOR).
    Returns 422 if a tenure date string is malformed (T-08-DATE).
    """
    try:
        updated = await people_service.update_person(db, person_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**updated)


@router.post("/people/{person_id}/photo", response_model=PersonDetail)
async def upload_person_photo(
    person_id: int,
    photo_file: Optional[UploadFile] = File(None),
    photo_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> PersonDetail:
    """
    Upload or set a photo for a person (PADM-01).

    File path (D-03 file-takes-precedence): validates content_type (first gate)
    and Pillow Image.open/verify (second gate, server-side truth). Non-images → 422.
    URL path: stores the supplied URL directly.
    Returns 422 if neither a file nor a URL is provided.
    Returns 404 if the person does not exist (T-12-IDOR).

    Security (T-12-UPLOAD): two-gate image validation mirrors existing PDF magic-byte
    pattern. Server-derives filename from person_id + validated format — never from the
    client-supplied filename (T-12-PATHTRAVERSAL).
    Auth inherited from router-level dependency (T-12-AUTH).
    """
    if photo_file is not None:
        # First gate: content_type is client-supplied (spoofable) — fast reject
        if not (photo_file.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=422,
                detail="Uploaded file must be an image.",
            )
        file_bytes = await photo_file.read()
        # Second gate: Pillow server-side truth
        # CRITICAL (Pitfall 2): read img.format BEFORE calling img.verify()
        # because verify() exhausts the image object — no attributes readable after.
        try:
            with Image.open(BytesIO(file_bytes)) as img:
                img_format = img.format  # must read before verify()
                img.verify()
        except (UnidentifiedImageError, Exception):
            raise HTTPException(
                status_code=422,
                detail="Uploaded file is not a valid image.",
            )
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        ext = ext_map.get(img_format or "", "jpg")
        content_type = photo_file.content_type or f"image/{ext}"
        result = await people_service.upload_photo(db, person_id, file_bytes, ext, content_type)
    elif photo_url is not None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(photo_url, follow_redirects=True)
                r.raise_for_status()
                file_bytes = r.content
        except Exception:
            raise HTTPException(status_code=422, detail="Could not fetch image from URL.")
        # Same two-gate Pillow check as the file-upload path (Pitfall 2: read format before verify)
        try:
            with Image.open(BytesIO(file_bytes)) as img:
                img_format = img.format
                img.verify()
        except (UnidentifiedImageError, Exception):
            raise HTTPException(status_code=422, detail="URL does not point to a valid image.")
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        ext = ext_map.get(img_format or "", "jpg")
        content_type = f"image/{ext}"
        result = await people_service.upload_photo(db, person_id, file_bytes, ext, content_type)
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a file or a URL.",
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**result)


@router.get("/people/{person_id}/merge-preview", response_model=MergePreview)
async def get_merge_preview(
    person_id: int,
    target_id: int,
    db: AsyncSession = Depends(get_db),
) -> MergePreview:
    """
    Return transfer counts for a prospective merge (PADM-04).

    target_id is accepted as a query param for the frontend contract, but counts
    derive from the source (person_id) — per Plan 01 D-09.
    Returns 404 if the source person does not exist (T-12-IDOR).
    Auth inherited from router-level dependency (T-12-AUTH).
    """
    counts = await people_service.get_merge_preview(db, person_id)
    if counts is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return MergePreview(**counts)


@router.post("/people/{person_id}/merge", response_model=PersonDetail)
async def merge_person(
    person_id: int,
    body: MergeRequest,
    db: AsyncSession = Depends(get_db),
) -> PersonDetail:
    """
    Merge source person (person_id) into target person (body.target_id) (PADM-03).

    Transfers all FK rows from source to target in a single atomic transaction,
    then deletes the source person. Returns the updated target PersonDetail.
    Returns 422 on self-merge (T-12-SELF — ValueError from service → HTTPException 422).
    Returns 404 if either person does not exist (T-12-IDOR).
    Auth inherited from router-level dependency (T-12-AUTH).
    """
    try:
        result = await people_service.merge_people(db, person_id, body.target_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**result)


@router.delete("/people/{person_id}", status_code=200)
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a person only if they have no associated FK rows (PADM-02).

    Returns 200 + {"deleted": True} on success.
    Returns 404 if the person does not exist (T-12-IDOR).
    Returns 409 if the person has associated records (T-12-ORPHAN — server-side
    COUNT is authoritative; client disabled-state is defense-in-depth only, D-06).
    Auth inherited from router-level dependency (T-12-AUTH).
    """
    result = await people_service.delete_person_if_orphan(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if result is False:
        raise HTTPException(
            status_code=409,
            detail="Person has associated records and cannot be deleted.",
        )
    return {"deleted": True}


@router.get("/arguments", response_model=list[ArgumentListItem])
async def list_arguments(
    db: AsyncSession = Depends(get_db),
) -> list[ArgumentListItem]:
    """
    Return all arguments with lead case metadata, sorted argued_date DESC (D-01).

    One row per argument — consolidated dockets are not shown here (see detail endpoint).
    """
    args = await arguments_service.list_arguments(db)
    return [ArgumentListItem(**a) for a in args]


@router.get("/arguments/check-duplicate")
async def check_duplicate_argument(
    docket: str,
    question: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    JS preflight: check if (source_docket, question_number) already exists (D-04, Phase 19).

    Returns 200 always — absence of a match is a valid response.
    Response: {"exists": bool, "argument_id": int | null}.
    Auth inherited at router level (T-19-03-04).

    CRITICAL ordering note (T-19-03-05): this literal route MUST be registered
    before GET /arguments/{argument_id} so FastAPI resolves the literal segment
    "check-duplicate" first rather than consuming it as the argument_id param.
    """
    return await arguments_service.check_duplicate_argument(db, docket, question)


@router.get("/arguments/{argument_id}", response_model=ArgumentDetail)
async def get_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArgumentDetail:
    """
    Return full argument data for the edit form (D-02, D-10).

    Includes lead case fields (case_name, docket_number, slug) and a
    consolidated_dockets list for read-only display.
    Returns 404 if the argument does not exist (T-11-IDOR).
    """
    detail = await arguments_service.get_argument_detail(db, argument_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentDetail(**detail)


@router.patch("/arguments/{argument_id}", response_model=ArgumentDetail)
async def update_argument(
    argument_id: int,
    body: ArgumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> ArgumentDetail:
    """
    Update an argument's argued_date and its lead case's case_name / docket_number (D-02).

    Mass-assignment guard: ArgumentUpdate ONLY exposes case_name, docket_number,
    argued_date — published_at and slug are never writable via PATCH (T-11-MASS).
    Returns 404 if the argument does not exist (T-11-IDOR).
    Returns 422 if argued_date is malformed, or if slug/docket collision detected
    (T-11-SLUG, T-11-DOCKET). The detail string carries "slug_collision" or
    "docket_collision" so the SvelteKit layer can display the specific error message.
    """
    try:
        updated = await arguments_service.update_argument(db, argument_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentDetail(**updated)


@router.post("/arguments/{argument_id}/publish", response_model=ArgumentDetail)
async def publish_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArgumentDetail:
    """
    Stamp published_at = now(), making the argument publicly visible (D-07, D-08).

    Returns 404 if the argument does not exist (T-11-IDOR).
    Returns 422 if resolved_at IS NULL (T-11-PUBGATE — backend enforces this guard
    independently of the UI; a direct API call cannot publish an unresolved argument).
    Returns 422 if already published.
    """
    try:
        result = await arguments_service.publish_argument(db, argument_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentDetail(**result)


@router.post("/arguments/{argument_id}/unpublish", response_model=ArgumentDetail)
async def unpublish_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArgumentDetail:
    """
    Clear published_at, hiding the argument from the public site (D-07, D-08).

    Returns 404 if the argument does not exist (T-11-IDOR).
    Returns 422 if the argument is not currently published.
    """
    try:
        result = await arguments_service.unpublish_argument(db, argument_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentDetail(**result)


@router.patch("/arguments/{argument_id}/metadata")
async def update_argument_metadata(
    argument_id: int,
    body: MetadataUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Save operator-reviewed metadata from job detail page (D-15, Phase 19).

    Updates Argument.argued_date, Argument.source_docket, and lead Case.case_name.
    Auth inherited at router level (T-19-03-04).

    Returns 404 if the argument does not exist (T-19-03-02 IDOR guard).
    Returns {"success": True} on success.
    """
    result = await arguments_service.update_argument_metadata(db, argument_id, body)
    if result is False:
        raise HTTPException(status_code=404, detail="Argument not found")
    return {"success": True}


@router.delete("/arguments/{argument_id}", status_code=200)
async def delete_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an argument only if it is not published (ADMIN-01).

    Cascades deletion of all dependent rows in FK order:
    utterances → pipeline_runs → argument_participants → case_arguments → argument.
    AdminJob.argument_id rows are NULLed before the argument is deleted (Pitfall 1).

    Returns 200 + {"deleted": True} on success.
    Returns 404 if the argument does not exist (T-21-01-IDOR).
    Returns 409 if argument.status == 'published' (T-21-01-PUB — server-side guard;
    client disabled state is defense-in-depth only).

    Auth inherited from router-level verify_admin_token dependency (T-21-01-AUTH).
    argument_id is typed int — FastAPI validates path param (T-21-01-IDOR, V5).

    ORDERING NOTE: This route is placed after all literal-path /arguments/* routes
    (check-duplicate, publish, unpublish, metadata) so the literal segments are
    resolved before the {argument_id} parameterized path (consistent with the
    ordering note at the check-duplicate route).
    """
    result = await arguments_service.delete_argument(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    if result is False:
        raise HTTPException(
            status_code=409,
            detail="Published arguments cannot be deleted. Unpublish first.",
        )
    return {"deleted": True}


@router.post("/roles", status_code=201, response_model=RoleResponse)
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """
    Find-or-create a role by name (D-10, inline role creation from the edit form).

    Returns 201 + RoleResponse whether the role was just created or already existed.
    """
    role = await people_service.create_role(db, body.name)
    return RoleResponse(**role)


@router.get("/jobs/{job_id}/participants", response_model=list[ParticipantItem])
async def list_participants(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ParticipantItem]:
    """
    Return resolved participants for the argument linked to this job (D-02, PEOPLE-04).

    Only includes participants where person_id IS NOT NULL (resolved by the pipeline).
    Returns 404 if the job does not exist or has no argument linked yet.
    """
    participants = await people_service.list_participants_for_job(db, job_id)
    if participants is None:
        raise HTTPException(status_code=404, detail="Job not found or has no argument")
    return [ParticipantItem(**p) for p in participants]


# ---------------------------------------------------------------------------
# Phase 15: Approve, Re-run, and Participant-Side endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/approve", response_model=AdminJobResponse)
async def approve_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """
    Approve a pipeline job — transitions argument from pipeline to draft state (D-09).

    Sets argument.status = 'draft' and stamps argument.resolved_at = now().
    Sets admin_job.status = COMPLETED.

    Returns 422 on:
      - Job not found
      - Job has no linked argument
      - Argument already approved (double-approve guard, T-15-02-RACE)

    Auth inherited from router-level verify_admin_token dependency (T-15-02-AUTH).
    """
    try:
        result = await jobs_service.approve_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result  # type: ignore[return-value]


@router.post("/jobs/{job_id}/rerun", status_code=202, response_model=AdminJobResponse)
async def rerun_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """
    Re-run an existing pipeline job using the same PDF source (D-10).

    Creates a NEW AdminJob and immediately spawns the ingest subprocess for the
    new job.  The existing draft/published argument is unaffected — the new run
    goes through the pipeline state independently.

    Returns 202 + new AdminJobResponse so the caller can redirect to the new job.
    Returns 422 if the original job is not found.

    Auth inherited from router-level verify_admin_token dependency (T-15-02-AUTH).
    """
    try:
        new_job = await jobs_service.rerun_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Spawn ingest for the new job — same pattern as POST /api/admin/jobs
    if new_job.spaces_key:
        spawn_pipeline_step("ingest", new_job.id, ["--spaces-key", new_job.spaces_key])
    elif new_job.pdf_url:
        spawn_pipeline_step("ingest", new_job.id, ["--url", new_job.pdf_url])

    return new_job  # type: ignore[return-value]


@router.patch(
    "/arguments/{argument_id}/participants/{participant_id}",
    response_model=dict,
)
async def update_participant_side(
    argument_id: int,
    participant_id: int,
    body: ParticipantSideUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update argument_participants.side for a specific participant (ROLE-03).

    IDOR guard (T-15-02-IDOR): the participant must belong to the specified
    argument — a cross-argument update attempt returns 404.

    Mass-assignment guard (T-15-02-MASS): only ``side`` is writable via this
    endpoint (ParticipantSideUpdate exposes only that field).

    BENCH guard (T-15-02-BENCH): returns 422 if side == BENCH — operators
    cannot set advocate participants to BENCH via this endpoint.

    Returns 422 on side == BENCH.
    Returns 404 if the participant is not found under this argument.
    Auth inherited from router-level verify_admin_token dependency (T-15-02-AUTH).
    """
    try:
        result = await arguments_service.update_participant_side(
            db, argument_id, participant_id, body.side
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=404, detail="Participant not found for this argument"
        )
    return result
