"""
Async SQLAlchemy engine and session factory for the pipeline CLI.

The pipeline shares the same models as the FastAPI API (api/models/models.py)
but maintains its own engine instance. The engine is created lazily to avoid
failing at import time when DATABASE_URL is not set.

IMPORTANT: connect_args={"statement_cache_size": 0} is mandatory for asyncpg
compatibility behind Digital Ocean PgBouncer Transaction mode (CLAUDE.md).
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Load DATABASE_URL from .env at module level
load_dotenv()


def get_engine():
    """
    Create and return an async SQLAlchemy engine for the pipeline CLI.

    The engine is created lazily (called inside asyncio.run() wrappers)
    so DATABASE_URL failures surface at command execution time, not import time.

    connect_args={"statement_cache_size": 0} is in connect_args (NOT as a
    top-level kwarg) — required for asyncpg behind PgBouncer Transaction mode.
    See: github.com/sqlalchemy/sqlalchemy/issues/6467
    """
    database_url = os.environ["DATABASE_URL"]
    return create_async_engine(
        database_url,
        connect_args={"statement_cache_size": 0, "ssl": False},
        pool_size=2,  # pipeline is single-process CLI; small pool is sufficient
        echo=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields an AsyncSession.

    Usage:
        async with get_session() as session:
            session.add(obj)
            # commit happens inside context manager

    expire_on_commit=False is mandatory in async SQLAlchemy — otherwise lazy-
    loading expired attributes after commit triggers a sync DB call and raises
    MissingGreenlet.
    """
    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await engine.dispose()
