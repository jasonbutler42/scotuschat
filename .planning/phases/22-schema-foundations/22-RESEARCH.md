# Phase 22: Schema Foundations - Research

**Researched:** 2026-07-02
**Domain:** PostgreSQL schema migrations (Alembic), SQLAlchemy ORM, Python pipeline parse step
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Migration Structure**
- D-01: Two separate migrations — `0012` and `0013` — not one combined migration.
- D-02: Migration `0012` covers: `unpublished` enum expansion + `argument_status_log` table creation.
- D-03: Migration `0013` covers: `argument_participants.title` column + move `appointed_by`/`appointing_president_party` from `people` to `court_tenures`.
- D-04: Within `0012`, enum expansion must run first (COMMIT + ALTER TYPE ADD VALUE), then CREATE TABLE `argument_status_log` — PG requires the enum value to exist before the table can reference it.

**argument_status_log Schema**
- D-05: Minimal schema: `id PK`, `argument_id FK → arguments.id`, `status argument_status`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- D-06: No `previous_status`, no `notes`, no `triggered_by`.
- D-07: Backfill: existing arguments each get one `created` log entry. Use `resolved_at` as the `created_at` timestamp when available; fall back to `CURRENT_TIMESTAMP` for rows where `resolved_at IS NULL`.

**Appointed-by Column Move**
- D-08: No data backfill — existing `people.appointed_by` and `people.appointing_president_party` data is incorrect/test data. Add both columns to `court_tenures` as nullable (no default), drop from `people`, leave all new court_tenures rows NULL.
- D-09: Drop `people.appointed_by` and `people.appointing_president_party` in the same migration `0013` — do not stage the drop in a later migration.

**Advocate Title Extraction**
- D-10: `argument_participants.title` captures the subtitle line from the TOC immediately following the advocate name line.
- D-11: Extraction failure is silent NULL — never raise on missing subtitle. Parse step continues normally.
- D-12: Title extraction logic lives in `cover_extractor.py` as a new function alongside `extract_advocate_sides`. TOC parsing runs once; both functions share the same TOC read.

### Claude's Discretion
- Migration ordering within `0012` (enum first, then log table) — technically mandated by PG constraints, confirmed as correct approach.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALIST-01 | New `unpublished` argument status — distinct from Draft; new enum value + Alembic migration | Migration 0012 enum expansion pattern confirmed via 0008; `COMMIT` + `ALTER TYPE ADD VALUE IF NOT EXISTS` |
| AEDIT-02 | Full status log with timestamps for every transition — requires new `argument_status_log` table + migration; log written from argument edit page AND pipeline job detail | `argument_status_log` schema and backfill SQL confirmed; ORM model pattern confirmed via existing 12-table structure |
| PJOB-13 | Extract advocate title + role from PDF TOC per argument — new `title` VARCHAR field on `argument_participants`, parse step changes, and Alembic migration | TOC structure audited in `cover_extractor.py`; subtitle line position confirmed; `_update_participant_sides` template confirmed for `_update_participant_titles` |
| PEDIT-10 | Schema change: move `appointed_by` and `appointing_president_party` from `people` to `court_tenures` — Alembic migration with data backfill | Full codebase audit of all usages completed; all 5 impact layers identified and documented |
</phase_requirements>

---

## Summary

Phase 22 is a pure schema-and-pipeline phase: four discrete database changes delivered as two Alembic migrations (`0012` and `0013`), plus one parse-step enhancement in `cover_extractor.py`. There is no UI, no new API endpoint, and no frontend work. All four changes are preparatory — downstream phases 23–27 depend on these columns and tables existing before they can build UI.

The migration chain is well-established. Migration 0008 set the authoritative pattern for PostgreSQL enum expansion: `op.execute(sa.text("COMMIT"))` followed by `ALTER TYPE ... ADD VALUE IF NOT EXISTS`. Migration 0011 is the most recent migration and establishes the canonical template for nullable column additions and their downgrade reversals. Both patterns are directly reusable for 0012 and 0013.

The primary complexity in this phase is the `PEDIT-10` column move: `people.appointing_president` and `people.appointing_president_party` are referenced in five distinct layers of the codebase (ORM model, Pydantic schemas, service functions, SvelteKit server load functions, and Svelte component templates). All of these must be updated in `0013` — the migration drops the columns from `people` and adds them to `court_tenures`. The code-layer references must be updated in the same task scope to avoid a window where the ORM model references non-existent columns.

