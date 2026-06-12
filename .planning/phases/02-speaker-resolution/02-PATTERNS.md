# Phase 2: Speaker Resolution - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 11 (6 new, 5 modified + 1 Svelte component modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `alembic/versions/0002_add_speaker_alias.py` | migration | batch | `alembic/versions/0001_initial_schema.py` | exact |
| `api/models/models.py` (add SpeakerAlias) | model | CRUD | `api/models/models.py` (existing models) | exact |
| `pipeline/commands/resolve.py` | service | CRUD + event-driven (interactive) | `pipeline/commands/parse.py` | exact |
| `pipeline/commands/seed_aliases.py` | service | batch | `pipeline/commands/ingest.py` | exact |
| `api/routers/people.py` | controller | request-response | `api/routers/arguments.py` | exact |
| `api/services/people.py` | service | CRUD | `api/services/arguments.py` | role-match |
| `api/schemas/people.py` | model | request-response | `api/schemas/utterance.py` | exact |
| `api/main.py` (add include_router) | config | request-response | `api/main.py` (existing) | exact |
| `api/services/arguments.py` (extend JOIN) | service | CRUD | `api/services/arguments.py` (existing) | exact |
| `api/schemas/utterance.py` (add speaker fields) | model | request-response | `api/schemas/utterance.py` (existing) | exact |
| `pipeline/__main__.py` (add subcommands) | config | request-response | `pipeline/__main__.py` (existing) | exact |
| `app/src/lib/components/ChatBubble.svelte` (speaker display) | component | request-response | `app/src/lib/components/ChatBubble.svelte` (existing) | exact |

---

## Pattern Assignments

### `alembic/versions/0002_add_speaker_alias.py` (migration, batch)

**Analog:** `alembic/versions/0001_initial_schema.py`

**Header / revision identifiers pattern** (lines 22-32):
```python
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgENUM

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Core create_table pattern with FK, UniqueConstraint, index** (lines 59-66 and 166-191 from 0001):
```python
def upgrade() -> None:
    op.create_table(
        "speaker_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_label", sa.String(300), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),  # sa.text() for server_default — matches 0001 pattern
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_label", name="uq_speaker_alias_label"),
    )
    op.create_index(
        "ix_speaker_alias_normalized_label", "speaker_alias", ["normalized_label"]
    )

def downgrade() -> None:
    op.drop_index("ix_speaker_alias_normalized_label", table_name="speaker_alias")
    op.drop_table("speaker_alias")
```

**Key rules from analog:**
- FK constraints expressed as `sa.ForeignKeyConstraint(["col"], ["table.id"])` — not inline
- `server_default=sa.text("now()")` — not Python `datetime.now`
- `PgENUM(name="type_name", create_type=False)` for existing enum types (not needed for speaker_alias but follow the pattern if adding enum columns)
- Drop in reverse dependency order in `downgrade()`
- No `Base.metadata.create_all` — hand-written only

---

### `api/models/models.py` — add SpeakerAlias class (model, CRUD)

**Analog:** existing model classes in `api/models/models.py`

**ORM model pattern** (lines 62-80 from models.py — Role + Person as templates):
```python
# Imports already present at top of models.py — no new imports needed:
# Column, Integer, String, Text, DateTime, ForeignKey, func are all imported

class SpeakerAlias(Base):
    __tablename__ = "speaker_alias"

    id = Column(Integer, primary_key=True)
    normalized_label = Column(String(300), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
```

**Key rules from analog:**
- `Column(Type, primary_key=True)` — no `autoincrement=True` needed (SQLAlchemy default)
- `server_default=func.now()` for timestamp columns (matches `PipelineRun.created_at` on line 204)
- `unique=True` inline on column for single-column uniqueness (matches `Role.name` on line 66)
- ForeignKey as string `"table.id"` — matches all existing FK columns
- No `relationship()` declarations — project does not use ORM relationships

---

### `pipeline/commands/resolve.py` (service, CRUD + interactive)

**Analog:** `pipeline/commands/parse.py`

**Imports pattern** (lines 24-41 from parse.py):
```python
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    ArgumentParticipant,
    Person,
    PipelineRun,
    PipelineRunStatus,
    Role,
    SpeakerAlias,
    Utterance,
)
from pipeline.db import get_session
```

**Outer async function + session context pattern** (lines 43-82 from parse.py):
```python
async def run_resolve(args) -> None:
    """
    Args:
        args: argparse.Namespace with:
            - run_id (int): pipeline_run.id from a prior PARSE step
    """
    async with get_session() as session:
        # Step 1: Load the source parse run (read-only input)
        parse_run: Optional[PipelineRun] = await session.get(PipelineRun, args.run_id)
        if parse_run is None:
            raise ValueError(f"No pipeline_run with id={args.run_id}")

        # Step 2: Create a NEW resolve pipeline_run (never mutate the parse run)
        resolve_run = PipelineRun(
            argument_id=parse_run.argument_id,
            step="resolve",
            status=PipelineRunStatus.RUNNING,
        )
        session.add(resolve_run)
        await session.flush()  # get resolve_run.id
