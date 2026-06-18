# Phase 8: People Editor - Research

**Researched:** 2026-06-17
**Domain:** Admin CRUD — SvelteKit people directory & edit form, FastAPI PATCH + roles endpoint, Alembic migration 0005
**Confidence:** HIGH (codebase-driven; all patterns verified against existing source files)

---

## Summary

Phase 8 delivers the operator's people management UI: a directory listing with an incomplete-records filter, a person edit form with tenure management, and a participant summary on the completed job detail page. The migration, backend, and frontend patterns all have direct analogs in the Phases 6–7 codebase.

The backend work is additive: migration 0005 adds two nullable columns; three new FastAPI routes (`GET /api/admin/people/{id}`, `PATCH /api/admin/people/{id}`, `POST /api/admin/roles`) are added to the existing admin router; a new service file (`admin_people.py`) keeps people management separate from job orchestration. The frontend work creates two new route directories (`/admin/people` and `/admin/people/[id]`) and modifies two existing files (the nav layout, the job detail page).

The single architectural novelty is the delete-and-reinsert strategy for tenure rows — the PATCH endpoint receives the full current tenure array, deletes all existing `court_tenures` rows for that person, and inserts the submitted rows in one transaction. This is simpler and more correct than tracking per-row diffs on the frontend.

**Primary recommendation:** Follow the Phase 7 patterns exactly. Every new file has a clear codebase analog. The only net-new patterns are: (1) Svelte 5 `$state<T[]>` array mutation for dynamic tenure rows, (2) SvelteKit toggle switch that changes the URL query string via `goto()`, and (3) the `POST /api/admin/roles` inline role-creation endpoint called via raw fetch from the Svelte component.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** No dedicated participants page. PEOPLE-04 is satisfied by the incomplete filter in `/admin/people`. After a pipeline run completes, the operator uses the filter to find newly created person stubs.
**D-02:** The completed `/admin/pipeline/[job_id]` page gains a read-only resolved participants section at the bottom: a list of people resolved in that run (name + role), sourced by joining `argument_participants → people → roles` on `argument_participants.argument_id = admin_jobs.argument_id WHERE person_id IS NOT NULL`.
**D-03:** Below the participant list, a "Review people →" link navigates to `/admin/people?incomplete=1`. The link is global — it shows all incomplete people, not just this argument's participants.
**D-04:** A person record is incomplete if `role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL`. Court tenure absence is NOT considered missing.
**D-05:** The filter is a toggle switch at the top of `/admin/people`. When active, the URL becomes `/admin/people?incomplete=1` and the `+page.server.ts` load function re-runs with the filter. The toggle is pre-activated when the page loads with `?incomplete=1` in the URL.
**D-06:** Directory table columns: Name | Role | Missing fields badge | Edit link. The missing-fields badge shows which specific fields are absent as small amber chips (labels "bio", "photo", "role"). No bio snippet, no photo thumbnail.
**D-07:** Tenure fields are always visible on the person edit form, even for advocates with no tenure rows. If the operator fills in dates and saves, a new `court_tenures` row is created.
**D-08:** Show all tenure rows for the person, not just the most recent.
**D-09:** An "Add tenure" button appends a new empty tenure row (client-side Svelte state). A trash icon per row removes it. All creates/deletes/edits are sent in the single Save submission — the backend replaces tenure rows with whatever is submitted (delete-and-reinsert strategy).
**D-10:** Role is a `<select>` dropdown populated from the `roles` table. An "＋ Add new role" option at the bottom, when selected, opens a small inline form. Submitting creates a new `roles` row and immediately selects it. Requires a new `POST /api/admin/roles` endpoint.
**D-11:** Single scrolling page with three visual sections: "Basic Info", "Bio & Photo", "Court Tenure". One "Save changes" button at the bottom.

### Claude's Discretion

- Exact styling of the toggle switch (CSS or Tailwind, no JS library required)
- Whether the missing-fields badge chips are `<span>` tags or another element
- Whether tenure date inputs are `<input type="date">` or text fields (prefer `type="date"` for browser-native date pickers)
- Whether the "Add new role" inline form appears below the dropdown or as a small modal
- Exact wording of the "Review people" link on the completed job page
- Whether the participant list on the job page shows a count header before the list
- Exact amber color value for the missing-fields badge chips (use `#f59e0b` or similar — stay consistent with admin theme)

### Deferred Ideas (OUT OF SCOPE)

