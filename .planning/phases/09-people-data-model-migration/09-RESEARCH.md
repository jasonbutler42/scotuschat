# Phase 9: People Data Model Migration - Research

**Researched:** 2026-06-19
**Domain:** Alembic migration / SQLAlchemy ORM / Pydantic v2 schema extension / SvelteKit form action extension
**Confidence:** HIGH — all findings are verified directly from the project codebase and installed package versions

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Name Parts — Schema & Storage (PEOP-01)**
- D-01: Six new nullable columns added to `people` via migration 0006: `first_name VARCHAR(150)`, `last_name VARCHAR(150)`, `middle_name VARCHAR(150)`, `name_suffix VARCHAR(50)`, `appointing_president VARCHAR(200)`, `appointing_president_party VARCHAR(50)`. All nullable, no default, no NOT NULL constraint.
- D-02: `full_name` remains the resolution anchor and is NOT removed or made optional. Name parts are supplemental.
- D-03: Migration 0006 leaves all new columns NULL on existing rows — no backfill, no parsing attempt.

**Name Parts — Derivation Logic (PEOP-01)**
- D-04: When the PATCH handler receives a `PersonUpdate` payload where `first_name` is non-empty, the service auto-derives `full_name` from parts using the format `{first} [{middle}] {last}[ {suffix}]` (middle and suffix omitted when blank).
- D-05: If `first_name` is null or empty in the PATCH payload, `full_name` is left unchanged.
- D-06: `full_name` remains an editable text input on the form alongside the name parts. Server derivation fires server-side on save — no client-side live preview.

**Admin Directory Sort (PEOP-01)**
- D-07: The `/admin/people` directory query orders by `last_name NULLS LAST` as the primary sort. Records where `last_name IS NULL` appear at the bottom.

**Appointing President Fields — Storage (PEOP-02)**
- D-08: `appointing_president` is a free-text VARCHAR(200). Operator types the president's name.
- D-09: `appointing_president_party` is a VARCHAR(50) stored as plain text. The frontend renders a `<select>` dropdown with a fixed option list. Valid options: `Democratic`, `Republican`, `Whig`, `Federalist`, `Democratic-Republican`, `Independent`. Empty/null is valid.
- D-10: No party field is stored directly on the person (no "Justice's own party"). The party field always refers to the appointing president's party affiliation.

**Edit Form Layout**
- D-11: Basic Info section expands to include name parts below `full_name` — Row 1: `full_name` full-width; Row 2: 4-column name-parts grid (`first_name | middle_name | last_name | name_suffix`).
- D-12: New "Appointment" section added as 4th section after Court Tenure with `appointing_president` text input and `appointing_president_party` select dropdown.
- D-13: Page `<h1>` displays `data.person.full_name`.
- D-14: Final form section order: Basic Info → Bio & Photo → Court Tenure → Appointment. Single "Save changes" button unchanged.

### Claude's Discretion
- Exact column widths for the 4-input name parts row (4-column on desktop, 2-column on tablet/mobile)
- Whether `name_suffix` uses a small input (free text input is fine)
- Exact label wording for the Appointment section header
- Whether the Appointment section shows a note ("Leave blank for advocates") — silence is fine
- Amber chip colors and form styling follow the Phase 8 admin dark theme tokens

### Deferred Ideas (OUT OF SCOPE)
- Public display of name parts and appointing president — Phase 14 (Speaker Popover Card) consumes these
- Advocate-specific party or affiliation fields (ADV-01 deferred to v1.3+)
- Backfilling name parts from existing full_name values — intentionally deferred
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PEOP-01 | Operator can enter and edit structured name fields (first name, last name, middle name, suffix) on a person record in addition to the existing full name | Migration 0006 adds four name columns; ORM/schema/service/form all extended; derivation logic in `update_person()` service |
| PEOP-02 | Operator can enter and edit appointing president name and party affiliation on a person record | Migration 0006 adds two appointment columns; schema has free-text + fixed-option select; `PersonUpdate` mass-assignment guard extended |
</phase_requirements>

---

## Summary

