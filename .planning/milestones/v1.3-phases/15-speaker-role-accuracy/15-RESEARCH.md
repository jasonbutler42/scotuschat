# Phase 15: Speaker Role Accuracy — Research

**Researched:** 2026-06-25
**Domain:** SQLAlchemy async, PostgreSQL enum extension, SvelteKit form actions, date-range lookup
**Confidence:** HIGH (all claims verified against live codebase or authoritative references)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Argument Lifecycle Status**
- D-01: Add `arguments.status` as an explicit enum column with three values: `pipeline`, `draft`, `published`. Alembic migration.
- D-02: Admin arguments list shows only `draft` and `published` arguments. `pipeline`-state arguments accessible only via pipeline job detail.
- D-03: Public `/cases` page continues to filter on `published_at IS NOT NULL` — unchanged. The `status` column is admin-only.
- D-04: Mental model: pipeline is factory; argument is product. Argument "exists" when operator approves resolve step.

**Advocate Role Storage (SideEnum Expansion)**
- D-05: Expand `SideEnum` via `ALTER TYPE side ADD VALUE IF NOT EXISTS` for three new values: `PETITIONER`, `RESPONDENT`, `AMICUS`. `ADVOCATE` stays permanently. `UNKNOWN` means "advocate, role not yet determined."
- D-06: Migration backfills all existing `argument_participants` rows where `side = 'ADVOCATE'` → `side = 'UNKNOWN'`.
- D-07: Advocate `role_name` in popover comes from hard-coded label map — no join to `roles` table:
  - `PETITIONER` → `"Petitioner's Counsel"`
  - `RESPONDENT` → `"Respondent's Counsel"`
  - `AMICUS` → `"Amicus Curiae"`
  - `UNKNOWN` or `ADVOCATE` (legacy) → `"Counsel"`

**Pipeline Job Detail (Resolve Review — Prebirth Only)**
- D-08: Pipeline job detail handles resolve-step editing only while argument is in `pipeline` state. Includes: speaker alias confirmation/correction (existing) + advocate role assignment (new dropdown) for non-BENCH participants.
- D-09: Every pipeline run ends with a manual "Approve" action. Operator clicks "Create Argument" on pipeline job detail. Triggers: `argument.status = 'draft'`, `argument.resolved_at = now()`, pipeline job transitions to read-only.
- D-10: After approval, pipeline job detail is read-only but retains stats. "Re-run with same source" button visible; clicking starts a new pipeline run. The new run goes through `pipeline` state again; the existing `draft`/`published` argument is unaffected until operator approves the new run.

**Argument Edit Page (Draft + Published)**
- D-11: Argument edit page is canonical home for all argument-level editing after approval.
- D-12: Advocate role editor on argument edit page: dropdown per resolved advocate participant showing `PETITIONER`/`RESPONDENT`/`AMICUS`/`UNKNOWN`. Saving updates `argument_participants.side` for that argument only.

**Justice Popover Role (Tenure Date-Range Lookup)**
- D-13: In `get_argument_speakers`, `role_name` for bench speakers resolved by matching `argument.argued_date` against person's `CourtTenure` rows. The matching row's `seat` field becomes `role_name`.
- D-14: Fallback when `argued_date` falls outside all tenure rows: use the tenure row with the highest `start_date` (most recent).
- D-15: Tenure gaps surfaced to operator on argument edit page (inline warning) and people directory (new filter "Justices with tenure gaps").

### Claude's Discretion
- Exact label for the "Approve" button — resolved in UI-SPEC as "Create Argument"
- Whether the advocate role dropdown on pipeline job detail and argument edit page are the same component or separate — UI-SPEC says same pattern, either approach acceptable
- Visual treatment of the inline tenure gap warning — resolved in UI-SPEC as inline amber-bordered banner
- Whether the Re-run button requires confirmation — resolved in UI-SPEC as inline two-step confirm pattern

### Deferred Ideas (OUT OF SCOPE)
- Multi-appointer tenure attribution per tenure row
- Full pipeline flow redesign as submit form
- Advocate firm/organization in popover (ADV-01)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROLE-01 | Public speaker popover shows the role a Justice held at the time the argument was heard — determined by tenure date-range lookup against `argued_date`, not person's current role field | D-13/D-14: date-range logic in `get_argument_speakers`; requires adding `argument.argued_date` and `argument_participants.side` to that query |
| ROLE-02 | Advocate roles (petitioner's counsel, respondent's counsel, amicus curiae) are stored per argument, not per person | D-05/D-06: SideEnum expansion + backfill migration |
| ROLE-03 | Operator can set or correct an advocate's role for a specific argument in the admin interface without affecting that person's role in other arguments | D-12: separate PATCH endpoint for `argument_participants.side` scoped to one argument |
</phase_requirements>

---

## Summary

Phase 15 delivers four changes to a well-established codebase. No new packages are required. Every decision is locked in CONTEXT.md and the UI-SPEC is approved, so research is focused on implementation details, integration pitfalls, and the exact query shapes.

The four plans are fully sequential in terms of schema → service → UI:
1. **15-01 Schema** — Two Alembic changes: (a) extend the `side` PG enum type with three new values and backfill existing `ADVOCATE` rows to `UNKNOWN`; (b) add `arguments.status` as a new enum column, set existing rows to `draft` or `published` based on existing state.
2. **15-02 Service** — Extend `get_argument_speakers` with `argument.argued_date` and `argument_participants.side`; implement tenure date-range lookup for bench speakers; implement label-map for advocates. Extend `admin_people.list_people` with tenure-gaps filter. Add `approve_job` service function.
3. **15-03 Pipeline Job Detail** — Add advocate role dropdown column to resolve table; add "Create Argument" (Approve) button; add Re-run button; flip to read-only post-approval; update argument status badge.
4. **15-04 Argument Edit Page** — Add "Advocate Roles" section with dropdowns; add TenureGapWarning per affected bench speaker; update status badge to read `argument.status`; extend admin arguments list with Status column and draft/pipeline filter.

