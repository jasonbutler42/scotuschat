# Phase 19: Pipeline Reliability — Research

**Researched:** 2026-06-30
**Domain:** PostgreSQL unique constraints, FastAPI admin endpoints, SvelteKit form actions with JS preflight, Python cover extractor extension, Alembic hand-written migrations
**Confidence:** HIGH — all findings sourced directly from the project codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Uniqueness Constraint**
- D-01: Add `source_docket VARCHAR(50) NULL` column to `arguments`. Add UNIQUE constraint on `(source_docket, question_number)`. PostgreSQL NULL semantics apply — multiple rows with `source_docket = NULL` do NOT violate the constraint. Migration 0011.
- D-02: If ingest hits the unique constraint at DB write time: mark `admin_jobs.status = FAILED` with a human-readable `error_message`. No silent creation of a duplicate row.

**Pipeline Start Form Changes**
- D-03: Add optional docket field (text input) and Q1/Q2 question_number selector (default Q1) to the pipeline start form. Both are passed to the ingest subprocess as `--primary-docket` and `--question` args. If operator fills docket, ingest uses it to create a real `Case` row immediately (not a synthetic `job-{N}` placeholder).
- D-04: JS preflight fires on form submit if docket is filled: calls `GET /api/admin/arguments/check-duplicate?docket=...&question=...` before the SvelteKit form action.
- D-05: If preflight finds a match: inline warning banner appears above the Submit button with a link to the existing argument. Two buttons: "Cancel" and "Start anyway".
- D-06: If the docket field is empty: no preflight fires. The DB unique constraint is the backstop. Upload mode gets no preflight.

**Argument Model — New Columns (Migration 0011)**
- D-07: Add `cover_metadata JSONB NULL` to `arguments`. Parse always writes raw cover extractor output here unconditionally after parse completes.
- D-08: Make `Argument.argued_date` nullable. Job-driven ingest leaves it `NULL` instead of using today's date as a synthetic placeholder.

**Metadata Write-back (Parse Step)**
- D-09: At the end of parse, the parse step: (a) always writes raw extraction output to `cover_metadata` (unconditional); (b) auto-populates null main fields — `argued_date`, `case_name`, `source_docket` — from extraction results if and only if those fields are currently NULL. Does NOT overwrite operator-entered values.
- D-10: If cover extraction fails or returns empty: leave null fields as null, continue parse normally.
- D-11: Empty field = not yet extracted. No separate "extraction succeeded/failed" badge needed.

**Cover Extractor Extension**
- D-12: Extend `cover_extractor.py` to extract `primary_docket` in addition to `argued_date` and `case_name`. Must support both Alderson and Heritage transcript cover formats. Docket numbers appear as "No. 14-556" on Alderson covers. Update `pipeline/tests/test_cover_extractor.py` with docket extraction tests.

**Job Detail Page — Metadata Card**
- D-13: The job detail page gains a new "Argument Metadata" card with editable inputs for case name, docket, and argued date.
- D-14: When `cover_metadata` contains a value for a field that is already populated (operator-entered), the editor shows hint text below the input: `Extracted: [extracted value]`. When a field is null and extraction found a value, it is auto-populated.
- D-15: Saving the metadata card calls a new FastAPI admin endpoint that updates the `Argument` row (`argued_date`, `source_docket`) and the linked `Case` row (`case_name`) in the DB.

### Claude's Discretion

None specified — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Live polling for pipeline list page job cards — belongs to Phase 20 (PIPE-23, PIPE-24).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-25 | System enforces a unique DB constraint preventing duplicate arguments; UI warns the operator before starting a new run if a matching argument already exists | Migration 0011 adds UNIQUE on `(source_docket, question_number)`; FastAPI `check-duplicate` endpoint; JS preflight on start form; ingest failure path for constraint violation |
| PIPE-26 | Argument metadata (case name, docket, argued date) pre-populated from cover extraction results visible to operator during/after the pipeline run | Cover extractor extended to return `primary_docket`; parse step writes `cover_metadata` JSONB and auto-populates null fields; job detail metadata card with editable fields and hint text |
</phase_requirements>

---

## Summary

Phase 19 delivers two independent reliability features for the pipeline. The codebase is well-understood with no ambiguity about touch points — every file to modify is identified in CONTEXT.md and verified in this research session.

**Duplicate prevention (PIPE-25)** requires a Migration 0011 to add `source_docket VARCHAR(50) NULL` and a UNIQUE constraint `(source_docket, question_number)` to `arguments`. Ingest must be updated to (a) accept `--primary-docket` and `--question` CLI args from the form, (b) populate `source_docket` when `args.primary_docket` is set, and (c) leave `source_docket = NULL` and `argued_date = NULL` when not set (abandoning the synthetic `job-{N}` placeholder pattern from `_derive_metadata_from_key`). A new FastAPI endpoint `GET /api/admin/arguments/check-duplicate` enables JS preflight on the start form. The pipeline start form gains optional docket + question_number fields with a JS preflight that intercepts submit, calls the endpoint, and conditionally shows a duplicate warning banner or proceeds.

