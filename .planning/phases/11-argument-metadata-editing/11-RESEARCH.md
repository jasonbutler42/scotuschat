# Phase 11: Argument Metadata Editing - Research

**Researched:** 2026-06-22
**Domain:** SvelteKit admin forms, FastAPI PATCH pattern, Alembic migration, slug re-derivation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** New `/admin/arguments` list page showing all arguments (pending, resolved, published) with a status badge, sorted by `argued_date DESC`. Each row includes a publish/unpublish toggle.
- **D-02:** New `/admin/arguments/[id]` edit page. Editable fields: lead case's `case_name`, lead case's `docket_number`, and `argument.argued_date`. Always editable regardless of state.
- **D-03:** Job detail page gets a top-section argument metadata preview (case title, docket, argued date, current status) with an "Edit argument metadata" link. Preview appears once `argument_id` is set on the job.
- **D-04:** When `job.status === 'completed' AND published_at IS NULL`, the job detail page displays a "Ready to publish" CTA linking to `/admin/arguments/[argument_id]`.
- **D-05:** New `published_at` column (`TIMESTAMP WITH TIME ZONE`, nullable) added to `arguments` table via a new Alembic migration. `resolved_at` is preserved with its existing meaning.
- **D-06:** Public visibility gate changes: `Argument.resolved_at.isnot(None)` → `Argument.published_at.isnot(None)` in `api/services/cases.py` `get_cases()`.
- **D-07:** Publish only when `resolved_at IS NOT NULL AND published_at IS NULL`. Unpublish always available when `published_at IS NOT NULL`. No gate prevents editing at any state.
- **D-08:** Publish / Unpublish control in two places: toggle on each list row, and button on the edit page.
- **D-09:** ARG-02 (read-only after `resolved_at`) is dropped. The publish model replaces it.
- **D-10:** Editor shows title and docket for the lead case only (`is_lead = true`). Non-lead dockets shown as read-only reference list below editable fields.
- **D-11:** When `case_name` is edited and `published_at IS NULL`, slug re-derives from the new `case_name` using `_derive_slug()` logic. When `published_at IS NOT NULL`, slug is frozen — only `case_name` updates. Slug collision (unique constraint) surfaces as a 422 with a user-facing message.
- **D-12:** Admin TopNav gains an "Arguments" link: `SCOTUS CHAT | Pipeline Runner | Arguments | People Editor | [spacer] Log out`.

### Claude's Discretion

- Visual badge styling for Pending / Resolved / Published states — follow established admin dark theme tokens; pick distinct but not loud colors
- Label wording for publish/unpublish action
- Whether the list-row publish control is a button or a styled toggle
- Date display format on the arguments list
- Whether the argument edit page heading shows the case title or a generic label

### Deferred Ideas (OUT OF SCOPE)

- Unpublish → re-resolve workflow
- Bulk publish from the arguments list
- Post-resolve utterance or speaker editing
- ADV-01 (advocate firm/organization)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARG-01 | Operator can view and edit a pending argument's case title, docket number, and argued date from the admin area | D-02 edit page + D-01 list page; PATCH endpoint pattern mirrors `update_person()`; `published_at` migration enables publish gate |
| ARG-02 | Argument metadata fields are read-only after `resolved_at` is set | D-09 **drops** this requirement — publish model replaces it; always-editable is the new behavior |
</phase_requirements>

---

## Summary

Phase 11 is a full-stack CRUD feature delivered in three layers: a new Alembic migration (0007), new FastAPI endpoints in `admin.py` backed by a new `admin_arguments.py` service, and two new SvelteKit route groups under `/admin/arguments`. The phase also makes targeted edits to four existing files: `api/models/models.py` (add `published_at` column), `api/services/cases.py` (swap visibility gate), `api/schemas/admin_jobs.py` (extend `AdminJobResponse`), and the job detail page pair (`+page.svelte` / `+page.server.ts`) to add the argument preview section and "Ready to publish" CTA.

