# Phase 2: Speaker Resolution — Research

**Researched:** 2026-06-12
**Domain:** Python async SQLAlchemy / Alembic migration / FastAPI router / Svelte 5 Runes chat UI
**Confidence:** HIGH — all findings verified against actual codebase; no external library research required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `speaker_alias` uses exact string matching — each row stores a normalized label (e.g., `"JUSTICE KAGAN"`) mapped to a `person_id`. No regex patterns.
- **D-02:** Labels normalized before lookup: uppercase + strip trailing colon + trim whitespace. Example: `"Justice Kagan:"` → `"JUSTICE KAGAN"`. Applied consistently at resolve time and when saving new alias rows.
- **D-03:** Pre-seed Justices via `python -m pipeline seed-aliases`. Includes current Justices (Roberts, Thomas, Alito, Sotomayor, Kagan, Gorsuch, Kavanaugh, Barrett, Jackson) and recent historical (Scalia, Kennedy, Ginsburg, Breyer). Common label variants included: `"CHIEF JUSTICE"` → Roberts, `"JUSTICE [SURNAME]"` per Justice.
- **D-04:** Counsel records are NOT pre-seeded. Created interactively during the first resolve run and persisted to the alias table.
- **D-05:** Resolve step is interactive CLI. For each unique normalized `raw_speaker_label` (non-stage-directions only): check `speaker_alias` first. Hit → auto-resolve, set `person_id` on all matching utterances. Miss → prompt operator with numbered list of existing `people` + "Create new person".
- **D-06:** Every operator-resolved mapping immediately saved to `speaker_alias` for future auto-resolution.
- **D-07:** `pipeline_run.status` reaches `COMPLETED` only when every unique non-null `raw_speaker_label` has a resolved `person_id`. No skipping allowed.
- **D-08:** Creating new `people` records during interactive session is allowed with operator confirmation. "Never auto-creates" means no automatic creation; interactive creation is explicitly permitted.
- **D-09:** Operator interrupts (Ctrl+C) → `pipeline_run` status set to `needs_review`. Re-run auto-skips already-resolved labels; only unresolved labels prompt again.
- **D-10:** `GET /arguments/{id}/utterances` extended to JOIN `people` and `roles` tables and embed `speaker_name: Optional[str]` and `speaker_role: Optional[str]` directly in each `UtteranceResponse`. Single API call covers chat view needs.
- **D-11:** `GET /people/{id}` (API-03) implemented with `{id, full_name, role_name}`. `photo_url` deferred to Phase 3.

### Claude's Discretion

- Exact `speaker_alias` table column names (suggested: `id`, `normalized_label`, `person_id`, `created_at`, `notes`)
- Whether `argument_participants.person_id` is also updated during resolve (in addition to `utterances.person_id`)
- Seed data file format and exact `seed-aliases` CLI implementation
- Interactive terminal prompt display (numbering format, paging for large people lists)
- How `role_name` is derived — join `people → roles` via `person.role_id`
- `people` table `full_name` format — pick natural display format (e.g., "Elena Kagan")

### Deferred Ideas (OUT OF SCOPE)

- LLM-assisted matching for speaker resolution
- `photo_url` on Person (Phase 3)
- Obergefell Q2 session
- Additional cases beyond Obergefell
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-07 | Resolve step: operator runs CLI, matches raw speaker labels to `people` records | Resolved via alias-lookup + interactive prompt; see Architecture Patterns |
| PIPE-08 | Pre-seeded `speaker_alias` table handles surname-only and role-only labels | Seed command pattern follows existing `ingest.py`; Justice list compiled in Seed Data section |
| PIPE-09 | Resolve step gates low-confidence as `needs_review`; never auto-commits ambiguous; never auto-creates people | Ctrl+C → `needs_review` status (already in `PipelineRunStatus` enum); interactive confirm for new people |
| API-03 | `GET /people/{id}` returns person record (name, role, photo_url) | Follows `arguments` router/service/schema pattern exactly; `photo_url` deferred per D-11 |
</phase_requirements>

---

## Summary

Phase 2 is primarily a plumbing phase: it connects raw speaker labels (already in the database from Phase 1 parse) to `Person` records via an alias lookup table. The implementation has four distinct work streams that can be planned sequentially: (1) schema — one new Alembic migration; (2) pipeline — two new CLI subcommands (`seed-aliases` and `resolve`); (3) API — one new endpoint (`GET /people/{id}`) and a JOIN extension on the existing utterances endpoint; (4) frontend — `ChatBubble.svelte` updated to display resolved name and role instead of raw label.

Every pattern needed for Phase 2 already exists in the Phase 1 codebase. The Alembic migration follows the hand-written style of `0001_initial_schema.py`. The pipeline commands follow the `async with get_session()` pattern from `ingest.py` and `parse.py`. The FastAPI endpoint follows the router/service/schema split from `api/routers/arguments.py`. The Svelte chat view follows the Runes `$props()` pattern from `ChatBubble.svelte`.

