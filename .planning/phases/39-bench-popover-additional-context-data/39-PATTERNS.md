# Phase 39: Bench popover — additional context data for Justices - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 12 (2 new migrations + 10 modified files)
**Analogs found:** 12 / 12 (all analogs are in-repo, prior-phase precedents — this phase modifies existing files far more than it creates new ones)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/00XX_add_person_death_date.py` (new) | migration | batch/DDL | `alembic/versions/0016_add_person_birthdate.py` | exact |
| `alembic/versions/00XX_add_constrain_tenure_reason_left.py` (new) | migration | batch/DDL | `alembic/versions/0020_rename_tenure_seat_to_office.py` + `0021_constrain_tenure_office.py` | exact (two-step add-then-constrain shape), with a documented divergence (nullable forever — see Pitfall 3 in RESEARCH.md) |
| `api/models/models.py` (modify: `Person.death_date`, `CourtTenure.reason_left`, `REASON_*` constants, `reason_left_title()`) | model | CRUD | Same file's existing `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`/`VALID_OFFICES`/`OFFICE_TITLES`/`office_title()` block (lines 137–179) | exact |
| `pipeline/commands/import_justices_csv.py` (modify: read 3 new CSV columns, null-only backfill) | service (offline CLI) | batch/transform | Same file's existing per-row read (`birthdate`/`appointed_by`/`appointing_party`, lines 204–207) and person-upgrade branch (lines 183–188) | exact |
| `api/schemas/admin_people.py` (modify: `TenureWrite.reason_left`, `TenureRow.reason_left`, `PersonDetail.death_date`, `PersonUpdate.death_date`) | model (Pydantic schema) | request-response | Same file's existing `appointing_president_party` field on `TenureWrite`/`TenureRow`, and `birthdate` field on `PersonDetail`/`PersonUpdate` | exact |
| `api/services/admin_people.py` (modify: `_replace_tenures`, `get_person_detail`, `update_person`) | service | CRUD | Same file's existing `birthdate` `fields_set`-guarded write (lines 479–486) and `appointed_by`/`appointing_president_party` tenure read/write (lines 173–174, 405–406) | exact |
| `api/schemas/speakers.py` (modify: `TenureEntry` gains `appointed_by`/`appointing_president_party`/`reason_left`; `SpeakerPopoverEntry` gains `birthdate`/`death_date`/`bio_text`, loses top-level `appointing_president`; T-14-02 comment reversal) | model (Pydantic schema) | request-response | Same file's existing `TenureEntry.office` field shape and module docstring | exact |
| `api/services/speakers.py` (modify: Step 3a per-tenure dict, Step 5 assembly; T-14-02 comment reversal) | service | CRUD (read-assembly) | Same file's existing Step 3a `str_tenures_by_person` dict-building loop (lines 172–178) and Step 5 assembly dict (lines 207–220) | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` (modify: activate Death Date input ~521–536 rewritten as active; activate Reason Left `<select>` ~798–813) | component (Svelte) | request-response (form) | Same file's existing `Birth Date` `<input type="date">` (line 595–600, active) and the `President's Party` `<select>` (lines 782–796, active dropdown-with-escape-hatch pattern) | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` (modify: `TenureRowClient`/`PersonDetail` interfaces, `save` action field mapping) | route (SvelteKit form action) | request-response | Same file's existing `birthdate`/`appointed_by`/`appointing_president_party` handling throughout `load` and the `save` action | exact |
| `app/src/lib/components/SpeakerPopover.svelte` (modify: restructure layout, add birth/death line, bio clamp/expand, per-tenure appointed_by/party/reason, advocate descriptor placeholder) | component (Svelte) | request-response (render) | Same file's existing `officeTitle()`/`OFFICE_TITLES` mapping (lines 9–21) and `showInitials` `$state` toggle idiom (line 45) | exact |
| `.planning/PROJECT.md` (modify: append T-14-02 reversal note to Key Decisions) | config/doc | — | Existing "Key Decisions" table entry for T-14-02 itself | exact (doc-only) |