The dominant patterns are identical to Phase 9 (People Editor): a load function that fetches one record by ID, a `+page.svelte` with `use:enhance` on all forms, named form actions for `save` / `publish` / `unpublish`, and a service layer that validates before writing. The only new complexity is slug re-derivation with collision detection (D-11) and the two-place publish/unpublish control (D-08).

No new npm packages or Python packages are required. All UI follows the established admin inline-style pattern documented in `11-UI-SPEC.md`. The `_derive_slug()` function in `pipeline/commands/ingest.py` (line 82) is the canonical slug logic — the service layer imports or replicates it.

**Primary recommendation:** Model `admin_arguments.py` exactly on `admin_people.py`. The shape of `update_argument()` mirrors `update_person()`: load by ID, apply field changes, commit, return detail dict. The only divergence is slug re-derivation gated on `published_at IS NULL`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| List all arguments with status | API / Backend | Frontend Server (SSR) | Service query joins arguments + cases; load function fetches and passes data |
| Edit argument fields (title, docket, date) | API / Backend | Frontend Server (SSR) | PATCH endpoint owns validation, slug re-derivation, write; form action proxies |
| Publish / Unpublish control | API / Backend | Frontend Server (SSR) | Backend stamps `published_at`; form action calls endpoint; no client-side state |
| Public visibility gate | Database / Storage | API / Backend | Filter `published_at IS NOT NULL` in SQLAlchemy query |
| Job detail argument preview | Frontend Server (SSR) | API / Backend | Extend existing load function to join argument + case metadata; no new page |
| Slug re-derivation | API / Backend | — | Business rule belongs in service layer, not in UI; pipeline logic reused |
| Slug collision detection | API / Backend | — | Must query DB for duplicate before write; 422 surfaced as form error |
| Status badge rendering | Browser / Client | — | Pure display logic derived from `resolved_at` / `published_at` values |
| TopNav "Arguments" link | Browser / Client | — | Static link addition to existing component |

---

## Standard Stack

### Core

No new packages. All dependencies already installed.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit | 2.x | Admin pages, form actions, server load | Project standard (CLAUDE.md) |
| Svelte 5 (Runes) | 5.x | `$state`, `$derived`, `$props`, `$effect` | Project standard — no legacy stores |
| FastAPI | 0.115+ | New argument CRUD endpoints | Project standard |
| Pydantic v2 | 2.x | Request/response schemas | Project standard |
| SQLAlchemy 2.0 async | 2.x | ORM queries and updates | Project standard |
| Alembic | latest | DDL migration (add `published_at`) | Sole DDL authority per CLAUDE.md |

### No New Packages Required

[VERIFIED: codebase] — All tooling already present. No npm install or pip install steps needed in this phase.

### Installation

None required.

---

## Package Legitimacy Audit

Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
  │
  ├─ GET /admin/arguments
  │    └─ +page.server.ts load()
  │         └─ GET /api/admin/arguments ──► admin.py get_arguments()
  │                                              └─ admin_arguments.list_arguments(db)
  │                                                   SELECT arguments JOIN case_arguments JOIN cases
  │                                                   WHERE is_lead=True ORDER BY argued_date DESC
  │
  ├─ POST /admin/arguments?/publish (row toggle)
  │    └─ +page.server.ts publish()
  │         └─ POST /api/admin/arguments/{id}/publish ──► stamp published_at=now()
  │
  ├─ GET /admin/arguments/[id]
  │    └─ +page.server.ts load()
  │         └─ GET /api/admin/arguments/{id} ──► admin_arguments.get_argument_detail(db, id)
  │                                                  JOIN cases (lead + non-lead), check published_at
  │
  ├─ POST /admin/arguments/[id]?/save
  │    └─ +page.server.ts save()
  │         └─ PATCH /api/admin/arguments/{id} ──► admin_arguments.update_argument(db, id, body)
  │                                                   if published_at IS NULL: re-derive slug
  │                                                   check slug collision → 422 if conflict
  │                                                   UPDATE cases SET case_name, docket_number, slug
  │                                                   UPDATE arguments SET argued_date
  │
  ├─ POST /admin/arguments/[id]?/publish
  │    └─ POST /api/admin/arguments/{id}/publish ──► UPDATE arguments SET published_at=now()
  │
  ├─ POST /admin/arguments/[id]?/unpublish
  │    └─ POST /api/admin/arguments/{id}/unpublish ──► UPDATE arguments SET published_at=NULL
  │
  └─ GET /admin/pipeline/[job_id]  (existing page, extended)
       └─ +page.server.ts load()
            ├─ existing: GET /api/admin/jobs/{job_id}
            └─ new (when argument_id set): GET /api/admin/arguments/{argument_id}
                  → pass argument metadata to Svelte for preview card + CTA

