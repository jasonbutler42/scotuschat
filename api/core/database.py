"""
Async database engine, session factory, and FastAPI lifespan handler.

Key invariants:
  - statement_cache_size=0 is in connect_args (not top-level) — required for
    PgBouncer Transaction mode on Digital Ocean. Passing it as a top-level
    kwarg silently has no effect (SQLAlchemy bug reference: gh#6467).
  - expire_on_commit=False prevents MissingGreenlet errors when accessing
    ORM attributes after session.commit() in async context.
  - Engine is created inside lifespan, not at module import — avoids
    requiring DATABASE_URL at import time (e.g. during test collection).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.core.config import settings

# Module-level globals initialised inside lifespan
engine: Optional[object] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Creates the async engine and session factory on startup, disposes the
    engine on shutdown.  Use this instead of deprecated @app.on_event("startup").
    """
    global engine, AsyncSessionLocal
    engine = create_async_engine(
        settings.database_url,
        connect_args={"statement_cache_size": 0},  # REQUIRED for PgBouncer — in connect_args NOT top-level
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,  # prevents MissingGreenlet on attribute access after commit
    )
    yield
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a scoped AsyncSession.

    Usage:
        @router.get("/...")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database session factory is not initialised — "
            "lifespan may not have completed startup."
        )
    async with AsyncSessionLocal() as session:
        yield session
