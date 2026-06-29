# Phase 9: People Data Model Migration - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 6 (1 new, 5 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `alembic/versions/0006_add_structured_name_fields.py` | migration | batch | `alembic/versions/0005_add_person_metadata.py` | exact |
| `api/models/models.py` | model | CRUD | `api/models/models.py` `Person` class (current) | exact |
| `api/schemas/admin_people.py` | schema | request-response | `api/schemas/admin_people.py` (current `PersonDetail` / `PersonUpdate`) | exact |
| `api/services/admin_people.py` | service | CRUD | `api/services/admin_people.py` (current `update_person` / `list_people` / `get_person_detail`) | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` | route / server | request-response | `app/src/routes/admin/people/[id]/+page.server.ts` (current) | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` | component | request-response | `app/src/routes/admin/people/[id]/+page.svelte` (current) | exact |

---

## Pattern Assignments

### `alembic/versions/0006_add_structured_name_fields.py` (migration, batch)

**Analog:** `alembic/versions/0005_add_person_metadata.py`

**Full file pattern** (lines 1–37 of analog):
```python
"""Add bio_text and photo_url columns to people table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17
...
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("bio_text", sa.Text(), nullable=True))
    op.add_column("people", sa.Column("photo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("people", "photo_url")
    op.drop_column("people", "bio_text")
```

**Copy rule:** Use the same module docstring format, same four revision variables, same `op.add_column` per column. Chain `down_revision = "0005"`. Drop columns in downgrade in reverse add order. All six new columns are `sa.String(N), nullable=True` — no `server_default`, no NOT NULL.

**0006 upgrade block:**
```python
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

---

### `api/models/models.py` — `Person` class (model, CRUD)

**Analog:** `api/models/models.py` `Person` class (lines 90–98)

**Existing class to extend:**
```python
class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(300), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    bio_text = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
```

**Copy rule:** Append six new `Column` entries after `photo_url`. Use `Column(String(N), nullable=True)` with no `server_default`. Imports (`String`) are already present in the file — no new imports needed.

**Six entries to append:**
```python
    # Phase 9 additions — migration 0006
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    middle_name = Column(String(150), nullable=True)
    name_suffix = Column(String(50), nullable=True)
    appointing_president = Column(String(200), nullable=True)
    appointing_president_party = Column(String(50), nullable=True)
```

---

### `api/schemas/admin_people.py` — `PersonDetail` and `PersonUpdate` (schema, request-response)

**Analog:** `api/schemas/admin_people.py` (lines 47–78)

**Existing `PersonDetail` to extend** (lines 47–61):
```python
class PersonDetail(BaseModel):
    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: list[TenureRow] = []

    model_config = {"from_attributes": True}
```

**Existing `PersonUpdate` to extend** (lines 64–78):
```python
class PersonUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureRow]] = None
```

**Copy rule:** Append six `Optional[str] = None` fields to BOTH classes before the closing line / `model_config`. Use the exact same `Optional[str] = None` pattern — no validators, no aliases, no constraints. The `from typing import Optional` import is already present.

**Six fields for both classes:**
```python
    # Phase 9 additions
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    appointing_president: Optional[str] = None
    appointing_president_party: Optional[str] = None
```

**Mass-assignment note:** Adding to `PersonUpdate` is the only path by which these fields can be written. If omitted from `PersonUpdate`, the PATCH endpoint cannot write them regardless of what the form sends.

---

### `api/services/admin_people.py` — three functions (service, CRUD)

**Analog:** `api/services/admin_people.py` (lines 100–209)

#### Change 1: `list_people()` — sort clause (lines 109–113)

**Existing `ORDER BY`:**
```python
    q = (
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(Person.full_name)
    )
```

**Replacement `ORDER BY`:**
```python
        .order_by(Person.last_name.nulls_last(), Person.full_name.asc())
```

`nulls_last()` is a SQLAlchemy 2.0 column-method — no additional import needed (SQLAlchemy 2.0.51 is installed). Secondary `full_name.asc()` keeps stable ordering among null-`last_name` records.

#### Change 2: `get_person_detail()` — return dict extension (lines 159–174)

**Existing return dict:**
```python
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

**Six keys to append before the closing `}`:**
```python
        "first_name": person.first_name,
        "last_name": person.last_name,
        "middle_name": person.middle_name,
        "name_suffix": person.name_suffix,
        "appointing_president": person.appointing_president,
        "appointing_president_party": person.appointing_president_party,
```

**Critical:** If these keys are omitted, Pydantic v2 silently defaults them to `None` on page reload — saved values disappear.

#### Change 3: `update_person()` — derivation helper + column assignments (lines 177–209)

**Existing empty-string normalization pattern** (lines 200–202) — copy for all six new fields:
```python
    person.bio_text = body.bio_text if body.bio_text else None
    person.photo_url = body.photo_url if body.photo_url else None
```

**Add before `await db.commit()`:**

