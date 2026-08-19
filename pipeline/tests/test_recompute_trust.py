"""
Coverage for the offline recompute-trust CLI command (Phase 48, plan 48-06).

Locks: `--all` repairs real drift and reports an accurate changed count,
re-running `--all` is idempotent (changed == 0), `--dry-run` reports without
writing, `--argument-id` scopes to exactly one argument, an unknown
`--argument-id` raises ValueError naming the id, and `--all` against an
empty database reports scanned == 0 / changed == 0 rather than failing or
succeeding vacuously (D-09/D-21's falsifiable verification vehicle).

Reuses plan 48-01's argument-seeding helper (`_seed_argument`/
`_teardown_argument`) from api/tests/test_trust_recompute.py rather than
duplicating the seeding logic in a second file, per this plan's <action>.
That helper builds sessions via api.core.database.AsyncSessionLocal, which
is only populated once FastAPI's lifespan() has run — api/tests/conftest.py
has an autouse fixture that does this for every test under api/tests/, but
pipeline/tests/ has no equivalent (pipeline commands normally build
sessions via pipeline.db.get_session() instead, which recompute_trust.py
itself uses). `_api_lifespan_for_recompute_trust` below reproduces that same
one-time lifespan bootstrap for exactly this module, mirroring
api/tests/conftest.py::_api_lifespan.

recompute-trust's own `--all` path scans EVERY row in `arguments` via
pipeline.db.get_session() (a separate engine from AsyncSessionLocal) — so,
unlike a single-argument-scoped test, an exact scanned/changed count needs a
genuinely COMMITTED empty table, not just an empty view inside one
subsequently-rolled-back transaction (pipeline/tests/conftest.py's clean_db
fixture only truncates inside its own async_session's transaction, which
that fixture rolls back at teardown — invisible to, and undone before, any
other engine's session ever reads it). `_reset_arguments_table` below
mirrors pipeline/tests/conftest.py's own session-scoped `_reset_test_db`
hard safety guard and TRUNCATE list exactly, run per-test instead of once
per session, so `--all`'s scan is deterministic regardless of what else ran
earlier in the same pytest session.
"""

from __future__ import annotations

import argparse
import os

import pytest
import pytest_asyncio
from sqlalchemy import text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.domain.trust import TrustTier
from api.models.models import Argument, ImportMethod, ImportSource
from api.tests.test_trust_recompute import _seed_argument, _teardown_argument
from pipeline.commands.recompute_trust import run_recompute_trust


def _db_configured() -> bool:
    """Same guard api/tests/test_trust_recompute.py uses (post-redirect DATABASE_URL)."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


requires_db = pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")


@pytest_asyncio.fixture(autouse=True)
async def _api_lifespan_for_recompute_trust():
    """
    Bootstrap api.core.database.AsyncSessionLocal for this module's imported
    seeding helper (see module docstring) — mirrors
    api/tests/conftest.py::_api_lifespan exactly, scoped to this module only
    since pipeline/tests/ has no equivalent autouse fixture of its own.
    """
    if not _db_configured():
        yield
        return
    from api.core.database import lifespan
    from api.main import app

    async with lifespan(app):
        yield


@pytest_asyncio.fixture(autouse=True)
async def _reset_arguments_table():
    """
    Genuinely (committed) empty the trust-relevant tables before AND after
    every test in this module.

    HARD SAFETY GUARD, mirrored verbatim from pipeline/tests/conftest.py's
    session-scoped `_reset_test_db`: reads TEST_DATABASE_URL directly
    (never DATABASE_URL, which — if TEST_DATABASE_URL were unset — could be
    the real shared dev DB) and no-ops unless the resolved database name is
    exactly "scotus_test".
    """
    test_url = os.environ.get("TEST_DATABASE_URL", "")
    if not test_url or make_url(test_url).database != "scotus_test":
        yield
        return

    reset_engine = create_async_engine(
        test_url, connect_args={"statement_cache_size": 0}, pool_size=2, echo=False
    )

    async def _truncate() -> None:
        async with reset_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    TRUNCATE TABLE
                        utterances,
                        import_run,
                        case_arguments,
                        case_appearances,
                        argument_participants,
                        arguments,
                        cases,
                        court_tenures,
                        people,
                        roles
                    CASCADE
                    """
                )
            )

    try:
        await _truncate()
        yield
        await _truncate()
    finally:
        await reset_engine.dispose()