Phase 9 is a pure extension phase — no new tables, no new routes, no new UI pages. Every change is additive and nullable, so existing data is fully preserved. The work spans four layers: (1) a single Alembic migration adding six columns, (2) ORM model attribute additions, (3) Pydantic schema field additions on two classes, (4) service-layer derivation logic, and (5) form extension in two SvelteKit files.

The `full_name` resolution anchor is not touched by any of these changes. The derivation logic fires only when `first_name` is non-empty on save; existing rows without name parts continue to use their current `full_name` unchanged. The directory sort change is a single `ORDER BY` swap in the service layer.

The existing Phase 8 code is well-structured for this extension — the `update_person()` service function already receives a `PersonUpdate` Pydantic model; adding six new `Optional[str] = None` fields to that model and handling them in the service body is the complete backend change. The SvelteKit form action already extracts individual form fields via `formData.get()`; adding six more extractions and including them in the PATCH JSON body follows the exact established pattern.

**Primary recommendation:** Implement in strict layer order — migration first, ORM second, schemas third, service fourth, routes (no changes needed), SvelteKit server fifth, SvelteKit component sixth. Never run the service changes before the migration is applied or SQLAlchemy will raise `InvalidRequestError` on the unknown attributes.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema columns (DDL) | Database / Alembic | — | Alembic is sole DDL authority per CLAUDE.md; never `create_all` |
| ORM model attributes | API / Backend | — | SQLAlchemy ORM mirrors DB schema; must match migration columns exactly |
| PATCH validation + mass-assignment guard | API / Backend (Pydantic schema) | — | `PersonUpdate` is the only allowed surface area for writes |
| full_name derivation logic | API / Backend (service) | — | Server-side only per D-04; no client-side preview |
| Directory sort | API / Backend (service query) | — | `list_people()` query is the canonical sort source |
| Admin edit form UI | Frontend Server (SvelteKit) | — | `+page.svelte` and `+page.server.ts` — inline style pattern from Phase 8 |
| FASTAPI_BASE_URL | Frontend Server only | — | Must never be PUBLIC_ per CLAUDE.md |

---

## Standard Stack

### Core (installed, verified from `.venv`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alembic | 1.18.4 | DDL migrations via `op.add_column` | Sole DDL authority per CLAUDE.md; chained from 0005 |
| sqlalchemy | 2.0.51 | ORM `Column(String(N), nullable=True)` on `Person` model | Project ORM; async engine configured |
| pydantic | 2.13.4 | `Optional[str] = None` fields on `PersonDetail` and `PersonUpdate` | Project v2 schema layer; mass-assignment guard lives here |
| SvelteKit 2.x | (app/package.json) | `+page.server.ts` form action; `+page.svelte` component extension | Project frontend framework; established Phase 8 pattern |
| Svelte 5 | (app/package.json) | `$state`, `$props`, `$derived` runes | Project UI reactivity; no legacy stores |

[VERIFIED: project venv and codebase]

**No new packages are installed in this phase.** All capabilities are covered by the existing stack.

---

## Package Legitimacy Audit

No external packages are installed in Phase 9. This section is not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
     |
     | POST ?/save (formData — 11 fields including 6 new)
     v
SvelteKit +page.server.ts (save action)
     |   formData.get('first_name') ... formData.get('appointing_president_party')
     |   JSON.stringify({ full_name, role_id, bio_text, photo_url, tenures,
     |                    first_name, middle_name, last_name, name_suffix,
     |                    appointing_president, appointing_president_party })
     | PATCH /api/admin/people/{id}
     v
FastAPI PATCH /people/{person_id}
     |   body: PersonUpdate (Pydantic — 11 fields; mass-assignment guard)
     v
admin_people.update_person(db, person_id, body)
     |   if body.first_name:  ← derivation branch
     |       person.full_name = _derive_full_name(...)
     |   person.first_name = body.first_name  (all 6 nullable assigns)
     |   await db.commit()
     v
PostgreSQL people table
     |   (migration 0006 has already added 6 nullable columns)
     v
get_person_detail() — returns refreshed dict including all 6 new fields
     v
PersonDetail response → SvelteKit redirect(303) → page reloads with fresh data
```

### Recommended Project Structure

No new files or directories. Phase 9 modifies existing files:

```
alembic/versions/
└── 0006_add_structured_name_fields.py   ← NEW (migration)