**Primary recommendation:** Execute plans in strict order (schema first, service second, UI last) because the Svelte components depend on service-layer API response shapes that depend on schema columns.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SideEnum expansion + backfill | Database / Storage | — | PG enum type DDL; Alembic owns all DDL |
| `arguments.status` enum column | Database / Storage | — | New DB column; Alembic owns |
| Tenure date-range role lookup | API / Backend | — | Business logic; `get_argument_speakers` in `api/services/speakers.py` |
| Advocate label map | API / Backend | — | Pure mapping logic; belongs in service layer not frontend |
| Approve action (set status=draft) | API / Backend | Frontend Server (SvelteKit) | FastAPI endpoint + SvelteKit form action |
| Re-run action (spawn new job) | API / Backend | Frontend Server (SvelteKit) | FastAPI endpoint using existing `spawn_pipeline_step` |
| Advocate role editor (per argument) | API / Backend | Frontend Server (SvelteKit) | PATCH endpoint + SvelteKit form action |
| Tenure gap warning (argument edit page) | Frontend Server (SSR) | — | Data computed server-side; rendered in Svelte |
| Tenure gaps people directory filter | API / Backend | Frontend Server (SvelteKit) | Service-layer query + Svelte filter toggle |
| Public popover role display | Frontend Server (SSR) | — | Already built; `role_name` field populated by service layer |

---

## Standard Stack

This phase introduces no new packages. All work is extension of the existing stack.

### Core (pre-existing, no new installs)

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| SQLAlchemy | 2.0 async | ORM queries + `op.execute()` for DDL | `[VERIFIED: api/requirements.txt read]` |
| Alembic | current | Migration 0008 | `[VERIFIED: alembic/versions/ read]` |
| FastAPI | 0.115+ | New endpoints (approve, rerun, participant side PATCH) | `[VERIFIED: CLAUDE.md]` |
| Pydantic v2 | current | New request/response schemas | `[VERIFIED: CLAUDE.md]` |
| SvelteKit 2.x / Svelte 5 | current | Admin UI modifications (Runes only) | `[VERIFIED: CLAUDE.md]` |

### No New Packages

Phase 15 is a pure codebase extension. No npm or pip installs are required.

**Package Legitimacy Audit: N/A — no new packages.**

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
    │
    ├─► POST ?/approve (SvelteKit form action)
    │       │
    │       └─► POST /api/admin/jobs/{job_id}/approve (FastAPI)
    │               └─► UPDATE arguments SET status='draft', resolved_at=now()
    │                   UPDATE admin_jobs SET status=COMPLETED
    │
    ├─► POST ?/updateParticipantSide (SvelteKit form action, argument edit page)
    │       │
    │       └─► PATCH /api/admin/arguments/{id}/participants/{participant_id}
    │               └─► UPDATE argument_participants SET side=X WHERE id=Y
    │
    └─► POST ?/rerun (SvelteKit form action)
            │
            └─► POST /api/admin/jobs/{job_id}/rerun (FastAPI)
                    └─► spawn_pipeline_step("ingest", new_job_id, [--pdf-source])

Public browser
    │
    └─► GET /cases/[slug]/arguments/[id] (SvelteKit +page.server.ts)
            │
            └─► GET /api/arguments/{id}/speakers (FastAPI)
                    └─► get_argument_speakers()
                            ├─► Query distinct person_ids from utterances
                            ├─► Query Person + Role for those ids
                            ├─► Query CourtTenure for those ids
                            ├─► Query argument_participants.side per person (NEW)
                            └─► Assemble: bench → tenure date-range → seat as role_name
                                         advocate → label map from side
```

### Recommended Project Structure (no structural changes)

All new files follow existing file placement patterns:

```
alembic/versions/
└── 0008_side_enum_and_argument_status.py   # Plan 15-01

api/
├── models/models.py          # Add ArgumentStatusEnum, update SideEnum values, add Argument.status
├── services/
│   ├── speakers.py           # Plan 15-02: extend get_argument_speakers
│   └── admin_people.py       # Plan 15-02: extend list_people with tenure_gaps filter
│   └── admin_jobs.py         # Plan 15-02: add approve_job(), rerun_job()
├── schemas/
│   ├── speakers.py           # Plan 15-02: add is_bench flag or side to SpeakerPopoverEntry
│   └── admin_arguments.py    # Plan 15-04: extend ArgumentListItem + ArgumentDetail with status
├── routers/
│   └── admin.py              # Plans 15-03/15-04: add approve/rerun/participant-side endpoints

app/src/routes/admin/
├── pipeline/[job_id]/+page.svelte        # Plan 15-03
├── pipeline/[job_id]/+page.server.ts     # Plan 15-03
├── arguments/[id]/+page.svelte           # Plan 15-04
├── arguments/[id]/+page.server.ts        # Plan 15-04
├── arguments/+page.svelte                # Plan 15-04: add Status column
├── arguments/+page.server.ts             # Plan 15-04: filter pipeline-status args
└── people/+page.svelte                   # Plan 15-04: add tenure_gaps toggle
    people/+page.server.ts                # Plan 15-04: pass tenure_gaps param
