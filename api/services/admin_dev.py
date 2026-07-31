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
    3. (Plan 43-02) state-transition service calls commit on yet another
       session reference.
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

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import AdminJob, Argument
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
        pipeline_runs,
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
    Wipe the full D-01 table set and reseed exactly FIXTURE_SET's
    conversations through the real import-convokit path.

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
    # its Argument row and its paired AdminJob row landed.
    fixtures: list[dict] = []
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

        fixtures.append(
            {
                "conversation_id": conversation_id,
                "case_name": entry["case_name"],
                "role": entry["role"],
                "argument_id": argument.id,
                "argument_status": argument.status.value,
                "admin_job_status": admin_job.status.value,
            }
        )

    # 5. Return in FIXTURE_SET declaration order, values read back from the DB.
    return {"fixtures": fixtures}