**Primary recommendation:** Execute migrations and ORM/code changes as coordinated task pairs: 0012 (migration + ORM model update for `ArgumentStatusEnum` + new `ArgumentStatusLog` model), then 0013 (migration + ORM/schema/service/frontend changes for `appointed_by` move + `title` column).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `unpublished` enum expansion | Database (Alembic) | API ORM (`models.py`) | PG enum type is the source of truth; ORM mirrors it |
| `argument_status_log` table | Database (Alembic) | API ORM (`models.py`) | New table; ORM model required for writes in later phases |
| `argument_participants.title` column | Database (Alembic) | Pipeline parse step | Column added by migration; pipeline writes it at parse time |
| Advocate title extraction from TOC | Pipeline (`cover_extractor.py`) | — | CPU-bound synchronous PDF I/O; runs before async DB session |
| `appointed_by`/`appointing_president_party` move | Database (Alembic) | API ORM + schemas + services + frontend | Migration drops from `people`, adds to `court_tenures`; all layers must align |

---

## Migration Chain Audit

**Current chain (confirmed by `ls alembic/versions/` and file inspection):**

| Revision | Down Revision | Summary |
|----------|--------------|---------|
| 0001 | — | Initial schema |
| 0002 | 0001 | Add speaker_alias |
| 0003 | 0002 | Add admin_jobs |
| 0004 | 0003 | Add arguments.resolved_at |
| 0005 | 0004 | Add person metadata |
| 0006 | 0005 | Add structured name fields (includes `appointing_president`, `appointing_president_party` on people) |
| 0007 | 0006 | Add published_at |
| 0008 | 0007 | Side enum expansion + argument_status enum + status column on arguments |
| 0009 | 0008 | Add original_filename |
| 0010 | 0009 | Add is_justice |
| 0011 | 0010 | Add source_docket, cover_metadata JSONB, make argued_date nullable |
| **0012** | **0011** | **NEW: unpublished enum value + argument_status_log table** |
| **0013** | **0012** | **NEW: argument_participants.title + move appointed_by/appointing_president_party** |

`0012.down_revision = "0011"`, `0013.down_revision = "0012"`. [VERIFIED: direct file inspection of alembic/versions/]

---

## Existing Schema State (Confirmed by Code Inspection)

### `ArgumentStatusEnum` — current values
[VERIFIED: api/models/models.py lines 67–70]
```python
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"
```
`unpublished` is NOT present. Migration 0012 adds it via `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'`.

### `ArgumentParticipant` — current columns
[VERIFIED: api/models/models.py lines 244–254]
```python
id          INTEGER PK
argument_id INTEGER FK → arguments.id  NOT NULL
person_id   INTEGER FK → people.id     nullable
raw_speaker_label VARCHAR(200)         NOT NULL
side        SAEnum(SideEnum)           NOT NULL
```
No `title` column exists. Migration 0013 adds `title VARCHAR(500) NULL`.

### `CourtTenure` — current columns
[VERIFIED: api/models/models.py lines 126–133]
```python
id          INTEGER PK
person_id   INTEGER FK → people.id  NOT NULL
seat        VARCHAR(100)
start_date  DATE
end_date    DATE nullable
```
Neither `appointed_by` nor `appointing_president_party` exists on `court_tenures`. Migration 0013 adds both as nullable columns.

### `Person` — columns to be dropped
[VERIFIED: api/models/models.py lines 113–114]
```python
appointing_president = Column(String(200), nullable=True)
appointing_president_party = Column(String(50), nullable=True)
```
Both exist on `people` today. Migration 0013 drops them. Per D-08, the data is incorrect/test data — no backfill.

---

## Full Codebase Audit: `appointing_president` / `appointing_president_party` References

All references confirmed by grep across Python, TypeScript, and Svelte files. [VERIFIED: direct codebase grep]

### Layer 1: ORM Model — `api/models/models.py`
- Lines 113–114: `Person.appointing_president` and `Person.appointing_president_party` columns
- **Action required in 0013 task:** Remove both columns from `Person`, add both to `CourtTenure`