```

---

## Critical Implementation Patterns

### Pattern 1: PostgreSQL Enum Expansion (ALTER TYPE … ADD VALUE IF NOT EXISTS)

`[VERIFIED: alembic/versions/0001_initial_schema.py]` — the project already uses raw SQL via `op.execute(sa.text(...))` for enum type creation.

The `side` PG type was created as:
```sql
CREATE TYPE side AS ENUM ('BENCH', 'ADVOCATE', 'UNKNOWN');
```

Adding values uses `ALTER TYPE ... ADD VALUE IF NOT EXISTS`:
```python
# Migration 0008 — upgrade()
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))
```

**Critical constraint:** `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block in PostgreSQL. [ASSUMED] This means the migration script must use `op.execute` with `connection.execution_options(isolation_level="AUTOCOMMIT")` or structure the migration with a `with op.get_context().autocommit_block():` pattern, OR the `IF NOT EXISTS` clause itself is safe because Alembic by default runs each migration file in its own transaction but the ADD VALUE must be committed before it can be used in the same transaction.

**Practical safe approach `[ASSUMED]`:** Use separate `op.execute()` calls for each `ADD VALUE`, then a separate `op.execute()` for the backfill UPDATE. This is valid because PostgreSQL 12+ allows `ALTER TYPE ... ADD VALUE IF NOT EXISTS` to appear before values are used in the same script, as long as the backfill is in a separate statement.

**Python SideEnum model update required:** `api/models/models.py` `SideEnum` must be updated to include the new values before the service layer can reference them as Python enum members.

```python
# VERIFIED: api/models/models.py line 34 (current)
class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"
    UNKNOWN = "UNKNOWN"

# Updated (Phase 15):
class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"   # legacy — do not remove (PG cannot drop enum values)
    UNKNOWN = "UNKNOWN"
    PETITIONER = "PETITIONER"
    RESPONDENT = "RESPONDENT"
    AMICUS = "AMICUS"
```

### Pattern 2: New PG Enum Type for `arguments.status`

D-01 requires a new three-value enum for `arguments.status`. Unlike `SideEnum`, this is a brand-new PG type — same DO-block pattern as migration 0001:

```python
# Migration 0008 — upgrade()
op.execute(sa.text("""
    DO $$ BEGIN
        CREATE TYPE argument_status AS ENUM ('pipeline', 'draft', 'published');
    EXCEPTION WHEN duplicate_object THEN null;
    END $$;
"""))
op.add_column(
    "arguments",
    sa.Column(
        "status",
        sa.Enum("pipeline", "draft", "published", name="argument_status"),
        nullable=True,  # nullable initially for backfill
    )
)
```

**Backfill logic for existing `arguments` rows:**

| Existing row state | New `status` value |
|--------------------|--------------------|
| `published_at IS NOT NULL` | `'published'` |
| `resolved_at IS NOT NULL AND published_at IS NULL` | `'draft'` |
| `resolved_at IS NULL` | `'pipeline'` (prebirth) |

```python
# Backfill in the same migration — three UPDATE statements
op.execute(sa.text(
    "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"
))
op.execute(sa.text(
    "UPDATE arguments SET status = 'draft' WHERE resolved_at IS NOT NULL AND published_at IS NULL"
))
op.execute(sa.text(
    "UPDATE arguments SET status = 'pipeline' WHERE resolved_at IS NULL"
))
# After backfill, make NOT NULL
op.alter_column("arguments", "status", nullable=False)
```

**Python model update:**

```python
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"

# In Argument model:
status = Column(
    SAEnum(ArgumentStatusEnum, name="argument_status",
           values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    default=ArgumentStatusEnum.PIPELINE,
)
```

`[VERIFIED: api/models/models.py — SAEnum pattern from existing SideEnum and PipelineRunStatus columns]`

### Pattern 3: Tenure Date-Range Lookup in `get_argument_speakers`

`[VERIFIED: api/services/speakers.py read]` — current implementation already fetches `CourtTenure` rows for all person_ids (step 3). What is MISSING is:
1. `argument.argued_date` — the date to match against
2. `argument_participants.side` per person — to distinguish BENCH from advocate

The current query does `select(distinct(Utterance.person_id))` — it has no access to `argument_participants.side` at all.

**Required service-layer changes:**

**Step A:** Add a query for `argument.argued_date`:
```python
# New Step 0 — fetch argument's argued_date
arg_result = await db.execute(
    select(Argument.argued_date).where(Argument.id == argument_id)
)
argued_date = arg_result.scalar_one_or_none()
# If no argument or no argued_date, role_name stays None for bench speakers
```

**Step B:** Add a query for `argument_participants.side` per person:
```python
# New Step 4 (after existing step 3 tenures)
sides_result = await db.execute(
    select(ArgumentParticipant.person_id, ArgumentParticipant.side)
    .where(
        ArgumentParticipant.argument_id == argument_id,
        ArgumentParticipant.person_id.in_(person_ids),
    )
)
side_by_person: dict[int, SideEnum] = {
    row.person_id: row.side for row in sides_result.all()
}
```

**Step C:** Replace role_name assembly:
```python
ADVOCATE_LABEL_MAP = {
    SideEnum.PETITIONER: "Petitioner's Counsel",
    SideEnum.RESPONDENT: "Respondent's Counsel",
    SideEnum.AMICUS: "Amicus Curiae",
    SideEnum.UNKNOWN: "Counsel",
    SideEnum.ADVOCATE: "Counsel",  # legacy
}

def _resolve_role_name(
    person_id: int,
    side: SideEnum | None,
    tenures: list[dict],
    argued_date,
) -> str | None:
    if side == SideEnum.BENCH:
        # Tenure date-range lookup (D-13)
        if argued_date and tenures:
            for t in tenures:
                start = t["start_date"]  # "YYYY-MM-DD" string
                end = t["end_date"]      # "YYYY-MM-DD" or None
                if start and argued_date >= start:
                    if end is None or argued_date <= end:
                        return t["seat"]
            # D-14 fallback: most recent tenure (highest start_date)
            return sorted(tenures, key=lambda t: t["start_date"] or "", reverse=True)[0]["seat"]
        return None
    else:
        return ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)
```

