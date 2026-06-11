"""
Pipeline ingest command.

Downloads a transcript PDF from supremecourt.gov and creates the following
database records:
    - Case row(s) — one per docket number (primary + consolidated)
    - Argument row — one per hearing session
    - CaseArgument rows — M:M join (one per case, with is_lead=True for primary)
    - PipelineRun row — status=COMPLETED (ingest is synchronous)

SECURITY: URL validation (SSRF mitigation) happens BEFORE any httpx call.
Only https://...supremecourt.gov/... URLs are accepted.

IMMUTABILITY: Downloaded PDFs are never overwritten. If the file already
exists on disk, the download step is skipped (idempotent re-run support).
"""

import urllib.parse
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select

from api.models.models import (
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
    - netloc does not end with 'supremecourt.gov'

    This check MUST happen before any httpx call to prevent SSRF attacks
    (T-03-01 in the threat model).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"Only HTTPS URLs are accepted; got scheme '{parsed.scheme}'. "
            "Only supremecourt.gov URLs are accepted."
        )
    if not parsed.netloc.endswith("supremecourt.gov"):
        raise ValueError(
            f"Only supremecourt.gov URLs are accepted; got host '{parsed.netloc}'."
        )


def _derive_slug(case_name: str) -> str:
    """
    Derive a URL-safe slug from a case name.

    Example: "Obergefell v. Hodges" → "obergefell-v-hodges"
    """
    return (
        case_name.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace(",", "")
    )


async def run_ingest(args) -> None:
    """
    Ingest a transcript PDF from supremecourt.gov into the database.

    Args:
        args: argparse.Namespace with:
            - url (str): PDF URL — must be https://...supremecourt.gov/...
            - primary_docket (str): primary docket number (e.g. "14-556")
            - dockets (list[str]): additional consolidated docket numbers
            - case_name (str): human-readable case name
            - argued_date (str): YYYY-MM-DD argument date
            - question (int): question number (1 or 2)

    Steps:
        1. Validate URL (SSRF mitigation) — raises ValueError on invalid URL
        2. Derive slug and PDF path
        3. Download PDF (idempotent — skip if file already exists)
        4. Create DB records (idempotent — skip existing cases)
        5. Commit
    """
    # ------------------------------------------------------------------
    # Step 1: URL validation — MUST be before any httpx call (T-03-01)
    # ------------------------------------------------------------------
    _validate_url(args.url)

    # ------------------------------------------------------------------
    # Step 2: Derive slug and local PDF path
    # ------------------------------------------------------------------
    base_slug = _derive_slug(args.case_name)
    pdf_filename = f"{args.primary_docket}-q{args.question}.pdf"
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / pdf_filename

    # ------------------------------------------------------------------
    # Step 3: Download PDF (idempotent — PIPE-02: immutable after ingest)
    # ------------------------------------------------------------------
    if pdf_path.exists():
        print(f"PDF already exists at {pdf_path} — skipping download.")
    else:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # write_bytes is fine for SCOTUS PDF sizes (~3–10 MB)
            response = await client.get(args.url)
            response.raise_for_status()
            pdf_path.write_bytes(response.content)
            print(f"Downloaded {pdf_filename} ({len(response.content)} bytes)")

    # ------------------------------------------------------------------
    # Step 4: Create DB records
    # ------------------------------------------------------------------
    # Build the list of all dockets: primary first, then consolidated.
    all_dockets: list[str] = [args.primary_docket] + list(args.dockets or [])

    async with get_session() as session:
        # ---- a. Case records (idempotent) ----
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
                if docket == args.primary_docket:
                    case_slug = base_slug
                else:
                    case_slug = f"{base_slug}-{docket}"

                new_case = Case(
                    docket_number=docket,
                    docket_number_norm=docket.replace("-", ""),
                    case_name=args.case_name,
                    term_year=int(args.argued_date.split("-")[0]),
                    slug=case_slug,
                )
                session.add(new_case)
                cases.append(new_case)

        # Flush to get IDs for newly created Case rows
        await session.flush()

        # ---- b. Argument record ----
        argument = Argument(
            argued_date=date.fromisoformat(args.argued_date),
            question_number=args.question,
        )
        session.add(argument)
        await session.flush()  # get argument.id

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
                    is_lead=(case.docket_number == args.primary_docket),
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

    # get_session() commits on clean exit
    print(f"Ingest complete. pipeline_run.id = {run_id}")