Public visibility gate change (D-06):
  GET /api/cases ──► cases.py get_cases()
                          WHERE Argument.published_at.isnot(None)   ← was resolved_at
```

### Recommended Project Structure

```
api/
├── models/models.py               # ADD: published_at column to Argument
├── schemas/
│   ├── admin_jobs.py              # EXTEND: AdminJobResponse with argument metadata
│   └── admin_arguments.py         # NEW: ArgumentDetail, ArgumentUpdate, ArgumentListItem schemas
├── services/
│   ├── admin_arguments.py         # NEW: list_arguments(), get_argument_detail(), update_argument(),
│   │                              #      publish_argument(), unpublish_argument()
│   └── cases.py                   # EDIT: swap resolved_at → published_at filter
├── routers/
│   └── admin.py                   # ADD: GET/PATCH /arguments, GET/PATCH /arguments/{id},
│                                   #      POST /arguments/{id}/publish,
│                                   #      POST /arguments/{id}/unpublish
alembic/versions/
└── 0007_add_published_at.py       # NEW: add published_at to arguments

app/src/routes/admin/
├── arguments/
│   ├── +page.svelte               # NEW: list page
│   ├── +page.server.ts            # NEW: load + publish/unpublish actions
│   └── [id]/
│       ├── +page.svelte           # NEW: edit page
│       └── +page.server.ts        # NEW: load + save/publish/unpublish actions
├── pipeline/[job_id]/
│   ├── +page.svelte               # EXTEND: argument preview card + "Ready to publish" CTA
│   └── +page.server.ts            # EXTEND: fetch argument metadata when argument_id set
└── lib/components/
    └── TopNav.svelte              # EXTEND: add "Arguments" link to admin variant
