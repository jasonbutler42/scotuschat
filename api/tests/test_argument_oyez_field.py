"""
Targeted tests for the oyez_transcript_id field on the public argument payload.

Scope: only the oyez_transcript_id field (Phase 29 Plan 06, Task 1). Kept in its
own file so its verify run is unaffected by the pre-existing FastAPI test
lifespan/session-factory failure in the broader suite (test_arguments.py etc.).

Test 1 is DB-independent — it never imports api.main, so it never triggers the
app lifespan. Test 2 requires a live DATABASE_URL and mirrors test_arguments.py's
_db_configured() skipif + client fixture pattern.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Test 1: Schema field presence — no database, no api.main import
# ---------------------------------------------------------------------------


def test_argument_metadata_response_has_oyez_transcript_id() -> None:
    """
    ArgumentMetadataResponse must declare oyez_transcript_id: str | None = None.

    - Field must be present in model_fields.
    - Building the model without the field yields oyez_transcript_id is None
      (the PDF-ingested default).
    - Building the model with a value round-trips it (the corpus-sourced case).
    """
    from api.schemas.utterance import ArgumentMetadataResponse

    assert "oyez_transcript_id" in ArgumentMetadataResponse.model_fields

    without_field = ArgumentMetadataResponse(
        argument_id=1,
        case_name="Obergefell v. Hodges",
        docket_number="14-556",
        argued_date="2015-04-28",
        question_number=1,
    )
    assert without_field.oyez_transcript_id is None

    with_field = ArgumentMetadataResponse(
        argument_id=2,
        case_name="Synthetic Historical Case",
        docket_number="1955-71",
        argued_date="1955-11-15",
        question_number=1,
        oyez_transcript_id="13127",
    )
    assert with_field.oyez_transcript_id == "13127"


# ---------------------------------------------------------------------------
# Test 2: Live payload includes oyez_transcript_id — requires real DB
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app (mirrors test_arguments.py)."""
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_utterances_payload_includes_oyez_transcript_id(client: AsyncClient) -> None:
    """
    GET /arguments/{id}/utterances — the argument payload must include the
    oyez_transcript_id key (null for PDF-ingested arguments).

    Creates its own durable Argument/Case/CaseArgument via a committed
    AsyncSessionLocal() session rather than assuming a hardcoded argument_id=1
    row exists (Phase 31, T-31-19: the previous hardcoded-id=1 assumption was
    order-dependent on another test file seeding it first — no test in the
    current suite reliably does that, so it 404'd; this version is
    self-contained). Uses a plain committed session (not the shared
    db_session rollback fixture) because the HTTP client's request handler
    opens its own separate DB session via the app's get_db dependency —
    an uncommitted row in a different session/connection would not be
    visible to it.
    """
    import datetime

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        case = Case(
            docket_number="14-556-OYEZ-FIELD-TEST",
            docket_number_norm="14556OYEZFIELDTEST",
            case_name="Synthetic Oyez-Field Test Case",
            term_year=2015,
            slug="synthetic-oyez-field-test-case",
            oyez_case_id="oyez-field-test",
        )
        db.add(case)
        await db.flush()

        argument = Argument(
            argued_date=None,
            question_number=1,
            source_docket="14-556-OYEZ-FIELD-TEST",
            status=ArgumentStatusEnum.DRAFT,
            # get_argument_with_utterances() gates on published_at (BUG-01/D-02) —
            # this fixture tests the oyez_transcript_id field, not the publish
            # gate, so it publishes the argument to keep the assertion live.
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(argument)
        await db.flush()

        case_argument = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
        db.add(case_argument)
        await db.commit()

        case_id = case.id
        argument_id = argument.id

    try:
        response = await client.get(f"/arguments/{argument_id}/utterances")
        assert response.status_code == 200

        body = response.json()
        assert "oyez_transcript_id" in body["argument"]
    finally:
        # Cleanup — rows above were committed, not protected by any rollback.
        async with AsyncSessionLocal() as db:
            case_argument = await db.get(CaseArgument, (case_id, argument_id))
            if case_argument is not None:
                await db.delete(case_argument)
            argument = await db.get(Argument, argument_id)
            if argument is not None:
                await db.delete(argument)
            case = await db.get(Case, case_id)
            if case is not None:
                await db.delete(case)
            await db.commit()


# ---------------------------------------------------------------------------
# Test 3: ArgumentMetadataResponse accepts a null argued_date — no database
# ---------------------------------------------------------------------------
#
# Regression test for 29-VERIFICATION.md gap #13 / 29-REVIEW.md CR-01: prior
# to this plan's fix, constructing this model with argued_date=None raised
# pydantic.ValidationError: "Input should be a valid date [type=date_type]".
# Real historical rows imported via pipeline/commands/import_convokit.py's
# _parse_argued_date legitimately produce None when cases.jsonl has no
# parseable transcript date.


def test_argument_metadata_response_accepts_null_argued_date() -> None:
    """Constructing ArgumentMetadataResponse with argued_date=None must not raise."""
    from api.schemas.utterance import ArgumentMetadataResponse

    response = ArgumentMetadataResponse(
        argument_id=99,
        case_name="Synthetic Historical Case",
        docket_number="1955-71",
        argued_date=None,
        question_number=1,
        oyez_transcript_id="13127",
    )
    assert response.argued_date is None


# ---------------------------------------------------------------------------
# Test 4: GET /arguments/{id}/utterances survives a null argued_date — DB-gated
# ---------------------------------------------------------------------------
#
# Exercises the real get_argument_with_utterances() -> ArgumentUtterancesResponse
# construction path directly (no HTTP client, no api.main import) to avoid the
# documented pre-existing FastAPI test lifespan/session-factory failure. Uses
# the db_session rollback pattern from test_admin_jobs_phase25.py so this test
# leaves no rows behind and is safely repeatable.


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with a live schema")
async def test_utterances_endpoint_returns_200_for_null_argued_date(db_session) -> None:
    """
    get_argument_with_utterances() -> ArgumentUtterancesResponse must not raise
    for an Argument with argued_date=None — this is the exact 500 (previously
    ResponseValidationError) that GET /arguments/{id}/utterances raised for
    corpus-imported arguments before this plan's fix.

    Does not assert on response.utterances length/contents: whether any
    utterances are returned for a corpus-imported row depends on a separate,
    out-of-scope ImportRun.step="ingest" vs. get_argument_with_utterances'
    step=="parse" filter mismatch (see this plan's <objective>) — an empty
    utterances list is still a valid 200 response for this test's purpose.
    """
    import datetime

    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
    )
    from api.schemas.utterance import ArgumentUtterancesResponse
    from api.services.arguments import get_argument_with_utterances

    case = Case(
        docket_number="1955-99-CR01-TEST",
        docket_number_norm="195599CR01TEST",
        case_name="Synthetic Null-Date Case (CR-01 regression)",
        term_year=1955,
        slug="synthetic-null-date-case-cr01-test",
        oyez_case_id="1955_test_cr01",
    )
    db_session.add(case)
    await db_session.flush()

    argument = Argument(
        argued_date=None,
        question_number=1,
        source_docket="1955-99-CR01-TEST",
        status=ArgumentStatusEnum.DRAFT,
        oyez_transcript_id="synthetic-null-date-transcript-cr01",
        # get_argument_with_utterances() gates on published_at (BUG-01/D-02) —
        # this fixture tests the null-argued_date response shape, not the
        # publish gate, so it publishes the argument to keep the assertion live.
        published_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db_session.add(argument)
    await db_session.flush()

    case_argument = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    db_session.add(case_argument)
    await db_session.flush()

    result = await get_argument_with_utterances(db_session, argument.id)
    assert result is not None

    response = ArgumentUtterancesResponse(**result)
    assert response.argument.argued_date is None