```

**PipelineRunStatus transition pattern** (lines 78-82, 194-200 from parse.py):
```python
        # On completion
        resolve_run.status = PipelineRunStatus.COMPLETED
        resolve_run.completed_at = datetime.now(timezone.utc)
        print("Resolve complete.")
```

**KeyboardInterrupt + needs_review pattern** (based on parse.py error handling structure):
```python
        try:
            # ... resolve logic ...
            resolve_run.status = PipelineRunStatus.COMPLETED
            resolve_run.completed_at = datetime.now(timezone.utc)
        except KeyboardInterrupt:
            resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
            await session.flush()
            print("\nInterrupted — run status set to needs_review. Re-run to continue.")
            return
```
`NEEDS_REVIEW` is already in `PipelineRunStatus` enum (models.py line 44).

**select() scalar query pattern** (lines 65-68 from parse.py):
```python
result = await session.execute(
    select(SpeakerAlias).where(SpeakerAlias.normalized_label == normalized_label)
)
alias = result.scalar_one_or_none()
```

**Bulk UPDATE pattern** (not in parse.py — uses SQLAlchemy 2.0 execute(update()) form):
```python
from sqlalchemy import update

await session.execute(
    update(Utterance)
    .where(
        Utterance.argument_id == parse_run.argument_id,
        Utterance.pipeline_run_id == args.run_id,
        Utterance.raw_speaker_label == raw_label,   # raw form — NOT normalized
    )
    .values(person_id=resolved_person_id)
    .execution_options(synchronize_session=False)   # bypass stale identity map
)
```

**session.flush() pattern** (lines 157, 164 from ingest.py):
```python
session.add(new_obj)
await session.flush()  # get obj.id without committing
```
Commit happens on clean `async with get_session()` exit — no explicit `session.commit()` call.

---

### `pipeline/commands/seed_aliases.py` (service, batch)

**Analog:** `pipeline/commands/ingest.py`

**Imports + session pattern** (lines 20-32 from ingest.py):
```python
from sqlalchemy import select

from api.models.models import Person, Role, SpeakerAlias
from pipeline.db import get_session


async def run_seed_aliases(args) -> None:
    async with get_session() as session:
        # ...
```

**Idempotency pattern — check-before-insert** (lines 129-136 from ingest.py):
```python
result = await session.execute(
    select(Role).where(Role.name == role_name)
)
existing = result.scalar_one_or_none()

if existing is not None:
    print(f"Role '{role_name}' already exists (id={existing.id}) — reusing.")
    role = existing
else:
    role = Role(name=role_name)
    session.add(role)
    await session.flush()
```
Apply same pattern for Person rows (check by full_name) and SpeakerAlias rows (check by normalized_label). This makes `seed-aliases` safe to re-run without duplicating rows.

**flush-then-use-id pattern** (lines 156-164 from ingest.py):
```python
session.add(person)
await session.flush()  # get person.id before creating alias rows that reference it

