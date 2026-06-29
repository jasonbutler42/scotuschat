# Phase 15: Speaker Role Accuracy — Pattern Map

**Mapped:** 2026-06-25
**Files analyzed:** 13 new/modified files
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `alembic/versions/0008_side_enum_and_argument_status.py` | migration | batch | `alembic/versions/0007_add_published_at.py` + `0001_initial_schema.py` | composite |
| `api/models/models.py` | model | — | `api/models/models.py` (self-extend) | exact |
| `api/schemas/speakers.py` | schema | request-response | `api/schemas/speakers.py` (self-extend) | exact |
| `api/schemas/admin_arguments.py` | schema | request-response | `api/schemas/admin_arguments.py` (self-extend) | exact |
| `api/services/speakers.py` | service | request-response | `api/services/speakers.py` (self-extend) | exact |
| `api/services/admin_jobs.py` | service | CRUD | `api/services/admin_jobs.py` `resolve_job` | exact |
| `api/services/admin_arguments.py` | service | CRUD | `api/services/admin_arguments.py` `list_arguments` | exact |
| `api/services/admin_people.py` | service | CRUD | `api/services/admin_people.py` `list_people` | exact |
| `api/routers/admin.py` | controller | request-response | `api/routers/admin.py` existing endpoints | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | server-load | request-response | `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (self-extend) | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | component | request-response | `app/src/routes/admin/arguments/[id]/+page.svelte` | role-match |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | server-load | request-response | `app/src/routes/admin/arguments/[id]/+page.server.ts` (self-extend) | exact |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | component | request-response | `app/src/routes/admin/arguments/[id]/+page.svelte` (self-extend) | exact |
| `app/src/routes/admin/arguments/+page.svelte` | component | request-response | `app/src/routes/admin/arguments/+page.svelte` (self-extend) | exact |
| `app/src/routes/admin/arguments/+page.server.ts` | server-load | request-response | `app/src/routes/admin/arguments/+page.server.ts` | exact |
| `app/src/routes/admin/people/+page.svelte` | component | request-response | `app/src/routes/admin/people/+page.svelte` (self-extend) | exact |
| `app/src/routes/admin/people/+page.server.ts` | server-load | request-response | `app/src/routes/admin/people/+page.server.ts` | exact |
| `api/tests/test_speakers_service.py` | test | — | (no analog — new test file) | none |

---

## Pattern Assignments

### `alembic/versions/0008_side_enum_and_argument_status.py` (migration, batch)

**Analogs:** `alembic/versions/0001_initial_schema.py` (DO-block enum creation) and `alembic/versions/0007_add_published_at.py` (op.add_column pattern)

**Migration header pattern** (`0007_add_published_at.py` lines 24–34):
```python
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**DO-block enum creation pattern** (`0001_initial_schema.py` lines 42–54):
```python
op.execute(sa.text("""
    DO $$ BEGIN
        CREATE TYPE side AS ENUM ('BENCH', 'ADVOCATE', 'UNKNOWN');
    EXCEPTION WHEN duplicate_object THEN null;
    END $$;
"""))
```
New `argument_status` type uses identical DO-block pattern. The new type's values are `('pipeline', 'draft', 'published')`.

**op.add_column pattern** (`0007_add_published_at.py` lines 36–40):
```python
def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("arguments", "published_at")
```

**Critical ALTER TYPE constraint** (RESEARCH.md Pitfall 1): `ALTER TYPE ... ADD VALUE` cannot run inside a transaction. The migration must commit Alembic's implicit transaction before the ADD VALUE calls:
```python
def upgrade() -> None:
    # Commit open transaction before ALTER TYPE ADD VALUE (Pitfall 1)
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))
    # Backfill + new column can follow in transactional statements
```

**Backfill + NOT NULL alter pattern** (RESEARCH.md Pattern 2):
```python
op.add_column("arguments", sa.Column("status",
    sa.Enum("pipeline", "draft", "published", name="argument_status"),
    nullable=True))
op.execute(sa.text(
    "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"))
op.execute(sa.text(
    "UPDATE arguments SET status = 'draft' "
    "WHERE resolved_at IS NOT NULL AND published_at IS NULL"))
op.execute(sa.text(
    "UPDATE arguments SET status = 'pipeline' WHERE resolved_at IS NULL"))
op.alter_column("arguments", "status", nullable=False)
```

---

### `api/models/models.py` (model, extend SideEnum + add ArgumentStatusEnum + Argument.status)

**Analog:** self-extend. Copy existing SAEnum column pattern.