**Metadata prefill (PIPE-26)** requires extending `cover_extractor.py` to also return `primary_docket`, adding `cover_metadata JSONB NULL` and making `argued_date` nullable in Migration 0011, and extending the parse step's existing cover metadata write-back block to also (a) unconditionally write raw extraction output to `cover_metadata`, and (b) conditionally populate `source_docket` from extraction if it is currently NULL. The job detail page gains a new "Argument Metadata" card with three editable fields and a new FastAPI PATCH endpoint for saving them.

**Primary recommendation:** Implement in four clearly separated concerns — (1) migration 0011, (2) ingest changes, (3) parse/extractor changes, (4) UI + FastAPI endpoint changes — each independently testable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Unique constraint enforcement | Database | API (ingest pipeline) | PostgreSQL enforces the UNIQUE constraint; ingest catches `IntegrityError` and converts to human-readable failure |
| Duplicate check (preflight) | API / Backend | Browser / Client | FastAPI `check-duplicate` endpoint is the authority; JS calls it before form submission |
| Duplicate warning banner | Browser / Client | — | Pure UI state machine — no server round-trip beyond the preflight fetch |
| Ingest args forwarding | Frontend Server (SSR) | API / Backend | SvelteKit form action reads form fields and passes as subprocess CLI args; FastAPI job creation does NOT change |
| Cover metadata extraction | Pipeline | — | `cover_extractor.py` runs synchronously in the pipeline subprocess; no API involvement |
| cover_metadata JSONB write | Pipeline | — | Parse step writes directly to PostgreSQL (pipeline writes DB directly per CLAUDE.md architecture) |
| Metadata auto-population | Pipeline | — | Parse step fills null fields from extraction results; no UI involvement at parse time |
| Metadata card save | API / Backend | Frontend Server (SSR) | New FastAPI PATCH endpoint; SvelteKit server action proxies the call |

---

## Standard Stack

No new external packages. All work uses the existing project stack.

### Existing Libraries Used (no new installs)

| Library | Version (in use) | Purpose in this phase |
|---------|-----------------|----------------------|
| SQLAlchemy 2.0 async | existing | `UniqueConstraint`, `JSONB` column, UPDATE statements in ingest/parse |
| Alembic | existing | Migration 0011 DDL — hand-written per project convention |
| pdfplumber | existing | Cover extractor reads PDF pages 0–2 for docket extraction |
| FastAPI + Pydantic v2 | existing | New `check-duplicate` endpoint, new metadata PATCH endpoint, new schemas |
| SvelteKit 2.x / Svelte 5 | existing | Start form JS preflight, job detail metadata card, `use:enhance` save action |

### No New Packages

This phase introduces zero new npm or PyPI dependencies. The UI uses only native HTML form elements and inline styles (per UI-SPEC).

---

## Package Legitimacy Audit

No external packages are installed in this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No new packages |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** none

---

## Architecture Patterns

### System Architecture Diagram

```
PIPE-25: Duplicate Prevention

Operator fills docket + Q# → [Start form submit]
  ↓ JS intercepts onsubmit
  ↓ fetch GET /api/admin/arguments/check-duplicate?docket=X&question=N
      ↓ FastAPI queries arguments.source_docket + question_number
      ↓ returns {exists: bool, argument_id: int|null}
  ↓ if exists → render warning banner (Cancel | Start anyway)
  ↓ if not exists / Start anyway → SvelteKit form action
      ↓ reads primary_docket + question_number from FormData
      ↓ forwards as --primary-docket, --question args to ingest subprocess
          ↓ ingest creates Argument(source_docket=docket, argued_date=NULL, question_number=N)
          ↓ DB UNIQUE(source_docket, question_number) enforces constraint
          ↓ on IntegrityError → AdminJob.status = FAILED + error_message

PIPE-26: Metadata Prefill

[Parse step completes utterances]
  ↓ extract_cover_metadata(pdf_path) → {argued_date, case_name, primary_docket} or {}
  ↓ always writes raw result → Argument.cover_metadata = {...}
  ↓ if argued_date NULL on Argument → UPDATE Argument SET argued_date = extracted_date
  ↓ if source_docket NULL on Argument → UPDATE Argument SET source_docket = extracted_docket
  ↓ if case_name still synthetic → UPDATE Case SET case_name = extracted_name

[Operator views job detail page]
  ↓ load: fetch Argument → cover_metadata, argued_date, source_docket
  ↓ fetch linked Case → case_name
  ↓ render "Argument Metadata" card with pre-populated inputs
  ↓ show hint "Extracted: [X]" when field value ≠ cover_metadata value

[Operator clicks Save metadata]
  ↓ SvelteKit ?/saveMetadata action
  ↓ PATCH /api/admin/arguments/{id}/metadata {case_name, source_docket, argued_date}
      ↓ UPDATE Argument SET argued_date, source_docket
      ↓ UPDATE Case SET case_name (lead case only)
```

