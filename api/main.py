"""
SCOTUS Chat FastAPI application.

Entry point: uvicorn api.main:app --reload --port 8000

The app uses the lifespan context manager (not deprecated @app.on_event) to
initialise the async database engine on startup and dispose it on shutdown.
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.core.config import settings
from api.core.database import lifespan
from api.routers import admin as admin_router
from api.routers import admin_dev as admin_dev_router
from api.routers import admin_review as admin_review_router
from api.routers import arguments as arguments_router
from api.routers import people as people_router

app = FastAPI(
    title="SCOTUS Chat API",
    description="Read-only API for Supreme Court oral argument transcripts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(arguments_router.router)
app.include_router(people_router.router)
app.include_router(admin_router.router)
app.include_router(admin_review_router.router)

# Dev-only "Reset to Fixture" router: mounted ONLY when
# settings.environment == "development" (allow-list comparison). In every
# other environment this route is genuinely unregistered — a request to it
# 404s because FastAPI never learned the route exists, not because a
# handler-level check returned 403. A handler-body 403 is deliberately NOT
# used here: a 403 would confirm to a prober that the endpoint exists at all.
if settings.environment == "development":
    app.include_router(admin_dev_router.router)

# Serve locally-stored photos at /uploads/people/{file}.
# The mount is added after router includes so API routes take precedence.
# Harmless when DO Spaces is the active storage path (directory stays empty).
os.makedirs("data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")


@app.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 when the process is running."""
    return {"status": "ok"}