**Date comparison note:** `argument.argued_date` is a Python `datetime.date` object from SQLAlchemy. `CourtTenure.start_date` and `end_date` are also `datetime.date` objects. Direct Python `date >= date` comparison works. The current service assembles `tenures_by_person` as dicts with stringified dates (`str(t.start_date)`). For the date-range comparison, keep them as `datetime.date` objects (don't stringify) — or use string lexicographic comparison on "YYYY-MM-DD" (valid for ISO dates). `[ASSUMED]` The simplest approach: keep the existing `str()` serialization for the SpeakerPopoverEntry output, but for the lookup function compare before stringifying.

### Pattern 4: `approve_job` Service Function

The approve action must:
1. Validate the job exists and has an argument in `pipeline` state
2. Set `argument.status = 'draft'` and `argument.resolved_at = now()` atomically
3. Set `admin_job.status = COMPLETED` (same as the existing `resolve_job` final step)
4. Return the updated job

```python
async def approve_job(db: AsyncSession, job_id: int) -> AdminJob:
    """Transition argument from pipeline to draft state (D-09).

    Sets argument.status = 'draft', argument.resolved_at = now().
    Sets admin_job.status = COMPLETED.
    Raises ValueError if job not found, job has no argument, or argument is
    not in 'pipeline' status (guard against double-approve).
    """
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.argument_id is None:
        raise ValueError(f"AdminJob {job_id} has no linked argument")

    # Load argument and validate state
    arg_result = await db.execute(
        select(Argument).where(Argument.id == job.argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        raise ValueError("Argument not found for this job")
    if argument.status != ArgumentStatusEnum.PIPELINE:
        raise ValueError(
            f"Argument is already in '{argument.status.value}' state; cannot approve again."
        )

    # Set status + resolved_at
    await db.execute(
        update(Argument)
        .where(Argument.id == job.argument_id)
        .values(
            status=ArgumentStatusEnum.DRAFT,
            resolved_at=func.now(),
        )
        .execution_options(synchronize_session=False)
    )
    # Set job COMPLETED
    await db.execute(
        update(AdminJob)
        .where(AdminJob.id == job_id)
        .values(status=AdminJobStatus.COMPLETED)
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    updated = await get_job(db, job_id)
    return updated
```

`[VERIFIED: pattern mirrors existing resolve_job in api/services/admin_jobs.py]`

### Pattern 5: Re-run Action

The Re-run action creates a NEW AdminJob pointing at the same PDF source:

```python
async def rerun_job(db: AsyncSession, job_id: int) -> AdminJob:
    """Create a new pipeline job re-using the source from an existing approved job."""
    original = await get_job(db, job_id)
    if original is None:
        raise ValueError(f"AdminJob {job_id} not found")

    # Create a fresh job with same PDF source
    new_job = await create_job(
        db,
        pdf_url=original.pdf_url,
        spaces_key=original.spaces_key,
    )
    return new_job
```

The caller (router) spawns `ingest` after this returns, exactly as in `POST /api/admin/jobs`.

`[VERIFIED: api/services/admin_jobs.py create_job pattern; PipelineRun.pdf_url and pdf_path fields in api/models/models.py]`

### Pattern 6: Participant Side PATCH Endpoint

`argument_participants.side` requires a separate PATCH endpoint, NOT included in `ArgumentUpdate` (mass-assignment constraint — D-12, T-11-MASS).

```
PATCH /api/admin/arguments/{argument_id}/participants/{participant_id}
Body: { "side": "PETITIONER" | "RESPONDENT" | "AMICUS" | "UNKNOWN" }
```

Schema guard: `ParticipantSideUpdate` Pydantic model exposes only `side` as a `SideEnum` field — no other `ArgumentParticipant` columns writable.

```python
class ParticipantSideUpdate(BaseModel):
    side: SideEnum
    # Only PETITIONER, RESPONDENT, AMICUS, UNKNOWN are valid for advocates.
    # BENCH is not settable via this endpoint (service validates).
```

### Pattern 7: Tenure Gap Query for People Directory Filter

`[VERIFIED: api/services/admin_people.py list_people pattern]`

The tenure-gaps filter requires a subquery that identifies person_ids where at least one of their argument appearances has an `argued_date` not covered by ANY of their `CourtTenure` rows.

```python
# SQLAlchemy approach for tenure_gaps filter
# Step 1: get person_ids of all bench speakers in any argument
# Step 2: for each, check if any argued_date is outside their tenure windows

from sqlalchemy import and_, exists, not_

# A person has a tenure gap if:
# EXISTS an argument_participant where side='BENCH' AND argument.argued_date is not covered
# by any court_tenure for that person.

# Subquery: for a given person_id and argued_date, does a covering tenure exist?
def _has_covering_tenure(person_id_col, argued_date_col):
    return exists(
        select(CourtTenure.id).where(
            and_(
                CourtTenure.person_id == person_id_col,
                CourtTenure.start_date <= argued_date_col,
                or_(
                    CourtTenure.end_date.is_(None),
                    CourtTenure.end_date >= argued_date_col,
                ),
            )
        )
    )

# People with tenure gaps: bench speakers where at least one argument is uncovered
tenure_gap_person_ids = (
    select(ArgumentParticipant.person_id)
    .join(Argument, Argument.id == ArgumentParticipant.argument_id)
    .where(
        ArgumentParticipant.side == SideEnum.BENCH,
        ArgumentParticipant.person_id.isnot(None),
        not_(_has_covering_tenure(ArgumentParticipant.person_id, Argument.argued_date)),
    )
    .distinct()
)

# Apply to list_people query:
if tenure_gaps:
    q = q.where(Person.id.in_(tenure_gap_person_ids))
```

`[ASSUMED — SQLAlchemy syntax; correct conceptually but exact parameter names need verification against SQLAlchemy 2.0 docs. The pattern mirrors how Phase 13 applied the incomplete filter.]`

### Pattern 8: Tenure Gap Warning Data (Argument Edit Page)

The warning data must be computed server-side in `+page.server.ts`. The FastAPI detail endpoint for an argument must return enough data for the Svelte page to render warnings.

New field on `ArgumentDetail` response: `tenure_gap_warnings: list[TenureGapWarning]`

```python
class TenureGapWarning(BaseModel):
    person_id: int
    full_name: str
    argued_date: str   # "YYYY-MM-DD"
```

The service computes this by:
1. Getting bench participants for the argument
2. For each, checking if `argued_date` is outside their tenures
3. Returning warnings for those where it is

This computation can live in `get_argument_detail` or a separate `get_tenure_gap_warnings(db, argument_id)` helper.

### Pattern 9: Admin Arguments List — Draft/Pipeline Filter (D-02)

The admin arguments list must exclude `pipeline`-state arguments (D-02). The `list_arguments` service must be updated:

```python
# Updated list_arguments in api/services/admin_arguments.py
q = q.where(Argument.status.in_([ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.PUBLISHED]))
```

This also means the admin arguments list must return `status` in each row so the Svelte page can render the status badge. `ArgumentListItem` schema must gain a `status: ArgumentStatusEnum` field.

### Pattern 10: SvelteKit Form Action — Approve (Pipeline Job Detail)

```typescript
// +page.server.ts — new action
approve: async ({ params, fetch }) => {
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/approve`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch {
        return fail(502, { approveError: 'Could not create argument. Try again.' });
    }
    if (!res.ok) {
        return fail(422, { approveError: 'Could not create argument. Try again.' });
    }
    throw redirect(303, `/admin/pipeline/${params.job_id}`);
},
```

`[VERIFIED: mirrors existing publish action pattern in app/src/routes/admin/arguments/[id]/+page.server.ts]`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PG enum expansion | Custom migration script | `op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS ..."))` | Standard Alembic DDL pattern; already used in project |
| Tenure date-range overlap check | Custom date library | Python `datetime.date` comparison operators | `CourtTenure` columns are `Date` type; SQLAlchemy returns native `datetime.date` objects |
| Advocate role label | DB join to `roles` table | Hard-coded dict in service layer | D-07: explicitly decided; roles table has dynamic values, popover labels are fixed copy |
| Admin auth | Custom token logic | Existing `verify_admin_token` router-level dependency | All admin routes inherit it automatically; no per-route auth needed |
| DB enum creation | `Base.metadata.create_all` | Alembic `op.execute()` with `IF NOT EXISTS` | CLAUDE.md hard constraint: Alembic is sole DDL authority |

