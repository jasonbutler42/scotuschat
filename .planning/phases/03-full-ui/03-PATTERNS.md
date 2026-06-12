# Phase 3: Full UI - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 13 (8 new, 5 edited)
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `api/schemas/cases.py` | schema | request-response | `api/schemas/people.py` | exact |
| `api/services/cases.py` | service | CRUD | `api/services/arguments.py` | role-match |
| `api/routers/cases.py` | router | request-response | `api/routers/people.py` | exact |
| `api/main.py` (edit) | config | — | `api/main.py` (self) | self |
| `app/src/routes/cases/+page.server.ts` | route (server load) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | exact |
| `app/src/routes/cases/+page.svelte` | component (page) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | role-match |
| `app/src/routes/cases/[slug]/+page.server.ts` | route (server load) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | exact |
| `app/src/routes/cases/[slug]/+page.svelte` | component (page) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | role-match |
| `app/src/lib/components/SectionRail.svelte` | component | event-driven | `app/src/lib/components/StageDirection.svelte` (structure only) | partial |
| `app/src/lib/components/ChatBubble.svelte` (edit) | component | request-response | `app/src/lib/components/ChatBubble.svelte` (self) | self |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (edit) | component (page) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (self) | self |
| `app/src/routes/+layout.svelte` (edit) | layout | request-response | `app/src/routes/+layout.svelte` (self) | self |
| `tests/test_cases_api.py` | test | — | `tests/test_schema.py` | role-match |

---

## Pattern Assignments

### `api/schemas/cases.py` (schema, request-response)

**Analog:** `api/schemas/people.py`

**Full analog** (`api/schemas/people.py` lines 1–16):
```python
"""Pydantic v2 response models for the people API endpoint."""

from typing import Optional

from pydantic import BaseModel


class PersonResponse(BaseModel):
    """A resolved speaker — Justice or counsel."""

    id: int
    full_name: str
    role_name: Optional[str] = None  # None if person has no role assigned

    model_config = {"from_attributes": True}
```

**Pattern to copy:**
- Module docstring format: `"""Pydantic v2 response models for the [noun] API endpoint."""`
- Import block: `from typing import Optional` + `from pydantic import BaseModel` (add `import datetime` for `date` fields)
- `model_config = {"from_attributes": True}` on each item model that is serialized from ORM rows
- Wrapper/list model (`CaseListResponse`) does NOT need `from_attributes` — it wraps a plain list of dicts

**New schema shape to implement:**
```python
import datetime
from pydantic import BaseModel

class CaseItem(BaseModel):
    id: int
    slug: str
    case_name: str
    docket_number: str
    term_year: int
    argued_date: datetime.date
    argument_id: int

    model_config = {"from_attributes": True}

class CaseListResponse(BaseModel):
    cases: list[CaseItem]
```

---

### `api/services/cases.py` (service, CRUD)

**Analog:** `api/services/arguments.py`

**Module docstring pattern** (`api/services/arguments.py` lines 1–15):
```python
"""
Business logic for argument and utterance queries.

Responsibilities:
  - Fetch an Argument row by ID
  - ...

PIPE-11 policy:
  ...
"""
```

**Imports pattern** (`api/services/arguments.py` lines 17–20):
```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument, Case, CaseArgument, Person, PipelineRun, PipelineRunStatus, Role, Utterance
```

**Core CRUD + join pattern** (`api/services/arguments.py` lines 56–74):
```python
lead_case_result = await db.execute(
    select(Case)
    .join(CaseArgument, CaseArgument.case_id == Case.id)
    .where(
        CaseArgument.argument_id == argument_id,
        CaseArgument.is_lead == True,  # noqa: E712 — SQLAlchemy requires == True
    )
)
lead_case = lead_case_result.scalar_one_or_none()
```

**Return dict pattern** (`api/services/arguments.py` lines 124–133):
```python
return {
    "argument": {
        "argument_id": argument.id,
        "case_name": lead_case.case_name,
        "docket_number": lead_case.docket_number,
        "argued_date": argument.argued_date,
        "question_number": argument.question_number,
    },
    "utterances": utterances,
}
```

