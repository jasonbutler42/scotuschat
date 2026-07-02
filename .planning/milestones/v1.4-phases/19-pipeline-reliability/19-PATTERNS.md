# Phase 19: Pipeline Reliability — Pattern Map

**Mapped:** 2026-06-30
**Files analyzed:** 12
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0011_add_source_docket_cover_metadata.py` | migration | batch (DDL) | `alembic/versions/0010_add_is_justice.py` | exact |
| `api/models/models.py` (modify Argument) | model | CRUD | `api/models/models.py` (AdminJob JSONB columns) | exact |
| `api/schemas/admin_arguments.py` (add MetadataUpdate, extend ArgumentDetail) | schema | request-response | `api/schemas/admin_arguments.py` (ArgumentUpdate) | exact |
| `api/services/admin_arguments.py` (add check_duplicate, update_argument_metadata) | service | CRUD | `api/services/admin_arguments.py` (update_argument / get_argument_detail) | exact |
| `api/routers/admin.py` (add 2 new endpoints) | controller | request-response | `api/routers/admin.py` (existing GET/PATCH argument routes) | exact |
| `pipeline/parser/cover_extractor.py` (add primary_docket extraction) | utility | transform | `pipeline/parser/cover_extractor.py` (extract_cover_metadata) | exact |
| `pipeline/commands/parse.py` (add cover_metadata write-back) | service | batch | `pipeline/commands/parse.py` (Phase 16 PARSE-01 block, lines 308–342) | exact |
| `pipeline/commands/ingest.py` (source_docket + nullable argued_date) | service | CRUD | `pipeline/commands/ingest.py` (job-driven path, lines 253–266, 350–356) | exact |
| `pipeline/tests/test_cover_extractor.py` (add docket tests) | test | — | `pipeline/tests/test_cover_extractor.py` (existing PARSE-01 tests) | exact |
| `app/src/routes/admin/pipeline/+page.svelte` (docket input, Q# selector, preflight banner) | component | request-response | `app/src/routes/admin/pipeline/+page.svelte` (existing form fields) | exact |
| `app/src/routes/admin/pipeline/+page.server.ts` (forward primary_docket + question) | route | request-response | `app/src/routes/admin/pipeline/+page.server.ts` (existing default action) | exact |
| `app/src/routes/admin/pipeline/check-duplicate/+server.ts` (NEW proxy endpoint) | route | request-response | `app/src/routes/admin/people/[id]/merge-preview/+server.ts` | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (Argument Metadata card) | component | request-response | `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (existing resolve/approve cards) | role-match |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (load cover_metadata; saveMetadata action) | route | request-response | `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (approve action, argument load block) | exact |

---

## Pattern Assignments

### `alembic/versions/0011_add_source_docket_cover_metadata.py` (migration, batch)

**Analog:** `alembic/versions/0010_add_is_justice.py`

**File header + imports pattern** (lines 1–29):
```python
"""Add source_docket, cover_metadata JSONB to arguments; make argued_date nullable.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-30
...
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql  # required for JSONB

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Core DDL pattern** (from 0010 lines 31–48, adapted):
```python
def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("source_docket", sa.String(50), nullable=True),
    )
    op.add_column(
        "arguments",
        sa.Column("cover_metadata", postgresql.JSONB(), nullable=True),
    )
    op.alter_column("arguments", "argued_date", nullable=True)
    op.create_unique_constraint(
        "uq_arguments_source_docket_question",
        "arguments",
        ["source_docket", "question_number"],
    )

def downgrade() -> None:
    op.drop_constraint("uq_arguments_source_docket_question", "arguments", type_="unique")
    op.alter_column("arguments", "argued_date", nullable=False)
    op.drop_column("arguments", "cover_metadata")
    op.drop_column("arguments", "source_docket")
```

**Key notes:**
- No `op.execute("COMMIT")` needed — no `ALTER TYPE ADD VALUE` here (that guard is enum-specific)
- `op.alter_column` for `argued_date → nullable=True` needs no backfill because all existing rows already have a value
- `postgresql.JSONB()` import must be from `sqlalchemy.dialects`, not `sqlalchemy.dialects.postgresql.types`

---

### `api/schemas/admin_arguments.py` — new `MetadataUpdate` schema, extended `ArgumentDetail` and `ArgumentListItem`

**Analog:** `api/schemas/admin_arguments.py` (ArgumentUpdate, lines 127–145)

**Existing ArgumentUpdate pattern to mirror** (lines 127–145):
```python
class ArgumentUpdate(BaseModel):
    """PATCH request body for updating an argument record.

    Mass-assignment guard (T-11-MASS): ONLY case_name, docket_number, and
    argued_date are writable via PATCH.
    ...
    argued_date is accepted as an ISO 8601 string ("YYYY-MM-DD") and parsed
    by the service layer with datetime.date.fromisoformat() (V5 Input Validation).
    """
    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None  # ISO date string "YYYY-MM-DD"
```

**New MetadataUpdate schema** (copy ArgumentUpdate pattern exactly):
```python
class MetadataUpdate(BaseModel):
    """PATCH body for argument metadata from job detail page (D-15).
    Mass-assignment guard: only case_name, source_docket, argued_date writable.
    argued_date accepted as ISO 8601 string; parsed by service with fromisoformat().
    """
    case_name: Optional[str] = None
    source_docket: Optional[str] = None
    argued_date: Optional[str] = None  # ISO date string "YYYY-MM-DD"
```

**ArgumentListItem change** — line 77 `argued_date: datetime.date` becomes:
```python
argued_date: Optional[datetime.date] = None  # D-08: nullable after migration 0011
```

**ArgumentDetail change** — line 112 `argued_date: datetime.date` becomes:
```python
argued_date: Optional[datetime.date] = None  # D-08: nullable after migration 0011
```
Add two new fields to `ArgumentDetail`:
```python
source_docket: Optional[str] = None        # D-01: new column on Argument
cover_metadata: Optional[dict] = None      # D-07: JSONB, raw cover extractor output
```

---

### `api/services/admin_arguments.py` — new `check_duplicate_argument`, `update_argument_metadata`

**Analog:** `api/services/admin_arguments.py` (get_argument_detail lines 85–203, update_argument lines 204+)

**Imports pattern** (lines 1–35 of existing file — follow exactly):
```python
import datetime
from sqlalchemy import and_, exists, func as sqlfunc, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument, ...
```

**check_duplicate pattern** (mirrors scalar_one_or_none guard from get_argument_detail):
```python
async def check_duplicate_argument(db: AsyncSession, docket: str, question: int) -> dict:
    """Check if an argument with (source_docket, question_number) already exists.
    Returns {"exists": bool, "argument_id": int | None}.
    """
    result = await db.execute(
        select(Argument.id).where(
            Argument.source_docket == docket,
            Argument.question_number == question,
        )
    )
    row = result.scalar_one_or_none()
    return {"exists": row is not None, "argument_id": row}
```

**update_argument_metadata pattern** (mirrors update_argument: fromisoformat, execution_options guard):
```python
async def update_argument_metadata(
    db: AsyncSession, argument_id: int, body: MetadataUpdate
) -> bool:
    """Update Argument.argued_date, Argument.source_docket, and lead Case.case_name.
    Returns False if argument_id not found (router → 404).
    Mass-assignment guard: only the three fields above are writable.
    Critical guard: every update() uses .execution_options(synchronize_session=False).
    """
    arg_result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        return False

    # UPDATE Argument — only argued_date and source_docket
    argued_date_parsed = (
        datetime.date.fromisoformat(body.argued_date)
        if body.argued_date else None
    )
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(
            argued_date=argued_date_parsed,
            source_docket=body.source_docket,
        )
        .execution_options(synchronize_session=False)
    )

    # UPDATE lead Case.case_name (only if provided)
    if body.case_name is not None:
        lead_result = await db.execute(
            select(CaseArgument.case_id).where(
                CaseArgument.argument_id == argument_id,
                CaseArgument.is_lead == True,  # noqa: E712
            )
        )
        lead_row = lead_result.first()
        if lead_row:
            await db.execute(
                update(Case)
                .where(Case.id == lead_row.case_id)
                .values(case_name=body.case_name)
                .execution_options(synchronize_session=False)
            )
    return True
```

**get_argument_detail extension** — add `source_docket` and `cover_metadata` to the returned dict (lines 192–203):
```python
return {
    "id": argument.id,
    "argued_date": argument.argued_date,      # now Optional — no change needed
    "source_docket": argument.source_docket,  # NEW
    "cover_metadata": argument.cover_metadata, # NEW — JSONB, may be None
    "case_name": lead_case.case_name,
    ...
}
```

---

### `api/routers/admin.py` — new `GET /arguments/check-duplicate` and `PATCH /arguments/{id}/metadata`

**Analog:** `api/routers/admin.py` (existing argument routes, lines 617–695)

**Route registration order** (CRITICAL — verified from admin.py lines 617–695):
```
Line 617: @router.get("/arguments")                          ← list
Line 630: @router.get("/arguments/{argument_id}")            ← detail (parameterized)
Line 648: @router.patch("/arguments/{argument_id}")          ← update
Line 673: @router.post("/arguments/{argument_id}/publish")
Line 695: @router.post("/arguments/{argument_id}/unpublish")
```
The new `GET /arguments/check-duplicate` MUST be inserted **before** line 630 (`GET /arguments/{argument_id}`) to avoid FastAPI matching `check-duplicate` as a path parameter.

**check-duplicate endpoint pattern** (after line 629, before the detail route):
```python
@router.get("/arguments/check-duplicate")
async def check_duplicate_argument(
    docket: str,
    question: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    JS preflight: check if (source_docket, question_number) already exists (D-04).
    Returns 200 always — absence of match is valid. Auth inherited at router level.
    """
    return await arguments_service.check_duplicate_argument(db, docket, question)
