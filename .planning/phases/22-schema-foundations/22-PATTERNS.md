# Phase 22: Schema Foundations - Pattern Map

**Mapped:** 2026-07-02
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0012_unpublished_enum_and_status_log.py` | migration | batch | `alembic/versions/0008_side_enum_and_argument_status.py` | exact |
| `alembic/versions/0013_participant_title_and_tenure_appointed_by.py` | migration | batch | `alembic/versions/0011_add_source_docket_cover_metadata.py` | exact |
| `api/models/models.py` | model | CRUD | self (modify in-place) | exact |
| `api/schemas/admin_people.py` | model (Pydantic schema) | request-response | self (modify in-place) | exact |
| `api/services/admin_people.py` | service | CRUD | self (modify in-place) | exact |
| `api/services/speakers.py` | service | request-response | self (modify in-place) | exact |
| `pipeline/parser/cover_extractor.py` | utility | transform | self (extend in-place) | exact |
| `pipeline/commands/parse.py` | utility (pipeline command) | batch | self (extend in-place) | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` | route (server load) | request-response | self (modify in-place) | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` | component | request-response | self (modify in-place) | exact |
| `tests/test_schema.py` | test | — | self (modify in-place) | exact |
| `pipeline/tests/test_cover_extractor.py` | test | — | self (extend in-place) | exact |

---

## Pattern Assignments

### `alembic/versions/0012_unpublished_enum_and_status_log.py` (migration, batch)

**Analog:** `alembic/versions/0008_side_enum_and_argument_status.py`

**File header / revision metadata pattern** (lines 31–41):
```python
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
For 0012: `revision = "0012"`, `down_revision = "0011"`.

**Enum expansion pattern — COMMIT before ADD VALUE** (lines 51–54):
```python
op.execute(sa.text("COMMIT"))
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))
```
For 0012: replace `side`/`'PETITIONER'` etc. with `argument_status`/`'unpublished'`. Only one `ADD VALUE` call needed.

**CREATE TABLE after enum expansion** — comes after the enum `ADD VALUE` in the same `upgrade()`. There is no existing analog for `CREATE TABLE` in these migrations; use `op.create_table()` with `sa.PrimaryKeyConstraint`. See RESEARCH.md Code Examples section for the exact `op.create_table("argument_status_log", ...)` call.

**Backfill via INSERT ... SELECT** (lines 94–103, adapted — use `op.execute(sa.text(...))`):
```python
op.execute(sa.text(
    "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"
))
```
For 0012 backfill: replace with a single `INSERT INTO argument_status_log (argument_id, status, created_at) SELECT id, status::argument_status, COALESCE(resolved_at, CURRENT_TIMESTAMP) FROM arguments`.

**Downgrade pattern — no enum reversal** (lines 111–122):
```python
def downgrade() -> None:
    op.drop_column("arguments", "status")
    op.execute(sa.text("DROP TYPE IF EXISTS argument_status"))

    # NOTE: The PETITIONER, RESPONDENT, and AMICUS values added to the
    # `side` enum type are NOT reversed here. PostgreSQL does not support
    # removing enum values — they remain in the type permanently.
```
For 0012: `downgrade()` drops `argument_status_log` table only. Do NOT attempt to remove `'unpublished'` from `argument_status` enum.

---

### `alembic/versions/0013_participant_title_and_tenure_appointed_by.py` (migration, batch)

**Analog:** `alembic/versions/0011_add_source_docket_cover_metadata.py`

**File header / revision metadata pattern** (lines 30–36):
```python
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
For 0013: `revision = "0013"`, `down_revision = "0012"`.

**Nullable column add pattern** (lines 44–48):
```python
op.add_column(
    "arguments",
    sa.Column("source_docket", sa.String(50), nullable=True),
)
```
For 0013, apply this pattern three times: `argument_participants.title VARCHAR(500)`, `court_tenures.appointed_by VARCHAR(200)`, `court_tenures.appointing_president_party VARCHAR(50)`.

**Column drop pattern** (lines 78–80):
```python
op.drop_column("arguments", "cover_metadata")
op.drop_column("arguments", "source_docket")
```
For 0013 `upgrade()`: drop `people.appointing_president` and `people.appointing_president_party` (note: column name on `people` is `appointing_president`; new column on `court_tenures` is `appointed_by` per D-08/A4).

**Downgrade reversal order** (lines 71–80 — reverse order of upgrade):
```python
def downgrade() -> None:
    op.drop_constraint("uq_arguments_source_docket_question", "arguments", type_="unique")
    op.execute("UPDATE arguments SET argued_date = CURRENT_DATE WHERE argued_date IS NULL")
    op.alter_column("arguments", "argued_date", nullable=False)
    op.drop_column("arguments", "cover_metadata")
    op.drop_column("arguments", "source_docket")