- Argument/case metadata editing (title, docket_number, argued_date, case_name) — deferred to Phase 9 or a follow-on patch.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PEOPLE-01 | Operator can view all people in a directory listing | `GET /api/admin/people` already exists; needs bio_text/photo_url/missing fields added; new `/admin/people` SvelteKit route |
| PEOPLE-02 | Operator can filter the directory to show only people with one or more missing metadata fields | Incomplete filter in load fn via `?incomplete=1` URL param; toggle switch drives `goto()` navigation; server-side `missing: string[]` field per person |
| PEOPLE-03 | Operator can edit a person's name, role, bio text, photo URL, and tenure dates | New `/admin/people/[id]` route; `PATCH /api/admin/people/{id}` with delete-and-reinsert tenure strategy; `POST /api/admin/roles` for inline role creation |
| PEOPLE-04 | After a pipeline run completes resolve, operator can review that argument's resolved participants and fill in missing metadata inline | ParticipantList section added to existing `/admin/pipeline/[job_id]` page; "Review people →" link to `/admin/people?incomplete=1` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| People directory listing | Frontend Server (SSR) | API / Backend | Load function calls FastAPI, renders table server-side; no client-side fetch needed |
| Incomplete filter toggle | Browser / Client | Frontend Server (SSR) | Toggle triggers `goto()` URL change; SSR load fn re-runs with `?incomplete=1` |
| Missing-fields badge derivation | API / Backend | — | Computed server-side in FastAPI service so API response carries `missing: string[]`; avoids re-deriving in Svelte |
| Person edit form load | Frontend Server (SSR) | API / Backend | Load function fetches person + roles + tenures; form pre-populated on server before render |
| Dynamic tenure row add/delete | Browser / Client | — | Pure client-side `$state` array mutation; no server call until Save |
| Inline role creation | Browser / Client | API / Backend | Raw fetch to `POST /api/admin/roles` from Svelte (not a form action); response updates dropdown in-place |
| Save person (PATCH) | Frontend Server (SSR) | API / Backend | SvelteKit form action POSTs, action calls FastAPI PATCH, redirects on success |
| Participant list on job page | Frontend Server (SSR) | API / Backend | Added to existing job load fn; participants joined from `argument_participants` |
| Database migration | Database / Storage | — | Alembic migration 0005 adds bio_text + photo_url to people table |

---

## Standard Stack

### Core

No new packages required. All capabilities use libraries already installed in the project.

| Layer | Existing Dependency | Usage in Phase 8 |
|-------|---------------------|-----------------|
| Frontend | SvelteKit 2.x / Svelte 5 | New route directories, Runes state management |
| Backend | FastAPI 0.115+ / Pydantic v2 | New admin routes, new schemas |
| ORM | SQLAlchemy 2.0 async | New service functions, delete-and-reinsert tenure |
| Migrations | Alembic | Migration 0005 |

**No `npm install` or `pip install` steps required for Phase 8.** [VERIFIED: codebase scan]

### Package Legitimacy Audit

> Not applicable — Phase 8 installs zero new packages (no npm install, no pip install).

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
  │
  ├─ GET /admin/people(?incomplete=1)
  │    └─ +page.server.ts load()
  │         └─ GET /api/admin/people?incomplete=1
  │              └─ admin_people.list_people(incomplete=True) → PersonListItem[]
  │                    (includes missing: string[] per person — derived server-side)
  │
  ├─ [toggle click] → goto('/admin/people?incomplete=1') → SSR re-run
  │
  ├─ [Edit person link] → GET /admin/people/[id]
  │    └─ +page.server.ts load()
  │         ├─ GET /api/admin/people/{id} → PersonDetail (name, role, bio, photo, tenures[])
  │         └─ GET /api/admin/roles → RoleListItem[]
  │
  ├─ [Add tenure / Remove tenure] → $state<TenureRow[]> mutation (client only, no server call)
  │
  ├─ [＋ Add new role] → raw fetch POST /api/admin/roles
  │    └─ admin.create_role() → RoleResponse
  │         └─ dropdown updated in-place, new role selected
  │
  ├─ [Save changes] → form POST → +page.server.ts action()
  │    └─ PATCH /api/admin/people/{id}  ← body: {full_name, role_id, bio_text, photo_url, tenures[]}
  │         └─ admin_people.update_person() — delete-and-reinsert tenures in one transaction
  │              └─ success: throw redirect(303, /admin/people/{id})
  │
  └─ GET /admin/pipeline/[job_id] (existing — Phase 7)
       └─ +page.server.ts load() (extended)
            └─ GET /api/admin/jobs/{id} (existing)
            └─ GET /api/admin/jobs/{id}/participants (new lightweight endpoint, or inline join)
                 └─ argument_participants JOIN people JOIN roles WHERE argument_id = job.argument_id AND person_id IS NOT NULL
```

### Recommended Project Structure

New files only — all existing files extended in-place:

```
api/
├── schemas/
│   └── admin_people.py         # PersonListItem, PersonDetail, PersonUpdate, TenureRow, RoleResponse
├── services/
│   └── admin_people.py         # list_people(), get_person(), update_person(), create_role(), list_roles()
└── routers/
    └── admin.py                # +3 routes: GET /people/{id}, PATCH /people/{id}, POST /roles

alembic/versions/
└── 0005_add_person_metadata.py # adds bio_text TEXT nullable, photo_url VARCHAR(500) nullable