Private helper (add at module top-level, below `_replace_tenures`):
```python
def _derive_full_name(first: str, middle: str | None, last: str, suffix: str | None) -> str:
    """Derive full_name from structured name parts (D-04).

    Joins non-blank parts with a single space.
    Middle and suffix are omitted when blank/None.
    Example: first='Amy', middle='Coney', last='Barrett' -> 'Amy Coney Barrett'
    """
    return " ".join(p for p in [first, middle or "", last, suffix or ""] if p)
```

Column assignments in `update_person()`, after the existing `photo_url` normalization line:
```python
    # Phase 9: normalize empty strings to None (same pattern as bio_text/photo_url)
    person.first_name = body.first_name if body.first_name else None
    person.last_name = body.last_name if body.last_name else None
    person.middle_name = body.middle_name if body.middle_name else None
    person.name_suffix = body.name_suffix if body.name_suffix else None
    person.appointing_president = body.appointing_president if body.appointing_president else None
    person.appointing_president_party = body.appointing_president_party if body.appointing_president_party else None

    # Derivation: overwrite full_name only when BOTH first_name and last_name are non-empty (D-04/D-05)
    # Requiring both prevents overwriting a valid full_name with a partial "Amy" string (Pitfall 3)
    if body.first_name and body.last_name:
        person.full_name = _derive_full_name(
            body.first_name,
            body.middle_name,
            body.last_name,
            body.name_suffix,
        )
```

---

### `app/src/routes/admin/people/[id]/+page.server.ts` (route/server, request-response)

**Analog:** `app/src/routes/admin/people/[id]/+page.server.ts` (lines 1–179)

**Existing `PersonDetail` interface to extend** (lines 13–25):
```typescript
interface PersonDetail {
    id: number;
    full_name: string;
    role_id: number | null;
    role_name: string | null;
    bio_text: string | null;
    photo_url: string | null;
    tenures: Array<{
        seat: string | null;
        start_date: string | null;
        end_date: string | null;
    }>;
}
```

**Six fields to append to the interface:**
```typescript
    // Phase 9 additions
    first_name: string | null;
    last_name: string | null;
    middle_name: string | null;
    name_suffix: string | null;
    appointing_president: string | null;
    appointing_president_party: string | null;
```

**Existing `formData.get` extraction pattern** (lines 94–99) — copy for all six new fields:
```typescript
    const full_name = ((formData.get('full_name') as string) ?? '').trim();
    const bio_text = ((formData.get('bio_text') as string) ?? '').trim() || null;
    const photo_url = ((formData.get('photo_url') as string) ?? '').trim() || null;
```

**Six extractions to add after `photo_url` extraction, before `tenuresRaw`:**
```typescript
    const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
    const last_name = ((formData.get('last_name') as string) ?? '').trim() || null;
    const middle_name = ((formData.get('middle_name') as string) ?? '').trim() || null;
    const name_suffix = ((formData.get('name_suffix') as string) ?? '').trim() || null;
    const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
    const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '') || null;
```

Note: `appointing_president_party` skips `.trim()` (value comes from a `<select>`) — the empty string `''` still converts to `null` via `|| null`.

**Existing PATCH body** (line 127):
```typescript
body: JSON.stringify({ full_name, role_id, bio_text, photo_url, tenures }),
```

**Updated PATCH body — include all six new variables:**
```typescript
body: JSON.stringify({
    full_name, role_id, bio_text, photo_url, tenures,
    first_name, last_name, middle_name, name_suffix,
    appointing_president, appointing_president_party
}),
```

---

### `app/src/routes/admin/people/[id]/+page.svelte` (component, request-response)

**Analog:** `app/src/routes/admin/people/[id]/+page.svelte` (current file)

**Existing input pattern** (lines 131–145) — copy for all six new inputs:
```svelte
<div style="margin-bottom: 16px;">
    <label
        for="full_name"
        style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
    >
        Full name
    </label>
    <input
        id="full_name"
        name="full_name"
        type="text"
        value={data.person.full_name}
        style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
    />
</div>
```

**Existing section card wrapper** (lines 122–128) — copy for Appointment section:
```svelte
<div
    style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
>
    <h2
        style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
    >
        Basic Info
    </h2>
```

**New name-parts grid — insert inside Section 1 (Basic Info), after the `full_name` `<div>`, before the Role `<div>` at line 148:**
```svelte
<!-- Name parts — 4-column on desktop, 2-column on mobile -->
<div style="margin-bottom: 16px;">
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: 12px;">
        <div>
            <label for="first_name" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">First name</label>
            <input id="first_name" name="first_name" type="text"
                value={data.person.first_name ?? ''}
                style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;" />
        </div>
        <div>
            <label for="middle_name" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">Middle name</label>
            <input id="middle_name" name="middle_name" type="text"
                value={data.person.middle_name ?? ''}
                style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;" />
        </div>
        <div>
            <label for="last_name" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">Last name</label>
            <input id="last_name" name="last_name" type="text"
                value={data.person.last_name ?? ''}
                style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;" />
        </div>
        <div>
            <label for="name_suffix" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">Suffix</label>
            <input id="name_suffix" name="name_suffix" type="text"
                value={data.person.name_suffix ?? ''}
                style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;" />
        </div>
    </div>
</div>
```