### Recommended Project Structure (changes only)

```
alembic/versions/
└── 0011_add_source_docket_cover_metadata.py   ← NEW migration

pipeline/
├── parser/
│   └── cover_extractor.py                      ← EXTEND: add primary_docket extraction
├── commands/
│   ├── ingest.py                               ← MODIFY: source_docket, nullable argued_date
│   └── parse.py                                ← MODIFY: write cover_metadata, conditional source_docket
└── tests/
    └── test_cover_extractor.py                 ← EXTEND: docket extraction tests

api/
├── routers/
│   └── admin.py                                ← ADD: check-duplicate + metadata PATCH endpoints
├── schemas/
│   └── admin_arguments.py                      ← ADD: MetadataUpdate schema
└── services/
    └── admin_arguments.py                      ← ADD: check_duplicate_argument, update_argument_metadata

app/src/routes/admin/pipeline/
├── +page.svelte                                ← ADD: docket input, Q# selector, preflight, banner
├── +page.server.ts                             ← ADD: forward primary_docket + question_number
└── [job_id]/
    ├── +page.svelte                            ← ADD: Argument Metadata card
    └── +page.server.ts                         ← ADD: load cover_metadata; saveMetadata action
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique constraint enforcement | Application-layer duplicate check before INSERT | PostgreSQL UNIQUE constraint on `(source_docket, question_number)` | Race condition between check-then-insert; DB constraint is atomic |
| IntegrityError detection | String parsing of exception messages | `sqlalchemy.exc.IntegrityError` type check | sqlalchemy surfaces the constraint name in the exception |
| JSONB column in SQLAlchemy | Text column + JSON serialization | `Column(JSONB)` from `sqlalchemy.dialects.postgresql` | Already used on `admin_jobs.discrepancies` in this codebase |
| Date input ISO format | Custom format conversion | `value={argued_date_iso}` where iso string is sliced to 10 chars | Existing pattern: `toDateInputValue()` slices first 10 chars of ISO string |
| JS fetch with CSRF | Bare `fetch()` call | SvelteKit's `use:enhance` for form submissions; bare `fetch()` is fine for preflight GET calls (no state mutation) | Preflight is a read-only GET — no CSRF concern |

**Key insight:** The DB constraint is the authoritative backstop. The JS preflight is a UX convenience, not the security layer. Ingest must still handle the IntegrityError gracefully.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL NULL semantics for the unique constraint
**What goes wrong:** UNIQUE `(source_docket, question_number)` with `source_docket = NULL` does NOT deduplicate rows — multiple NULL rows are all distinct per SQL standard (NULL ≠ NULL in unique index evaluation).
**Why it happens:** Expected SQL behavior; CONTEXT.md D-01 explicitly acknowledges this.
**How to avoid:** Accept this. The constraint only deduplicates when docket is known. Upload-mode ingest (no docket at submit time) has no DB-level backstop. The operator warning and preflight are the only guards for that path.
**Warning signs:** Test confirms that two rows with `source_docket = NULL, question_number = 1` can coexist without constraint violation.

### Pitfall 2: `argued_date NOT NULL` → `NULL` requires all callers to handle None
**What goes wrong:** After migration 0011 makes `argued_date` nullable, any service or schema that assumes `argued_date` is always a date will fail at runtime.
**Why it happens:** `admin_arguments.py` list_arguments, get_argument_detail, update_argument all reference `argument.argued_date`. The `ArgumentListItem` schema has `argued_date: datetime.date` (non-optional).
**How to avoid:** Update `ArgumentListItem.argued_date` to `Optional[datetime.date]`. Update `get_argument_detail` tenure gap warning logic — it currently guards `if argument.argued_date is not None` (already correct). Audit all callers of `argued_date` after migration.
**Warning signs:** `422 Unprocessable Entity` from FastAPI when serializing a row with `argued_date = NULL`.

### Pitfall 3: Writing `cover_metadata` from a separate DB session
**What goes wrong:** Parse step currently runs cover extraction before the main async session (per Pitfall 1 from Phase 16 research — pdfplumber must not run inside the async transaction). The `cover_metadata` write must happen inside the main session, not a separate one that might commit before utterances.
**Why it happens:** `cover_meta` is already in scope before the main `async with get_session()` block. Writing it to the session within that block is correct — already the established pattern for `argued_date` and `case_name` writes (lines 315–340 in `parse.py`).
**How to avoid:** Add the `cover_metadata` JSONB write to the existing "Phase 16 PARSE-01" block in `parse.py`, alongside the existing `argued_date` and `case_name` writes. Do not open a new session.

### Pitfall 4: `execution_options(synchronize_session=False)` on every UPDATE
**What goes wrong:** UPDATE statements without `synchronize_session=False` cause SQLAlchemy to evaluate affected rows in memory, which fails silently or raises an error in async context.
**Why it happens:** Established project-wide critical guard documented in `admin_arguments.py` docstring.
**How to avoid:** Every new `update()` statement must include `.execution_options(synchronize_session=False)`. The existing update blocks in `parse.py` (lines 317–340) already set this — follow the exact same pattern.

### Pitfall 5: JS preflight fires as a POST, triggering CSRF protection
**What goes wrong:** If the preflight is implemented as a form submission or POST, SvelteKit's CSRF protection may reject it.
**Why it happens:** SvelteKit enforces same-origin CSRF checks on non-GET form submissions.
**How to avoid:** The preflight is a `fetch()` GET call — no CSRF concern. D-04 specifies `GET /api/admin/arguments/check-duplicate`. The FastAPI route must be `@router.get(...)`.

### Pitfall 6: `source_docket` on `Argument` vs `docket_number` on `Case`
**What goes wrong:** The codebase has `Case.docket_number` (the canonical docket, UNIQUE on the `cases` table). `Argument.source_docket` is a NEW tracking field for deduplication — not the same as `Case.docket_number`. The `check-duplicate` endpoint queries `Argument.source_docket`, not `Case.docket_number`.
**Why it happens:** The M:M join between cases and arguments means multiple cases can link to one argument. `source_docket` is the primary docket the operator used at ingest time — it matches what was passed as `--primary-docket`.
**How to avoid:** Never confuse these two. The unique constraint is on `arguments.source_docket` + `arguments.question_number`. The `Cases.docket_number` UNIQUE constraint is separate and already exists.

### Pitfall 7: `_derive_metadata_from_key` still called when `--primary-docket` is provided
**What goes wrong:** The current ingest code at line 261–265 calls `_derive_metadata_from_key` and uses the derived values only if `primary_docket` is falsy. After D-03/D-08, the behavior changes: when `--primary-docket` is set, use it. When not set, leave `source_docket = NULL` and `argued_date = NULL` (no synthetic placeholder).
**Why it happens:** `_derive_metadata_from_key` returns synthetic `argued_date = date.today()`. After D-08, leaving `argued_date = NULL` is correct.
**How to avoid:** In the job-driven path: if `args.primary_docket` is set, use it for `source_docket`. If `args.case_name` is set, use it. If `args.argued_date` is set, parse it. Leave any unset fields as `None`. Do not call `_derive_metadata_from_key` for a synthetic `argued_date` — the `Argument` row gets `argued_date = NULL`.

### Pitfall 8: `ArgumentListItem.argued_date` expected as non-null by list consumers
**What goes wrong:** The `list_arguments` query in `admin_arguments.py` joins Argument to Case and returns `argued_date`. The list page template may render `argued_date` directly without a null guard.
**Why it happens:** `argued_date` was `NOT NULL` before migration 0011.
**How to avoid:** After making the column nullable, audit the `ArgumentListItem` schema (make `argued_date: Optional[datetime.date]`) and any Svelte templates that render it without a null guard.

### Pitfall 9: `cover_metadata` null check before writing hint text
**What goes wrong:** The job detail page renders `cover_metadata` values as hint text. If `cover_metadata` is null (parse not yet run, or extraction returned `{}`), accessing keys raises a JS error.
**Why it happens:** JSONB column returns `None` in Python / `null` in JSON when not set.
**How to avoid:** Null-guard `cover_metadata` in the SvelteKit load function before passing to the component. The component should only render hint text when `cover_metadata?.[field]` is non-null and differs from the current field value.

---

## Code Examples

### Pattern 1: Alembic migration 0011 (hand-written, follow migration 0010 as template)

```python
# Source: verified from alembic/versions/0010_add_is_justice.py [VERIFIED: codebase]