```

### Pattern 1: SvelteKit Named Form Actions + use:enhance

Identical to Phase 9 people editor. Every mutation goes through a named form action; `use:enhance` provides progressive enhancement.

```typescript
// Source: app/src/routes/admin/people/[id]/+page.server.ts (Phase 9 canonical pattern)
export const actions: Actions = {
    save: async ({ request, params, fetch }) => {
        const formData = await request.formData();
        // ... extract fields, validate, call FastAPI PATCH
        // On success: throw redirect(303, `/admin/arguments/${params.id}`)
        // On error: return fail(422, { error: '...' })
    },
    publish: async ({ request, params, fetch }) => {
        // POST /api/admin/arguments/{id}/publish
        // On success: throw redirect(303, `/admin/arguments/${params.id}`)
    },
    unpublish: async ({ request, params, fetch }) => {
        // POST /api/admin/arguments/{id}/unpublish
        // On success: throw redirect(303, `/admin/arguments/${params.id}`)
    },
};
```

```svelte
<!-- Source: established pattern from people editor and pipeline pages -->
<form method="POST" action="?/save" use:enhance={() => {
    saving = true;
    return async ({ result, update }) => {
        saving = false;
        await update({ reset: false });
    };
}}>
```

**Key rule:** `use:enhance` with `reset: false` on save so form fields keep their values on a 422 failure. The redirect(303) on success re-runs the load function, returning fresh data.

### Pattern 2: FastAPI Service Layer — update_argument()

Mirrors `update_person()` in `admin_people.py`. Load row, apply validated changes, commit, return fresh detail dict.

```python
# Source: api/services/admin_people.py update_person() — adapted for arguments
async def update_argument(db: AsyncSession, argument_id: int, body: ArgumentUpdate) -> dict | None:
    # 1. Load argument row
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    # 2. Load lead case via CaseArgument.is_lead == True
    lead_result = await db.execute(
        select(Case)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(CaseArgument.argument_id == argument_id, CaseArgument.is_lead == True)
    )
    lead_case = lead_result.scalar_one_or_none()
    if lead_case is None:
        raise ValueError("No lead case found for this argument")

    # 3. Apply argued_date
    if body.argued_date is not None:
        argument.argued_date = datetime.date.fromisoformat(body.argued_date)

    # 4. Apply case_name + docket_number to lead case
    if body.case_name is not None:
        lead_case.case_name = body.case_name.strip()
        # Slug re-derivation (D-11): only when not yet published
        if argument.published_at is None:
            new_slug = _derive_slug(lead_case.case_name)
            # Collision check: any other case with this slug
            collision = await db.execute(
                select(Case).where(Case.slug == new_slug, Case.id != lead_case.id)
            )
            if collision.scalar_one_or_none() is not None:
                raise ValueError("slug_collision")
            lead_case.slug = new_slug
        # else: published — freeze slug, only update case_name display

    if body.docket_number is not None:
        lead_case.docket_number = body.docket_number.strip()

    await db.commit()
    return await get_argument_detail(db, argument_id)
```

### Pattern 3: Alembic Migration (0007)

Chains from `down_revision = "0006"`.

```python
# Source: alembic/versions/0006_add_structured_name_fields.py — structural pattern
revision: str = "0007"
down_revision: str = "0006"

def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("arguments", "published_at")
```

**Constraints:** `Alembic is the sole DDL authority` (CLAUDE.md). Never call `Base.metadata.create_all`. Never add the column directly in `models.py` without a migration. After writing the migration, add the `published_at` column to the `Argument` ORM class in `models.py` (`Column(DateTime(timezone=True), nullable=True)`).

### Pattern 4: get_cases() Visibility Gate Swap (D-06)

```python
# Source: api/services/cases.py (current — line 34)
# BEFORE:
.where(Argument.resolved_at.isnot(None))
# AFTER:
.where(Argument.published_at.isnot(None))
```

Single-line change. The comment on that line should also update: `# hide unpublished arguments`.

### Pattern 5: Extending AdminJobResponse for Argument Preview (D-03)

The job detail load function currently returns only `job` (which has `argument_id`). To render the preview card without a second fetch, extend `AdminJobResponse` to carry argument metadata — OR add a separate fetch of `/api/admin/arguments/{argument_id}` in the load function when `argument_id` is set.

The CONTEXT.md (canonical refs, admin_jobs.py) specifies: "extend `AdminJobResponse` with argument metadata" AND "extend the load function to pass argument metadata". The cleanest approach consistent with the existing pattern is a **separate fetch** in the load function (not embedding all argument fields in `AdminJobResponse` — that would bloat the jobs list endpoint for no reason). The load function already makes multiple fetches (people list, participants).

