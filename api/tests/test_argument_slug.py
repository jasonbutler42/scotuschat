"""
Tests for Argument.slug generation and the by-slug public routes
(Phase 51 plan 51-02, D-10/D-12/D-13).

Pure-function tests (reserved-word guard, collision disambiguation) run
without a database. The remaining tests are live-DB integration tests,
skipped when DATABASE_URL is not configured — mirroring the pattern
established in api/tests/test_arguments.py.
"""

import datetime
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.domain.argument_slug import RESERVED_SLUG_WORDS, derive_argument_slug


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


# ---------------------------------------------------------------------------
# Pure-function tests: no DB required
# ---------------------------------------------------------------------------


def test_derive_argument_slug_bare_for_common_case():
    """The single-argument common case gets the bare base slug, no suffix."""
    assert derive_argument_slug("Obergefell v. Hodges") == "obergefell-v-hodges"


def test_derive_argument_slug_never_returns_reserved_word():
    """D-13: 'Term' must never mint the bare reserved word 'term'."""
    slug = derive_argument_slug("Term")
    assert slug != "term"
    assert slug not in RESERVED_SLUG_WORDS


def test_derive_argument_slug_never_returns_empty_string():
    """A case name that slugifies to nothing still gets a real, non-empty slug."""
    slug = derive_argument_slug("...")
    assert slug != ""
    assert slug not in RESERVED_SLUG_WORDS


def test_derive_argument_slug_disambiguates_on_question_number():
    """
    Two arguments sharing a case name (the reargued/multi-session case)
    get distinct slugs when the base is already taken — question_number
    is the primary discriminator (see module docstring for the corpus-scale
    rationale: it is always populated and unique-by-construction, unlike
    argued_date).
    """
    base = derive_argument_slug("Smith v. Jones")
    second = derive_argument_slug(
        "Smith v. Jones", question_number=2, taken={base}
    )
    assert second != base
    assert second not in RESERVED_SLUG_WORDS


def test_derive_argument_slug_falls_back_to_argued_date_without_question_number():
    """When question_number is unavailable, argued_date disambiguates instead."""
    base = derive_argument_slug("Smith v. Jones")
    second = derive_argument_slug(
        "Smith v. Jones",
        argued_date=datetime.date(2019, 3, 1),
        taken={base},
    )
    assert second != base


def test_derive_argument_slug_terminates_with_no_discriminators():
    """
    With neither question_number nor argued_date, the incrementing-counter
    fallback still produces a distinct, terminating slug.
    """
    base = derive_argument_slug("Smith v. Jones")
    second = derive_argument_slug("Smith v. Jones", taken={base})
    assert second != base
    assert second.startswith(base)


# ---------------------------------------------------------------------------
# Live-DB fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seeded_published_argument():
    """
    A minimal PUBLISHED Argument + lead Case, with a real slug — the
    happy path for the by-slug routes.
    """
    from sqlalchemy import delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            argued_date=datetime.date(2019, 3, 1),
            question_number=1,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            published_at=datetime.datetime.now(datetime.timezone.utc),
            slug="fixture-published-argument-51-02",
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="24-TEST-51-02-PUB",
            docket_number_norm="24-test-51-02-pub",
            case_name="Fixture Published Argument",
            term_year=2019,
            slug="fixture-published-argument-51-02-case",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        slug = arg.slug

    yield arg_id, slug

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CaseArgument).where(CaseArgument.argument_id == arg_id))
        case_obj = await db.get(Case, case_id)
        if case_obj is not None:
            await db.delete(case_obj)
        arg_obj = await db.get(Argument, arg_id)
        if arg_obj is not None:
            await db.delete(arg_obj)
        await db.commit()


@pytest_asyncio.fixture
async def seeded_unpublished_previously_published_argument():
    """
    An UNPUBLISHED argument whose published_at is deliberately non-NULL
    (Phase 48 plan 10 Defect 2: unpublish_argument retains published_at).
    The by-slug gate must 404 this — asserting BOTH predicates are checked,
    not just published_at.
    """
    from sqlalchemy import delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.UNPUBLISHED,
            argued_date=datetime.date(2019, 3, 1),
            question_number=1,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            published_at=datetime.datetime.now(datetime.timezone.utc),
            slug="fixture-unpublished-argument-51-02",
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="24-TEST-51-02-UNPUB",
            docket_number_norm="24-test-51-02-unpub",
            case_name="Fixture Unpublished Argument",
            term_year=2019,
            slug="fixture-unpublished-argument-51-02-case",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        slug = arg.slug

    yield arg_id, slug

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CaseArgument).where(CaseArgument.argument_id == arg_id))
        case_obj = await db.get(Case, case_id)
        if case_obj is not None:
            await db.delete(case_obj)
        arg_obj = await db.get(Argument, arg_id)
        if arg_obj is not None:
            await db.delete(arg_obj)
        await db.commit()


@pytest_asyncio.fixture
async def seeded_draft_argument():
    """A DRAFT argument with a stamped slug, for the immutability test."""
    from sqlalchemy import delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            argued_date=datetime.date(2019, 3, 1),
            question_number=1,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            slug="fixture-draft-argument-51-02",
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="24-TEST-51-02-DRAFT",
            docket_number_norm="24-test-51-02-draft",
            case_name="Fixture Draft Argument",
            term_year=2019,
            slug="fixture-draft-argument-51-02-case",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        original_argument_slug = arg.slug

    yield arg_id, case_id, original_argument_slug

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CaseArgument).where(CaseArgument.argument_id == arg_id))
        case_obj = await db.get(Case, case_id)
        if case_obj is not None:
            await db.delete(case_obj)
        arg_obj = await db.get(Argument, arg_id)
        if arg_obj is not None:
            await db.delete(arg_obj)
        await db.commit()