revision: str = "0011"
down_revision: Union[str, None] = "0010"

def upgrade() -> None:
    # Add source_docket — nullable, no server default
    op.add_column(
        "arguments",
        sa.Column("source_docket", sa.String(50), nullable=True),
    )
    # Add cover_metadata JSONB — nullable
    op.add_column(
        "arguments",
        sa.Column("cover_metadata", postgresql.JSONB(), nullable=True),
    )
    # Make argued_date nullable (was NOT NULL)
    op.alter_column("arguments", "argued_date", nullable=True)
    # UNIQUE constraint on (source_docket, question_number)
    # NULL semantics: multiple NULLs do NOT violate this constraint (D-01)
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

Note: `from sqlalchemy.dialects import postgresql` required for JSONB in migrations.

### Pattern 2: Ingest — source_docket population and nullable argued_date

```python
# Source: verified from pipeline/commands/ingest.py lines 253–266 [VERIFIED: codebase]
# CHANGED behavior for job-driven path:

# Job-driven path after D-03/D-08:
primary_docket = getattr(args, "primary_docket", None) or None
case_name = getattr(args, "case_name", None) or None
argued_date_str = getattr(args, "argued_date", None) or None

# Step 5b: Argument record — new columns
argument = Argument(
    argued_date=date.fromisoformat(argued_date_str) if argued_date_str else None,  # D-08: nullable
    question_number=args.question,
    source_docket=primary_docket,  # D-01: NULL when not provided
)
```

