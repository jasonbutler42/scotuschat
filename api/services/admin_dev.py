"""
Dev-only destructive reset service (Phase 43, DEVTOOL-01/DEVTOOL-02).

D-07 keeps this module's router (api/routers/admin_dev.py) unmounted outside
development — settings.environment must equal "development" for
reset_to_fixture to ever be reachable over HTTP at all (see api/main.py's
guarded include_router call).

NOT ATOMIC (RESEARCH.md Pitfall 1): the reset is several independently-
committing units, not one transaction —
    1. the TRUNCATE runs on FastAPI's own AsyncSession (this module's `db`
       argument) and commits immediately;
    2. each `run_import_convokit` call opens and commits its own session via
       pipeline.db.get_session() — a SEPARATE engine/pool from FastAPI's
       AsyncSessionLocal, pointed at the same DATABASE_URL;
    3. the state-realization block below (Plan 43-02) commits via the real
       admin_jobs.approve_job / admin_arguments.publish_argument service
       calls (each on this module's own `db` session) plus one direct
       AdminJob.status bulk update/commit for the Mid-pipeline fixture.
Do NOT attempt to wrap the whole thing in one `async with db.begin():` —
that session boundary never extends into pipeline's own engine. On any
failure, the correct recovery is to re-run the whole reset: the TRUNCATE is
idempotent-safe to re-invoke from any partial state.

Performance note: run_import_convokit streams the whole
data/corpus/utterances.jsonl file once per conversation, and each of the
four fixtures below is in a different October Term, so a real-corpus reset
performs four full passes over that file. Measured on the development
machine at plan time: one pass over 900,080,134 bytes costs approximately
20.4 seconds, so expect roughly 80-120 seconds end to end for a real-corpus
reset. This is a dev-only tool on localhost with no proxy in the path — do
not add a timeout, a background job, or a progress channel; the UI-SPEC's
Running state is a deliberately blocking request with a spinner.
"""

from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    Argument,
    ArgumentParticipant,
    ReviewState,
    SideEnum,
)
from api.services import admin_arguments as arguments_service
from api.services import admin_jobs as jobs_service
from api.services.trust import recompute_argument_tier
from pipeline.commands.import_convokit import DEFAULT_CORPUS_DIR, run_import_convokit
from pipeline.corpus.loader import (
    CASES_FILENAME,
    CONVERSATIONS_FILENAME,
    SPEAKERS_FILENAME,
    UTTERANCES_FILENAME,
)


class CorpusUnavailableError(Exception):
    """Raised when the corpus directory or one of its four required raw files
    is missing. Always raised BEFORE the TRUNCATE runs (RESEARCH.md Pitfall
    6), so a corpus-missing failure leaves the database completely
    untouched."""


class ResetIncompleteError(Exception):
    """Raised when a fixture's Argument row does not exist after
    run_import_convokit returns, when run_import_convokit itself raises for
    a fixture (e.g. an unresolvable/missing conversation id — RESEARCH.md
    Open Question 2), or when a fixture landed without its required paired
    AdminJob row. run_import_convokit catches and counts per-conversation
    exceptions internally rather than always raising, so success is never
    inferred from the mere absence of an exception — this module always
    verifies both rows exist for every fixture before ever returning a
    success response. A short `fixtures` list is never a valid 200."""


class FixtureNotSeededError(Exception):
    """Raised by seed_unresolved_speaker_fixture when the target fixture
    argument does not exist, or exists but has no eligible participant to
    null. An un-reset database is the expected cause — mirrors
    ResetIncompleteError's own reasoning: this function never returns
    success with nothing done."""


# Single source of truth for both the reseed loop and the response
# case_name/role values, transcribed from .planning/FIXTURES.md (status
# CONFIRMED, operator-confirmed 2026-07-29) — that file is the authority if
# these values ever disagree with this constant. Declaration order is the
# response order (Complexity, then Draft, then Published, then
# Mid-pipeline), and the /admin Success list renders this order verbatim.
FIXTURE_SET: list[dict] = [
    {
        "conversation_id": "15169",
        "case_name": "Baltimore & Ohio Railroad Company v. United States",
        "role": "Complexity",
    },
    {
        "conversation_id": "13015",
        "case_name": "Archawski v. Hanioti",
        "role": "Draft",
    },
    {
        "conversation_id": "18897",
        "case_name": "Anderson v. Liberty Lobby, Inc.",
        "role": "Published",
    },
    {
        "conversation_id": "22372",
        "case_name": "Abbott v. United States",
        "role": "Mid-pipeline",
    },
]

