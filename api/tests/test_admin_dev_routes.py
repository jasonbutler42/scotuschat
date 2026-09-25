"""
End-to-end test for the dev-only "Reset to Fixture" endpoint (Phase 43,
DEVTOOL-01).

DB-dependent tests are gated by _require_test_db(): they skip the whole
module unless TEST_DATABASE_URL is set AND the effective DATABASE_URL
(after tests/conftest.py's redirect) equals it. This is a SECOND,
in-file safety net on top of the root conftest.py redirect — no automated
test in this file may ever execute reset_to_fixture against the shared dev
database (carry-forward constraint from Phase 31).

The synthetic corpus fixture mirrors
pipeline/tests/test_import_convokit_adminjob.py's `_write_corpus_fixture`
shape, extended (Plan 43-02) to all four of FIXTURE_SET's conversations —
15169, 13015, 18897, 22372 — each with its own October-Term-prefixed
`case_id` (matching .planning/FIXTURES.md's Term column) and distinct
docket, so the reseed exercises the real (source_docket, question_number)
uniqueness contract across four different dockets/terms, never the real
900MB corpus.

`corpus_dir` is a Python-level keyword argument used only by tests — the HTTP
client's request carries no body, query parameter, or header naming a
corpus directory at all. Every corpus-dependent test reaches its synthetic
corpus dir by patching api.routers.admin_dev.admin_dev_service.reset_to_fixture
with a thin wrapper that forwards corpus_dir to the real service function —
same module object as api.services.admin_dev, so this is not a redefinition
of the service, just an injected default for the one HTTP call under test.

Phase 52-04 (JUSTICE-04): `_require_corpus_files` now also requires the two
real, gitignored, operator-supplied justice CSVs
(supreme_court_justices_sections.csv, justice_identity_mapping.csv) for
EVERY reset, seeded-bench assertions or not — so `_write_corpus_fixture`
copies both into its synthetic corpus_dir and every test in this module
transitively depends on them being present on this machine. Missing either
one skips the whole module the same way `_require_test_db()` does, via
`_require_real_justice_corpus_files()`.
"""

import csv
import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    Case,
    CourtTenure,
    ImportMethod,
    ImportRun,
    ImportSource,
    Person,
    Role,
    Utterance,
)
from pipeline.commands.import_justices_csv import (
    DEFAULT_CSV_PATH as JUSTICES_CSV_PATH,
    DEFAULT_MAPPING_CSV_PATH as JUSTICE_MAPPING_CSV_PATH,
)

# ===========================================================================
# Shared fixture data — the four FIXTURE_SET conversations, transcribed from
# .planning/FIXTURES.md's Fixture Set table (case_join_id carries the real
# October Term as its "<term>_" prefix, matching that table's Term column;
# docket_no matches that table's Docket(s) column). Titles/speaker
# ids/utterance text are synthetic — the reset response's case_name always
# comes from api.services.admin_dev.FIXTURE_SET, never from these corpus
# files, so assertions below check against FIXTURES.md's names regardless
# of what these synthetic titles say.
# ===========================================================================

FIXTURE_CONVERSATIONS: dict[str, dict] = {
    "15169": {
        "case_join_id": "1966_642",
        "docket_no": "642",
        "title": "Baltimore & Ohio Railroad Company v. United States",
        "petitioner": "Baltimore & Ohio Railroad Company",
        "respondent": "United States",
        "year": 1966,
        "transcript_name": "Oral Argument - January 9, 1967",
    },
    "13015": {
        "case_join_id": "1955_351",
        "docket_no": "351",
        "title": "Archawski v. Hanioti",
        "petitioner": "Archawski",
        "respondent": "Hanioti",
        "year": 1955,
        "transcript_name": "Oral Argument - March 5, 1956",
    },
    "18897": {
        "case_join_id": "1985_84-1602",
        "docket_no": "84-1602",
        "title": "Anderson v. Liberty Lobby, Inc.",
        "petitioner": "Anderson",
        "respondent": "Liberty Lobby, Inc.",
        "year": 1985,
        "transcript_name": "Oral Argument - December 3, 1985",
    },
    "22372": {
        "case_join_id": "2010_09-479",
        "docket_no": "09-479",
        "title": "Abbott v. United States",
        "petitioner": "Abbott",
        "respondent": "United States",
        "year": 2010,
        "transcript_name": "Oral Argument - October 4, 2010",
    },
}

FIXTURE_ORDER = ["15169", "13015", "18897", "22372"]


