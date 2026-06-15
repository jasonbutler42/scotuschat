"""
FastAPI admin router — Phase 5 foundation for the v1.1 operator admin interface.

Endpoints:
  GET /api/admin/health
    Smoke-test target; verifies the 401 auth dependency is wired correctly.
    Returns {"status": "ok"} when X-Admin-Token matches settings.admin_token.

Auth:
  All routes are protected via the router-level verify_admin_token dependency
  (injected at APIRouter construction, not per-route). Phase 6 replaces
  verify_admin_token with HMAC session-cookie auth in a single location.

Prefix:
  /api/admin — full prefix (not bare /admin) to avoid collision with
  SvelteKit's /admin/* page routes (D-09).
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.database import get_db


async def verify_admin_token(x_admin_token: str = Header(...)) -> None:
    """
    Throwaway token check — Phase 6 replaces this with HMAC session cookie auth.

    The dependency is injected at the router level so Phase 6 can swap it
    without touching individual route signatures (D-12).

    Security notes (T-05-01, T-05-05):
    - The inbound token value must never be logged or echoed in a response.
    - The settings.admin_token value must never be logged or echoed in a response.
    - The 401 response body is the constant string "Unauthorized" — no token
      information, no timing-revealing detail returned to the client.
    """
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/health")
async def admin_health() -> dict:
    """Smoke-test target — verifies the 401 dependency is wired before Phase 7 routes land."""
    return {"status": "ok"}