```
For 0013: reverse by restoring `people.appointing_president` and `people.appointing_president_party` as nullable, then dropping from `court_tenures`, then dropping `argument_participants.title`.

---

### `api/models/models.py` (model, CRUD) — four changes

**Analog:** self — four distinct in-place modifications.

**1. Extend `ArgumentStatusEnum`** (lines 66–69 — current state):
```python
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"
```
Add `UNPUBLISHED = "unpublished"` after `PUBLISHED`. Follow the same `str, enum.Enum` pattern.

**2. New `ArgumentStatusLog` model — copy `SpeakerAlias` ORM pattern** (lines 327–334):
```python
class SpeakerAlias(Base):
    __tablename__ = "speaker_alias"

    id = Column(Integer, primary_key=True)
    normalized_label = Column(String(300), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
```
For `ArgumentStatusLog`: `Integer` PK, `argument_id` FK to `arguments.id` (not nullable), `status` using `SAEnum(ArgumentStatusEnum, name="argument_status", values_callable=lambda e: [x.value for x in e])` (not nullable), `created_at DateTime(timezone=True)` with `server_default=func.now()` (not nullable). See `Argument.status` column (lines 177–182) for the exact `SAEnum` constructor syntax.

**`SAEnum` constructor pattern** (lines 177–182):
```python
status = Column(
    SAEnum(ArgumentStatusEnum, name="argument_status",
           values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    default=ArgumentStatusEnum.PIPELINE,
)
```

**3. Add `title` to `ArgumentParticipant`** (lines 244–253 — current state):
```python
class ArgumentParticipant(Base):
    __tablename__ = "argument_participants"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)
    raw_speaker_label = Column(String(200), nullable=False)
    side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False)
```
Add `title = Column(String(500), nullable=True)` after `side`. Follow nullable column pattern from `Person` (lines 109–114).

**4. Move columns between `Person` and `CourtTenure`** (lines 113–114 and 125–132):
- Remove from `Person` (lines 113–114): `appointing_president = Column(String(200), nullable=True)` and `appointing_president_party = Column(String(50), nullable=True)`.
- Add to `CourtTenure` after `end_date`: `appointed_by = Column(String(200), nullable=True)` and `appointing_president_party = Column(String(50), nullable=True)`. Follow the `end_date` nullable pattern (line 132).

---

### `api/schemas/admin_people.py` (Pydantic schema, request-response)

**Analog:** self — remove two fields from two classes.

**`PersonDetail` — fields to remove** (lines 73–74):
```python
appointing_president: Optional[str] = None
appointing_president_party: Optional[str] = None
```
Delete both lines. Do NOT add them to `TenureRow` in Phase 22 (Pitfall 4 / D-08).

**`PersonUpdate` — fields to remove** (lines 103–104):
```python
appointing_president: Optional[str] = None
appointing_president_party: Optional[str] = None
```
Delete both lines. The surrounding comment block on line 98 (`# Phase 9 additions — mass-assignment allow-list extension`) may be trimmed to only list the four remaining fields.

---

### `api/services/admin_people.py` (service, CRUD)

**Analog:** self — remove four read/write references.

**`get_person_detail` — reads to remove** (lines 246–247):
```python
"appointing_president": person.appointing_president,
"appointing_president_party": person.appointing_president_party,
```
Delete both lines from the return dict. The surrounding dict keys (`"name_suffix"`, `"is_justice"`) remain.

**`update_person` — writes to remove** (lines 289–290):
```python
person.appointing_president = body.appointing_president if body.appointing_president else None
person.appointing_president_party = body.appointing_president_party if body.appointing_president_party else None
```
Delete both lines. The surrounding assignment pattern for `name_suffix` (line 288) and `is_justice` (after line 290) remains and shows the correct style.

---

### `api/services/speakers.py` (service, request-response)

**Analog:** self — one line change.

**Read to remove** (line 197 per RESEARCH.md):
The `get_argument_speakers` service builds a speaker dict that includes `"appointing_president": person.appointing_president`. After migration 0013 drops the column, this will raise `AttributeError`. Remove the key from the dict. The `SpeakerPopoverEntry` schema field can remain (it is nullable and the `{#if speaker.appointing_president}` guard in the template handles `None` safely — no frontend change needed in Phase 22).

---

### `pipeline/parser/cover_extractor.py` (utility, transform)

**Analog:** self — add new function `_parse_toc_titles` and new public function `extract_advocate_titles` following existing patterns.

