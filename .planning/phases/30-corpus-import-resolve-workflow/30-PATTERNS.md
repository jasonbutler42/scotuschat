# Phase 30: Corpus Import Resolve Workflow - Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 4 (all modified, none new)
**Analogs found:** 4 / 4

**Note on this phase's shape:** Unlike a typical phase, RESEARCH.md already did the analog work at code-excerpt level (it read the actual target files directly, since the "analog" for each modified file is mostly *itself*, at a different code path/line range within the same file). This PATTERNS.md packages those excerpts in planner-consumable form and adds the confirmed line numbers from direct reads performed in this pass.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|----------------|------|-----------|-----------------|----------------|
| `pipeline/commands/import_convokit.py` (`_import_conversation`) | pipeline command / batch writer | batch, CRUD (insert) | `pipeline/commands/resolve.py` (HIT-row `discrepancies.append` block) | exact — same JSONB shape, same producer role (pipeline layer writing `AdminJob.discrepancies`) |
| `api/services/admin_jobs.py` (`list_jobs`, `get_job`) | service | CRUD (read, derived field) | `list_jobs`'s own existing `is_archived` outerjoin derivation (same file) | exact — same function, same derivation pattern, needs `exists()` instead of `outerjoin` per the 1:many fix RESEARCH.md flags |
| `api/schemas/admin_jobs.py` (`AdminJobResponse`) | schema (Pydantic) | request-response | `AdminJobResponse.is_archived` field (same file, same class) | exact — identical shape: a derived boolean/literal field with a default and a comment explaining its derivation |
| `app/src/routes/admin/pipeline/+page.svelte` (jobs table) | component | request-response (SSR list render) | Existing Status badge `<td>`/`badgeStyle`/`badgeLabel` column in the same table | exact — same table, same per-row derived-tag rendering pattern |

## Pattern Assignments

### `pipeline/commands/import_convokit.py` (pipeline command, batch/CRUD)

**Analog:** `pipeline/commands/resolve.py` lines 235-282 (HIT/MISS discrepancy shape) + `import_convokit.py`'s own `_import_conversation` (lines 380-483, this session's direct read).

**Current write to change (`import_convokit.py:394-400`):**
```python
argument = Argument(
    argued_date=argued_date,
    question_number=next_question_number,
    source_docket=case_fields["docket_no"],
    status=ArgumentStatusEnum.DRAFT,  # D-06
    oyez_transcript_id=conversation_id,  # D-10
)
```
Change `status=ArgumentStatusEnum.DRAFT,  # D-06` to `status=ArgumentStatusEnum.PIPELINE,  # Phase 30 fix — D-06 superseded, see 30-RESEARCH.md Pitfall 1`. This is the crux write-path fix; without it every corpus Resolve card renders permanently read-only.