app/src/routes/admin/
├── people/
│   ├── +page.server.ts         # load (list + filter) + no actions needed (navigate only)
│   └── +page.svelte            # PeopleTable + IncompleteToggle
└── people/[id]/
    ├── +page.server.ts         # load (person + roles) + save action
    └── +page.svelte            # PersonEditForm (Basic Info, Bio & Photo, Court Tenure sections)
```

Modified files:
```
app/src/routes/admin/+layout.svelte          # activate People Editor nav link
app/src/routes/admin/pipeline/[job_id]/+page.server.ts  # extend load to include participants
app/src/routes/admin/pipeline/[job_id]/+page.svelte     # add ParticipantList section
api/models/models.py                         # add bio_text + photo_url columns to Person model
```

---

### Pattern 1: Svelte 5 `$state<T[]>` for dynamic tenure rows

**What:** Client-side array of tenure row objects managed with `$state`. Add/remove rows before form submission — no server call until Save is clicked.

**When to use:** Whenever the operator needs to add/delete items in a list that is submitted as a batch.

**Key rule:** Mutate the `$state` array in-place using `push()` and `splice()`. Do NOT reassign the array variable (e.g., `rows = [...rows, newItem]` is less idiomatic in Svelte 5 Runes — in-place mutation on the proxy object is the correct approach). [ASSUMED — training knowledge; confirmed as the standard Svelte 5 pattern but not verified via Context7 this session]

```typescript
// Source: inferred from Svelte 5 Runes semantics + project convention (app/src/routes/admin patterns)
interface TenureRow {
  id?: number;       // undefined for new rows; present for rows loaded from DB
  seat: string;
  start_date: string;
  end_date: string;
}

let tenureRows = $state<TenureRow[]>(data.person.tenures ?? []);

function addTenureRow() {
  tenureRows.push({ seat: '', start_date: '', end_date: '' });
}

function removeTenureRow(index: number) {
  tenureRows.splice(index, 1);
}
```

Serializing tenure rows into the form submission — since HTML forms cannot send JSON arrays, encode as hidden fields with indexed names (e.g., `tenure[0][seat]`) **or** use a single hidden `<input>` with the JSON-serialized array and parse it in the action. The hidden-JSON approach is simpler and avoids n × 3 hidden fields: [ASSUMED]

```svelte
<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)} />
```

The `+page.server.ts` action parses this:
```typescript
const tenuresRaw = formData.get('tenures') as string ?? '[]';
const tenures = JSON.parse(tenuresRaw) as TenureRow[];
```

---

### Pattern 2: Toggle switch driving URL query string

**What:** CSS toggle switch (checkbox) that navigates to `/admin/people?incomplete=1` or `/admin/people` when toggled. The URL change causes SvelteKit to re-run the load function server-side.

**When to use:** Filters that must be bookmarkable and shareable via URL.

**Implementation:** `goto()` from `$app/navigation` — the canonical SvelteKit way to change the URL from a component without a form submission. [ASSUMED — standard SvelteKit pattern]

```svelte
// Source: inferred from Phase 7 patterns + SvelteKit 2 documentation
import { goto } from '$app/navigation';