IntegrityError catch pattern (new, follows existing exception wrapping in `run_ingest`):
```python
from sqlalchemy.exc import IntegrityError

try:
    # ... argument create + flush ...
except IntegrityError:
    raise ValueError(
        f"Duplicate argument: docket {primary_docket} Q{args.question} already exists."
    )
```

### Pattern 3: Parse — cover_metadata write (extends existing Phase 16 block)

```python
# Source: verified from pipeline/commands/parse.py lines 313–340 [VERIFIED: codebase]
# New block inserted after existing argued_date and case_name writes:

# Block C: write raw cover_metadata unconditionally (D-07, D-09)
import json
await session.execute(
    update(Argument)
    .where(Argument.id == source_run.argument_id)
    .values(cover_metadata=cover_meta if cover_meta else None)
    .execution_options(synchronize_session=False)
)

# Block D: auto-populate source_docket from extraction if currently NULL (D-09)
if cover_meta.get("primary_docket") is not None:
    await session.execute(
        update(Argument)
        .where(
            Argument.id == source_run.argument_id,
            Argument.source_docket.is_(None),   # only if null
        )
        .values(source_docket=cover_meta["primary_docket"])
        .execution_options(synchronize_session=False)
    )
```

### Pattern 4: FastAPI check-duplicate endpoint

```python
# Source: verified from existing admin.py patterns [VERIFIED: codebase]
# Follows existing @router.get pattern with X-Admin-Token auth inherited at router level

@router.get("/arguments/check-duplicate")
async def check_duplicate_argument(
    docket: str,
    question: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if an argument with (source_docket, question_number) already exists.
    Called by JS preflight on the pipeline start form (D-04).
    Returns {"exists": bool, "argument_id": int | null}.
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

**Routing note:** This endpoint path is `/api/admin/arguments/check-duplicate`. FastAPI routes in `admin.py` are registered with the router prefix `/api/admin`. Ensure this GET route is placed BEFORE any parameterized `arguments/{argument_id}` routes to avoid path conflicts. Currently `admin.py` has argument routes — verify registration order.

### Pattern 5: SvelteKit JS preflight pattern (Svelte 5 Runes)

```typescript
// Source: verified from +page.svelte existing submit handler pattern [VERIFIED: codebase]
// onsubmit intercept before use:enhance (or native submit)

let duplicateWarning = $state<{ argumentId: number; docket: string; question: number } | null>(null);
let prefligthChecked = $state(false);