async def _corrupt_tier(argument_id: int, tier: TrustTier) -> None:
    """Directly overwrite Argument.trust_tier to a deliberately-wrong value, bypassing derive_tier."""
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Argument).where(Argument.id == argument_id).values(trust_tier=tier)
        )
        await db.commit()


async def _read_tier(argument_id: int) -> TrustTier:
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        argument = await db.get(Argument, argument_id)
        return argument.trust_tier


def _all_args(*, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(all=True, argument_id=None, dry_run=dry_run)


def _single_args(argument_id: int, *, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(all=False, argument_id=argument_id, dry_run=dry_run)


# ---------------------------------------------------------------------------
# --all repairs real drift and reports an accurate changed count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_all_repairs_drifted_tier(capsys):
    """
    A corpus/direct argument with one resolved utterance derives to TRUSTED.
    Corrupting the stored value to UNCERTAIN and running --all must repair
    it back to TRUSTED and report exactly one changed argument.
    """
    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        await _corrupt_tier(ids["argument_id"], TrustTier.UNCERTAIN)

        await run_recompute_trust(_all_args())
        out = capsys.readouterr().out

        assert f"argument {ids['argument_id']}: uncertain -> trusted" in out
        assert "1 scanned" in out
        assert "0 unchanged" in out
        assert "1 changed." in out

        assert await _read_tier(ids["argument_id"]) is TrustTier.TRUSTED
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# Idempotence — the adjacency edge plan 48-09 relies on
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_all_is_idempotent(capsys):
    """Running --all twice in a row reports changed == 0 on the second run."""
    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        await _corrupt_tier(ids["argument_id"], TrustTier.UNCERTAIN)

        await run_recompute_trust(_all_args())
        capsys.readouterr()  # discard first run's output

        await run_recompute_trust(_all_args())
        out = capsys.readouterr().out

        assert "0 changed." in out
        assert await _read_tier(ids["argument_id"]) is TrustTier.TRUSTED
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# --dry-run reports without writing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_dry_run_reports_without_writing(capsys):
    """--dry-run against a corrupted row reports changed == 1 but leaves the stored value untouched."""
    ids = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    try:
        await _corrupt_tier(ids["argument_id"], TrustTier.UNCERTAIN)

        await run_recompute_trust(_all_args(dry_run=True))
        out = capsys.readouterr().out

        assert f"argument {ids['argument_id']}: uncertain -> trusted" in out
        assert "1 changed." in out

        # Nothing was actually written — the corrupted value survives.
        assert await _read_tier(ids["argument_id"]) is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(ids)


# ---------------------------------------------------------------------------
# --argument-id scopes to exactly one argument
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_single_argument_scopes_to_that_argument(capsys):
    """--argument-id repairs only the named argument, leaving a second corrupted argument untouched."""
    first = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "PETITIONER")],
    )
    second = await _seed_argument(
        ImportSource.CORPUS,
        ImportMethod.DIRECT,
        utterance_specs=[(True, False, "RESPONDENT")],
    )
    try:
        await _corrupt_tier(first["argument_id"], TrustTier.UNCERTAIN)
        await _corrupt_tier(second["argument_id"], TrustTier.UNCERTAIN)

        await run_recompute_trust(_single_args(first["argument_id"]))
        out = capsys.readouterr().out

        assert "1 scanned" in out
        assert f"argument {first['argument_id']}: uncertain -> trusted" in out
        assert str(second["argument_id"]) not in out

        assert await _read_tier(first["argument_id"]) is TrustTier.TRUSTED
        assert await _read_tier(second["argument_id"]) is TrustTier.UNCERTAIN
    finally:
        await _teardown_argument(first)
        await _teardown_argument(second)


# ---------------------------------------------------------------------------
# Unknown --argument-id raises rather than reporting a vacuous success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_unknown_argument_id_raises():
    """--argument-id for an id that does not exist raises ValueError naming the id."""
    unknown_id = 999_999_999
    with pytest.raises(ValueError, match=str(unknown_id)):
        await run_recompute_trust(_single_args(unknown_id))


# ---------------------------------------------------------------------------
# Empty-database edge — must not fail and must not report success vacuously
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@requires_db
async def test_recompute_all_on_empty_database_reports_zero(capsys):
    """--all against an empty database (no seeding) reports scanned == 0, changed == 0."""
    await run_recompute_trust(_all_args())
    out = capsys.readouterr().out

    assert "0 scanned" in out
    assert "0 unchanged" in out
    assert "0 changed." in out