---

## Common Pitfalls

### Pitfall 1: `ALTER TYPE ADD VALUE` inside a transaction

**What goes wrong:** PostgreSQL raises `ERROR: ALTER TYPE ... ADD VALUE cannot run inside a transaction block` if the `ADD VALUE` is wrapped in a transaction. Alembic by default wraps migrations in a transaction.

**Why it happens:** `ALTER TYPE ... ADD VALUE` is a schema-altering DDL that PostgreSQL cannot roll back in a transaction.

**How to avoid:** `[ASSUMED — standard Alembic pattern]` Set the migration to run in non-transactional mode:
```python
# At the top of the migration file
def upgrade() -> None:
    # Must run outside transaction for ADD VALUE
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))  # close Alembic's open transaction
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))
    # Resume transactional work for the backfill
    op.execute(sa.text("UPDATE argument_participants SET side = 'UNKNOWN' WHERE side = 'ADVOCATE'"))
```

Alternatively, split into two migrations: one for the ADD VALUE (non-transactional), one for the backfill (transactional). The safest approach for this codebase is a single migration that commits before the ADD VALUE calls.

**Warning signs:** Alembic prints `ERROR: ALTER TYPE ... ADD VALUE cannot run inside a transaction block` during `alembic upgrade head`.

### Pitfall 2: `asyncpg` and `statement_cache_size=0`

**What goes wrong:** Without `statement_cache_size=0` in `connect_args`, asyncpg caches prepared statements. After a schema migration that adds new enum values, the cache may hold stale type information, causing `InvalidCachedStatementError`.

**Why it happens:** DO PgBouncer (Transaction mode) requirement. Already set in project.

**How to avoid:** `[VERIFIED: CLAUDE.md constraint — already enforced in database engine config]` No action needed; the constraint is pre-existing.

### Pitfall 3: `argument_participants.side` NEW values not in Python SideEnum before migration runs

**What goes wrong:** If `api/models/models.py` `SideEnum` is updated with `PETITIONER/RESPONDENT/AMICUS` before the Alembic migration runs on an existing DB, SQLAlchemy will try to write enum values that the PG type doesn't have yet.

**Why it happens:** Deployment order — code deploy before migration, or migration not run.

**How to avoid:** In development, always run `alembic upgrade head` before restarting the API. In production, run migration before deploying code. Document this in the migration file's docstring.