def _require_test_db() -> None:
    """Skip the whole module unless TEST_DATABASE_URL is set AND the
    effective DATABASE_URL equals it (carry-forward Phase 31 constraint —
    this destructive reset must never run against the shared dev DB)."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url or os.environ.get("DATABASE_URL") != test_url:
        pytest.skip(
            "Requires TEST_DATABASE_URL set and DATABASE_URL redirected to it "
            "(tests/conftest.py) — refusing to run a destructive reset test "
            "without confirmed test-DB isolation."
        )


def _require_real_justice_corpus_files() -> None:
    """Skip the calling test unless the real, gitignored, operator-supplied
    supreme_court_justices_sections.csv and justice_identity_mapping.csv
    are present on this machine (52-04's user_setup precondition).
    reset_to_fixture's pre-flight now hard-requires both for every reset
    (JUSTICE-04), so a skip here means the justice seed step was never
    exercised — not that it passed — mirroring _require_test_db()'s own
    environment-gate pattern rather than letting every test in this module
    fail with a confusing FileNotFoundError from shutil.copy2."""
    if not JUSTICES_CSV_PATH.exists() or not JUSTICE_MAPPING_CSV_PATH.exists():
        pytest.skip(
            f"Requires the real {JUSTICES_CSV_PATH} and "
            f"{JUSTICE_MAPPING_CSV_PATH} on this machine (gitignored, "
            "operator-supplied — see 52-04-PLAN.md's user_setup)."
        )


def _write_corpus_fixture(
    tmp_path: Path,
    *,
    omit_conversation_id: str | None = None,
    justice_speaker_overrides: dict[str, str] | None = None,
) -> Path:
    """Write a synthetic corpus_dir tree containing all four FIXTURE_SET
    conversations (15169, 13015, 18897, 22372) — one advocate turn and one
    bench turn each, with per-conversation-unique speaker ids to avoid
    unintended cross-conversation Person dedup.

    `omit_conversation_id`, when set, drops exactly that one conversation
    from conversations.json (its case/speakers/utterances rows are still
    written) — used by test_reset_incomplete_reseed_raises to simulate a
    partial reseed without inventing a fake fifth conversation id.

    `justice_speaker_overrides`, when given, maps a conversation_id to a
    REAL mapped oyez_speaker_id (e.g. "j__byron_r_white") to use as that
    conversation's justice speaker id in place of the synthetic
    f"j__{conversation_id}" — lets a test resolve that utterance onto the
    already-seeded bench Person row instead of creating a new, unmapped
    one (used by the Success Criterion 2 speaker_name test). The speaker's
    `type` stays "justice" either way — `_is_justice_type` reads that
    field, never the id's naming convention.

    Also copies the real justice CSV + mapping CSV (Phase 52-04) into the
    synthetic corpus_dir, since reset_to_fixture's pre-flight now requires
    both for every reset — see _require_real_justice_corpus_files above,
    called first so a missing pair skips cleanly rather than raising deep
    inside shutil.copy2.
    """
    _require_real_justice_corpus_files()

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    justice_speaker_overrides = justice_speaker_overrides or {}

    conversations: dict = {}
    cases: list[dict] = []
    speakers: dict = {}
    utterances: list[dict] = []

    for conversation_id, meta in FIXTURE_CONVERSATIONS.items():
        advocate_key = f"adv__{conversation_id}"
        justice_key = justice_speaker_overrides.get(
            conversation_id, f"j__{conversation_id}"
        )

        if conversation_id != omit_conversation_id:
            conversations[conversation_id] = {
                "case_id": meta["case_join_id"],
                "advocates": {advocate_key: {"side": 1}},
            }

        cases.append(
            {
                "id": meta["case_join_id"],
                "docket_no": meta["docket_no"],
                "title": meta["title"],
                "petitioner": meta["petitioner"],
                "respondent": meta["respondent"],
                "year": meta["year"],
                "transcripts": [
                    {"id": conversation_id, "name": meta["transcript_name"]}
                ],
            }
        )
        speakers[advocate_key] = {
            "name": f"Advocate {conversation_id}",
            "type": "advocate",
        }
        speakers[justice_key] = {
            "name": f"Justice {conversation_id}",
            "type": "justice",
        }
        utterances.append(
            {
                "id": f"{conversation_id}-u1",
                "conversation_id": conversation_id,
                "speaker": advocate_key,
                "text": "May it please the Court.",
            }
        )
        utterances.append(
            {
                "id": f"{conversation_id}-u2",
                "conversation_id": conversation_id,
                "speaker": justice_key,
                "text": "Counsel, what about the statute's plain text?",
            }
        )

    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    with (corpus_dir / "utterances.jsonl").open("w", encoding="utf-8") as f:
        for row in utterances:
            f.write(json.dumps(row) + "\n")

    shutil.copy2(JUSTICES_CSV_PATH, corpus_dir / JUSTICES_CSV_PATH.name)
    shutil.copy2(JUSTICE_MAPPING_CSV_PATH, corpus_dir / JUSTICE_MAPPING_CSV_PATH.name)

    return corpus_dir


@pytest_asyncio.fixture
async def client():
    """Async httpx test client for the FastAPI app (ASGITransport, no socket)."""
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def db():
    """
    Dedicated session with its own engine, NOT wrapped in an auto-rollback
    transaction — api/tests/conftest.py's db_session fixture wraps the whole
    test in one `session.begin()` block that it rolls back at the end, which
    is unusable here: this test needs its seeded rows and post-reset
    assertions to see genuinely COMMITTED state, since the reset endpoint's
    TRUNCATE and reseed run on a completely separate connection/session
    (get_db's own AsyncSessionLocal, and pipeline.db.get_session() for each
    run_import_convokit call) that cannot see this test's uncommitted rows.
    No rollback needed for THIS destructive test's own seed data — the
    reset's TRUNCATE (or the module-level _require_test_db() gate refusing
    to run at all against a non-test DB) is what keeps this safe.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()