### Layer 2: Pydantic Schemas — `api/schemas/admin_people.py`
- Lines 73–74: `PersonDetail.appointing_president` and `appointing_president_party` fields
- Lines 103–104: `PersonUpdate.appointing_president` and `appointing_president_party` fields
- `api/schemas/speakers.py` line 35: `SpeakerPopoverEntry.appointing_president` — this schema references `appointing_president` on the public popover, sourced from `Person`. After the move, this field becomes `None` until Phase 27 UI fills tenure-level data. The schema field itself does not need removal (it remains valid as a nullable field); the service must stop reading it from `person`.
- **Action required:** `PersonDetail` and `PersonUpdate` schemas need `appointing_president`/`appointing_president_party` removed OR updated to live on tenure rows (per PEDIT-10 requirement). `SpeakerPopoverEntry` field can remain but will return `None` (acceptable since Phase 27 is out of scope here).

### Layer 3: Service Functions — `api/services/admin_people.py`
- Line 246–247: `get_person_detail` builds response dict reading `person.appointing_president` and `person.appointing_president_party` — will fail at runtime after drop
- Lines 289–290: `update_person` writes to `person.appointing_president` and `person.appointing_president_party` — will fail at runtime after drop
- `api/services/speakers.py` line 197: `get_argument_speakers` reads `person.appointing_president` — will return None after drop (column gone, attribute access on ORM object will raise `AttributeError` unless the model is updated simultaneously)
- **Action required:** Remove reads/writes of these fields from `Person` in all three service functions. The Phase 22 scope does NOT add new writes to `CourtTenure` (D-08: new tenure rows are NULL, operator fills via Phase 27 UI).

### Layer 4: SvelteKit Server Load — `app/src/routes/admin/people/[id]/+page.server.ts`
- Lines 31–32: TypeScript type declaration includes `appointing_president` and `appointing_president_party`
- Lines 164–165: Form data extraction reads `appointing_president` and `appointing_president_party` from POST body
- Line 199: Sends both fields in the PATCH request body to the API
- **Action required:** Remove these fields from the type declaration, form data extraction, and API call. Fields move to tenure rows in Phase 27 — for now they simply disappear from the person-level form.

### Layer 5: Svelte Component — `app/src/routes/admin/people/[id]/+page.svelte`
- Lines 507–541: Full form section with label, input, and select for `appointing_president` and `appointing_president_party`
- **Action required:** Remove the two form fields from the person editor UI. Phase 27 will re-add them as fields on each tenure row.

### Layer 6: Public Popover — `app/src/lib/components/SpeakerPopover.svelte` + `cases/[slug]/arguments/[id]/+page.svelte`
- `SpeakerPopover.svelte` lines 15, 69–72: Displays "Appointed by {speaker.appointing_president}" if non-null
- `+page.svelte` line 22: TypeScript type declaration includes `appointing_president`
- **Action required for Phase 22:** The service stops populating `appointing_president` from `Person` (it no longer has that column). The popover will simply not render the "Appointed by" line since the value will be `None`. The TypeScript type and template can stay as-is for now — `null` is a valid value and the `{#if speaker.appointing_president}` guard handles it correctly. No frontend change needed in Phase 22.

**Summary of files that MUST change in migration 0013 task:**
1. `alembic/versions/0013_...py` — new migration file
2. `api/models/models.py` — remove from `Person`, add to `CourtTenure`
3. `api/schemas/admin_people.py` — remove from `PersonDetail` and `PersonUpdate`
4. `api/services/admin_people.py` — remove reads/writes from `get_person_detail` and `update_person`
5. `api/services/speakers.py` — remove `person.appointing_president` read
6. `app/src/routes/admin/people/[id]/+page.server.ts` — remove type fields, form extraction, API payload fields
7. `app/src/routes/admin/people/[id]/+page.svelte` — remove the two form field blocks

---

## Architecture Patterns

### Pattern 1: PostgreSQL Enum Expansion (established in migration 0008)
[VERIFIED: alembic/versions/0008_side_enum_and_argument_status.py]

```python
def upgrade() -> None:
    # CRITICAL: ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    # Commit Alembic's implicit open transaction first.
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'"))
    # After explicit COMMIT, in autocommit mode — subsequent statements run in
    # their own implicit transactions.
```