# D-01's nine named tables, ending with CASCADE. CASCADE also transitively
# reaches three tables NOT named here: case_appearances (FK -> cases,
# people), speaker_alias (FK -> people), and argument_status_log
# (FK -> arguments) — naming them explicitly is unnecessary, CASCADE makes
# the result identical either way (RESEARCH.md Open Question 1, resolved in
# favor of the explicit 9-table list for auditability).
#
# `roles` is deliberately EXCLUDED — D-01 excludes lookup tables. `roles` is
# the parent of people.role_id / case_appearances.role_id (upstream), not a
# child reached by CASCADE from any table in this list.
#
# One piece of state this reset destroys and does NOT restore: the
# speaker_alias rows seeded independently by pipeline/commands/seed_aliases.py
# are removed by CASCADE and are not recreated here, because the corpus
# importer resolves people by oyez_speaker_id/full_name and never reads or
# writes that table. Re-running the alias seeder is deliberately out of
# scope for this reset — noted here so a later PDF-pipeline resolve step
# starting from an empty alias table is not mistaken for a defect.
TRUNCATE_SQL = """
    TRUNCATE TABLE
        utterances,
        import_run,
        case_arguments,
        argument_participants,
        arguments,
        cases,
        court_tenures,
        people,
        admin_jobs
    CASCADE
"""


def _require_corpus_files(corpus_dir: Path) -> None:
    """Pre-flight check, BEFORE any destructive statement (Pitfall 6)."""
    if not corpus_dir.is_dir():
        raise CorpusUnavailableError(f"Corpus directory not found: {corpus_dir}")
    for filename in (
        CONVERSATIONS_FILENAME,
        CASES_FILENAME,
        SPEAKERS_FILENAME,
        UTTERANCES_FILENAME,
    ):
        required = corpus_dir / filename
        if not required.exists():
            raise CorpusUnavailableError(f"Required corpus file not found: {required}")