async function handleSubmit(e: SubmitEvent) {
    const docket = (document.getElementById('primary_docket') as HTMLInputElement)?.value.trim();
    const question = parseInt((document.getElementById('question_number') as HTMLSelectElement)?.value ?? '1');

    if (!docket || prefligthChecked) {
        // No docket — no preflight. Or already confirmed after warning.
        return; // let form proceed
    }

    e.preventDefault(); // block native submit

    const res = await fetch(
        `/api/admin/arguments/check-duplicate?docket=${encodeURIComponent(docket)}&question=${question}`,
        { headers: { 'X-Admin-Token': adminToken } }  // NOTE: admin token is NOT a public var
    );
    // ...
}
```

**Important:** `ADMIN_TOKEN` is a private env var (`$env/static/private`). The preflight fetch must go through a SvelteKit server-side proxy or a dedicated +server.ts endpoint — NOT a direct client-side fetch with the token embedded. The existing pattern for proxying admin calls is the `+page.server.ts` `load` function and form actions. For the preflight specifically, a `+server.ts` file at `/admin/pipeline/check-duplicate` (or similar) is the cleanest approach — it reads `ADMIN_TOKEN` server-side and proxies the FastAPI call.

### Pattern 6: SvelteKit saveMetadata form action

```typescript
// Source: verified from [job_id]/+page.server.ts existing approve action pattern [VERIFIED: codebase]
saveMetadata: async ({ request, params }) => {
    const data = await request.formData();
    const case_name = (data.get('case_name') as string)?.trim() || null;
    const source_docket = (data.get('source_docket') as string)?.trim() || null;
    const argued_date = (data.get('argued_date') as string)?.trim() || null;

    // Must fetch argument_id from job
    // Then PATCH /api/admin/arguments/{argument_id}/metadata
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/metadata`, {
            method: 'PATCH',
            headers: {
                'X-Admin-Token': ADMIN_TOKEN,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ case_name, source_docket, argued_date }),
        });
    } catch {
        return fail(502, { metadataError: 'Could not save metadata. Please try again.' });
    }
    if (!res.ok) {
        return fail(422, { metadataError: 'Could not save metadata. Please try again.' });
    }
    return { metadataSaved: true };
},
```

### Pattern 7: Cover extractor docket regex (Alderson format)

```python
# Source: CONTEXT.md D-12 + verified from cover_extractor.py patterns [VERIFIED: codebase]
# Alderson format: "No. 14-556" or "No. 14-556, 14-562"
# Heritage format may differ — needs real sample verification

DOCKET_RE = re.compile(
    r'No\.\s+(\d{2}-\d+)',  # "No. 14-556"
    re.IGNORECASE,
)
```

The extractor returns `{}` on any exception (D-05/D-10). The new `primary_docket` key should follow the same pattern:
```python
result: dict = {}
# ... existing argued_date and case_name extraction ...
if "primary_docket" not in result:
    m = DOCKET_RE.search(raw)
    if m:
        result["primary_docket"] = m.group(1)
```

---

## Migration 0011 — Detailed Schema Changes

| Column | Table | Change | Type | Nullable | Default |
|--------|-------|--------|------|----------|---------|
| `source_docket` | `arguments` | ADD | `VARCHAR(50)` | YES | none |
| `cover_metadata` | `arguments` | ADD | `JSONB` | YES | none |
| `argued_date` | `arguments` | ALTER | `DATE` | YES (was NO) | none |
| `uq_arguments_source_docket_question` | `arguments` | ADD UNIQUE | — | — | `(source_docket, question_number)` |

**Model changes in `api/models/models.py`:**
- `Argument.argued_date`: change to `Column(Date, nullable=True)` [VERIFIED: codebase — currently `nullable=False`]
- `Argument.source_docket`: add `Column(String(50), nullable=True)`
- `Argument.cover_metadata`: add `Column(JSONB, nullable=True)` — import `JSONB` from `sqlalchemy.dialects.postgresql` (already imported elsewhere; check models.py imports)
- `Argument.__table_args__`: add `UniqueConstraint("source_docket", "question_number", name="uq_arguments_source_docket_question")`

**JSONB import verification:** `models.py` already imports `JSONB` from `sqlalchemy.dialects.postgresql` (line 17). [VERIFIED: codebase]

---

## FastAPI Endpoint Inventory (new endpoints)

### GET /api/admin/arguments/check-duplicate
- Auth: `X-Admin-Token` (inherited from router dependency)
- Query params: `docket: str`, `question: int`
- Response: `{"exists": bool, "argument_id": int | null}`
- Service: query `Argument.source_docket == docket AND Argument.question_number == question`
- Returns 200 always (no 404) — absence of a match is a valid response

### PATCH /api/admin/arguments/{argument_id}/metadata
- Auth: `X-Admin-Token`
- Body: `MetadataUpdate` schema `{case_name: str | null, source_docket: str | null, argued_date: str | null}`
- Response: updated `ArgumentDetail` (or a simpler `{success: true}`)
- Service: `update_argument_metadata(db, argument_id, body)` in `admin_arguments.py`
- Logic: UPDATE `Argument.argued_date`, `Argument.source_docket`; UPDATE lead `Case.case_name`
- Must handle: `argued_date` as ISO string → `date.fromisoformat()` (same as `update_argument`)
- Security: same mass-assignment guards as existing `update_argument` — only these three fields writable

**New schema in `api/schemas/admin_arguments.py`:**
```python
class MetadataUpdate(BaseModel):
    """PATCH body for argument metadata from job detail page (D-15).
    Mass-assignment guard: only case_name, source_docket, argued_date writable."""
    case_name: Optional[str] = None
    source_docket: Optional[str] = None
    argued_date: Optional[str] = None  # ISO date string "YYYY-MM-DD"
```

---

## Job Detail Page — Load Changes

The `+page.server.ts` load function must be extended to:
1. Fetch `Argument.cover_metadata` from the argument endpoint (or embed in a new response field)
2. Fetch `Argument.source_docket` — this is the docket field on the Argument row, distinct from the lead `Case.docket_number`

The existing `ArgumentPreview` interface and `get_argument_detail` response do not currently expose `cover_metadata` or `source_docket`. Options:
- **Option A (recommended):** Add `cover_metadata` and `source_docket` to the `ArgumentDetail` schema response from `GET /api/admin/arguments/{id}`. This is the cleanest approach — one endpoint already called in the load function provides all needed data.
- **Option B:** Add a separate endpoint `/api/admin/arguments/{id}/cover-metadata`. Unnecessary complexity.

**Option A chosen per CONTEXT.md spirit:** Add `cover_metadata: dict | null` and `source_docket: str | null` to `ArgumentDetail` schema and `get_argument_detail` service return dict.

---

## Preflight Admin Token Problem — Analysis

The JS preflight (D-04) calls `GET /api/admin/arguments/check-duplicate` from the browser. The FastAPI admin router requires `X-Admin-Token`. This token is a private server-side env var — it MUST NOT be sent to the browser.

**Solution:** Add a SvelteKit `+server.ts` at a path like `/admin/pipeline/check-duplicate/+server.ts` that:
- Accepts `GET ?docket=...&question=...`
- Reads `ADMIN_TOKEN` from `$env/static/private`
- Proxies the request to FastAPI
- Returns the FastAPI response JSON

The browser's `fetch()` calls the SvelteKit endpoint (same-origin, no token exposure). SvelteKit proxies to FastAPI server-side.

This follows the existing pattern: `[job_id]/+page.server.ts` proxies all FastAPI calls server-side. The merge-preview `+server.ts` in `/admin/people/` is the existing precedent for a GET proxy endpoint (STATE.md: "merge-preview +server.ts proxies ADMIN_TOKEN server-side so client never sees the secret").

[VERIFIED: codebase — `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` already follows this proxy pattern for all FastAPI calls]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| `_derive_metadata_from_key` creates synthetic `job-{N}` placeholders and `date.today()` as `argued_date` | Leave `source_docket = NULL`, `argued_date = NULL` for job-driven ingest without explicit docket | Phase 19 (this phase) | Empty field = "not extracted yet" rather than misleading synthetic data |
| Cover extractor returns only `argued_date` and `case_name` | Cover extractor also returns `primary_docket` | Phase 19 (this phase) | Enables auto-population of `source_docket` from extraction |
| Parse overwrites `argued_date` and `case_name` unconditionally (Phase 16 D-04) | Parse writes `cover_metadata` unconditionally; auto-populates null fields only (D-09) | Phase 19 (this phase) | Prevents overwriting operator-entered values |

**Important deviation from Phase 16:** Phase 16's parse block (lines 314–340) currently writes `argued_date` and `case_name` **unconditionally** (the comment says "Always overwrite — D-04"). Phase 19 D-09 changes this to **only if null** for `argued_date` and `source_docket`. The `cover_metadata` JSONB write is always unconditional. The planner must note this behavioral change clearly.

---

## Integration Points Summary

| Signal | Source | Destination | Notes |
|--------|--------|-------------|-------|
| `--primary-docket` CLI arg | SvelteKit form action → subprocess | `ingest.py` `args.primary_docket` | New arg added to `spawn_pipeline_step` call |
| `--question` CLI arg | SvelteKit form action → subprocess | `ingest.py` `args.question` | Already exists; now also forwarded from form |
| `Argument.source_docket` | Ingest (from `args.primary_docket`) | DB | New column; NULL when docket not provided |
| `Argument.cover_metadata` | Parse (from `cover_extractor`) | DB | New JSONB column; unconditionally written |
| `Argument.argued_date` | Parse (conditional, only if NULL) | DB | Now nullable; not overwritten if set |
| `ArgumentDetail.cover_metadata` | FastAPI `get_argument_detail` | SvelteKit load | New field in response |
| `ArgumentDetail.source_docket` | FastAPI `get_argument_detail` | SvelteKit load | New field in response |
| `check-duplicate` | SvelteKit proxy `+server.ts` | FastAPI | GET, read-only, no state mutation |
| `saveMetadata` form action | SvelteKit `+page.server.ts` | FastAPI `PATCH /arguments/{id}/metadata` | New action + new endpoint |

---

## Environment Availability

Step 2.6 SKIPPED — no new external tools, CLIs, or services required. All changes use the existing Python/FastAPI/SvelteKit/PostgreSQL environment that is already operational.

---

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json`. Validation Architecture section skipped per config.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | `X-Admin-Token` auth on all new endpoints; inherited at router level |
| V5 Input Validation | yes | `docket` query param: plain string (no HTML injection concern); `argued_date`: `date.fromisoformat()` validation; `source_docket` stored as VARCHAR, not executed |
| V6 Cryptography | no | no new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mass assignment via MetadataUpdate | Tampering | `MetadataUpdate` schema explicitly restricts to `{case_name, source_docket, argued_date}` — same pattern as `ArgumentUpdate` |
| IDOR on metadata PATCH | Elevation of Privilege | Service must verify `argument_id` exists before update; return 404 if not found |
| Admin token exposure via preflight | Information Disclosure | Token NEVER sent to browser; SvelteKit `+server.ts` proxy keeps it server-side |
| SQL injection via `docket` query param | Tampering | SQLAlchemy parameterized query; docket is a bind parameter, never interpolated |
| Duplicate warning bypass | Tampering | DB UNIQUE constraint is the authoritative backstop regardless of whether preflight ran |
| Path traversal via `source_docket` | Tampering | `source_docket` is only stored in DB and used in queries — never used as a file path |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Heritage transcript docket format may differ from Alderson "No. 14-556" | Cover Extractor Extension / D-12 | Docket regex fails to extract from Heritage transcripts; `primary_docket` returns null from extraction, operator must type manually — acceptable fallback per D-10 |
| A2 | `op.alter_column` for `argued_date` to nullable works cleanly on existing rows | Migration 0011 | Existing rows all have argued_date set (not null), so `nullable=True` alter succeeds without any backfill needed — existing rows retain their values |

**If A1 is wrong:** The extractor silently returns no `primary_docket` for Heritage transcripts, which is the documented D-10 safe fallback. Operator enters the docket manually in the metadata card. No data loss, no error.

---

## Open Questions (RESOLVED)

1. **Route ordering for `GET /api/admin/arguments/check-duplicate`**
   - What we know: FastAPI registers routes in order; a `/arguments/{argument_id}` parameterized route already exists in `admin.py`.
   - What's unclear: Whether `/arguments/check-duplicate` will be shadowed by `/arguments/{argument_id}`.
   - Recommendation: Register `GET /arguments/check-duplicate` **before** any `GET /arguments/{argument_id}` route in `admin.py`. FastAPI resolves literal path segments before parameters. Verify registration order in `admin.py` before writing the endpoint.
   - **RESOLVED:** Plan 19-03 Task 3 addresses this explicitly with a CRITICAL note and a verification command to confirm route ordering.

2. **Ingest CLI arg for `--question` forwarding**
   - What we know: `spawn_pipeline_step("ingest", job.id, ["--url", pdf_url])` in `admin.py` does NOT currently pass `--question`.
   - What's unclear: Whether `--question` is already an accepted CLI arg in `ingest.py` (it appears in `args.question` usage in the body but the argparse registration isn't shown in the read portion).
   - Recommendation: Planner should verify `pipeline/main.py` argparse config includes `--question` as an arg that is already wired, then ensure `spawn_pipeline_step` forwards both `--primary-docket` and `--question` from the form submission.
   - **RESOLVED:** Plan 19-02 Task 2 reads `pipeline/main.py` first and handles both `--primary-docket` and `--question` forwarding.

---

## Sources

### Primary (HIGH confidence)
- `api/models/models.py` — ORM model for `Argument`, `AdminJob`, `Case`, existing JSONB usage confirmed
- `pipeline/commands/ingest.py` — full ingest logic, `_derive_metadata_from_key`, job-driven path, CLI arg handling
- `pipeline/commands/parse.py` — existing Phase 16 cover metadata write blocks (lines 313–340), session management
- `pipeline/parser/cover_extractor.py` — existing extraction logic, fail-safe pattern, return schema
- `pipeline/tests/test_cover_extractor.py` — existing test patterns for extending docket tests
- `alembic/versions/0010_add_is_justice.py` — migration template for 0011
- `api/routers/admin.py` — all admin endpoints, auth pattern, spawn_pipeline_step usage
- `api/services/admin_arguments.py` — update_argument pattern, mass-assignment guards, session patterns
- `api/schemas/admin_arguments.py` — existing schema patterns for new MetadataUpdate schema
- `api/schemas/admin_jobs.py` — AdminJobResponse, existing schema patterns
- `app/src/routes/admin/pipeline/+page.svelte` — start form structure for docket/Q# field additions
- `app/src/routes/admin/pipeline/+page.server.ts` — form action for forwarding new fields to FastAPI
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — job detail page for metadata card placement
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — load function and existing actions for saveMetadata pattern
- `.planning/phases/19-pipeline-reliability/19-CONTEXT.md` — all locked decisions
- `.planning/phases/19-pipeline-reliability/19-UI-SPEC.md` — UI-SPEC approved

### Secondary (MEDIUM confidence)
- PostgreSQL documentation on NULL semantics in unique indexes — [ASSUMED] but well-established SQL standard behavior; consistent with CONTEXT.md D-01 acknowledgment

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all existing
- Architecture: HIGH — verified against codebase
- Pitfalls: HIGH — derived directly from reading actual code
- Migration pattern: HIGH — verified against migration 0010 template

**Research date:** 2026-06-30
**Valid until:** 2026-07-30 (stable codebase, no fast-moving dependencies)