## Pattern Assignments

### `alembic/versions/00XX_add_person_death_date.py` (migration)

**Analog:** `alembic/versions/0016_add_person_birthdate.py` (full file read above)

**Core pattern** — single nullable column add, no backfill, explicit downgrade:
```python
revision: str = "00XX"          # pick next free number at execution time (Pitfall 2)
down_revision: Union[str, None] = "<current head>"

def upgrade() -> None:
    op.add_column(
        "people",
        sa.Column("death_date", sa.Date(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("people", "death_date")
```
Note the migration 0016 docstring literally names this exact future phase ("Person 'Death Date' ... deferred to a future phase") — cite it in the new migration's docstring as the fulfillment.

### `alembic/versions/00XX_add_constrain_tenure_reason_left.py` (migration)

**Analog:** `alembic/versions/0021_constrain_tenure_office.py` (full file read above), diverging per Pitfall 3 (RESEARCH.md) — no `NOT NULL` step, and the CHECK constraint must include `IS NULL OR`.

**Core pattern** — add nullable column + CHECK constraint in the same or two migrations, following the `office` two-step shape but WITHOUT the final `alter_column(nullable=False)`:
```python
CONSTRAINT_NAME = "ck_court_tenures_reason_left"

def upgrade() -> None:
    op.add_column(
        "court_tenures",
        sa.Column("reason_left", sa.String(length=50), nullable=True),
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "court_tenures",
        "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
    )

def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "court_tenures", type_="check")
    op.drop_column("court_tenures", "reason_left")
```
Unlike 0021, there is no preflight `SELECT COUNT(*)` guard needed since `reason_left` starts fully NULL for every existing row (NULL always satisfies `IS NULL OR ...`) — but the plan may still add a defensive no-op preflight for symmetry/documentation if desired; it is not required for correctness the way 0021's was.

### `api/models/models.py` (model)

**Analog:** same file's `OFFICE_CHIEF`/`VALID_OFFICES`/`OFFICE_TITLES`/`office_title()` block (lines 137–159) and `CourtTenure` class (lines 162–179).

**Core constant + helper pattern** (copy shape verbatim, renamed):
```python
REASON_RETIRED = "retired"
REASON_DIED = "died"
REASON_PROMOTED = "promoted"
VALID_REASONS_LEFT = (REASON_RETIRED, REASON_DIED, REASON_PROMOTED)

REASON_LEFT_TITLES = {
    REASON_RETIRED: "Retired",
    REASON_DIED: "Died in office",
    REASON_PROMOTED: "Promoted",
}

def reason_left_title(reason: str) -> str:
    """Exhaustive over VALID_REASONS_LEFT — raises KeyError for any other input."""
    return REASON_LEFT_TITLES[reason]
```

**Model field additions:**
```python
# Person — add near existing birthdate (line 120)
death_date = Column(Date, nullable=True)
```
```python
class CourtTenure(Base):
    __table_args__ = (
        CheckConstraint("office IN ('chief', 'associate')", name="ck_court_tenures_office"),
        CheckConstraint(
            "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
            name="ck_court_tenures_reason_left",
        ),
    )
    ...
    reason_left = Column(String(50), nullable=True)  # D-01/D-02 — nullable permanently
```
Naming discipline note (Pitfall 7, RESEARCH.md): keep `reason_left`-specific names (`VALID_REASONS_LEFT`, `REASON_LEFT_TITLES`, `reason_left_title`), not a generic `REASON_*`/`VALID_REASONS` name, mirroring `VALID_OFFICES`'s office-specific naming.

### `pipeline/commands/import_justices_csv.py` (pipeline service)

**Analog:** same file — existing per-row CSV read (lines 204–207) and null-only-vs-create branching (lines 183–229).

