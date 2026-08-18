# Phase 47: Provenance Foundation - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 15 (production + test + migration)
**Analogs found:** 15 / 15 (all in-repo; this is a rename/extend refactor, no genuinely novel code)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `alembic/versions/0026_import_run_provenance.py` (new) | migration | batch/DDL | `alembic/versions/0025_rename_participant_title_to_descriptor.py` (rename idiom) + `alembic/versions/0003_add_admin_jobs.py` (enum-create idiom) | exact (two analogs combined) |
| `api/models/models.py` — `PipelineRun`→`ImportRun`, new `ImportSource`/`ImportMethod` enums, `Utterance.pipeline_run_id`→`import_run_id`, drop `Utterance.strategy` | model | CRUD | same file — `ArgumentStatusEnum`/`SideEnum` (enum decl) + `PipelineRun` class itself (column layout) | exact |
| `pipeline/commands/import_convokit.py` (`ImportRun` stamping ~:563, idempotency key ~:490) | service/writer | event-driven (batch import) | itself (existing `PipelineRun(...)` construction) | exact |
| `pipeline/commands/ingest.py` (~:528) | service/writer | request-response (CLI step) | itself (existing `PipelineRun(...)` construction) | exact |
| `pipeline/commands/parse.py` (~:256, strategy branch ~:189-239) | service/writer | request-response (CLI step) | itself | exact |
| `pipeline/commands/resolve.py` (~:145) | service/writer | request-response (CLI step) | itself | exact |
| `api/services/arguments.py` (`PipelineRun`→`ImportRun` query refs) | service | CRUD/read | itself | exact |
| `api/services/admin_jobs.py` (`PipelineRun`→`ImportRun`; `strategy==` → `source==` checks) | service | CRUD/read | itself | exact |
| `api/services/admin_arguments.py` (cascade-delete `PipelineRun`→`ImportRun`) | service | CRUD | itself | exact |
| `api/routers/admin.py` (PDF streaming lookup) | route/controller | request-response | itself | exact |
| `api/schemas/utterance.py` (`pipeline_run_id`→`import_run_id`, drop `strategy` field) | model (Pydantic schema) | request-response | itself | exact |
| `api/services/admin_dev.py` — `TRUNCATE_SQL` table-name update | service | batch (test fixture reset) | itself (`TRUNCATE_SQL` constant, `reset_to_fixture`) | exact |
| `conftest.py` (repo root) — `_WATCHED_TABLES` tuple | config/test | batch | itself | exact |
| `pipeline/tests/conftest.py` — 2 TRUNCATE lists | config/test | batch | itself | exact |
| `pipeline/tests/test_import_run_provenance.py` (new) | test | request-response (integration) | `pipeline/tests/test_parse.py::test_run_id_strategy` | exact |
| `pipeline/tests/test_pipeline_run.py` → rename/rewrite as `test_import_run.py` | test | request-response | itself | exact |

## Pattern Assignments

### `alembic/versions/0026_import_run_provenance.py` (migration)

**Analog 1 — table/column rename idiom:** `alembic/versions/0025_rename_participant_title_to_descriptor.py` (full file, 49 lines)

```python
# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "argument_participants",
        "title",
        new_column_name="descriptor",
        existing_type=sa.String(length=500),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "argument_participants",
        "descriptor",
        new_column_name="title",
        existing_type=sa.String(length=500),
        existing_nullable=True,
    )
```
Use `down_revision = "0025"` for the new migration (current head, verified via `ls alembic/versions/`).

**Analog 2 — brand-new PG enum type creation (DO-block guarded):** `alembic/versions/0003_add_admin_jobs.py` lines 38-69