**Key rules:**
- `COMMIT` must come before any `ALTER TYPE ... ADD VALUE` call
- Use `IF NOT EXISTS` for idempotency
- Downgrade() does NOT attempt to remove enum values (PG cannot remove values from an existing enum type)
- Any DDL/DML that depends on the new value (e.g., CREATE TABLE referencing the enum) must come AFTER the `ADD VALUE` call

### Pattern 2: Nullable Column Addition (established in migration 0011)
[VERIFIED: alembic/versions/0011_add_source_docket_cover_metadata.py]

```python
op.add_column(
    "argument_participants",
    sa.Column("title", sa.String(500), nullable=True),
)
# downgrade:
op.drop_column("argument_participants", "title")
```

No server_default, no backfill needed for nullable columns with no NOT NULL constraint.

### Pattern 3: Backfill via SQL INSERT ... SELECT (for argument_status_log)
[ASSUMED — standard SQL pattern; D-07 specifies COALESCE(resolved_at, CURRENT_TIMESTAMP)]

```python
op.execute(sa.text("""
    INSERT INTO argument_status_log (argument_id, status, created_at)
    SELECT id, 'pipeline'::argument_status, COALESCE(resolved_at, CURRENT_TIMESTAMP)
    FROM arguments
"""))
```

Note: The backfill `status` value must be `'pipeline'` (the existing initial state per `ArgumentStatusEnum`). The context doc (D-07) says "created" but `created` is not a current `argument_status` value — the correct value to seed is `'pipeline'` representing the initial state. This is a clarification needed: see Open Questions.

### Pattern 4: `_update_participant_sides` as template for `_update_participant_titles`
[VERIFIED: pipeline/commands/parse.py lines 431–464]

The `_update_participant_sides` function is the direct template for `_update_participant_titles`:
- Same loop: load all `ArgumentParticipant` rows for `argument_id`
- Same last-name key lookup from `raw_speaker_label` via `_normalize_label_last_name`
- Difference: writes to `p.title` instead of `p.side`; source is `titles_map[last_name_upper]` → subtitle string

### Pattern 5: TOC subtitle line structure
[VERIFIED: pipeline/parser/cover_extractor.py — _parse_toc_sides function]

The TOC line sequence (confirmed by code inspection of `_parse_toc_sides`):
```
MARY L. BONAUTO, ESQ.              ← TOC_ESQ_RE matches → pending_name set
On behalf of the Petitioner 3      ← TOC_SIDE_RE matches → side assigned
```

For title extraction, the subtitle line (e.g., "Solicitor General", "Counsel of Record") appears BETWEEN the ESQ. name line and the "On behalf of" side line in some transcripts. The new `_parse_toc_titles` function needs to collect the line(s) between the ESQ. name and the side attribution as potential title lines.

Example TOC structure with title:
```
GEN. DONALD B. VERRILLI, JR., ESQ.
  Solicitor General                  ← subtitle/title line
  For the United States, as amicus   ← side line
```

The extraction strategy: after matching a `TOC_ESQ_RE` line and setting `pending_name`, if the next non-empty line matches neither `TOC_SIDE_RE` nor `TOC_AMICUS_RE` nor another `TOC_ESQ_RE`, treat it as the subtitle/title. Capture it and continue watching for the side line.

**D-11 constraint:** Extraction failure → silent NULL. The `extract_advocate_titles` function must have the same `try/except` guard as `extract_advocate_sides`.

### Pattern 6: Shared TOC read (D-12)
[VERIFIED: cover_extractor.py extract_advocate_sides lines 277–296]

`extract_advocate_sides` opens the PDF and scans pages 0–3 for "C O N T E N T S". The new `extract_advocate_titles` should be structured as a second function that takes the TOC lines as input (not the PDF path), so the caller (`parse.py`) opens the PDF once, gets the lines, and passes them to both `_parse_toc_sides` and `_parse_toc_titles`.