**`_parse_toc_sides` — direct template for `_parse_toc_titles`** (lines 195–229):
```python
def _parse_toc_sides(lines: list[str]) -> "dict[str, str]":
    from api.models.models import SideEnum

    mapping: dict[str, str] = {}
    pending_name: str | None = None

    for line in lines:
        if TOC_ESQ_RE.match(line):
            last = _toc_last_name(line)
            pending_name = last.upper() if last else None
            continue

        if pending_name:
            if TOC_AMICUS_RE.search(line):
                mapping[pending_name] = SideEnum.AMICUS.value
                pending_name = None
            elif m := TOC_SIDE_RE.search(line):
                role_word = m.group(1).upper()
                mapping[pending_name] = (
                    SideEnum.PETITIONER.value
                    if role_word.startswith("PETITIONER")
                    else SideEnum.RESPONDENT.value
                )
                pending_name = None

    return mapping
```
For `_parse_toc_titles`: same loop skeleton, same `TOC_ESQ_RE`/`_toc_last_name`/`pending_name` structure. Key difference: when `pending_name` is set and the next line is NOT a `TOC_SIDE_RE`/`TOC_AMICUS_RE`/`TOC_ESQ_RE` match, treat it as the subtitle string. Returns `dict[str, str]` mapping `{last_name_upper: subtitle_string}`.

**`extract_advocate_sides` — template for `extract_advocate_titles`** (lines 277–296):
```python
def extract_advocate_sides(pdf_path: Path) -> "dict[str, str]":
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(4, len(pdf.pages))):
                raw = pdf.pages[i].extract_text(layout=False) or ""
                if "C O N T E N T S" in raw:
                    return _parse_toc_sides(_clean_lines(raw))
    except Exception:
        pass  # D-09: never raise
    return {}
```
For `extract_advocate_titles`: same structure, call `_parse_toc_titles` instead. Same `try/except` guard (D-11). To satisfy D-12 (shared TOC read), the preferred approach is: refactor `extract_advocate_sides` to return a `(sides, titles)` tuple by calling both parsers on the same `_clean_lines(raw)` result, and rename the public entry point to something like `extract_toc_data`. Then `parse.py` unpacks both results from one call.

**Fail-safe pattern** (lines 251–273 — `extract_cover_metadata`):
```python
try:
    with pdfplumber.open(pdf_path) as pdf:
        ...
except Exception:
    pass  # D-05: never raise; caller receives partial result or {}
return result
```
All extractor functions use this `try/except Exception: pass` guard. `extract_advocate_titles` must follow the same pattern.

---

### `pipeline/commands/parse.py` (pipeline command, batch)

**Analog:** self — add import, add `_update_participant_titles` function, call it after the existing `_update_participant_sides` call.

**Import line to extend** (line 45):
```python
from pipeline.parser.cover_extractor import extract_cover_metadata, extract_advocate_sides
```
After refactor, this becomes: `from pipeline.parser.cover_extractor import extract_cover_metadata, extract_toc_data` (or similar per the chosen refactor approach in `cover_extractor.py`).

**CPU-side extraction block before async session** (lines 139–146):
```python
cover_meta = extract_cover_metadata(pdf_path)
advocate_sides = extract_advocate_sides(pdf_path)
if cover_meta:
    print(f"Cover metadata extracted: {list(cover_meta.keys())}")
if advocate_sides:
    print(f"Advocate sides mapped: {advocate_sides}")
```
After refactor: call `extract_toc_data(pdf_path)` (or equivalent) once here and unpack `advocate_sides, advocate_titles`. Both extractions remain outside the `async with get_session()` block.

**`_update_participant_sides` — direct template for `_update_participant_titles`** (lines 431–464):
```python
async def _update_participant_sides(
    session: AsyncSession,
    argument_id: int,
    sides_map: "dict[str, str]",
) -> int:
    if not sides_map:
        return 0

    result = await session.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.argument_id == argument_id
        )
    )
    participants = result.scalars().all()

    updated = 0
    for p in participants:
        if p.raw_speaker_label is None:
            continue
        label_last = _normalize_label_last_name(p.raw_speaker_label)
        if label_last and label_last.upper() in sides_map:
            p.side = SideEnum(sides_map[label_last.upper()])
            updated += 1

    return updated
```
For `_update_participant_titles`: same signature shape (`titles_map: dict[str, str]`), same loop. Difference: `p.title = titles_map[label_last.upper()]` (plain string assignment, not an enum cast).

**Call site pattern** (lines 378–380):
```python
if advocate_sides and run.argument_id is not None:
    sides_updated = await _update_participant_sides(session, run.argument_id, advocate_sides)
    print(f"Participant sides updated: {sides_updated} row(s) from TOC mapping.")
```
Add an identical block immediately after for titles: `if advocate_titles and run.argument_id is not None: titles_updated = await _update_participant_titles(...)`.

