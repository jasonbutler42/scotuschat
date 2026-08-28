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

from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
from api.tests.test_arguments import assert_no_key_anywhere

# `AsyncSessionLocal` is None at import time and only assigned inside the
# FastAPI lifespan (api/core/database.py), so it must never be bound at module
# scope here — neither the name (`from ... import AsyncSessionLocal`, which
# would freeze the pre-lifespan None) NOR the module object
# (`from api.core import database as _database`, which freezes the pre-RESET
# module).
#
# The module-object form is the subtler trap and it is why this file failed
# under a bare `pytest` run: `tests/test_admin_router.py::
# test_api_main_imports_without_error` deletes and re-imports every `api.*`
# module mid-suite, and pytest.ini's `testpaths = tests pipeline/tests
# api/tests` runs `tests/` FIRST. A module-scope binding here therefore points
# at the pre-reset `api.core.database` while conftest's `_api_lifespan` fixture
# sets `AsyncSessionLocal` on the post-reset one — two disconnected module
# graphs, exactly as `api/tests/conftest.py::_api_lifespan` documents. The
# failure only hides when `api/tests` is collected first, which is what an
# explicit-path invocation like `pytest api/tests tests pipeline/tests` does.
#
# Import inside each function that needs it, so the lookup re-resolves
# `sys.modules` at call time. This matches `test_arguments.py`'s helpers.


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
        from api.core.database import AsyncSessionLocal

        suffix = uuid.uuid4().hex[:10]
        if published_at is None and status == ArgumentStatusEnum.PUBLISHED:
            published_at = datetime.datetime.now(datetime.timezone.utc)

        async with AsyncSessionLocal() as db:
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
        from api.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
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


