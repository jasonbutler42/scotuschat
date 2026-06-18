# Phase 5: Admin Foundation - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 5
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0003_add_admin_jobs.py` | migration | batch (DDL) | `alembic/versions/0002_add_speaker_alias.py` | exact |
| `api/models/models.py` | model | CRUD | `api/models/models.py` (PipelineRun, SpeakerAlias) | exact (same file) |
| `api/routers/admin.py` | router | request-response | `api/routers/people.py` | role-match |
| `api/core/config.py` | config | — | `api/core/config.py` (Settings class) | exact (same file) |
| `api/main.py` | config/entrypoint | — | `api/main.py` (existing include_router block) | exact (same file) |

---

## Pattern Assignments

### `alembic/versions/0003_add_admin_jobs.py` (migration, DDL)

**Analog:** `alembic/versions/0002_add_speaker_alias.py`

**File header / revision block** (lines 1–23):
```python
"""Add admin_jobs table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15

Adds the admin_jobs table:
  - Tracks operator-initiated pipeline jobs for the v1.1 admin UI
  - status and current_step stored as PG enum types
  - argument_id is a nullable FK to arguments; NULL until ingest creates the row
  - discrepancies stored as JSONB for batch fire-and-poll reads
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**upgrade() structure** (lines 25–55, adapted from 0002 lines 25–50):
```python
def upgrade() -> None:
    # Enum types must be created before the table that uses them
    admin_job_status = sa.Enum(
        "pending", "running", "paused", "completed", "failed",
        name="admin_job_status",
    )
    admin_job_step = sa.Enum(
        "ingest", "parse", "resolve",
        name="admin_job_step",
    )
    admin_job_status.create(op.get_bind(), checkfirst=True)
    admin_job_step.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "admin_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", admin_job_status, nullable=False, server_default="pending"),
        sa.Column("current_step", admin_job_step, nullable=True),
        sa.Column("argument_id", sa.Integer(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("spaces_key", sa.Text(), nullable=True),
        sa.Column("discrepancies", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
```

Note: `sa.JSON()` maps to PostgreSQL JSONB when using the asyncpg dialect. If the project prefers explicit JSONB, use `sa.dialects.postgresql.JSONB()` and add `from sqlalchemy.dialects import postgresql` to imports. Either works; match whichever other migrations use if a JSONB column exists elsewhere.

**downgrade() structure** (lines 57–62, mirroring 0002 lines 53–55):
```python
def downgrade() -> None:
    op.drop_table("admin_jobs")
    op.execute("DROP TYPE IF EXISTS admin_job_status")
    op.execute("DROP TYPE IF EXISTS admin_job_step")
```

---

### `api/models/models.py` — additions only (model, CRUD)

**Analog:** existing `PipelineRun` and `SpeakerAlias` classes in the same file.

**Enum block to add** — copy the `PipelineRunStatus` pattern (lines 39–44) but with new values:
```python
class AdminJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AdminJobStep(str, enum.Enum):
    INGEST = "ingest"
    PARSE = "parse"
    RESOLVE = "resolve"
```

Place immediately after `PipelineRunStatus` (after line 44), before the `Base` declaration.

**ORM class to add** — copy the `PipelineRun` pattern (lines 193–210) for DateTime/Enum/nullable FK columns:
```python
# ---------------------------------------------------------------------------
# Table 12: admin_jobs
# Tracks operator-initiated pipeline jobs submitted via the admin UI.
# status and current_step use PG enums defined in migration 0003.
# argument_id is nullable FK — NULL until ingest creates the argument row.
# discrepancies is JSONB — read as a batch during fire-and-poll.
# ---------------------------------------------------------------------------


class AdminJob(Base):
    __tablename__ = "admin_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(
        SAEnum(AdminJobStatus, name="admin_job_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=AdminJobStatus.PENDING,
    )
    current_step = Column(
        SAEnum(AdminJobStep, name="admin_job_step", values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=True)
    pdf_url = Column(Text, nullable=True)
    spaces_key = Column(Text, nullable=True)
    discrepancies = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Add `JSON` to the existing `sqlalchemy` import block (line 10–24). The `SAEnum`, `ForeignKey`, `Text`, `DateTime`, `func`, `Integer`, `Column` imports already exist.

---

### `api/routers/admin.py` (router, request-response)

**Analog:** `api/routers/people.py`

**Imports pattern** (people.py lines 9–15 — adapt for admin):
```python
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.database import get_db
```

**Auth dependency** — new pattern, no existing analog. Place as a module-level function before the router:
```python
async def verify_admin_token(x_admin_token: str = Header(...)) -> None:
    """
    Throwaway token check — Phase 6 replaces this with HMAC session cookie auth.
    The dependency is injected at the router level so Phase 6 can swap it
    without touching individual route signatures.
    """
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
```

**Router declaration** — copy the prefix/tags pattern from people.py line 16, add router-level dependency:
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```

Note: `prefix="/api/admin"` rather than `prefix="/admin"` per D-09. Other routers use bare prefixes (`/people`, `/cases`) because `main.py` does not add a global `/api` prefix; the admin router uses the full prefix to avoid any future collision with SvelteKit's `/admin/*` page routes.

**Health route** — copy the response pattern from `api/main.py` lines 29–32:
```python
@router.get("/health")
async def admin_health() -> dict:
    """Smoke-test target — verifies the 401 dependency is wired before Phase 7 routes land."""
    return {"status": "ok"}
```

---

### `api/core/config.py` — addition only (config)

**Analog:** existing `Settings` class (lines 11–28).

**Field to add** — copy the `database_url: str` pattern (line 14); insert after `debug`:
```python
admin_token: str  # required; set via ADMIN_TOKEN env var
```

No default value — the app should refuse to start without it, matching the same fail-fast posture as `database_url`.

---

### `api/main.py` — two-line modification (entrypoint)

**Analog:** existing `include_router` block (lines 13–26).

**Import to add** (after line 15):
```python
from api.routers import admin as admin_router
```

**Router mount to add** (after line 26):
```python
app.include_router(admin_router.router)
```

---

## Shared Patterns

### Dependency injection (get_db)
**Source:** `api/core/database.py` (imported in all existing routers)
**Apply to:** `api/routers/admin.py` for any Phase 7 DB-touching routes
**Pattern:** `db: AsyncSession = Depends(get_db)` as a route parameter — not used by the Phase 5 health route but the import should be present so Phase 7 can add it without structural changes.

### SAEnum with values_callable
**Source:** `api/models/models.py` lines 183 and 200–203
**Apply to:** `AdminJobStatus` and `AdminJobStep` columns in `AdminJob`
```python
SAEnum(AdminJobStatus, name="admin_job_status", values_callable=lambda e: [x.value for x in e])
```
This pattern ensures the PG enum type uses the `.value` strings (`"pending"`, not `"PENDING"`), consistent with every other enum in the file.

### DateTime with server_default=func.now()
**Source:** `api/models/models.py` lines 204–205 (`PipelineRun.created_at`)
**Apply to:** `AdminJob.created_at` and `AdminJob.updated_at`
```python
created_at = Column(DateTime(timezone=True), server_default=func.now())
```
`func.now()` is the project convention — not `sa.text("now()")` in the ORM layer (migrations use `sa.text("now()")` directly in `op.create_table`).

### Router-level dependency (not middleware)
**Source:** D-12 / specifics section in 05-CONTEXT.md
**Apply to:** `api/routers/admin.py` router declaration
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```
Placing the dependency at the `APIRouter` constructor rather than per-route or as ASGI middleware is the surgical-replacement pattern Phase 6 requires. Phase 6 replaces `verify_admin_token` with the HMAC cookie dependency in one place.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `verify_admin_token` dependency (inside admin.py) | middleware/dependency | request-response | No auth dependency pattern exists yet — this is the first protected router in the project |

---

## Metadata

**Analog search scope:** `alembic/versions/`, `api/routers/`, `api/models/`, `api/core/`, `api/main.py`
**Files scanned:** 5 analog files read in full
**Pattern extraction date:** 2026-06-15