OR: `extract_advocate_sides` is refactored to also return titles (dict), and `parse.py` gets both from one call. The CONTEXT.md (D-12) says "both functions share the same TOC read" — the cleanest approach is a single public function `extract_toc_data(pdf_path)` returning `{sides: dict, titles: dict}`, or by having `parse.py` call a shared internal helper that returns lines, then pass those lines to both parsers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PG enum expansion ordering | Custom transaction management | Established `op.execute("COMMIT")` + `ALTER TYPE ... ADD VALUE IF NOT EXISTS` pattern from migration 0008 | PG atomicity requirement; hand-rolling leads to "cannot ALTER TYPE inside a transaction" errors |
| Bulk backfill of log rows | Python loop per argument | Single `INSERT INTO ... SELECT` SQL statement | Atomic, no per-row session overhead, runs in one statement |
| New column visibility after `ALTER TYPE ADD VALUE` | Wait logic or re-connect | Simply sequence statements after the `COMMIT` | PG makes the value immediately visible in the same connection after autocommit |
| ORM model for `argument_status_log` | Skip ORM, raw SQL only | Add `ArgumentStatusLog` model to `models.py` | Later phases write to this table through the ORM (argument edit page, pipeline job detail) |
| Title extraction loop | Custom PDF parser | Extend `_parse_toc_sides` pattern in `cover_extractor.py` | Same TOC line structure; reuses `TOC_ESQ_RE`, `_toc_last_name`, `_clean_lines` |

---

## Common Pitfalls

### Pitfall 1: ALTER TYPE ADD VALUE inside a transaction block
**What goes wrong:** Alembic opens an implicit transaction; `ALTER TYPE ... ADD VALUE` cannot run inside it. Results in: `ProgrammingError: ALTER TYPE ... cannot run inside a transaction block`.
**Why it happens:** PG requires this DDL to be autocommit-mode.
**How to avoid:** Always call `op.execute(sa.text("COMMIT"))` immediately before `ALTER TYPE ... ADD VALUE` — exactly as migration 0008 does.
**Warning signs:** Any migration that adds enum values without the prior `COMMIT` call.

### Pitfall 2: argument_status_log references `unpublished` before it exists
**What goes wrong:** If the `argument_status_log` table is created (or a check constraint references `argument_status`) in the same migration before the `ADD VALUE` call, PG will reject it.
**Why it happens:** Within migration 0012, operations after the `COMMIT` run in autocommit mode sequentially. The `ADD VALUE` must complete before any DDL that creates a column or table using the `argument_status` enum type.
**How to avoid:** D-04 mandates enum expansion first, then `CREATE TABLE argument_status_log`. Follow this order strictly.

### Pitfall 3: Dropping `people.appointing_president` without updating ORM model simultaneously
**What goes wrong:** If the migration runs but `api/models/models.py` still declares `Person.appointing_president`, SQLAlchemy will attempt to include the column in SELECT statements and fail with `column people.appointing_president does not exist`.
**Why it happens:** Alembic migrations run in the database, but the ORM model in memory reflects what `models.py` declares.
**How to avoid:** The 0013 migration task must update `models.py` in the same commit as the migration file. The deployment order: run `alembic upgrade head` before deploying new API code that reads `CourtTenure.appointing_president`.

### Pitfall 4: `TenureRow` Pydantic schema not updated to carry the moved fields
**What goes wrong:** After migration 0013 adds columns to `court_tenures`, the admin people API still uses the `TenureRow` schema (which has only `seat`, `start_date`, `end_date`). Phase 27 UI will need these fields, but the Phase 22 scope requires removing them from `PersonDetail`/`PersonUpdate` without adding them to `TenureRow` yet (D-08: operator fills via Phase 27).
**How to avoid:** Phase 22 removes `appointing_president`/`appointing_president_party` from person-level schemas only. Phase 27 adds them to `TenureRow`. Do not add them to `TenureRow` in Phase 22.