alias = SpeakerAlias(
    normalized_label="JUSTICE KAGAN",
    person_id=person.id,
)
session.add(alias)
```

---

### `api/routers/people.py` (controller, request-response)

**Analog:** `api/routers/arguments.py`

**Full file pattern** (lines 1-38 from arguments.py):
```python
"""
FastAPI router for people endpoints.

Endpoints:
  GET /people/{person_id}
    Returns a person record with resolved name and role.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.people import PersonResponse
from api.services import people as people_service

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: int,                           # int annotation = FastAPI injection prevention (T-05-01)
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """
    Return person metadata by ID.

    Path parameter `person_id` is validated as int by FastAPI — non-integer
    values produce a 422 Unprocessable Entity response without reaching the
    service layer.

    Returns 404 if the person ID is not found.
    """
    result = await people_service.get_person_by_id(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return result
```

---

### `api/services/people.py` (service, CRUD)

**Analog:** `api/services/arguments.py`

**Imports + function signature pattern** (lines 17-26 from arguments.py):
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Person, Role


async def get_person_by_id(
    db: AsyncSession,
    person_id: int,
) -> dict | None:
```

**SELECT with join + scalar_one_or_none pattern** (lines 46-64 from arguments.py):
```python
    result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .where(Person.id == person_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    person, role_name = row
    return {
        "id": person.id,
        "full_name": person.full_name,
        "role_name": role_name,   # None if person has no role_id
    }
```

**Return type:** `dict | None` — matches `arguments.py` signature (line 26). Pydantic validates at the router layer via `response_model=PersonResponse`.

---

### `api/schemas/people.py` (model, request-response)

**Analog:** `api/schemas/utterance.py`

**Pydantic v2 BaseModel pattern** (lines 22-36 from utterance.py):
```python
"""
Pydantic v2 response models for the people API endpoint.
"""

from typing import Optional

from pydantic import BaseModel


class PersonResponse(BaseModel):
    """A resolved speaker — Justice or counsel."""

    id: int
    full_name: str
    role_name: Optional[str] = None  # None if person has no role assigned

    model_config = {"from_attributes": True}
```

**Key rules from analog:**
- `Optional[str] = None` for nullable fields — matches `utterance.py` pattern for `raw_speaker_label`, `section_hint`, `person_id`
- `model_config = {"from_attributes": True}` — required for ORM-to-Pydantic deserialization
- No validators needed for this read-only response schema

---

### `api/main.py` — add include_router (config, request-response)

**Analog:** `api/main.py` lines 13-22

**Existing pattern to copy exactly:**
```python
# Existing lines 13-22:
from api.core.database import lifespan
from api.routers import arguments as arguments_router

app = FastAPI(
    title="SCOTUS Chat API",
    description="Read-only API for Supreme Court oral argument transcripts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(arguments_router.router)
```

**Add parallel import + include_router:**
```python
from api.routers import arguments as arguments_router
from api.routers import people as people_router   # ADD

app.include_router(arguments_router.router)
app.include_router(people_router.router)          # ADD
```
One new import line and one new `include_router` call. No other changes.

---

### `api/services/arguments.py` — extend utterances query with JOIN (service, CRUD)

**Analog:** `api/services/arguments.py` (the file being modified)

**Current Step 4 to be replaced** (lines 94-104):
```python
# CURRENT — pure ORM select, returns Utterance scalars
utterances_result = await db.execute(
    select(Utterance)
    .where(
        Utterance.argument_id == argument_id,
        Utterance.pipeline_run_id == max_run_id,
    )
    .order_by(Utterance.sequence.asc())
)
utterances = list(utterances_result.scalars().all())
```

**Replacement — JOIN select returning Row tuples:**
```python
# ADD Person, Role to imports at line 21
from api.models.models import Argument, Case, CaseArgument, Person, PipelineRun, PipelineRunStatus, Role, Utterance

# Replace Step 4 body:
utterances_result = await db.execute(
    select(
        Utterance,
        Person.full_name.label("speaker_name"),
        Role.name.label("speaker_role"),
    )
    .outerjoin(Person, Utterance.person_id == Person.id)
    .outerjoin(Role, Person.role_id == Role.id)
    .where(
        Utterance.argument_id == argument_id,
        Utterance.pipeline_run_id == max_run_id,
    )
    .order_by(Utterance.sequence.asc())
)
rows = utterances_result.all()   # Returns Row tuples, not scalars

# Build dicts for Pydantic (from_attributes won't work on Row tuples — Pitfall 6)
utterances = [
    {
        **{c.key: getattr(utterance, c.key) for c in utterance.__table__.columns},
        "speaker_name": speaker_name,
        "speaker_role": speaker_role,
    }
    for utterance, speaker_name, speaker_role in rows
]
```

**Step 5 response assembly** — `utterances` list now contains dicts; the router passes them to `ArgumentUtterancesResponse` which uses `UtteranceResponse.model_validate(u)` implicitly via Pydantic's list coercion. `from_attributes=True` on `UtteranceResponse` handles both pure ORM objects and dicts.

---

### `api/schemas/utterance.py` — add speaker_name, speaker_role (model, request-response)

**Analog:** `api/schemas/utterance.py` (the file being modified)

**Existing UtteranceResponse** (lines 22-36):
```python
class UtteranceResponse(BaseModel):
    id: int
    sequence: int
    raw_speaker_label: Optional[str] = None
    text: str
    is_stage_direction: bool
    side: str
    section_hint: Optional[str] = None
    person_id: Optional[int] = None
    strategy: str
    pipeline_run_id: int

    model_config = {"from_attributes": True}
```

**Two lines to add — follow existing Optional[str] = None pattern:**
```python
class UtteranceResponse(BaseModel):
    id: int
    sequence: int
    raw_speaker_label: Optional[str] = None
    text: str
    is_stage_direction: bool
    side: str
    section_hint: Optional[str] = None
    person_id: Optional[int] = None
    strategy: str
    pipeline_run_id: int
    speaker_name: Optional[str] = None   # Phase 2: resolved from people table
    speaker_role: Optional[str] = None   # Phase 2: resolved from roles table

    model_config = {"from_attributes": True}
```

`Optional[str] = None` default preserves backward compatibility — Phase 1 parsed utterances with no `person_id` will return `null` for both new fields.

---

### `pipeline/__main__.py` — add resolve + seed-aliases subcommands (config, request-response)

**Analog:** `pipeline/__main__.py` (the file being modified)

**Existing import + subparser block pattern** (lines 27-29):
```python
from pipeline.commands.ingest import run_ingest
from pipeline.commands.parse import run_parse
```

**Add two parallel imports:**
```python
from pipeline.commands.resolve import run_resolve
from pipeline.commands.seed_aliases import run_seed_aliases
```

**Existing subparser definition pattern** (lines 88-106 — parse subcommand):
```python
parse_p = sub.add_parser(
    "parse",
    help="Parse transcript into utterances (Plan 04)",
    description=("..."),
)
parse_p.add_argument(
    "--run-id",
    required=True,
    type=int,
    help="pipeline_run.id from a prior ingest step",
)
parse_p.add_argument(
    "--dry-run",
    action="store_true",
    help="Parse but do not write utterance rows to the DB",
)
```

**New subparsers to add following the same pattern:**
```python
# resolve subcommand
resolve_p = sub.add_parser(
    "resolve",
    help="Interactively resolve raw speaker labels to people records",
    description=(
        "For each unique speaker label in a parse run, look up the alias table "
        "or prompt the operator to map it to a Person record."
    ),
)
resolve_p.add_argument(
    "--run-id",
    required=True,
    type=int,
    help="pipeline_run.id from a prior PARSE step (step='parse', status=COMPLETED)",
)

# seed-aliases subcommand
sub.add_parser(
    "seed-aliases",
    help="Pre-seed Justice people records and speaker_alias rows",
    description=(
        "Insert roles, people, and speaker_alias rows for all current and "
        "relevant historical SCOTUS Justices. Idempotent — safe to re-run."
    ),
)
```

**Dispatch block — extend existing if/elif chain** (lines 110-113):
```python
# Existing:
if args.command == "ingest":
    asyncio.run(run_ingest(args))
elif args.command == "parse":
    asyncio.run(run_parse(args))

# Add:
elif args.command == "resolve":
    asyncio.run(run_resolve(args))
elif args.command == "seed-aliases":
    asyncio.run(run_seed_aliases(args))
```

---

### `app/src/lib/components/ChatBubble.svelte` — speaker name display (component, request-response)

**Analog:** `app/src/lib/components/ChatBubble.svelte` (the file being modified)

**Existing $props() and derived constant pattern** (lines 1-7):
```svelte
<script lang="ts">
    let { utterance } = $props();

    const isBench = utterance.side === 'BENCH';
    const labelColor = isBench ? '#94a3b8' : '#93c5fd';
</script>
```

**Add two derived constants following the same pattern:**
```svelte
<script lang="ts">
    let { utterance } = $props();

    const isBench = utterance.side === 'BENCH';
    const labelColor = isBench ? '#94a3b8' : '#93c5fd';
    // Phase 2: use resolved name when available, fall back to raw label
    const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
    const displayRole = utterance.speaker_role ?? null;
</script>
```

**Existing speaker label span** (lines 47-55):
```svelte
<span
    style="
        font-size: 13px;
        font-weight: 600;
        color: {labelColor};
    "
>
    {utterance.raw_speaker_label ?? ''}
</span>
```

**Replace with displayName + optional role span:**
```svelte
<span
    style="
        font-size: 13px;
        font-weight: 600;
        color: {labelColor};
    "
>
    {displayName}
</span>
{#if displayRole}
    <span
        style="
            font-size: 11px;
            color: #475569;
        "
    >
        {displayRole}
    </span>
{/if}
```

**Key rules from analog:**
- No `export let` — Svelte 5 Runes only; `$props()` destructuring is the established pattern (line 2)
- All styling is inline `style=` strings — no CSS classes, no `<style>` blocks in this component
- `??` nullish coalescing for optional fields — matches existing `{utterance.raw_speaker_label ?? ''}` pattern (line 53)

---

## Shared Patterns

### Async Session — Pipeline Commands
**Source:** `pipeline/db.py` lines 47-71
**Apply to:** `pipeline/commands/resolve.py`, `pipeline/commands/seed_aliases.py`
```python
async with get_session() as session:
    obj = SomeModel(...)
    session.add(obj)
    await session.flush()   # get obj.id without committing
    # commit happens on clean context manager exit; rollback on exception
```
- `expire_on_commit=False` already set in session factory — do not override
- `statement_cache_size=0` already set in engine — do not add to command code
- No explicit `await session.commit()` — the context manager handles it
- Explicit `await session.rollback()` is also handled by context manager on exception

### FastAPI Dependency Injection — API Layer
**Source:** `api/core/database.py` lines 52-68 + `api/routers/arguments.py` lines 12-14
**Apply to:** `api/routers/people.py`, `api/services/people.py`
```python
from api.core.database import get_db
# In router:
db: AsyncSession = Depends(get_db)
# In service signature:
async def get_thing(db: AsyncSession, id: int) -> dict | None:
```

### 404 Pattern — API Routers
**Source:** `api/routers/arguments.py` lines 35-38
**Apply to:** `api/routers/people.py`
```python
result = await service.get_by_id(db, id)
if result is None:
    raise HTTPException(status_code=404, detail="Person not found")
return result
```
Service returns `None` for missing records; router raises HTTPException. No try/except in router layer.

### Idempotency — Pipeline Seed Commands
**Source:** `pipeline/commands/ingest.py` lines 129-136
**Apply to:** `pipeline/commands/seed_aliases.py` (for Role, Person, and SpeakerAlias rows)
```python
result = await session.execute(select(Model).where(Model.field == value))
existing = result.scalar_one_or_none()
if existing is not None:
    # reuse existing row
else:
    new_obj = Model(...)
    session.add(new_obj)
    await session.flush()
```

### Pydantic Optional Fields with Null Default
**Source:** `api/schemas/utterance.py` lines 27-32
**Apply to:** `api/schemas/people.py` (role_name field), `api/schemas/utterance.py` (two new fields)
```python
field_name: Optional[str] = None  # comment explaining when non-null
```
Always import `Optional` from `typing`. Pydantic v2 also accepts `str | None = None` — use `Optional[str]` to match existing codebase style.

---

## No Analog Found

All files in Phase 2 have close codebase analogs. No entries in this section.

---

## Critical Implementation Notes (from RESEARCH.md pitfalls)

These are not patterns but constraints the planner must enforce in task descriptions:

1. **Pitfall 2 — raw vs normalized label:** Keep two variables. `raw_label` for `UPDATE WHERE utterances.raw_speaker_label = raw_label`. `normalize_label(raw_label)` only for alias table lookup and INSERT. Never use normalized form to query utterances.

2. **Pitfall 3 — synchronize_session:** Add `.execution_options(synchronize_session=False)` to all `execute(update(...))` calls. Do not re-read updated utterance objects from the same session.

3. **Pitfall 4 — KeyboardInterrupt scope:** Wrap `asyncio.run(run_resolve(args))` in `pipeline/__main__.py` with a top-level `try/except KeyboardInterrupt` that prints a clean message, in addition to the inner catch inside `run_resolve()`.

4. **Pitfall 5 — models + migration in sync:** Add `SpeakerAlias` to `models.py` at the same time as writing `0002_add_speaker_alias.py`. Run `alembic upgrade head` immediately after both files exist.

5. **Pitfall 6 — from_attributes on Row tuples:** After the JOIN query change in `arguments.py`, assemble utterances as dicts (`{**utterance.__dict__, "speaker_name": ..., "speaker_role": ...}`) before Pydantic validation. Do not rely on `from_attributes=True` to pull labeled columns from a SQLAlchemy `Row`.

6. **Resolve creates its own PipelineRun:** `run_resolve()` inserts a NEW `PipelineRun(step="resolve", ...)`. It reads the parse run as input but never mutates it. `--run-id` is the parse run id; the resolve run gets a new id via `session.flush()`.

---

## Metadata

**Analog search scope:** `alembic/versions/`, `api/models/`, `api/routers/`, `api/services/`, `api/schemas/`, `api/core/`, `pipeline/commands/`, `pipeline/db.py`, `pipeline/__main__.py`, `app/src/lib/components/`
**Files scanned:** 12 analog files read in full
**Pattern extraction date:** 2026-06-12
