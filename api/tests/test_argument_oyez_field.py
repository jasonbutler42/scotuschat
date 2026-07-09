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
    GET /arguments/1/utterances — the argument payload must include the
    oyez_transcript_id key (null for PDF-ingested arguments).
    """
    response = await client.get("/arguments/1/utterances")
    assert response.status_code == 200

    body = response.json()
    assert "oyez_transcript_id" in body["argument"]
