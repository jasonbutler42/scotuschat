"""
DB-gated recompute coverage across every tier combination (Phase 48, plan
48-01, Task 3 — a 48-VALIDATION.md Wave 0 requirement, D-21 owner of tier
coverage).

Exhaustive, not representative: every (source, method) pair a writer path
can actually produce, both the D-11 (unresolved speaker/participant) and
D-12 (stage-direction carve-out, side=UNKNOWN not carved out) rules, the
zero-constituent base case, the non-committing contract (48-RESEARCH.md
Pitfall 2), and every summarize_tier_blockers code are locked here.

DB-gated against TEST_DATABASE_URL using the same _db_configured() skipif
+ AsyncSessionLocal() seed/assert/teardown shape api/tests/test_trust_tracer.py
and api/tests/test_admin_arguments_service.py use. Every test leaves the
database exactly as it found it so the rootdir conftest.py dev-DB
row-count tripwire stays green.
"""

from __future__ import annotations

import os

import pytest


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


async def _seed_argument(source, method, utterance_specs, participant_specs=()):
    """
    Seed one CANDIDATE Argument, one ImportRun with the given (source,
    method), a shared Person for resolved constituents, one Utterance row
    per entry in utterance_specs — each a (resolved, is_stage_direction,
    side) tuple, OR (Phase 53 plan 53-01) a (resolved, is_stage_direction,
    side, speaker_undetermined) 4-tuple — and one ArgumentParticipant row
    per entry in participant_specs — each a `resolved` bool.

    A 3-element utterance spec seeds speaker_undetermined=False (the
    default, matching every pre-Phase-53 caller unchanged). A 4-element
    spec's fourth entry is the stored speaker_undetermined column value:
    True forces raw_speaker_label and person_id to None regardless of
    `resolved` (D-05's CHECK constraint shape — a sentinel row is never
    resolved); the literal None seeds an explicit NULL flag (the
    pre-migration-0033 shape), leaving raw_speaker_label/person_id
    governed by `resolved`/`is_stage_direction` exactly as before.

    Returns a dict of every id needed for the matching teardown helper.
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        ImportRun,
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
            source=source,
            method=method,
        )
        db.add(import_run)
        await db.flush()

        person = None
        if any(resolved for resolved, *_rest in utterance_specs) or any(
            resolved for resolved in participant_specs
        ):
            person = Person(full_name="Trust Recompute Test Person")
            db.add(person)
            await db.flush()

        utterance_ids = []
        for i, spec in enumerate(utterance_specs):
            if len(spec) == 4:
                resolved, is_stage_direction, side, speaker_undetermined = spec
            else:
                resolved, is_stage_direction, side = spec
                speaker_undetermined = False

            if speaker_undetermined is True:
                # D-05 CHECK constraint shape: a source-sentinel row is
                # never resolved and never carries a label, regardless of
                # what `resolved` was passed as.
                raw_speaker_label = None
                row_person_id = None
            else:
                raw_speaker_label = "MR. TEST" if not is_stage_direction else None
                row_person_id = person.id if (resolved and person is not None) else None

            utterance = Utterance(
                argument_id=argument.id,
                import_run_id=import_run.id,
                sequence=i + 1,
                raw_speaker_label=raw_speaker_label,
                text=f"Test utterance {i + 1}.",
                is_stage_direction=is_stage_direction,
                side=SideEnum(side) if isinstance(side, str) else side,
                person_id=row_person_id,
                speaker_undetermined=speaker_undetermined,
            )
            db.add(utterance)
            await db.flush()
            utterance_ids.append(utterance.id)

        participant_ids = []
        for resolved in participant_specs:
            participant = ArgumentParticipant(
                argument_id=argument.id,
                person_id=person.id if (resolved and person is not None) else None,
                raw_speaker_label="MR. TEST PARTICIPANT",
                side=SideEnum.PETITIONER,
            )
            db.add(participant)
            await db.flush()
            participant_ids.append(participant.id)

        ids = {
            "argument_id": argument.id,
            "import_run_id": import_run.id,
            "person_id": person.id if person is not None else None,
            "utterance_ids": utterance_ids,
            "participant_ids": participant_ids,
        }
        await db.commit()

    return ids


async def _seed_second_import_run(argument_id, source, method, resolved, is_stage_direction, side):
    """Add a second ImportRun + resolved utterance to an already-seeded argument (floor test)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportRun, Person, Utterance

    async with AsyncSessionLocal() as db:
        import_run = ImportRun(
            argument_id=argument_id,
            step="parse",
            source=source,
            method=method,
        )
        db.add(import_run)
        await db.flush()

        person = None
        if resolved:
            person = Person(full_name="Trust Recompute Test Person 2")
            db.add(person)
            await db.flush()

        utterance = Utterance(
            argument_id=argument_id,
            import_run_id=import_run.id,
            sequence=99,
            raw_speaker_label="MR. TEST 2" if not is_stage_direction else None,
            text="Test utterance second run.",
            is_stage_direction=is_stage_direction,
            side=side,
            person_id=person.id if (resolved and person is not None) else None,
        )
        db.add(utterance)
        await db.flush()

        ids = {
            "import_run_id": import_run.id,
            "person_id": person.id if person is not None else None,
            "utterance_id": utterance.id,
        }
        await db.commit()

    return ids