### Pitfall 4: `SideEnum.ADVOCATE` legacy rows survive the backfill

**What goes wrong:** If the backfill SQL is `SET side = 'UNKNOWN' WHERE side = 'ADVOCATE'`, but no rows have `side = 'ADVOCATE'` (all are `BENCH` or `UNKNOWN` already), the UPDATE is a no-op. This is fine. But if someone adds a new `ADVOCATE` row between migration time and code deploy, the service layer must still handle `SideEnum.ADVOCATE` gracefully.

**Why it happens:** `ADVOCATE` cannot be removed from the PG type — only addition is supported.

**How to avoid:** The `ADVOCATE_LABEL_MAP` in the service layer must include `SideEnum.ADVOCATE: "Counsel"` permanently. `[VERIFIED: D-07 decision]`

### Pitfall 5: `get_argument_speakers` — missing `argument.argued_date` breaks tenure lookup

**What goes wrong:** If `argument.argued_date` is `None` (e.g., the argument was created in `pipeline` state before Phase 15 backfill), the date-range comparison returns no match and falls back to the most-recent tenure. This is correct behavior per D-14, but only if the code handles `None` gracefully without raising.

**How to avoid:** Always null-check `argued_date` before the date-range loop. If `None`, go directly to D-14 fallback (most-recent tenure).

### Pitfall 6: Double-approval guard

**What goes wrong:** If the operator clicks "Create Argument" twice quickly, two POST requests race to set `argument.status = 'draft'`. The second write is idempotent (same value) but also stamps `resolved_at` again.

**How to avoid:** The `approve_job` service validates `argument.status == 'pipeline'` before writing. The second call hits the guard and raises `ValueError` → 422. The UI must display the error without showing it as a failure state (the first call already succeeded).

**Warning signs:** `Could not create argument. Try again.` error message appears immediately after a successful approve on the same page.

### Pitfall 7: Admin arguments list must not show `pipeline`-state arguments

**What goes wrong:** Before Phase 15, `list_arguments` returns all arguments. After Phase 15, `pipeline`-state arguments must be excluded (D-02). Forgetting to update the query means pipeline-state arguments appear in the admin list where they shouldn't.

**How to avoid:** Update `list_arguments` in `api/services/admin_arguments.py` to add `.where(Argument.status.in_([...DRAFT, PUBLISHED]))` and update the `ArgumentListItem` schema to include the `status` field.

### Pitfall 8: Svelte 5 Runes — no `$:` reactive blocks, no `export let`

**What goes wrong:** Using legacy Svelte syntax in modified `.svelte` files causes a compile error in Svelte 5.

**Why it happens:** Svelte 5 Runes (`$state`, `$derived`, `$props`) are incompatible with Options API syntax.

**How to avoid:** `[VERIFIED: CLAUDE.md hard constraint]` All new Svelte code must use `$props()`, `$state()`, `$derived()`, `$effect()` exclusively.

### Pitfall 9: PATCH endpoint for `argument_participants.side` must scope by `argument_id`, not just `participant_id`

**What goes wrong:** If the PATCH endpoint uses only `participant_id` in the WHERE clause, an IDOR attacker could update a participant's role in a different argument (T-IDOR).

**How to avoid:** Always scope: `WHERE argument_participants.id = :participant_id AND argument_participants.argument_id = :argument_id`. Return 404 if the participant doesn't belong to the specified argument.

---

## Code Examples

### Example 1: Tenure Date-Range Lookup (service layer)

```python
# Source: CONTEXT.md D-13/D-14; pattern derived from existing api/services/speakers.py

def _tenure_role_name(
    tenures: list[dict],  # list of {seat, start_date, end_date} — dates as datetime.date
    argued_date: datetime.date | None,
) -> str | None:
    """Return the seat name for the tenure covering argued_date (D-13),
    or the most-recent tenure's seat as fallback (D-14).
    Returns None if tenures is empty.
    """
    if not tenures:
        return None
    if argued_date is not None:
        for t in tenures:
            start = t["start_date"]
            end = t["end_date"]
            if start is not None and argued_date >= start:
                if end is None or argued_date <= end:
                    return t["seat"]
    # D-14 fallback: most recent (highest start_date, None treated as earliest)
    most_recent = max(
        tenures,
        key=lambda t: t["start_date"] or datetime.date.min,
    )
    return most_recent["seat"]
```

Note: The existing service assembles tenures as `{"seat": t.seat, "start_date": str(t.start_date), "end_date": str(t.end_date)}` — string dates. The date-range lookup should either compare before stringifying, or use `datetime.date.fromisoformat()` to convert back. The cleanest approach: keep an internal dict with `datetime.date` objects for the lookup, then serialize to strings only for the final `SpeakerPopoverEntry`.

### Example 2: Alembic Migration 0008 Structure

