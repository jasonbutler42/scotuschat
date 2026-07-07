"""
Pipeline ingest command.

Downloads a transcript PDF from supremecourt.gov (or fetches from DO Spaces)
and creates the following database records:
    - Case row(s) — one per docket number (primary + consolidated)
    - Argument row — one per hearing session. Argument.source_docket is set to
      the primary/first docket (canonical dedup key); Argument.source_dockets
      is set to the full ordered docket list (primary + --dockets).
    - CaseArgument rows — M:M join (one per case, with is_lead=True for primary)
    - PipelineRun row — status=COMPLETED (ingest is synchronous)

SECURITY: URL validation (SSRF mitigation) happens BEFORE any httpx call.
Only https://...supremecourt.gov/... URLs are accepted.

IMMUTABILITY: Downloaded PDFs are never overwritten. If the file already
exists on disk, the download step is skipped (idempotent re-run support).

JOB-AWARE MODE (--job-id set):
    When invoked by the admin UI subprocess runner, --job-id is passed.
    In this mode, ingest writes its own status to admin_jobs:
      - RUNNING at start (with current_step=INGEST)
      - COMPLETED on success (with argument_id set)
      - FAILED on any exception (with error_message)
    FastAPI is a reader only for pipeline progress — the pipeline writes
    its own status directly to PostgreSQL per D-02.

    Required args are relaxed when --job-id is set: --url or --spaces-key
    provide the PDF source; --primary-docket, --case-name, --argued-date
    may be derived from the spaces_key filename if not supplied.

BACKWARD COMPATIBILITY: Running without --job-id behaves exactly as before.
    All legacy required args must be present (--url, --primary-docket,
    --case-name, --argued-date), or a ValueError is raised.
"""

import io
import os
import urllib.parse
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    Case,
    CaseArgument,
    PipelineRun,
    PipelineRunStatus,
)
from pipeline.db import get_session