async def _teardown_argument(ids, extra_import_run_ids=(), extra_utterance_ids=(), extra_person_ids=()):
    """Delete every seeded row in FK order: Utterance, ArgumentParticipant, ImportRun, Argument, Person."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, ImportRun, Person, Utterance

    async with AsyncSessionLocal() as db:
        for utterance_id in list(ids.get("utterance_ids", [])) + list(extra_utterance_ids):
            utterance = await db.get(Utterance, utterance_id)
            if utterance is not None:
                await db.delete(utterance)
        for participant_id in ids.get("participant_ids", []):
            participant = await db.get(ArgumentParticipant, participant_id)
            if participant is not None:
                await db.delete(participant)
        for import_run_id in [ids["import_run_id"], *extra_import_run_ids]:
            import_run = await db.get(ImportRun, import_run_id)
            if import_run is not None:
                await db.delete(import_run)
        argument = await db.get(Argument, ids["argument_id"])
        if argument is not None:
            await db.delete(argument)
        person_ids = [pid for pid in (ids.get("person_id"), *extra_person_ids) if pid is not None]
        for person_id in person_ids:
            person = await db.get(Person, person_id)
            if person is not None:
                await db.delete(person)
        await db.commit()


# ---------------------------------------------------------------------------
# Single-provenance cases — every (source, method) pair a writer path
# actually produces (48-01-PLAN.md action text).
# ---------------------------------------------------------------------------

SINGLE_PROVENANCE_CASES = [
    ("corpus", "direct", "trusted"),
    ("seed", "direct", "trusted"),
    ("pdf_pipeline", "normalized", "provisional"),
    ("pdf_pipeline", "rule_based", "provisional"),
    ("pdf_pipeline", "llm_corrective", "uncertain"),
]


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
@pytest.mark.parametrize(
    "source, method, expected_tier_value",
    SINGLE_PROVENANCE_CASES,
    ids=[f"{s}-{m}" for s, m, _t in SINGLE_PROVENANCE_CASES],
)
async def test_recompute_single_provenance_pairs(source, method, expected_tier_value):
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource(source),
        ImportMethod(method),
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier(expected_tier_value)
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier(expected_tier_value)
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# Floor test: mixing a trusted utterance and a provisional utterance on one
# argument recomputes to provisional — the floor, not the ceiling/majority.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_floor_across_two_import_runs():
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource, SideEnum
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    second = await _seed_second_import_run(
        ids["argument_id"],
        ImportSource.PDF_PIPELINE,
        ImportMethod.RULE_BASED,
        resolved=True,
        is_stage_direction=False,
        side=SideEnum.RESPONDENT,
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.PROVISIONAL
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.PROVISIONAL
    finally:
        await _teardown_argument(
            ids,
            extra_import_run_ids=[second["import_run_id"]],
            extra_utterance_ids=[second["utterance_id"]],
            extra_person_ids=[second["person_id"]],
        )


# ---------------------------------------------------------------------------
# D-11 / D-12 carve-out tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unresolved_speaker_drags_trusted_argument_to_uncertain():
    """D-11: one utterance with person_id NULL floors an otherwise-trusted argument."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER"), (False, False, "RESPONDENT")],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_stage_direction_unresolved_speaker_is_excluded():
    """D-12: an unresolved stage-direction utterance does NOT drag the tier down."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER"), (False, True, "UNKNOWN")],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.TRUSTED
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.TRUSTED
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_side_unknown_non_stage_direction_speaker_is_not_excluded():
    """D-12: a side=UNKNOWN (but NOT stage-direction) unresolved utterance DOES drag the tier down."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER"), (False, False, "UNKNOWN")],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_unresolved_participant_drags_tier_to_uncertain():
    """An ArgumentParticipant with person_id NULL drags the tier to uncertain."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
        participant_specs=[False],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_resolved_participant_with_unset_provenance_drags_tier_to_uncertain():
    """
    Phase 49 (D-18) supersedes D-13's Phase 48 placeholder: a resolved
    ArgumentParticipant (person_id NOT NULL) now contributes a REAL tier
    derived from its own (source, method, review_state) columns instead of
    contributing nothing. `_seed_argument`'s `participant_specs=[True]` sets
    person_id but leaves source/method NULL and review_state at its
    migration-0028 default (UNREVIEWED) — derive_tier("", "", "unreviewed")
    matches none of rules 1-6 and fail-closes to UNCERTAIN (rule 7), which
    now floors an otherwise-TRUSTED argument down to UNCERTAIN. This is the
    intended, fail-closed direction (TRUST-02): a participant with no
    recorded provenance no longer rides along for free — it now surfaces as
    needing review, which is the whole point of the Phase 49 review model.
    """
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
        participant_specs=[True],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_zero_constituent_argument_recomputes_to_uncertain():
    """An argument with zero utterances and zero participants recomputes to uncertain."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# Phase 53 plan 53-01 Task 2 (D-05/D-06/D-18): sentinel PROVISIONAL floor +