api/models/
└── models.py                             ← MODIFY (Person class — 6 new Column entries)

api/schemas/
└── admin_people.py                       ← MODIFY (PersonDetail + PersonUpdate — 6 new fields each)

api/services/
└── admin_people.py                       ← MODIFY (update_person derivation; list_people sort; get_person_detail return dict)

app/src/routes/admin/people/
├── +page.server.ts                       ← MODIFY (directory sort — no code change; sort is in FastAPI service)
└── [id]/
    ├── +page.server.ts                   ← MODIFY (PersonDetail interface; formData extraction; PATCH body)
    └── +page.svelte                      ← MODIFY (name-parts grid; Appointment section)
```

### Pattern 1: Alembic `op.add_column` — Multiple Nullable Columns

**What:** Each new column is a separate `op.add_column` call. Downgrade reverses in opposite column order.
**When to use:** All DDL changes in this project.

```python
# Source: verified from alembic/versions/0005_add_person_metadata.py
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("people", sa.Column("first_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("last_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("middle_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("name_suffix", sa.String(50), nullable=True))
    op.add_column("people", sa.Column("appointing_president", sa.String(200), nullable=True))
    op.add_column("people", sa.Column("appointing_president_party", sa.String(50), nullable=True))

def downgrade() -> None:
    op.drop_column("people", "appointing_president_party")
    op.drop_column("people", "appointing_president")
    op.drop_column("people", "name_suffix")
    op.drop_column("people", "middle_name")
    op.drop_column("people", "last_name")
    op.drop_column("people", "first_name")
```

[VERIFIED: project codebase — matches 0005 pattern exactly]

### Pattern 2: SQLAlchemy ORM Model Extension

**What:** Add `Column(String(N), nullable=True)` entries to the existing `Person` class. Order after existing columns. No `server_default` needed — NULL is correct.
**When to use:** Whenever the migration adds columns that the service layer must read/write.

```python
# Source: verified from api/models/models.py Person class pattern
class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(300), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    bio_text = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    # Phase 9 additions:
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    middle_name = Column(String(150), nullable=True)
    name_suffix = Column(String(50), nullable=True)
    appointing_president = Column(String(200), nullable=True)
    appointing_president_party = Column(String(50), nullable=True)
```

[VERIFIED: project codebase]

### Pattern 3: Pydantic v2 Schema Extension

**What:** Add `Optional[str] = None` to both `PersonDetail` (response) and `PersonUpdate` (PATCH body). The mass-assignment guard in `PersonUpdate` is the only surface area for writes — omitting a field from `PersonUpdate` means it can never be written.

```python
# Source: verified from api/schemas/admin_people.py
from typing import Optional

class PersonDetail(BaseModel):
    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: list[TenureRow] = []
    # Phase 9 additions:
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    appointing_president: Optional[str] = None
    appointing_president_party: Optional[str] = None

class PersonUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureRow]] = None
    # Phase 9 additions (mass-assignment guard extension):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    appointing_president: Optional[str] = None
    appointing_president_party: Optional[str] = None
```

[VERIFIED: project codebase — extends existing pattern]

### Pattern 4: Service Layer — Derivation Helper + Column Assignment

**What:** Private helper function `_derive_full_name` joins non-blank parts; called in `update_person()` only when `first_name` is non-empty (D-04/D-05).

```python
# Source: verified pattern from api/services/admin_people.py + CONTEXT.md D-04/D-05 Specifics

def _derive_full_name(first: str, middle: str | None, last: str, suffix: str | None) -> str:
    """Derive full_name from structured name parts (D-04).

    Joins non-blank parts with a single space.
    Middle and suffix are omitted when blank/None.
    Example: first='Amy', middle='Coney', last='Barrett' -> 'Amy Coney Barrett'
    """
    return " ".join(p for p in [first, middle or "", last, suffix or ""] if p)


# Inside update_person(), after the existing full_name / role_id / bio_text / photo_url block:
# Normalize new string fields to None when empty (same pattern as bio_text/photo_url)
person.first_name = body.first_name if body.first_name else None
person.last_name = body.last_name if body.last_name else None
person.middle_name = body.middle_name if body.middle_name else None
person.name_suffix = body.name_suffix if body.name_suffix else None
person.appointing_president = body.appointing_president if body.appointing_president else None
person.appointing_president_party = body.appointing_president_party if body.appointing_president_party else None

# Derivation: overwrite full_name only when first_name is non-empty (D-04/D-05)
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name,
        body.middle_name,
        body.last_name,
        body.name_suffix,
    )