**Existing SideEnum** (lines 34–37) — add three values after UNKNOWN:
```python
class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"   # legacy — never remove (PG cannot drop enum values)
    UNKNOWN = "UNKNOWN"
# Phase 15 additions:
    PETITIONER = "PETITIONER"
    RESPONDENT = "RESPONDENT"
    AMICUS = "AMICUS"
```

**SAEnum column pattern** (models.py lines 230–234, `PipelineRun.status` — exact pattern to copy for `Argument.status`):
```python
status = Column(
    SAEnum(PipelineRunStatus, name="pipeline_run_status",
           values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    default=PipelineRunStatus.PENDING,
)
```
New `Argument.status` column follows identical pattern using `ArgumentStatusEnum` and name `"argument_status"`. Default is `ArgumentStatusEnum.PIPELINE`.

**New enum class** (models.py — add after `AdminJobStep`):
```python
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"
```

---

### `api/schemas/speakers.py` (schema, extend SpeakerPopoverEntry)

**Analog:** self-extend (`api/schemas/speakers.py` lines 22–38).

**Existing SpeakerPopoverEntry** (lines 22–38):
```python
class SpeakerPopoverEntry(BaseModel):
    person_id: int
    full_name: str
    role_name: Optional[str] = None
    photo_url: Optional[str] = None
    appointing_president: Optional[str] = None
    tenure: list[TenureEntry] = []
    model_config = ConfigDict(from_attributes=True)
```
Phase 15 adds `side: Optional[str] = None` (the raw SideEnum value) so `+page.server.ts` can conditionally apply `isBench` rendering logic. The `role_name` field stays — its source changes in the service layer, not the schema.

---

### `api/schemas/admin_arguments.py` (schema, extend ArgumentListItem + ArgumentDetail + add new schemas)

**Analog:** self-extend.

**Mass-assignment allow-list pattern** (lines 69–87) — new `ParticipantSideUpdate` copies this isolation pattern:
```python
class ArgumentUpdate(BaseModel):
    """PATCH body — mass-assignment guard (T-11-MASS): ONLY these fields writable."""
    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None
```

**New schemas to add** (RESEARCH.md Patterns 6 and 8):
```python
class ParticipantSideUpdate(BaseModel):
    """PATCH body for argument_participants.side — IDOR guard: scoped by argument_id + participant_id."""
    side: SideEnum  # only PETITIONER, RESPONDENT, AMICUS, UNKNOWN; service validates BENCH cannot be set

class TenureGapWarning(BaseModel):
    person_id: int
    full_name: str
    argued_date: str  # "YYYY-MM-DD"
```

**ArgumentListItem extension** — add `status: ArgumentStatusEnum` field (from_attributes=True already set).

**ArgumentDetail extension** — add `tenure_gap_warnings: list[TenureGapWarning] = []`.

---

### `api/services/speakers.py` (service, extend get_argument_speakers)

**Analog:** self-extend. The file is the primary target — read it in full above.

**Existing three-query pattern** (lines 20–92) — Phase 15 inserts two new queries and replaces the assembly step.

**Imports to add** (line 17 area):
```python
from api.models.models import ArgumentParticipant, Argument, CourtTenure, Person, Role, SideEnum, Utterance
```

**New Step 0 — argued_date fetch** (insert before Step 1):
```python
arg_result = await db.execute(
    select(Argument.argued_date).where(Argument.id == argument_id)
)
argued_date = arg_result.scalar_one_or_none()
```

**New Step between 3 and 4 — side per person** (RESEARCH.md Pattern 3, Step B):
```python
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

**New label map + tenure lookup helper** (RESEARCH.md Example 1 — place as module-level constants/functions):
```python
ADVOCATE_LABEL_MAP = {
    SideEnum.PETITIONER: "Petitioner's Counsel",
    SideEnum.RESPONDENT: "Respondent's Counsel",
    SideEnum.AMICUS: "Amicus Curiae",
    SideEnum.UNKNOWN: "Counsel",
    SideEnum.ADVOCATE: "Counsel",  # legacy
}

def _tenure_role_name(tenures: list[dict], argued_date) -> str | None:
    """D-13/D-14: date-range lookup, fallback to most-recent tenure."""
    import datetime
    if not tenures:
        return None
    if argued_date is not None:
        for t in tenures:
            start = t["start_date"]  # keep as datetime.date for comparison
            end = t["end_date"]
            if start is not None and argued_date >= start:
                if end is None or argued_date <= end:
                    return t["seat"]
    most_recent = max(tenures, key=lambda t: t["start_date"] or datetime.date.min)
    return most_recent["seat"]