```typescript
// Source: app/src/routes/admin/pipeline/[job_id]/+page.server.ts (extension pattern)
let argument: ArgumentPreview | null = null;
if (job.argument_id != null) {
    try {
        const argRes = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/arguments/${job.argument_id}`,
            { headers: { 'X-Admin-Token': ADMIN_TOKEN } }
        );
        if (argRes.ok) argument = await argRes.json();
    } catch {
        // Non-critical — preview omitted if fetch fails; existing job view still renders
    }
}
return { job, people, peopleLoadError, participants, argument };
```

### Anti-Patterns to Avoid

- **Embedding argument metadata in AdminJobResponse:** Would bloat the list endpoint (`GET /api/admin/jobs`) for all 10 recent jobs, most of which don't need full argument detail. Use a separate fetch in the load function instead.
- **Writing `published_at` directly from the frontend:** The publish endpoint is a named FastAPI action, not a field in the PATCH body. `published_at` must never be in `ArgumentUpdate` — it is set only by `publish_argument()` and cleared only by `unpublish_argument()`.
- **Reading `published_at` state from Svelte client-side `$state`:** The post-publish state is server-controlled. After publish/unpublish, use `redirect(303, ...)` to re-run the load function — do not try to update a local `published_at` variable in Svelte.
- **Calling `Base.metadata.create_all`:** Forbidden by CLAUDE.md. Alembic only.
- **Importing `FASTAPI_BASE_URL` as a PUBLIC_ env var:** It must come from `$env/static/private`, never `$env/static/public`. Enforced by existing patterns in all `+page.server.ts` files.
- **Slug re-derivation in the Svelte layer:** The slug is server-only. Never expose the derived slug to the client or attempt to preview it. Only surface a collision error after the PATCH fails.
- **Checking `resolved_at` in any new publish gate logic (front or back):** The publish model uses `resolved_at` as the precondition (D-07), but the API should check `Argument.resolved_at IS NOT NULL` server-side before allowing publish — never trust a frontend boolean.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slug generation | Custom regex / transliteration | `_derive_slug()` from `pipeline/commands/ingest.py` | Already tested; edge cases handled (periods, commas, spaces); must match what ingest writes |
| Form progressive enhancement | Manual fetch() + JSON updates | `use:enhance` from `$app/forms` | SvelteKit's built-in; handles devalue serialization, error recovery, redirect responses |
| Slug uniqueness | Application-level UUID suffix | Pre-write collision query + 422 error | Slug has a DB UNIQUE constraint; better to detect and surface clearly than to auto-suffix |
| Date parsing | Custom string split | `datetime.date.fromisoformat()` | Established project pattern (Phase 9 Pitfall 6); raises clean `ValueError` on bad input |
| ORM direct DDL | `alter_table()` in Python code | Alembic migration | CLAUDE.md constraint; Alembic is sole DDL authority |

**Key insight:** Every problem in this phase has been solved by prior phases. Model everything on Phase 9 (admin_people / people editor). The only net-new concern is slug re-derivation with collision detection, and the logic is already written in `pipeline/commands/ingest.py`.

---

## Common Pitfalls

### Pitfall 1: Stamping published_at Without Checking resolved_at Guard

**What goes wrong:** Operator POSTs to `/publish` on an argument whose `resolved_at IS NULL` (pipeline not yet complete). The argument appears on the public site with no utterances.

**Why it happens:** The frontend only renders the Publish button when resolved, but the backend must enforce the guard independently — a direct API call bypasses the UI.

**How to avoid:** In `publish_argument()`, check `argument.resolved_at IS NOT NULL` before writing `published_at`. If not met, raise `ValueError("Cannot publish: resolve step not yet complete")` → router returns 422.

**Warning signs:** Public `/cases/` showing an argument with 0 utterances.

### Pitfall 2: Slug Collision on Case Name Edit

**What goes wrong:** Operator renames "Obergefell v. Hodges" to something that collides with an existing case slug. DB raises `IntegrityError` (unique constraint violation) instead of a user-facing message.

**Why it happens:** `Case.slug` has `unique=True`. Without a pre-write check, the ORM commit raises `IntegrityError`, which FastAPI catches as a 500.

**How to avoid:** In `update_argument()`, before setting `lead_case.slug`, query `SELECT id FROM cases WHERE slug = :new_slug AND id != :lead_case_id`. If a row is found, raise `ValueError("slug_collision")`. The router catches `ValueError` and returns 422. The SvelteKit action checks for the `"slug_collision"` string (or a 422) and displays the specific copywriting from the UI-SPEC: "This title generates a URL slug that conflicts with an existing case. Choose a different title."

**Warning signs:** 500 errors on save when a name edit is submitted.

### Pitfall 3: Forgetting the Slug Freeze for Published Arguments (D-11)

**What goes wrong:** Operator edits the `case_name` of a published argument. The slug re-derives and breaks all existing URLs/bookmarks to that case.

**Why it happens:** The slug freeze logic (`if argument.published_at is None`) is easy to omit when writing `update_argument()`.

**How to avoid:** Explicit conditional in `update_argument()`: re-derive and write slug only when `argument.published_at is None`. When already published, write `lead_case.case_name` only — leave `lead_case.slug` unchanged.

**Warning signs:** Publicly visible case URL changes after operator edits a published argument title.

### Pitfall 4: Stale Argument Metadata in Job Detail After Edit

**What goes wrong:** Operator edits argument metadata from `/admin/arguments/[id]`, then navigates to the job detail page and sees the old title/docket.

**Why it happens:** SvelteKit caches page data unless `invalidateAll()` is called or the load function re-fetches on navigation.

**How to avoid:** The load function in `+page.server.ts` always fetches fresh data from the API. Since SvelteKit server load functions run on every navigation (no client-side caching), this is not an issue as long as the load function always calls the API rather than using a module-level cache.

**Warning signs:** Job detail page shows outdated case title after user edits from the arguments editor.

### Pitfall 5: EVERY update() Needs .execution_options(synchronize_session=False)

**What goes wrong:** SQLAlchemy Core `update()` statements without `execution_options(synchronize_session=False)` can trigger unexpected session identity-map synchronization, causing stale reads or silent no-ops on async sessions.

**Why it happens:** This is a project-wide critical guard documented in `admin_jobs.py` and `admin_people.py`. New developers miss it.

**How to avoid:** Every `await db.execute(update(...).values(...))` call in `admin_arguments.py` must include `.execution_options(synchronize_session=False)`. See all existing service files as examples.

**Warning signs:** Update appears to succeed (no error) but the DB row is unchanged.

### Pitfall 6: Publish Toggle on List Page Needs Per-Row Forms

**What goes wrong:** Using a single shared `<form>` for all publish toggles on the list page — the argument_id gets confused across rows.

**Why it happens:** Simple mistake when building a table with multiple interactive elements.

**How to avoid:** Each table row gets its own `<form method="POST" action="?/publish">` (or `?/unpublish`) containing a hidden `<input name="argument_id" value={arg.id}>`. The server action reads `argument_id` from `formData`.

**Warning signs:** Publish toggle publishes the wrong argument.

---

## Code Examples

### Alembic Migration 0007

```python
# Source: api/models/models.py + alembic pattern from 0006_add_structured_name_fields.py
revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("arguments", "published_at")
```

### Argument model addition (models.py)

```python
# Source: existing Argument model in api/models/models.py
class Argument(Base):
    __tablename__ = "arguments"
    id = Column(Integer, primary_key=True)
    argued_date = Column(Date, nullable=False)
    question_number = Column(Integer, nullable=False, default=1)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)  # Phase 11: D-05