def _admin_headers() -> dict:
    from api.core.config import settings

    return {"X-Admin-Token": settings.admin_token}


async def _post_reset(client, corpus_dir: Path):
    """POST /api/admin/dev/reset-to-fixture, patching in the given synthetic
    corpus_dir via the same corpus_dir-forwarding wrapper technique proven in
    Plan 43-01 (never a request field)."""
    from api.services import admin_dev as admin_dev_service

    real_reset = admin_dev_service.reset_to_fixture

    async def _patched(request_db):
        return await real_reset(request_db, corpus_dir=corpus_dir)

    with patch(
        "api.routers.admin_dev.admin_dev_service.reset_to_fixture", new=_patched
    ):
        return await client.post(
            "/api/admin/dev/reset-to-fixture", headers=_admin_headers()
        )


async def _fetch_argument(db, conversation_id: str) -> Argument:
    db.expire_all()
    return (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalar_one()


async def _fetch_latest_import_run_step(db, argument_id: int) -> str | None:
    """Phase 50 (D-14/D-19, PD-05): replaces _fetch_admin_job -- there is no
    AdminJob for a corpus fixture anymore. Mirrors admin_dev.py's own
    latest_import_run_step derivation (the highest-id ImportRun's step).
    Deliberately does NOT call db.expire_all() (unlike _fetch_argument) --
    callers commonly do `arg = await _fetch_argument(...)` followed by this,
    then keep reading attributes off `arg`; expiring here would force a
    synchronous re-load of `arg`'s already-fetched attributes on next
    access, which raises sqlalchemy.exc.MissingGreenlet outside of an
    explicit await."""
    return (
        await db.execute(
            select(ImportRun.step)
            .where(ImportRun.argument_id == argument_id)
            .order_by(ImportRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@pytest.mark.asyncio
async def test_reset_requires_admin_token(client):
    """POST without a valid X-Admin-Token returns non-200/non-5xx and does
    not mutate the database. Runs without needing a corpus dir at all."""
    _require_test_db()

    resp = await client.post("/api/admin/dev/reset-to-fixture")
    assert resp.status_code != 200
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_reset_wipes_and_reseeds_fixtures(client, tmp_path, db):
    """One HTTP POST wipes the test database and reseeds all four
    FIXTURE_SET conversations through the real import-convokit path, and
    nothing that predated the reset survives."""
    _require_test_db()

    # Seed throwaway rows across every table this reset must clear. Primary
    # keys are captured as plain ints BEFORE the reset (rather than read off
    # the ORM objects afterward) because db.expire_all() below expires every
    # attribute, including each object's own `id` -- re-accessing an expired
    # PK attribute after its row has been TRUNCATEd away would attempt a
    # synchronous lazy-reload that raises sqlalchemy.exc.MissingGreenlet in
    # this async context.
    throwaway_person = Person(full_name="Throwaway Person")
    db.add(throwaway_person)
    await db.flush()
    throwaway_person_id = throwaway_person.id

    throwaway_tenure = CourtTenure(person_id=throwaway_person_id, office="associate")
    db.add(throwaway_tenure)

    throwaway_argument = Argument(
        oyez_transcript_id="not-a-fixture-id",
        status=ArgumentStatusEnum.DRAFT,
    )
    db.add(throwaway_argument)
    await db.flush()
    throwaway_argument_id = throwaway_argument.id

    throwaway_run = ImportRun(
        argument_id=throwaway_argument_id,
        step="resolve",
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
    )
    db.add(throwaway_run)
    await db.flush()
    throwaway_run_id = throwaway_run.id

    throwaway_utterance = Utterance(
        argument_id=throwaway_argument_id,
        import_run_id=throwaway_run_id,
        sequence=0,
        text="Throwaway utterance.",
    )
    db.add(throwaway_utterance)
    await db.commit()
    throwaway_utterance_id = throwaway_utterance.id

    roles_before = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["fixtures"]) == 4

    db.expire_all()

    # Throwaway rows are all gone.
    assert (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == "not-a-fixture-id")
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(Person).where(Person.full_name == "Throwaway Person")
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(CourtTenure).where(CourtTenure.person_id == throwaway_person_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(Utterance).where(Utterance.id == throwaway_utterance_id)
        )
    ).scalar_one_or_none() is None

    # Exactly four Argument rows, the fixture set.
    all_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(all_arguments) == 4
    assert {a.oyez_transcript_id for a in all_arguments} == set(FIXTURE_ORDER)

    # Phase 50 (D-14/D-19): zero AdminJob rows anywhere -- the corpus
    # importer no longer creates one, and TRUNCATE_SQL's admin_jobs entry
    # wiped whatever legacy PDF-path rows existed before this reset.
    all_jobs = (await db.execute(select(AdminJob))).scalars().all()
    assert len(all_jobs) == 0

    # The fixtures' own people were created.
    person_count = (
        await db.execute(select(func.count()).select_from(Person))
    ).scalar_one()
    assert person_count > 0

    # roles table untouched — same row count before and after.
    roles_after = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()
    assert roles_after == roles_before


@pytest.mark.asyncio
async def test_reset_response_order_is_declaration_order(client, tmp_path, db):
    """The response's four conversation_id values, read in array order, are
    exactly FIXTURE_ORDER — on both a first and second consecutive run
    (Edge probe: ordering)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200
    order1 = [f["conversation_id"] for f in resp1.json()["fixtures"]]
    assert order1 == FIXTURE_ORDER

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200
    order2 = [f["conversation_id"] for f in resp2.json()["fixtures"]]
    assert order2 == FIXTURE_ORDER


@pytest.mark.asyncio
async def test_reset_is_repeatable(client, tmp_path, db):
    """Running the reset twice in a row produces the identical four-fixture
    end state: still exactly four arguments, no duplicates, and the same
    per-docket question_number values as the first run (Edge probe:
    adjacency)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200

    db.expire_all()
    first_run_numbers = {
        a.oyez_transcript_id: (a.source_docket, a.question_number)
        for a in (await db.execute(select(Argument))).scalars().all()
    }
    assert len(first_run_numbers) == 4
    # Commit (ends this session's implicit read transaction) before the
    # second reset's own TRUNCATE runs on a separate session/connection —
    # Postgres's TRUNCATE takes ACCESS EXCLUSIVE, which conflicts with any
    # still-open transaction that has touched the same table, even a bare
    # SELECT (autobegin leaves the transaction open until commit/rollback).
    # Leaving this uncommitted deadlocks the second POST against this
    # fixture's own held lock.
    await db.commit()

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200

    db.expire_all()
    second_run_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(second_run_arguments) == 4
    assert {a.oyez_transcript_id for a in second_run_arguments} == set(FIXTURE_ORDER)

    seen_pairs = set()
    for argument in second_run_arguments:
        pair = (argument.source_docket, argument.question_number)
        assert pair not in seen_pairs, "duplicate (source_docket, question_number) pair"
        seen_pairs.add(pair)
        assert pair == first_run_numbers[argument.oyez_transcript_id]


@pytest.mark.asyncio
async def test_reset_against_empty_database(client, tmp_path, db):
    """A reset against an already-empty database succeeds and produces the
    same four-fixture end state as a reset against a populated one — TRUNCATE
    over empty tables is a no-op, not an error (Edge probe: empty)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    # Reach a known state, then TRUNCATE the wipe set directly to reach a
    # genuinely empty database (bypassing the reset's own reseed step).
    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200

    from api.services.admin_dev import TRUNCATE_SQL
    from sqlalchemy import text

    await db.execute(text(TRUNCATE_SQL))
    await db.commit()

    db.expire_all()
    empty_count = (
        await db.execute(select(func.count()).select_from(Argument))
    ).scalar_one()
    assert empty_count == 0
    # Commit before the second reset's TRUNCATE (see test_reset_is_repeatable
    # for why an uncommitted read-only transaction here would deadlock it).
    await db.commit()

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200
    body = resp2.json()
    assert len(body["fixtures"]) == 4
    assert [f["conversation_id"] for f in body["fixtures"]] == FIXTURE_ORDER

    db.expire_all()
    all_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(all_arguments) == 4
    assert {a.oyez_transcript_id for a in all_arguments} == set(FIXTURE_ORDER)


@pytest.mark.asyncio
async def test_reset_incomplete_reseed_raises(client, tmp_path, db):
    """A synthetic corpus missing one of the four conversations causes a
    failure, not a 200 with a three-item fixtures array."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path, omit_conversation_id="22372")

    resp = await _post_reset(client, corpus_dir)

    assert resp.status_code != 200
    assert resp.status_code >= 500


@pytest.mark.asyncio
async def test_reset_realizes_state_variety(client, tmp_path, db):
    """All four fixtures land in four mutually distinguishable end states
    after the reset (D-03, D-04)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    # Capture status/step values as PLAIN LOCALS immediately after each
    # fetch pair -- _fetch_argument's own db.expire_all() (and the next
    # iteration's) would otherwise expire an earlier iteration's already-
    # loaded `argument` object, and re-accessing an expired attribute
    # outside an explicit await raises sqlalchemy.exc.MissingGreenlet in
    # this async context (same discipline test_reset_writes_status_log_rows
    # already uses for `.id`).

    # 15169 (Complexity): untouched freshly-imported default -- candidate,
    # latest ImportRun at step="parse" (Phase 50 D-14/D-19: no AdminJob).
    complexity_arg = await _fetch_argument(db, "15169")
    complexity_status = complexity_arg.status
    assert complexity_status == ArgumentStatusEnum.CANDIDATE
    assert complexity_arg.resolved_at is None
    assert complexity_arg.published_at is None
    complexity_step = await _fetch_latest_import_run_step(db, complexity_arg.id)
    assert complexity_step == "parse"

    # 13015 (Draft): CANDIDATE -> DRAFT via approve_argument, latest
    # ImportRun still step="parse" (approve_argument writes no ImportRun).
    draft_arg = await _fetch_argument(db, "13015")
    draft_status = draft_arg.status
    assert draft_status == ArgumentStatusEnum.DRAFT
    assert draft_arg.resolved_at is not None
    assert draft_arg.published_at is None
    draft_step = await _fetch_latest_import_run_step(db, draft_arg.id)
    assert draft_step == "parse"

    # 18897 (Published): CANDIDATE -> DRAFT -> PUBLISHED, latest ImportRun
    # still step="parse".
    published_arg = await _fetch_argument(db, "18897")
    published_status = published_arg.status
    assert published_status == ArgumentStatusEnum.PUBLISHED
    assert published_arg.resolved_at is not None
    assert published_arg.published_at is not None
    published_step = await _fetch_latest_import_run_step(db, published_arg.id)
    assert published_step == "parse"

    # 22372 (Mid-pipeline): stays CANDIDATE, a step="reconcile" ImportRun is
    # seeded (OQ-2) -- its highest id makes it the "latest" run.
    mid_arg = await _fetch_argument(db, "22372")
    mid_status = mid_arg.status
    assert mid_status == ArgumentStatusEnum.CANDIDATE
    assert mid_arg.resolved_at is None
    mid_step = await _fetch_latest_import_run_step(db, mid_arg.id)
    assert mid_step == "reconcile"

    # PD-05: all four fixtures are distinguishable by the
    # (argument_status, latest_import_run_step) pair.
    pairs = {
        (complexity_status.value, complexity_step),
        (draft_status.value, draft_step),
        (published_status.value, published_step),
        (mid_status.value, mid_step),
    }
    assert len(pairs) == 4

    # Zero AdminJob rows anywhere (Phase 50 D-14/D-19 -- none created).
    all_jobs = (await db.execute(select(AdminJob))).scalars().all()
    assert len(all_jobs) == 0


@pytest.mark.asyncio
async def test_reset_writes_status_log_rows(client, tmp_path, db):
    """argument_status_log has at least two rows for 13015 (the CANDIDATE
    birth log plus its DRAFT transition) and at least two for 18897 (birth
    plus PUBLISHED), and EXACTLY one row -- the CANDIDATE birth log, no
    more -- for 15169/22372 (which never left the candidate state) — proof
    the transitions went through the real service functions, not a column
    write.

    Phase 48 D-03 changed what "never left the candidate state" means for
    this assertion: every corpus-imported argument now gets a birth-state
    ArgumentStatusLog row (import_convokit.py, plan 48-05 Task 1), so
    15169/22372 carry exactly one row each rather than zero -- this test's
    original zero-row expectation predates that write site and is now
    stale, not a sign of a missing DRAFT/PUBLISHED transition."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    # Capture each argument's id immediately after its own fetch -- the
    # NEXT _fetch_argument call's internal db.expire_all() would otherwise
    # expire this object's own `id` attribute too, and re-accessing an
    # expired attribute later (outside an explicit await) raises
    # sqlalchemy.exc.MissingGreenlet in this async context.
    draft_argument_id = (await _fetch_argument(db, "13015")).id
    published_argument_id = (await _fetch_argument(db, "18897")).id
    complexity_argument_id = (await _fetch_argument(db, "15169")).id
    mid_argument_id = (await _fetch_argument(db, "22372")).id

    async def _log_count(argument_id: int) -> int:
        return (
            await db.execute(
                select(func.count())
                .select_from(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == argument_id)
            )
        ).scalar_one()

    assert await _log_count(draft_argument_id) >= 2  # birth + DRAFT
    assert await _log_count(published_argument_id) >= 2  # birth + PUBLISHED
    assert await _log_count(complexity_argument_id) == 1  # birth only
    assert await _log_count(mid_argument_id) == 1  # birth only


@pytest.mark.asyncio
async def test_reset_response_reports_realized_states(client, tmp_path, db):
    """Each response item's argument_status and latest_import_run_step
    fields match the values read back from the database, not values
    assumed from FIXTURE_SET (Phase 50 D-14/D-19, PD-05 -- replaces the
    retired AdminJob-status field, which no longer exists)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200
    body = resp.json()

    seen_pairs = set()
    for item in body["fixtures"]:
        argument = await _fetch_argument(db, item["conversation_id"])
        latest_step = await _fetch_latest_import_run_step(db, argument.id)
        assert item["argument_status"] == argument.status.value
        assert item["latest_import_run_step"] == latest_step
        seen_pairs.add((item["argument_status"], item["latest_import_run_step"]))

    # PD-05: all four fixtures are distinguishable by the
    # (argument_status, latest_import_run_step) pair.
    assert len(seen_pairs) == 4


@pytest.mark.asyncio
async def test_reset_status_log_created_at_monotonic_with_id(client, tmp_path, db):
    """argument_status_log rows, ordered by id, are also non-decreasing by
    created_at for both multi-transition fixtures (13015/Draft,
    18897/Published) -- the invariant that silently broke because
    reset_to_fixture reused one long-lived transaction across its
    fixture-verification loop and its state-realization block. PostgreSQL's
    now() is transaction-START time, not statement time, so a DRAFT row
    written late in that transaction was stamped earlier than the CANDIDATE
    row that logically preceded it (2026-08-20 todo, Task 2 fix). Also
    checks arguments.resolved_at on the Draft fixture is not earlier than
    its own CANDIDATE status-log row."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    candidate_created_at_by_conversation: dict[str, object] = {}

    for conversation_id in ("13015", "18897"):
        argument = await _fetch_argument(db, conversation_id)
        rows = (
            await db.execute(
                select(ArgumentStatusLog.id, ArgumentStatusLog.status, ArgumentStatusLog.created_at)
                .where(ArgumentStatusLog.argument_id == argument.id)
                .order_by(ArgumentStatusLog.id.asc())
            )
        ).all()
        assert len(rows) >= 2, f"expected >=2 status-log rows for {conversation_id!r}"

        timestamps = [created_at for _, _, created_at in rows]
        assert timestamps == sorted(timestamps), (
            f"argument_status_log rows for conversation {conversation_id!r} "
            f"are not monotonic by id: {rows}"
        )

        candidate_row = next(
            (row for row in rows if row[1] == ArgumentStatusEnum.CANDIDATE), None
        )
        assert candidate_row is not None, (
            f"expected a CANDIDATE birth-state row for {conversation_id!r}"
        )
        candidate_created_at_by_conversation[conversation_id] = candidate_row[2]

    draft_argument = await _fetch_argument(db, "13015")
    assert draft_argument.resolved_at is not None
    assert draft_argument.resolved_at >= candidate_created_at_by_conversation["13015"]


# ===========================================================================
# Phase 52-04 (JUSTICE-04) — the justice bench seed step inside
# reset_to_fixture. All five tests below exercise the REAL
# data/corpus/supreme_court_justices_sections.csv and
# data/corpus/justice_identity_mapping.csv (copied into the synthetic
# corpus_dir by _write_corpus_fixture) rather than a hand-built fixture, so
# a "skipped" outcome here always means the seed step was never exercised,
# not that it passed.
# ===========================================================================


def _load_real_justice_mapping_ids() -> set[str]:
    """The full set of oyez_speaker_id values in the real, verified mapping
    CSV -- read directly, independent of the importer's own parsing, so
    this is a genuine cross-check rather than the importer grading its own
    homework."""
    ids: set[str] = set()
    with JUSTICE_MAPPING_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.add((row.get("oyez_speaker_id") or "").strip())
    return ids


async def _fetch_seeded_bench_person_rows(db) -> list:
    """Every (id, oyez_speaker_id) pair for a Person seeded by the justice
    bench step -- identified via court_tenures, which ONLY
    run_import_justices_csv ever writes, so this never picks up the
    FIXTURE_SET's own synthetic justice-type speakers (which get no
    court_tenures row)."""
    db.expire_all()
    justice_person_ids = (
        (await db.execute(select(CourtTenure.person_id).distinct())).scalars().all()
    )
    if not justice_person_ids:
        return []
    rows = (
        await db.execute(
            select(Person.id, Person.oyez_speaker_id).where(
                Person.id.in_(justice_person_ids)
            )
        )
    ).all()
    return rows


@pytest.mark.asyncio
async def test_reset_seeds_full_justice_roster(client, tmp_path, db):
    """After a reset, people carries the full 116-distinct-person justice
    roster from the real 121-row supreme_court_justices_sections.csv, and
    court_tenures carries both rows for each of the five dual-service
    justices (Rutledge, E.D. White, Hughes, Stone, Rehnquist) -- Success
    Criterion 3, proven through the real reset path, not just the four
    FIXTURE_SET conversations' own synthetic advocates/justices."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    db.expire_all()
    justice_person_ids = (
        (await db.execute(select(CourtTenure.person_id).distinct())).scalars().all()
    )
    assert len(justice_person_ids) == 116

    tenure_counts = (
        await db.execute(
            select(CourtTenure.person_id, func.count())
            .where(CourtTenure.person_id.in_(justice_person_ids))
            .group_by(CourtTenure.person_id)
        )
    ).all()
    dual_service_count = sum(1 for _, count in tenure_counts if count == 2)
    assert dual_service_count == 5
    assert all(count in (1, 2) for _, count in tenure_counts)


@pytest.mark.asyncio
async def test_reset_seeded_oyez_ids_unique_and_match_mapping(client, tmp_path, db):
    """Every people.oyez_speaker_id written by the seed step is unique
    (JUSTICE-04 / adjacency -- the partial unique index would refuse a
    duplicate at the database, and this proves the seed's own dedup logic
    never even attempts one), and the set of non-null ids exactly matches
    the mapping CSV's own 114-id set. Exactly 2 of the 116 seeded justices
    (Barrett, Jackson -- D-04) are unmapped."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    rows = await _fetch_seeded_bench_person_rows(db)
    assert len(rows) == 116

    non_null_ids = [oyez_id for _, oyez_id in rows if oyez_id is not None]
    assert len(non_null_ids) == len(set(non_null_ids)), (
        "duplicate oyez_speaker_id among seeded justices"
    )
    assert len(rows) - len(non_null_ids) == 2

    mapping_ids = _load_real_justice_mapping_ids()
    assert set(non_null_ids) == mapping_ids


@pytest.mark.asyncio
async def test_reset_justice_seed_is_idempotent(client, tmp_path, db):
    """Running reset_to_fixture twice in a row leaves the identical seeded
    justice-roster count and the identical non-null oyez_speaker_id set as
    running it once (JUSTICE-04 / idempotency)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200

    first_rows = await _fetch_seeded_bench_person_rows(db)
    first_non_null_ids = {oyez_id for _, oyez_id in first_rows if oyez_id is not None}
    # Commit before the second reset's TRUNCATE — an open read transaction
    # here (even a bare SELECT) deadlocks against TRUNCATE's ACCESS
    # EXCLUSIVE lock (same discipline as test_reset_is_repeatable above).
    await db.commit()

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200

    second_rows = await _fetch_seeded_bench_person_rows(db)
    second_non_null_ids = {oyez_id for _, oyez_id in second_rows if oyez_id is not None}

    assert len(first_rows) == len(second_rows) == 116
    assert first_non_null_ids == second_non_null_ids


@pytest.mark.asyncio
async def test_reset_missing_justice_csv_raises_before_truncate(client, tmp_path, db):
    """A corpus directory missing one of the two required justice CSVs
    raises CorpusUnavailableError, proven by a pre-seeded people row still
    existing afterward -- not merely by the exception type (JUSTICE-04 /
    empty: an absent mapping must never be able to leave the database
    empty, because the pre-flight runs BEFORE the TRUNCATE)."""
    _require_test_db()
    from api.services.admin_dev import CorpusUnavailableError, reset_to_fixture

    corpus_dir = _write_corpus_fixture(tmp_path)
    (corpus_dir / JUSTICE_MAPPING_CSV_PATH.name).unlink()

    sentinel = Person(full_name="Pre-Flight Sentinel Person, 52-04")
    db.add(sentinel)
    await db.commit()
    sentinel_id = sentinel.id

    with pytest.raises(CorpusUnavailableError):
        await reset_to_fixture(db, corpus_dir=corpus_dir)

    db.expire_all()
    assert (
        await db.execute(select(Person).where(Person.id == sentinel_id))
    ).scalar_one_or_none() is not None, (
        "the TRUNCATE ran despite the missing justice CSV — the pre-flight "
        "did not refuse before the destructive statement"
    )


@pytest.mark.asyncio
async def test_reset_justice_utterance_speaker_name_uses_corpus_display_form(
    client, tmp_path, db
):
    """Reset with one fixture's justice speaker id overridden to a REAL
    mapped oyez_speaker_id (j__byron_r_white): that utterance's person is
    the already-seeded bench row, whose display_name ("Byron R. White") is
    what speaker_name coalesces to; the fixture's advocate is unaffected --
    Success Criterion 2 / JUSTICE-03, proven through the reset path rather
    than a hand-built fixture."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(
        tmp_path, justice_speaker_overrides={"15169": "j__byron_r_white"}
    )
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    argument = await _fetch_argument(db, "15169")

    rows = (
        await db.execute(
            select(Person.is_justice, Person.full_name, Person.display_name)
            .join(Utterance, Utterance.person_id == Person.id)
            .where(Utterance.argument_id == argument.id)
        )
    ).all()

    justice_rows = [row for row in rows if row[0] is True]
    advocate_rows = [row for row in rows if row[0] is False]
    assert len(justice_rows) == 1
    assert len(advocate_rows) == 1

    _, justice_full_name, justice_display_name = justice_rows[0]
    assert justice_display_name == "Byron R. White"
    assert justice_full_name == "Byron Raymond White"

    _, advocate_full_name, advocate_display_name = advocate_rows[0]
    assert advocate_display_name is None
    assert advocate_full_name == "Advocate 15169"


# ===========================================================================
# Phase 52-05 (D-14/D-15) — GET /api/admin/dev/fixture-state, the read-only
# re-read the frontend's resetToFixture action consults on any failure, and
# the source of the Running state's per-fixture progress polling.
# ===========================================================================


async def _get_fixture_state(client):
    return await client.get(
        "/api/admin/dev/fixture-state", headers=_admin_headers()
    )


async def _table_row_counts(db) -> dict[str, int]:
    """Row counts across every table Phase 52-05's TRUNCATE_SQL names plus
    the two FK-reached-only-by-CASCADE tables this module's fixtures ever
    touch — used to prove get_fixture_state performs no write (a snapshot
    identical before and after, not merely a 200 status)."""
    db.expire_all()
    counts: dict[str, int] = {}
    for label, model in (
        ("people", Person),
        ("court_tenures", CourtTenure),
        ("cases", Case),
        ("arguments", Argument),
        ("argument_participants", ArgumentParticipant),
        ("utterances", Utterance),
        ("import_run", ImportRun),
        ("admin_jobs", AdminJob),
    ):
        counts[label] = (
            await db.execute(select(func.count()).select_from(model))
        ).scalar_one()
    return counts


@pytest.mark.asyncio
async def test_fixture_state_before_reset_reports_all_absent(client, db):
    """Before any reset, every FIXTURE_SET entry reports present=False with
    every nullable field null, in declaration order, and progress is None
    (no reset in flight)."""
    _require_test_db()

    # This test's own TRUNCATE-adjacent isolation: reset_to_fixture always
    # TRUNCATEs on entry, so calling it once with an empty synthetic corpus
    # dir would itself populate fixtures -- instead, directly TRUNCATE the
    # same table set here so this test asserts the true pre-reset state
    # without depending on another test's ordering.
    from sqlalchemy import text as sa_text

    from api.services.admin_dev import TRUNCATE_SQL

    await db.execute(sa_text(TRUNCATE_SQL))
    await db.commit()

    resp = await _get_fixture_state(client)
    assert resp.status_code == 200
    body = resp.json()

    assert body["progress"] is None
    assert [f["conversation_id"] for f in body["fixtures"]] == FIXTURE_ORDER
    for fixture in body["fixtures"]:
        assert fixture["present"] is False
        assert fixture["argument_id"] is None
        assert fixture["status"] is None
        assert fixture["latest_import_run_step"] is None


@pytest.mark.asyncio
async def test_fixture_state_after_reset_reports_expected_states(
    client, tmp_path, db
):
    """After a successful reset, the re-read reports all four fixtures
    present, in FIXTURE_SET declaration order, each carrying the exact
    per-role end-state reset_to_fixture's own state-realization block
    leaves behind -- the same evidence the frontend's D-14 re-read
    interprets as full success."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    reset_resp = await _post_reset(client, corpus_dir)
    assert reset_resp.status_code == 200

    resp = await _get_fixture_state(client)
    assert resp.status_code == 200
    body = resp.json()

    assert body["progress"] is None
    assert [f["conversation_id"] for f in body["fixtures"]] == FIXTURE_ORDER

    expected_by_conversation = {
        "15169": ("candidate", "parse"),
        "13015": ("draft", "parse"),
        "18897": ("published", "parse"),
        "22372": ("candidate", "reconcile"),
    }
    for fixture in body["fixtures"]:
        expected_status, expected_step = expected_by_conversation[
            fixture["conversation_id"]
        ]
        assert fixture["present"] is True
        assert fixture["argument_id"] is not None
        assert fixture["status"] == expected_status
        assert fixture["latest_import_run_step"] == expected_step


@pytest.mark.asyncio
async def test_fixture_state_performs_no_write(client, tmp_path, db):
    """Calling GET /fixture-state twice in a row, after a reset, leaves
    every table's row count byte-identical -- proven by a before/after
    snapshot comparison across every TRUNCATE_SQL table, not merely by
    asserting a 200 status (must_haves: 'The endpoint performs no write')."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    reset_resp = await _post_reset(client, corpus_dir)
    assert reset_resp.status_code == 200
    await db.commit()

    before = await _table_row_counts(db)

    resp1 = await _get_fixture_state(client)
    assert resp1.status_code == 200
    after_first = await _table_row_counts(db)
    assert after_first == before

    resp2 = await _get_fixture_state(client)
    assert resp2.status_code == 200
    after_second = await _table_row_counts(db)
    assert after_second == before


@pytest.mark.asyncio
async def test_fixture_state_requires_admin_token(client):
    """GET without a valid X-Admin-Token returns non-200/non-5xx, mirroring
    test_reset_requires_admin_token's own assertion shape."""
    _require_test_db()

    resp = await client.get("/api/admin/dev/fixture-state")
    assert resp.status_code != 200
    assert resp.status_code < 500
