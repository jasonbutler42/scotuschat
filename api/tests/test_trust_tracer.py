"""
End-to-end tracer: a corpus argument materializes a derived trust_tier
(Phase 48, plan 48-01, Task 1).

Proves ONE path from api.domain.trust.derive_tier through
api.services.trust.recompute_argument_tier to a stored, re-readable
arguments.trust_tier value — with no other call sites. DB-gated against
TEST_DATABASE_URL, using the same _db_configured() skipif + AsyncSessionLocal()
seed/assert/teardown shape api/tests/test_admin_arguments_service.py uses.
"""

import os

import pytest


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.fixture
async def corpus_argument_with_two_resolved_utterances():
    """
    Seed one CANDIDATE argument, one ImportRun (source=CORPUS,
    method=DIRECT, step=parse), one Person, and two resolved Utterance rows
    — exactly the "corpus argument, all speakers resolved" tracer fixture
    every test in this module shares. Tears down every seeded row in FK
    order afterward so the rootdir conftest.py dev-DB row-count tripwire
    stays green.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportSource,
        Person,
        SideEnum,
        Utterance,
    )

    async with AsyncSessionLocal() as db:
        argument = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
        db.add(argument)
        await db.flush()

        import_run = ImportRun(
            argument_id=argument.id,
            step="parse",
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
        )
        db.add(import_run)
        await db.flush()

        person = Person(full_name="Trust Tracer Test Person")
        db.add(person)
        await db.flush()

        utterance_1 = Utterance(
            argument_id=argument.id,
            import_run_id=import_run.id,
            sequence=1,
            raw_speaker_label="MR. TEST",
            text="Test utterance one.",
            is_stage_direction=False,
            side=SideEnum.PETITIONER,
            person_id=person.id,
        )
        utterance_2 = Utterance(
            argument_id=argument.id,
            import_run_id=import_run.id,
            sequence=2,
            raw_speaker_label="MR. TEST",
            text="Test utterance two.",
            is_stage_direction=False,
            side=SideEnum.PETITIONER,
            person_id=person.id,
        )
        db.add_all([utterance_1, utterance_2])
        await db.flush()

        ids = {
            "argument_id": argument.id,
            "import_run_id": import_run.id,
            "person_id": person.id,
            "utterance_1_id": utterance_1.id,
            "utterance_2_id": utterance_2.id,
        }

        await db.commit()

    yield ids

    async with AsyncSessionLocal() as db:
        for utterance_id in (ids["utterance_1_id"], ids["utterance_2_id"]):
            utterance = await db.get(Utterance, utterance_id)
            if utterance is not None:
                await db.delete(utterance)
        import_run = await db.get(ImportRun, ids["import_run_id"])
        if import_run is not None:
            await db.delete(import_run)
        argument = await db.get(Argument, ids["argument_id"])
        if argument is not None:
            await db.delete(argument)
        person = await db.get(Person, ids["person_id"])
        if person is not None:
            await db.delete(person)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_stores_trusted_for_resolved_corpus_argument(
    corpus_argument_with_two_resolved_utterances,
) -> None:
    """
    A corpus argument (source=CORPUS, method=DIRECT) whose every utterance
    has a non-null person_id recomputes and stores TRUSTED — the shape
    every real corpus-imported argument should read at birth.
    """
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument
    from api.services.trust import recompute_argument_tier

    ids = corpus_argument_with_two_resolved_utterances

    async with AsyncSessionLocal() as db:
        result = await recompute_argument_tier(db, ids["argument_id"])
        assert result is TrustTier.TRUSTED
        # recompute_argument_tier must not commit itself — the caller's
        # commit persists the value (48-RESEARCH.md Pitfall 2).
        await db.commit()

    async with AsyncSessionLocal() as db:
        argument = await db.get(Argument, ids["argument_id"])
        assert argument.trust_tier is TrustTier.TRUSTED


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_stores_uncertain_when_one_speaker_unresolved(
    corpus_argument_with_two_resolved_utterances,
) -> None:
    """
    The same argument with one non-stage-direction utterance's person_id
    NULLed recomputes and stores UNCERTAIN (D-11) — an unresolved speaker
    floors the whole argument regardless of how trusted the rest is.
    """
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, Utterance
    from api.services.trust import recompute_argument_tier

    ids = corpus_argument_with_two_resolved_utterances

    async with AsyncSessionLocal() as db:
        utterance = await db.get(Utterance, ids["utterance_1_id"])
        utterance.person_id = None
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await recompute_argument_tier(db, ids["argument_id"])
        assert result is TrustTier.UNCERTAIN
        await db.commit()

    async with AsyncSessionLocal() as db:
        argument = await db.get(Argument, ids["argument_id"])
        assert argument.trust_tier is TrustTier.UNCERTAIN


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_stores_uncertain_for_zero_utterance_argument(
    corpus_argument_with_two_resolved_utterances,
) -> None:
    """
    An argument with zero utterances and zero participants recomputes and
    stores UNCERTAIN (Zero-Utterance Tier Decision) — floor_tier's explicit
    empty-sequence base case, never a min()-over-empty-iterable crash.
    """
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, Utterance
    from api.services.trust import recompute_argument_tier

    ids = corpus_argument_with_two_resolved_utterances

    async with AsyncSessionLocal() as db:
        utterance_1 = await db.get(Utterance, ids["utterance_1_id"])
        utterance_2 = await db.get(Utterance, ids["utterance_2_id"])
        await db.delete(utterance_1)
        await db.delete(utterance_2)
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await recompute_argument_tier(db, ids["argument_id"])
        assert result is TrustTier.UNCERTAIN
        await db.commit()

    async with AsyncSessionLocal() as db:
        argument = await db.get(Argument, ids["argument_id"])
        assert argument.trust_tier is TrustTier.UNCERTAIN
