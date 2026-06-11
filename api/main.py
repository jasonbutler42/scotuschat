"""
SCOTUS Chat FastAPI application.

Entry point: uvicorn api.main:app --reload --port 8000

The app uses the lifespan context manager (not deprecated @app.on_event) to
initialise the async database engine on startup and dispose it on shutdown.
"""

from fastapi import FastAPI

from api.core.database import lifespan
from api.routers import arguments as arguments_router

app = FastAPI(
    title="SCOTUS Chat API",
    description="Read-only API for Supreme Court oral argument transcripts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(arguments_router.router)


@app.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 when the process is running."""
    return {"status": "ok"}
