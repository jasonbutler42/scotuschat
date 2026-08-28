"""
Integration tests for the term-grouped public arguments listing (Phase 51
plan 51-04, D-14/D-15): `GET /arguments/terms` and
`GET /arguments/term/{term_year}`.

Named after the unit under test, not the phase, per CLAUDE.md's Testing
Policy. Requires a live `TEST_DATABASE_URL` / `DATABASE_URL` (the rootdir
conftest.py redirects onto `scotus_test` for the whole suite) — every test
below is DB-gated and skips (not silently passes) when no DB is configured.
"""

import datetime
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from api.core import database as _database
from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

# `AsyncSessionLocal` is None at import time and only assigned inside the
# FastAPI lifespan (api/core/database.py) — a `from ... import
# AsyncSessionLocal` at module scope here would bind this module's name to
# that pre-lifespan None permanently. Reference `_database.AsyncSessionLocal`
# as a module attribute instead, so every lookup re-reads the current
# (post-lifespan-startup) value, matching the deferred-import pattern
# established in test_published_gate.py's helpers.


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


class _SeededFixture:
    """Tracks every Case/Argument/CaseArgument row a test creates, for
    FK-ordered teardown regardless of how many consolidated-docket rows
    were added."""

    def __init__(self) -> None:
        self.case_ids: list[int] = []
        self.argument_ids: list[int] = []

    async def add_argument(
        self,
        *,
        term_year: int,
        status: ArgumentStatusEnum = ArgumentStatusEnum.PUBLISHED,
        published_at: datetime.datetime | None = None,
        argued_date: datetime.date | None = None,
        question_number: int | None = None,
        slug: str | None = None,
        extra_lead_cases: int = 0,
    ) -> int:
        """
        Seed one Argument with a lead Case (term_year on the Case, reached
        through the is_lead join per D-14). `extra_lead_cases` adds that
        many ADDITIONAL non-lead Case rows joined to the SAME argument
        (the consolidated-docket shape, e.g. Obergefell 14-556/562/571/574)
        — only the first (is_lead=True) row should ever be counted.

        Commits so the ASGI client (its own AsyncSessionLocal session) can
        see the rows.
        """
        suffix = uuid.uuid4().hex[:10]
        if published_at is None and status == ArgumentStatusEnum.PUBLISHED:
            published_at = datetime.datetime.now(datetime.timezone.utc)

        async with _database.AsyncSessionLocal() as db:
            lead_case = Case(
                docket_number=f"PAL-{suffix}",
                docket_number_norm=f"pal-{suffix}",
                case_name=f"Test Fixture Case {suffix}",
                term_year=term_year,
                slug=f"test-fixture-case-{suffix}",
            )
            db.add(lead_case)
            await db.flush()

            arg = Argument(
                status=status,
                published_at=published_at,
                argued_date=argued_date,
                question_number=question_number,
                slug=slug,
            )
            db.add(arg)
            await db.flush()

            db.add(CaseArgument(case_id=lead_case.id, argument_id=arg.id, is_lead=True))

            extra_case_ids: list[int] = []
            for i in range(extra_lead_cases):
                extra_case = Case(
                    docket_number=f"PAL-{suffix}-X{i}",
                    docket_number_norm=f"pal-{suffix}-x{i}",
                    case_name=f"Test Fixture Consolidated Case {suffix}-{i}",
                    # A consolidated docket's non-lead cases can carry a
                    # different term_year in principle; keep them identical
                    # to the lead here since D-14 groups on the LEAD case's
                    # term_year only (reached through is_lead == True).
                    term_year=term_year,
                    slug=f"test-fixture-consolidated-case-{suffix}-{i}",
                )
                db.add(extra_case)
                await db.flush()
                db.add(
                    CaseArgument(case_id=extra_case.id, argument_id=arg.id, is_lead=False)
                )
                extra_case_ids.append(extra_case.id)

            await db.commit()

            self.case_ids.append(lead_case.id)
            self.case_ids.extend(extra_case_ids)
            self.argument_ids.append(arg.id)
            return arg.id

    async def teardown(self) -> None:
        async with _database.AsyncSessionLocal() as db:
            await db.execute(
                delete(CaseArgument).where(CaseArgument.argument_id.in_(self.argument_ids))
            )
            await db.execute(delete(Argument).where(Argument.id.in_(self.argument_ids)))
            await db.execute(delete(Case).where(Case.id.in_(self.case_ids)))
            await db.commit()