# majority-undetermined blocker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_resolved_and_sentinel_stays_provisional_no_blocker():
    """[resolved, sentinel] -> PROVISIONAL with an empty blocker list."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER"), (False, False, "UNKNOWN", True)],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.PROVISIONAL
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.PROVISIONAL
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert blockers == []
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_sentinel_plus_unresolved_non_sentinel_is_uncertain():
    """[sentinel, unresolved non-sentinel] -> UNCERTAIN with exactly one
    unresolved_utterance_speaker of count 1 -- the sentinel row is not
    counted as unresolved (Pitfall 2 ordering)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(False, False, "UNKNOWN", True), (False, False, "UNKNOWN")],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert blockers == [{"code": "unresolved_utterance_speaker", "count": 1}]
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_three_of_five_sentinel_holds_with_majority_blocker():
    """3 sentinel + 2 resolved -> UNCERTAIN, blockers contain
    {"code": "majority_undetermined_speaker", "count": 3, "percent": 60}."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[
            (True, False, "PETITIONER"),
            (True, False, "RESPONDENT"),
            (False, False, "UNKNOWN", True),
            (False, False, "UNKNOWN", True),
            (False, False, "UNKNOWN", True),
        ],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "majority_undetermined_speaker", "count": 3, "percent": 60} in blockers
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_two_of_four_sentinel_stays_provisional_no_majority_blocker():
    """2 sentinel + 2 resolved -> PROVISIONAL, no majority blocker (exactly
    half is NOT held -- strictly greater than half is required, D-06)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[
            (True, False, "PETITIONER"),
            (True, False, "RESPONDENT"),
            (False, False, "UNKNOWN", True),
            (False, False, "UNKNOWN", True),
        ],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.PROVISIONAL
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.PROVISIONAL
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert not any(b["code"] == "majority_undetermined_speaker" for b in blockers)
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_stage_directions_do_not_dilute_majority_ratio():
    """2 sentinel + 1 resolved + 3 stage directions -> majority blocker
    with percent 67 -- stage-direction rows are excluded from BOTH the
    numerator and the denominator, so they cannot dilute the ratio to
    33 (2 of 6) instead of the correct 67 (2 of 3)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[
            (True, False, "PETITIONER"),
            (False, False, "UNKNOWN", True),
            (False, False, "UNKNOWN", True),
            (False, True, "UNKNOWN"),
            (False, True, "UNKNOWN"),
            (False, True, "UNKNOWN"),
        ],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "majority_undetermined_speaker", "count": 2, "percent": 67} in blockers
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_null_speaker_undetermined_flag_fails_closed():
    """A row with an explicit NULL speaker_undetermined flag (the
    pre-migration-0033 shape) and no person takes the existing unresolved
    path -> UNCERTAIN with unresolved_utterance_speaker (fail closed) --
    never treated as a sentinel."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier, summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(False, False, "UNKNOWN", None)],
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await recompute_argument_tier(db, ids["argument_id"])
            assert result is TrustTier.UNCERTAIN
            await db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.UNCERTAIN
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "unresolved_utterance_speaker", "count": 1} in blockers
        assert not any(b["code"] == "majority_undetermined_speaker" for b in blockers)
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# Idempotence + non-committing contract (48-RESEARCH.md Pitfall 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_is_idempotent_on_unchanged_data():
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        async with AsyncSessionLocal() as db:
            first = await recompute_argument_tier(db, ids["argument_id"])
            await db.commit()

        async with AsyncSessionLocal() as db:
            second = await recompute_argument_tier(db, ids["argument_id"])
            await db.commit()

        assert first is second is TrustTier.TRUSTED
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_does_not_commit_until_caller_commits():
    """
    recompute_argument_tier issues its UPDATE but does NOT commit
    (48-RESEARCH.md Pitfall 2) — a separate session must still see the
    pre-call value until the first session's own commit runs.
    """
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ImportMethod, ImportSource
    from api.services.trust import recompute_argument_tier

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        async with AsyncSessionLocal() as write_db:
            result = await recompute_argument_tier(write_db, ids["argument_id"])
            assert result is TrustTier.TRUSTED

            # A separate, concurrent session must still see the pre-call
            # default (uncertain) — write_db has not committed yet.
            async with AsyncSessionLocal() as read_db:
                argument = await read_db.get(Argument, ids["argument_id"])
                assert argument.trust_tier is TrustTier.UNCERTAIN

            await write_db.commit()

        async with AsyncSessionLocal() as db:
            argument = await db.get(Argument, ids["argument_id"])
            assert argument.trust_tier is TrustTier.TRUSTED
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# summarize_tier_blockers coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_blocker_unresolved_utterance_speaker():
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.trust import summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(False, False, "PETITIONER"), (False, False, "RESPONDENT"), (False, False, "UNKNOWN")],
    )
    try:
        async with AsyncSessionLocal() as db:
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "unresolved_utterance_speaker", "count": 3} in blockers
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_blocker_unresolved_participant():
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.trust import summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
        participant_specs=[False],
    )
    try:
        async with AsyncSessionLocal() as db:
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "unresolved_participant", "count": 1} in blockers
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_blocker_llm_corrective_utterance():
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.trust import summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.PDF_PIPELINE,
        ImportMethod.LLM_CORRECTIVE,
        utterance_specs=[(True, False, "PETITIONER"), (True, False, "RESPONDENT")],
    )
    try:
        async with AsyncSessionLocal() as db:
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "llm_corrective_utterance", "count": 2} in blockers
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_blocker_no_constituents():
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.trust import summarize_tier_blockers

    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[],
    )
    try:
        async with AsyncSessionLocal() as db:
            blockers = await summarize_tier_blockers(db, ids["argument_id"])
        assert {"code": "no_constituents", "count": 1} in blockers
    finally:
        await _teardown_argument(ids)
