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
    3. the state-realization block below (Plan 43-02, reworked Phase 50
       D-14) commits via the real admin_arguments.approve_argument /
       admin_arguments.publish_argument service calls (each on this
       module's own `db` session) plus one directly-seeded step="reconcile"
       ImportRun for the Mid-pipeline fixture (_seed_reconcile_run_fixture).
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
    Argument,
    ArgumentParticipant,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    ReviewState,
    SideEnum,
    Utterance,
)
from api.services import admin_arguments as arguments_service
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
    run_import_convokit returns, or when run_import_convokit itself raises
    for a fixture (e.g. an unresolvable/missing conversation id —
    RESEARCH.md Open Question 2). run_import_convokit catches and counts
    per-conversation exceptions internally rather than always raising, so
    success is never inferred from the mere absence of an exception — this
    module always verifies the Argument row exists for every fixture before
    ever returning a success response. A short `fixtures` list is never a
    valid 200.

    Phase 50 (D-14/D-19): no longer also raised for a missing AdminJob row
    — the corpus importer no longer creates one at all."""


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


async def _seed_reconcile_run_fixture(
    db: AsyncSession, argument_id: int, *, conversation_id: str
) -> None:
    """
    Phase 50 (D-04/OQ-2): seed ONE `step="reconcile"` ImportRun for the
    Mid-pipeline dev fixture, replacing the pre-Phase-50 `AdminJob.status =
    RUNNING` flip (there is no AdminJob to flip anymore, D-14/D-19).

    D-06 mints reconcile runs lazily in real reconcile passes; a dev-only
    fixture forcing one into existence is acceptable and intended (OQ-2,
    operator-confirmed 2026-08-25) — it re-realizes the "Mid-pipeline"
    reference state without inventing a parallel mechanism.

    `content_digest` stays NULL — a `step="reconcile"` run carries no
    comparison digest (OQ-3; only `step="parse"` runs do).

    Structurally INVISIBLE to `api/services/arguments.py`'s
    `MAX(ImportRun.id) WHERE step='parse' AND status=completed` read path
    (the blank-page hazard, `api/services/arguments.py:100-108`) — a
    `step="reconcile"` row can never make this argument's public chat page
    render empty, because that read path only ever considers `step="parse"`
    rows, and this fixture's own `step="parse"` run (from the initial
    import) is untouched and still the one that path serves.

    No commit here — the caller (`reset_to_fixture`) commits once after all
    four fixtures' state realization, matching its existing per-fixture
    write pattern.
    """
    db.add(
        ImportRun(
            argument_id=argument_id,
            step="reconcile",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
            external_id=conversation_id,
            content_digest=None,
        )
    )


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

    # 3-4. Reseed each fixture through the real importer, then verify its
    # Argument row landed. Collect (entry, argument_id) pairs in
    # FIXTURE_SET declaration order for the state-realization step below.
    # Phase 50 (D-14/D-19): no paired AdminJob check anymore — the corpus
    # importer no longer creates one at all.
    fixture_rows: list[tuple[dict, int]] = []
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

        fixture_rows.append((entry, argument.id))

    # 5. State realization (D-03, D-04) — runs strictly AFTER every fixture
    # has landed and passed its existence check above, so every Argument
    # row referenced below is guaranteed to exist before any transition is
    # attempted. Looked up by id collected during the reseed loop, never
    # assumed.
    ids_by_conversation = {
        entry["conversation_id"]: argument_id for entry, argument_id in fixture_rows
    }

    # Fixture 15169 (Complexity): no action. It stays exactly as the
    # importer left it — status=CANDIDATE, no AdminJob, latest ImportRun at
    # step="parse". This is deliberate: it is the reference "freshly
    # imported" state.

    # Fixture 13015 (Draft target): CANDIDATE -> DRAFT via the real
    # argument-scoped service function (D-03, D-14). approve_argument
    # stamps resolved_at and writes the ArgumentStatusLog row — this module
    # performs none of those writes itself.
    draft_argument_id = ids_by_conversation["13015"]
    await arguments_service.approve_argument(db, draft_argument_id)

    # Fixture 18897 (Published target): TWO calls, in this order, and the
    # order is NOT optional. approve_argument must run first to reach DRAFT
    # and stamp resolved_at — publish_argument raises ValueError("Cannot
    # publish: resolve step not yet complete") when resolved_at is still
    # null, which is exactly the state a freshly-imported CANDIDATE argument
    # is in. Do not "simplify" these two calls into one.
    published_argument_id = ids_by_conversation["18897"]
    await arguments_service.approve_argument(db, published_argument_id)
    await arguments_service.publish_argument(db, published_argument_id)

    # Fixture 22372 (Mid-pipeline target, D-04, OQ-2): seeds a
    # step="reconcile" ImportRun rather than flipping an AdminJob's status
    # (there is no AdminJob to flip, D-14/D-19). Argument.status stays
    # CANDIDATE, Argument.resolved_at stays null, unchanged — mirrors the
    # pre-Phase-50 fixture's "still mid-pipeline" semantics exactly.
    mid_argument_id = ids_by_conversation["22372"]
    await _seed_reconcile_run_fixture(db, mid_argument_id, conversation_id="22372")
    await db.commit()

    # 6. Build the response strictly from values re-read from the database
    # after every transition above has committed — never from FIXTURE_SET
    # and never from the values this function intended to write.
    # publish_argument/approve_argument already call db.refresh() on their
    # own argument after their bulk updates, but expire the whole identity
    # map before this final read rather than trusting any object loaded
    # earlier in this call (Phase 31 refresh-after-bulk-update precedent).
    db.expire_all()

    fixtures: list[dict] = []
    for entry, argument_id in fixture_rows:
        argument = (
            await db.execute(select(Argument).where(Argument.id == argument_id))
        ).scalar_one()
        # PD-05: the highest-id ImportRun for this argument reports its
        # step, which together with argument_status keeps all four
        # reference states distinguishable: Complexity = candidate/parse,
        # Draft = draft/parse, Published = published/parse, Mid-pipeline =
        # candidate/reconcile.
        latest_run_step = (
            await db.execute(
                select(ImportRun.step)
                .where(ImportRun.argument_id == argument_id)
                .order_by(ImportRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        fixtures.append(
            {
                "conversation_id": entry["conversation_id"],
                "case_name": entry["case_name"],
                "role": entry["role"],
                "argument_id": argument.id,
                "argument_status": argument.status.value,
                "latest_import_run_step": latest_run_step or "",
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

    This exists to make the unresolved-speaker state reachable
    *deterministically and on demand*. A live corpus path CAN produce a
    NULL-person_id participant -- a pipeline job parked at the resolve
    step has created participant rows but has not run `_resolve_person`
    yet, so pre-resolve NULLs are a normal, reachable state (verified
    2026-08-23 against argument 1788 / job 1147, which carried 11 such
    rows). What that path cannot give is repeatability: it depends on
    hand-parking a real job and on whatever the corpus happens to hold.
    26-UAT Test 26 (the unresolved-advocate placeholder and per-row Save
    gate) and 14-UAT Test 8 (an argument containing an unresolved
    speaker) need a fixture that reproduces the state the same way every
    run -- that is the gap this seeder closes.

    NOTE: 49-RESEARCH.md Pitfall 4 claims no live corpus path can produce
    an unresolved speaker. That claim is false; do not propagate it.

    It does not fabricate a synthetic participant from nothing: it takes
    an existing fixture argument's own advocate participant -- preferring
    one whose `side` is already SideEnum.UNKNOWN, so the Speakers card's
    "Unresolved -- choose a role" placeholder (26-UAT Test 26) is also
    reachable, not just the review queue -- and nulls its person_id, and
    the person_id of every Utterance row carrying that same
    raw_speaker_label on this argument (14-UAT Test 8's "non-resolved
    utterance" state; the participant and its utterances are independent
    columns, exactly as api/services/admin_jobs.py's own resolve flow
    writes them separately). This produces the same row shape a future
    PDF-pipeline MISS would, so the fixture stays representative rather
    than invented.

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
    #
    # Prefer a participant whose side is ALREADY SideEnum.UNKNOWN (the
    # Complexity fixture's real corpus data has several — a residual
    # state from before the Resolve-table rework, per 26-UAT Test 26's
    # own waiver note) over an arbitrary resolved-side one. Verified
    # against the source of both consumers this seeder must satisfy:
    # api.services.admin_arguments.list_argument_speakers returns
    # `side: participant.side.value` unchanged regardless of person_id,
    # and the Speakers card's "Unresolved — choose a role" placeholder /
    # Save gate (26-UAT Test 26) key on that value collapsing to the
    # literal string "UNKNOWN" — nulling person_id alone on an
    # already-resolved PETITIONER/RESPONDENT/AMICUS row would leave that
    # placeholder unreachable, silently failing this task's own must-have
    # truth. Falls back to the plan's original "first non-BENCH ordered
    # by id" pick when no UNKNOWN-side participant exists, so this still
    # terminates deterministically on a fixture that lacks one.
    target = (
        (
            await db.execute(
                select(ArgumentParticipant)
                .where(
                    ArgumentParticipant.argument_id == argument.id,
                    ArgumentParticipant.side == SideEnum.UNKNOWN,
                )
                .order_by(ArgumentParticipant.id.asc())
            )
        )
        .scalars()
        .first()
    )
    if target is None:
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

    # Captured as plain values BEFORE the commit/expire below — accessing
    # an ORM attribute on an expired instance triggers a synchronous lazy
    # reload that MissingGreenlet's under AsyncSession, so `target`/
    # `argument` themselves must never be touched again after expire_all().
    target_id = target.id
    target_raw_speaker_label = target.raw_speaker_label
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
    # Also null the matching Utterance rows (D-33a correction): the
    # participant and its utterances are independent columns —
    # api/services/admin_jobs.py's own real resolve flow writes both
    # separately, scoped by (argument_id, raw_speaker_label) for the
    # utterance leg. Nulling ONLY the participant would leave every
    # utterance this speaker gave still reading a resolved person_id, so
    # the public ChatBubble avatar would still render as a clickable,
    # resolved speaker (api/services/arguments.py joins on
    # Utterance.person_id directly, never through ArgumentParticipant) —
    # silently failing to reproduce 14-UAT Test 8's "non-resolved
    # utterance" state, which is this seeder's other named purpose.
    await db.execute(
        update(Utterance)
        .where(
            Utterance.argument_id == argument_id,
            Utterance.raw_speaker_label == target_raw_speaker_label,
        )
        .values(person_id=None)
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