**New service implementation pattern** (copy join style from arguments.py, adapted):
```python
async def get_cases(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Case, Argument)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .join(Argument, CaseArgument.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712
        .order_by(Argument.argued_date.desc())
    )
    rows = result.all()
    return [
        {
            "id": case.id,
            "slug": case.slug,
            "case_name": case.case_name,
            "docket_number": case.docket_number,
            "term_year": case.term_year,
            "argued_date": argument.argued_date,
            "argument_id": argument.id,
        }
        for case, argument in rows
    ]
```

**Key model names** (confirmed from `api/models/models.py`):
- `Case` — fields: `id`, `docket_number`, `case_name`, `term_year`, `slug`
- `Argument` — fields: `id`, `argued_date`, `question_number`
- `CaseArgument` — join table fields: `case_id`, `argument_id`, `is_lead`

---

### `api/routers/cases.py` (router, request-response)

**Analog:** `api/routers/people.py` (exact match — same pattern)

**Full analog** (`api/routers/people.py` lines 1–37):
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
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """..."""
    result = await people_service.get_person_by_id(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return result
```

**Adaptation for cases router:**
- No `HTTPException` needed — `GET /cases` returns an empty list when no cases exist (not 404)
- Remove `HTTPException` import if not used
- Endpoint path is `""` (not `"/{id}"`) — GET /cases is a collection endpoint
- `response_model=CaseListResponse`; return `CaseListResponse(cases=results)`
- Note from `api/routers/arguments.py` line 18: `router = APIRouter(prefix="/arguments", tags=["arguments"])` — follow same prefix/tag convention: `prefix="/cases", tags=["cases"]`

**New router skeleton:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.cases import CaseListResponse
from api.services import cases as cases_service

router = APIRouter(prefix="/cases", tags=["cases"])

@router.get("", response_model=CaseListResponse)
async def get_cases(
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """Return all loaded cases with metadata for the case list page."""
    results = await cases_service.get_cases(db)
    return CaseListResponse(cases=results)
```

---

### `api/main.py` (edit — router registration)

**Source:** `api/main.py` lines 1–31 (self — read as-is)

**Current state** (lines 13–24):
```python
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
```

**Edit: add two lines** — one import and one `include_router` call, following the exact style of the existing two routers:
```python
# Add to import block (line 15, after people_router):
from api.routers import cases as cases_router

# Add to include_router block (line 25, after people_router):
app.include_router(cases_router.router)
```

---

### `app/src/routes/cases/+page.server.ts` (server load, request-response)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` (exact match)

**Full analog** (lines 1–14):
```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
	if (!res.ok) throw error(res.status, 'Failed to load argument');
	const data = await res.json();
	return {
		utterances: data.utterances,
		argument: data.argument,
		argument_id: parseInt(params.id)
	};
};
```

**Adaptation for `/cases` load:**
- No `params` needed — `/cases` is not a dynamic route
- URL: `${FASTAPI_BASE_URL}/cases`
- Return `{ cases: data.cases }`
- Error message: `'Failed to load cases'`

```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	return { cases: data.cases };
};
```

---

### `app/src/routes/cases/[slug]/+page.server.ts` (server load, request-response)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` (exact match)

**Pattern to copy** (same as above — see full analog there).

**Adaptation for `/cases/[slug]` load:**
- `params.slug` used in this route (not `params.id`)
- No direct FastAPI endpoint for `GET /cases/{slug}` exists yet — the slug page derives its data from the cases list already passed via parent load, OR re-fetches `GET /cases` and filters by slug client-side in the load function
- **Recommended approach:** Re-fetch `GET /cases`, filter to the matching slug in the load function, extract the single matching case + its `argument_id`; if exactly one argument, redirect via `redirect(307, ...)` from `@sveltejs/kit`

```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	const matches = data.cases.filter((c: { slug: string }) => c.slug === params.slug);
	if (matches.length === 0) throw error(404, 'Case not found');
	if (matches.length === 1) {
		redirect(307, `/cases/${params.slug}/arguments/${matches[0].argument_id}`);
	}
	// Multi-argument case: return list for picker page
	return { slug: params.slug, arguments: matches };
};
```

**`redirect` import:** `import { error, redirect } from '@sveltejs/kit'` — note the existing analog only imports `error`; add `redirect` for this route.

---

### `app/src/routes/cases/+page.svelte` (page component, request-response)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`

**Svelte 5 Runes pattern** (lines 1–5):
```svelte
<script lang="ts">
	let { data } = $props();
	// computed values use $derived
</script>
```

**Page shell pattern** (lines 25–30):
```svelte
<div style="background-color: #0f1117; min-height: 100vh;">
	<!-- header bar: #1e293b, border-bottom: #334155, padding: 16px 24px -->
	<div style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		...
	</div>
	<!-- content area: max-width centered, padding: 48px 24px -->
	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		...
	</div>
</div>
```

**Typography constants** (from palette in `+page.svelte` heading):
- `h1`: `font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 4px 0`
- subline: `font-size: 14px; color: #94a3b8`
- body text: `font-size: 16px; color: #e2e8f0; line-height: 1.6`

**Empty state pattern** (`+page.svelte` lines 70–79):
```svelte
{#if !data.utterances || data.utterances.length === 0}
	<p style="text-align: center; color: #94a3b8; font-size: 16px;">
		No utterances found for this argument.
	</p>
{:else}
	...
{/if}
```

**`formatDate` function** (`+page.svelte` lines 14–21) — copy verbatim for any date display:
```typescript
function formatDate(dateStr: string): string {
	const date = new Date(dateStr + 'T00:00:00');
	return new Intl.DateTimeFormat('en-US', {
		month: 'long',
		day: 'numeric',
		year: 'numeric'
	}).format(date);
}
```

**Case list `{#each}` pattern** — adapt from utterance `{#each}`:
```svelte
{#each data.cases as c (c.id)}
	<a href="/cases/{c.slug}" style="...">
		{c.case_name}
		<span style="color: #94a3b8;">No. {c.docket_number} · Argued {formatDate(c.argued_date)}</span>
	</a>
{/each}
```

---

### `app/src/routes/cases/[slug]/+page.svelte` (page component, request-response)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`

This page only renders for multi-argument cases (Phase 3: will rarely be reached since the server load redirects single-argument cases). Copy the same shell pattern, display the `data.arguments` list with links to `/cases/{slug}/arguments/{argument_id}`.

**`$props()` pattern** (line 5): `let { data } = $props();`

**Page shell** and **typography constants**: same as case list page above.

---

### `app/src/lib/components/SectionRail.svelte` (component, event-driven)

**Analog for structure:** `app/src/lib/components/StageDirection.svelte` (props + inline styles)

**StageDirection structure** (lines 1–32 — full file):
```svelte
<script lang="ts">
	let { utterance } = $props();
</script>

<div style="
	background-color: #1e293b;
	border-left: 3px solid #d97706;
	...
">
	<p style="font-size: 14px; color: #fcd34d; ...">
		{utterance.text}
	</p>
</div>
```

**Key patterns to copy from StageDirection:**
- Single `$props()` destructure at top of `<script>`
- All styles inline (no `<style>` block) — consistent with rest of codebase
- No imports from external libraries

**SectionRail-specific patterns** (no codebase analog — use RESEARCH.md patterns):
- `import { browser } from '$app/environment'` — REQUIRED SSR guard
- `$state<string | null>` for `activeSection`
- `$effect` with `if (!browser) return` as first line
- IntersectionObserver cleanup via `return () => observers.forEach(o => o.disconnect())`
- `document.getElementById(anchorId)` (not `bind:this` — avoids svelte#12731)
- `onclick` (not `on:click`) — Svelte 5 event syntax

**Color constants for active/inactive states** (from established palette):
- Active: `background-color: #1e293b; color: #e2e8f0; border-left: 3px solid #93c5fd`
- Inactive: `background-color: transparent; color: #94a3b8; border-left: 3px solid transparent`

---

### `app/src/lib/components/ChatBubble.svelte` (edit — avatar + alignment flip)

**Source:** `app/src/lib/components/ChatBubble.svelte` (self — full file is 73 lines)

**Current full file** for reference:

Lines 1–9 (`<script>`):
```svelte
<script lang="ts">
	let { utterance } = $props();

	const isBench = utterance.side === 'BENCH';
	// BENCH: right-aligned; ADVOCATE or UNKNOWN: left-aligned
	const labelColor = isBench ? '#94a3b8' : '#93c5fd';
	const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
	const displayRole = utterance.speaker_role ?? null;
</script>
```

Lines 11–16 (outer flex div — alignment):
```svelte
<div
	style="
		display: flex;
		justify-content: {isBench ? 'flex-end' : 'flex-start'};
	"
>
```

Lines 29–57 (bubble header row):
```svelte
<div style="display: flex; align-items: center; gap: 4px; margin-bottom: 8px;">
	<span style="font-size: 13px; color: #475569; font-weight: 400; padding-right: 4px;">
		{utterance.sequence}
	</span>
	<span style="font-size: 13px; font-weight: 600; color: {labelColor};">
		{displayName}
	</span>{#if displayRole}<span style="font-size: 11px; color: #475569;">{displayRole}</span>{/if}
</div>
```

**Edit 1 — D-05 alignment flip** (line 14): change `flex-end` ↔ `flex-start`:
```svelte
justify-content: {isBench ? 'flex-start' : 'flex-end'};
```

**Edit 2 — D-07/D-08 avatar circle** — add to `<script>` block (after `displayRole`):
```typescript
const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
const initials = (() => {
	const parts = displayName.trim().split(/\s+/);
	if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
	return displayName.slice(0, 2).toUpperCase();
})();
```

**Edit 3 — insert avatar circle** into the bubble header row `<div>` (before the sequence `<span>`):
```svelte
<div style="
	width: 32px; height: 32px; border-radius: 50%;
	background-color: {avatarBg};
	display: flex; align-items: center; justify-content: center;
	font-size: 12px; font-weight: 600; color: #0f1117;
	flex-shrink: 0;
">{initials}</div>
```

**Edit 4 — increase gap** on the header row from `gap: 4px` to `gap: 8px` to accommodate the avatar circle.

---

### `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (edit — two-column layout + roster + section anchors)

**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (self — 99 lines)

**Current layout structure** (lines 25–99):
```
<div bg=#0f1117>                         ← page bg
  <div bg=#1e293b>                       ← header bar (full width)
    <div max-width: 860px>               ← header inner
      <h1> case_name </h1>
      <p> docket · date · question </p>
    </div>
  </div>
  <div max-width: 860px; margin: 0 auto> ← single chat column
    {#each utterances}...{/each}
  </div>
</div>
```

**New layout structure** — replace the single-column with CSS Grid:
```svelte
<!-- outer: page bg, full-width header stays the same -->
<div style="background-color: #0f1117; min-height: 100vh;">
  <!-- header bar: EXTEND with roster below existing subline -->
  <div style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
    <!-- existing: case name + subline (no change to those elements) -->
    <!-- NEW: two-column roster below subline -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
      <div><!-- bench names --></div>
      <div><!-- advocate names --></div>
    </div>
  </div>

  <!-- two-column content: sidebar + chat -->
  <div style="display: grid; grid-template-columns: 180px 1fr; max-width: 1200px; margin: 0 auto;">
    <!-- nav rail column -->
    <div>
      <SectionRail sections={sectionAnchors} />
    </div>
    <!-- chat column -->
    <div style="padding: 48px 24px;">
      {#each utterances}...{/each}
    </div>
  </div>
</div>
```

**New `<script>` additions** (after `formatDate`):
```typescript
import SectionRail from '$lib/components/SectionRail.svelte';

// D-12: Roster derived client-side from utterances
const roster = $derived.by(() => {
	const seen = new Set<string>();
	const bench: { name: string; role: string | null }[] = [];
	const advocates: { name: string; role: string | null }[] = [];
	for (const u of data.utterances) {
		if (u.is_stage_direction) continue;
		const key = u.speaker_name ?? u.raw_speaker_label ?? '';
		if (!key || seen.has(key)) continue;
		seen.add(key);
		const entry = { name: key, role: u.speaker_role ?? null };
		if (u.side === 'BENCH') bench.push(entry);
		else advocates.push(entry);
	}
	return { bench, advocates };
});

// D-04: Section anchors derived from section_hint — lowercase values confirmed
const sectionAnchors = $derived(
	data.utterances
		.filter((u: { section_hint: string | null; is_stage_direction: boolean }) =>
			u.section_hint !== null && !u.is_stage_direction
		)
		.map((u: { section_hint: string; sequence: number }) => ({
			hint: u.section_hint,
			label: u.section_hint.charAt(0).toUpperCase() + u.section_hint.slice(1),
			anchorId: `section-${u.section_hint}-${u.sequence}`,
			sequence: u.sequence,
		}))
);
```

**Section anchor `id` attribute** — in the `{#each}` loop, add `id` to the first utterance of each section. Pattern: the utterance has `section_hint !== null`, so add `id="section-{utterance.section_hint}-{utterance.sequence}"` to its wrapper `<div>`.

**Mobile breakpoint** (D-03): `@media (max-width: 768px)` — since all styles are inline, use conditional inline style or a `<style>` block scoped to this page only.

---

### `app/src/routes/+layout.svelte` (edit — nav link replacement)

**Source:** `app/src/routes/+layout.svelte` (self — 32 lines, full file read)

**Current hard-coded link** (lines 19–27):
```svelte
<a
	href="/cases/obergefell-v-hodges/arguments/3"
	style="
		font-size: 13px;
		color: #93c5fd;
		text-decoration: none;
	"
>
	Obergefell v. Hodges
</a>
```

**Edit:** Replace the `<a>` href and text:
```svelte
<a
	href="/cases"
	style="
		font-size: 13px;
		color: #93c5fd;
		text-decoration: none;
	"
>
	Cases
</a>
```

All other layout structure (nav bar styles, `{@render children()}`, `$props()`) remains unchanged.

---

### `tests/test_cases_api.py` (test, static analysis)

**Analog:** `tests/test_schema.py`

**Module structure pattern** (`tests/test_schema.py` lines 1–29):
```python
"""
Smoke tests for the database schema.

These tests verify:
1. ...
2. ...

Tests 1 and 2 require a running PostgreSQL instance with DATABASE_URL set.
Test N (test_no_create_all) is a static analysis check — runs always.

Run with:
    pytest tests/test_schema.py -x -q
"""

import os
import pathlib

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "")
requires_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping database connectivity tests",
)
```

**Static analysis test pattern** (`tests/test_schema.py` lines 122–151):
```python
def test_no_create_all_in_codebase():
    """..."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs = [
        os.path.join(project_root, "api"),
        os.path.join(project_root, "alembic"),
        os.path.join(project_root, "pipeline"),
    ]
    offending_files = []
    for search_dir in search_dirs:
        for py_file in pathlib.Path(search_dir).rglob("*.py"):
            try:
                if "create_all" in py_file.read_text(encoding="utf-8", errors="ignore"):
                    offending_files.append(str(py_file))
            except OSError:
                pass
    assert not offending_files, (
        "Found 'create_all' in production source files — ...\n"
        + "\n".join(f"  {f}" for f in offending_files)
    )
```

**New tests to implement** (mirroring the static analysis pattern from test_schema.py):
```python
def test_cases_router_registered_in_main():
    """cases router must be registered in api/main.py."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = pathlib.Path(project_root) / "api" / "main.py"
    content = main_py.read_text(encoding="utf-8")
    assert "cases" in content, "cases router not imported or registered in api/main.py"
    assert "cases_router" in content or "cases as cases_router" in content

def test_cases_router_has_get_cases_path():
    """api/routers/cases.py must define a GET route."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cases_router = pathlib.Path(project_root) / "api" / "routers" / "cases.py"
    content = cases_router.read_text(encoding="utf-8")
    assert "@router.get" in content, "No GET route defined in cases router"

def test_no_create_all_in_cases_router():
    """api/routers/cases.py must not call Base.metadata.create_all."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cases_router = pathlib.Path(project_root) / "api" / "routers" / "cases.py"
    content = cases_router.read_text(encoding="utf-8")
    assert "create_all" not in content

def test_fastapi_base_url_not_public_in_cases_pages():
    """No SvelteKit cases route must use PUBLIC_FASTAPI_BASE_URL."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cases_dir = pathlib.Path(project_root) / "app" / "src" / "routes" / "cases"
    for ts_file in cases_dir.rglob("*.ts"):
        content = ts_file.read_text(encoding="utf-8", errors="ignore")
        assert "PUBLIC_FASTAPI_BASE_URL" not in content, (
            f"PUBLIC_ prefix found in {ts_file} — violates CLAUDE.md constraint"
        )
```

---

## Shared Patterns

### Svelte 5 Runes — Props
**Source:** `app/src/lib/components/ChatBubble.svelte` line 2; `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` line 5
**Apply to:** All Svelte components and page files in Phase 3
```svelte
let { data } = $props();           // pages
let { utterance } = $props();      // single-prop components
let { sections } = $props();       // SectionRail
```
Never use `export let`. No `$:` reactive blocks — use `$derived` instead.

### FastAPI 3-Layer — Dependency Injection
**Source:** `api/routers/people.py` lines 9–10 and 22; `api/routers/arguments.py` lines 22–25
**Apply to:** `api/routers/cases.py`
```python
from api.core.database import get_db
# ...
async def handler(db: AsyncSession = Depends(get_db)) -> ResponseModel:
```

### SvelteKit SSR Load — Private Env Var
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` lines 1–2
**Apply to:** All new `+page.server.ts` files
```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
```
Never `PUBLIC_FASTAPI_BASE_URL`. Always `$env/static/private`.

### Error Handling — HTTP Errors
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` line 7; `api/routers/people.py` line 35
**Apply to:** All server load functions and routers

Frontend pattern:
```typescript
if (!res.ok) throw error(res.status, 'Failed to load cases');
```
Backend pattern:
```python
if result is None:
    raise HTTPException(status_code=404, detail="Not found")
```

### Dark Palette — Color Constants
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` inline styles; `app/src/lib/components/ChatBubble.svelte`
**Apply to:** All Svelte files in Phase 3

| Token | Value | Usage |
|-------|-------|-------|
| Page bg | `#0f1117` | `background-color` on page root |
| Surface | `#1e293b` | Cards, header bar, bubble bg |
| Border | `#334155` | All `border` colors |
| Body text | `#e2e8f0` | Primary text, `h1` |
| Muted / bench | `#94a3b8` | Secondary text, bench label, bench avatar bg |
| Advocate | `#93c5fd` | Advocate label, advocate avatar bg, active rail accent |
| Dim | `#475569` | Sequence numbers, role text |
| Avatar text | `#0f1117` | Initials on avatar circles |

### SQLAlchemy Async — Query Pattern
**Source:** `api/services/arguments.py` lines 56–64; `api/services/people.py` lines 28–37
**Apply to:** `api/services/cases.py`
```python
result = await db.execute(
    select(ModelA, ModelB)
    .join(JoinTable, JoinTable.a_id == ModelA.id)
    .join(ModelB, JoinTable.b_id == ModelB.id)
    .where(JoinTable.flag == True)  # noqa: E712
    .order_by(ModelB.field.desc())
)
rows = result.all()
return [{"field": a.field, ...} for a, b in rows]
```

### Pydantic Schema — `from_attributes`
**Source:** `api/schemas/people.py` line 15; `api/schemas/utterance.py` line 38
**Apply to:** `api/schemas/cases.py` `CaseItem`
```python
model_config = {"from_attributes": True}
```
Include on every model that is serialized from ORM rows or row dicts. The wrapper collection model (`CaseListResponse`) does not need it.

---

## No Analog Found

No files in Phase 3 are entirely without analog. `SectionRail.svelte` has a structural partial match (`StageDirection.svelte`) but no scroll-spy analog exists in the codebase — use the RESEARCH.md Pattern 4 (`$effect` + IntersectionObserver) for that logic.

---

## Metadata

**Analog search scope:** `api/routers/`, `api/services/`, `api/schemas/`, `api/main.py`, `app/src/routes/`, `app/src/lib/components/`, `tests/`
**Files scanned:** 13 source files read directly
**Pattern extraction date:** 2026-06-12
