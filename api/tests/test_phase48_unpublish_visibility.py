"""
Phase 48 Plan 10 — Defect 2 regression: unpublish must actually hide the
argument from every public read path.

`unpublish_argument` sets `status = UNPUBLISHED` and deliberately leaves
`published_at` set (D-02, so the Status card can show the last publish date).
Before this plan, all three public read paths gated ONLY on
`Argument.published_at.isnot(None)`, so an UNPUBLISHED argument (whose
`published_at` stays set) remained fully visible on the public site —
the operator's only "take this down" control took nothing down.

This module seeds a DRAFT argument, publishes it (proving visibility),
unpublishes it, and proves absence across all three read paths:
  - api.services.cases.get_cases
  - api.services.arguments.get_argument_with_utterances
  - api.services.speakers.get_argument_speakers
plus a router-level 404 check on GET /arguments/{id}/utterances.

DB-gated (skipped without DATABASE_URL), mirroring
test_admin_arguments_service.py's `_db_configured()` / seeding / FK-ordered
cleanup conventions.
"""

import datetime
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app (ASGITransport, no real socket)."""
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublished_argument_is_absent_from_all_three_public_read_paths(
    client: AsyncClient,
) -> None:
    """
    Seed a DRAFT argument, publish it (with an override reason — this
    synthetic argument has zero constituents and floors to UNCERTAIN per
    D-13), confirm it IS visible via all three public read paths, then
    unpublish it and confirm it is ABSENT from all three — plus a
    router-level 404 on GET /arguments/{id}/utterances.
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, ArgumentStatusLog, Case, CaseArgument
    from api.services.admin_arguments import publish_argument, unpublish_argument
    from api.services.arguments import get_argument_with_utterances
    from api.services.cases import get_cases
    from api.services.speakers import get_argument_speakers

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        # get_argument_detail (which publish_argument's return value
        # delegates to) requires a lead case to return non-None.
        case = Case(
            docket_number="26-01-TEST-UNPUB",
            docket_number_norm="26-01-test-unpub",
            case_name="Synthetic Test Case v. Unpublish Visibility",
            term_year=2026,
            slug="synthetic-test-case-v-unpublish-visibility-26-01",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id

    # --- publish (with override — zero-constituent floors to UNCERTAIN) -----
    async with AsyncSessionLocal() as db:
        result = await publish_argument(
            db, arg_id, override_reason="unpublish visibility regression test"
        )
    assert result is not None
    assert result["status"] == ArgumentStatusEnum.PUBLISHED

    # --- confirm visible via all three public read paths ---------------------
    async with AsyncSessionLocal() as db:
        cases = await get_cases(db)
        assert any(c["argument_id"] == arg_id for c in cases), (
            "published argument must appear in get_cases()"
        )

        detail = await get_argument_with_utterances(db, arg_id)
        assert detail is not None, "published argument must resolve via get_argument_with_utterances"

        speakers = await get_argument_speakers(db, arg_id)
        assert speakers is not None, (
            "published argument must resolve via get_argument_speakers "
            "(an empty [] speaker list is fine — the argument itself must resolve)"
        )

    utterances_response = await client.get(f"/arguments/{arg_id}/utterances")
    assert utterances_response.status_code == 200

    # --- unpublish -------------------------------------------------------------
    async with AsyncSessionLocal() as db:
        unpub_result = await unpublish_argument(db, arg_id)
    assert unpub_result is not None
    assert unpub_result["status"] == ArgumentStatusEnum.UNPUBLISHED
    # published_at is deliberately retained (D-02) — this is the whole point
    # of Defect 2: the bug is NOT that published_at is missing.
    assert unpub_result["published_at"] is not None

    # --- confirm ABSENT from all three public read paths ------------------------
    async with AsyncSessionLocal() as db:
        cases_after = await get_cases(db)
        assert not any(c["argument_id"] == arg_id for c in cases_after), (
            "UNPUBLISHED argument (published_at retained per D-02) must be "
            "absent from get_cases() — Defect 2."
        )

        detail_after = await get_argument_with_utterances(db, arg_id)
        assert detail_after is None, (
            "UNPUBLISHED argument must return None from "
            "get_argument_with_utterances() — Defect 2."
        )

        speakers_after = await get_argument_speakers(db, arg_id)
        assert speakers_after is None, (
            "UNPUBLISHED argument must return None from "
            "get_argument_speakers() — Defect 2's third, previously-unnamed leak path."
        )

    # --- router-level: direct fetch must 404, not silently succeed -------------
    utterances_after = await client.get(f"/arguments/{arg_id}/utterances")
    assert utterances_after.status_code == 404

    # --- cleanup (FK-ordered, mirroring test_admin_arguments_service.py) -------
    async with AsyncSessionLocal() as db:
        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        log_rows = log_result.scalars().all()
        ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
        await db.delete(ca)
        for row in log_rows:
            await db.delete(row)
        await db.flush()
        case_row = await db.get(Case, case_id)
        await db.delete(case_row)
        arg_row = await db.get(Argument, arg_id)
        await db.delete(arg_row)
        await db.commit()