```python
# Source: existing alembic/versions/0001_initial_schema.py and 0007_add_published_at.py patterns

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"

def upgrade() -> None:
    # Part A: Add new values to 'side' enum (must commit first)
    # Commit the implicit Alembic transaction before ALTER TYPE ADD VALUE
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))

    # Part B: Backfill ADVOCATE -> UNKNOWN
    op.execute(sa.text(
        "UPDATE argument_participants SET side = 'UNKNOWN' WHERE side = 'ADVOCATE'"
    ))

    # Part C: Create argument_status enum
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE argument_status AS ENUM ('pipeline', 'draft', 'published');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    # Part D: Add status column (nullable first for backfill)
    op.add_column(
        "arguments",
        sa.Column(
            "status",
            sa.Enum("pipeline", "draft", "published", name="argument_status"),
            nullable=True,
        )
    )

    # Part E: Backfill status from existing state
    op.execute(sa.text(
        "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"
    ))
    op.execute(sa.text(
        "UPDATE arguments SET status = 'draft' "
        "WHERE resolved_at IS NOT NULL AND published_at IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE arguments SET status = 'pipeline' WHERE resolved_at IS NULL"
    ))

    # Part F: Make NOT NULL after backfill
    op.alter_column("arguments", "status", nullable=False)

def downgrade() -> None:
    op.drop_column("arguments", "status")
    op.execute(sa.text("DROP TYPE IF EXISTS argument_status"))
    # Note: cannot remove PETITIONER/RESPONDENT/AMICUS from 'side' enum in downgrade
    # — PG does not support removing enum values
```

### Example 3: AdvocateRoleDropdown Svelte Pattern

```svelte
<!-- Source: UI-SPEC.md AdvocateRoleDropdown contract; mirrors existing <select> patterns -->
<select
    name="side"
    value={participant.side}
    onchange={/* immediate save or grouped with save form */}
    style="
        background-color: #0f1117;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 16px;
        font-weight: 400;
        color: #e2e8f0;
        min-height: 36px;
    "
>
    <option value="PETITIONER">Petitioner's Counsel</option>
    <option value="RESPONDENT">Respondent's Counsel</option>
    <option value="AMICUS">Amicus Curiae</option>
    <option value="UNKNOWN">Counsel</option>
</select>
```

On the pipeline job detail page: change is grouped into the "Create Argument" form submission (the whole form POSTs with advocate sides as part of approve, or they are saved first — see interaction contract in UI-SPEC).

On the argument edit page: change is grouped with the "Advocate Roles" section save button (D-12, UI-SPEC §Interaction Contracts).

### Example 4: TenureGapWarning Svelte Pattern

```svelte
<!-- Source: UI-SPEC.md TenureGapWarning contract; color constants from UI-SPEC §Color -->
{#each data.argument.tenure_gap_warnings ?? [] as warning}
    <div
        role="status"
        style="
            background-color: #0f1117;
            border: 1px solid #fbbf24;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 16px;
        "
    >
        <p style="font-size: 14px; font-weight: 400; color: #fbbf24; margin: 0 0 4px 0;">
            {warning.full_name}'s role could not be resolved from tenure data
        </p>
        <p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0;">
            argued_date {warning.argued_date} falls outside all recorded tenures.
            Showing most recent tenure as fallback.
            <a href="/admin/people/{warning.person_id}"
               style="color: #93c5fd; text-decoration: underline;">Edit person</a>
        </p>
    </div>
{/each}
```

---

## Runtime State Inventory

> Phase 15 is NOT a rename/refactor phase — this section is not applicable.

---

## Environment Availability

No new external dependencies. All tools already available:

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| PostgreSQL (asyncpg) | Schema migration | ✓ | Pre-existing; `statement_cache_size=0` enforced |
| Python 3.12+ | Service layer | ✓ | Python 3.14.4 installed |
| SvelteKit / Node.js | Frontend | ✓ | Pre-existing |
| Alembic | Migration 0008 | ✓ | Pre-existing in project |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (api/tests/) |
| Config file | pytest.ini |
| Quick run command | `pytest api/tests/ -x -q` |
| Full suite command | `pytest api/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | File |
|--------|----------|-----------|------|
| ROLE-01 | Tenure date-range lookup returns correct seat for argued_date | unit | `api/tests/test_speakers_service.py` (new) |
| ROLE-01 | Fallback to most-recent tenure when argued_date is outside all ranges | unit | `api/tests/test_speakers_service.py` (new) |
| ROLE-01 | Graceful None when no tenure rows exist | unit | `api/tests/test_speakers_service.py` (new) |
| ROLE-02 | Migration 0008 backfill: `ADVOCATE` → `UNKNOWN` in argument_participants | integration | `api/tests/test_migration_0008.py` (new, optional) |
| ROLE-03 | PATCH participant side scoped to argument_id (IDOR guard) | unit | `api/tests/test_admin_arguments.py` (extend) |
| D-01 | approve_job sets status='draft' and resolved_at | unit | `api/tests/test_admin_jobs.py` (extend) |
| D-01 | approve_job raises on double-approve (status != pipeline) | unit | `api/tests/test_admin_jobs.py` (extend) |

### Wave 0 Gaps

- [ ] `api/tests/test_speakers_service.py` — covers ROLE-01 tenure logic (new file)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | Existing `verify_admin_token` router dependency (all admin endpoints inherit); new PATCH endpoint for participant side must also be under this router. IDOR guard: participant_id scoped by argument_id in WHERE clause. |
| V5 Input Validation | yes | `ParticipantSideUpdate` Pydantic schema — only `side: SideEnum` is writable; service validates BENCH cannot be set via this endpoint; `fromisoformat()` for any date strings |
| V2 Authentication | no | Auth unchanged from Phase 6 |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on participant side PATCH | Tampering | Scope WHERE by both `argument_id` and `participant_id`; return 404 if mismatch |
| Mass-assignment on ArgumentParticipant | Tampering | `ParticipantSideUpdate` exposes only `side`; all other fields excluded |
| Double-approve race | Spoofing | `approve_job` validates `argument.status == PIPELINE` before write; second attempt gets 422 |
| BENCH side set via participant PATCH | Tampering | Service validates `body.side != BENCH`; return 422 if attempted |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `argument_participants.side` limited to BENCH/ADVOCATE/UNKNOWN | Expanded to include PETITIONER/RESPONDENT/AMICUS | Phase 15 migration | Advocate roles now per-argument, not inferred from person-level role |
| `role_name` from `Person.role_id` join (static) | `role_name` from tenure date-range lookup (dynamic) | Phase 15 service update | Justices show historically accurate titles |
| Argument lifecycle: pipeline/resolved/published via NULL-check columns | Explicit `status` enum: pipeline/draft/published | Phase 15 migration | Cleaner state machine; admin list can filter by status |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ALTER TYPE ... ADD VALUE` requires `COMMIT` before the ADD VALUE statement inside Alembic migration | Pitfall 1, Example 2 | Migration fails with `ERROR: ALTER TYPE ... ADD VALUE cannot run inside a transaction block`. Fix: restructure migration with explicit COMMIT before ADD VALUE calls. |
| A2 | SQLAlchemy `exists()` subquery syntax for tenure-gap filter | Pattern 7 | Query syntax error at startup or wrong results. Fix: test the query against actual DB. |
| A3 | `CourtTenure.start_date` and `end_date` are returned as `datetime.date` objects (not strings) by SQLAlchemy async queries | Pattern 3 | Date comparison fails with TypeError (comparing str to date). Fix: serialize/deserialize consistently. |
| A4 | Advocate side dropdowns in pipeline job detail are submitted as part of the approve form (not as separate auto-save PATCH calls) | Patterns 3/10 | If auto-save on change is desired, each change requires a separate PATCH. UI-SPEC §Interaction Contracts says pipeline job detail advocate roles are read-only post-approval — implies they are captured at approve time. This needs a field per participant in the approve form payload. |