**Insertion point — end of `_import_conversation`, after `_import_utterances(...)` returns (`import_convokit.py:474-483`, confirmed the function's last statement):**
```python
await _import_utterances(
    session=session,
    argument_id=argument.id,
    pipeline_run_id=run.id,
    strategy=run.strategy,
    turns=turns,
    speakers_index=speakers_index,
    resolved_participants=resolved_participants,
    counters=counters,
)

# --- Phase 30: pause every corpus-imported argument for operator review (D-01, D-03) ---
resolved = [p for p in resolved_participants.values() if p is not None]
session.add(
    AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
        discrepancies=_build_discrepancies(resolved),
    )
)
# No separate commit/flush — get_session()'s context manager commits the
# whole per-conversation transaction atomically on clean exit.
```

**HIT-shaped discrepancy dict to mirror (`resolve.py:245-255`, the exact analog):**
```python
discrepancies.append(
    {
        "raw_speaker_label": raw_label,
        "normalized": normalized,
        "candidates": [],  # HIT rows need no candidates — operator confirms or overrides
        "auto_match_id": person_id,
        "auto_match_name": person.full_name,
        "auto_match_role": auto_match_role,
        "auto_resolved": True,
    }
)
```

**New helper to add in `import_convokit.py` (per RESEARCH.md Pattern 2), built from `ArgumentParticipant` rows instead of `resolve.py`'s raw-label loop:**
```python
from pipeline.commands.resolve import normalize_label

def _build_discrepancies(participants: list[ArgumentParticipant]) -> list[dict]:
    """One HIT-shaped dict per already-resolved corpus participant (D-05 parity)."""
    return [
        {
            "raw_speaker_label": p.raw_speaker_label,
            "normalized": normalize_label(p.raw_speaker_label),
            "candidates": [],
            "auto_match_id": p.person_id,
            "auto_match_name": p.raw_speaker_label,  # full_name IS raw_speaker_label for corpus rows
            "auto_match_role": None,  # corpus Person rows never set role_id
            "auto_resolved": True,
        }
        for p in participants
        if p.person_id is not None
    ]
```

**Anti-pattern to avoid (do not copy):** Do not use `admin_jobs.py`'s `create_job()` helper — it defaults to `PENDING`/`INGEST` and commits internally, breaking the per-conversation atomicity this file already relies on. Construct `AdminJob` directly with `session.add()`, matching how `Case`/`Argument`/`PipelineRun` are already created in this same file (see `argument = Argument(...); session.add(argument)` and `run = PipelineRun(...); session.add(run)` above).

**Imports needed:** `AdminJob`, `AdminJobStatus`, `AdminJobStep` from `api.models.models` (confirm these aren't already imported in `import_convokit.py` — `Argument`/`ArgumentStatusEnum`/`ArgumentParticipant`/`PipelineRun` clearly already are, per the excerpt above) and `normalize_label` from `pipeline.commands.resolve`.

---

### `api/services/admin_jobs.py` (service, CRUD/derived-field read)

**Analog:** `list_jobs`'s own existing `is_archived` derivation, `admin_jobs.py:219-255` (direct read, this pass):
```python
query = select(AdminJob, Argument.status).outerjoin(
    Argument, AdminJob.argument_id == Argument.id
)
if incomplete:
    query = query.where(
        AdminJob.status.in_([AdminJobStatus.PAUSED, AdminJobStatus.FAILED])
    )
query = query.order_by(AdminJob.created_at.desc())
result = await db.execute(query)
rows = result.all()
jobs: list[AdminJob] = []
for job, arg_status in rows:
    job.__dict__["is_archived"] = (
        arg_status is not None and arg_status != ArgumentStatusEnum.PIPELINE
    )
    job.__dict__.setdefault("parse_stats", None)
    jobs.append(job)
return jobs
```

**New `source` derivation to add (per RESEARCH.md Code Examples — use `exists()`, NOT a raw second `outerjoin`, because `Argument -> PipelineRun` is 1:many and a naive join risks duplicate `AdminJob` rows):**
```python
from sqlalchemy import exists
from pipeline.commands.import_convokit import PIPELINE_RUN_STRATEGY  # "convokit_import"

is_corpus_subq = exists(
    select(PipelineRun.id).where(
        PipelineRun.argument_id == AdminJob.argument_id,
        PipelineRun.strategy == PIPELINE_RUN_STRATEGY,
    )
)

query = select(AdminJob, Argument.status, is_corpus_subq.label("is_corpus")).outerjoin(
    Argument, AdminJob.argument_id == Argument.id
)
...
for job, arg_status, is_corpus in rows:
    job.__dict__["source"] = "corpus" if is_corpus else "pdf"
```
Apply the same single-row `exists()` subquery to `get_job()` for parity (RESEARCH.md Code Examples, "get_job() also needs this field") — `get_job()` currently defaults `is_archived=False` unconditionally with an explanatory comment; add an equivalent `source` derivation there rather than defaulting to `"pdf"` unconditionally.

**Precedent for cross-layer import:** `admin_jobs.py` already imports `normalize_label` from `pipeline.commands.resolve`, and `admin_arguments.py` already imports `_derive_slug` from `pipeline.commands.ingest` — importing `PIPELINE_RUN_STRATEGY` from `pipeline.commands.import_convokit` into `admin_jobs.py` follows this same established precedent (or hardcode the literal string with a cross-reference comment if preferred — both are consistent with existing codebase precedent).

---

### `api/schemas/admin_jobs.py` (`AdminJobResponse`)

**Analog:** `is_archived` field on the same class, `admin_jobs.py:59-65` (direct read, this pass):
```python
# Phase 26 gap closure (PLIST-05): true when the job's linked argument has
# already been created (its status is no longer PIPELINE), mirroring the
# already_created state RunReadiness reports for the detail page. Defaults
# to False for get_job (single-job path derives its archived signal from
# the readiness endpoint instead) and is populated for real by list_jobs
# via an Argument outerjoin.
is_archived: bool = False
```

**New field to add, same style:**
```python
# Phase 30: "pdf" for jobs created via the ingest pipeline, "corpus" for
# jobs created directly by import-convokit (Phase 30, D-01). Derived via
# an exists() subquery on PipelineRun.strategy == "convokit_import" in
# both list_jobs() and get_job() — see api/services/admin_jobs.py.
source: Literal["pdf", "corpus"] = "pdf"
```
`Literal` is already imported at the top of this file (`from typing import Literal, Optional`, line 4) — no new import needed.

---

### `app/src/routes/admin/pipeline/+page.svelte` (jobs list table)

**Analog:** existing Status badge column, `+page.svelte:110-129` (`badgeStyle`/`badgeLabel` functions) and the table row rendering at `+page.svelte:628-641` (direct read, this pass):
```svelte
{#each data.jobs as job}
    <tr>
        <td style="...">
            <span style={badgeStyle(job.status, job.is_archived)}>
                {badgeLabel(job.status, job.current_step, job.is_archived)}
            </span>
        </td>
        ...
```
Per 30-UI-SPEC.md (referenced in RESEARCH.md, scoped to the list page only — detail page is explicitly unchanged, D-05), add a new "Source" `<th>`/`<td>` column following this exact same derived-tag rendering shape: a small helper function analogous to `badgeStyle`/`badgeLabel` that maps `job.source` ("pdf" | "corpus") to a label/style, rendered in its own `<td>` cell per row, positioned per the UI spec's column order. `job.source` arrives on `data.jobs` because `+page.server.ts`'s load function passes through whatever `AdminJobResponse` returns from the API — no `+page.server.ts` change needed since `source` is now part of the schema (confirm this by checking `+page.server.ts`'s load function does a straight passthrough, not a field allowlist).

## Shared Patterns

### Two-step resolve -> approve lifecycle (must not be re-implemented for corpus jobs)
**Source:** `api/services/admin_jobs.py` `resolve_job()` (~lines 360-479) and `approve_job()` (~lines 487-541), both reused completely unmodified.
**Apply to:** `import_convokit.py` — do not have the new `AdminJob` insert set `Argument.status` to anything other than `PIPELINE`; do not have it stamp `resolved_at`. Both of those remain `resolve_job()`'s and `approve_job()`'s exclusive responsibility, unchanged, for both PDF and corpus jobs.
```python
# resolve_job(): stamps resolved_at, completes the JOB, never touches Argument.status
if job.argument_id is not None:
    await db.execute(
        update(Argument)
        .where(Argument.id == job.argument_id)
        .values(resolved_at=func.now())
        .execution_options(synchronize_session=False)
    )
# approve_job(): the ONLY place Argument.status transitions PIPELINE -> DRAFT
if argument.status != ArgumentStatusEnum.PIPELINE:
    raise ValueError(...)  # double-approve guard — also protects corpus jobs
await db.execute(
    update(Argument)
    .where(Argument.id == job.argument_id)
    .values(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
    .execution_options(synchronize_session=False)
)
```

### Derived-field-via-subquery pattern (source, is_archived)
**Source:** `api/services/admin_jobs.py` `list_jobs()`'s `is_archived` derivation, `admin_jobs.py:235-249`.
**Apply to:** both the new `source` field in `list_jobs()`/`get_job()` and any future derived boolean/enum fields on `AdminJob` — never add a schema/DDL column when the signal is already computable from an existing relationship (`PipelineRun.strategy`, `Argument.status`), per CLAUDE.md's "Alembic is the sole DDL authority" constraint and this codebase's established precedent.

### HIT-shaped discrepancies dict
**Source:** `pipeline/commands/resolve.py` lines 245-255.
**Apply to:** the new `_build_discrepancies()` helper in `import_convokit.py` — must reproduce the exact same 7 keys (`raw_speaker_label`, `normalized`, `candidates`, `auto_match_id`, `auto_match_name`, `auto_match_role`, `auto_resolved`) so `ResolveCard.svelte`'s Action-column rendering (driven entirely by this JSONB shape, per D-05) works unmodified for corpus jobs.

## No Analog Found

None — RESEARCH.md's direct code reads confirm all 4 modified files have a fully-applicable in-codebase analog (in 3 of 4 cases, the analog is a different code path within the *same* file being modified).

## Metadata

**Analog search scope:** `pipeline/commands/`, `api/services/admin_jobs.py`, `api/schemas/admin_jobs.py`, `app/src/routes/admin/pipeline/` (list + detail pages) — matches RESEARCH.md's "Sources" list; no additional directories searched since RESEARCH.md already performed exhaustive direct reads of every file in scope.
**Files scanned:** 4 modified files + 2 analog-source files (`pipeline/commands/resolve.py`, existing badge-rendering block in `+page.svelte`) via direct Read in this pass, cross-checked against RESEARCH.md's line-numbered excerpts.
**Pattern extraction date:** 2026-07-10