function handleToggle(checked: boolean) {
  if (checked) {
    goto('/admin/people?incomplete=1');
  } else {
    goto('/admin/people');
  }
}
```

Pre-check state from URL on load:
```svelte
let { data } = $props();
// data.incomplete is set by the load function reading url.searchParams
let toggleChecked = $state(data.incomplete ?? false);
```

Load function reads the param:
```typescript
export const load: PageServerLoad = async ({ fetch, url }) => {
  const incomplete = url.searchParams.get('incomplete') === '1';
  // pass incomplete flag to FastAPI
  const apiUrl = incomplete
    ? `${FASTAPI_BASE_URL}/api/admin/people?incomplete=1`
    : `${FASTAPI_BASE_URL}/api/admin/people`;
  // ...
  return { people, incomplete };
};
```

---

### Pattern 3: Inline role creation via raw fetch

**What:** The "＋ Add new role" option in the role dropdown triggers a raw `fetch()` call to `POST /api/admin/roles` — not a SvelteKit form action — so the dropdown can update in-place without a page reload.

**When to use:** Any time a dependent UI element (the role dropdown) must update immediately after a sub-operation, without navigating away from the current form.

**Key consideration:** This pattern was also used in Phase 7 (`[07-05]` note in STATE.md about `AddNewPersonForm` originally using raw fetch, later converted to `use:enhance`). For Phase 8, raw fetch remains appropriate here because the role create is a side operation that does NOT affect the main form's `form` prop or page data. [VERIFIED: codebase — STATE.md [07-07] documents this distinction]

```typescript
// Source: inferred from Phase 7 patterns (api/routers/admin.py auth pattern)
// All fetch calls from the browser to SvelteKit go through +page.server.ts
// BUT direct calls to /api/admin/* from the browser require X-Admin-Token.
// Since this is admin-only and the token is in a server-only env var, the
// role creation MUST be proxied through a SvelteKit server action.
```

**Critical constraint:** `FASTAPI_BASE_URL` and `ADMIN_TOKEN` are server-only env vars (`$env/static/private`). The browser cannot call FastAPI directly. The role creation call must go through a SvelteKit server action (`?/createRole` named action on `/admin/people/[id]/+page.server.ts`), with `use:enhance` so the response updates the dropdown without a page reload. [VERIFIED: codebase — all `+page.server.ts` files use `$env/static/private`; architecture rule in CLAUDE.md]

Pattern for the named action:
```typescript
// +page.server.ts
createRole: async ({ request }) => {
  const data = await request.formData();
  const name = (data.get('role_name') as string ?? '').trim();
  if (!name) return fail(400, { roleError: 'Role name is required.' });
  
  const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/roles`, {
    method: 'POST',
    headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) return fail(400, { roleError: 'Could not create role. Try again.' });
  
  const role = await res.json();
  return { roleCreated: true, role };  // use:enhance reads this in the Svelte component
},
```

---

### Pattern 4: FastAPI PATCH with optional Pydantic v2 fields

**What:** `PATCH /api/admin/people/{id}` accepts a partial update body. All fields are optional in the schema. The service validates that at least the person exists, then applies the update plus tenure replacement.

**Why PATCH not PUT:** Only the fields present in the body are updated. However, for tenures the delete-and-reinsert strategy means the full array must always be sent — omitting `tenures` from the body means "keep existing tenures unchanged" (not "delete all tenures").

```python
# Source: inferred from api/schemas/admin_jobs.py pattern + Pydantic v2 docs
from typing import Optional
from pydantic import BaseModel

class TenureRow(BaseModel):
    seat: Optional[str] = None
    start_date: Optional[str] = None   # ISO date string "YYYY-MM-DD" or None
    end_date: Optional[str] = None

class PersonUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureRow]] = None  # None = don't touch tenures; [] = delete all
```

**Gotcha:** Pydantic v2 distinguishes between a field set to `None` (explicitly nulled) and a field not present in the body (field not set). Use `model.model_fields_set` if partial-update semantics require this distinction. For Phase 8, the form always sends all fields (it is a full edit form, not a partial patch) — so this edge case does not apply. [ASSUMED]

---

### Pattern 5: SQLAlchemy delete-and-reinsert for tenure rows

**What:** The PATCH service deletes all existing `court_tenures` rows for the person and inserts the submitted rows in one transaction.

**Why:** Simpler than tracking per-row diffs. The frontend sends the complete current state; the backend replaces it atomically.

**Pattern:** [ASSUMED — standard SQLAlchemy pattern; no existing codebase analog for bulk delete-reinsert]

```python
# Source: inferred from api/services/admin_jobs.py patterns + SQLAlchemy 2.0 async docs
from sqlalchemy import delete, insert
from api.models.models import CourtTenure

async def _replace_tenures(db: AsyncSession, person_id: int, tenures: list[TenureRow]) -> None:
    """Delete all existing CourtTenure rows for person_id and insert new ones."""
    await db.execute(
        delete(CourtTenure).where(CourtTenure.person_id == person_id)
    )
    for t in tenures:
        # Only insert rows with at least a seat or start_date value
        if t.seat or t.start_date:
            db.add(CourtTenure(
                person_id=person_id,
                seat=t.seat or None,
                start_date=t.start_date or None,  # parse to date if non-None
                end_date=t.end_date or None,
            ))
    # No separate commit here — caller commits
```

**Date handling:** `CourtTenure.start_date` and `end_date` are SQLAlchemy `Date` columns. When receiving ISO strings from the form, parse with `datetime.date.fromisoformat(s)` before inserting. Handle `None` and empty string gracefully. [ASSUMED]

---

### Pattern 6: Alembic migration 0005

**What:** Adds `bio_text TEXT nullable` and `photo_url VARCHAR(500) nullable` to the `people` table.

**Exact pattern from migration 0004:** [VERIFIED: codebase — alembic/versions/0004_add_arguments_resolved_at.py]

```python
# alembic/versions/0005_add_person_metadata.py
revision: str = "0005"
down_revision: Union[str, None] = "0004"

def upgrade() -> None:
    op.add_column("people", sa.Column("bio_text", sa.Text(), nullable=True))
    op.add_column("people", sa.Column("photo_url", sa.String(500), nullable=True))

def downgrade() -> None:
    op.drop_column("people", "photo_url")
    op.drop_column("people", "bio_text")
```

**Model update required:** `api/models/models.py` `Person` class needs two new columns added alongside the existing `role_id` column. Alembic is the sole DDL authority — the model update is for ORM access only; it does not create the column (migration does). [VERIFIED: codebase — CLAUDE.md "Alembic is the sole DDL authority"]

---

### Pattern 7: Participant list endpoint strategy

**What:** The completed job detail page needs to show resolved participants. Two implementation options:

**Option A — Extend existing `GET /api/admin/jobs/{id}` response** to include a `participants` field when `status=completed` and `argument_id` is set. Avoids a new endpoint; the load function already calls this endpoint.

**Option B — New lightweight `GET /api/admin/jobs/{id}/participants` endpoint.** Cleaner separation but requires a second fetch in the load function.

**D-02 in CONTEXT.md indicates Option A or a dedicated participants call.** The CONTEXT.md `<specifics>` section says "avoids a new endpoint by including participants in the existing `GET /api/admin/jobs/{id}` response payload (or a lightweight separate `GET /api/admin/jobs/{id}/participants` endpoint)." [VERIFIED: codebase — 08-CONTEXT.md specifics section]

**Recommendation:** Option B (dedicated participants endpoint) — extending `AdminJobResponse` adds a nullable list that is always fetched even for non-completed jobs, and changes the Phase 7 response contract. A separate lightweight endpoint is cleaner. The load function already makes one parallel FastAPI call and can make a second.

---

### Anti-Patterns to Avoid

- **`Base.metadata.create_all` anywhere:** Alembic is the sole DDL authority. Never call `create_all` to add the new columns. [VERIFIED: codebase — CLAUDE.md constraint]
- **`PUBLIC_` env vars for FastAPI URL:** `FASTAPI_BASE_URL` must remain `$env/static/private`. Never expose the internal FastAPI URL to the browser. [VERIFIED: codebase — CLAUDE.md architecture rule]
- **Reassigning `$state` array instead of mutating it:** `tenureRows = [...tenureRows, newRow]` creates a new array reference. Use `tenureRows.push(newRow)` or `tenureRows.splice(i, 1)` to mutate in-place. [ASSUMED]
- **Client-side fetch to `/api/admin/*` from Svelte component:** All FastAPI calls go through `+page.server.ts` load functions or named actions — browser code never calls FastAPI directly (token is server-only). [VERIFIED: codebase — established pattern in all Phase 6–7 files]
- **Using `method: 'PATCH'` on an HTML `<form>`:** Browsers only support GET and POST on HTML forms. The SvelteKit action always receives a POST; the action's `fetch()` call to FastAPI uses `method: 'PATCH'`. [ASSUMED — standard web platform behavior]
- **Forgetting `execution_options(synchronize_session=False)` on UPDATE calls:** Required for all raw `update()` statements in SQLAlchemy 2.0 async context. Already established as a critical project pattern in `api/services/admin_jobs.py`. [VERIFIED: codebase — admin_jobs.py + PATTERNS.md]
- **Forgetting to re-query after Person update for the redirect:** After PATCH, redirect to the edit page (GET). SvelteKit's `throw redirect(303, ...)` in the action causes the load function to re-run, fetching the updated person from FastAPI — no stale-data issue.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tenure delete-reinsert atomicity | Manual multi-step delete then insert with separate commits | Single SQLAlchemy session, delete + add + one `db.commit()` | Separate commits risk partial state if insert fails |
| Auth on new admin routes | Per-route `Depends(verify_admin_token)` | Router-level dependency already in place (`api/routers/admin.py` line 76–80) | All routes on the admin router inherit the dependency automatically |
| Incomplete filter SQL | Python-side post-filter of all people | SQL `WHERE role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL` | DB-side filter avoids loading the full table for a common operator workflow |
| Roles list for dropdown | Separate endpoint + separate load call | Load roles alongside person detail in the same load function (two parallel fetches) | One round-trip cheaper; roles list is small |
| Missing-fields badge derivation | Client-side Svelte computed | Server-side in `list_people()` service returning `missing: list[str]` per person | API response is the stable contract; client rendering is trivial from a `string[]` |

---

## Common Pitfalls

### Pitfall 1: Forgetting to update `Person` ORM model after migration

**What goes wrong:** Migration 0005 adds `bio_text` and `photo_url` to the DB, but `api/models/models.py` `Person` class still only has `full_name` and `role_id`. SQLAlchemy will not return or insert those columns.

**Why it happens:** Developers apply the migration and assume the ORM auto-discovers new columns.

**How to avoid:** Update `api/models/models.py` `Person` class in the same plan wave as migration 0005. The two changes must land together.

**Warning signs:** `AttributeError: 'Person' object has no attribute 'bio_text'` on first PATCH call.

---

### Pitfall 2: Svelte 5 tenure row binding with dynamic list

**What goes wrong:** Using `bind:value={tenureRows[i].seat}` on a row that was just pushed to the array — the binding may not connect correctly if the row index changes before the DOM updates.

**Why it happens:** Svelte 5 Runes track object identity, not array index. If rows are deleted and indices shift, `bind:value` on an index-based access can bind to the wrong object.

**How to avoid:** Add a stable `key` property to each tenure row (e.g., a counter) and use it in the `{#each ... (row.key)}` keyed each block. For the hidden JSON field, serialize the reactive array directly:

```svelte
{#each tenureRows as row, i (row._key)}
  <input bind:value={row.seat} ... />
  <button onclick={() => removeTenureRow(i)}>✕</button>
{/each}
<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)} />
```

**Warning signs:** After deleting a tenure row, adjacent rows show swapped values.

---

### Pitfall 3: `PATCH /api/admin/people/{id}` receives tenures as stringified JSON

**What goes wrong:** The PATCH body arrives at FastAPI as `application/json` with `tenures` as a list of objects. But if the SvelteKit action sends `tenures` as a form field (string), FastAPI receives a string, not a list.

**Why it happens:** The SvelteKit form encodes the hidden JSON tenure field as a form string. The action must parse it and then send it as a proper JSON body to FastAPI.

**How to avoid:** In the SvelteKit action, parse the `tenures` form field, then send the whole body to FastAPI as `Content-Type: application/json` with a properly structured object — not as form data:

```typescript
const tenuresRaw = formData.get('tenures') as string ?? '[]';
const tenures = JSON.parse(tenuresRaw);
const body = { full_name, role_id, bio_text, photo_url, tenures };
const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${id}`, {
  method: 'PATCH',
  headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
```

---

### Pitfall 4: Role dropdown "＋ Add new role" action returning `fail()` after reload

**What goes wrong:** The inline `createRole` action on `/admin/people/[id]` returns `fail()`. SvelteKit's `use:enhance` sets `form.roleError`. But because this is a named action on the same page as the `save` action, `form` in the Svelte component now carries `roleError`. If the operator then hits Save without reloading, the `save` action's `form` prop might show a stale `roleError`.

**How to avoid:** Use separate form variables for the role creation result vs. the save result. Destructure them via `let { data, form } = $props()` and handle the `roleCreated` vs `roleError` fields by checking which action triggered the result. The simplest approach: after a successful role creation, the `use:enhance` callback adds the new role to a local `$state` list and resets the inline form — no page data invalidation needed.

---

### Pitfall 5: Missing-fields SQL query — NULL vs empty string

**What goes wrong:** `photo_url = ''` (empty string) is stored instead of `NULL` when the operator saves a blank photo URL field. The incomplete filter `WHERE photo_url IS NULL` then misses this person.

**Why it happens:** HTML form fields submit empty strings `''` not `None`. FastAPI receives `""` and stores it.

**How to avoid:** In the PATCH service, normalize empty strings to `None` before writing:

```python
bio_text = body.bio_text if body.bio_text else None
photo_url = body.photo_url if body.photo_url else None
```

The incompleteness check then works correctly because `''` is never stored.

---

### Pitfall 6: `CourtTenure` date columns — string vs Python `date` object

**What goes wrong:** `start_date` and `end_date` on `CourtTenure` are SQLAlchemy `Date` columns. Passing an ISO string `"2005-09-29"` directly to `CourtTenure(start_date="2005-09-29")` may work with some asyncpg versions but is not reliable.

**How to avoid:** Parse the ISO string explicitly:

```python
import datetime
start = datetime.date.fromisoformat(t.start_date) if t.start_date else None
end = datetime.date.fromisoformat(t.end_date) if t.end_date else None
db.add(CourtTenure(person_id=person_id, seat=t.seat, start_date=start, end_date=end))
```

Handle `ValueError` from `fromisoformat` on malformed date strings and surface a 422 from the PATCH endpoint. [ASSUMED — standard Python practice]

---

## Code Examples

### List people with missing-fields derivation (FastAPI service)

```python
# Source: inferred from api/services/admin_jobs.py list_people() + CONTEXT.md D-04
from sqlalchemy import or_, select
from api.models.models import CourtTenure, Person, Role

async def list_people(
    db: AsyncSession,
    incomplete: bool = False,
) -> list[dict]:
    """Return all Person rows with role name and missing-fields list.
    
    D-04: incomplete if role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL.
    Court tenure absence is NOT incomplete.
    """
    q = (
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(Person.full_name)
    )
    if incomplete:
        q = q.where(
            or_(
                Person.role_id.is_(None),
                Person.bio_text.is_(None),
                Person.photo_url.is_(None),
            )
        )
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": person.id,
            "full_name": person.full_name,
            "role_id": person.role_id,
            "role_name": role_name,
            "missing": _missing_fields(person),
        }
        for person, role_name in rows
    ]