```

### New Pydantic schemas (api/schemas/admin_arguments.py)

```python
# Source: api/schemas/admin_people.py — structural pattern
import datetime
from typing import Optional
from pydantic import BaseModel

class ArgumentListItem(BaseModel):
    """One row in the /admin/arguments list."""
    id: int
    argued_date: datetime.date
    case_name: str          # lead case
    docket_number: str      # lead case
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    model_config = {"from_attributes": True}

class ConsolidatedDocket(BaseModel):
    """A non-lead docket number for read-only display (D-10)."""
    docket_number: str

class ArgumentDetail(BaseModel):
    """Full argument data for the edit form."""
    id: int
    argued_date: datetime.date
    case_name: str
    docket_number: str
    slug: str
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    consolidated_dockets: list[ConsolidatedDocket] = []
    model_config = {"from_attributes": True}

class ArgumentUpdate(BaseModel):
    """PATCH body for argument edit.
    
    Mass-assignment guard: only case_name, docket_number, argued_date writable.
    published_at is NOT in this schema — it is controlled only by /publish and /unpublish.
    """
    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None  # ISO date string "YYYY-MM-DD"
```

### Slug re-derivation (reused from pipeline)

```python
# Source: pipeline/commands/ingest.py _derive_slug() line 82
def _derive_slug(case_name: str) -> str:
    return (
        case_name.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace(",", "")
    )