**Imports pattern** (existing, line 31) — add `Person.death_date`/reason mapping is a model attribute, not an import addition; only need:
```python
from api.models.models import CourtTenure, OFFICE_ASSOCIATE, OFFICE_CHIEF, Person
```
(no new import needed beyond what's already imported, since reason/death_date are plain columns, not constants referenced by name in this file — confirm no `REASON_LEFT_TITLES` import is needed here per D-03's "no derivation" rule.)

**Core per-row read extension** (Pattern 1 from RESEARCH.md, lines 251–282 already give the exact code):
```python
birthdate = _parse_optional_date(row.get("Birthdate", ""))
death_date = _parse_optional_date(row.get("Death Date", ""))
reason_left_raw = row.get("Reason Left", "").strip()
reason_left = _REASON_LEFT_CSV_MAP.get(reason_left_raw)

_REASON_LEFT_CSV_MAP = {
    "Died": "died",
    "Retired": "retired",
    "Promoted to Chief Justice": "promoted",
    "Still in Office": None,
    "": None,
}
```

**Null-only backfill pattern** (Pattern 2 from RESEARCH.md, lines 140–158) — extend the existing `if person is not None:` branch:
```python
if person is not None:
    if not person.is_justice:
        person.is_justice = True
        people_upgraded += 1
    if person.birthdate is None and birthdate is not None:
        person.birthdate = birthdate
    if person.death_date is None and death_date is not None:
        person.death_date = death_date
else:
    person = Person(
        ...,
        birthdate=birthdate,
        death_date=death_date,
    )
```
And extend the tenure `else` no-op arm (currently silently does nothing on `existing_tenure is not None`, line ~218) to null-only-backfill `reason_left` analogously.

### `api/schemas/admin_people.py` (schema)

**Analog:** same file's `TenureWrite`/`TenureRow` classes (lines 36–77) and `PersonDetail`/`PersonUpdate` classes (lines 106–167).

**TenureWrite/TenureRow addition** (Pitfall 4, RESEARCH.md — strict vs tolerant split must be preserved):
```python
class TenureWrite(BaseModel):
    office: Literal["chief", "associate"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None
    reason_left: Optional[Literal["retired", "died", "promoted"]] = None  # new — strict write side

class TenureRow(BaseModel):
    office: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None
    reason_left: Optional[str] = None  # new — tolerant read side
```