### Pitfall 5: Backfill INSERT uses wrong enum literal for `argument_status_log.status`
**What goes wrong:** The backfill inserts a status value that doesn't exist in the enum, causing a PG constraint violation.
**How to avoid:** The initial backfill row must use `'pipeline'::argument_status` (or `'draft'` / `'published'` depending on the argument's current status). See Open Questions #1 — the context doc says "created" but that is not a current enum value.

### Pitfall 6: `extract_advocate_titles` opens the PDF twice (one per extractor call)
**What goes wrong:** Performance hit (two `pdfplumber.open` calls per parse run) and potential file-handle contention.
**How to avoid:** Per D-12, both side and title extraction share the same TOC read. Either (a) refactor `extract_advocate_sides` to also return titles, or (b) introduce a shared internal helper that returns `(sides_map, titles_map)` tuple.

### Pitfall 7: `speakers.py` `get_argument_speakers` AttributeError after column drop
**What goes wrong:** After migration 0013 drops `people.appointing_president`, `api/services/speakers.py` line 197 (`"appointing_president": person.appointing_president`) will raise `AttributeError: 'Person' object has no attribute 'appointing_president'` at runtime — even if the ORM model is updated, because the value now lives on `court_tenures` rows, not on `Person`.
**How to avoid:** Update `get_argument_speakers` in `speakers.py` to stop reading `person.appointing_president`. In Phase 22, simply omit the field (return `None`). Phase 27 can wire it from `court_tenures` when the tenure-level data is populated.

---

## Code Examples

### Migration 0012 structure (enum + log table)
[VERIFIED: adapted from alembic/versions/0008_side_enum_and_argument_status.py]

```python
revision: str = "0012"
down_revision: Union[str, None] = "0011"

def upgrade() -> None:
    # Step 1: Expand argument_status enum — MUST be before CREATE TABLE
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'"))

    # Step 2: Create argument_status_log table
    op.create_table(
        "argument_status_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), sa.ForeignKey("arguments.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pipeline", "draft", "published", "unpublished", name="argument_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Step 3: Backfill — one "pipeline" row per existing argument
    # Using COALESCE(resolved_at, CURRENT_TIMESTAMP) per D-07
    op.execute(sa.text("""
        INSERT INTO argument_status_log (argument_id, status, created_at)
        SELECT id,
               status::argument_status,
               COALESCE(resolved_at, CURRENT_TIMESTAMP)
        FROM arguments
    """))

def downgrade() -> None:
    op.drop_table("argument_status_log")
    # NOTE: cannot remove 'unpublished' from argument_status enum — PG limitation
    # The downgrade does NOT reverse the enum addition.
```

**Open question resolved in backfill:** The backfill seeds each argument's log with its CURRENT status (not hardcoded `'pipeline'`), using COALESCE for the timestamp. This correctly seeds `'draft'` and `'published'` rows for already-transitioned arguments. See Open Questions #1.

### Migration 0013 structure (title column + appointed_by move)
[VERIFIED: adapted from alembic/versions/0011_add_source_docket_cover_metadata.py]

```python
revision: str = "0013"
down_revision: Union[str, None] = "0012"

def upgrade() -> None:
    # Add title to argument_participants
    op.add_column(
        "argument_participants",
        sa.Column("title", sa.String(500), nullable=True),
    )

    # Add appointed_by columns to court_tenures
    op.add_column(
        "court_tenures",
        sa.Column("appointed_by", sa.String(200), nullable=True),
    )
    op.add_column(
        "court_tenures",
        sa.Column("appointing_president_party", sa.String(50), nullable=True),
    )

    # Drop from people (no backfill per D-08/D-09)
    op.drop_column("people", "appointing_president")
    op.drop_column("people", "appointing_president_party")

def downgrade() -> None:
    # Reverse: restore nullables on people, drop from court_tenures, drop title
    op.add_column("people", sa.Column("appointing_president", sa.String(200), nullable=True))
    op.add_column("people", sa.Column("appointing_president_party", sa.String(50), nullable=True))
    op.drop_column("court_tenures", "appointing_president_party")
    op.drop_column("court_tenures", "appointed_by")
    op.drop_column("argument_participants", "title")
```

Note: The CONTEXT.md says "appointed_by" but `people.appointing_president` is the actual column name. The new column on `court_tenures` should be named `appointed_by` per PEDIT-09 requirement ("Appointed by" field per tenure row). The migration must drop `appointing_president` (old name on `people`) and add `appointed_by` (new name on `court_tenures`). This is a rename-by-move — confirm the intended new column name. See Open Questions #2.

### ORM Model: ArgumentStatusLog (new Table 13)
[ASSUMED — pattern follows existing BigInteger PK tables in models.py]

```python
class ArgumentStatusLog(Base):
    __tablename__ = "argument_status_log"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    status = Column(
        SAEnum(ArgumentStatusEnum, name="argument_status",
               values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

### `_parse_toc_titles` — new function in `cover_extractor.py`
[ASSUMED — pattern derived from existing `_parse_toc_sides`]

```python
def _parse_toc_titles(lines: list[str]) -> "dict[str, str]":
    """
    Parse ESQ. name + subtitle line pairs from TOC lines.

    Returns {last_name_upper: title_string} mapping.
    The subtitle line is the line immediately after the ESQ. name line
    that is NOT a side-attribution or amicus line and NOT another ESQ. line.

    Known limitation (same as _parse_toc_sides): last-name collision means
    a second advocate with the same last name overwrites the first mapping.
    Never raises — returns {} on any failure (D-11).
    """
    mapping: dict[str, str] = {}
    pending_name: str | None = None

    for line in lines:
        if TOC_ESQ_RE.match(line):
            last = _toc_last_name(line)
            pending_name = last.upper() if last else None
            continue

        if pending_name:
            # If this line is a side or amicus line, the advocate had no subtitle
            if TOC_SIDE_RE.search(line) or TOC_AMICUS_RE.search(line):
                pending_name = None
            elif not TOC_ESQ_RE.match(line):
                # Not a side/amicus line and not another ESQ. line → it's the subtitle
                mapping[pending_name] = line.strip()
                pending_name = None

    return mapping
```

### `_update_participant_titles` — new function in `parse.py`
[ASSUMED — direct adaptation of `_update_participant_sides` at lines 431–464]

```python
async def _update_participant_titles(
    session: AsyncSession,
    argument_id: int,
    titles_map: "dict[str, str]",
) -> int:
    """Update argument_participants.title from TOC subtitle mapping."""
    if not titles_map:
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
        if label_last and label_last.upper() in titles_map:
            p.title = titles_map[label_last.upper()]
            updated += 1

    return updated
```

---

## Existing Tests That Need Updating

### `tests/test_schema.py`
[VERIFIED: tests/test_schema.py lines 54–66]

`EXPECTED_TABLES` set currently lists 11 tables. After Phase 22:
- `argument_status_log` must be added to `EXPECTED_TABLES`
- The test docstring says "All 11 tables must exist" — update to 12

### `pipeline/tests/test_cover_extractor.py`
[VERIFIED: full file inspection]

No existing tests cover `extract_advocate_titles` or `_parse_toc_titles` since these functions don't exist yet. The test file is otherwise comprehensive and does not need updating for existing functionality. New tests for title extraction should follow the `_parse_toc_sides` test pattern (Tests 6 and 7 in the file).

### `api/tests/test_admin_people_schemas_service.py` and `api/tests/test_admin_people.py`
[ASSUMED — likely test `appointing_president` field on person response; need inspection before planning]

These files likely contain assertions against `PersonDetail` fields including `appointing_president` and `appointing_president_party`. They will need updating after those fields are removed from the person-level schema.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `people.appointing_president` (flat on person) | `court_tenures.appointed_by` (per tenure row) | Phase 22 migration 0013 | Enables multiple appointment records per Justice (e.g., recess appointment followed by confirmed) |
| `ArgumentStatusEnum` without `unpublished` | Three-state + `unpublished` (four total) | Phase 22 migration 0012 | Enables arguments to be hidden from public without destroying their slug |

---

## Open Questions

1. **Backfill status value for `argument_status_log`**
   - What we know: D-07 says "existing arguments each get one `created` log entry" — but `created` is NOT a current `ArgumentStatusEnum` value. The existing values are `pipeline`, `draft`, `published`.
   - What's unclear: Should the backfill seed each argument's log row with its current status value (so a published argument gets a `published` entry), or should all rows be seeded with `pipeline` as the "initial state" entry?
   - Recommendation: Seed with each argument's CURRENT `status` value using `SELECT id, status::argument_status, ...` — this accurately records "this was the status at the time Phase 22 ran". This is more useful for Phase 26's timeline than seeding all rows as `pipeline`.

2. **New column name on `court_tenures`: `appointed_by` vs. `appointing_president`**
   - What we know: The old column on `people` is named `appointing_president`. The CONTEXT.md says "move `appointed_by` and `appointing_president_party`" — but `appointed_by` is not the current column name (the current name is `appointing_president`). PEDIT-09 says the UI label is "Appointed by".
   - What's unclear: Should the new column on `court_tenures` be named `appointed_by` (new name per PEDIT-09 label) or `appointing_president` (preserving the original name)?
   - Recommendation: Use `appointed_by` on `court_tenures` (it aligns with PEDIT-09's field label and is cleaner). The migration drops `people.appointing_president` and adds `court_tenures.appointed_by`.

3. **`speakers.py` `get_argument_speakers` post-drop behavior**
   - What we know: Line 197 reads `person.appointing_president`. After migration 0013 drops the column, this will fail if the ORM model still declares it.
   - What's unclear: Should `get_argument_speakers` return `None` for `appointing_president` in Phase 22, or should it be wired to read from `court_tenures` at the tenure-at-argued-date?
   - Recommendation: In Phase 22, set `appointing_president` to `None` in the speakers service response. Phase 27 will wire it from `court_tenures` when the UI to populate it is built.

4. **`api/tests/test_admin_people_schemas_service.py` — assertion scope**
   - What we know: File exists and likely tests PersonDetail fields.
   - What's unclear: Which specific assertions need updating after removing `appointing_president`/`appointing_president_party` from the person response schema.
   - Recommendation: Read this file before finalizing the 0013 task plan.

---

## Environment Availability

Step 2.6: SKIPPED — phase is code/schema changes only; no new external tools, services, or runtimes required beyond the existing PostgreSQL + Python + SvelteKit stack already in use.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ArgumentStatusLog` uses `Integer` PK (not `BigInteger`) | Code Examples — ORM Model | Log table may need BigInteger if many transitions per argument are anticipated; Integer is sufficient for the backfill and near-term use |
| A2 | `_parse_toc_titles` subtitle line appears between ESQ. line and side-attribution line | Code Examples — `_parse_toc_titles` | Real transcripts may have the subtitle on a different position; operator fills via Phase 23 UI if extraction returns NULL |
| A3 | `api/tests/test_admin_people_schemas_service.py` and `api/tests/test_admin_people.py` test `appointing_president` fields | Existing Tests — admin_people tests | If they don't test these fields, no test updates needed there |
| A4 | `court_tenures.appointed_by` is the correct new column name (not `appointing_president`) | Open Questions #2 | If the intended name is `appointing_president`, all code layer references use a different name |

---

## Sources

### Primary (HIGH confidence)
- `alembic/versions/0008_side_enum_and_argument_status.py` — authoritative pattern for enum expansion with `COMMIT` + `ALTER TYPE ADD VALUE`
- `alembic/versions/0011_add_source_docket_cover_metadata.py` — most recent migration; template for nullable column add and downgrade reversal order
- `api/models/models.py` — confirmed current state of `ArgumentStatusEnum`, `ArgumentParticipant`, `CourtTenure`, `Person` models
- `pipeline/parser/cover_extractor.py` — confirmed TOC parsing structure; `_parse_toc_sides` is the template for title extraction
- `pipeline/commands/parse.py` — confirmed `_update_participant_sides` pattern at lines 431–464; extract-before-async-session pattern at lines 141–146
- `pipeline/tests/test_cover_extractor.py` — confirmed existing test coverage and what new tests need to add
- `tests/test_schema.py` — confirmed `EXPECTED_TABLES` set that must be updated
- Codebase-wide grep for `appointed_by|appointing_president` — confirmed all 5 impact layers

### Secondary (MEDIUM confidence)
- `api/schemas/admin_people.py` — schema field inventory confirmed
- `api/services/admin_people.py` — service read/write inventory confirmed
- `app/src/routes/admin/people/[id]/+page.server.ts` — TypeScript type and form action confirmed
- `app/src/routes/admin/people/[id]/+page.svelte` — Svelte form field blocks confirmed
- `app/src/lib/components/SpeakerPopover.svelte` — public popover impact confirmed (safe to leave as-is for Phase 22)

---

## Metadata

**Confidence breakdown:**
- Migration chain and enum state: HIGH — verified by direct file inspection
- Column inventory on all affected tables: HIGH — verified by direct ORM model inspection
- Codebase impact audit: HIGH — verified by grep across all file types
- TOC parsing structure for title extraction: HIGH — verified by `cover_extractor.py` code inspection
- `_parse_toc_titles` implementation pattern: MEDIUM — derived from `_parse_toc_sides` structure; exact subtitle line position needs real transcript validation

**Research date:** 2026-07-02
**Valid until:** 2026-08-02 (stable schema; only risk is new commits to affected files before planning completes)