# ---------------------------------------------------------------------------
# Live-DB tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_published_argument_resolves_by_slug(
    client: AsyncClient, seeded_published_argument
) -> None:
    """A published argument's slug resolves via the by-slug route with 200."""
    _arg_id, slug = seeded_published_argument
    response = await client.get(f"/arguments/by-slug/{slug}/utterances")
    assert response.status_code == 200
    body = response.json()
    assert body["argument"]["case_name"] == "Fixture Published Argument"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unknown_slug_returns_404(client: AsyncClient) -> None:
    """A slug that does not exist 404s with the standard detail string."""
    response = await client.get("/arguments/by-slug/no-such-slug-at-all/utterances")
    assert response.status_code == 404
    assert response.json()["detail"] == "Argument not found"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublished_but_previously_published_argument_404s_by_slug(
    client: AsyncClient, seeded_unpublished_previously_published_argument
) -> None:
    """
    T-51-02-02: the by-slug gate checks BOTH published_at IS NOT NULL AND
    status == PUBLISHED. An UNPUBLISHED argument with a non-null
    published_at (unpublish_argument deliberately retains it) must still
    404 — a single-predicate gate would leak this exact case.
    """
    _arg_id, slug = seeded_unpublished_previously_published_argument
    response = await client.get(f"/arguments/by-slug/{slug}/utterances")
    assert response.status_code == 404
    assert response.json()["detail"] == "Argument not found"


@pytest.mark.asyncio
async def test_single_segment_traversal_slug_returns_422(client: AsyncClient) -> None:
    """
    T-51-02-01: a traversal/injection-shaped value THAT STAYS WITHIN ONE
    path segment (dots, no literal or encoded slash) is rejected by the
    Path pattern (422) before the service layer runs — no DB required,
    since FastAPI/Starlette validates path parameters before dependency
    resolution. `%2e` is the percent-encoding of `.`, so this exercises
    the same "encoded characters must still fail the allow-list" property
    without relying on how the ASGI layer handles an encoded slash (see
    the next test).
    """
    response = await client.get("/arguments/by-slug/%2e%2e/utterances")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_encoded_slash_traversal_never_reaches_the_service_layer(
    client: AsyncClient,
) -> None:
    """
    Verified framework behavior (corrects an assumption in this plan's
    original acceptance criteria, which expected 422 here): ASGI servers
    percent-decode `%2F` into a literal `/` in `scope["path"]` BEFORE
    Starlette's router runs (ASGI spec; confirmed identical under both
    httpx's ASGITransport and real uvicorn — both implement the same
    scope contract). A decoded `..%2F..%2Fetc%2Fpasswd` therefore becomes
    a 5-segment path that does not match this 4-segment route pattern at
    all, and Starlette answers 404 — the request never dispatches to this
    view function, so it never reaches Path validation OR the service/DB
    layer. That is the same security property T-51-02-01 asks for (the
    payload never reaches the service layer); it just surfaces as 404
    rather than 422 because the mismatch is caught one layer earlier, by
    routing, not by parameter validation. The only requirement this
    asserts is what actually matters: never 200, never 500.
    """
    response = await client.get("/arguments/by-slug/..%2F..%2Fetc%2Fpasswd/utterances")
    assert response.status_code not in (200, 500)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_duplicate_slug_raises_integrity_error_backstop() -> None:
    """
    The database's uq_arguments_slug unique constraint is the backstop
    behind derive_argument_slug's in-memory `taken` check — a second insert
    with an already-used slug value must raise IntegrityError even when the
    caller bypasses derive_argument_slug entirely.
    """
    import datetime as _dt

    from sqlalchemy.exc import IntegrityError

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    dup_slug = "fixture-duplicate-slug-51-02"
    async with AsyncSessionLocal() as db:
        first = Argument(
            status=ArgumentStatusEnum.DRAFT,
            argued_date=_dt.date(2019, 3, 1),
            question_number=1,
            slug=dup_slug,
        )
        db.add(first)
        await db.commit()
        first_id = first.id

    try:
        async with AsyncSessionLocal() as db:
            second = Argument(
                status=ArgumentStatusEnum.DRAFT,
                argued_date=_dt.date(2019, 3, 2),
                question_number=1,
                slug=dup_slug,
            )
            db.add(second)
            with pytest.raises(IntegrityError):
                await db.commit()
    finally:
        async with AsyncSessionLocal() as db:
            obj = await db.get(Argument, first_id)
            if obj is not None:
                await db.delete(obj)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_case_name_edit_leaves_argument_slug_unchanged(
    seeded_draft_argument,
) -> None:
    """
    D-12 immutability: editing a DRAFT argument's case name re-derives
    Case.slug but must leave Argument.slug byte-identical.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, Case
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    arg_id, case_id, original_argument_slug = seeded_draft_argument

    async with AsyncSessionLocal() as db:
        result = await update_argument(
            db, arg_id, ArgumentUpdate(case_name="Fixture Draft Argument Renamed")
        )
        assert result is not None

    async with AsyncSessionLocal() as db:
        case_obj = await db.get(Case, case_id)
        arg_obj = await db.get(Argument, arg_id)
        assert case_obj.case_name == "Fixture Draft Argument Renamed"
        assert case_obj.slug != "fixture-draft-argument-51-02-case"
        assert arg_obj.slug == original_argument_slug