**Responsive collapse for mobile — add a `<style>` block** (scoped component style, placed after `</main>`):
```svelte
<style>
    @media (max-width: 640px) {
        .name-parts-grid {
            grid-template-columns: 1fr 1fr !important;
        }
    }
</style>
```

Replace inline `style="display: grid; grid-template-columns: 1fr 1fr 1fr 80px; ..."` with `class="name-parts-grid"` plus the inline style for non-responsive properties. This follows the pattern established in Phase 8 (inline styles for static values; scoped `<style>` for breakpoints).

**No `$state` for name-parts inputs.** The six new fields are plain form inputs — they submit as form data via the existing `use:enhance` form. No reactive state variables. The only `$state` tracked in this file are: `localRoles`, `selectedRoleId`, `showAddRoleForm`, `roleError`, `creatingRole`, `nextKey`, `tenureRows`, `saveSubmitting`.

**New Section 4: Appointment — insert after the Court Tenure section card, before the Save button:**
```svelte
<!-- ── Section 4: Appointment ── -->
<div
    style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;"
>
    <h2
        style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;"
    >
        Appointment
    </h2>

    <!-- Appointed by -->
    <div style="margin-bottom: 16px;">
        <label for="appointing_president" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
            Appointed by
        </label>
        <input
            id="appointing_president"
            name="appointing_president"
            type="text"
            value={data.person.appointing_president ?? ''}
            style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
        />
    </div>

    <!-- Appointing president's party -->
    <div style="margin-bottom: 0;">
        <label for="appointing_president_party" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
            Appointing president's party
        </label>
        <select
            id="appointing_president_party"
            name="appointing_president_party"
            style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
        >
            <option value="" selected={!data.person.appointing_president_party}>— No party —</option>
            <option value="Democratic" selected={data.person.appointing_president_party === 'Democratic'}>Democratic</option>
            <option value="Democratic-Republican" selected={data.person.appointing_president_party === 'Democratic-Republican'}>Democratic-Republican</option>
            <option value="Federalist" selected={data.person.appointing_president_party === 'Federalist'}>Federalist</option>
            <option value="Independent" selected={data.person.appointing_president_party === 'Independent'}>Independent</option>
            <option value="Republican" selected={data.person.appointing_president_party === 'Republican'}>Republican</option>
            <option value="Whig" selected={data.person.appointing_president_party === 'Whig'}>Whig</option>
        </select>
    </div>
</div>
```

Options are alphabetical after the blank (D-09, Specifics). Each option uses `selected={...}` comparison rather than a `value` binding because this is a plain form select, not a `$state`-backed reactive select.

---

## Shared Patterns

### Empty-String Normalization to None
**Source:** `api/services/admin_people.py` lines 200–202
**Apply to:** All six new string fields in `update_person()`
```python
person.bio_text = body.bio_text if body.bio_text else None
```
Pattern: `person.field = body.field if body.field else None`. Ensures PostgreSQL `IS NULL` filters work correctly when the operator clears a field and saves.

### Server-Only Env Var Access
**Source:** `app/src/routes/admin/people/[id]/+page.server.ts` line 1
**Apply to:** All `+page.server.ts` files
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
```
`FASTAPI_BASE_URL` must never use the `PUBLIC_` prefix — it is always `$env/static/private`.

### `use:enhance` Form Submission
**Source:** `app/src/routes/admin/people/[id]/+page.svelte` lines 108–118
**Apply to:** The existing save form — pattern is unchanged. Six new inputs submit as plain form fields with no additional setup.
```svelte
use:enhance={() => {
    saveSubmitting = true;
    return async ({ result, update }) => {
        saveSubmitting = false;
        await update();
    };
}}
```

### Inline Dark Theme Tokens
**Source:** `app/src/routes/admin/people/[id]/+page.svelte` (throughout)
**Apply to:** All new inputs and the Appointment section card
```
Background:    #0f1117   (page body)
Card:          #1e293b   (section wrapper background)
Border:        #334155   (card and input borders)
Body text:     #94a3b8   (label color)
Input text:    #e2e8f0   (input value color)
Border-radius: 6px (inputs), 8px (cards)
Input padding: 8px 12px
```

### `redirect(303)` After Successful Save
**Source:** `app/src/routes/admin/people/[id]/+page.server.ts` line 138
**Apply to:** The `save` action — pattern is unchanged
```typescript
throw redirect(303, '/admin/people/' + params.id);
```
Re-runs the load function with fresh data. No additional change needed for Phase 9.

---

## No Analog Found

None — all six files have exact project analogs. Phase 9 is a pure additive extension with no structural novelty.

---

## Metadata

**Analog search scope:** `alembic/versions/`, `api/models/`, `api/schemas/`, `api/services/`, `app/src/routes/admin/people/`
**Files read:** 7 source files
**Pattern extraction date:** 2026-06-19