```

**Note on derivation trigger:** The CONTEXT.md says "when `first_name` is non-empty" (D-04), but a useful real-world guard is to also require `last_name` — a first name alone is not enough to derive a meaningful `full_name`. Claude's discretion applies here; requiring both `first_name` and `last_name` is the safer choice.

[VERIFIED: project codebase + CONTEXT.md D-04/D-05]

### Pattern 5: get_person_detail Return Dict Extension

**What:** The `get_person_detail()` function returns a dict that is wrapped in `PersonDetail(**p)` by the router. The dict must include all six new fields; they come directly from the ORM `person` object (nullable → None when unset).

```python
# Source: verified from api/services/admin_people.py get_person_detail()
return {
    "id": person.id,
    "full_name": person.full_name,
    "role_id": person.role_id,
    "role_name": role_name,
    "bio_text": person.bio_text,
    "photo_url": person.photo_url,
    "tenures": [...],
    # Phase 9 additions:
    "first_name": person.first_name,
    "last_name": person.last_name,
    "middle_name": person.middle_name,
    "name_suffix": person.name_suffix,
    "appointing_president": person.appointing_president,
    "appointing_president_party": person.appointing_president_party,
}
```

[VERIFIED: project codebase — dict literal extension pattern]

### Pattern 6: list_people Sort Change

**What:** A single `ORDER BY` clause change in the `list_people()` query. The secondary `full_name ASC` sort ensures stable ordering among records sharing a `last_name` or having no `last_name`.

```python
# Source: verified from api/services/admin_people.py list_people() + CONTEXT.md D-07 Specifics
from sqlalchemy import asc, nulls_last  # or use .nulls_last() method on column

# Replace: .order_by(Person.full_name)
# With:
.order_by(Person.last_name.nulls_last(), Person.full_name.asc())
```

[VERIFIED: project codebase — SQLAlchemy 2.0.51 `.nulls_last()` method is available]

### Pattern 7: SvelteKit +page.server.ts Interface and Action Extension

**What:** The `PersonDetail` TypeScript interface in `+page.server.ts` must gain six optional fields. The `save` action extracts six new form fields via `formData.get()` and includes them in the PATCH body.

```typescript
// Source: verified from app/src/routes/admin/people/[id]/+page.server.ts

// Interface extension (add to existing PersonDetail interface):
interface PersonDetail {
    id: number;
    full_name: string;
    role_id: number | null;
    role_name: string | null;
    bio_text: string | null;
    photo_url: string | null;
    tenures: Array<{ seat: string | null; start_date: string | null; end_date: string | null; }>;
    // Phase 9 additions:
    first_name: string | null;
    last_name: string | null;
    middle_name: string | null;
    name_suffix: string | null;
    appointing_president: string | null;
    appointing_president_party: string | null;
}

// In save action — add after photo_url extraction:
const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
const last_name = ((formData.get('last_name') as string) ?? '').trim() || null;
const middle_name = ((formData.get('middle_name') as string) ?? '').trim() || null;
const name_suffix = ((formData.get('name_suffix') as string) ?? '').trim() || null;
const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '') || null;

// In body: JSON.stringify({ ..., first_name, last_name, middle_name, name_suffix,
//                           appointing_president, appointing_president_party })
```

**Note on `appointing_president_party`:** This comes from a `<select>` — `.trim()` is unnecessary but harmless; the empty string `''` from the blank option converts to `null` via `|| null`.

[VERIFIED: project codebase — exact formData.get pattern from +page.server.ts]

### Pattern 8: SvelteKit +page.svelte — Name-Parts Grid and Appointment Section

**What:** The `+page.svelte` component adds a 4-input grid inside the Basic Info section and a new Appointment section after Court Tenure. No new `$state` variables are needed — all six fields are simple inputs read on form submit (not tracked in reactive state). Values pre-populate from `data.person.first_name ?? ''` etc.

Key detail: The name-parts inputs do NOT need `$state` tracking because they are submitted as plain form fields. The existing `tenureRows` are the only reactive state (managed separately via `$state<TenureRow[]>`).

```svelte
<!-- Source: 09-UI-SPEC.md + verified pattern from +page.svelte -->