def _missing_fields(person: Person) -> list[str]:
    """Return list of missing field labels per D-04."""
    missing = []
    if person.role_id is None:
        missing.append("role")
    if person.bio_text is None:
        missing.append("bio")
    if person.photo_url is None:
        missing.append("photo")
    return missing
```

### Get person detail for edit form (including tenure rows)

```python
# Source: inferred from api/services/people.py get_person_by_id() + CONTEXT.md D-07/D-08
async def get_person_detail(db: AsyncSession, person_id: int) -> dict | None:
    """Return full person data for the edit form, including all tenure rows."""
    result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .where(Person.id == person_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    person, role_name = row

    # Load all tenure rows ordered by start_date
    tenure_result = await db.execute(
        select(CourtTenure)
        .where(CourtTenure.person_id == person_id)
        .order_by(CourtTenure.start_date.asc().nullsfirst())
    )
    tenures = tenure_result.scalars().all()

    return {
        "id": person.id,
        "full_name": person.full_name,
        "role_id": person.role_id,
        "role_name": role_name,
        "bio_text": person.bio_text,
        "photo_url": person.photo_url,
        "tenures": [
            {
                "seat": t.seat,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "end_date": t.end_date.isoformat() if t.end_date else None,
            }
            for t in tenures
        ],
    }
```

### SvelteKit load function — people directory

```typescript
// Source: inferred from app/src/routes/admin/pipeline/+page.server.ts pattern
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
  const incomplete = url.searchParams.get('incomplete') === '1';
  const apiUrl = `${FASTAPI_BASE_URL}/api/admin/people${incomplete ? '?incomplete=1' : ''}`;
  
  const res = await fetch(apiUrl, {
    headers: { 'X-Admin-Token': ADMIN_TOKEN },
  });
  
  const people = res.ok ? await res.json() : [];
  return { people, incomplete };
};
```

### SvelteKit save action — person edit form

```typescript
// Source: inferred from app/src/routes/admin/pipeline/[job_id]/+page.server.ts action pattern
save: async ({ request, params }) => {
  const formData = await request.formData();
  const full_name = (formData.get('full_name') as string ?? '').trim();
  const role_id = formData.get('role_id') ? parseInt(formData.get('role_id') as string, 10) : null;
  const bio_text = (formData.get('bio_text') as string ?? '').trim() || null;
  const photo_url = (formData.get('photo_url') as string ?? '').trim() || null;
  const tenuresRaw = (formData.get('tenures') as string) ?? '[]';

  let tenures: Array<{ seat: string; start_date: string; end_date: string }>;
  try {
    tenures = JSON.parse(tenuresRaw);
  } catch {
    return fail(422, { error: 'Invalid tenure data. Please try again.' });
  }

  if (!full_name) {
    return fail(400, { error: 'Full name is required.' });
  }

  let res: Response;
  try {
    res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
      method: 'PATCH',
      headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, role_id, bio_text, photo_url, tenures }),
    });
  } catch {
    return fail(502, { error: 'Could not save changes. Check the form and try again.' });
  }

  if (!res.ok) {
    return fail(422, { error: 'Could not save changes. Check the form and try again.' });
  }

  // Redirect causes the load function to re-run, fetching updated data (no stale state)
  throw redirect(303, `/admin/people/${params.id}`);
},
```

---

## Runtime State Inventory

> This is not a rename/refactor phase. This section is omitted per the research instructions.

---

## Environment Availability

> Phase 8 uses no external CLI tools, runtimes, or services beyond the existing project stack. All dependencies (Node.js, Python, PostgreSQL, FastAPI) are already verified operational (Phase 7 is complete). Skipped per "no external dependencies" condition.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no — all admin routes already guarded by hooks.server.ts + verify_admin_token | Existing Phase 6 HMAC session cookie |
| V3 Session Management | no | Existing Phase 6 session management |
| V4 Access Control | yes — new routes must inherit admin auth | Router-level `Depends(verify_admin_token)` already in place on admin router |
| V5 Input Validation | yes | Pydantic v2 on PATCH body; empty-string-to-None normalization in service |
| V6 Cryptography | no | Not applicable for CRUD endpoints |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PATCH person with arbitrary `person_id` path param | Tampering | `get_person_by_id()` returns `None` if not found; router raises 404; no data written to wrong person |
| `photo_url` stores arbitrary URL | Information Disclosure | No server-side URL fetch; stored as opaque string only; no SSRF risk from storage alone |
| `bio_text` stored as arbitrary text | Tampering | Stored as plain text; rendered in admin UI only; operator-only interface; XSS risk is low but bio_text should not be rendered as `{@html}` |
| Role name injection via `POST /api/admin/roles` | Tampering | Pydantic v2 validates `name: str`; `Role.name` is `String(100)` with unique constraint; duplicate names return existing role or 409 |
| Tenure date injection | Tampering | `datetime.date.fromisoformat()` validates format; invalid dates return 422 before any DB write |

**Note on `{@html}` in Svelte:** Bio text must be rendered as plain text (using Svelte's default text interpolation `{person.bio_text}`) — never `{@html person.bio_text}`. This is an admin-only interface but defense in depth applies. [ASSUMED — standard Svelte/XSS practice]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Svelte 5 `$state<T[]>` array push/splice triggers reactivity correctly on proxy | Pattern 1 | Tenure rows don't update the DOM; may need `$state.snapshot()` or reassignment workaround |
| A2 | `goto()` from `$app/navigation` is the correct API to change URL query params in SvelteKit 2 | Pattern 2 | If API changed, toggle may not trigger load fn re-run |
| A3 | HTML `<form method="POST">` with `use:enhance` intercepting a named action (`?/save`) redirects correctly after `throw redirect(303, ...)` | Pattern 3 | Edit form may not redirect to updated page after save |
| A4 | `datetime.date.fromisoformat()` correctly parses the ISO strings from `<input type="date">` | Pitfall 6 | Date values not stored; 500 error on save |
| A5 | Pydantic v2 `Optional[int] = None` correctly handles a `role_id` form field that is submitted as an empty string | Pattern 4 | Role assignment fails silently; person saved with no role |
| A6 | The `{@html}` prohibition for bio_text rendering is adequate XSS mitigation in this admin-only context | Security Domain | XSS in bio_text field for admin users (low risk but not zero) |

---

## Open Questions (RESOLVED)

1. **Participants endpoint strategy — extend `AdminJobResponse` or new endpoint?**
   - What we know: CONTEXT.md gives both options; the existing load function already calls `GET /api/admin/jobs/{id}`
   - What's unclear: Whether extending `AdminJobResponse` with an optional `participants` field changes Phase 7 contract in a breaking way
   - Recommendation: New `GET /api/admin/jobs/{id}/participants` endpoint; the job detail load function fetches it in parallel only when `job.status === 'completed'` and `job.argument_id` is set

2. **`role_id` empty string from form — how to handle?**
   - What we know: `<select>` with no selection may submit empty string `""` rather than omitting the field
   - What's unclear: Whether Pydantic v2 coerces `""` to `None` for `Optional[int]` or raises a validation error
   - Recommendation: In the SvelteKit action, explicitly convert: `const role_id = formData.get('role_id') ? parseInt(...) : null` before sending JSON to FastAPI

3. **`incomplete` query param forwarding to FastAPI — should FastAPI accept it as a query param or path param?**
   - What we know: GET /api/admin/people currently returns all people; filtering is new for Phase 8
   - What's unclear: Whether to pass `?incomplete=1` as a FastAPI query param or handle filtering purely in the service
   - Recommendation: FastAPI query param `incomplete: bool = False` on `GET /api/admin/people` — consistent with REST conventions; allows direct API testing

---

## Sources

### Primary (HIGH confidence — verified from codebase)

- `api/routers/admin.py` — existing admin router structure, `verify_admin_token` dependency pattern, all existing routes
- `api/services/admin_jobs.py` — `list_people()`, `resolve_job()`, SQLAlchemy patterns, `execution_options(synchronize_session=False)` usage
- `api/models/models.py` — `Person`, `CourtTenure`, `Role`, `ArgumentParticipant`, `AdminJob` ORM model definitions
- `api/schemas/admin_jobs.py` — Pydantic v2 schema patterns, `model_config = {"from_attributes": True}`
- `api/schemas/people.py` — existing `PersonResponse` shape
- `api/services/people.py` — `get_person_by_id()` pattern
- `alembic/versions/0004_add_arguments_resolved_at.py` — migration file structure and column-add pattern
- `app/src/routes/admin/+layout.svelte` — People Editor nav item (currently disabled span, line ~36)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Svelte 5 Runes patterns, `$state`, `$derived`, `$effect`, Phase 7 component structure
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load + named actions pattern, parallel fetch, `fail()` / `redirect()` usage
- `app/src/routes/admin/pipeline/+page.server.ts` — form action forwarding to FastAPI pattern
- `.planning/phases/07-pipeline-runner/07-PATTERNS.md` — shared patterns reference for all Phase 8 file analogs
- `.planning/phases/08-people-editor/08-CONTEXT.md` — all locked decisions D-01 through D-11
- `.planning/STATE.md` — `[07-07]` notes on `use:enhance` vs raw fetch distinction
- `CLAUDE.md` — `asyncpg statement_cache_size=0`, `Alembic is sole DDL authority`, `FastAPI calls from +page.server.ts`

### Secondary (MEDIUM confidence — assumed from framework knowledge)

- SvelteKit 2 `goto()` API for URL navigation without form submission
- SvelteKit `use:enhance` behavior with named actions and `throw redirect(303, ...)`
- Pydantic v2 `Optional[int]` behavior with missing vs null form fields

### Tertiary (LOW confidence — training knowledge only)

- Svelte 5 `$state` proxy array in-place mutation semantics (push/splice reactivity)
- `datetime.date.fromisoformat()` for ISO date string parsing in Python

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all libraries verified in existing codebase
- Architecture patterns: HIGH — all patterns have direct codebase analogs (Phases 6–7)
- Pitfalls: MEDIUM — derived from codebase knowledge + standard framework behavior; some are training-knowledge assumptions
- Security: HIGH — existing auth infrastructure applies; new threat patterns are standard for CRUD forms

**Research date:** 2026-06-17
**Valid until:** 2026-07-17 (stable stack; no fast-moving dependencies)
