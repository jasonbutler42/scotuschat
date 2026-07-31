"""
43-04 Task 1, step 24: prove the complexity fixture (15169) carries Phase 42's
corrected counts.

Run from the project root:
    ./.venv/Scripts/python.exe .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_fixture_integrity.py

Expect: 480 utterances, 1 with a non-null section_hint, 17 participants.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.core.config import settings

TRANSCRIPT_ID = "15169"

UTTERANCE_QUERY = """
select count(*), count(u.section_hint)
from utterances u
join arguments a on a.id = u.argument_id
where a.oyez_transcript_id = :transcript_id
"""

PARTICIPANT_QUERY = """
select count(*)
from argument_participants p
join arguments a on a.id = p.argument_id
where a.oyez_transcript_id = :transcript_id
"""


async def main():
    engine = create_async_engine(
        settings.database_url,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.connect() as conn:
        total, with_hint = (
            await conn.execute(text(UTTERANCE_QUERY), {"transcript_id": TRANSCRIPT_ID})
        ).one()
        print(f"utterances: {total} total, {with_hint} with a section_hint")

        (participants,) = (
            await conn.execute(text(PARTICIPANT_QUERY), {"transcript_id": TRANSCRIPT_ID})
        ).one()
        print(f"argument_participants: {participants}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