<!-- Inside Section 1: Basic Info, after full_name input, before role select -->
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: 16px; margin-bottom: 16px;">
    <!-- first_name -->
    <div>
        <label for="first_name" style="display: block; font-size: 14px; color: #94a3b8; margin-bottom: 8px;">
            First name
        </label>
        <input id="first_name" name="first_name" type="text"
            value={data.person.first_name ?? ''}
            style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;" />
    </div>
    <!-- middle_name, last_name, name_suffix follow same pattern -->
</div>

<!-- Section 4: Appointment — see 09-UI-SPEC.md for exact HTML -->
```

[VERIFIED: 09-UI-SPEC.md approved design contract + project codebase patterns]

### Anti-Patterns to Avoid

- **Calling `Base.metadata.create_all()`:** The project constraint is absolute — Alembic only. Never call `create_all` anywhere (CLAUDE.md).
- **Setting `server_default` on the new columns:** All six columns should be `nullable=True` with no default. A `server_default=None` or `server_default=''` would be incorrect and inconsistent with the "no backfill" decision (D-03).
- **Adding `full_name` to the derivation when `first_name` is empty:** D-05 is explicit — if `first_name` is null/empty, `full_name` is left unchanged. Do not overwrite it with a partial derivation.
- **Exposing `FASTAPI_BASE_URL` with `PUBLIC_` prefix:** Project-wide constraint — server-only env var (CLAUDE.md and established pattern).
- **Adding reactive `$state` for the six new form fields in `+page.svelte`:** Unnecessary. Plain inputs submitted via the form work correctly with the existing `use:enhance` pattern. Adding `$state` would add complexity with no benefit.
- **Forgetting to extend `get_person_detail()` return dict:** The router does `PersonDetail(**p)` — if the dict lacks the new keys, Pydantic v2 will use the field defaults (`None`), which silently drops any previously saved data on reload. The dict must explicitly include all six new fields.
- **Ordering `last_name NULLS LAST` only:** The secondary sort by `full_name ASC` is required for stable ordering among null-`last_name` records. Without it, the order of incomplete records is database-dependent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nullable column DDL | Inline SQL `ALTER TABLE` | `alembic op.add_column` | Alembic is sole DDL authority; hand-rolled DDL bypasses the revision chain |
| PATCH body validation | Manual dict parsing | Pydantic `PersonUpdate` model | Mass-assignment guard already in place; extending the model is the correct surface |
| full_name derivation | Complex regex | `" ".join(p for p in [...] if p)` | Project's own CONTEXT.md Specifics already documents this 1-line pattern |
| `NULLS LAST` sort | Python-side sort after query | SQLAlchemy `.nulls_last()` | Database-side sort is correct for paginated/filtered queries |

---

## Runtime State Inventory

This is not a rename/refactor phase. However, there is one runtime state consideration:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing `people` rows — all six new columns will be NULL after migration runs | No action — NULL is correct; operators fill in via the form |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no new env vars introduced | None |
| Build artifacts | None | None |

**Migration run sequence:** The Alembic migration must be run before the application server restarts with the new ORM model. If the server starts with the new `Person` model columns before the migration runs, SQLAlchemy will not error on startup (columns are declared but not validated against live schema), but any query that reads/writes the new columns will fail at runtime with a database-level `column does not exist` error.

**Recommended execution sequence for the plan:**
1. Write migration file
2. Write ORM model update
3. Write schema/service/route updates
4. Write SvelteKit updates
5. Run `alembic upgrade head`
6. Test end-to-end

---

## Common Pitfalls

### Pitfall 1: Migration Runs Before ORM Is Updated (or Vice Versa)

**What goes wrong:** If the migration runs but the ORM model is not updated, the columns exist in the DB but SQLAlchemy does not know about them — reads return `AttributeError`. If the ORM is updated but the migration has not run, runtime queries fail with PostgreSQL `column "first_name" does not exist`.
**Why it happens:** The migration and ORM are separate artifacts that must be kept in sync.
**How to avoid:** Always write both in the same plan wave and note the dependency: ORM change is safe to write before migration runs (it's just Python), but the server must not call any endpoint that touches the new columns until after `alembic upgrade head`.
**Warning signs:** `AttributeError: 'Person' object has no attribute 'first_name'` or `psycopg2.errors.UndefinedColumn`.

### Pitfall 2: Forgetting to Include New Fields in `get_person_detail()` Return Dict

**What goes wrong:** The PATCH saves correctly (SQLAlchemy writes the values), but the page reloads with `None` in all six fields because `get_person_detail()` is called after commit and doesn't include the new keys in the returned dict. Pydantic v2 uses the schema defaults (`None`) silently.
**Why it happens:** The service function builds a dict literal — adding columns to the ORM model does NOT automatically include them in the dict.
**How to avoid:** Treat the `get_person_detail()` return dict as a checklist against `PersonDetail` schema fields. Every field in `PersonDetail` must appear in the dict.
**Warning signs:** Save succeeds (no error), but refreshed page shows empty name-parts fields even after saving real values.

### Pitfall 3: Derivation Overwrites full_name When first_name Is Provided Without last_name

**What goes wrong:** Operator types only `first_name` (e.g., "Amy") and saves. Service derives `full_name = "Amy"`, destroying the existing `full_name = "Amy Coney Barrett"` that the resolver depends on.
**Why it happens:** D-04 says "when `first_name` is non-empty" — but a single first name alone cannot produce a valid full name.
**How to avoid:** Guard derivation on both `first_name` AND `last_name` being non-empty. If either is missing, leave `full_name` unchanged.
**Warning signs:** Resolver begins returning no matches for previously-resolved speakers after a partial form save.

### Pitfall 4: Empty String in `appointing_president_party` Select Not Normalized to None

**What goes wrong:** Operator selects "— No party —" (value `""`). The form sends `appointing_president_party=""`. Service stores `""` (empty string) instead of `NULL`. The IS NULL filter for incomplete records continues to show this person as "complete" for a field that has no meaningful data.
**Why it happens:** Empty string and NULL are different in PostgreSQL. The project's pattern (`if body.field else None`) handles this correctly — but only if it's applied to the party field.
**How to avoid:** Apply the same `if body.appointing_president_party else None` normalization used for `bio_text` and `photo_url`.

### Pitfall 5: TypeScript `PersonDetail` Interface Not Updated in `+page.server.ts`

**What goes wrong:** The FastAPI response includes the six new fields, but the TypeScript interface `PersonDetail` in `+page.server.ts` does not declare them. TypeScript will not error at runtime (JSON is parsed dynamically), but the `data.person.first_name` reference in `+page.svelte` will be typed as `unknown` and may cause TypeScript compiler errors or undefined values in the form.
**Why it happens:** TypeScript interfaces are not automatically synced from Pydantic schemas.
**How to avoid:** Update the `PersonDetail` interface in `+page.server.ts` alongside the schema changes.

### Pitfall 6: Name-Parts Grid Breaks on Mobile Without Media Query

**What goes wrong:** 4-column grid on a narrow mobile viewport causes inputs to overflow or be too small to interact with comfortably.
**Why it happens:** `grid-template-columns: 1fr 1fr 1fr 80px` does not self-collapse.
**How to avoid:** Add a `<style>` block or inline `@media` at the grid container to collapse to 2-column below 640px. The UI-SPEC prescribes this breakpoint. (Note: the project uses inline styles throughout — a `<style>` block scoped to the component is acceptable and consistent with Phase 8 patterns.)

---

## Code Examples

All examples are drawn directly from the project codebase.

### Alembic Migration 0006 — Complete Template

```python
# Source: verified from alembic/versions/0005_add_person_metadata.py pattern
"""Add structured name fields and appointment fields to people table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-19

Adds six nullable columns to the people table to support the Phase 9 People
Data Model Migration. All columns default to NULL — no backfill (D-03).

  - first_name VARCHAR(150): structured first name
  - last_name VARCHAR(150): structured last name; used for directory sort (D-07)
  - middle_name VARCHAR(150): structured middle name
  - name_suffix VARCHAR(50): name suffix (Jr., Sr., II, etc.)
  - appointing_president VARCHAR(200): free-text name of appointing president (D-08)
  - appointing_president_party VARCHAR(50): appointing president's party affiliation (D-09)
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("first_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("last_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("middle_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("name_suffix", sa.String(50), nullable=True))
    op.add_column("people", sa.Column("appointing_president", sa.String(200), nullable=True))
    op.add_column("people", sa.Column("appointing_president_party", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("people", "appointing_president_party")
    op.drop_column("people", "appointing_president")
    op.drop_column("people", "name_suffix")
    op.drop_column("people", "middle_name")
    op.drop_column("people", "last_name")
    op.drop_column("people", "first_name")
```

### `_derive_full_name` Helper

```python
# Source: CONTEXT.md Specifics + verified pattern from admin_people.py helpers

def _derive_full_name(first: str, middle: str | None, last: str, suffix: str | None) -> str:
    """Derive full_name from structured name parts (D-04).

    Joins non-blank parts with a single space.
    Middle and suffix are omitted when blank/None.
    Examples:
      first='Amy', middle='Coney', last='Barrett' → 'Amy Coney Barrett'
      first='John', middle=None, last='Roberts', suffix='Jr.' → 'John Roberts Jr.'
      first='Ketanji', middle='Brown', last='Jackson' → 'Ketanji Brown Jackson'
    """
    return " ".join(p for p in [first, middle or "", last, suffix or ""] if p)
```

### SQLAlchemy `.nulls_last()` Sort

```python
# Source: verified from SQLAlchemy 2.0.51 installed in project venv
# Replace the existing ORDER BY in list_people():
.order_by(Person.last_name.nulls_last(), Person.full_name.asc())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `full_name` string | `full_name` + 4 structured name parts | Phase 9 | Enables last_name directory sort; enables popover display (Phase 14) |
| No appointment data | `appointing_president` + `appointing_president_party` columns | Phase 9 | Enables bench speaker popover (Phase 14 consumes) |
| Directory sorted by `full_name` | Sorted by `last_name NULLS LAST, full_name ASC` | Phase 9 | Operators can scan by surname; incomplete records float to bottom |

**Deprecated/outdated in this phase:**
- `list_people()` `ORDER BY people.full_name` — replaced by `ORDER BY people.last_name NULLS LAST, people.full_name ASC`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `alembic upgrade head` is the correct command to run the migration in this project's dev environment | Environment Availability | Low — standard Alembic command; verified against installed version |
| A2 | Derivation should require BOTH `first_name` AND `last_name` non-empty (not just `first_name` per D-04 literal text) | Pattern 4 | Medium — if only `first_name` required, operator can accidentally overwrite full_name with a single-word value; the "both required" guard is safer |

---

## Open Questions (RESOLVED)

1. **Derivation guard: `first_name` only, or `first_name` AND `last_name`?**
   - What we know: D-04 says "when `first_name` is non-empty." D-05 says "if `first_name` is null or empty, `full_name` is left unchanged."
   - What's unclear: Whether providing `first_name` without `last_name` should derive `full_name = "Amy"` (overwriting "Amy Coney Barrett") or leave `full_name` unchanged.
   - Recommendation: Require both `first_name` AND `last_name` non-empty to trigger derivation. This is a safe default — the planner can add a comment noting the deviation from D-04's literal text, and the user can override during plan review.
   - **RESOLVED:** Both-field guard adopted per Pitfall 3 — deviation from D-04 literal text confirmed by user. Derivation fires only when `first_name AND last_name` are both non-empty, preventing anchor corruption from partial name entry.

2. **`PersonListItem.missing` — should `first_name`/`last_name` absence be flagged as "missing"?**
   - What we know: The current incomplete filter checks `role_id`, `bio_text`, and `photo_url`. D-04 defines these as the three "missing" signals. PEOP-01 adds name parts as new fields.
   - What's unclear: Whether the "missing fields" filter and amber chip should count absent `first_name`/`last_name` as incomplete.
   - Recommendation: Keep the existing incomplete filter definition (role/bio/photo only). Adding name parts to the filter is a separate product decision not covered by PEOP-01 or PEOP-02. The planner should NOT add this unless the user confirms.
   - **RESOLVED:** Incomplete filter unchanged — name parts absence is NOT flagged as missing. Existing role/bio/photo-only definition retained per PEOP-01/PEOP-02 scope.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | All backend changes | ✓ | Python 3.14.4 | — |
| alembic | Migration 0006 | ✓ | 1.18.4 | — |
| sqlalchemy | ORM model update | ✓ | 2.0.51 | — |
| pydantic | Schema update | ✓ | 2.13.4 | — |
| Node.js / npm | SvelteKit changes | ✓ | Node 24.15.0 / npm 11.12.1 | — |
| PostgreSQL | Migration target | ✓ (local dev data dir) | 16.x (from project setup) | — |

**Missing dependencies with no fallback:** None.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | Admin-only route; HMAC session cookie gate in `hooks.server.ts`; no new public exposure |
| V5 Input Validation | yes | Pydantic `PersonUpdate` validates all six new fields; empty-string normalization to None |
| V2 Authentication | no | No new auth surface; existing HMAC session cookie unchanged |
| V6 Cryptography | no | No cryptographic operations |

**Phase 9 specific security notes:**

- The six new fields are admin-only. `appointing_president_party` is intentionally not surfaced in any public API response in this phase — Phase 14 will handle that read path. The `PersonDetail` schema is returned by `GET /api/admin/people/{id}` which requires the admin auth dependency.
- The party dropdown options are enforced by the UI, not by a DB-level CHECK constraint. The DB accepts any VARCHAR(50). This is consistent with the CONTEXT.md decision (D-09) and is an intentional tradeoff (fewer than 50 known values; operator-only access; CHECK constraint adds migration complexity with no meaningful security benefit for an admin-only field).
- Mass-assignment guard: `PersonUpdate` is the sole write surface for the PATCH endpoint. The six new fields must be explicitly added to `PersonUpdate` — they cannot be injected via any other path.

---

## Sources

### Primary (HIGH confidence — verified from project codebase)
- `alembic/versions/0005_add_person_metadata.py` — canonical migration pattern for `op.add_column`
- `alembic/versions/0004_add_arguments_resolved_at.py` — second migration pattern example
- `api/models/models.py` — `Person` model; current columns; `Column(String(N), nullable=True)` pattern
- `api/schemas/admin_people.py` — `PersonDetail`, `PersonUpdate`, `Optional[str] = None` pattern
- `api/services/admin_people.py` — `update_person()`, `_missing_fields()`, `list_people()` patterns
- `api/routers/admin.py` — PATCH route; mass-assignment guard; `PersonDetail(**updated)` pattern
- `app/src/routes/admin/people/[id]/+page.server.ts` — `formData.get()`, `redirect(303)` pattern
- `app/src/routes/admin/people/[id]/+page.svelte` — Svelte 5 Runes, inline styles, Phase 8 form structure
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — all locked decisions D-01 through D-14
- `.planning/phases/09-people-data-model-migration/09-UI-SPEC.md` — approved visual contract

### Secondary (MEDIUM confidence — installed versions verified)
- `.venv/Scripts/python` — `alembic 1.18.4`, `sqlalchemy 2.0.51`, `pydantic 2.13.4` confirmed

---

## Metadata

**Confidence breakdown:**
- Migration pattern: HIGH — copied from existing 0005 in the same project
- ORM model extension: HIGH — copied from existing `Person` class pattern
- Schema extension: HIGH — copied from existing `PersonDetail` / `PersonUpdate` pattern
- Derivation logic: HIGH — CONTEXT.md Specifics provides the exact Python one-liner
- SvelteKit form action: HIGH — copied from existing `save` action pattern in `+page.server.ts`
- SvelteKit component: HIGH — 09-UI-SPEC.md provides exact HTML; pattern from `+page.svelte`
- Sort change: HIGH — SQLAlchemy `.nulls_last()` method verified in 2.0.51

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable stack; no fast-moving dependencies)