```

**Assembly step change** (replace lines 79–90): use `side_by_person.get(person.id)` and call `_tenure_role_name` for BENCH vs `ADVOCATE_LABEL_MAP` for advocates. Also include `side` in each assembled dict so `SpeakerPopoverEntry.side` is populated.

**Date serialization note** (RESEARCH.md Example 1, final paragraph): keep tenures as `datetime.date` objects internally for the lookup; stringify only in the final dict assembly (`"start_date": str(t.start_date) if t.start_date else None`).

---

### `api/services/admin_jobs.py` (service, add approve_job + rerun_job)

**Analog:** `resolve_job` function (lines 195–314) — exact structural model.

**approve_job pattern** (RESEARCH.md Pattern 4 — mirrors resolve_job Step 3 commit):
```python
async def approve_job(db: AsyncSession, job_id: int) -> AdminJob:
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.argument_id is None:
        raise ValueError(f"AdminJob {job_id} has no linked argument")

    arg_result = await db.execute(select(Argument).where(Argument.id == job.argument_id))
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        raise ValueError("Argument not found for this job")
    if argument.status != ArgumentStatusEnum.PIPELINE:
        raise ValueError(
            f"Argument is already in '{argument.status.value}' state; cannot approve again."
        )

    await db.execute(
        update(Argument)
        .where(Argument.id == job.argument_id)
        .values(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        update(AdminJob)
        .where(AdminJob.id == job_id)
        .values(status=AdminJobStatus.COMPLETED)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    updated = await get_job(db, job_id)
    return updated  # type: ignore[return-value]
```

**rerun_job pattern** (RESEARCH.md Pattern 5 — mirrors create_job):
```python
async def rerun_job(db: AsyncSession, job_id: int) -> AdminJob:
    original = await get_job(db, job_id)
    if original is None:
        raise ValueError(f"AdminJob {job_id} not found")
    new_job = await create_job(db, pdf_url=original.pdf_url, spaces_key=original.spaces_key)
    return new_job
```
Caller (router) spawns the ingest subprocess after this returns, matching `POST /api/admin/jobs` pattern (admin.py lines 155–156).

---

### `api/services/admin_arguments.py` (service, extend list_arguments + get_argument_detail + add update_participant_side)

**Analog:** self-extend.

**list_arguments filter extension** (RESEARCH.md Pattern 9 — add after existing query build):
```python
# Exclude pipeline-state arguments from admin list (D-02)
q = q.where(Argument.status.in_([ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.PUBLISHED]))
```

**get_argument_detail extension** (RESEARCH.md Pattern 8) — add tenure gap warnings computation before final return dict:
```python
# Tenure gap warnings: bench participants whose argued_date is outside all their tenures
# (service helper or inline — see Pattern 8)
```

**update_participant_side new function** (RESEARCH.md Pattern 6):
```python
async def update_participant_side(
    db: AsyncSession,
    argument_id: int,
    participant_id: int,
    side: SideEnum,
) -> dict | None:
    """PATCH argument_participants.side scoped by both argument_id and participant_id (IDOR guard)."""
    if side == SideEnum.BENCH:
        raise ValueError("BENCH cannot be set via participant side update")
    result = await db.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None  # router → 404
    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
        .values(side=side)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return {"id": participant_id, "side": side.value}
```

---

### `api/services/admin_people.py` (service, extend list_people with tenure_gaps filter)

**Analog:** `list_people` function (lines 123–152) — the `incomplete` filter is the direct model.

**Existing filter toggle pattern** (lines 141–149):
```python
q = (
    select(Person, Role.name.label("role_name"))
    .outerjoin(Role, Person.role_id == Role.id)
    .order_by(sqlfunc.coalesce(Person.last_name, Person.full_name).asc())
)
if incomplete:
    q = q.where(
        or_(Person.role_id.is_(None), Person.bio_text.is_(None), Person.photo_url.is_(None))
    )
```

**New tenure_gaps filter** (RESEARCH.md Pattern 7 — add as a parallel `if tenure_gaps:` branch):
```python
from sqlalchemy import and_, exists, not_

if tenure_gaps:
    covering_tenure = exists(
        select(CourtTenure.id).where(
            and_(
                CourtTenure.person_id == ArgumentParticipant.person_id,
                CourtTenure.start_date <= Argument.argued_date,
                or_(
                    CourtTenure.end_date.is_(None),
                    CourtTenure.end_date >= Argument.argued_date,
                ),
            )
        )
    )
    gap_person_ids = (
        select(ArgumentParticipant.person_id)
        .join(Argument, Argument.id == ArgumentParticipant.argument_id)
        .where(
            ArgumentParticipant.side == SideEnum.BENCH,
            ArgumentParticipant.person_id.isnot(None),
            not_(covering_tenure),
        )
        .distinct()
    )
    q = q.where(Person.id.in_(gap_person_ids))
```

Add `tenure_gaps: bool = False` parameter to `list_people` signature (matches `incomplete` parameter pattern).

---

### `api/routers/admin.py` (controller, add approve + rerun + participant side endpoints)

**Analog:** self-extend. All new endpoints follow the exact pattern of existing endpoints in the file.

**Router-level auth** (lines 98–101) — all new endpoints inherit automatically, no per-route auth needed:
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```

**POST endpoint returning 200 pattern** (lines 245–260 area, get_job poll endpoint):
```python
@router.post("/jobs/{job_id}", response_model=AdminJobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
```

**ValueError → 422 pattern** (existing resolve endpoint — copy for approve and participant side PATCH):
```python
try:
    result = await jobs_service.approve_job(db, job_id)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
```

**New endpoints to add:**
- `POST /api/admin/jobs/{job_id}/approve` → calls `jobs_service.approve_job`; returns `AdminJobResponse`
- `POST /api/admin/jobs/{job_id}/rerun` → calls `jobs_service.rerun_job` + `spawn_pipeline_step`; returns 202 + `AdminJobResponse`
- `PATCH /api/admin/arguments/{argument_id}/participants/{participant_id}` → calls `arguments_service.update_participant_side`; body is `ParticipantSideUpdate`; returns 404 if participant not found

---

### `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (server-load, add approve + rerun actions)

**Analog:** self-extend. The `resolve` action (lines 112–143) is the direct model.

**Existing action pattern** (lines 112–143):
```typescript
resolve: async ({ request, params }) => {
    const data = await request.formData();
    // ... parse form data ...
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/resolve`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
            body: JSON.stringify({ matches }),
        });
    } catch {
        return fail(422, { error: 'Could not save...' });
    }
    if (!res.ok) {
        return fail(422, { error: 'Could not save...' });
    }
    return { success: true };
},
```

**New approve action** (RESEARCH.md Pattern 10 — uses redirect on success, matching argument edit publish action):
```typescript
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