```

**metadata PATCH endpoint pattern** (after unpublish, follows existing PATCH pattern lines 648–671):
```python
@router.patch("/arguments/{argument_id}/metadata")
async def update_argument_metadata(
    argument_id: int,
    body: MetadataUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Save operator-reviewed metadata from job detail page (D-15).
    Updates Argument.argued_date, Argument.source_docket, and lead Case.case_name.
    """
    success = await arguments_service.update_argument_metadata(db, argument_id, body)
    if not success:
        raise HTTPException(status_code=404, detail="Argument not found")
    return {"success": True}
```

**Imports to add to admin.py** (follow existing import block structure):
```python
from api.schemas.admin_arguments import (
    ArgumentDetail,
    ArgumentListItem,
    ArgumentUpdate,
    MetadataUpdate,       # NEW
    ParticipantSideUpdate,
)
```

---

### `pipeline/parser/cover_extractor.py` — extend to extract `primary_docket`

**Analog:** `pipeline/parser/cover_extractor.py` (extract_cover_metadata, lines 230–263)

**New regex constant** (add after CAPTION_PUNCT_RE block, lines 49–58):
```python
# Docket number — Alderson: "No. 14-556" / "No. 14-556, 14-562"
# Heritage format may differ — partial match is the acceptable fallback (D-10, A1)
DOCKET_RE = re.compile(
    r'No\.\s+(\d{1,2}-\d+)',
    re.IGNORECASE,
)
```

**Extension to `extract_cover_metadata`** — insert inside the `for raw in raws` loop (after lines 254–258):
```python
# Existing loop structure (lines 250–260) — add primary_docket alongside argued_date/case_name:
for raw in raws:
    if "argued_date" not in result:
        m = DATE_LINE_RE.search(raw) or HERITAGE_DATE_RE.search(raw)
        if m:
            result["argued_date"] = _parse_date(m)
    if "case_name" not in result:
        name = _extract_case_name(_clean_lines(raw))
        if name:
            result["case_name"] = name
    if "primary_docket" not in result:        # NEW
        m = DOCKET_RE.search(raw)             # NEW
        if m:                                 # NEW
            result["primary_docket"] = m.group(1)  # NEW
    if len(result) == 3:                      # was 2 — now stops when all three found
        break
```

**Fail-safe pattern** (lines 261–263 — do NOT change):
```python
    except Exception:
        pass  # D-05: never raise; caller receives partial result or {}
return result
```

---

### `pipeline/commands/parse.py` — write `cover_metadata`, conditional `source_docket`

**Analog:** `pipeline/commands/parse.py` Phase 16 PARSE-01 block (lines 308–342)

**Existing blocks to keep and modify** (lines 314–342):
```python
# Block A: argued_date → Argument row
# CHANGED in Phase 19 D-09: only if currently NULL (was "always overwrite" per Phase 16 D-04)
if cover_meta.get("argued_date") is not None:
    await session.execute(
        update(Argument)
        .where(Argument.id == source_run.argument_id, Argument.argued_date.is_(None))
        .values(argued_date=cover_meta["argued_date"])
        .execution_options(synchronize_session=False)
    )

# Block B: case_name — keep existing conditional logic (unchanged)
```

**New blocks to insert after Block B** (after line 342):
```python
# Block C: cover_metadata — always written unconditionally (D-07, D-09a)
await session.execute(
    update(Argument)
    .where(Argument.id == source_run.argument_id)
    .values(cover_metadata=cover_meta if cover_meta else None)
    .execution_options(synchronize_session=False)
)

# Block D: source_docket — only if currently NULL (D-09b)
if cover_meta.get("primary_docket") is not None:
    await session.execute(
        update(Argument)
        .where(
            Argument.id == source_run.argument_id,
            Argument.source_docket.is_(None),
        )
        .values(source_docket=cover_meta["primary_docket"])
        .execution_options(synchronize_session=False)
    )
```

**Critical guard** (project-wide, from admin_arguments.py docstring): Every `update()` statement MUST include `.execution_options(synchronize_session=False)`.

**Phase 19 behavioral change note:** Block A changes from "always overwrite" (Phase 16 D-04) to "only if NULL" (Phase 19 D-09). The `update().where(..., Argument.argued_date.is_(None))` WHERE clause enforces this — the UPDATE is a no-op when `argued_date` is already set.

---

### `pipeline/commands/ingest.py` — `source_docket`, nullable `argued_date`

**Analog:** `pipeline/commands/ingest.py` (job-driven path, lines 253–266 and 350–356)

**Existing job-driven path** (lines 253–266 — to be replaced):
```python
# CURRENT (to replace in Phase 19):
if not primary_docket or not case_name or not argued_date:
    derived_docket, derived_name, derived_date = _derive_metadata_from_key(
        spaces_key or "", args.job_id
    )
    primary_docket = primary_docket or derived_docket
    case_name = case_name or derived_name
    argued_date = argued_date or derived_date
```

**New job-driven path** (D-03/D-08 — do NOT call `_derive_metadata_from_key` for synthetic placeholders):
```python
# Phase 19 D-03/D-08: use provided values; leave NULL when not provided
# primary_docket and argued_date are already read from args above
# No synthetic placeholder — empty fields stay None
```

**Argument creation change** (lines 351–354 — `argued_date` becomes Optional):
```python
# CURRENT:
argument = Argument(
    argued_date=date.fromisoformat(argued_date),
    question_number=args.question,
)

# Phase 19 D-08:
argument = Argument(
    argued_date=date.fromisoformat(argued_date) if argued_date else None,
    question_number=args.question,
    source_docket=primary_docket or None,   # D-01: new column
)
```

**IntegrityError catch pattern** (new, wrap the session.flush after argument.add):
```python
from sqlalchemy.exc import IntegrityError

try:
    session.add(argument)
    await session.flush()
except IntegrityError:
    raise ValueError(
        f"Duplicate argument: docket {primary_docket!r} Q{args.question} already exists."
    )
```

**D-02 failure path** — the ValueError propagates to the job runner, which marks `admin_jobs.status = FAILED` with `error_message`. Verify the ingest error-catching wrapper already converts ValueError to a FAILED job status (existing pattern — look at how other ValueErrors in `_run_ingest_inner` are handled at the call site).

---

### `pipeline/tests/test_cover_extractor.py` — docket extraction tests

**Analog:** `pipeline/tests/test_cover_extractor.py` (existing PARSE-01 tests, lines 24–60)

**Existing test pattern to copy**:
```python
def test_extract_case_name_alderson_basic():
    """_extract_case_name on Alderson-format lines returns name up to 'Petitioners,'."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "\xad \xad \xad ... x",
        "JAMES OBERGEFELL, ET AL.,",
        "Petitioners,",
    ]
    result = _extract_case_name(lines)
    assert result == "JAMES OBERGEFELL, ET AL."