async def reset_to_fixture(db: AsyncSession, corpus_dir: str | Path | None = None) -> dict:
    """
    Wipe the full D-01 table set, reseed exactly FIXTURE_SET's conversations
    through the real import-convokit path, then drive the three
    state-variety fixtures into their distinguishable end states (D-03,
    D-04).

    `corpus_dir` is a Python-level keyword argument used only by tests — it
    is NEVER exposed as a request body field, query parameter, or header on
    the reset endpoint (must_haves prohibition). Production callers always
    invoke this with corpus_dir=None, resolving to
    pipeline.commands.import_convokit.DEFAULT_CORPUS_DIR.

    Returns a dict shaped for api.schemas.admin_dev.ResetToFixtureResponse.
    """
    # 1. Pre-flight — before any destructive statement (Pitfall 6).
    resolved_corpus_dir = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
    _require_corpus_files(resolved_corpus_dir)

    # 2. TRUNCATE — one statement, one transaction, per D-01.
    await db.execute(text(TRUNCATE_SQL))
    await db.commit()

    # 3-4. Reseed each fixture through the real importer, then verify both
    # its Argument row and its paired AdminJob row landed. Collect
    # (entry, argument_id, admin_job_id) triples in FIXTURE_SET declaration
    # order for the state-realization step below.
    fixture_rows: list[tuple[dict, int, int]] = []
    for entry in FIXTURE_SET:
        conversation_id = entry["conversation_id"]

        try:
            await run_import_convokit(
                SimpleNamespace(
                    conversation_id=conversation_id,
                    corpus_dir=str(resolved_corpus_dir),
                )
            )
        except Exception as exc:
            # run_import_convokit's own per-conversation resilience only
            # wraps the per-term _import_conversation call; a scoped
            # --conversation-id lookup failure (e.g. the id is genuinely
            # absent from conversations.json) raises BEFORE that guard, so
            # this module must catch it here rather than let an unrelated
            # exception type escape as an unhandled 500 (RESEARCH.md Open
            # Question 2). Either way, a partial reseed never reports
            # success — it always surfaces as ResetIncompleteError.
            raise ResetIncompleteError(
                f"Conversation {conversation_id!r} failed to import — "
                f"reset is incomplete ({exc!r})."
            ) from exc

        argument = (
            await db.execute(
                select(Argument).where(Argument.oyez_transcript_id == conversation_id)
            )
        ).scalar_one_or_none()
        if argument is None:
            raise ResetIncompleteError(
                f"Conversation {conversation_id!r} did not land an Argument row "
                "after run_import_convokit — reset is incomplete."
            )

        admin_job = (
            await db.execute(
                select(AdminJob).where(AdminJob.argument_id == argument.id)
            )
        ).scalar_one_or_none()
        if admin_job is None:
            # Phase 30 invariant: every corpus-imported argument must land
            # paired with exactly one AdminJob, or it is unpublishable. A
            # fixture missing its AdminJob is exactly as incomplete as a
            # fixture missing its Argument row.
            raise ResetIncompleteError(
                f"Conversation {conversation_id!r} landed an Argument row but "
                "no paired AdminJob — reset is incomplete."
            )

        fixture_rows.append((entry, argument.id, admin_job.id))

    # 5. State realization (D-03, D-04) — runs strictly AFTER every fixture
    # has landed and passed its existence checks above, so every Argument
    # and AdminJob row referenced below is guaranteed to exist before any
    # transition is attempted. Looked up by id collected during the reseed
    # loop, never assumed.
    ids_by_conversation = {
        entry["conversation_id"]: (argument_id, admin_job_id)
        for entry, argument_id, admin_job_id in fixture_rows
    }

    # Fixture 15169 (Complexity): no action. It stays exactly as the
    # importer left it — status=CANDIDATE with a PAUSED/RESOLVE AdminJob.
    # This is deliberate: it is the reference "freshly imported" state and
    # the Phase 30 invariant's canonical shape.

    # Fixture 13015 (Draft target): CANDIDATE -> DRAFT via the real service
    # function (D-03). approve_job stamps resolved_at, marks the AdminJob
    # COMPLETED, and writes the ArgumentStatusLog row — this module performs
    # none of those writes itself.
    _draft_argument_id, draft_job_id = ids_by_conversation["13015"]
    await jobs_service.approve_job(db, draft_job_id)

    # Fixture 18897 (Published target): TWO calls, in this order, and the
    # order is NOT optional. approve_job must run first to reach DRAFT and
    # stamp resolved_at — publish_argument raises ValueError("Cannot
    # publish: resolve step not yet complete") when resolved_at is still
    # null, which is exactly the state a freshly-imported CANDIDATE argument
    # is in. Do not "simplify" these two calls into one.
    published_argument_id, published_job_id = ids_by_conversation["18897"]
    await jobs_service.approve_job(db, published_job_id)
    await arguments_service.publish_argument(db, published_argument_id)

    # Fixture 22372 (Mid-pipeline target, D-04): the ONE direct column
    # write in this service, and it is deliberately NOT a D-03 violation —
    # D-03 is scoped to Argument.status transitions, not to AdminJob.status.
    # There is no ArgumentStatusLog-style audit table for AdminJob.status,
    # and no existing service function performs a PAUSED -> RUNNING flip:
    # the real step-advance guards try_advance_ingest_to_parse and
    # try_advance_parse_to_resolve handle different step pairs entirely and
    # must not be repurposed here (RESEARCH.md Pitfall 3). The simple flip
    # (rather than partially resolving some ArgumentParticipant rows) is
    # taken because (a) the Complexity fixture already gives Phase 44's
    # Resolve Table Rework a fully editable CANDIDATE argument with a
    # PAUSED/RESOLVE job, so partially resolving participants here would add
    # implementation cost without unlocking anything Phase 44 lacks, and
    # (b) resolve-card editability keys on Argument.status staying CANDIDATE,
    # which this flip preserves (Argument.resolved_at stays null, unchanged).
    _mid_argument_id, mid_job_id = ids_by_conversation["22372"]
    await db.execute(
        update(AdminJob)
        .where(AdminJob.id == mid_job_id)
        .values(status=AdminJobStatus.RUNNING)
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    # 6. Build the response strictly from values re-read from the database
    # after every transition above has committed — never from FIXTURE_SET
    # and never from the values this function intended to write.
    # publish_argument already calls db.refresh() on its own argument after
    # its bulk update, but the other rows above were changed via
    # synchronize_session=False updates on this same session too, so expire
    # the whole identity map before this final read rather than trusting any
    # object loaded earlier in this call (Phase 31 refresh-after-bulk-update
    # precedent).
    db.expire_all()

    fixtures: list[dict] = []
    for entry, argument_id, _admin_job_id in fixture_rows:
        argument = (
            await db.execute(select(Argument).where(Argument.id == argument_id))
        ).scalar_one()
        admin_job = (
            await db.execute(
                select(AdminJob).where(AdminJob.argument_id == argument_id)
            )
        ).scalar_one_or_none()
        fixtures.append(
            {
                "conversation_id": entry["conversation_id"],
                "case_name": entry["case_name"],
                "role": entry["role"],
                "argument_id": argument.id,
                "argument_status": argument.status.value,
                "admin_job_status": admin_job.status.value if admin_job else "",
            }
        )

    return {"fixtures": fixtures}


# Default target for seed_unresolved_speaker_fixture: the Complexity fixture
# (conversation 15169), the same "freshly imported" reference argument
# reset_to_fixture leaves at CANDIDATE with no state-realization applied.
DEFAULT_UNRESOLVED_SPEAKER_CONVERSATION_ID = "15169"


async def seed_unresolved_speaker_fixture(
    db: AsyncSession,
    conversation_id: str = DEFAULT_UNRESOLVED_SPEAKER_CONVERSATION_ID,
) -> dict:
    """
    Dev-only mechanism (D-33a) that nulls the person_id of one advocate-side
    ArgumentParticipant on a fixture argument (the Complexity fixture,
    conversation 15169, by default) and sets its review_state to
    needs_review, so the unresolved-speaker case -- the main thing the
    review queue exists for -- can be produced on demand in a browser.

    This exists because no live corpus path can produce a NULL-person_id
    participant today: `_resolve_person` in
    pipeline/commands/import_convokit.py always resolves-or-creates a
    Person for every speaker label it sees (verified 2026-08-21). That has
    made 26-UAT Test 26 (the unresolved-advocate placeholder and per-row
    Save gate) and 14-UAT Test 8 (an argument containing an unresolved
    speaker) unreachable in a browser since they were written in June
    2026 -- this seeder closes that gap.

    It does not fabricate a synthetic participant from nothing: it takes
    an existing fixture argument's own advocate participant and nulls its
    person_id, producing the same row shape a future PDF-pipeline MISS
    would, so the fixture stays representative rather than invented.

    Dev-only for the same reason reset_to_fixture is (D-07): the router
    this is mounted on (api/routers/admin_dev.py) is only ever registered
    on the FastAPI app when settings.environment == "development" -- see
    api/main.py's guarded include_router call. There is no handler-level
    check in this function or its route; the gate is the router never
    existing outside development.

    Idempotent: if a NULL-person_id participant already exists on the
    target argument, returns its id unchanged (already_seeded=True)
    rather than nulling a second row -- no write, no recompute, no commit
    on that path.

    Raises FixtureNotSeededError if the target argument does not exist, or
    if it exists but has no eligible (non-BENCH) participant to null --
    either case means the database was never reset to the fixture set,
    and this function never returns success with nothing done (mirrors
    ResetIncompleteError's own reasoning).

    Returns a dict shaped for
    api.schemas.admin_dev.SeedUnresolvedSpeakerResponse.
    """
    argument = (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalar_one_or_none()
    if argument is None:
        raise FixtureNotSeededError(
            f"Conversation {conversation_id!r} has no Argument row -- "
            "reset to fixture before seeding an unresolved speaker."
        )

    already_seeded = (
        (
            await db.execute(
                select(ArgumentParticipant)
                .where(
                    ArgumentParticipant.argument_id == argument.id,
                    ArgumentParticipant.person_id.is_(None),
                )
                .order_by(ArgumentParticipant.id.asc())
            )
        )
        .scalars()
        .first()
    )
    if already_seeded is not None:
        return {
            "argument_id": argument.id,
            "participant_id": already_seeded.id,
            "raw_speaker_label": already_seeded.raw_speaker_label,
            "trust_tier": argument.trust_tier.value,
            "already_seeded": True,
        }

    # Deterministic — the same row every time — never a random/first-scan
    # pick. "Non-BENCH" per D-33a's action text: BENCH participants are
    # justices, not the advocate-side speaker this fixture is meant to
    # represent.
    target = (
        (
            await db.execute(
                select(ArgumentParticipant)
                .where(
                    ArgumentParticipant.argument_id == argument.id,
                    ArgumentParticipant.side != SideEnum.BENCH,
                )
                .order_by(ArgumentParticipant.id.asc())
            )
        )
        .scalars()
        .first()
    )
    if target is None:
        raise FixtureNotSeededError(
            f"Conversation {conversation_id!r}'s Argument row has no "
            "non-BENCH participant to seed -- reset to fixture before "
            "seeding an unresolved speaker."
        )

    # Captured as plain ints BEFORE the commit/expire below — accessing an
    # ORM attribute on an expired instance triggers a synchronous lazy
    # reload that MissingGreenlet's under AsyncSession, so `target`/
    # `argument` themselves must never be touched again after expire_all().
    target_id = target.id
    argument_id = argument.id

    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == target_id,
            ArgumentParticipant.argument_id == argument_id,
        )
        .values(person_id=None, review_state=ReviewState.NEEDS_REVIEW)
        .execution_options(synchronize_session=False)
    )
    await recompute_argument_tier(db, argument_id)
    await db.commit()

    # Never build the response from what this function intended to write
    # -- read both rows back after the commit (reset_to_fixture's own step
    # 6 discipline).
    db.expire_all()
    participant = (
        await db.execute(
            select(ArgumentParticipant).where(ArgumentParticipant.id == target_id)
        )
    ).scalar_one()
    argument = (
        await db.execute(select(Argument).where(Argument.id == argument_id))
    ).scalar_one()

    return {
        "argument_id": argument.id,
        "participant_id": participant.id,
        "raw_speaker_label": participant.raw_speaker_label,
        "trust_tier": argument.trust_tier.value,
        "already_seeded": False,
    }