# In admin_arguments.py: import or replicate this 5-line function.
# Importing from pipeline is acceptable since admin_jobs.py already imports
# from pipeline.commands.resolve (normalize_label).
```

### Publish/Unpublish service functions

```python
# Source: admin_people.py pattern + D-07 guard requirements
from sqlalchemy import func as sqlfunc

async def publish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    # D-07 guard: can only publish when resolved and not yet published
    if argument.resolved_at is None:
        raise ValueError("Cannot publish: resolve step not yet complete")
    if argument.published_at is not None:
        raise ValueError("Already published")
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(published_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return await get_argument_detail(db, argument_id)

async def unpublish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    if argument.published_at is None:
        raise ValueError("Not currently published")
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(published_at=None)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return await get_argument_detail(db, argument_id)
```

### TopNav admin variant extension (D-12)

```svelte
<!-- Source: app/src/lib/components/TopNav.svelte (Phase 10 pattern) -->
<!-- BEFORE: Pipeline Runner | People Editor -->
<!-- AFTER:  Pipeline Runner | Arguments | People Editor -->
<a href="/admin/pipeline" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    Pipeline Runner
</a>
<a href="/admin/arguments" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    Arguments
</a>
<a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
    People Editor
</a>
```

### Date formatting (established pattern)

```typescript
// Source: app/src/routes/admin/pipeline/+page.svelte formatDate() — replicate in new pages
function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}
// → "Oct 6, 2014"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `resolved_at IS NOT NULL` as public visibility gate | `published_at IS NOT NULL` as public visibility gate | Phase 11 (D-06) | Decouples "pipeline done" from "operator approved for publish"; resolved_at retains its pipeline meaning |
| ARG-02: read-only after resolve | Always-editable + publish model (D-09) | Phase 11 | Simpler UX; operator can correct metadata at any time |