**PersonDetail/PersonUpdate addition** (mirrors `birthdate`'s exact shape, lines 130–131 / 165–166):
```python
class PersonDetail(BaseModel):
    ...
    death_date: Optional[str] = None  # new — ISO date string, mirrors birthdate

class PersonUpdate(BaseModel):
    ...
    death_date: Optional[str] = None  # new — None = leave unchanged (mirrors birthdate)
```

### `api/services/admin_people.py` (service)

**Analog:** same file's `_replace_tenures()` (lines 124–176), `get_person_detail()` (lines 377–424), `update_person()`'s `fields_set`-guarded `birthdate` write (lines 479–486, Pitfall 5).

**`_replace_tenures` addition** — add `reason_left` alongside `appointed_by`/`appointing_president_party` in the `CourtTenure(...)` constructor call (line ~168–175):
```python
db.add(
    CourtTenure(
        person_id=person_id,
        office=t.office,
        start_date=start_date,
        end_date=end_date,
        appointed_by=t.appointed_by or None,
        appointing_president_party=t.appointing_president_party or None,
        reason_left=t.reason_left or None,
    )
)
```

**`get_person_detail` addition** — add `reason_left` to the tenure dict comprehension (lines 401–409) and `death_date` to the top-level dict (mirrors line 423's `birthdate.isoformat()`):
```python
"death_date": person.death_date.isoformat() if person.death_date else None,
```

**`update_person` addition** (Pitfall 5 — exact `fields_set` guard, not `is not None`):
```python
if "death_date" in fields_set:
    person.death_date = (
        datetime.date.fromisoformat(body.death_date) if body.death_date else None
    )
```
Place this in the save-form-only guard block alongside `birthdate` (lines 483–486), NOT alongside `is_justice`'s older `is not None` guard style (line 502) — this is the exact pitfall the RESEARCH.md flags.

### `api/schemas/speakers.py` (public schema — T-14-02 reversal)

**Analog:** same file, entire file read above (45 lines) — this is a small file, fully in context.

**Full rewritten shape:**
```python
"""
Public speaker popover schemas.

Phase 39 (D-11, D-12): appointing_president_party is now intentionally
INCLUDED — this reverses the prior exclusion (originally justified by
T-14-02's apolitical-framing rationale). Party affiliation of the
appointing PRESIDENT (not the Justice) is factual historical data,
rendered identically for every entry (see 39-CONTEXT.md D-11).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class TenureEntry(BaseModel):
    office: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None                      # new — D-13, per-tenure now
    appointing_president_party: Optional[str] = None        # new — D-11 reversal
    reason_left: Optional[str] = None                       # new — D-01


class SpeakerPopoverEntry(BaseModel):
    person_id: int
    full_name: str
    role_name: Optional[str] = None
    photo_url: Optional[str] = None
    birthdate: Optional[str] = None       # new — D-14 (bio) counterpart
    death_date: Optional[str] = None      # new
    bio_text: Optional[str] = None        # new — D-14
    tenure: list[TenureEntry] = []
    side: Optional[str] = None
    # NOTE: top-level `appointing_president` field REMOVED (D-13) — moved to
    # per-TenureEntry.appointed_by. Grep the repo for bare `appointing_president`
    # (not `_party`) before removing to confirm SpeakerPopover.svelte (lines 30, 84-88)
    # is the only remaining consumer.

    model_config = ConfigDict(from_attributes=True)
```

### `api/services/speakers.py` (public service — T-14-02 reversal + D-13 wiring)

**Analog:** same file, Step 3a (lines 158–178) and Step 5 (lines 192–220), already read in full above.

**Step 3a addition** — extend `str_tenures_by_person` dict per tenure:
```python
str_tenures_by_person[t.person_id].append(
    {
        "office": t.office,
        "start_date": str(t.start_date) if t.start_date else None,
        "end_date": str(t.end_date) if t.end_date else None,
        "appointed_by": t.appointed_by,
        "appointing_president_party": t.appointing_president_party,
        "reason_left": t.reason_left,
    }
)
```

**Step 5 rewrite** — drop the `"appointing_president": None` hardcode, add birthdate/death_date/bio_text:
```python
result.append(
    {
        "person_id": person.id,
        "full_name": person.full_name,
        "role_name": role_name,
        "photo_url": person.photo_url,
        "birthdate": str(person.birthdate) if person.birthdate else None,
        "death_date": str(person.death_date) if person.death_date else None,
        "bio_text": person.bio_text,
        "tenure": str_tenures_by_person[person.id],
        "side": side.value if side is not None else None,
    }
)
```
Also update the module docstring (lines 8–9) — remove "CRITICAL: appointing_president_party is intentionally never included..." and replace with the D-11/D-12 reversal note (mirror the `schemas/speakers.py` docstring text above).

**Error-handling pattern to replicate for `reason_left_title()`** (used only in the frontend render boundary, but the backend degrade-gracefully convention it must match is `_tenure_role_name`'s):
```python
try:
    return office_title(t["office"])
except KeyError:
    return None
```

### `app/src/routes/admin/people/[id]/+page.svelte` (admin editor)

**Analog:** same file's active `Birth Date` `<input type="date">` (lines 588–601) for Death Date, and the `President's Party` `<select>` with escape-hatch option (lines 776–796) for Reason Left.

**Death Date — remove `disabled`/`opacity:0.6`, bind like Birth Date:**
```svelte
<div>
    <label for="death_date" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
        Death Date
    </label>
    <input
        id="death_date"
        type="date"
        bind:value={deathDate}
        style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
    />
</div>
```
Also add a hidden input carrying it into the save-form, mirroring line 581:
```svelte
<input type="hidden" name="death_date" form="save-form" value={deathDate} />
```

**Reason Left — convert to `<select>` per D-09, copying the President's Party escape-hatch shape exactly (lines 782–796):**
```svelte
<div>
    <label for="tenure-reason-{row._key}" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
        Reason Left
    </label>
    <select
        id="tenure-reason-{row._key}"
        bind:value={row.reason_left}
        style="display: block; width: 100%; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
    >
        <option value="">— None —</option>
        <option value="retired">Retired</option>
        <option value="died">Died in office</option>
        <option value="promoted">Promoted</option>
        {#if row.reason_left && !['retired','died','promoted'].includes(row.reason_left)}
            <option value={row.reason_left}>{row.reason_left}</option>
        {/if}
    </select>
</div>
```
Note: unlike President's Party (a free-text-compatible dropdown with an open vocabulary, `PARTY_OPTIONS`), Reason Left is a genuinely constrained enum (`TenureWrite.reason_left: Literal[...]`) — the escape-hatch `<option>` here only exists to display a pre-existing invalid/legacy value without crashing the `<select>`, not to permit submitting new invalid values (mirrors the `office` radiogroup's "show invalid original, force correction" precedent at lines 713–725, not the open-vocabulary Party dropdown).

**Also add `reason_left` to the `tenureRows` state shape** (wherever the client-side row type/state is defined near the top of `<script>` — read the file's earlier `<script>` block at plan time for the exact `tenureRows` state initializer) and to the `JSON.stringify(tenureRows)` hidden input already at line 582 (no change needed there — it serializes whatever keys exist on each row object).

### `app/src/routes/admin/people/[id]/+page.server.ts` (form action route)

**Analog:** same file's existing `birthdate`/`appointed_by`/`appointing_president_party` handling throughout `load` and `save` (full file read above).

**`TenureRowClient` interface addition:**
```typescript
interface TenureRowClient {
    _key: number;
    id?: number;
    office: string;
    start_date: string;
    end_date: string;
    appointed_by: string;
    appointing_president_party: string;
    reason_left: string;  // new — '' means None/unselected
}
```

**`PersonDetail` interface addition:**
```typescript
interface PersonDetail {
    ...
    death_date: string | null;  // new — mirrors birthdate
    tenures: Array<{
        office: string | null;
        start_date: string | null;
        end_date: string | null;
        appointed_by: string | null;
        appointing_president_party: string | null;
        reason_left: string | null;  // new
    }>;
    ...
}
```

**`save` action addition** — add `death_date` to the destructure/fail-state-restore blocks (mirrors `birthdate` at lines 149, 164, 183, 197, 213, 221, 229) and add `reason_left` to the tenure-stripping map (line 172–178):
```typescript
const death_date = ((formData.get('death_date') as string) ?? '').trim() || null;
...
const tenures = tenuresParsed.map(({ office, start_date, end_date, appointed_by, appointing_president_party, reason_left }) => ({
    office, start_date, end_date, appointed_by, appointing_president_party,
    reason_left: reason_left || null,
}));
...
body: JSON.stringify({
    full_name, tenures,
    first_name, last_name, middle_name, name_suffix,
    is_justice, birthdate, death_date,
}),
```
Note: unlike Reason Left (D-19's prior "disabled input, no value submitted" comment at line 170–171), this comment must be removed/updated once wired — it currently documents the OLD disabled-input state.

### `app/src/lib/components/SpeakerPopover.svelte` (public popover)

**Analog:** same file's `OFFICE_TITLES`/`officeTitle()` mapping (lines 9–21) for a new `REASON_LEFT_TITLES`/`reasonLeftTitle()` helper, and `showInitials` `$state<boolean>` toggle (line 45) for the new bio expand/collapse toggle.

**New display-title helper** (mirrors `officeTitle()` exactly):
```svelte
const REASON_LEFT_TITLES: Record<string, string> = {
    retired: 'Retired',
    died: 'Died in office',
    promoted: 'Promoted'
};

function reasonLeftTitle(reason: string | null): string {
    return reason ? (REASON_LEFT_TITLES[reason] ?? '') : '';
}
```

**Bio clamp/expand toggle** (mirrors `showInitials` idiom):
```svelte
let bioExpanded = $state(false);
```
```svelte
{#if speaker.bio_text}
    <p
        style="font-size:14px;font-weight:400;line-height:1.5;color:#94a3b8;margin:8px 0 0 0;
               {bioExpanded ? '' : 'display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;'}"
    >{speaker.bio_text}</p>
    <button
        type="button"
        aria-expanded={bioExpanded}
        onclick={() => (bioExpanded = !bioExpanded)}
        style="font-size:13px;color:#93c5fd;text-decoration:underline;background:none;border:none;padding:0;cursor:pointer;margin-top:4px;"
    >{bioExpanded ? 'Show less' : 'Read more'}</button>
{/if}
```

**Interface additions** (mirrors existing `TenureRow`/`SpeakerDetail` interfaces, lines 2–31):
```typescript
interface TenureRow {
    office: string | null;
    start_date: string | null;
    end_date: string | null;
    appointed_by: string | null;               // new
    appointing_president_party: string | null; // new
    reason_left: string | null;                // new
}

interface SpeakerDetail {
    person_id: number;
    full_name: string;
    role_name: string | null;
    photo_url_full: string | null;
    is_bench: boolean;
    tenure: TenureRow[];
    birthdate: string | null;    // new
    death_date: string | null;   // new
    bio_text: string | null;     // new
    // appointing_president (top-level) REMOVED — moved into each TenureRow
}
```

**Per-tenure block rewrite** (replaces the single-line `{#each}` at lines 79–83; new 3-line block per UI-SPEC §"Multi-tenure list layout"):
```svelte
{#each speaker.tenure as t}
    <div style="margin-bottom:16px;">
        <p style="font-size:13px;color:#94a3b8;margin:0;">
            {officeTitle(t.office)} — {t.start_date ? t.start_date.slice(0, 4) : '?'}–{t.end_date ? t.end_date.slice(0, 4) : 'present'}
        </p>
        {#if t.appointed_by}
            <p style="font-size:13px;color:#94a3b8;margin:0;">
                {t.appointed_by}{t.appointing_president_party ? ` · ${t.appointing_president_party}` : ''}
            </p>
        {/if}
        {#if t.reason_left}
            <p style="font-size:13px;color:#94a3b8;margin:0;">{reasonLeftTitle(t.reason_left)}</p>
        {/if}
    </div>
{/each}
```

**Birth/death line** (new, UI-SPEC copywriting contract — `Intl.DateTimeFormat`, distinct from the case-header's full-month formatter):
```svelte
{#if speaker.birthdate || speaker.death_date}
    <p style="font-size:13px;color:#94a3b8;margin:8px 0 0 0;">
        {#if speaker.birthdate}b. {formatShort(speaker.birthdate)}{/if}{#if speaker.death_date} · d. {formatShort(speaker.death_date)}{/if}
    </p>
{/if}
```
```typescript
function formatShort(iso: string): string {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        .format(new Date(iso));
}
```

**Advocate descriptor placeholder** (new, D-16, static/no data):
```svelte
{#if !isBench}
    <p style="font-size:13px;font-weight:400;font-style:italic;color:#94a3b8;margin:2px 0 0 0;">Coming soon</p>
{/if}
```

**Layout restructure note:** UI-SPEC mandates removing the `@media (max-width: 767px) { flex-direction: column }` override (lines 108–114) and widening `min-width`/`max-width` to `300px`/`400px` (from `280px`/`360px`, lines 100–101) — this is a structural rewrite of the whole template, not an additive patch; treat the whole file as the "existing code to restructure," not just an insertion point.

## Shared Patterns

### Canonical-value + display-title helper (Phase 37 precedent)
**Source:** `api/models/models.py` lines 137–159 (`office_title`/`OFFICE_TITLES`) — mirrored on the frontend at `SpeakerPopover.svelte` lines 9–21.
**Apply to:** `reason_left_title()`/`REASON_LEFT_TITLES` (backend, new) and `reasonLeftTitle()`/`REASON_LEFT_TITLES` (frontend, new). Both must be exhaustive-over-canonical-values-only, degrading gracefully (backend: `except KeyError: return None`; frontend: `?? ''`) — never crash or coerce.

### Two-step migration (add column → add CHECK constraint)
**Source:** `alembic/versions/0016_add_person_birthdate.py` (simple add) + `alembic/versions/0021_constrain_tenure_office.py` (add CHECK + preflight).
**Apply to:** Both new migrations this phase. `death_date` only needs the simple-add shape (no constraint). `reason_left` needs the CHECK-constraint shape but WITHOUT the final `NOT NULL` step (see Pitfall 3).

### Null-only backfill on re-import
**Source:** `pipeline/commands/import_justices_csv.py` lines 183–188 (existing `is_justice` upgrade-in-place branch).
**Apply to:** New `birthdate`/`death_date`/`reason_left` backfill branches in the same function — never overwrite a non-null value.

### `model_fields_set` write guard (not `is not None`)
**Source:** `api/services/admin_people.py` `update_person()` lines 462–486 (`fields_set` guard for `bio_text`/`photo_url`/name parts/`birthdate`).
**Apply to:** New `death_date` write in the same function — must use `"death_date" in fields_set`, placed in the save-form field group (with `birthdate`), not the photo-form group, and not styled after the older `is_justice is not None` guard.

### Strict-write vs. tolerant-read schema split
**Source:** `api/schemas/admin_people.py` `TenureWrite` (strict `Literal["chief","associate"]`) vs. `TenureRow` (tolerant `Optional[str]`).
**Apply to:** New `reason_left` field on both — `TenureWrite.reason_left: Optional[Literal["retired","died","promoted"]] = None`, `TenureRow.reason_left: Optional[str] = None`.

### Degrade-gracefully-on-invalid-enum (Phase 37 CR-01 precedent)
**Source:** `api/services/speakers.py` `_tenure_role_name()` lines 81–96 and `api/services/admin_people.py` `_bench_role_and_missing_tenure()` lines 830–838 — both wrap `office_title()` in `try/except KeyError: return None`.
**Apply to:** Any new call site of `reason_left_title()` — never let an out-of-vocabulary value 500 the whole popover/editor.

## No Analog Found

None — every file this phase touches has a directly matching, already-read prior-phase precedent in the same codebase (this phase is unusually well-precedented; RESEARCH.md independently reached the same conclusion).

## Metadata

**Analog search scope:** `api/models/`, `api/schemas/`, `api/services/`, `alembic/versions/`, `pipeline/commands/`, `app/src/routes/admin/people/[id]/`, `app/src/lib/components/`
**Files scanned:** 12 (all read in full or in large targeted ranges: `api/models/models.py`, `api/services/speakers.py`, `api/schemas/speakers.py`, `api/schemas/admin_people.py`, `api/services/admin_people.py`, `alembic/versions/0016_add_person_birthdate.py`, `alembic/versions/0021_constrain_tenure_office.py`, `pipeline/commands/import_justices_csv.py`, `app/src/lib/components/SpeakerPopover.svelte`, `app/src/routes/admin/people/[id]/+page.svelte` (two ranges), `app/src/routes/admin/people/[id]/+page.server.ts`)
**Pattern extraction date:** 2026-07-22