def _validate_url(url: str) -> None:
    """
    Validate that the URL is a safe, supremecourt.gov https URL.

    Raises ValueError if:
    - scheme is not 'https'
    - netloc is not exactly 'supremecourt.gov' or a subdomain thereof
      (prevents bypass via 'xsupremecourt.gov' which ends with 'supremecourt.gov')

    This check MUST happen before any httpx call to prevent SSRF attacks
    (T-03-01 in the threat model).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"Only HTTPS URLs are accepted; got scheme '{parsed.scheme}'. "
            "Only supremecourt.gov URLs are accepted."
        )
    netloc = parsed.netloc.lower()
    if not (netloc == "supremecourt.gov" or netloc.endswith(".supremecourt.gov")):
        raise ValueError(
            f"Only supremecourt.gov URLs are accepted; got host '{parsed.netloc}'."
        )


def _derive_slug(case_name: str) -> str:
    """
    Derive a URL-safe slug from a case name.

    Example: "Obergefell v. Hodges" → "obergefell-v-hodges"
    Example: "Smith & Jones" → "smith-and-jones"
    Example: "City/County v. State" → "city-county-v-state"
    """
    import re
    slug = case_name.lower()
    slug = slug.replace("'", "")        # apostrophes: Women's → womens
    slug = slug.replace("&", "and")     # ampersands: RFC 3986 unsafe in path segment
    slug = slug.replace("/", "-")       # slashes: create phantom path segments
    slug = slug.replace("(", "").replace(")", "")  # parentheses
    slug = slug.replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"-{2,}", "-", slug)  # WR-03: collapse consecutive dashes
    return slug.strip("-")


def _get_spaces_client():
    """
    Build a boto3 S3 client pointing at DO Spaces.

    Reads credentials from environment variables — same vars used by the
    API-side spaces service, but imported directly here to keep pipeline
    decoupled from api.services.spaces (offline pipeline constraint).

    Required env vars:
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        DO_SPACES_BUCKET
        DO_SPACES_ENDPOINT  — e.g. "https://nyc3.digitaloceanspaces.com"
        DO_SPACES_REGION    — e.g. "nyc3"
    """
    import boto3

    endpoint = os.environ.get("DO_SPACES_ENDPOINT", "")
    region = os.environ.get("DO_SPACES_REGION", "nyc3")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _download_from_spaces(spaces_key: str, dest_path: Path) -> None:
    """
    Download a PDF from DO Spaces to dest_path.

    spaces_key is treated as an opaque object key (e.g. "uploads/42.pdf").
    It is server-generated and never used as a local filesystem path outside
    of data/pdfs/ — T-07-08 path traversal threat is mitigated by the
    caller deriving dest_path from a docket-based filename, not from spaces_key.

    Args:
        spaces_key: DO Spaces object key (e.g. "uploads/42.pdf")
        dest_path: local Path to write the downloaded bytes
    """
    client = _get_spaces_client()
    bucket = os.environ.get("DO_SPACES_BUCKET", "")

    buf = io.BytesIO()
    client.download_fileobj(bucket, spaces_key, buf)
    buf.seek(0)
    dest_path.write_bytes(buf.read())
    print(f"Downloaded {spaces_key} from DO Spaces -> {dest_path}")


def _derive_metadata_from_key(spaces_key: str, job_id: int) -> tuple[str, str, str]:
    """
    Derive placeholder metadata for a job-driven ingest when operator did not
    supply --primary-docket, --case-name, or --argued-date.

    Strategy: use the job_id as a synthetic docket number so the Argument row
    gets a unique, deterministic identifier. Phase 8 (People Editor) lets the
    operator edit full metadata after ingest.

    Returns:
        (primary_docket, case_name, argued_date) — all strings
    """
    # Use job_id-based synthetic docket — guaranteed unique, safe placeholder
    primary_docket = f"job-{job_id}"
    case_name = f"Pending review (job {job_id})"
    argued_date = date.today().isoformat()
    return primary_docket, case_name, argued_date


async def run_ingest(args) -> None:
    """
    Ingest a transcript PDF from supremecourt.gov (or DO Spaces) into the database.

    Args:
        args: argparse.Namespace with:
            - url (str | None): PDF URL — must be https://...supremecourt.gov/...
            - spaces_key (str | None): DO Spaces object key (alternative to url)
            - primary_docket (str | None): primary docket number (e.g. "14-556")
            - dockets (list[str]): additional consolidated docket numbers
            - case_name (str | None): human-readable case name
            - argued_date (str | None): YYYY-MM-DD argument date
            - question (int): question number (1 or 2)
            - job_id (int | None): admin_jobs.id — when set, writes status to admin_jobs

    Steps:
        0. (job-driven) Mark admin_jobs RUNNING / INGEST
        1. Validate legacy required args OR derive metadata (job-driven path)
        2. Validate URL (SSRF mitigation) — raises ValueError on invalid URL
        3. Derive slug and PDF path
        4. Download PDF — from URL or from DO Spaces (idempotent)
        5. Create DB records (idempotent — skip existing cases)
        6. (job-driven) Mark admin_jobs COMPLETED + argument_id
    """
    try:
        await _run_ingest_inner(args)
    except Exception as exc:
        if args.job_id is not None:
            try:
                async with get_session() as session:
                    await session.execute(
                        update(AdminJob)
                        .where(AdminJob.id == args.job_id)
                        .values(
                            status=AdminJobStatus.FAILED,
                            error_message=str(exc),
                        )
                        .execution_options(synchronize_session=False)
                    )
            except Exception as write_err:
                print(f"Warning: could not write FAILED status for job {args.job_id}: {write_err}")
        raise


async def _run_ingest_inner(args) -> None:
    """Core ingest logic. Errors bubble up to run_ingest for FAILED status write."""

    # ------------------------------------------------------------------
    # Step 0: Mark admin_jobs RUNNING (job-driven path only)
    # ------------------------------------------------------------------
    if args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.RUNNING,
                    current_step=AdminJobStep.INGEST,
                )
                .execution_options(synchronize_session=False)
            )

    # ------------------------------------------------------------------
    # Step 1: Validate / derive args
    # ------------------------------------------------------------------
    if args.job_id is None:
        # Legacy direct-CLI path — enforce all required args
        missing = []
        if not args.url and not getattr(args, "spaces_key", None):
            missing.append("--url")
        if not args.primary_docket:
            missing.append("--primary-docket")
        if not args.case_name:
            missing.append("--case-name")
        if not args.argued_date:
            missing.append("--argued-date")
        if missing:
            raise ValueError(
                f"Missing required arguments for direct CLI use: {', '.join(missing)}. "
                "Pass --job-id to enable job-driven mode with derived metadata."
            )
        primary_docket = args.primary_docket
        case_name = args.case_name
        argued_date = args.argued_date
    else:
        # Job-driven path — use operator-supplied args as-is; may be None.
        # D-03/D-08: synthetic placeholder behavior removed for job-driven ingest.
        # Null fields are left NULL; parse step auto-populates from cover extractor (D-09).
        primary_docket = args.primary_docket  # may be None
        case_name = args.case_name            # may be None
        argued_date = args.argued_date        # may be None

    # ------------------------------------------------------------------
    # Step 2: URL validation — MUST be before any httpx call (T-03-01)
    # ------------------------------------------------------------------
    spaces_key = getattr(args, "spaces_key", None)
    if args.url:
        _validate_url(args.url)

    # ------------------------------------------------------------------
    # Step 3: Derive slug and local PDF path
    # Fallbacks when operator did not supply docket/case_name/argued_date (D-08):
    #   - pdf_filename uses job_id when primary_docket is None (avoids "None-q1.pdf")
    #   - base_slug uses job_id when case_name is None
    #   - term_year uses today's year when argued_date is None (Case requires term_year)
    # ------------------------------------------------------------------
    if case_name is not None:
        base_slug = _derive_slug(case_name)
    else:
        base_slug = f"job-{args.job_id}" if args.job_id is not None else "unknown"

    if primary_docket is not None:
        pdf_filename = f"{primary_docket}-q{args.question}.pdf"
    else:
        pdf_filename = (
            f"job-{args.job_id}-q{args.question}.pdf"
            if args.job_id is not None
            else f"unknown-q{args.question}.pdf"
        )

    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / pdf_filename

    # ------------------------------------------------------------------
    # Step 4: Download PDF (idempotent — PIPE-02: immutable after ingest)
    # Source: --url (supremecourt.gov), --spaces-key (object storage upload),
    #         or --local-file (dev fallback when object storage is not configured)
    # ------------------------------------------------------------------
    local_file = getattr(args, "local_file", None)
    if pdf_path.exists():
        print(f"PDF already exists at {pdf_path} — skipping download.")
    elif local_file:
        # Dev fallback: copy from locally saved upload to the immutable pdf_path.
        # local_file is an absolute path written by the API before spawning this
        # subprocess; it is never derived from user input directly.
        import shutil
        shutil.copy2(local_file, pdf_path)
        print(f"Copied local file {local_file} -> {pdf_path}")
    elif spaces_key:
        # Fetch uploaded PDF from object storage (T-07-08: key is opaque, never
        # used as a local path — dest_path derived from docket, not from key)
        _download_from_spaces(spaces_key, pdf_path)
    else:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # write_bytes is fine for SCOTUS PDF sizes (~3–10 MB)
            response = await client.get(args.url)
            response.raise_for_status()
            pdf_path.write_bytes(response.content)
            print(f"Downloaded {pdf_filename} ({len(response.content)} bytes)")

    # ------------------------------------------------------------------
    # Step 5: Create DB records
    # ------------------------------------------------------------------
    # Build the list of all dockets: primary first, then consolidated.
    all_dockets: list[str] = (
        ([primary_docket] if primary_docket is not None else [])
        + list(args.dockets or [])
    )

    # CR-03: Guarantee at least one Case row exists for the argument.
    # get_argument_detail requires a CaseArgument row with is_lead=True to
    # resolve the lead case; without it the service returns None → router 404.
    # When the operator didn't supply a docket, create a synthetic placeholder
    # docket (job-{id}) that they can edit after the parse step fills in the
    # cover metadata (D-08). This restores the Case-creation guarantee that
    # was lost when _derive_metadata_from_key was removed.
    if not all_dockets and args.job_id is not None:
        synthetic_docket = f"job-{args.job_id}"
        all_dockets = [synthetic_docket]
        primary_docket = synthetic_docket

    # Derive term_year: use argued_date year when available, fall back to current year
    # (Case.term_year is NOT NULL, so we must always supply a value — D-08).
    if argued_date is not None:
        term_year = int(argued_date.split("-")[0])
    else:
        term_year = date.today().year

    async with get_session() as session:
        # ---- a. Case records (idempotent) ----
        # CR-02: when case_name is None (operator did not supply it), use a placeholder
        # that satisfies Case.case_name NOT NULL constraint; operator can edit it later.
        effective_case_name = case_name or f"Pending review (job {args.job_id})"
        # CR-02: designate lead docket — first in all_dockets when primary_docket is None,
        # so at least one CaseArgument row has is_lead=True (required by get_argument_detail).
        lead_docket = primary_docket if primary_docket is not None else (all_dockets[0] if all_dockets else None)

        cases: list[Case] = []
        for docket in all_dockets:
            result = await session.execute(
                select(Case).where(Case.docket_number == docket)
            )
            existing_case = result.scalar_one_or_none()

            if existing_case is not None:
                print(f"Case {docket} already exists (id={existing_case.id}) — reusing.")
                cases.append(existing_case)
            else:
                # Derive slug: primary docket uses base slug;
                # consolidated dockets get base_slug + "-" + docket
                if docket == primary_docket:
                    case_slug = base_slug
                else:
                    case_slug = f"{base_slug}-{docket}"

                new_case = Case(
                    docket_number=docket,
                    docket_number_norm=docket.replace("-", ""),
                    case_name=effective_case_name,  # CR-02: never None
                    term_year=term_year,
                    slug=case_slug,
                )
                session.add(new_case)
                cases.append(new_case)

        # Flush to get IDs for newly created Case rows
        await session.flush()

        # ---- b. Argument record ----
        # Phase 24 Plan 04 (D-07 supersession): persist the full ordered docket
        # list to source_dockets while keeping source_docket synced to the
        # primary/first docket — the canonical dedup key used by the UNIQUE
        # constraint (source_docket, question_number). Dedup logic is unchanged;
        # it still keys off source_docket alone, never source_dockets.
        argument = Argument(
            argued_date=date.fromisoformat(argued_date) if argued_date else None,  # D-08: nullable
            question_number=args.question,
            source_docket=primary_docket or (all_dockets[0] if all_dockets else None),
            source_dockets=all_dockets or None,
        )
        session.add(argument)
        try:
            await session.flush()  # get argument.id; raises IntegrityError on duplicate
        except IntegrityError:
            raise ValueError(
                f"Duplicate argument: docket {primary_docket!r} Q{args.question} already exists."
            )

        # ---- c. CaseArgument rows (idempotent) ----
        for case in cases:
            existing_link = await session.execute(
                select(CaseArgument).where(
                    CaseArgument.case_id == case.id,
                    CaseArgument.argument_id == argument.id,
                )
            )
            if existing_link.scalar_one_or_none() is None:
                link = CaseArgument(
                    case_id=case.id,
                    argument_id=argument.id,
                    is_lead=(case.docket_number == lead_docket),  # CR-02: use lead_docket (not primary_docket which may be None)
                )
                session.add(link)

        # ---- d. PipelineRun record ----
        run = PipelineRun(
            argument_id=argument.id,
            step="ingest",
            status=PipelineRunStatus.COMPLETED,
            pdf_path=str(pdf_path),
            pdf_url=args.url,
        )
        session.add(run)

        # Flush to get run.id before commit
        await session.flush()
        run_id = run.id
        argument_id = argument.id

    # get_session() commits on clean exit
    print(f"Ingest complete. pipeline_run.id = {run_id}")

    # ------------------------------------------------------------------
    # Step 6: Mark admin_jobs COMPLETED + argument_id (job-driven path)
    # Note: current_step stays INGEST — poll endpoint advances to PARSE
    # atomically using the step-advance guard (Pattern 3 / D-05).
    # ------------------------------------------------------------------
    if args.job_id is not None:
        async with get_session() as session:
            await session.execute(
                update(AdminJob)
                .where(AdminJob.id == args.job_id)
                .values(
                    status=AdminJobStatus.COMPLETED,
                    argument_id=argument_id,
                )
                .execution_options(synchronize_session=False)
            )
        print(f"Admin job {args.job_id} marked completed (argument_id={argument_id})")