**New rerun action** — same shape as approve but calls `/rerun`; redirects to the NEW job's page (returned in response body).

**Import pattern** (line 1–3) — add `redirect` if not already present:
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
```

---

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (component, add advocate dropdowns + Approve button + Re-run button)

**Analog:** `app/src/routes/admin/arguments/[id]/+page.svelte` for the form action + use:enhance pattern; `app/src/routes/admin/people/+page.svelte` lines 1–17 for Svelte 5 Runes `$props()` + `$derived()` pattern.

**Svelte 5 Runes props pattern** (`admin/people/+page.svelte` lines 1–8):
```svelte
<script lang="ts">
    let { data } = $props();
    let checked = $derived(data.incomplete ?? false);
</script>
```

**use:enhance form action pattern** (`admin/arguments/[id]/+page.svelte` — enhance is imported from `$app/forms`):
```svelte
<script lang="ts">
    import { enhance } from '$app/forms';
    let { data } = $props();
</script>
<form method="POST" action="?/approve" use:enhance>
    ...
    <button type="submit">Create Argument</button>
</form>
```

**Advocate role dropdown pattern** (RESEARCH.md Example 3):
```svelte
<select
    name="side"
    value={participant.side}
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

---

### `app/src/routes/admin/arguments/[id]/+page.server.ts` (server-load, add updateParticipantSide action)

**Analog:** self-extend. The `save` action (lines 44–92) is the direct model.

**Existing PATCH action pattern** (lines 44–92):
```typescript
save: async ({ request, params, fetch }) => {
    const formData = await request.formData();
    // ... extract fields ...
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
            method: 'PATCH',
            headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
            body: JSON.stringify({ case_name, docket_number, argued_date }),
        });
    } catch {
        return fail(502, { error: 'Could not save changes...' });
    }
    if (!res.ok) {
        // error handling with detail parsing
    }
    throw redirect(303, '/admin/arguments/' + params.id);
},
```

**New updateParticipantSide action** — follows identical try/catch/fail/redirect structure; PATCH to `/api/admin/arguments/${params.id}/participants/${participant_id}` with `{ side }` body.

**Load function extension** — add `tenure_gap_warnings` from the existing `argument` fetch (already loaded via `get_argument_detail`; no second fetch needed once `ArgumentDetail` includes the field).

---

### `app/src/routes/admin/arguments/[id]/+page.svelte` (component, add advocate role editor + TenureGapWarning)

**Analog:** self-extend.