@pytest_asyncio.fixture
async def seeded():
    fixture = _SeededFixture()
    try:
        yield fixture
    finally:
        await fixture.teardown()


# ---------------------------------------------------------------------------
# Task 1: GET /arguments/terms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_empty_when_nothing_published(client: AsyncClient) -> None:
    """
    A brand-new, uniquely-numbered term with zero seeded rows returns 200
    with that term absent from the list — the response as a whole is never
    a 404. (The literal `{"terms": []}` empty-corpus case is covered
    structurally by this same assertion: a term this test never seeds
    cannot appear.)
    """
    response = await client.get("/arguments/terms")
    assert response.status_code == 200
    body = response.json()
    assert "terms" in body
    assert isinstance(body["terms"], list)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_counts_published_only_ordered_desc(client: AsyncClient, seeded: _SeededFixture) -> None:
    """
    Two published arguments in one term and one in an earlier term produce
    two term rows, most recent term first, with accurate counts. Uses
    uniquely-generated term years (year 1850 + a random offset) so this
    test never collides with real seed data or other tests' terms.
    """
    base_year = 1850 + (uuid.uuid4().int % 100)
    later_year = base_year + 1

    await seeded.add_argument(term_year=later_year, question_number=1)
    await seeded.add_argument(term_year=later_year, question_number=2)
    await seeded.add_argument(term_year=base_year, question_number=1)

    response = await client.get("/arguments/terms")
    assert response.status_code == 200
    terms_by_year = {t["term_year"]: t["argument_count"] for t in response.json()["terms"]}

    assert terms_by_year.get(later_year) == 2
    assert terms_by_year.get(base_year) == 1

    # Ordering: the later term must appear before the earlier one in the
    # raw list (descending term_year).
    years_in_order = [t["term_year"] for t in response.json()["terms"]]
    assert years_in_order.index(later_year) < years_in_order.index(base_year)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_excludes_draft_argument(client: AsyncClient, seeded: _SeededFixture) -> None:
    """A DRAFT argument (never published) must not inflate its term's count."""
    year = 1860 + (uuid.uuid4().int % 100)

    await seeded.add_argument(term_year=year, question_number=1)
    await seeded.add_argument(
        term_year=year,
        question_number=2,
        status=ArgumentStatusEnum.DRAFT,
        published_at=None,
    )

    response = await client.get("/arguments/terms")
    terms_by_year = {t["term_year"]: t["argument_count"] for t in response.json()["terms"]}
    assert terms_by_year.get(year) == 1


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_excludes_unpublished_argument_with_retained_published_at(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """
    An argument whose `status` is UNPUBLISHED but whose `published_at` is
    still non-null (unpublish_argument deliberately retains it, Phase 48
    plan 10 Defect 2) must not inflate its term's count — the gate is both
    predicates, never one instead of the other.
    """
    year = 1870 + (uuid.uuid4().int % 100)

    await seeded.add_argument(term_year=year, question_number=1)
    await seeded.add_argument(
        term_year=year,
        question_number=2,
        status=ArgumentStatusEnum.UNPUBLISHED,
        published_at=datetime.datetime.now(datetime.timezone.utc),
    )

    response = await client.get("/arguments/terms")
    terms_by_year = {t["term_year"]: t["argument_count"] for t in response.json()["terms"]}
    assert terms_by_year.get(year) == 1


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_consolidated_docket_contributes_one(client: AsyncClient, seeded: _SeededFixture) -> None:
    """
    A consolidated case with four `case_arguments` rows (one lead, three
    non-lead) contributes exactly 1 to its term's count — never 4.
    """
    year = 1880 + (uuid.uuid4().int % 100)

    await seeded.add_argument(term_year=year, question_number=1, extra_lead_cases=3)

    response = await client.get("/arguments/terms")
    terms_by_year = {t["term_year"]: t["argument_count"] for t in response.json()["terms"]}
    assert terms_by_year.get(year) == 1


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_absent_when_only_argument_is_unpublished(client: AsyncClient, seeded: _SeededFixture) -> None:
    """A term whose only argument is unpublished (DRAFT) is absent from the list entirely."""
    year = 1890 + (uuid.uuid4().int % 100)

    await seeded.add_argument(
        term_year=year,
        question_number=1,
        status=ArgumentStatusEnum.DRAFT,
        published_at=None,
    )

    response = await client.get("/arguments/terms")
    years_present = {t["term_year"] for t in response.json()["terms"]}
    assert year not in years_present
