"""
Published-lock enforcement on the whole-argument write path (Phase 49, D-35a).

Every argument-data writer must refuse a PUBLISHED argument:
`update_argument`, `update_argument_metadata`, `resolve_job`, and
`create_person_for_job`. The deliberate NON-locks are proved live too —
`unpublish_argument` and review-state writes still succeed on a published
argument. These are LIVE database assertions; the claim is NON-PERSISTENCE.

Also covers, at the Python layer: that the guards add no second argument
SELECT, that the router endpoints document the published case, and that
every argument-data writer carries the shared published predicate.

Trimmed 2026-08-27 (debridement pass): 7 static `.svelte`/`.ts`-source
assertions removed. See CLAUDE.md -> Testing Policy.
"""

import ast
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]

ADMIN_ARGUMENTS_SERVICE_PATH = ROOT / "api" / "services" / "admin_arguments.py"
ADMIN_JOBS_SERVICE_PATH = ROOT / "api" / "services" / "admin_jobs.py"
ADMIN_ROUTER_PATH = ROOT / "api" / "routers" / "admin.py"
# The shared error-prose fragment every argument-data writer's published
# guard carries, old and new alike (see
# test_every_argument_data_writer_carries_the_published_predicate below).
SHARED_PUBLISHED_CLAUSE = "is published (current status:"


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _service_function_source_lines(module_path: Path, function_name: str) -> list[str]:
    """
    Read a Python service module and return non-comment, non-blank lines from
    the named async function's body. Local copy of the helper established in
    test_phase49_participant_side_contract.py and test_published_gate.py —
    deliberately not imported across test modules.
    """
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            start = node.lineno
            end = node.end_lineno
            lines = source.splitlines()[start - 1 : end]
            non_comment = [
                line for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            return non_comment
    return []


def _router_function_docstring(module_path: Path, function_name: str) -> str:
    """Return the docstring of the named (async) function in module_path, by
    AST, so multiple functions across files sharing a name (e.g. the router's
    `update_argument` vs. the service's `update_argument`) cannot collide."""
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == function_name:
            doc = ast.get_docstring(node)
            if doc is not None:
                return doc
    return ""


def _argument_select_count(lines: list[str]) -> int:
    """Count occurrences of an Argument SELECT inside a function body's
    non-comment lines. Scoped to `select(Argument)` (the exact call shape
    both target functions use for their own load), not a bare mention of the
    `Argument` symbol, which would also match imports and type hints."""
    text = "\n".join(lines)
    return len(re.findall(r"select\(Argument\)", text))


# ─────────────────────────────────────────────────────────────────────────
# Task 1: the published lock on update_argument and update_argument_metadata
# (D-35a's whole-argument scope, half one — the argument's own data).
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_refuses_a_published_argument() -> None:
    """
    D-35a: "whole argument — lock everything." Before this plan,
    `update_argument` froze only the SLUG on a published argument;
    `argued_date`, `case_name`, and `docket_number` all remained writable
    on live public data.

    This asserts NON-PERSISTENCE, not merely that an exception was raised:
    all five affected columns (argument.argued_date, case.case_name,
    case.docket_number, case.docket_number_norm, case.slug) are re-read
    from a FRESH session after the raise and asserted byte-identical to
    their seeded values.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
    from api.schemas.admin_arguments import ArgumentUpdate
    from api.services.admin_arguments import update_argument

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            argued_date=__import__("datetime").date(2020, 1, 15),
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="20-PUBLOCK-1",
            docket_number_norm="20-publock-1",
            case_name="Original Published Case Name",
            term_year=2020,
            slug="original-published-case-name-lock",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        original_argued_date = arg.argued_date
        original_case_name = case.case_name
        original_docket_number = case.docket_number
        original_docket_number_norm = case.docket_number_norm
        original_slug = case.slug

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await update_argument(
                    db,
                    arg_id,
                    ArgumentUpdate(
                        case_name="Renamed While Published",
                        docket_number="20-SHOULD-NOT-PERSIST",
                        argued_date="2021-06-01",
                    ),
                )

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            case = await db.get(Case, case_id)
            assert arg.argued_date == original_argued_date
            assert case.case_name == original_case_name
            assert case.docket_number == original_docket_number
            assert case.docket_number_norm == original_docket_number_norm
            assert case.slug == original_slug
    finally:
        async with AsyncSessionLocal() as db:
            ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
            if ca is not None:
                await db.delete(ca)
            case = await db.get(Case, case_id)
            if case is not None:
                await db.delete(case)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_argument_metadata_refuses_a_published_argument() -> None:
    """
    D-35a: `update_argument_metadata` had NO status check at any layer
    before this plan — not the service, not the router, not the SvelteKit
    action. This asserts NON-PERSISTENCE across every column it writes:
    argued_date, source_docket, source_dockets, question_number, and the
    lead Case.case_name.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
    from api.schemas.admin_arguments import MetadataUpdate
    from api.services.admin_arguments import update_argument_metadata

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            argued_date=__import__("datetime").date(2020, 1, 15),
            source_docket="20-META-1",
            source_dockets=["20-META-1"],
            question_number=1,
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="20-META-1",
            docket_number_norm="20-meta-1",
            case_name="Original Metadata Case Name",
            term_year=2020,
            slug="original-metadata-case-name-lock",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        original_argued_date = arg.argued_date
        original_source_docket = arg.source_docket
        original_source_dockets = list(arg.source_dockets)
        original_question_number = arg.question_number
        original_case_name = case.case_name

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await update_argument_metadata(
                    db,
                    arg_id,
                    MetadataUpdate(
                        argued_date="2021-06-01",
                        source_dockets=["20-SHOULD-NOT-PERSIST"],
                        question_number="2",
                        case_name="Renamed Metadata Case",
                    ),
                )

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            case = await db.get(Case, case_id)
            assert arg.argued_date == original_argued_date
            assert arg.source_docket == original_source_docket
            assert arg.source_dockets == original_source_dockets
            assert arg.question_number == original_question_number
            assert case.case_name == original_case_name
    finally:
        async with AsyncSessionLocal() as db:
            ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
            if ca is not None:
                await db.delete(ca)
            case = await db.get(Case, case_id)
            if case is not None:
                await db.delete(case)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_argument_writers_still_accept_draft_and_unpublished() -> None:
    """
    The folded todo `2026-08-21-widen-participant-editability-to-all-
    unpublished-states` exists because a sibling writer's guard was once
    CANDIDATE-only and had to be widened after the fact. The predicate here
    must key on PUBLISHED alone — a narrower predicate would re-introduce
    that exact bug on two more paths. Both writers, both non-published
    states, all four writes must succeed and persist.
    """
    import datetime

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum, Case, CaseArgument
    from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate
    from api.services.admin_arguments import update_argument, update_argument_metadata

    for status in (ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.UNPUBLISHED):
        for writer_name in ("update_argument", "update_argument_metadata"):
            async with AsyncSessionLocal() as db:
                arg = Argument(status=status, argued_date=datetime.date(2019, 1, 1))
                db.add(arg)
                await db.flush()

                case = Case(
                    docket_number=f"20-STILL-{status.value}-{writer_name[:4]}",
                    docket_number_norm=f"20-still-{status.value}-{writer_name[:4]}".lower(),
                    case_name="Still Editable Case",
                    term_year=2020,
                    slug=f"still-editable-{status.value}-{writer_name[:4]}",
                )
                db.add(case)
                await db.flush()

                db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
                await db.commit()

                arg_id = arg.id
                case_id = case.id

            try:
                async with AsyncSessionLocal() as db:
                    if writer_name == "update_argument":
                        result = await update_argument(
                            db, arg_id, ArgumentUpdate(case_name="Renamed While Editable")
                        )
                        assert result is not None
                        assert result["case_name"] == "Renamed While Editable"
                    else:
                        ok = await update_argument_metadata(
                            db, arg_id, MetadataUpdate(question_number="9")
                        )
                        assert ok is True

                async with AsyncSessionLocal() as db:
                    arg = await db.get(Argument, arg_id)
                    case = await db.get(Case, case_id)
                    if writer_name == "update_argument":
                        assert case.case_name == "Renamed While Editable"
                    else:
                        assert arg.question_number == 9
            finally:
                async with AsyncSessionLocal() as db:
                    ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
                    if ca is not None:
                        await db.delete(ca)
                    case = await db.get(Case, case_id)
                    if case is not None:
                        await db.delete(case)
                    arg = await db.get(Argument, arg_id)
                    if arg is not None:
                        await db.delete(arg)
                    await db.commit()


def test_published_guards_add_no_second_argument_select() -> None:
    """
    Source. `test_admin_arguments_service.py` drives `update_argument_metadata`
    three times with an AsyncMock whose `db.execute.side_effect` is a fixed
    ordered list, and `test_metadata_update_null_final_pair_does_not_collide`
    asserts `db.execute.await_count == 1`. An extra Argument SELECT inside
    either guarded function would break all three of those tests. Both
    guards must reuse the row the function already loads, never adding a
    query. This assertion is the executable form of that constraint — its
    value is prospective: it fails only if a future edit adds a query.
    """
    update_argument_lines = _service_function_source_lines(ADMIN_ARGUMENTS_SERVICE_PATH, "update_argument")
    update_metadata_lines = _service_function_source_lines(ADMIN_ARGUMENTS_SERVICE_PATH, "update_argument_metadata")

    assert update_argument_lines, "could not extract update_argument() body"
    assert update_metadata_lines, "could not extract update_argument_metadata() body"

    assert _argument_select_count(update_argument_lines) == 1, (
        "update_argument() must load the Argument row exactly once — the "
        "published guard must compare the already-loaded row's status, "
        "never issue a second select(Argument). Actual body:\n"
        + "\n".join(update_argument_lines)
    )
    assert _argument_select_count(update_metadata_lines) == 1, (
        "update_argument_metadata() must load the Argument row exactly "
        "once — a second select(Argument) would break the three "
        "AsyncMock-driven tests in test_admin_arguments_service.py whose "
        "fixed db.execute.side_effect ordering and db.execute.await_count "
        "== 1 assertion depend on the current call count. Actual body:\n"
        + "\n".join(update_metadata_lines)
    )


def test_router_endpoints_document_the_published_case() -> None:
    """
    STRUCTURAL-ONLY (docs, not runtime behavior): both PATCH endpoint
    docstrings must document the new 422 case this plan adds, phrased in
    the operator's own terms (the argument is published; unpublish to
    edit it).
    """
    argument_doc = _router_function_docstring(ADMIN_ROUTER_PATH, "update_argument")
    metadata_doc = _router_function_docstring(ADMIN_ROUTER_PATH, "update_argument_metadata")

    assert "published" in argument_doc.lower(), (
        f"PATCH /arguments/{{argument_id}}'s docstring must document the "
        f"new published-argument 422 case. Actual docstring:\n{argument_doc}"
    )
    assert "unpublish" in argument_doc.lower(), (
        f"PATCH /arguments/{{argument_id}}'s docstring must name unpublishing "
        f"as the remedy. Actual docstring:\n{argument_doc}"
    )
    assert "published" in metadata_doc.lower(), (
        f"PATCH /arguments/{{argument_id}}/metadata's docstring must document "
        f"the new published-argument 422 case. Actual docstring:\n{metadata_doc}"
    )
    assert "unpublish" in metadata_doc.lower(), (
        f"PATCH /arguments/{{argument_id}}/metadata's docstring must name "
        f"unpublishing as the remedy. Actual docstring:\n{metadata_doc}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Task 2: the two job-scoped participant writers D-35's first half never
# reached; the deliberate non-locks (lifecycle, review-state); and the
# full six-writer parity assertion.
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_resolve_job_refuses_a_published_argument() -> None:
    """
    This seeded state — a PAUSED job pointing at a PUBLISHED argument — is
    NOT reachable through any current path: a PAUSED job never points at a
    publishable argument today (see `<planner_decisions>` in
    49-11-PLAN.md for the full reachability trace). The guard is therefore
    defence in depth against a future change to how jobs bind to
    arguments, which would otherwise remove the transitive control (the
    job's own PAUSED requirement) that blocks the published case today,
    silently and with no failing test.

    Asserts NON-PERSISTENCE: the targeted participant's person_id, the
    targeted utterance's person_id, and the argument's resolved_at are
    all unchanged after the raise, and no SpeakerAlias row was written for
    the label.
    """
    import datetime

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportSource,
        Person,
        SideEnum,
        SpeakerAlias,
        Utterance,
    )
    from api.schemas.admin_jobs import ResolveMatch
    from api.services.admin_jobs import resolve_job
    from pipeline.commands.resolve import normalize_label
    from sqlalchemy import select as sa_select

    raw_label = "MR. PUBLISHED LOCK RESOLVE"
    original_resolved_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED, resolved_at=original_resolved_at)
        db.add(arg)
        await db.flush()

        run = ImportRun(
            argument_id=arg.id,
            step="parse",
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
        )
        db.add(run)
        await db.flush()

        utt = Utterance(
            argument_id=arg.id,
            import_run_id=run.id,
            sequence=1,
            raw_speaker_label=raw_label,
            text="Test utterance.",
            side=SideEnum.PETITIONER,
            person_id=None,
        )
        db.add(utt)

        participant = ArgumentParticipant(
            argument_id=arg.id,
            raw_speaker_label=raw_label,
            side=SideEnum.PETITIONER,
            person_id=None,
        )
        db.add(participant)
        await db.flush()

        person = Person(full_name="Published Lock Resolve Target")
        db.add(person)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        arg_id = arg.id
        job_id = job.id
        run_id = run.id
        utterance_id = utt.id
        participant_id = participant.id
        person_id = person.id

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await resolve_job(
                    db, job_id, [ResolveMatch(raw_speaker_label=raw_label, person_id=person_id)]
                )

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, participant_id)
            utt = await db.get(Utterance, utterance_id)
            arg = await db.get(Argument, arg_id)
            assert participant.person_id is None
            assert utt.person_id is None
            assert arg.resolved_at == original_resolved_at

            alias_result = await db.execute(
                sa_select(SpeakerAlias).where(SpeakerAlias.normalized_label == normalize_label(raw_label))
            )
            assert alias_result.scalar_one_or_none() is None, (
                "a refused resolve on a PUBLISHED argument must leave no new "
                "SpeakerAlias row behind"
            )
    finally:
        async with AsyncSessionLocal() as db:
            alias_result = await db.execute(
                sa_select(SpeakerAlias).where(SpeakerAlias.normalized_label == normalize_label(raw_label))
            )
            alias = alias_result.scalar_one_or_none()
            if alias is not None:
                await db.delete(alias)
                await db.commit()

        async with AsyncSessionLocal() as db:
            utt = await db.get(Utterance, utterance_id)
            if utt is not None:
                await db.delete(utt)
            participant = await db.get(ArgumentParticipant, participant_id)
            if participant is not None:
                await db.delete(participant)
            job = await db.get(AdminJob, job_id)
            if job is not None:
                await db.delete(job)
            run = await db.get(ImportRun, run_id)
            if run is not None:
                await db.delete(run)
            person = await db.get(Person, person_id)
            if person is not None:
                await db.delete(person)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_refuses_a_published_argument() -> None:
    """
    Same seeded shape and same non-reachability caveat as the resolve_job
    test above. This function's own contract is validate-before-mutate
    (WR-02: PAUSED and participant validation both run before any Person
    row exists); the published guard extends that same contract rather
    than bolting a check onto the end.

    Asserts no Person row with the submitted name exists afterwards, and
    that the targeted participant's person_id and side are unchanged.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job
    from sqlalchemy import select as sa_select

    raw_label = "MR. PUBLISHED LOCK CREATE PERSON"

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            raw_speaker_label=raw_label,
            side=SideEnum.UNKNOWN,
            person_id=None,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        arg_id = arg.id
        job_id = job.id
        participant_id = participant.id

    body = PersonCreate(
        first_name="Should",
        last_name="NotPersist",
        raw_speaker_label=raw_label,
        side=SideEnum.PETITIONER,
    )

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError):
                await create_person_for_job(db, job_id, body)

        async with AsyncSessionLocal() as db:
            person_result = await db.execute(
                sa_select(Person).where(Person.full_name == "Should NotPersist")
            )
            assert person_result.scalar_one_or_none() is None, (
                "a refused create-person on a PUBLISHED argument must create no Person row"
            )
            participant = await db.get(ArgumentParticipant, participant_id)
            assert participant.person_id is None
            assert participant.side == SideEnum.UNKNOWN
    finally:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, participant_id)
            if participant is not None:
                await db.delete(participant)
            job = await db.get(AdminJob, job_id)
            if job is not None:
                await db.delete(job)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unpublish_still_works_on_a_published_argument() -> None:
    """
    D-35 says an argument in any state OTHER than published is editable —
    which presupposes it can always LEAVE the published state. This is the
    counterweight to every other assertion in this module: it stops a
    future over-broad lock from making an argument permanently frozen and
    unpublishable-from, which would defeat D-35a rather than implement it.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        ArgumentStatusLog,
        Case,
        CaseArgument,
    )
    from api.services.admin_arguments import unpublish_argument
    from sqlalchemy import select as sa_select

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="20-UNPUB-1",
            docket_number_norm="20-unpub-1",
            case_name="Still Unpublishable Case",
            term_year=2020,
            slug="still-unpublishable-case",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
        await db.commit()

        arg_id = arg.id
        case_id = case.id

    try:
        async with AsyncSessionLocal() as db:
            result = await unpublish_argument(db, arg_id)
        assert result is not None
        assert result["status"] == ArgumentStatusEnum.UNPUBLISHED

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, arg_id)
            assert arg.status == ArgumentStatusEnum.UNPUBLISHED
    finally:
        async with AsyncSessionLocal() as db:
            log_result = await db.execute(
                sa_select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
            )
            for log in log_result.scalars().all():
                await db.delete(log)
            ca = await db.get(CaseArgument, {"case_id": case_id, "argument_id": arg_id})
            if ca is not None:
                await db.delete(ca)
            case = await db.get(Case, case_id)
            if case is not None:
                await db.delete(case)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_review_state_writes_still_work_on_a_published_argument() -> None:
    """
    Carries forward 49-09's classification verbatim: `resolve_participant_
    review` writes `review_state` only, never a value column. Under D-35a
    review metadata is not "the argument's published data" — nothing a
    member of the public sees changes — and locking it would break
    auditing for exactly the published rows most likely to need it. This
    is an intentional non-hole, now proved live rather than merely
    asserted in prose.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        ReviewState,
        SideEnum,
    )
    from api.services.admin_review import resolve_participant_review

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PUBLISHED)
        db.add(arg)
        await db.flush()

        advocate = Person(full_name="Review State Still Works Advocate")
        db.add(advocate)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate.id,
            raw_speaker_label="MR. REVIEW STATE STILL WORKS",
            side=SideEnum.PETITIONER,
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(participant)
        await db.commit()

        arg_id = arg.id
        advocate_id = advocate.id
        participant_id = participant.id

    try:
        async with AsyncSessionLocal() as db:
            result = await resolve_participant_review(db, participant_id, "confirm")
        assert result is not None

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, participant_id)
            assert participant.review_state == ReviewState.OPERATOR_CONFIRMED
    finally:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, participant_id)
            if participant is not None:
                await db.delete(participant)
            person = await db.get(Person, advocate_id)
            if person is not None:
                await db.delete(person)
            arg = await db.get(Argument, arg_id)
            if arg is not None:
                await db.delete(arg)
            await db.commit()


def test_every_argument_data_writer_carries_the_published_predicate() -> None:
    """
    D-35a's whole point is that all six argument-data writers behave
    identically on the published question. Six inline guards were chosen
    over one extracted helper (see 49-11-PLAN.md `<planner_decisions>`);
    this assertion is the mechanism that makes that choice safe. Scoped
    STRICTLY to these six named function bodies, not to files — a
    file-level grep would also match `publish_argument` and
    `unpublish_argument`, which reference the same enum member for
    entirely unrelated reasons (the already-published check, the status
    write), which would make a file-scoped assertion trivially true.
    """
    functions = [
        (ADMIN_ARGUMENTS_SERVICE_PATH, "update_argument"),
        (ADMIN_ARGUMENTS_SERVICE_PATH, "update_argument_metadata"),
        (ADMIN_ARGUMENTS_SERVICE_PATH, "update_participant_side"),
        (ADMIN_JOBS_SERVICE_PATH, "update_resolve_row_for_job"),
        (ADMIN_JOBS_SERVICE_PATH, "resolve_job"),
        (ADMIN_JOBS_SERVICE_PATH, "create_person_for_job"),
    ]
    for path, name in functions:
        lines = _service_function_source_lines(path, name)
        assert lines, f"could not extract {name}() body from {path}"
        text = "\n".join(lines)
        assert "ArgumentStatusEnum.PUBLISHED" in text, (
            f"{name}() must compare status to ArgumentStatusEnum.PUBLISHED. "
            f"Actual body:\n{text}"
        )
        assert SHARED_PUBLISHED_CLAUSE in text, (
            f"{name}()'s published-guard error must share the same prose "
            f"clause every other guard uses ('is published (current "
            f"status: ...)'). Actual body:\n{text}"
        )


# ─────────────────────────────────────────────────────────────────────────
# Task 3: reverse the always-editable decision, lock the Case and
# Argument Details cards behind 49-09's single flag, one page-level
# statement, and honest rejection copy on both argument-data forms.
#
# Every assertion below is STRUCTURAL-ONLY: it proves a string/pattern is
# present in source, never that a control renders or behaves correctly in
# a browser. See this module's own docstring for the standing false-green
# incident this project has on record (plan 48-10).
# ─────────────────────────────────────────────────────────────────────────