**TenureGapWarning banner pattern** (RESEARCH.md Example 4):
```svelte
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

**Advocate role section form** — wraps advocate participant dropdowns in a form with `method="POST" action="?/updateParticipantSide" use:enhance`, identical to existing `save` form structure.

---

### `app/src/routes/admin/arguments/+page.svelte` (component, add status badge)

**Analog:** self-extend. The existing `badgeStyle` / `badgeLabel` helpers (lines 19–36) are replaced by `status`-field equivalents.

**Existing status badge helpers** (lines 19–36):
```svelte
function badgeStyle(resolved_at: string | null, published_at: string | null): string {
    let color: string;
    if (published_at) { color = '#4ade80'; }
    else if (resolved_at) { color = '#a78bfa'; }
    else { color = '#94a3b8'; }
    return `border: 1px solid ${color}; ...`;
}
function badgeLabel(resolved_at: string | null, published_at: string | null): string {
    if (published_at) return 'Published';
    if (resolved_at) return 'Resolved';
    return 'Pending';
}
```
Replace with `status`-field equivalents: `'draft'` → violet, `'published'` → green. The list no longer receives `pipeline` rows (D-02 service filter).

---

### `app/src/routes/admin/people/+page.svelte` (component, add tenure_gaps toggle)

**Analog:** self-extend. The `incomplete` toggle (lines 1–62) is the exact model.

**Filter toggle pattern** (lines 1–62):
```svelte
<script lang="ts">
    import { goto } from '$app/navigation';
    let { data } = $props();
    let checked = $derived(data.incomplete ?? false);
    function handleToggle() {
        if (checked) { goto('/admin/people'); }
        else { goto('/admin/people?incomplete=1'); }
    }
</script>
<!-- button role="switch" aria-checked={checked} ... -->
```
New `tenure_gaps` toggle follows identical pattern: `data.tenure_gaps ?? false`, navigates to `/admin/people?tenure_gaps=1`.

---

### `app/src/routes/admin/people/+page.server.ts` (server-load, pass tenure_gaps param)

**Analog:** existing people `+page.server.ts`. Copy `incomplete` param extraction and pass to API.

The load function reads `url.searchParams.get('incomplete')` and appends `?incomplete=1` to the API URL. New `tenure_gaps` param follows identical pattern.

---

## Shared Patterns

### Admin Authentication
**Source:** `api/routers/admin.py` lines 81–101
**Apply to:** All new FastAPI router endpoints (approve, rerun, participant side PATCH)
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```
Auth is inherited at router level — no per-route auth annotation needed.

### ValueError → HTTPException 422
**Source:** `api/routers/admin.py` (resolve endpoint area)
**Apply to:** approve, rerun, updateParticipantSide router endpoints
```python
try:
    result = await service.approve_job(db, job_id)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
if result is None:
    raise HTTPException(status_code=404, detail="Not found")
```

### SQLAlchemy update() mandatory option
**Source:** `api/services/admin_jobs.py` lines 115–126; `api/services/admin_arguments.py` lines 242–247
**Apply to:** Every `update()` call in new/extended services
```python
.execution_options(synchronize_session=False)
```
Every `update()` statement must include this. Omitting it is a known critical pitfall.

### SvelteKit Server-Only Env Vars
**Source:** `app/src/routes/admin/arguments/[id]/+page.server.ts` line 1
**Apply to:** All `+page.server.ts` files
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
```
Never `$env/static/public` or `PUBLIC_` prefix. FASTAPI_BASE_URL is server-only.

### SvelteKit fail/redirect error handling
**Source:** `app/src/routes/admin/arguments/[id]/+page.server.ts` lines 52–92
**Apply to:** All new form actions (approve, rerun, updateParticipantSide)
```typescript
let res: Response;
try {
    res = await fetch(...);
} catch {
    return fail(502, { error: 'Network error message.' });
}
if (!res.ok) {
    return fail(422, { error: 'Application error message.' });
}
throw redirect(303, returnPath);
```

### Svelte 5 Runes Only
**Source:** `app/src/routes/admin/people/+page.svelte` lines 1–17
**Apply to:** ALL `.svelte` files
```svelte
<script lang="ts">
    let { data } = $props();
    let someState = $state(false);
    let derived = $derived(data.someField ?? false);
</script>
```
No `export let`, no `$:` reactive blocks, no Svelte stores.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `api/tests/test_speakers_service.py` | test | — | No existing unit test for `speakers.py`; planner should use pytest patterns from `api/tests/` directory for structure |

---

## Metadata

**Analog search scope:** `api/models/`, `api/services/`, `api/schemas/`, `api/routers/`, `alembic/versions/`, `app/src/routes/admin/`
**Files read:** 16
**Pattern extraction date:** 2026-06-25
