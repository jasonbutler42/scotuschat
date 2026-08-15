"""
43-04 Task 1, step 22: print each fixture's status/resolved/published/job state.

Run from the project root:
    ./.venv/Scripts/python.exe .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_states.py

Expect:
  13015  draft     resolved=True   published=False  job=completed
  15169  pipeline  resolved=False  published=False  job=paused     (step: resolve)
  18897  published resolved=True   published=True   job=completed
  22372  pipeline  resolved=False  published=False  job=running    (step: resolve)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.core.config import settings

QUERY = """
select
    a.oyez_transcript_id,
    a.status,
    a.resolved_at is not null as resolved,
    a.published_at is not null as published,
    j.status as job_status,
    j.current_step as job_step
from arguments a
left join admin_jobs j on j.argument_id = a.id
order by a.oyez_transcript_id
"""


async def main():
    engine = create_async_engine(
        settings.database_url,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(text(QUERY))).all()
        for row in rows:
            print(row)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