```python
conn = op.get_bind()
for type_name, ddl in [
    (
        "admin_job_status",
        "CREATE TYPE admin_job_status AS ENUM "
        "('pending', 'running', 'paused', 'completed', 'failed')",
    ),
    (
        "admin_job_step",
        "CREATE TYPE admin_job_step AS ENUM ('ingest', 'parse', 'resolve')",
    ),
]:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"),
        {"n": type_name},
    ).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))

admin_job_status = postgresql.ENUM(
    "pending", "running", "paused", "completed", "failed",
    name="admin_job_status",
    create_type=False,
)
```
Apply this pattern for two new types: `import_source` (`'operator', 'corpus', 'pdf_pipeline', 'seed'`) and `import_method` (`'manual', 'direct', 'normalized', 'rule_based', 'llm_corrective'`). RESEARCH.md's Code Examples section already has the exact DDL strings — copy verbatim.

**In-place enum rename (no new values), RESEARCH.md Code Examples:**
```python
op.execute(sa.text("ALTER TYPE pipeline_run_status RENAME TO import_run_status"))
```

**Table rename + FK column rename** (RESEARCH.md Code Examples, mirrors migration 0025's `alter_column` idiom):
```python
op.rename_table("pipeline_runs", "import_run")
op.alter_column(
    "utterances", "pipeline_run_id", new_column_name="import_run_id",
    existing_type=sa.Integer(), existing_nullable=False,
)
```

**Column drop** (`utterance.strategy`, D-05) — no existing drop-column migration was found in the 0001-0025 chain to copy verbatim; use plain `op.drop_column("utterances", "strategy")` in `upgrade()`, and re-add as `sa.Column("strategy", sa.String(100), nullable=True)` in `downgrade()` (nullable, since D-05 notes re-adding needs a re-population source — cannot restore NOT NULL data).

**New columns** (`source`, `method`, `external_id`) — use `op.add_column("import_run", sa.Column("source", <enum>, nullable=False))` etc. Given D-01's clean-rebuild framing, `DROP TABLE pipeline_runs CASCADE` + `CREATE TABLE import_run` from scratch (full column list per updated `ImportRun` model) is also an acceptable one-shot alternative to rename+alter+add — either satisfies the same end DDL state; RESEARCH.md flags both as valid, defers final shape choice to the planner.

---

### `api/models/models.py` (model — enum decls, `PipelineRun`→`ImportRun`, `Utterance`)

**Analog:** same file, existing `ArgumentStatusEnum`/`SideEnum` pattern (lines 37-51, 68+) and `PipelineRun` class (lines 387-404), `Utterance` class (lines 416-439)

**Enum declaration pattern to copy** (lines 37-51):
```python
class SideEnum(str, enum.Enum):
    ...

class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
```
Add two new enums following this exact shape:
```python
class ImportSource(str, enum.Enum):
    OPERATOR = "operator"
    CORPUS = "corpus"
    PDF_PIPELINE = "pdf_pipeline"
    SEED = "seed"

class ImportMethod(str, enum.Enum):
    MANUAL = "manual"
    DIRECT = "direct"
    NORMALIZED = "normalized"
    RULE_BASED = "rule_based"
    LLM_CORRECTIVE = "llm_corrective"
```

**Column declaration pattern to copy** (line 293-297, `ArgumentStatusEnum` usage):
```python
status = Column(
    SAEnum(ArgumentStatusEnum, name="argument_status",
           values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    default=ArgumentStatusEnum.PIPELINE,
)
```
Apply identically for `source`/`method` on the renamed `ImportRun` model (`SAEnum(ImportSource, name="import_source", values_callable=lambda e: [x.value for x in e])`, `nullable=False`, no default — every writer must declare it explicitly per D-02).

**Existing `PipelineRun` class to rename/extend** (lines 387-404, full body):
```python
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    step = Column(String(50), nullable=False)  # "ingest", "parse", "resolve"
    status = Column(
        SAEnum(PipelineRunStatus, name="pipeline_run_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)    # local path to immutable PDF
    pdf_url = Column(String(1000), nullable=True)    # original download URL
    strategy = Column(String(100), nullable=True)    # "rule_based", "llm_corrective"
    prompt_version = Column(String(50), nullable=True)  # for schema version tracking
```
Rename class to `ImportRun`, `__tablename__` to `"import_run"`, `PipelineRunStatus`→`ImportRunStatus` (enum type renamed via `ALTER TYPE`, values unchanged), drop `strategy`, add `source` (`SAEnum(ImportSource, ...)`, `nullable=False`), `method` (`SAEnum(ImportMethod, ...)`, `nullable=False`), `external_id = Column(String(50), nullable=True)`. Keep `step`, `pdf_path`, `pdf_url` as-is (already nullable — Pitfall 3, no DDL change needed for nullability).

**Existing `Utterance` class** (lines 416-439) — `pipeline_run_id` FK (line 421) → rename to `import_run_id` (FK target `"import_run.id"`); drop `strategy` column (line 429, currently `nullable=False`); update `__table_args__` unique constraint (`uq_utterance_arg_run_seq`, lines 431-437) and index name references from `pipeline_run_id` to `import_run_id`.

---

### `pipeline/commands/import_convokit.py` (writer — corpus path)

**Analog:** itself, existing `PipelineRun(...)` construction (lines 563-568) + idempotency key (line 490)

**Idempotency key pattern to preserve UNCHANGED** (line 490):
```python
select(Argument).where(Argument.oyez_transcript_id == conversation_id)
```
Per RESEARCH.md Pitfall 1: do NOT move `oyez_transcript_id` off `Argument` — dual-write only.

**Existing run construction to modify** (lines 563-568):
```python
run = PipelineRun(
    argument_id=argument.id,
    step="parse",
    status=PipelineRunStatus.COMPLETED,
    strategy=PIPELINE_RUN_STRATEGY,  # D-09
)
```
New shape (source=corpus, method=direct, dual-write external_id per D-03's locked mapping):
```python
run = ImportRun(
    argument_id=argument.id,
    step="parse",
    status=ImportRunStatus.COMPLETED,
    source=ImportSource.CORPUS,
    method=ImportMethod.DIRECT,
    external_id=conversation_id,  # dual-write; Argument.oyez_transcript_id unchanged
)
```
Remove the `PIPELINE_RUN_STRATEGY` module constant (line 116/118) and its second consumer in `api/services/admin_jobs.py`'s `strategy ==` check (per RESEARCH.md Open Question 2 recommendation — delete in the same commit).

The downstream `_import_utterances(..., strategy=run.strategy, ...)` call (line 600) and its `strategy=strategy` params inside the function (lines 1062, 1118) must be removed entirely — `Utterance.strategy` is dropped (D-05); utterances no longer receive a `strategy` kwarg.

---

### `pipeline/commands/ingest.py` (writer — PDF path, step=ingest)

**Analog:** itself, lines 527-535

```python
# ---- d. PipelineRun record ----
run = PipelineRun(
    argument_id=argument.id,
    step="ingest",
    status=PipelineRunStatus.COMPLETED,
    pdf_path=str(pdf_path),
    pdf_url=args.url,
)
session.add(run)
```
New shape (source=pdf_pipeline, method=normalized — per RESEARCH.md Pattern 2 mapping, ingest performs deterministic docket-norm/slug transforms):
```python
run = ImportRun(
    argument_id=argument.id,
    step="ingest",
    status=ImportRunStatus.COMPLETED,
    source=ImportSource.PDF_PIPELINE,
    method=ImportMethod.NORMALIZED,
    pdf_path=str(pdf_path),
    pdf_url=args.url,
)
session.add(run)
```

---

### `pipeline/commands/parse.py` (writer — PDF path, step=parse, rule_based/llm_corrective branch)

**Analog:** itself, strategy-branch logic (lines 188-239) + run construction (lines 256-263)

**Existing branch logic to preserve UNCHANGED (only the terminal enum value changes)** (lines 189-239):
```python
parse_strategy = "rule_based"
try:
    llm_response = await parse_with_llm(pages_text)
    ...
    parse_strategy = "llm_corrective"
except Exception as exc:
    ...
    parse_strategy = "rule_based"
```
Map the local `parse_strategy` string to `ImportMethod` at the run-construction site rather than rewriting the branch logic itself:
```python
parse_method = (
    ImportMethod.LLM_CORRECTIVE if parse_strategy == "llm_corrective"
    else ImportMethod.RULE_BASED
)
```

**Existing run construction to modify** (lines 256-263):
```python
run = PipelineRun(
    argument_id=source_run.argument_id,
    step="parse",
    status=PipelineRunStatus.RUNNING,
    strategy=parse_strategy,
    pdf_path=source_run.pdf_path,
)
```
New shape:
```python
run = ImportRun(
    argument_id=source_run.argument_id,
    step="parse",
    status=ImportRunStatus.RUNNING,
    source=ImportSource.PDF_PIPELINE,
    method=parse_method,
    pdf_path=source_run.pdf_path,
)
```
Downstream `Utterance(..., pipeline_run_id=run.id, ...)` (line 274) → `import_run_id=run.id`; drop the `strategy=` kwarg entirely from the `Utterance(...)` construction inside the write loop (~line 278+, not shown but present per RESEARCH.md's `run.strategy` reference at parse.py:282).

---

### `pipeline/commands/resolve.py` (writer — PDF path, step=resolve)

**Analog:** itself, lines 145-150

```python
resolve_run = PipelineRun(
    argument_id=parse_run.argument_id,
    step="resolve",
    status=PipelineRunStatus.RUNNING,
)
```
New shape (source=pdf_pipeline, method=normalized — deterministic label-normalization + alias lookup, no LLM):
```python
resolve_run = ImportRun(
    argument_id=parse_run.argument_id,
    step="resolve",
    status=ImportRunStatus.RUNNING,
    source=ImportSource.PDF_PIPELINE,
    method=ImportMethod.NORMALIZED,
)
```
Also update the `parse_run` lookup at lines 129-130 (`await session.get(PipelineRun, args.run_id)` → `await session.get(ImportRun, args.run_id)`) and the error-message string at line 137 (`f"pipeline_run {args.run_id} has step=..."` — cosmetic string, update to `import_run` for consistency but not load-bearing).

---

## Shared Patterns

### Native PG Enum column declaration (applies to `import_run.source`, `import_run.method`, and the renamed `import_run.status`)
**Source:** `api/models/models.py` — `SAEnum(EnumClass, name="...", values_callable=lambda e: [x.value for x in e])`, used identically for `SideEnum`, `PipelineRunStatus`, `AdminJobStatus`, `AdminJobStep`, `ArgumentStatusEnum`.
**Apply to:** every new/renamed enum column in `ImportRun`.

### Brand-new PG enum type creation in a migration (DO-block guarded `CREATE TYPE`)
**Source:** `alembic/versions/0003_add_admin_jobs.py` lines 38-69 (`conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = :n"))` existence check before `CREATE TYPE`).
**Apply to:** `import_source`, `import_method` type creation in migration 0026. Do NOT use the `ALTER TYPE ... ADD VALUE` outside-transaction idiom (migration 0008) — that's only for expanding an *existing* type, not creating a new one (RESEARCH.md Anti-Patterns).

### Simple in-place column/table rename via `op.alter_column`/`op.rename_table`
**Source:** `alembic/versions/0025_rename_participant_title_to_descriptor.py` (full file — the entire migration is 3 statements: `alter_column` upgrade, mirrored `alter_column` downgrade).
**Apply to:** `pipeline_runs`→`import_run` table rename, `pipeline_run_id`→`import_run_id` column rename, `pipeline_run_status`→`import_run_status` type rename.

### Fixture-driven monkeypatch integration test for PDF-path strategy branches
**Source:** `pipeline/tests/test_parse.py::test_run_id_strategy` (lines 103-229) — full reusable skeleton: monkeypatches `pipeline.commands.parse.parse_with_llm` (raise `RuntimeError` → forces `rule_based`; or return a valid response object → forces `llm_corrective`), `pipeline.commands.parse.extract_pages` (returns a minimal synthetic transcript string), and `pipeline.commands.parse.get_session` (yields the test's own `async_session` via an `asynccontextmanager`). Creates minimal `Case`/`Argument`/`CaseArgument`/`PipelineRun` rows directly via the ORM, then calls `await run_parse(args)` and asserts on the newly-created run + its utterances.
**Apply to:** the new `pipeline/tests/test_import_run_provenance.py` — reuse this exact skeleton twice (once per LLM-mock behavior) to prove `pdf_pipeline/rule_based` and `pdf_pipeline/llm_corrective`, asserting `import_run.source == ImportSource.PDF_PIPELINE` and `import_run.method == (ImportMethod.RULE_BASED | ImportMethod.LLM_CORRECTIVE)` instead of the old `strategy in (...)` string assertion. For `corpus/direct`, add analogous assertions to an existing `pipeline/tests/test_import_convokit_core.py` test rather than duplicating the whole reset-to-fixture flow.

### Hardcoded `"pipeline_runs"` string sites (3 locations — must update together, same commit as migration)
**Source / line numbers:**
1. `/home/jason/scotuschat/project/conftest.py` line 78 — `_WATCHED_TABLES` tuple entry `"pipeline_runs"` → `"import_run"`.
2. `/home/jason/scotuschat/project/pipeline/tests/conftest.py` lines 130, 217 — two TRUNCATE list entries `pipeline_runs,` → `import_run,`.
3. `/home/jason/scotuschat/project/api/services/admin_dev.py` line 123 (`TRUNCATE_SQL` constant, inside a 9-table `TRUNCATE TABLE ... CASCADE` statement) — `pipeline_runs,` → `import_run,`.

**Apply to:** all three in the same PR as migration 0026 — RESEARCH.md's Runtime State Inventory + Security Domain sections flag that a stale string here silently blinds the leak-detection tripwire (per the Phase 45 incident referenced in `conftest.py`'s own header) or breaks `reset_to_fixture`/`clean_db` with `UndefinedTable`.

### `reset_to_fixture` reseed harness (verification vehicle for D-02/D-06's `corpus/direct` combination)
**Source:** `api/services/admin_dev.py::FIXTURE_SET` (lines 79-100, 4 fixed conversation-id/case-name/role dicts) + `reset_to_fixture` (lines 150-210+): pre-flight corpus-file check → `TRUNCATE_SQL` → loop over `FIXTURE_SET` calling `run_import_convokit(SimpleNamespace(conversation_id=..., corpus_dir=...))` → verify `Argument` row landed via `select(Argument).where(Argument.oyez_transcript_id == conversation_id)` → raise `ResetIncompleteError` on any gap.
**Apply to:** confirmed by RESEARCH.md Pitfall 2 that this ONLY exercises `corpus/direct` — it has no PDF fixture and cannot be extended to cover `pdf_pipeline/rule_based`/`llm_corrective` without adding a PDF file under `pipeline/tests/` (none exists today). Use this harness only for the `corpus/direct` leg of D-06; use the `test_run_id_strategy`-style monkeypatch harness (above) for the two PDF-path legs.

## No Analog Found

None. Every file this phase touches is a rename/extend of existing, directly-analogous in-repo code — no genuinely new architectural pattern is being introduced (confirmed by RESEARCH.md's own framing: "every piece of 'generalize the run/job model' work this phase needs already has a near-identical precedent").

## Metadata

**Analog search scope:** `api/models/models.py`, `alembic/versions/` (0001, 0003, 0025 read; 0008/0013/0017/0020/0021/0024 referenced via RESEARCH.md), `pipeline/commands/{ingest,parse,resolve,import_convokit}.py`, `api/services/{arguments,admin_jobs,admin_arguments,admin_dev}.py`, `conftest.py` (repo root), `pipeline/tests/{conftest.py,test_parse.py,test_pipeline_run.py}`
**Files scanned:** ~15 read directly this session (in addition to the 15 already read during RESEARCH.md's session, per its Sources list)
**Pattern extraction date:** 2026-08-17