```

**New docket tests to add** (follow same import-inside-test pattern):
```python
def test_extract_cover_metadata_docket_alderson():
    """extract_cover_metadata returns primary_docket from Alderson 'No. 14-556' pattern."""
    from pipeline.parser.cover_extractor import DOCKET_RE

    raw = "IN THE SUPREME COURT\nNo. 14-556\nObergefell v. Hodges"
    m = DOCKET_RE.search(raw)
    assert m is not None
    assert m.group(1) == "14-556"

def test_extract_cover_metadata_docket_absent():
    """extract_cover_metadata returns {} primary_docket key when no docket pattern found."""
    from pipeline.parser.cover_extractor import DOCKET_RE

    raw = "IN THE SUPREME COURT\nNo docket here."
    m = DOCKET_RE.search(raw)
    assert m is None
```

---

### `app/src/routes/admin/pipeline/check-duplicate/+server.ts` (NEW proxy endpoint)

**Analog:** `app/src/routes/admin/people/[id]/merge-preview/+server.ts` (entire file, 43 lines)

**Full file pattern** (copy merge-preview exactly, adapted for check-duplicate):
```typescript
/**
 * GET /admin/pipeline/check-duplicate?docket={docket}&question={question}
 *
 * Server-only proxy to FastAPI GET /api/admin/arguments/check-duplicate.
 * Injects ADMIN_TOKEN server-side — browser never sees the secret
 * (mirrors merge-preview +server.ts pattern, T-12-TOKENLEAK).
 *
 * Returns { exists: boolean, argument_id: number | null }
 */
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, fetch }) => {
    const docket = url.searchParams.get('docket');
    const question = url.searchParams.get('question');

    if (docket === null || question === null) {
        return error(400, 'docket and question are required');
    }

    let res: Response;
    try {
        res = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/arguments/check-duplicate?docket=${encodeURIComponent(docket)}&question=${encodeURIComponent(question)}`,
            { headers: { 'X-Admin-Token': ADMIN_TOKEN } }
        );
    } catch {
        return error(502, 'Could not check for duplicate');
    }

    if (!res.ok) {
        return error(502, 'Could not check for duplicate');
    }

    return json(await res.json(), { headers: { 'Cache-Control': 'no-store' } });
};
```

---

### `app/src/routes/admin/pipeline/+page.svelte` — docket input, Q# selector, preflight banner

**Analog:** `app/src/routes/admin/pipeline/+page.svelte` (existing form, lines 174–290)

**Existing form field pattern** (lines 183–215 — copy input styling exactly):
```svelte
<div style="margin-bottom: 16px;">
    <label
        for="pdf_url"
        style="
            display: block;
            font-size: 14px;
            font-weight: 400;
            color: #94a3b8;
            margin-bottom: 8px;
        "
    >
        Transcript PDF URL
    </label>
    <input
        type="url"
        name="pdf_url"
        id="pdf_url"
        required
        placeholder="https://www.supremecourt.gov/..."
        style="
            display: block;
            width: 100%;
            background-color: #0f1117;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 16px;
            color: #e2e8f0;
            box-sizing: border-box;
        "
    />
</div>
```

**New docket input** (insert after URL/file input, same styling, not `required`):
```svelte
<div style="margin-bottom: 16px;">
    <label for="primary_docket" style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;">
        Docket Number
    </label>
    <input
        type="text"
        name="primary_docket"
        id="primary_docket"
        placeholder="e.g. 14-556 (optional)"
        bind:value={docketInput}
        style="display: block; width: 100%; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #e2e8f0; box-sizing: border-box;"
    />
</div>
```

**Svelte 5 Runes state pattern** (follows `let submitting = $state(false)` line 26):
```typescript
let docketInput = $state('');
let questionInput = $state('1');
let duplicateWarning = $state<{ argumentId: number; docket: string; question: string } | null>(null);
let preflightCleared = $state(false);
```

**Preflight submit handler pattern** (replace `handleSubmit` lines 32–34):
```typescript
async function handleSubmit(e: SubmitEvent) {
    if (!docketInput.trim() || preflightCleared) {
        submitting = true;
        return; // no preflight or already confirmed — let form proceed
    }
    e.preventDefault();
    const res = await fetch(
        `/admin/pipeline/check-duplicate?docket=${encodeURIComponent(docketInput.trim())}&question=${encodeURIComponent(questionInput)}`
    );
    const data = await res.json();
    if (data.exists) {
        duplicateWarning = { argumentId: data.argument_id, docket: docketInput.trim(), question: questionInput };
    } else {
        preflightCleared = true;
        (e.target as HTMLFormElement).requestSubmit();
    }
}
```

**Duplicate warning banner pattern** (insert above submit button, before lines 268–290, follows `{#if form?.error}` pattern lines 253–266):
```svelte
{#if duplicateWarning}
    <div role="alert" style="border: 1px solid #fbbf24; border-radius: 6px; padding: 16px; margin-bottom: 16px; background-color: #1e293b;">
        <p style="color: #fbbf24; font-size: 14px; margin: 0 0 8px 0;">
            An argument for docket {duplicateWarning.docket} Q{duplicateWarning.question} already exists.
            <a href="/admin/arguments/{duplicateWarning.argumentId}" style="color: #93c5fd; text-decoration: underline;">View existing argument</a>
        </p>
        <div style="display: flex; gap: 8px;">
            <button type="button" onclick={() => duplicateWarning = null}
                style="font-size: 14px; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px; background-color: transparent; color: #e2e8f0; cursor: pointer;">
                Cancel
            </button>
            <button type="button" onclick={() => { preflightCleared = true; duplicateWarning = null; document.querySelector('form')?.requestSubmit(); }}
                style="font-size: 14px; padding: 8px 16px; border: 1px solid #fbbf24; border-radius: 6px; background-color: transparent; color: #fbbf24; cursor: pointer;">
                Start anyway
            </button>
        </div>
    </div>
{/if}
```

---

### `app/src/routes/admin/pipeline/+page.server.ts` — forward primary_docket + question

**Analog:** `app/src/routes/admin/pipeline/+page.server.ts` (default action, lines 30–99)

**Existing FormData forwarding pattern** (lines 37–43):
```typescript
const pdf_url = (data.get('pdf_url') as string) ?? '';
const body = new FormData();
body.append('pdf_url', pdf_url);
```

**New fields to add** (insert before the `body.append` calls in both `url` and `upload` branches):
```typescript
const primary_docket = (data.get('primary_docket') as string)?.trim() || null;
const question_number = (data.get('question_number') as string)?.trim() || '1';

const body = new FormData();
body.append('pdf_url', pdf_url);   // existing
if (primary_docket) body.append('primary_docket', primary_docket);
body.append('question_number', question_number);
```

Note: FastAPI's `create_job` endpoint (`POST /api/admin/jobs`) must also be updated to accept `primary_docket` and `question_number` form fields and forward them as `--primary-docket` and `--question` subprocess args via `spawn_pipeline_step`.

---

### `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load cover_metadata, saveMetadata action

**Analog:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (approve action lines 155–216, argument load block lines 86–104)

**Existing argument load pattern** (lines 86–104 — no change needed to the fetch itself):
```typescript
let argument: ArgumentPreview | null = null;
if (job.argument_id != null) {
    try {
        const argRes = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/arguments/${job.argument_id}`,
            { headers: { 'X-Admin-Token': ADMIN_TOKEN } },
        );
        if (argRes.ok) {
            argument = await argRes.json();
        }
    } catch (err) { ... }
}
```

**ArgumentPreview interface extension** (lines 13–21):
```typescript
interface ArgumentPreview {
    id: number;
    case_name: string;
    docket_number: string;
    argued_date: string | null;
    resolved_at: string | null;
    published_at: string | null;
    status: string | null;
    source_docket: string | null;       // NEW D-01
    cover_metadata: Record<string, unknown> | null;  // NEW D-07
}
```

**saveMetadata action pattern** (follows approve action lines 155–216):
```typescript
saveMetadata: async ({ request, params }) => {
    const data = await request.formData();
    const case_name = (data.get('case_name') as string)?.trim() || null;
    const source_docket = (data.get('source_docket') as string)?.trim() || null;
    const argued_date = (data.get('argued_date') as string)?.trim() || null;

    // Get argument_id from the job (same pattern as approve action lines 167–179)
    let argumentId: number | null = null;
    try {
        const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
        if (jobRes.ok) {
            const job = await jobRes.json();
            argumentId = job.argument_id ?? null;
        }
    } catch { /* continue */ }

    if (argumentId == null) {
        return fail(400, { metadataError: 'No argument linked to this job yet.' });
    }

    let res: Response;
    try {
        res = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/metadata`,
            {
                method: 'PATCH',
                headers: {
                    'X-Admin-Token': ADMIN_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ case_name, source_docket, argued_date }),
            },
        );
    } catch {
        return fail(502, { metadataError: 'Could not save metadata. Please try again.' });
    }

    if (!res.ok) {
        return fail(422, { metadataError: 'Could not save metadata. Please try again.' });
    }

    return { metadataSaved: true };
},
```

---

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Argument Metadata card

**Analog:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (job detail card structure — existing card pattern with title + form)

**Card container pattern** (copy from existing cards — same background/border/padding):
```svelte
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 32px; margin-top: 32px;">
    <h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 24px 0; line-height: 1.2;">
        Argument Metadata
    </h2>
    <form method="POST" action="?/saveMetadata" use:enhance>
        <!-- case_name field -->
        <!-- source_docket field -->
        <!-- argued_date field -->
        <!-- hint text pattern -->
        <!-- save button -->
    </form>
</div>
```

**Hint text pattern** (D-14 — "Extracted: [value]" as muted secondary text below input):
```svelte
{#if data.argument?.cover_metadata?.case_name && data.argument.cover_metadata.case_name !== formCaseName}
    <p style="font-size: 12px; color: #64748b; margin: 4px 0 0 0;">
        Extracted: {data.argument.cover_metadata.case_name}
    </p>
{/if}
```

**Null guard pattern** (D-09, Pitfall 9 in RESEARCH): Always check `cover_metadata?.[field]` before rendering hint text. Null `cover_metadata` renders nothing — no error.

**metadataSaved success message pattern** (follow `form?.success` pattern used in existing approve action):
```svelte
{#if form?.metadataSaved}
    <p style="color: #4ade80; font-size: 14px; margin: 8px 0 0 0;">Metadata saved.</p>
{/if}
{#if form?.metadataError}
    <p role="alert" style="color: #ef4444; font-size: 14px; margin: 8px 0 0 0;">{form.metadataError}</p>
{/if}
```

---

## Shared Patterns

### Authentication
**Source:** `api/routers/admin.py` (lines 86–107)
**Apply to:** Both new FastAPI endpoints (`check-duplicate` GET and `/metadata` PATCH)
```python
# Auth is inherited at router level — no per-route auth needed:
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
# Simply register new routes on this router — auth is automatic.
```

### Admin Token Proxy
**Source:** `app/src/routes/admin/people/[id]/merge-preview/+server.ts` (full file)
**Apply to:** `app/src/routes/admin/pipeline/check-duplicate/+server.ts`
- `ADMIN_TOKEN` imported from `$env/static/private` — NEVER passed to client
- Browser fetches the SvelteKit `+server.ts` (same-origin); SvelteKit proxies to FastAPI
- Return `json(await res.json(), { headers: { 'Cache-Control': 'no-store' } })`

### Error Handling — FastAPI services
**Source:** `api/services/admin_arguments.py` (get_argument_detail lines 85–97, update_argument)
**Apply to:** `check_duplicate_argument`, `update_argument_metadata`
```python
# Return None when argument not found → router raises 404
arg_result = await db.execute(select(Argument).where(Argument.id == argument_id))
argument = arg_result.scalar_one_or_none()
if argument is None:
    return None  # or False — router: if not result: raise HTTPException(404)
```

### synchronize_session=False Guard
**Source:** `api/services/admin_arguments.py` docstring + `pipeline/commands/parse.py` lines 316–340
**Apply to:** ALL new `update()` statements in parse.py and admin_arguments.py
```python
.execution_options(synchronize_session=False)
```
This is a project-wide critical guard — every UPDATE without it may fail silently in async context.

### SvelteKit server-to-FastAPI fetch
**Source:** `app/src/routes/admin/pipeline/+page.server.ts` (lines 14–17, 47–50)
**Apply to:** saveMetadata action, check-duplicate proxy
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
// ...
headers: { 'X-Admin-Token': ADMIN_TOKEN }
```

### Svelte 5 Runes state
**Source:** `app/src/routes/admin/pipeline/+page.svelte` (lines 23–34)
**Apply to:** `+page.svelte` preflight state, metadata card state
```typescript
let submitting = $state(false);
let mode = $state<'url' | 'upload'>('url');
// New state follows same $state<Type>(initialValue) pattern
```

### `use:enhance` form action
**Source:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (existing action forms)
**Apply to:** Argument Metadata card form — `use:enhance` for progressive enhancement

---

## No Analog Found

All files have strong analogs in the codebase. No file requires falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `api/`, `pipeline/`, `alembic/versions/`, `app/src/routes/admin/`
**Files scanned:** 14 source files read directly
**Pattern extraction date:** 2026-06-30