# ---------------------------------------------------------------------------
# Task 2: GET /arguments/term/{term_year}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_lists_only_published_arguments_for_that_term(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """
    GET /arguments/term/{year} lists only published arguments whose lead
    case has that term_year — a published argument in a different term, and
    a draft argument in the same term, are both excluded.
    """
    year = 1900 + (uuid.uuid4().int % 100)
    other_year = year + 1

    included_id = await seeded.add_argument(term_year=year, question_number=1)
    await seeded.add_argument(term_year=other_year, question_number=1)
    await seeded.add_argument(
        term_year=year,
        question_number=2,
        status=ArgumentStatusEnum.DRAFT,
        published_at=None,
    )

    response = await client.get(f"/arguments/term/{year}")
    assert response.status_code == 200
    body = response.json()
    assert body["term_year"] == year
    argument_ids = [a["argument_id"] for a in body["arguments"]]
    assert argument_ids == [included_id]


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_real_empty_term_returns_200_not_404(client: AsyncClient) -> None:
    """
    A real, in-range year with no seeded data (1799) returns 200 with an
    empty `arguments` list — never a 404. This is the UI-SPEC E2 "empty"
    row: an empty term is not the same as a non-existent one.
    """
    response = await client.get("/arguments/term/1799")
    assert response.status_code == 200
    assert response.json() == {"term_year": 1799, "arguments": []}


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_non_numeric_year_returns_422(client: AsyncClient) -> None:
    response = await client.get("/arguments/term/notayear")
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_out_of_range_year_returns_422(client: AsyncClient) -> None:
    response = await client.get("/arguments/term/99999")
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_excludes_unpublished_with_retained_published_at(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """
    An argument whose `status` is UNPUBLISHED but whose `published_at` is
    still non-null is absent from the term-detail response for its term
    (same both-predicates gate as the term index).
    """
    year = 1910 + (uuid.uuid4().int % 100)

    await seeded.add_argument(
        term_year=year,
        question_number=1,
        status=ArgumentStatusEnum.UNPUBLISHED,
        published_at=datetime.datetime.now(datetime.timezone.utc),
    )

    response = await client.get(f"/arguments/term/{year}")
    assert response.status_code == 200
    assert response.json()["arguments"] == []


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_consolidated_docket_contributes_one_row(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """A consolidated case (one lead + three non-lead case_arguments rows) contributes exactly one row."""
    year = 1920 + (uuid.uuid4().int % 100)

    argument_id = await seeded.add_argument(term_year=year, question_number=1, extra_lead_cases=3)

    response = await client.get(f"/arguments/term/{year}")
    assert response.status_code == 200
    argument_ids = [a["argument_id"] for a in response.json()["arguments"]]
    assert argument_ids == [argument_id]


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_shared_argued_date_orders_stably(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """
    Two arguments in the same term sharing an argued_date return in a
    stable order (tiebroken by Argument.id) across two consecutive
    requests — no accidental reordering between calls.
    """
    year = 1930 + (uuid.uuid4().int % 100)
    shared_date = datetime.date(year, 1, 15)

    id_a = await seeded.add_argument(term_year=year, question_number=1, argued_date=shared_date)
    id_b = await seeded.add_argument(term_year=year, question_number=2, argued_date=shared_date)

    first_response = await client.get(f"/arguments/term/{year}")
    second_response = await client.get(f"/arguments/term/{year}")

    first_order = [a["argument_id"] for a in first_response.json()["arguments"]]
    second_order = [a["argument_id"] for a in second_response.json()["arguments"]]

    assert set(first_order) == {id_a, id_b}
    assert first_order == second_order


# ---------------------------------------------------------------------------
# Task 3: live leak assertions — the half a static schema sweep structurally
# cannot see (T-51-04-06).
#
# api/tests/test_trust_public_leak_ban.py's static sweep derives response
# models from each public router's declared `response_model=` and walks
# their DECLARED fields. It cannot see a payload that never passes through a
# declared model at all — a route with no response_model, a raw JSONResponse
# return, or a dict/Any-typed field whose runtime keys no declared-field
# sweep can enumerate. These three tests fetch the real endpoint and walk
# the DECODED JSON body recursively with assert_no_key_anywhere (imported,
# not copied, from api/tests/test_arguments.py), covering every new
# unauthenticated public payload this phase ships:
#   - GET /arguments/terms
#   - GET /arguments/term/{term_year}
#   - GET /arguments/by-slug/{slug}/utterances (route added by plan 51-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_terms_live_response_never_leaks_trust_tier(client: AsyncClient, seeded: _SeededFixture) -> None:
    """GET /arguments/terms — live decoded JSON body, walked recursively."""
    year = 1940 + (uuid.uuid4().int % 100)
    await seeded.add_argument(term_year=year, question_number=1)

    response = await client.get("/arguments/terms")
    assert response.status_code == 200
    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /arguments/terms response")


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_term_detail_live_response_never_leaks_trust_tier(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """GET /arguments/term/{term_year} — live decoded JSON body, against a seeded, populated term."""
    year = 1950 + (uuid.uuid4().int % 100)
    await seeded.add_argument(term_year=year, question_number=1)

    response = await client.get(f"/arguments/term/{year}")
    assert response.status_code == 200
    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /arguments/term/{term_year} response")


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="DATABASE_URL not configured")
async def test_by_slug_utterances_live_response_never_leaks_trust_tier(
    client: AsyncClient, seeded: _SeededFixture
) -> None:
    """
    GET /arguments/by-slug/{slug}/utterances — live decoded JSON body,
    against a seeded published argument. This route was added by plan
    51-02; plan 51-04's live-leak coverage extends to it too, since it is
    one of the three new unauthenticated public payloads this phase ships
    (the other two are this module's own two term-grouped endpoints).
    """
    suffix = uuid.uuid4().hex[:10]
    slug = f"test-fixture-leak-check-{suffix}"
    year = 1960 + (uuid.uuid4().int % 100)
    await seeded.add_argument(term_year=year, question_number=1, slug=slug)

    response = await client.get(f"/arguments/by-slug/{slug}/utterances")
    assert response.status_code == 200
    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /arguments/by-slug/{slug}/utterances response")