No new external libraries are needed. The resolve step is interactive lookup plus database writes — not LLM-driven. The only new ORM model is `SpeakerAlias`.

**Primary recommendation:** Build in four sequential plan chunks: (1) Alembic migration + ORM model, (2) `seed-aliases` + `resolve` pipeline commands, (3) API layer changes, (4) chat view update.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `speaker_alias` table DDL | Database (Alembic) | — | Alembic-only DDL constraint; new migration `0002_add_speaker_alias.py` |
| `SpeakerAlias` ORM model | API models layer (`api/models/models.py`) | — | Models file is the shared ORM registry; pipeline imports from here |
| Justice seed data | Pipeline CLI (`seed-aliases`) | Database | One-time seed; writes `people` + `roles` + `speaker_alias` rows |
| Interactive label resolution | Pipeline CLI (`resolve`) | Database | Offline operator step; reads utterances, writes `person_id`, writes alias rows |
| `GET /people/{id}` | API router/service/schema | Database | Follows existing router-service-schema pattern; read-only |
| Embed `speaker_name/role` in utterances response | API service (`arguments.py`) | Database | JOIN extension on existing query; no new endpoint |
| Display resolved name in chat view | Frontend (`ChatBubble.svelte`) | API | Client-side render; receives fields from `+page.server.ts` load |

---

## Standard Stack

No new external libraries are introduced in Phase 2. All dependencies are already installed.

### Existing Libraries Used

| Library | Purpose in Phase 2 | Where Used |
|---------|-------------------|-----------|
| SQLAlchemy 2.0 async | ORM queries for alias lookup, utterance updates, person creation | `pipeline/commands/resolve.py`, `seed_aliases.py` |
| Alembic | New `0002_add_speaker_alias.py` migration | `alembic/versions/` |
| FastAPI 0.115+ | New `/people/{id}` router; existing utterances router extended | `api/routers/people.py`, `api/services/arguments.py` |
| Pydantic v2 | New `PeopleResponse` schema; `UtteranceResponse` extended | `api/schemas/` |
| python-dotenv | Already used in pipeline and API; no changes | `pipeline/db.py` |
| Svelte 5 (Runes) | `ChatBubble.svelte` updated to use `speaker_name`/`speaker_role` | `app/src/lib/components/` |
| asyncpg | Underlying async DB driver; no changes | Configured in `pipeline/db.py` + `api/core/database.py` |