**Not deprecated:** `resolved_at` stays on the `Argument` model and retains its meaning (pipeline resolve step completion). Only the public visibility check changes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_derive_slug()` can be imported from `pipeline.commands.ingest` in the service layer without circular import | Code Examples | If circular: duplicate the 5-line function verbatim in `admin_arguments.py` instead |
| A2 | The job detail load function should use a separate fetch to `/api/admin/arguments/{id}` rather than expanding `AdminJobResponse` | Architecture Patterns (Pattern 5) | If wrong: `AdminJobResponse` must be extended; the list endpoint also returns extra fields unnecessarily |

---

## Open Questions (RESOLVED)

1. RESOLVED: **Import `_derive_slug` from pipeline or duplicate it?**
   - Decision: Import `_derive_slug` directly from `pipeline.commands.ingest`. Cross-layer import is precedented (admin_jobs.py imports normalize_label from pipeline.commands.resolve) and the function has no import-time side effects.

2. RESOLVED: **How does the list-page publish toggle send `argument_id`?**
   - Decision: Hidden `<input name="argument_id" value={arg.id}>` inside a per-row `<form method="POST" action="?/publish">` (or `?/unpublish`). The action reads `formData.get('argument_id')`.

---

## Environment Availability

Step 2.6: SKIPPED — no external tool dependencies. All required services (PostgreSQL, FastAPI, SvelteKit dev server) are part of the existing project stack, verified operational by Phase 10 completion.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (admin area) | Existing `verify_admin_token` dependency on router — all new routes inherit it automatically via the shared `APIRouter(dependencies=[Depends(verify_admin_token)])` |
| V3 Session Management | no | Session auth is Phase 6 HMAC cookie; new routes inherit same guard |
| V4 Access Control | yes | IDOR: load argument by ID and return 404 if not found — same T-08-IDOR pattern as people editor |
| V5 Input Validation | yes | Pydantic v2 `ArgumentUpdate` schema; date strings parsed with `datetime.date.fromisoformat()`; slug collision caught before write |
| V6 Cryptography | no | No new secrets or encryption in this phase |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on argument ID | Spoofing / Info Disclosure | Return 404 (not 403) on missing argument — same pattern as `get_person_detail()` |
| Mass-assignment via ArgumentUpdate | Tampering | `ArgumentUpdate` schema has explicit allow-list: `case_name`, `docket_number`, `argued_date` only; `published_at` is NOT in the schema |
| Slug collision → IntegrityError 500 | Denial of Service | Pre-write collision check → 422 before commit (Pitfall 2) |
| Publish gate bypass | Tampering | Backend enforces `resolved_at IS NOT NULL` before setting `published_at`; UI gate alone is insufficient |
| DB constraint crash on docket_number | Denial of Service | `docket_number` has `unique=True` on `Case`; if operator enters a duplicate docket, SQLAlchemy raises `IntegrityError` → handle with pre-write check or surface as 422 (recommendation: add a pre-write check identical to slug collision) |

**Note on docket_number uniqueness:** `Case.docket_number` has `unique=True` and `Case.docket_number_norm` also has `NOT NULL`. If an operator types a docket number already belonging to a different case, the commit will raise `IntegrityError`. The planner should add a pre-write check in `update_argument()` for `docket_number` collisions, analogous to the slug collision check.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `api/services/admin_people.py` — canonical PATCH service pattern [VERIFIED: codebase]
- Codebase: `api/routers/admin.py` — existing router structure and auth dependency [VERIFIED: codebase]
- Codebase: `api/models/models.py` — Argument, Case, CaseArgument, Argument.resolved_at [VERIFIED: codebase]
- Codebase: `alembic/versions/0006_add_structured_name_fields.py` — migration chain, `down_revision = "0006"` [VERIFIED: codebase]
- Codebase: `pipeline/commands/ingest.py` `_derive_slug()` at line 82 [VERIFIED: codebase]
- Codebase: `api/services/cases.py` `get_cases()` — current `resolved_at.isnot(None)` filter [VERIFIED: codebase]
- Codebase: `app/src/lib/components/TopNav.svelte` — current admin link set [VERIFIED: codebase]
- Codebase: `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — multi-fetch load pattern [VERIFIED: codebase]
- Phase context: `.planning/phases/11-argument-metadata-editing/11-CONTEXT.md` — all decisions D-01 through D-12 [VERIFIED: codebase]
- Phase UI spec: `.planning/phases/11-argument-metadata-editing/11-UI-SPEC.md` — layout contracts, copywriting, color tokens [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- CLAUDE.md project constraints: Alembic sole DDL authority, asyncpg `statement_cache_size=0`, no `Base.metadata.create_all` [ASSUMED — sourced from project instructions file, not re-verified this session against runtime]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already installed; verified from codebase
- Architecture: HIGH — all patterns directly observed in existing Phase 8/9 code
- Pitfalls: HIGH — slug pitfall documented in CONTEXT.md D-11; other pitfalls observed from existing guard patterns in admin_jobs.py and admin_people.py
- Security: HIGH — IDOR and mass-assignment patterns directly observed from Phase 9

**Research date:** 2026-06-22
**Valid until:** 2026-07-22 (stable stack; no external dependencies to age out)