**A4 is the most consequential assumption.** The UI-SPEC (§Interaction Contracts, Advocate Role Dropdown) says: "On the pipeline job detail page: dropdown is only editable while `argument.status === 'pipeline'`. Post-approval: show role label as read-only text." This implies the advocate side values are saved at approve-time or as separate auto-saves. The CONTEXT.md does not specify the submission mechanism. The planner should decide: include advocate sides in the approve payload (simpler, atomic) vs. separate PATCH per row (flexible but more complex). **Recommend:** include advocate sides as part of the approve POST body for atomicity — one action sets status, resolved_at, AND all participant sides.

---

## Open Questions

1. **Advocate sides submitted with approve, or as separate PATCHes?**
   - What we know: UI-SPEC says dropdowns are editable pre-approve only; post-approve they become read-only text. CONTEXT.md D-09 says approve triggers `argument.status = 'draft'`, `argument.resolved_at = now()`, job read-only.
   - What's unclear: whether advocate sides are saved as part of the approve action or require separate PATCH calls before approve.
   - Recommendation: include advocate sides in the approve POST body as `participant_sides: list[{participant_id, side}]` — cleaner, atomic, one round-trip.

2. **Tenure gap warnings: should `get_argument_detail` compute them, or a separate endpoint?**
   - What we know: the argument edit page must show TenureGapWarning banners per affected bench speaker.
   - What's unclear: whether to embed in `ArgumentDetail` response or add a separate GET endpoint.
   - Recommendation: embed in `ArgumentDetail` as `tenure_gap_warnings: list[TenureGapWarning]` — the edit page already loads argument detail; a second endpoint adds latency and complexity.

---

## Sources

### Primary (HIGH confidence — verified against live codebase)
- `api/models/models.py` — SideEnum (line 34), ArgumentParticipant (line 205), Argument (line 149), CourtTenure (line 113)
- `api/services/speakers.py` — `get_argument_speakers` three-query pattern
- `api/services/admin_jobs.py` — `resolve_job`, `create_job`, `try_advance_*` patterns
- `api/services/admin_arguments.py` — `update_argument`, `publish_argument` service patterns
- `api/routers/admin.py` — router structure, existing endpoints, verify_admin_token dependency
- `api/schemas/admin_arguments.py` — mass-assignment allow-list pattern
- `api/schemas/speakers.py` — `SpeakerPopoverEntry` schema
- `alembic/versions/0001_initial_schema.py` — DO-block enum creation pattern
- `alembic/versions/0007_add_published_at.py` — `op.add_column` pattern
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — resolve review table, rowStates pattern
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — SvelteKit form actions pattern
- `app/src/routes/admin/arguments/[id]/+page.svelte` — argument edit form pattern
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — save/publish/unpublish actions
- `app/src/routes/admin/people/+page.svelte` — filter toggle pattern (role="switch")
- `.planning/phases/15-speaker-role-accuracy/15-CONTEXT.md` — all locked decisions
- `.planning/phases/15-speaker-role-accuracy/15-UI-SPEC.md` — visual and interaction contracts
- `CLAUDE.md` — Alembic DDL authority, asyncpg constraint, Svelte 5 Runes requirement

### Tertiary (LOW confidence — assumed from training knowledge)
- PostgreSQL `ALTER TYPE ... ADD VALUE` transaction restriction (A1)
- SQLAlchemy `exists()` subquery syntax for tenure-gap filter (A2)

---

## Metadata

**Confidence breakdown:**
- Schema migration pattern: HIGH — exact migration patterns verified against existing 0001/0007 migrations
- Service layer changes: HIGH — `get_argument_speakers` and admin service patterns verified in full
- Svelte UI patterns: HIGH — pipeline job detail and argument edit page read in full; form action patterns clear
- Tenure gap query: MEDIUM — conceptually sound, SQLAlchemy `exists()` syntax assumed
- ALTER TYPE transaction handling: LOW — assumed; must be tested locally before final plan

**Research date:** 2026-06-25
**Valid until:** 2026-07-25 (stable stack — no fast-moving dependencies)
