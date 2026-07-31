"""
43-04 Task 1, steps 2 and 21: print row counts for the tables the reset touches.

Run from the project root:
    ./.venv/Scripts/python.exe .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_counts.py

Run it once before the reset (step 2) and once after (step 21) and compare.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.core.config import settings

TABLES = [
    "arguments",
    "utterances",
    "people",
    "court_tenures",
    "argument_participants",
    "cases",
    "admin_jobs",
    "roles",
]


async def main():
    engine = create_async_engine(
        settings.database_url,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.connect() as conn:
        for table in TABLES:
            count = (await conn.execute(text(f"select count(*) from {table}"))).scalar()
            print(f"{table}: {count}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
