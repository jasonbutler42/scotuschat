"""
REVIEW-01 schema contract test for `argument_participants` (Phase 49, plan
49-01, Task 2).

Asserts, against the live test database after `alembic upgrade head`:
  1. The PG type `review_state` exists with exactly the four ordered
     values `unreviewed`, `needs_review`, `operator_confirmed`,
     `operator_edited` (set equality AND length 4 — the enum is one-way,
     PostgreSQL cannot drop a value, so this is the tripwire for a fifth
     value added later).
  2. `argument_participants` has columns `review_state`, `source`,
     `method`; `review_state` is NOT NULL with column default
     `'unreviewed'::review_state`; `source`/`method` are nullable and
     typed `import_source`/`import_method`.
  3. A freshly inserted `argument_participants` row that OMITS
     `review_state` (a raw INSERT, bypassing the ORM's Python-side
     `default=ReviewState.UNREVIEWED` so the database's own
     `server_default` is what is actually exercised) reads back
     `ReviewState.UNREVIEWED`.
  4. `api.models.models.ReviewState` and the PG type agree — the Python
     enum's `.value` set equals the `pg_enum` set (catches model/migration
     drift).

NOTE: this file asserts only the `argument_participants` half of REVIEW-01.
The `people` half (review_state on `people`) is asserted by this same file
after plan 49-02 lands migration 0029 — this file is knowingly incomplete
until then.

Follows this repo's DB-gated integration pattern (`_db_configured()` guard,
same as `api/tests/test_admin_review_service.py`) and the live-engine
column-introspection style of
`api/tests/test_migration_0022_person_name_authority.py`. No conftest is
added here — the repo-root `conftest.py` owns the TEST_DATABASE_URL
redirect.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio


def _db_configured() -> bool:
    """Same guard every DB-gated api/tests module uses (WR-04)."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


pytestmark = pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")


# ---------------------------------------------------------------------------
# 1. The PG enum type itself: exactly four values.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_state_pg_enum_has_exactly_four_values() -> None:
    from sqlalchemy import text

    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'review_state'
                ORDER BY e.enumsortorder
                """
            )
        )
        labels = [row[0] for row in result.all()]

    expected = ["unreviewed", "needs_review", "operator_confirmed", "operator_edited"]
    assert len(labels) == 4, (
        f"review_state PG enum must have exactly 4 values (one-way — PG "
        f"cannot drop a value); found {len(labels)}: {labels}"
    )
    assert set(labels) == set(expected)


# ---------------------------------------------------------------------------
# 2. Column presence, nullability, and default/type on argument_participants.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_participants_review_state_source_method_columns() -> None:
    from sqlalchemy import text

    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT column_name, is_nullable, column_default, udt_name
                FROM information_schema.columns
                WHERE table_name = 'argument_participants'
                  AND column_name IN ('review_state', 'source', 'method')
                """
            )
        )
        columns = {row.column_name: row for row in result.all()}

    assert set(columns) == {"review_state", "source", "method"}

    review_state = columns["review_state"]
    assert review_state.is_nullable == "NO"
    assert review_state.column_default is not None
    assert "unreviewed" in review_state.column_default
    assert review_state.udt_name == "review_state"

    source = columns["source"]
    assert source.is_nullable == "YES"
    assert source.udt_name == "import_source"

    method = columns["method"]
    assert method.is_nullable == "YES"
    assert method.udt_name == "import_method"

    # Model-level metadata check, distinct from the live-DB introspection
    # above: catches a `server_default`/`nullable` regression directly in
    # api/models/models.py, even before a new migration would ever apply
    # it. (Spot-checked: removing `server_default="unreviewed"` from the
    # ReviewState column in models.py makes this assertion fail.)
    from api.models.models import ArgumentParticipant

    model_review_state_col = ArgumentParticipant.__table__.columns["review_state"]
    assert model_review_state_col.server_default is not None
    assert not model_review_state_col.nullable


# ---------------------------------------------------------------------------
# 3. A row that omits review_state at INSERT time reads back UNREVIEWED via
#    the database's own server_default (not the ORM's Python-side default).
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def _bare_argument():
    """One CANDIDATE argument with no participants, for the raw-INSERT test
    below. Deleted in teardown."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    yield arg_id

    from sqlalchemy import delete as sa_delete

    async with AsyncSessionLocal() as db:
        await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
        await db.commit()


@pytest.mark.asyncio
async def test_insert_without_review_state_defaults_to_unreviewed(_bare_argument) -> None:
    from sqlalchemy import text

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, ReviewState

    arg_id = _bare_argument
    participant_id: int | None = None
    try:
        async with AsyncSessionLocal() as db:
            # Raw INSERT deliberately omits review_state — this is the
            # column the DATABASE's server_default must supply, not the
            # ORM's Python-side `default=ReviewState.UNREVIEWED` (which
            # would mask a missing/incorrect server_default entirely).
            result = await db.execute(
                text(
                    """
                    INSERT INTO argument_participants
                        (argument_id, raw_speaker_label, side)
                    VALUES (:argument_id, :raw_speaker_label, :side)
                    RETURNING id
                    """
                ),
                {
                    "argument_id": arg_id,
                    "raw_speaker_label": "REVIEW-01 SCHEMA FIXTURE",
                    "side": "PETITIONER",
                },
            )
            participant_id = result.scalar_one()
            await db.commit()

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, participant_id)
            assert participant.review_state == ReviewState.UNREVIEWED
    finally:
        if participant_id is not None:
            from sqlalchemy import delete as sa_delete

            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(ArgumentParticipant).where(
                        ArgumentParticipant.id == participant_id
                    )
                )
                await db.commit()


# ---------------------------------------------------------------------------
# 4. Python enum and PG enum agree (model/migration drift tripwire).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_python_review_state_enum_matches_pg_enum() -> None:
    from sqlalchemy import text

    from api.core.database import AsyncSessionLocal
    from api.models.models import ReviewState

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'review_state'
                """
            )
        )
        pg_values = {row[0] for row in result.all()}

    python_values = {member.value for member in ReviewState}
    assert python_values == pg_values
