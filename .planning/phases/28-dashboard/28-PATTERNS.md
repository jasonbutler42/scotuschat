# Phase 28: Dashboard - Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 9 (3 backend service additions, 1 schema file, 1 router file edit, 2 frontend files rewritten, 1 new shared component, 0 new migrations)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `api/services/admin_arguments.py` (add `get_argument_stats()`, `get_recent_drafts()`) | service | CRUD (aggregate COUNT/LIMIT read) | same file's existing `list_arguments()` (lines 49-98) | exact (same module, same resource, needs new aggregate query shape) |
| `api/services/admin_people.py` (add `get_people_stats()`, `get_incomplete_people()`, `get_tenure_gap_justices()`) | service | CRUD (aggregate COUNT/LIMIT read) | same file's existing `list_people()` (lines 168-322) | exact (same module; reuse `list_people(is_justice=True, tenure_gaps=True)` directly per RESEARCH.md "Don't Hand-Roll") |
| `api/services/admin_jobs.py` (add `get_pipeline_stats()`) | service | CRUD (aggregate COUNT/MAX read) | same file's `list_jobs()` (lines 239-288) | exact (same module, same resource; `AdminJob.created_at`/`updated_at` already reliable aggregation targets) |
| `api/schemas/admin_dashboard.py` (NEW) | model (Pydantic schema) | transform (ORM/dict → response shape) | `api/schemas/admin_arguments.py` (lines 1-40, `ArgumentListItem` shape) | role-match (same BaseModel + docstring-header convention) |
| `api/routers/admin.py` (add `GET /arguments/stats`, `GET /people/stats`, `GET /jobs/stats`, `GET /utterances/count`) | route | request-response | `GET /arguments/check-duplicate` (lines 856-873) | exact — same literal-route-before-`{id}`-route ordering discipline, same router-level auth |
| `app/src/routes/admin/+page.server.ts` (rewritten `load()`) | controller (SvelteKit server load) | request-response (sequential fan-out to FastAPI) | `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (lines 63-263) | exact — sequential-await + per-block try/catch degrade pattern, same file family |
| `app/src/routes/admin/+page.svelte` (rewritten) | component | request-response (render-only, no client state) | `app/src/routes/admin/+page.svelte` (current placeholder, lines 1-43) + `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (card composition precedent) | role-match (same route file being replaced; card composition borrowed from pipeline detail page) |
| `app/src/lib/components/StatCard.svelte` (NEW) | component | request-response (presentation only, props in / snippet out) | none — first shared card component; closest precedent is the repeated inline card markup on every admin page (e.g. `admin/pipeline/[job_id]/+page.svelte`'s Run Status Card block) | no direct analog (see "No Analog Found") — RESEARCH.md Pattern 2 supplies the shape |
| `app/src/lib/components/` — Web Traffic placeholder markup (inline in `+page.svelte`, not a separate component) | component | n/a (static, no data-fetch) | none — first placeholder-card pattern in the codebase | no analog (see "No Analog Found") — RESEARCH.md Pattern 3 supplies the shape |

## Pattern Assignments

### `api/services/admin_arguments.py` — add `get_argument_stats()`, `get_recent_drafts()` (service, CRUD-aggregate)

**Analog:** same file's `list_arguments()` (lines 49-98) and `ArgumentStatusEnum` usage throughout the file.

**Imports pattern** (already present at top of file, lines 19-41 — no new imports needed beyond `func as sqlfunc` which is already imported):
```python
from sqlalchemy import and_, delete, exists, func as sqlfunc, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import (
    AdminJob, Argument, ArgumentParticipant, ArgumentStatusEnum,
    ArgumentStatusLog, Case, CaseArgument, CourtTenure, Person,
    PipelineRun, SideEnum, Utterance,
)
```

**Core aggregate-count pattern to copy** (adapt `list_arguments`'s status filter + `Case` join, lines 58-84, but replace row-select with `sqlfunc.count()` grouped by status — do NOT reuse `list_arguments()` unmodified per RESEARCH.md Pitfall 2):
```python
# Pattern: same WHERE clause shape as list_arguments() (exclude PIPELINE status,
# ALIST-02), but COUNT grouped by status instead of returning full rows.
q = (
    select(Argument.status, sqlfunc.count())
    .where(
        Argument.status.in_([
            ArgumentStatusEnum.DRAFT,
            ArgumentStatusEnum.PUBLISHED,
            ArgumentStatusEnum.UNPUBLISHED,
        ])
    )
    .group_by(Argument.status)
)
result = await db.execute(q)
counts_by_status = dict(result.all())  # {ArgumentStatusEnum.DRAFT: 3, ...}
```

**"Recent drafts" LIMIT 5 pattern** (mirrors `list_arguments`'s `Case`/`CaseArgument` join shape, lines 58-70, but adds `WHERE status = DRAFT ORDER BY id DESC LIMIT 5` per Pitfall 3's guidance — do not use `resolved_at` as an ordering proxy):
```python
q = (
    select(Argument.id, Case.case_name, Case.docket_number)
    .join(CaseArgument, CaseArgument.argument_id == Argument.id)
    .join(Case, CaseArgument.case_id == Case.id)
    .where(CaseArgument.is_lead == True, Argument.status == ArgumentStatusEnum.DRAFT)  # noqa: E712
    .order_by(Argument.id.desc())
    .limit(5)
)
```

**Error handling pattern:** none needed — these are pure read functions; no try/except inside service layer anywhere in this codebase (errors propagate to the router, which the FastAPI dependency layer already handles for auth/404 cases). No precedent for service-level try/except on SELECT-only functions.

---

### `api/services/admin_people.py` — add `get_people_stats()`, `get_incomplete_people()`, `get_tenure_gap_justices()` (service, CRUD-aggregate)

**Analog:** same file's `list_people()` (lines 168-322), specifically its `missing`-filter dict (lines 219-226) and its tenure prefetch idiom (lines 269-279).

**Core pattern — reuse `list_people()` directly, filter/slice in Python (per RESEARCH.md "Don't Hand-Roll" — do NOT add a new SQL "any missing field" mode, per CONTEXT.md D-05):**
```python
async def get_people_stats(db: AsyncSession) -> dict:
    """Aggregate counts for the People stat card (DASH-01) — total + incomplete,
    computed from the existing list_people() output, not a new SQL filter mode
    (D-05 forbids reintroducing the removed generic 'incomplete' toggle)."""
    rows = await list_people(db)  # both tabs, no filter — small/bounded table
    total = len(rows)
    incomplete = sum(1 for r in rows if r["missing"])
    return {"total": total, "incomplete": incomplete}

async def get_incomplete_people(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Top-5 incomplete people across both tabs (Needs Attention 'People' sub-list,
    D-02, one combined list per UI-SPEC.md 'Combined vs. split People sub-list')."""
    rows = await list_people(db)
    return [r for r in rows if r["missing"]][:limit]

async def get_tenure_gap_justices(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Top-5 tenure-gap Justices (Needs Attention 'Justices' sub-list, D-06) —
    reuses list_people(is_justice=True, tenure_gaps=True) verbatim per RESEARCH.md
    Don't Hand-Roll (gap_person_ids_query is a local variable, not importable)."""
    rows = await list_people(db, is_justice=True, tenure_gaps=True)
    return rows[:limit]
```

**Imports pattern:** none new — `list_people` is already defined in the same module; no additional import needed.

**Error handling pattern:** same as arguments — pure reads, no try/except in service layer.

---

### `api/services/admin_jobs.py` — add `get_pipeline_stats()` (service, CRUD-aggregate)

**Analog:** same file's `list_jobs()` (lines 239-288) and `get_job()`'s `func.count()` usage (lines 169-206).

**Imports pattern** (already present, line 22 — `func` is already imported as `func`, not aliased):
```python
from sqlalchemy import delete, exists, select, update
from sqlalchemy import func
```

**Core "30-day recent count + unbounded last activity" pattern** (mirrors `get_job`'s `scalar_one()` COUNT idiom, lines 169-175, and 189-205's `func.count()` usage):
```python
import datetime

async def get_pipeline_stats(db: AsyncSession) -> dict:
    """Recent-window count + unbounded last-activity timestamp for the Pipeline
    runs stat card (DASH-01, A1: 30-day window, per RESEARCH.md Open Question 1).
    """
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    recent_result = await db.execute(
        select(func.count(AdminJob.id)).where(AdminJob.created_at >= cutoff)
    )
    recent_count = recent_result.scalar_one()  # COUNT always returns a row

    last_activity_result = await db.execute(select(func.max(AdminJob.updated_at)))
    last_activity_at = last_activity_result.scalar_one_or_none()  # MAX over empty table is NULL

    return {"recent_count": recent_count, "last_activity_at": last_activity_at}
```

**Error handling pattern:** same as other services — no try/except; `scalar_one()` is safe for COUNT (always returns a row per existing comment at line 169 of this same file), `scalar_one_or_none()` is required for MAX (can be NULL on an empty table).

---

### `api/schemas/admin_dashboard.py` (NEW schema file)

**Analog:** `api/schemas/admin_arguments.py` (lines 1-40) — module docstring header convention, `BaseModel` import, `Optional` typing style.

**Imports pattern:**
```python
import datetime
from typing import Optional

from pydantic import BaseModel

from api.models.models import ArgumentStatusEnum
```

**Core response-shape pattern** (mirrors `ArgumentListItem`'s flat-dict-friendly field style — every schema in this codebase is a plain `BaseModel`, no `from_attributes` needed here since these are hand-built dicts, not ORM rows):
```python
class ArgumentStats(BaseModel):
    total: int
    published: int
    draft: int
    unpublished: int

class RecentDraft(BaseModel):
    id: int
    case_name: str
    docket_number: str

class PeopleStats(BaseModel):
    total: int
    incomplete: int

class IncompletePerson(BaseModel):
    id: int
    full_name: str
    missing: list[str]

class TenureGapJustice(BaseModel):
    id: int
    full_name: str

class PipelineStats(BaseModel):
    recent_count: int
    last_activity_at: Optional[datetime.datetime]

class UtteranceCount(BaseModel):
    total: int
```

---

### `api/routers/admin.py` — add `GET /arguments/stats`, `GET /people/stats`, `GET /jobs/stats`, `GET /utterances/count`

**Analog:** `GET /arguments/check-duplicate` (lines 856-873) for the literal-route-ordering discipline; `GET /arguments` (lines 843-853) for the thin router→service delegation shape.

**Critical ordering rule (copy exactly — Pitfall 1):** each new `/stats` route MUST be registered **before** its sibling `{id}`-parameterized route:
```python
@router.get("/arguments/stats", response_model=ArgumentStats)
async def get_argument_stats_route(db: AsyncSession = Depends(get_db)) -> ArgumentStats:
    """
    Aggregate stat-card counts for the dashboard (DASH-01).

    CRITICAL ordering note (mirrors T-19-03-05 / check-duplicate): this literal
    route MUST be registered before GET /arguments/{argument_id} so FastAPI
    resolves the literal segment "stats" first rather than consuming it as
    argument_id.
    """
    counts = await arguments_service.get_argument_stats(db)
    return ArgumentStats(**counts)

@router.get("/arguments/{argument_id}", response_model=ArgumentDetail)
async def get_argument(argument_id: int, db: AsyncSession = Depends(get_db)) -> ArgumentDetail:
    ...  # existing, unchanged — new /stats route is now above this one
```
Apply the identical ordering pattern for `/people/stats` (before `/people/{person_id}`, currently at line 656) and `/jobs/stats` (before `/jobs/{job_id}`, currently at line 339). `GET /utterances/count` has no `{id}`-sibling route today (no `/utterances` router section exists at all) so no ordering hazard applies there — it can be added anywhere in the file, but the natural place is next to the other new `/stats` routes for discoverability.

**Auth pattern:** inherited automatically — every route lives under the same `router = APIRouter(prefix="/api/admin", dependencies=[Depends(verify_admin_token)])` (lines 109-113). No new auth code needed on any of the 4 new routes.

**Core delegation pattern:** each new route is a 2-3 line function: call the matching new service function, wrap the dict in the matching new Pydantic schema, return it — identical shape to `list_arguments` (lines 843-853).

---

### `app/src/routes/admin/+page.server.ts` (rewritten `load()`)

**Analog:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (lines 63-263), specifically the sequential-await + independent-try/catch idiom repeated at lines 82-98, 103-121, 126-144, 150-165, 169-189, 194-214.

**Imports pattern** (lines 1-3 of the analog):
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import type { PageServerLoad } from './$types';
```
(No `error`/`redirect`/`fail` needed — dashboard `load()` never throws a hard error per D-11/copywriting contract "must never hard-error on a partial data-source failure".)

**Auth pattern:** every fetch call includes `headers: { 'X-Admin-Token': ADMIN_TOKEN }` — copy verbatim from every fetch block in the analog (e.g. line 67).

**Core sequential degrade-gracefully pattern (copy this shape exactly, once per new stats endpoint — 4 blocks total: arguments/stats, people/stats, jobs/stats, utterances/count, plus 3 more for the Needs Attention top-5 lists = 7 blocks total):**
```typescript
// Source pattern: app/src/routes/admin/pipeline/[job_id]/+page.server.ts lines 82-98
let argumentStats: { total: number; published: number; draft: number; unpublished: number } =
    { total: 0, published: 0, draft: 0, unpublished: 0 };
try {
    const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/stats`, {
        headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    if (res.ok) {
        argumentStats = await res.json();
    } else {
        console.error(`[load] arguments/stats fetch failed: returned ${res.status}`);
    }
} catch (err) {
    console.error('[load] arguments/stats fetch threw:', err instanceof Error ? err.message : String(err));
}
```
Repeat this exact shape for `/api/admin/people/stats`, `/api/admin/jobs/stats`, `/api/admin/utterances/count`, `/api/admin/arguments/stats` (recent drafts sub-list — or fold into the same call if the endpoint returns both stats + recent_drafts in one payload, an implementation detail left to the planner), `/api/admin/people/stats` (incomplete people top-5), and the tenure-gap-justices endpoint. **No `Promise.all`** — sequential awaits only, matching the zero-precedent finding in RESEARCH.md.

**Failed-value convention (copy from UI-SPEC.md's "Load-failure state" table, not from any existing code — this is new copy-contract territory):** on fetch failure, stat card values must render as the string `"N/A"` in the Svelte template (not a bare `0`) — the `load()` function itself should return a sentinel (e.g. `null`) for a failed count so `+page.svelte` can distinguish "loaded and genuinely zero" from "failed to load" and render `"N/A"` accordingly; needs-attention sub-lists degrade to `[]` (empty, using normal empty-state copy) per the same table.

---

### `app/src/routes/admin/+page.svelte` (rewritten)

**Analog:** current placeholder file (its own header/`<main>` structure, lines 1-43) for the page shell; `app/src/routes/admin/pipeline/[job_id]/+page.svelte`'s card composition for how existing pages assemble multiple data-driven sections (not excerpted here — reuse the header/`<main>` wrapper shown below, then compose `StatCard.svelte` instances + inline Needs Attention markup per UI-SPEC.md "Layout & Component Notes").

**Page shell to keep (copy from lines 8-38 of the current placeholder, just replace the inner content div's contents):**
```svelte
<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0; line-height: 1.2;">
			Admin
		</h1>
	</header>
	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		<!-- D-09: Needs Attention section FIRST, then stat card grid, then placeholder card -->
	</div>
</main>
```

**Svelte 5 runes constraint (project-wide, CLAUDE.md):** use `let { data } = $props();` to receive `load()`'s return value — no `export let data` legacy syntax anywhere in this file.

---

### `app/src/lib/components/StatCard.svelte` (NEW — no analog, first shared card component)

**Source of shape:** RESEARCH.md Pattern 2 (verbatim recommendation, already vetted by gsd-phase-researcher and gsd-ui-checker):
```svelte
<script lang="ts">
	let { title, children } = $props();
</script>
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">{title}</h2>
	{@render children()}
</div>
```
Per-card breakdown content (Arguments' 3 sub-links, Utterances' single number, etc.) is passed as the `children` snippet from `+page.svelte` — do not try to make StatCard itself branch on card type.

---

### Web Traffic placeholder card (inline markup in `+page.svelte`, NOT a separate component — no analog, first placeholder-card pattern)

**Source of shape:** RESEARCH.md Pattern 3 / UI-SPEC.md "Layout & Component Notes" (verbatim, already checker-approved):
```svelte
<div style="border: 1px dashed #334155; border-radius: 8px; padding: 24px; margin-top: 48px; opacity: 0.7;">
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">Web Traffic</h2>
	<p style="font-size: 14px; color: #94a3b8; margin: 0;">Coming soon</p>
</div>
```
No icon (D-11 discretion resolved by UI-SPEC.md: "skip the optional icon entirely"). Never placed in the same grid row as the 4 real `StatCard` instances (D-12).

## Shared Patterns

### Sequential degrade-gracefully `load()` fetches
**Source:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (lines 82-214, repeated 6 times in that one file already)
**Apply to:** `app/src/routes/admin/+page.server.ts`'s new `load()` — every one of the ~4-7 new FastAPI calls (arguments/stats, people/stats, jobs/stats, utterances/count, plus Needs Attention top-5 lists) gets its own independent try/catch block with a safe zero/empty default. Never `Promise.all`.

### Router-level auth inheritance
**Source:** `api/routers/admin.py` lines 109-113 (`APIRouter(dependencies=[Depends(verify_admin_token)])`)
**Apply to:** All 4 new stats/count routes — no new auth code required, just add the route function under the existing `router`.

### Literal-route-before-`{id}`-route ordering
**Source:** `api/routers/admin.py` lines 856-873 (`check-duplicate` before `{argument_id}`)
**Apply to:** `/arguments/stats` (before `/arguments/{argument_id}` at line 876), `/people/stats` (before `/people/{person_id}` at line 656), `/jobs/stats` (before `/jobs/{job_id}` at line 339). This is a hard correctness requirement, not a style preference — misordering produces a silent 422.

### `.execution_options(synchronize_session=False)` on every UPDATE/DELETE
**Source:** every mutation function in `admin_people.py`, `admin_arguments.py`, `admin_jobs.py` (project-wide critical guard, CLAUDE.md-adjacent)
**Apply to:** N/A for this phase — Phase 28 introduces zero UPDATE/DELETE statements (pure read-aggregation only). Documented here only so the planner does not need to re-derive "is this phase mutation-free" — confirmed yes.

### COUNT-query safety (`scalar_one()` vs `scalar_one_or_none()`)
**Source:** `api/services/admin_jobs.py` lines 169-175 (comment: "COUNT queries always return a row — use scalar_one(), never scalar_one_or_none()")
**Apply to:** every new `func.count()` call in the 3 new stats service functions. `func.max()` (last_activity_at) must use `scalar_one_or_none()` instead, since MAX over zero rows is NULL, not a missing row.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/src/lib/components/StatCard.svelte` | component | request-response (presentation) | First shared admin card component in the codebase — every other admin page rolls its own inline card markup. RESEARCH.md Pattern 2 supplies the exact shape to use instead of a codebase analog. |
| Web Traffic placeholder markup | component | n/a (static) | First "coming soon" placeholder card anywhere in the admin UI. RESEARCH.md Pattern 3 / UI-SPEC.md supply the shape. |
| Needs Attention section markup (3 sub-lists + empty states) | component | request-response | No existing admin page has a capped top-5-with-"View all" list pattern; closest conceptual precedent (not a code analog) is the Resolve card's per-row rendering in `admin_people.list_resolve_rows_for_job` output, but that is backend row-shape, not frontend markup. Build directly from UI-SPEC.md's Copywriting Contract table (rows 101-115) and Layout & Component Notes section. |

## Metadata

**Analog search scope:** `api/services/admin_*.py`, `api/routers/admin.py`, `api/schemas/admin_*.py`, `app/src/routes/admin/**/*.{svelte,ts}`, `app/src/lib/components/` (confirmed empty of any existing card component)
**Files scanned:** `api/services/admin_people.py` (935 lines), `api/services/admin_arguments.py` (799 lines), `api/services/admin_jobs.py` (935 lines), `api/routers/admin.py` (route registration order via grep, plus 2 targeted excerpts), `api/schemas/admin_arguments.py` (header excerpt), `app/src/routes/admin/+page.svelte` (43 lines, full), `app/src/routes/admin/+page.server.ts` (17 lines, full), `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (586 lines, full)
**Pattern extraction date:** 2026-07-10