**Installation:** No `pip install` or `npm install` commands needed for Phase 2. [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

> Phase 2 introduces zero new packages. No audit required.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
PDF + DB (Phase 1 output)
        │
        ▼
[pipeline: seed-aliases]
  - Insert roles rows (if absent)
  - Insert people rows for all Justices
  - Insert speaker_alias rows for Justice label variants
        │
        ▼
[pipeline: resolve --run-id N]
  - Load pipeline_run → utterances for that run
  - Collect unique non-null raw_speaker_labels
  - Normalize each label (uppercase, strip colon, trim)
  ┌──────────────────────────────────────────┐
  │  For each unique normalized label:        │
  │    lookup speaker_alias → person_id?      │
  │      YES (hit) → bulk UPDATE utterances   │
  │      NO (miss) → prompt operator          │
  │        - numbered list of existing people │
  │        - "Create new person" option       │
  │        - save chosen mapping to alias tbl │
  │        - bulk UPDATE utterances           │
  └──────────────────────────────────────────┘
  - On Ctrl+C → set pipeline_run.status = needs_review
  - On full completion → set pipeline_run.status = COMPLETED
        │
        ▼
[PostgreSQL]
  utterances.person_id populated
  speaker_alias rows persisted
        │
        ▼
[FastAPI: GET /arguments/{id}/utterances]
  - Extended query: LEFT JOIN people + roles
  - speaker_name + speaker_role embedded in UtteranceResponse
        │
        ▼
[FastAPI: GET /people/{id}]   ← NEW (API-03)
  - Returns {id, full_name, role_name}
        │
        ▼
[SvelteKit: +page.server.ts]
  - Fetches /arguments/{id}/utterances (unchanged)
  - Returns utterances with speaker_name + speaker_role
        │
        ▼
[ChatBubble.svelte]
  - Renders utterance.speaker_name (not raw_speaker_label)
  - Renders utterance.speaker_role as role label
```

### Recommended Project Structure

New files Phase 2 adds:

```
alembic/versions/
└── 0002_add_speaker_alias.py      # new migration

api/
├── models/models.py               # SpeakerAlias ORM class added here
├── routers/people.py              # NEW — GET /people/{id}
├── services/people.py             # NEW — get_person_by_id()
├── schemas/people.py              # NEW — PersonResponse schema
└── schemas/utterance.py           # EXTENDED — UtteranceResponse gains speaker_name, speaker_role

pipeline/commands/
├── resolve.py                     # NEW — interactive resolve step
└── seed_aliases.py                # NEW — seed Justices + aliases

pipeline/tests/
└── test_resolve.py                # NEW — unit + integration tests
    test_seed_aliases.py           # NEW — seed idempotency test

api/tests/
└── test_people.py                 # NEW — GET /people/{id} tests
```

Existing files modified:

```
api/models/models.py               # add SpeakerAlias class
api/main.py                        # include_router(people_router)
api/services/arguments.py          # extend utterances query with JOIN
pipeline/__main__.py               # add resolve + seed-aliases subcommands
app/src/lib/components/ChatBubble.svelte   # use speaker_name + speaker_role
```

### Pattern 1: Alembic Hand-Written Migration (SpeakerAlias Table)

Following `0001_initial_schema.py` style exactly — hand-written, no autogenerate.

```python
# alembic/versions/0002_add_speaker_alias.py
# Source: alembic/versions/0001_initial_schema.py (project codebase)

revision: str = "0002"
down_revision: Union[str, None] = "0001"

def upgrade() -> None:
    op.create_table(
        "speaker_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_label", sa.String(300), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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

Key choices: `UniqueConstraint` on `normalized_label` (one canonical mapping per label); index for fast exact-match lookup; `notes` nullable text for operator context. [VERIFIED: codebase inspection of 0001 pattern]

### Pattern 2: SpeakerAlias ORM Model

Add to `api/models/models.py` following existing model style:

```python
# Source: api/models/models.py (project codebase — following existing pattern)

class SpeakerAlias(Base):
    __tablename__ = "speaker_alias"

    id = Column(Integer, primary_key=True)
    normalized_label = Column(String(300), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
```

### Pattern 3: Label Normalization Function

Implements D-02. Standalone function — no DB dependency, unit-testable in isolation.

```python
# Source: CONTEXT.md D-02 decision
def normalize_label(raw: str) -> str:
    """Normalize a raw speaker label for alias table lookup.

    Examples:
        "Justice Kagan:"  -> "JUSTICE KAGAN"
        "CHIEF JUSTICE:"  -> "CHIEF JUSTICE"
        "  MR. JONES  "   -> "MR. JONES"
    """
    return raw.strip().rstrip(":").strip().upper()
```

### Pattern 4: Pipeline Command Structure (resolve.py)

Follows `parse.py` and `ingest.py` patterns exactly — `async def run_resolve(args)`, `async with get_session() as session:`, state machine transitions.

```python
# Source: pipeline/commands/parse.py (project codebase — follow exactly)

async def run_resolve(args) -> None:
    async with get_session() as session:
        # 1. Load pipeline_run — must be a parse run, status completed
        run = await session.get(PipelineRun, args.run_id)

        # 2. Create new resolve pipeline_run (step="resolve", status=RUNNING)
        resolve_run = PipelineRun(
            argument_id=run.argument_id,
            step="resolve",
            status=PipelineRunStatus.RUNNING,
        )
        session.add(resolve_run)
        await session.flush()

        try:
            # 3. Collect unique labels, normalize, resolve or prompt
            # 4. Bulk UPDATE utterances.person_id
            # 5. Update argument_participants.person_id (discretionary)
            # 6. Set resolve_run.status = COMPLETED
            ...
        except KeyboardInterrupt:
            resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
            await session.flush()
            print("\nInterrupted — run status set to needs_review.")
            return
```

**Important:** The resolve step creates its own `PipelineRun` row with `step="resolve"`. It does NOT modify the parse run's status. The parse run is read-only input.

### Pattern 5: Bulk UPDATE Utterances

Use SQLAlchemy `update()` with `WHERE` clause instead of row-by-row `session.get()` calls. This handles the case where hundreds of utterances share the same label.

```python
# Source: SQLAlchemy 2.0 async documentation pattern [ASSUMED]
from sqlalchemy import update

await session.execute(
    update(Utterance)
    .where(
        Utterance.argument_id == argument_id,
        Utterance.pipeline_run_id == parse_run_id,
        Utterance.raw_speaker_label == raw_label,  # pre-normalization raw label
    )
    .values(person_id=resolved_person_id)
)
```

**Note:** The alias table stores the normalized label; utterances store the raw label. The resolve loop must collect raw labels, normalize each for alias lookup, but UPDATE utterances using the original raw label to match all variants. [ASSUMED — design reasoning, not verified against SQLAlchemy docs in this session]

### Pattern 6: Interactive Prompt Display

Standard Python `input()` — no new library needed. Display format:

```
Resolving 13 unique labels — 9 auto-matched from alias table, 4 need input.

Unknown label: "MR. MARY BONAUTO"
  1. Mary Bonauto (Petitioner's Counsel)
  2. John Bursch (Respondent's Counsel)
  ...
  N. Create new person

Enter number (or Ctrl+C to pause): _
```

When "Create new person" is selected, prompt for:
- Full name (required)
- Role (display numbered list of existing `roles` rows; allow creating new role)

### Pattern 7: FastAPI People Router

Follows `api/routers/arguments.py` pattern exactly:

```python
# api/routers/people.py
# Source: api/routers/arguments.py (project codebase)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.schemas.people import PersonResponse
from api.services import people as people_service

router = APIRouter(prefix="/people", tags=["people"])

@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    result = await people_service.get_person_by_id(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return result
```

### Pattern 8: Extended Utterances JOIN Query

`api/services/arguments.py` Step 4 extended to LEFT JOIN people + roles:

```python
# Source: api/services/arguments.py (project codebase) + SQLAlchemy 2.0 join pattern [ASSUMED]
from sqlalchemy import func, select
from api.models.models import Argument, Case, CaseArgument, Person, PipelineRun, PipelineRunStatus, Role, Utterance

# Replace the current bare Utterance select with a joined select:
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
rows = utterances_result.all()
```

The service then assembles each row into a dict that includes both ORM columns and the joined name/role fields. `UtteranceResponse` must switch from `from_attributes=True` (ORM object) to `model_validate(dict)` since the result is now a tuple row, not a pure ORM object. [ASSUMED — needs verification during implementation; may be able to keep from_attributes with a named tuple approach]

### Pattern 9: UtteranceResponse Extension

```python
# api/schemas/utterance.py — add two optional fields
class UtteranceResponse(BaseModel):
    ...existing fields...
    speaker_name: Optional[str] = None   # Phase 2: resolved from people table
    speaker_role: Optional[str] = None   # Phase 2: resolved from roles table
```

`Optional[str] = None` preserves backward compatibility — Phase 1 clients see null for unresolved utterances. [VERIFIED: existing schema uses same Optional[str] = None pattern for person_id]

### Pattern 10: Svelte 5 ChatBubble Update

Use resolved name when available, fall back to raw label. Runes pattern (`$props()`) is already established.

```svelte
<!-- app/src/lib/components/ChatBubble.svelte -->
<!-- Source: existing ChatBubble.svelte (project codebase) -->
<script lang="ts">
    let { utterance } = $props();
    const isBench = utterance.side === 'BENCH';
    const labelColor = isBench ? '#94a3b8' : '#93c5fd';
    // Use resolved name if available, fall back to raw label
    const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
    const displayRole = utterance.speaker_role ?? null;
</script>

<!-- In the bubble header row: -->
<span style="font-size: 13px; font-weight: 600; color: {labelColor};">
    {displayName}
</span>
{#if displayRole}
    <span style="font-size: 11px; color: #475569;">
        {displayRole}
    </span>
{/if}
```

### Anti-Patterns to Avoid

- **`Base.metadata.create_all`**: Never. Alembic only. (Hard constraint CLAUDE.md)
- **Regex patterns in alias table**: D-01 explicitly prohibits. Exact string matching only.
- **LLM-assisted matching in resolve step**: Deferred. Not in Phase 2 scope.
- **Exposing pipeline step as HTTP endpoint**: CLAUDE.md hard constraint. `resolve` and `seed-aliases` are CLI-only.
- **Row-by-row utterance updates in a Python loop**: Use `UPDATE ... WHERE` SQL statement. Obergefell has 377 utterances — a loop with individual flushes is fragile.
- **`autogenerate` for migrations**: 01-02 decision requires hand-written migrations for explicit FK dependency order control. The 0001 migration sets the pattern.
- **`PUBLIC_` prefix for FASTAPI_BASE_URL**: CLAUDE.md constraint. Server-only env var.
- **`export let` in Svelte components**: 01-01 decision. Use `$props()` only (Svelte 5 Runes).
- **Deleting prior parse run utterances before resolve**: PIPE-11 prohibits. Resolve writes to existing utterance rows via UPDATE (sets person_id); it does not delete and recreate rows.
- **Modifying the parse PipelineRun status from the resolve step**: The resolve step creates its OWN pipeline_run row (step="resolve"). The parse run is immutable from resolve's perspective.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async DB session management | Custom context manager | `pipeline/db.py get_session()` already exists | Handles commit/rollback/dispose correctly; asyncpg statement_cache_size=0 already set |
| FastAPI dependency injection | Manual session passing | `api/core/database.py get_db()` already exists | Lifespan-managed engine; expire_on_commit=False already set |
| Label normalization | Complex regex | Simple `str.strip().rstrip(':').strip().upper()` | D-02 specifies exact algorithm; over-engineering creates inconsistency |
| Interactive prompts | Curses / rich / prompt_toolkit | Built-in `input()` | Pipeline is operator-only CLI; no library needed for a numbered list |
| Pydantic response models | Manual dict validation | Pydantic v2 `BaseModel` | Already in use across all API schemas |
| SQL bulk update | Python loop + flush per row | SQLAlchemy `update().where().values()` | Single SQL statement; handles 300+ utterances atomically |

---

## Seed Data Reference

Justices and alias variants required for D-03. All current (as of 2026-06-12) and Phase 2 relevant historical Justices. [ASSUMED — based on public knowledge of SCOTUS membership; operator should verify completeness before running]

### Roles to Seed

| Role Name | Notes |
|-----------|-------|
| Chief Justice | For Roberts |
| Associate Justice | For all other Justices |
| Petitioner's Counsel | Generic role for advocate side |
| Respondent's Counsel | Generic role for advocate side |

### Justices to Seed (People rows + Alias rows)

| Full Name | Role | Label Variants |
|-----------|------|----------------|
| John G. Roberts, Jr. | Chief Justice | `CHIEF JUSTICE`, `CHIEF JUSTICE ROBERTS` |
| Clarence Thomas | Associate Justice | `JUSTICE THOMAS` |
| Samuel A. Alito, Jr. | Associate Justice | `JUSTICE ALITO` |
| Sonia Sotomayor | Associate Justice | `JUSTICE SOTOMAYOR` |
| Elena Kagan | Associate Justice | `JUSTICE KAGAN` |
| Neil M. Gorsuch | Associate Justice | `JUSTICE GORSUCH` |
| Brett M. Kavanaugh | Associate Justice | `JUSTICE KAVANAUGH` |
| Amy Coney Barrett | Associate Justice | `JUSTICE BARRETT` |
| Ketanji Brown Jackson | Associate Justice | `JUSTICE JACKSON` |
| Antonin Scalia | Associate Justice | `JUSTICE SCALIA` |
| Anthony M. Kennedy | Associate Justice | `JUSTICE KENNEDY` |
| Ruth Bader Ginsburg | Associate Justice | `JUSTICE GINSBURG` |
| Stephen G. Breyer | Associate Justice | `JUSTICE BREYER` |

**Note on Obergefell (2015):** The active Justices in Obergefell were Roberts, Thomas, Ginsburg, Breyer, Alito, Sotomayor, Kagan, Kennedy, and Scalia. The seed should include all 13 above so the alias table is future-proof for cases argued in different terms. [ASSUMED — public historical record; verify exact transcript labels against actual Obergefell parsed output before finalizing]

### Obergefell Counsel (NOT pre-seeded — interactive resolve creates them)

Expected counsel appearing in Obergefell Q1 transcript (based on public case record): Mary Bonauto (Petitioner), Douglas Hallward-Driemeier (Petitioner), John Bursch (Respondent), Joseph Whalen (Respondent), Donald Verrilli (Solicitor General). These are created interactively during the first resolve run, not pre-seeded. [ASSUMED — based on public case record; exact raw_speaker_label values must be confirmed from actual `utterances` table after Phase 1 parse]

---

## Common Pitfalls

### Pitfall 1: Resolve Run Creates a New PipelineRun vs. Modifying the Parse Run

**What goes wrong:** Developer sets `step="resolve"` on the existing parse `PipelineRun` instead of inserting a new row.
**Why it happens:** It seems simpler to update status in-place. But PIPE-11 says re-running any step produces new rows.
**How to avoid:** `run_resolve()` always inserts a new `PipelineRun(step="resolve", ...)`. It reads the parse run as input but never mutates it. The `--run-id` argument refers to the PARSE run (the source of utterances), not the resolve run.
**Warning signs:** If the service layer's "find latest completed parse run" query starts returning the resolve run, the step value was set incorrectly.

### Pitfall 2: Raw Label vs. Normalized Label Confusion

**What goes wrong:** Code normalizes the label for alias lookup but then uses the normalized form to UPDATE utterances. Since `utterances.raw_speaker_label` stores the un-normalized form, the WHERE clause finds zero rows.
**Why it happens:** The normalization function transforms the string, making it easy to use the wrong version downstream.
**How to avoid:** Keep two variables: `raw_label` (from utterances query — used for UPDATE WHERE clause) and `normalized_label = normalize_label(raw_label)` (used only for alias table lookup and INSERT). Never use normalized form to query `utterances`.

### Pitfall 3: SQLAlchemy async `update()` Requires Synchronize Session

**What goes wrong:** After `session.execute(update(Utterance).where(...).values(person_id=X))`, later reads of those Utterance objects from the session cache still show `person_id=None` because SQLAlchemy's identity map is not refreshed by a bulk update statement.
**Why it happens:** `execute(update(...))` bypasses the ORM identity map. The session cache is stale.
**How to avoid:** Either (a) do the bulk UPDATE then not re-read those objects from the same session, or (b) call `await session.flush()` followed by `await session.refresh(obj)` if individual objects are needed. In the resolve flow, reading back utterances is not needed — only the UPDATE matters. Use `execution_options(synchronize_session=False)` on the update statement to explicitly opt out of synchronization overhead.
**Warning signs:** Progress counts read from in-memory ORM objects after bulk updates show stale values.

### Pitfall 4: KeyboardInterrupt Not Caught in asyncio.run()

**What goes wrong:** `KeyboardInterrupt` raised during `asyncio.run(run_resolve(args))` propagates past the `try/except KeyboardInterrupt` block inside the coroutine, so `pipeline_run.status` is never set to `needs_review` and the transaction is rolled back without saving state.
**Why it happens:** `KeyboardInterrupt` in Python is raised in the main thread and can bypass `try/except` inside asyncio tasks in some scenarios. However, because `run_resolve()` is a coroutine running directly in `asyncio.run()` (not a Task), the `KeyboardInterrupt` is typically delivered to the coroutine's suspension point.
**How to avoid:** Wrap the resolve logic in `try/except KeyboardInterrupt` at the outermost level of `run_resolve()`. Additionally, wrap `asyncio.run(run_resolve(args))` in `__main__.py` with a `try/except KeyboardInterrupt` at the top level that prints a clean message. Verify the `needs_review` path works by testing with Ctrl+C on a mid-resolve run. [ASSUMED — asyncio interrupt behavior is environment-dependent; verify during implementation]

### Pitfall 5: Alembic Autogenerate Detects SpeakerAlias Before Migration Runs

**What goes wrong:** After adding `SpeakerAlias` to `api/models/models.py` but before running `alembic upgrade head`, running `alembic revision --autogenerate` produces a new migration that conflicts with the hand-written `0002_add_speaker_alias.py`.
**Why it happens:** The `env.py` imports `Base` from `api/models/models.py` — autogenerate always sees all current models.
**How to avoid:** Follow the 01-02 decision: write the migration by hand, don't use autogenerate. Add `SpeakerAlias` to `models.py` at the same time as writing `0002_add_speaker_alias.py`. Run `alembic upgrade head` immediately to keep schema and models in sync.

### Pitfall 6: `from_attributes=True` Breaks When UtteranceResponse Gets Non-ORM Fields

**What goes wrong:** `UtteranceResponse` currently uses `from_attributes=True` to deserialize directly from `Utterance` ORM objects. When the utterances query switches to a JOIN that returns `Row` tuples (not pure ORM objects), Pydantic can no longer auto-populate `speaker_name` and `speaker_role` from attributes.
**Why it happens:** SQLAlchemy `select(Utterance, Person.full_name.label(...))` returns `Row` objects, not `Utterance` instances.
**How to avoid:** In `arguments.py` service, explicitly build a dict from each row: `{**utterance.__dict__, "speaker_name": speaker_name, "speaker_role": speaker_role}` and validate with `UtteranceResponse.model_validate(the_dict)` instead of relying on ORM auto-mapping. The `from_attributes=True` config can remain for backward compatibility with code that passes pure ORM objects. [ASSUMED — Pydantic v2 + SQLAlchemy Row behavior; verify during implementation]

### Pitfall 7: `argument_participants.person_id` Left Stale

**What goes wrong:** `utterances.person_id` is updated by resolve, but `argument_participants.person_id` (which also has a nullable `person_id`) is never updated. The participants table remains null, which may cause issues in Phase 3 when the argument header needs to show the speaker roster.
**Why it happens:** The context says this is "Claude's Discretion" — easy to defer and forget.
**How to avoid:** Plan a discrete task to update `argument_participants.person_id` during the resolve step, mapping from raw_speaker_label → person_id for each participant row. It's two extra UPDATE statements using the same alias lookups already being performed.

---

## Code Examples

### Verified Patterns from Codebase

#### Async session usage (pipeline pattern)
```python
# Source: pipeline/db.py + pipeline/commands/ingest.py
async with get_session() as session:
    obj = SomeModel(...)
    session.add(obj)
    await session.flush()   # get obj.id without committing
    # commit happens on clean context manager exit
```

#### SQLAlchemy select with scalar result
```python
# Source: pipeline/commands/parse.py
run: Optional[PipelineRun] = await session.get(PipelineRun, args.run_id)
result = await session.execute(
    select(SomeModel).where(SomeModel.field == value)
)
obj = result.scalar_one_or_none()
```

#### FastAPI router + service + Depends pattern
```python
# Source: api/routers/arguments.py + api/services/arguments.py
@router.get("/{id}", response_model=SomeResponse)
async def get_thing(id: int, db: AsyncSession = Depends(get_db)):
    result = await some_service.get_by_id(db, id)
    if result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return result
```

#### Include new router in main.py
```python
# Source: api/main.py
from api.routers import people as people_router
app.include_router(people_router.router)
```

#### Svelte 5 Runes props pattern (DO NOT use export let)
```svelte
<!-- Source: app/src/lib/components/ChatBubble.svelte -->
<script lang="ts">
    let { utterance } = $props();
</script>
```

#### PipelineRunStatus.NEEDS_REVIEW already exists
```python
# Source: api/models/models.py
class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"   # ← already in the enum, used for D-09
```

#### Hand-written Alembic migration pattern
```python
# Source: alembic/versions/0001_initial_schema.py
# Use op.create_table() not Base.metadata.create_all()
# Use PgENUM(name="type_name", create_type=False) for existing enum types
# Use sa.text("now()") for server_default on DateTime columns
# Include down_revision to chain migrations
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93 | `@app.on_event` deprecated; project already uses lifespan (01-05 decision) |
| `export let prop` in Svelte | `$props()` rune | Svelte 5 | project enforces Runes exclusively (01-01 decision) |
| `Base.metadata.create_all` | Alembic migrations only | Phase 1 | Hard constraint CLAUDE.md; test enforces it |
| `$:` reactive blocks | Derived state via `$derived()` rune | Svelte 5 | Not applicable in Phase 2 (no derived state needed) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLAlchemy `update().where().values()` bulk statement requires `execution_options(synchronize_session=False)` to avoid identity map conflicts | Common Pitfalls #3 / Pattern 5 | Minor — worst case is a warning or stale cache; functional behavior is correct |
| A2 | `KeyboardInterrupt` can be caught inside an async coroutine running directly under `asyncio.run()` on the main thread | Common Pitfalls #4 | Medium — if not catchable, needs alternate interrupt handling strategy (e.g., signal handler in `__main__.py`) |
| A3 | `UtteranceResponse.model_validate(dict)` is required when the service returns mixed Row tuples; `from_attributes=True` alone is insufficient | Common Pitfalls #6 / Pattern 8 | Medium — if wrong, may need to construct a dataclass or NamedTuple for serialization |
| A4 | Obergefell Q1 counsel labels in the parsed transcript match: Mary Bonauto, Douglas Hallward-Driemeier, John Bursch, Joseph Whalen, Donald Verrilli | Seed Data Reference | Medium — if label variants differ (e.g., "MR. VERRILLI" not "GENERAL"), the interactive resolve session will have more unrecognized labels than expected |
| A5 | The 13 Justices listed in the seed table cover all speakers who appear as Justices in the Obergefell Q1 transcript | Seed Data Reference | Low — extra Justice entries in the seed don't cause harm; missing ones just require interactive resolution |
| A6 | `people.full_name` should use natural display order ("Elena Kagan" not "Kagan, Elena") | Seed Data Reference | Low — display format; can be changed without migration |

---

## Open Questions (RESOLVED)

1. **Should `argument_participants.person_id` be updated during resolve?**
   - What we know: `argument_participants` has a nullable `person_id` FK. It was populated at parse time with `raw_speaker_label` and `side` but `person_id=null`. Phase 3 argument header needs the full speaker roster.
   - What's unclear: Whether updating it now (Phase 2) is simpler than a separate Phase 3 migration step.
   - Recommendation: Update it during resolve. Same alias lookups are already being performed; two extra UPDATE statements add minimal complexity and prevent a deferred gotcha in Phase 3.

2. **What is the exact `raw_speaker_label` format in the Obergefell parsed transcript?**
   - What we know: The parse step stores `raw_speaker_label` as extracted from the PDF. The normalization function converts to uppercase + strips colon.
   - What's unclear: Whether labels are already uppercase in the transcript (e.g., "JUSTICE KAGAN") or mixed case (e.g., "Justice Kagan:"). SCOTUS transcripts conventionally use all-caps for speaker labels.
   - Recommendation: Before finalizing seed alias rows, run `SELECT DISTINCT raw_speaker_label FROM utterances WHERE argument_id=1` against the local database and inspect the actual values. This takes 30 seconds and removes all uncertainty.

3. **Should `resolve` operate on a parse run ID or an argument ID?**
   - What we know: CONTEXT.md and ROADMAP.md both say `--run-id <N>` (pipeline_run.id). The resolve step loads the utterances belonging to that parse run.
   - What's unclear: Whether the resolve run should be keyed to the parse run or to the argument. If an argument has multiple parse runs, which one does resolve target?
   - Recommendation: `--run-id` refers to the PARSE `pipeline_run.id`. The resolve step reads utterances WHERE `pipeline_run_id = args.run_id`. This is consistent with how `parse --run-id` refers to an ingest run. It also means you can resolve any specific parse run, which is correct for PIPE-11 (prior runs are not deleted).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | Alembic migration, resolve/seed commands, API tests | Assumed ✓ | 16 (Digital Ocean managed) | Run `alembic upgrade head` before executing plan tasks |
| asyncpg | SQLAlchemy async driver | ✓ (Phase 1 installed) | Current | — |
| Python 3.12 | Pipeline commands | ✓ (Phase 1 installed) | 3.12 | — |
| Node.js / npm | SvelteKit frontend | ✓ (Phase 1 installed) | Current | — |

**Missing dependencies with no fallback:** None — Phase 2 introduces no new dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` or inferred from `pyproject.toml` |
| Quick run command | `pytest pipeline/tests/test_resolve.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-07 | Resolve step updates `utterances.person_id` for alias-matched labels | integration | `pytest pipeline/tests/test_resolve.py::test_resolve_alias_hit -x` | ❌ Wave 0 |
| PIPE-07 | Resolve step prompts operator for unrecognized labels | unit (mocked input) | `pytest pipeline/tests/test_resolve.py::test_resolve_interactive_prompt -x` | ❌ Wave 0 |
| PIPE-08 | `seed-aliases` inserts expected Justice rows and alias variants | integration | `pytest pipeline/tests/test_seed_aliases.py::test_seed_creates_justices -x` | ❌ Wave 0 |
| PIPE-08 | `seed-aliases` is idempotent (re-run does not duplicate rows) | integration | `pytest pipeline/tests/test_seed_aliases.py::test_seed_idempotent -x` | ❌ Wave 0 |
| PIPE-09 | Ctrl+C sets `pipeline_run.status = needs_review` | unit (mocked interrupt) | `pytest pipeline/tests/test_resolve.py::test_resolve_interrupt_sets_needs_review -x` | ❌ Wave 0 |
| PIPE-09 | Re-running resolve after interrupt only prompts unresolved labels | integration | `pytest pipeline/tests/test_resolve.py::test_resolve_resumes_after_interrupt -x` | ❌ Wave 0 |
| API-03 | `GET /people/{id}` returns 200 with name and role | unit (no DB) + integration | `pytest api/tests/test_people.py -x` | ❌ Wave 0 |
| API-03 | `GET /people/99999` returns 404 | unit (no DB) | `pytest api/tests/test_people.py::test_get_person_404 -x` | ❌ Wave 0 |
| PIPE-07 | `normalize_label()` function handles colon, case, whitespace correctly | unit | `pytest pipeline/tests/test_resolve.py::test_normalize_label -x` | ❌ Wave 0 |
| D-02 | Label normalization: `"Justice Kagan:"` → `"JUSTICE KAGAN"` | unit | (same as above) | ❌ Wave 0 |
| D-10 | `GET /arguments/{id}/utterances` embeds `speaker_name` and `speaker_role` post-resolve | integration | `pytest api/tests/test_arguments.py::test_utterances_have_speaker_name_after_resolve -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest pipeline/tests/test_resolve.py -x -q` (or relevant test file for that task)
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pipeline/tests/test_resolve.py` — covers PIPE-07, PIPE-09, normalize_label unit tests
- [ ] `pipeline/tests/test_seed_aliases.py` — covers PIPE-08 seeding and idempotency
- [ ] `api/tests/test_people.py` — covers API-03 (GET /people/{id})
- [ ] Update `tests/test_schema.py` EXPECTED_TABLES to include `"speaker_alias"` after migration

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — pipeline is operator-only CLI; API is read-only public |
| V3 Session Management | no | No sessions in read-only API |
| V4 Access Control | no | No user roles; pipeline is offline |
| V5 Input Validation | yes | FastAPI path param `person_id: int` provides type-level injection prevention (same pattern as `argument_id: int` in existing endpoint) |
| V6 Cryptography | no | No encryption needed for speaker metadata |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `person_id` path param | Tampering | FastAPI `int` type annotation rejects non-integer at 422 before query layer — already established pattern from arguments router |
| Operator seeds malicious role names via interactive prompt | Tampering | Pipeline is local CLI; no external attack surface. Role name saved to DB via parameterized ORM insert (SQLAlchemy) — not raw SQL |

---

## Sources

### Primary (HIGH confidence)
- `api/models/models.py` — ORM model patterns, existing enum definitions
- `alembic/versions/0001_initial_schema.py` — migration style, PgENUM usage, hand-written pattern
- `pipeline/commands/ingest.py` — `get_session()`, argparse, async patterns
- `pipeline/commands/parse.py` — state machine, `PipelineRunStatus` transitions, error handling
- `pipeline/db.py` — session factory, `statement_cache_size=0` placement
- `api/routers/arguments.py` — router pattern
- `api/services/arguments.py` — service query pattern
- `api/schemas/utterance.py` — schema extension pattern
- `app/src/lib/components/ChatBubble.svelte` — `$props()` Runes pattern, existing speaker label render
- `.planning/phases/02-speaker-resolution/02-CONTEXT.md` — all locked decisions D-01 through D-11

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — PIPE-07, PIPE-08, PIPE-09, API-03 requirement text
- `.planning/ROADMAP.md` — Phase 2 success criteria

### Tertiary (LOW confidence — assumptions tagged above)
- SQLAlchemy 2.0 bulk update behavior with async sessions [ASSUMED — A1, A3]
- asyncio KeyboardInterrupt behavior in coroutines [ASSUMED — A2]
- Obergefell transcript speaker label exact format [ASSUMED — A4, A5]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all patterns verified against existing Phase 1 codebase; no new libraries
- Architecture: HIGH — all patterns are direct extensions of Phase 1 patterns already in use
- Pitfalls: MEDIUM/HIGH — most are verified against Phase 1 code; asyncio interrupt behavior is ASSUMED

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable domain — no fast-moving dependencies)