---

### `app/src/routes/admin/people/[id]/+page.server.ts` (route, request-response)

**Analog:** self — remove two fields from TypeScript type, form data extraction, and API payload.

**TypeScript type block — fields to remove** (lines 31–32):
```typescript
appointing_president: string | null;
appointing_president_party: string | null;
```
Delete both lines from the inline type declaration.

**Form data extraction — lines to remove** (lines 164–165):
```typescript
const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '').trim() || null;
```
Delete both `const` declarations.

**API payload — field to remove** (line 199):
```typescript
appointing_president, appointing_president_party,
```
Remove both properties from the PATCH request body object.

---

### `app/src/routes/admin/people/[id]/+page.svelte` (component, request-response)

**Analog:** self — remove a form section block.

**Form section to remove** (lines 507–541):
The block contains: `<label for="appointing_president">`, the text `<input>`, `<label for="appointing_president_party">`, and the `<select>` with six `<option>` children. Delete the entire block. The surrounding form fields (`name_suffix`, `is_justice`) remain and show the correct field structure for reference.

---

### `tests/test_schema.py` (test, batch)

**Analog:** self — add one table name to `EXPECTED_TABLES` and update the docstring count.

**`EXPECTED_TABLES` set — current state** (lines 54–66):
```python
EXPECTED_TABLES = {
    "roles", "people", "court_tenures", "cases", "arguments",
    "case_arguments", "case_appearances", "argument_participants",
    "pipeline_runs", "utterances", "speaker_alias",
}
```
Add `"argument_status_log"` to the set. Update the `test_all_tables_exist` docstring (line 72) from `"All 11 tables must exist"` to `"All 12 tables must exist"`. Also update the `admin_jobs` note — the set currently omits `admin_jobs` (11 declared entries but 12 actual tables including `admin_jobs`). Confirm the exact count by reading the full test docstring context before editing.

---

### `pipeline/tests/test_cover_extractor.py` (test, transform)

**Analog:** self — add new test cases following the existing `_parse_toc_sides` test pattern.

Per RESEARCH.md (line 511–515), "Tests 6 and 7 in the file" cover `_parse_toc_sides`. New tests for `_parse_toc_titles` / `extract_advocate_titles` should follow the same structure: provide a list of mock TOC lines, call the function, assert the returned dict. Read the existing Tests 6 and 7 in `pipeline/tests/test_cover_extractor.py` before writing new tests to confirm the exact test function name, fixture pattern, and assertion style used there.

---

## Shared Patterns

### Alembic Migration File Header
**Source:** `alembic/versions/0011_add_source_docket_cover_metadata.py` lines 30–36
**Apply to:** Both 0012 and 0013
```python
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "XXXX"
down_revision: Union[str, None] = "YYYY"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

### PG Enum Expansion (autocommit gate)
**Source:** `alembic/versions/0008_side_enum_and_argument_status.py` lines 51–54
**Apply to:** Migration 0012 only
```python
op.execute(sa.text("COMMIT"))
op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'"))
```
CRITICAL: `COMMIT` must come first. Any DDL that references the new enum value (including `op.create_table`) must come AFTER this block.

### SAEnum Column Declaration
**Source:** `api/models/models.py` lines 177–181
**Apply to:** New `ArgumentStatusLog.status` column in `models.py`
```python
SAEnum(ArgumentStatusEnum, name="argument_status",
       values_callable=lambda e: [x.value for x in e])
```

### Fail-safe Extractor Pattern
**Source:** `pipeline/parser/cover_extractor.py` lines 288–296
**Apply to:** New `extract_advocate_titles` public function
```python
try:
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(min(4, len(pdf.pages))):
            raw = pdf.pages[i].extract_text(layout=False) or ""
            if "C O N T E N T S" in raw:
                return _parse_toc_titles(_clean_lines(raw))
except Exception:
    pass
return {}
```

### Downgrade Reversal Order
**Source:** `alembic/versions/0011_add_source_docket_cover_metadata.py` lines 71–80
**Apply to:** Both 0012 and 0013 downgrade()
Operations must be reversed: if `upgrade()` adds column A then column B, `downgrade()` drops column B then column A.

---

## No Analog Found

All files in Phase 22 have clear analogs in the existing codebase. No files require falling back to RESEARCH.md patterns alone.

---

## Metadata

**Analog search scope:** `alembic/versions/`, `api/models/`, `api/schemas/`, `api/services/`, `pipeline/parser/`, `pipeline/commands/`, `pipeline/tests/`, `tests/`, `app/src/routes/admin/people/`
**Files read for pattern extraction:** 10
**Pattern extraction date:** 2026-07-02
