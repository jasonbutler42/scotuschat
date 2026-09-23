# Phase 47: Provenance Foundation - Research

**Researched:** 2026-08-17
**Domain:** PostgreSQL schema re-model (Alembic DDL) + SQLAlchemy 2.0 async ORM + Python 3.12 pipeline write paths
**Confidence:** HIGH — every claim below is grounded in files read this session (models, migrations, pipeline commands, services, tests, fixtures). No external library research was needed; this is an in-repo schema refactor using patterns already established in this codebase.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: Clean rebuild, not in-place backfill.** The project database holds no data that must be retained. The migration drops `pipeline_runs` and creates `import_run` fresh with the new shape rather than ALTER-and-backfill-existing-rows. No in-migration `strategy → source/method` translation step is required. Reversibility: one-way (needs a reverse Alembic migration to undo).
- **D-02: The `strategy → source/method` mapping lives in the go-forward import code, not a migration backfill.** Corpus (`import_convokit`) and PDF (ingest/parse/resolve) paths are updated to stamp `source`/`method`/`external_id` at write time. Provenance is correct by construction on every new row, verified by re-seeding a fixture and reading provenance directly off the rows.
- **D-03: PROV-05 is reframed from "backfill existing rows deterministically" to go-forward provenance.** New intent: every import path stamps `source`/`method`/`external_id` at write time, verified by re-seeding a fixture and reading provenance directly off the rows. REQUIREMENTS.md and ROADMAP.md have already been edited to reflect this (done 2026-08-17, operator-approved).
- **D-04: `admin_jobs` is NOT touched in Phase 47.** The `admin_job → import_run` re-point (and the corpus-writes-`import_run`-directly rework) is deferred to a later "Path rework" phase. Phase 47 keeps its migration tight: `import_run` + provenance + `external_id` + nullable PDF fields + utterance FK repoint only.
- **D-05: Drop `utterance.strategy` in this migration.** The column is NOT-NULL today and now redundant — utterances inherit provenance from their `import_run` (`source`/`method`). Reversibility: one-way (column drop; re-adding needs a migration and a re-population source).
- **D-06 (verification guardrail): The fixture re-seed used to verify write-time provenance MUST exercise all provenance combinations the code can produce** — at minimum `corpus/direct`, `pdf_pipeline/rule_based`, `pdf_pipeline/llm_corrective`. If the existing 4-fixture set (Phase 41/43) doesn't cover every combination, that gap must be surfaced during research/planning.

**Carried forward (locked by design notes — do NOT re-litigate):**
- `import_run` replaces `pipeline_run` as the lineage backbone; utterances FK to `import_run` (`import_run_id`).
- `source` closed vocabulary: `operator` / `corpus` / `pdf_pipeline` / `seed`.
- `method` closed vocabulary: `manual` / `direct` / `normalized` / `rule_based` / `llm_corrective`.
- `external_id` is populated from today's `oyez_transcript_id`; `oyez_case_id` / `oyez_speaker_id` remain where they are.
- `pdf_path` / `pdf_url` become nullable, populated only for `pdf_pipeline` runs; corpus runs carry no fabricated PDF artifacts.
- Provenance grain mapping: `convokit_import → corpus/direct`, `rule_based → pdf_pipeline/rule_based`, `llm_corrective → pdf_pipeline/llm_corrective`. Research must confirm what `source`/`method` the PDF-lifecycle ingest/resolve steps (which carry no `strategy` today) should stamp — **see "Method vocabulary for ingest/resolve" below, this is now resolved with a recommendation.**

### Claude's Discretion

- Enum representation for `source`/`method` (native PG enum type vs. varchar + CHECK constraint) — technical implementation detail. **See "Standard Stack" below — recommendation: native PG enum.**
- Whether `import_run` keeps today's per-step grain (one row per ingest/parse/resolve) or collapses to per-argument (one row for the whole PDF lifecycle) — the row-count-preservation constraint that would have forced per-step is gone (D-01). **See "Architecture Patterns" below — recommendation: keep per-step grain, with reasoning grounded in the read-path/admin-job code that depends on it.**

### Deferred Ideas (OUT OF SCOPE)

- `admin_job → import_run` re-point and corpus-writes-`import_run`-directly rework → later "Path rework" phase.
- `trust_tier` materialized rollup, `candidate` status, publish gate → Phase 48.
- `review_state`, discrepancy recording, operator review queue → Phase 49.
- Optional `import_batch` grouping for corpus term-range runs → possible later grouping, not this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROV-01 | Every import unit records a declared `source` (operator / corpus / pdf_pipeline / seed) | Native PG enum `import_source` on `import_run`, NOT NULL. See Standard Stack + Code Examples. |
| PROV-02 | Every import unit records a declared `method` (manual / direct / normalized / rule_based / llm_corrective) | Native PG enum `import_method` on `import_run`, NOT NULL. Method mapping resolved for all four write paths (ingest/parse/resolve/corpus) below. |
| PROV-03 | `import_run` generalizes `pipeline_run`; utterances reference `import_run` | Table rename `pipeline_runs` → `import_run` + FK rename `pipeline_run_id` → `import_run_id`. Full call-site inventory below (23 test files + 8 production modules). |
| PROV-04 | External-source lineage (oyez ids) captured on `import_run.external_id` | **Critical finding:** `Argument.oyez_transcript_id` is a public API field and frontend-consumed value — do NOT remove it from `Argument`. Recommend dual-write: keep `Argument.oyez_transcript_id` (existing dedup/API/frontend dependency) AND add `import_run.external_id` populated with the same value at write time. See Common Pitfalls #1. |
| PROV-05 | Every import path stamps `source`/`method`/`external_id` at write time, verified by re-seeding a fixture | **Critical finding:** existing `reset_to_fixture` (Phase 43) tool exercises ONLY the corpus path (all 4 fixtures go through `run_import_convokit`) — it does NOT cover `pdf_pipeline/rule_based` or `pdf_pipeline/llm_corrective`. D-06's guardrail is NOT satisfied by the existing tool. See Validation Architecture + Common Pitfalls #2 for the concrete test plan needed. |
| PROV-06 | `pdf_path`/`pdf_url` nullable, populated only for `pdf_pipeline` source | **Verified:** both columns are ALREADY `nullable=True` in the current schema (`api/models/models.py:401-402`) and the corpus importer never sets them. This criterion is largely a no-regression check, not a new ALTER — see Common Pitfalls #3. |
</phase_requirements>

## Summary

This phase renames and re-shapes `pipeline_runs` into `import_run`, adds two new closed-vocabulary enum columns (`source`, `method`) plus `external_id`, repoints `Utterance.pipeline_run_id → import_run_id`, and drops the now-redundant `Utterance.strategy` column. Because the project database is disposable (D-01/D-02/D-03), this ships as a clean-rebuild Alembic migration (`DROP TABLE pipeline_runs CASCADE` + `CREATE TABLE import_run`) rather than an ALTER-and-backfill, and every import writer (`ingest.py`, `parse.py`, `resolve.py`, `import_convokit.py`) is updated to stamp `source`/`method` at row-creation time instead of the migration doing any translation.

The codebase already has strong, directly-reusable precedent for every piece of this: native PG enums via `SAEnum(..., values_callable=...)` (used for `SideEnum`, `PipelineRunStatus`, `AdminJobStatus`, `ArgumentStatusEnum`), a DO-block-guarded `CREATE TYPE` idiom for brand-new enum types (migrations 0001, 0003), and an in-place `ALTER TYPE ... RENAME TO` path for the existing `pipeline_run_status` type (its 5 values — `pending/running/completed/failed/needs_review` — are unchanged, so it can be renamed rather than recreated). The riskiest parts of this phase are NOT the DDL — they are two things research found by reading the actual write/read paths, not by inference: (1) `Argument.oyez_transcript_id` is a public API field consumed by the SvelteKit frontend and used as the corpus-import idempotency key — it must NOT be removed from `Argument` even though the ER sketch's `IMPORT_RUN.external_id [CHG from oyez_transcript_id]` annotation could be misread that way; and (2) the existing fixture re-seed tool (`reset_to_fixture`, Phase 43) only exercises the corpus path, so D-06's three-combination verification guardrail requires new test coverage the plan must explicitly add, following the exact monkeypatch pattern `pipeline/tests/test_parse.py::test_run_id_strategy` already established for driving a real `ingest→parse` flow through both `rule_based` and (with one extra monkeypatch) `llm_corrective` without a live Anthropic API call.

**Primary recommendation:** Do a mechanical, low-risk rename-and-extend migration (keep the existing per-step grain that `api/services/arguments.py`, `api/services/admin_jobs.py`, and `api/services/admin_arguments.py` already depend on for their `step="parse"` filtering), add `source`/`method` as native PG enums, add `external_id` as a new nullable column that duplicates (never replaces) `Argument.oyez_transcript_id`, and write two new pipeline tests (rule_based + llm_corrective via ingest→parse monkeypatching) plus one corpus-path assertion (already covered by `reset_to_fixture`) to jointly satisfy D-06.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `import_run` schema (table, enums, FKs) | Database / Storage | — | Alembic is the sole DDL authority (CLAUDE.md); this is pure schema. |
| Provenance stamping at write time | Pipeline (CLI) | — | `ingest.py`/`parse.py`/`resolve.py`/`import_convokit.py` are offline CLI writers; FastAPI never writes (CLAUDE.md: "FastAPI is read-only"). |
| Utterance FK repoint + `strategy` column drop | Database / Storage | Pipeline (CLI) | Schema change (DB) + every writer that sets `Utterance.pipeline_run_id`/`strategy` (pipeline). |
| Read-path queries (`get_argument_with_utterances`, admin job source/stats) | API / Backend | — | `api/services/arguments.py`, `api/services/admin_jobs.py` query `PipelineRun`/`Utterance` directly; must be updated for the rename, read-only otherwise. |
| Public API schema fields (`pipeline_run_id`, `strategy`, `oyez_transcript_id`) | API / Backend | Frontend (consumer, no changes needed) | `api/schemas/utterance.py` is the contract; verified no SvelteKit component actually reads `pipeline_run_id`/`strategy` today (only `oyez_transcript_id` is consumed, and it stays put). |
| Verification fixture / reset tooling | Database / Storage (test data) | Pipeline (CLI, via `run_import_convokit`) | `api/services/admin_dev.py::reset_to_fixture` truncates and reseeds; new PDF-path fixture coverage is a pipeline-test concern (pytest), not a change to the dev-reset endpoint itself. |

## Standard Stack

### Core (already installed and in use — verified via `pip show`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 `[VERIFIED: pip show]` | ORM models, async session | Already the project's ORM; `api/models/models.py` uses `Enum as SAEnum` with `values_callable` throughout. |
| Alembic | 1.19.1 `[VERIFIED: pip show]` | Sole DDL authority (CLAUDE.md) | `alembic current` confirms head is `0025`; next migration is `0026`. |
| asyncpg | 0.31.0 `[VERIFIED: pip show]` | Async PG driver | `connect_args={"statement_cache_size": 0}` already present in `api/core/database.py:38` and `pipeline/db.py:49` — no change needed, just don't regress it. |

No new external packages are introduced by this phase (pure schema + in-repo pipeline/service code changes) — the Package Legitimacy Audit and dependency-install steps are not applicable.

### Enum representation decision: native PG enum (recommended)

CONTEXT.md left this as Claude's Discretion with the tradeoff already spelled out (native enum matches existing pattern but can't drop values; varchar+CHECK is easier to evolve). Evidence from the codebase settles it:

- **5 of 7** existing enum-shaped columns use native PG enums via `SAEnum(..., values_callable=lambda e: [x.value for x in e])`: `SideEnum` (`side`), `PipelineRunStatus` (`pipeline_run_status`), `AdminJobStatus`, `AdminJobStep`, `ArgumentStatusEnum` (`argument_status`) — all in `api/models/models.py`.
- Only **2 of 7** use varchar + CHECK constraint: `CourtTenure.office` and `CourtTenure.reason_left` (migrations 0020/0021, 0024) — and the model's own comments (`models.py:210-219`) frame these as late, narrow, two/three-value additions, not the primary identity vocabulary of a table.
- `source`/`method` are exactly analogous to `side`/`argument_status`/`pipeline_run_status`: a small, deliberately closed vocabulary that is the primary discriminator of a row, decided during a design phase (`provenance-and-trust-model.md`), not something expected to gain values incrementally in the next few phases.

**Recommendation: native PG enum types `import_source` and `import_method`**, created via the DO-block-guarded `CREATE TYPE` idiom already used in migrations 0001 and 0003 (see Code Examples). The one real cost — PG cannot drop enum values — is explicitly already a project-wide accepted tradeoff (see `SideEnum.ADVOCATE` comment: "legacy — never remove (PG cannot drop enum values)"; `argument_status`'s `PIPELINE` value is expected to be superseded by `candidate` the same way in Phase 48, per STATE.md's blocker note).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native PG enum for `source`/`method` | varchar(50) + CHECK constraint | Easier to add a 5th `source`/`method` value later without an `ALTER TYPE ADD VALUE` outside-transaction dance — but breaks consistency with `side`/`argument_status`/`pipeline_run_status` and loses DB-level exhaustiveness checking. Not recommended given the vocab is explicitly "closed" per design notes. |
| Rename `pipeline_run_status` enum type in place | Drop and recreate a new `import_run_status` type | The 5 values (`pending/running/completed/failed/needs_review`) are unchanged — `ALTER TYPE pipeline_run_status RENAME TO import_run_status` is a single, cheap, reversible statement; no reason to drop/recreate. |
| Per-step `import_run` grain (recommended) | Collapse to one row per argument-import-attempt | See Architecture Patterns below — collapsing breaks or requires rewriting `api/services/arguments.py:88-91`, `api/services/admin_jobs.py:157-268` step-filtering queries, which are explicitly out of scope this phase (D-04 keeps admin_jobs untouched; this extends to its query dependencies). |

**Installation:** N/A — no new packages.

## Package Legitimacy Audit

Not applicable — this phase installs no external packages. All work is schema DDL (Alembic) plus edits to existing in-repo Python modules using already-installed libraries (SQLAlchemy, asyncpg).

## Architecture Patterns

### System Architecture Diagram

```
 PDF PATH (3 writers, unchanged step sequence)          CORPUS PATH (1 writer)
 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    ┌──────────────────────┐
 │ ingest.py   │→→│ parse.py    │→→│ resolve.py  │     │ import_convokit.py   │
 │ step=ingest │   │ step=parse  │   │ step=resolve│    │ (single row per      │
 │             │   │ rule_based/ │   │             │    │  conversation)       │
 │             │   │ llm_correct.│   │             │    │                      │
 └──────┬──────┘   └──────┬──────┘   └──────┬──────┘    └──────────┬───────────┘
        │                 │                 │                      │
        ▼                 ▼                 ▼                      ▼
   creates 1 import_run row EACH, all source=pdf_pipeline    creates 1 import_run row,
   method: normalized | rule_based/llm_corrective | normalized  source=corpus, method=direct
        │                 │                                        │
        │                 ▼ (Utterance.import_run_id = parse run's id)
        │           ┌──────────────┐                                │
        └──────────▶│ import_run   │◀───────────────────────────────┘
                     │ source       │
                     │ method       │
                     │ external_id  │ (dual-written; Argument.oyez_transcript_id
                     │ pdf_path/url │  keeps its own copy — see Pitfall 1)
                     │ status       │
                     └──────┬───────┘
                            │ FK (import_run_id)
                            ▼
                     ┌──────────────┐
                     │ utterances   │  (strategy column DROPPED — inherits
                     │              │   provenance from its import_run)
                     └──────┬───────┘
                            │
                            ▼
        READ PATH: api/services/arguments.py::get_argument_with_utterances
        filters WHERE import_run.step='parse' AND status=COMPLETED,
        picks MAX(id) → unchanged query shape, renamed table/column only.
```

### Recommended Project Structure

No new directories. Changes land in:
```
alembic/versions/0026_*.py           — new migration (table rename + new columns + enum types)
api/models/models.py                 — PipelineRun → ImportRun rename, new enum classes, column additions
api/schemas/utterance.py              — pipeline_run_id → import_run_id, drop `strategy` field
api/services/arguments.py             — PipelineRun → ImportRun references
api/services/admin_jobs.py            — PipelineRun → ImportRun references; strategy== check → source== check
api/services/admin_arguments.py       — PipelineRun → ImportRun in cascade-delete
api/routers/admin.py                  — PipelineRun → ImportRun (pdf streaming lookup)
pipeline/commands/ingest.py           — stamp source=pdf_pipeline, method=normalized
pipeline/commands/parse.py            — stamp source=pdf_pipeline, method=rule_based|llm_corrective
pipeline/commands/resolve.py          — stamp source=pdf_pipeline, method=normalized
pipeline/commands/import_convokit.py  — stamp source=corpus, method=direct, external_id=conversation_id
tests/conftest.py                     — _WATCHED_TABLES: "pipeline_runs" → "import_run"
pipeline/tests/conftest.py            — TRUNCATE list: pipeline_runs → import_run
api/services/admin_dev.py             — TRUNCATE_SQL: pipeline_runs → import_run
```

### Pattern 1: Grain decision — keep per-step `import_run` rows (recommended over collapsing to per-argument)

**What:** `import_run` keeps a `step` column (`"ingest"|"parse"|"resolve"`, same 3 values as today's `PipelineRun.step`), and the PDF path continues to create one row per step, exactly as `PipelineRun` does today. The corpus path continues to create exactly one row (as it already does, using `step="parse"` as its label of convenience).

**When to use:** This phase. The alternative (collapsing ingest/parse/resolve into a single row per argument) is real and matches the design sketch's spirit more closely, but research found it has a much larger blast radius than CONTEXT.md's framing ("Claude's Discretion... utterance FK must be preserved either way") suggests:

- `api/services/arguments.py:88-91` — the PUBLIC read path filters `PipelineRun.step == "parse", status == COMPLETED` and takes `MAX(id)` to find "the latest completed parse." This is how every visitor's utterance list is selected. Losing `step` means rewriting this query's semantics, not just its table name.
- `api/services/admin_jobs.py:157-268` (`get_job`, `list_jobs`, `get_run_id_for_step`) — the admin job detail/list pages derive `parse_stats`, `is_corpus`, and step-specific IDs by filtering `PipelineRun.step`. `get_run_id_for_step(db, job_id, "parse")` is called from at least 2 call sites.
- `api/services/admin_arguments.py:762-794` — the DRAFT-argument delete cascade deletes `Utterance` then `PipelineRun` by `argument_id`, with an explicit ordering comment about the FK. Collapsing grain doesn't break this specific ordering, but every other query above does depend on `step`.

Since D-04 explicitly excludes `admin_jobs` rework from this phase ("keeps its migration tight"), and these three files are exactly the `admin_jobs`-adjacent surface D-04 is trying to keep untouched, **preserving `step` is what actually honors D-04's intent** — a per-argument collapse would force touching all three files' query logic in this phase regardless of whether the `admin_jobs` *table* itself changes. Recommend deferring the grain re-architecture to the "Path rework" phase where `admin_job → import_run` re-pointing already lives.

**Example (post-migration, ingest.py unchanged in shape, only field-adds):**
```python
# pipeline/commands/ingest.py — d. ImportRun record (was PipelineRun)
run = ImportRun(
    argument_id=argument.id,
    step="ingest",
    status=ImportRunStatus.COMPLETED,
    source=ImportSource.PDF_PIPELINE,
    method=ImportMethod.NORMALIZED,   # docket_number_norm / slug derivation is a
                                       # deterministic transform — matches the vocab's
                                       # own definition of "normalized" (see below)
    pdf_path=str(pdf_path),
    pdf_url=args.url,
)
session.add(run)
```

### Pattern 2: `source`/`method` stamping per writer — resolved mapping

CONTEXT.md flagged this as an open research question ("Research must confirm what source/method the PDF-lifecycle ingest/resolve steps... should stamp"). Resolved by reading each writer's actual behavior against the vocabulary's own definitions (`provenance-and-trust-model.md`):

| Writer | `source` | `method` | Why |
|--------|----------|----------|-----|
| `ingest.py` (creates argument + downloads/stores PDF) | `pdf_pipeline` | `normalized` | Ingest performs `normalize_docket_value` + `docket_number_norm` + `_derive_slug` — deterministic transforms, exactly the vocab's own definition of `normalized` ("derived by a deterministic transform (docket norm, name split)... applies to: corpus, pdf") `[VERIFIED: .planning/notes/provenance-and-trust-model.md]`. |
| `parse.py`, rule-based branch | `pdf_pipeline` | `rule_based` | Direct 1:1 with existing `strategy="rule_based"` — no change in meaning, just closed-vocab enum instead of free string. |
| `parse.py`, LLM branch (only on `parse_with_llm` success) | `pdf_pipeline` | `llm_corrective` | Direct 1:1 with existing `strategy="llm_corrective"`. Confirmed `parse.py:190-221`: the LLM pass runs unconditionally, and success (not failure) is what flips the strategy — no "ambiguous rule-based output" gate exists today. |
| `resolve.py` (matches raw labels via `speaker_alias`) | `pdf_pipeline` | `normalized` | Resolve is purely deterministic label normalization (`normalize_label` + alias-table lookup) — confirmed no Anthropic/instructor import anywhere in `resolve.py`. Fits `normalized` exactly, same reasoning as ingest. |
| `import_convokit.py` (`_import_conversation`) | `corpus` | `direct` | Matches D-03's locked mapping exactly: `convokit_import → corpus/direct`. |
| Seed loaders (`import_justices_csv.py`, `seed_aliases.py`) | `seed` (reserved, not written this phase) | `direct` or `manual` (reserved) | **Finding:** these loaders write directly to `Person`/`CourtTenure`/`SpeakerAlias` and create NO `PipelineRun`/`import_run` row today (`grep` confirms zero references) — there is no existing FK for them to stamp. D-06's guardrail only requires 3 combinations (`corpus/direct`, `pdf_pipeline/rule_based`, `pdf_pipeline/llm_corrective`); `seed` is closed-vocabulary scaffolding for future use, not a write path this phase must wire up. Flag this explicitly to the planner so `seed` isn't accidentally scoped in. |

### Anti-Patterns to Avoid

- **Do not remove `Argument.oyez_transcript_id`.** See Common Pitfalls #1 — this is the single highest-risk mistake a literal reading of the ER sketch could produce.
- **Do not assume the existing `reset_to_fixture` 4-fixture set satisfies D-06.** It only exercises the corpus path. See Common Pitfalls #2.
- **Do not add an `ALTER COLUMN ... SET NOT NULL`-style migration step for `pdf_path`/`pdf_url`.** They are already nullable. See Common Pitfalls #3.
- **Do not use `ALTER TYPE ... ADD VALUE` for the brand-new `import_source`/`import_method` types.** That workaround (`op.execute(sa.text("COMMIT"))` then `ADD VALUE IF NOT EXISTS`, seen in migration 0008) is only needed when *expanding an existing* enum type outside a transaction. For a *brand-new* type, just `CREATE TYPE ... AS ENUM (...)` with all values up front inside the DO-block guard (migrations 0001, 0003) — no transaction-boundary dance needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Closed-vocabulary column with DB-level exhaustiveness | A Python-only validator / a plain `String` column with app-level checks | Native PG `Enum` type via SQLAlchemy `SAEnum(..., values_callable=...)`, matching `SideEnum`/`ArgumentStatusEnum` precedent exactly | The DB itself rejects out-of-vocabulary writes; matches 5 of 7 existing enum columns in this codebase — consistency with `models.py`'s established idiom. |
| "Is this run a corpus import?" detection | A `strategy == "convokit_import"` string-equality hack (today's pattern in `api/services/admin_jobs.py:162,268`) | `ImportRun.source == ImportSource.CORPUS` | This is literally the phase's stated goal — "answerable by reading the row, not archaeology." Retiring the string hack in `admin_jobs.py` is a direct, low-risk win once the columns exist. |
| Detecting whether ingest/resolve produced a "declared" provenance value with no natural fit in the vocab | Inventing a 6th `method` value for ingest/resolve | `normalized` (already covers "deterministic transform" per the vocab's own docstring, and both steps qualify) | Avoids vocabulary sprawl; the design notes explicitly scoped `method` to 5 closed values. |

**Key insight:** Every piece of "generalize the run/job model" work this phase needs already has a near-identical precedent somewhere in `api/models/models.py` or `alembic/versions/`. The main risk is not technical novelty — it's under-scoping the blast radius of a table rename that a public API schema and a leak-detection test tripwire both quietly depend on.

## Runtime State Inventory

This is a rename/refactor phase (`pipeline_runs` → `import_run`, `pipeline_run_id` → `import_run_id`), so this section is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None — verified.** D-01 confirms the project DB is disposable/fixture-reseedable; no production data exists that references `pipeline_runs` by name outside this repo's own DB. | Clean-rebuild migration (`DROP TABLE ... CASCADE` + `CREATE TABLE import_run`) per D-01/D-02 — no data migration needed. |
| Live service config | **None found.** No n8n/Datadog/Tailscale/Cloudflare-style external service holds a reference to `pipeline_runs` outside this repo. This is a self-contained monorepo (FastAPI + SvelteKit + pipeline CLI), not a services-mesh deployment yet (DEPLOY-01/03 are explicitly out of scope for v1.8). | None. |
| OS-registered state | **None found.** No systemd/pm2/Task-Scheduler registration references `pipeline_runs`; the pipeline is invoked manually via `python -m pipeline <command>` (CLAUDE.md: pipeline is CLI-only, never HTTP). | None. |
| Secrets/env vars | **None found.** No env var name embeds "pipeline_run"; `DATABASE_URL`/`TEST_DATABASE_URL` are the only relevant vars and are table-name-agnostic. | None. |
| Build artifacts / test tripwires | **Found — 2 hardcoded string references that MUST be updated in the same commit as the migration:** (1) `tests/conftest.py`'s `_WATCHED_TABLES` tuple includes the literal string `"pipeline_runs"` `[VERIFIED: tests/conftest.py, read this session — tuple confirmed to contain "pipeline_runs" as one of 10 entries]`; (2) `pipeline/tests/conftest.py`'s TRUNCATE lists (2 occurrences, lines ~130 and ~217) include `pipeline_runs` `[VERIFIED: pipeline/tests/conftest.py grep hits at lines 130, 217]`; (3) `api/services/admin_dev.py`'s `TRUNCATE_SQL` constant includes `pipeline_runs` `[VERIFIED: api/services/admin_dev.py:123, read this session]`. | Update all three literal table-name lists to `import_run` in the same PR as the Alembic migration — a stale `pipeline_runs` string in any of these three will either silently stop watching the renamed table (leak-detection tripwire goes blind) or make `reset_to_fixture`/pytest's `clean_db` fixture raise `UndefinedTable` against the renamed schema. |

**Nothing found in "Stored data" / "Live service config" / "OS-registered state" / "Secrets" categories** — confirmed explicitly per the canonical question ("after every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?").

## Common Pitfalls

### Pitfall 1: Removing `Argument.oyez_transcript_id` because the ER sketch shows `IMPORT_RUN.external_id [CHG from oyez_transcript_id]`

**What goes wrong:** A literal reading of `.planning/notes/import-entity-sketch.md`'s ER diagram — where `ARGUMENT`'s field list no longer shows `oyez_transcript_id` at all, and `IMPORT_RUN.external_id` is annotated `[CHG from oyez_transcript_id]` — could lead a plan to drop the column from `Argument` and move it entirely to `import_run`.

**Why it happens:** The design-note ER sketch is a paper design pre-dating this session's code scout; it wasn't cross-checked against every live consumer of `Argument.oyez_transcript_id` at the time it was written.

**How to avoid:** Research confirmed `Argument.oyez_transcript_id` is used in three places that are explicitly OUT of this phase's scope to touch:
1. **Idempotency key** — `import_convokit.py:490` (`select(Argument).where(Argument.oyez_transcript_id == conversation_id)`) is the corpus importer's own re-run dedup check (D-08). Moving the column would require rewriting this to join through `import_run`, adding scope not asked for.
2. **Public API schema** — `api/schemas/utterance.py:54` (`ArgumentMetadataResponse.oyez_transcript_id`) and `api/services/arguments.py:135` serve it in the `GET /arguments/{id}/utterances` response.
3. **Frontend consumer** — `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:50-52` derives `is_corpus_sourced: data.argument.oyez_transcript_id != null` — a read-model / public-site behavior explicitly declared stable and out of scope by STATE.md's carry-forward constraint ("Do not touch CASE, CASE_ARGUMENT, or the utterance/participant/person read shapes beyond the provenance/review fields the sketch calls out").

**Recommendation:** Dual-write, don't move. Keep `Argument.oyez_transcript_id` exactly as-is (column, dedup query, API field, frontend behavior all unchanged) and additionally populate the new `import_run.external_id` with the same value at write time in `import_convokit.py`. This satisfies PROV-04 ("external-source lineage captured on `import_run.external_id`") without any of the three breakages above. `oyez_case_id` (`Case`) and `oyez_speaker_id` (`Person`) are unaffected either way per CONTEXT.md's carried-forward note ("remain where they are").

**Warning signs:** Any plan task that touches `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` or `api/schemas/utterance.py`'s `ArgumentMetadataResponse` — this phase's scope (CONTEXT.md) never mentions frontend or public-schema changes, so a task that requires them is a signal the grain/column decision has drifted from "generalize the backbone" into "change the read model."

### Pitfall 2: Assuming the existing fixture reset tool already satisfies D-06's verification guardrail

**What goes wrong:** D-06 requires the fixture re-seed to exercise `corpus/direct`, `pdf_pipeline/rule_based`, AND `pdf_pipeline/llm_corrective`. A plan that just points at "the existing 4-fixture reset tool" for verification will only ever prove `corpus/direct` — silently leaving 2 of 3 required combinations unverified.

**Why it happens:** `api/services/admin_dev.py::reset_to_fixture` (Phase 43) truncates and reseeds exactly 4 conversations, ALL of them via `run_import_convokit` (`FIXTURE_SET`, `admin_dev.py:79-100`) — there is no PDF fixture in the reset tool at all (confirmed: no `.pdf` files exist under `pipeline/tests/` and no PDF path is exercised by `reset_to_fixture`).

**How to avoid:** The plan needs NEW test coverage, not reuse of `reset_to_fixture`, for the two PDF-path combinations. The exact reusable pattern already exists: `pipeline/tests/test_parse.py::test_run_id_strategy` (lines 103-229) already drives a real `ingest`-created `PipelineRun` row through `run_parse()` with `monkeypatch.setattr("pipeline.commands.parse.extract_pages", ...)` (returns a minimal synthetic transcript) and `monkeypatch.setattr("pipeline.commands.parse.parse_with_llm", ...)` (raises `RuntimeError` to force the `rule_based` fallback) — then asserts `Utterance.strategy in ("rule_based", "llm_corrective")`. For Phase 47's D-06 verification:
- **`pdf_pipeline/rule_based`:** reuse this exact pattern (LLM raises → falls back), assert the new `import_run.source == PDF_PIPELINE` and `import_run.method == RULE_BASED`.
- **`pdf_pipeline/llm_corrective`:** the SAME pattern but monkeypatch `parse_with_llm` to return a valid `llm_response` object instead of raising (per `parse.py:192-212`, success — not failure — is what sets `parse_strategy = "llm_corrective"`), then assert `import_run.method == LLM_CORRECTIVE`.
- **`corpus/direct`:** already covered structurally by the existing `reset_to_fixture`/`import_convokit` test suite (`pipeline/tests/test_import_convokit_core.py` etc.) — just add the new source/method assertions to one of those existing tests rather than building a new fixture.

**Warning signs:** A plan task titled "verify provenance via reset_to_fixture" with no PDF-path test task alongside it.

### Pitfall 3: Adding an unnecessary `ALTER COLUMN pdf_path/pdf_url SET NULL`-style migration step

**What goes wrong:** PROV-06's wording ("pdf_path/pdf_url become nullable") could be read as requiring a schema change, adding migration complexity that isn't needed.

**Why it happens:** The phase description is written from the target-state perspective, not by diffing against the current schema.

**How to avoid:** `[VERIFIED: api/models/models.py:401-402]` — `pdf_path = Column(String(500), nullable=True)` and `pdf_url = Column(String(1000), nullable=True)` are ALREADY nullable in the current `PipelineRun` model; no `NOT NULL` constraint exists to relax. `[VERIFIED: pipeline/commands/import_convokit.py:563-568]` — the corpus path's `PipelineRun(...)` call never sets `pdf_path`/`pdf_url` at all, so they are already `NULL` for every corpus row today. The only real work here is (a) carrying these two columns forward unchanged into the new `import_run` table definition, and (b) confirming (via the new tests from Pitfall 2) that they stay populated for `pdf_pipeline` rows and stay `NULL` for `corpus` rows going forward — a behavioral assertion, not a DDL change.

**Warning signs:** A migration diff that includes `ALTER COLUMN pdf_path DROP NOT NULL` — this is a no-op today and signals the plan didn't check the current column definition.

## Code Examples

### Renaming an existing PG enum type in place (no value changes)

```python
# alembic/versions/0026_import_run_provenance.py
# pipeline_run_status's 5 values (pending/running/completed/failed/needs_review)
# are unchanged — a straight rename, no CREATE/DROP TYPE needed.
op.execute(sa.text("ALTER TYPE pipeline_run_status RENAME TO import_run_status"))
```
`[VERIFIED: api/models/models.py:46-51]` — `PipelineRunStatus` enum values verbatim: `PENDING = "pending"`, `RUNNING = "running"`, `COMPLETED = "completed"`, `FAILED = "failed"`, `NEEDS_REVIEW = "needs_review"`.

### Creating brand-new closed-vocabulary PG enum types (DO-block guarded, matches migrations 0001/0003 exactly)

```python
# Source pattern: alembic/versions/0003_add_admin_jobs.py (verified, read this session)
conn = op.get_bind()
for type_name, ddl in [
    (
        "import_source",
        "CREATE TYPE import_source AS ENUM "
        "('operator', 'corpus', 'pdf_pipeline', 'seed')",
    ),
    (
        "import_method",
        "CREATE TYPE import_method AS ENUM "
        "('manual', 'direct', 'normalized', 'rule_based', 'llm_corrective')",
    ),
]:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}
    ).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))
```

### Renaming a table and its FK column in one migration (op.rename_table + op.alter_column)

```python
# pipeline_runs -> import_run (D-01 clean rebuild variant: since the DB is
# disposable, DROP+CREATE is also acceptable — but a rename+extend is
# equally valid and lower-risk if the operator prefers to avoid a full drop).
op.rename_table("pipeline_runs", "import_run")
op.alter_column(
    "utterances", "pipeline_run_id", new_column_name="import_run_id",
    existing_type=sa.Integer(), existing_nullable=False,
)
```
This mirrors the exact `op.alter_column(..., new_column_name=...)` idiom already used in migration 0025 (`argument_participants.title → descriptor`) `[VERIFIED: alembic/versions/0025_rename_participant_title_to_descriptor.py, read this session]`.

### Existing test pattern to extend for D-06's pdf_pipeline verification

```python
# Source: pipeline/tests/test_parse.py::test_run_id_strategy (read this session,
# lines 103-229). Reusable skeleton for both rule_based and llm_corrective:
async def mock_parse_with_llm(pages_text):
    raise RuntimeError("LLM not available in unit tests")  # -> rule_based
    # OR: return a valid ParsedResponse-shaped object -> llm_corrective

monkeypatch.setattr("pipeline.commands.parse.parse_with_llm", mock_parse_with_llm)
monkeypatch.setattr("pipeline.commands.parse.extract_pages", mock_extract_pages)
monkeypatch.setattr("pipeline.commands.parse.get_session", mock_get_session)
await run_parse(args)
# assert new_run.source == ImportSource.PDF_PIPELINE
# assert new_run.method in (ImportMethod.RULE_BASED, ImportMethod.LLM_CORRECTIVE)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `strategy` free-text string on `PipelineRun`/`Utterance` (`"convokit_import"`, `"rule_based"`, `"llm_corrective"`) | Closed-vocabulary `source`/`method` enum pair on `import_run` | This phase (47) | Callers stop doing `PipelineRun.strategy == "convokit_import"` string-equality checks (`api/services/admin_jobs.py:162,268`) and instead compare `ImportRun.source == ImportSource.CORPUS` — a DB-enforced, self-documenting check. |
| `Utterance.strategy` (redundant per-row copy of the run's strategy) | Dropped; utterances inherit provenance via their `import_run_id` FK | This phase (47), D-05 | One fewer NOT-NULL column every writer must set; no behavior loss since `Utterance.strategy` was always identical to its parent run's strategy in every writer (`run.strategy` is literally what's assigned in both `parse.py:282` and `import_convokit.py:1062,1118`). |
| Provenance reconstructed by joining to `pipeline_runs` and reading a free-text `strategy`, or inferring from `oyez_*` nullability | Provenance declared directly on the row via `source`/`method` | This phase (47) | This is the phase's stated purpose — "answerable by reading the row, not archaeology." |

**Deprecated/outdated:** `PipelineRun`/`pipeline_run_id`/`pipeline_run_status` naming is retired in favor of `ImportRun`/`import_run_id`/`import_run_status` — but the underlying `step`/per-run-row *shape* is intentionally NOT deprecated this phase (see Architecture Patterns, Pattern 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `seed` source / `manual` method are reserved vocabulary this phase, not a write path to implement (no seed loader creates a `PipelineRun`/`import_run` row today, and D-06 only requires 3 combinations). | Pattern 2 (mapping table) | If wrong, the plan under-scopes: seed loaders (`import_justices_csv.py`, `seed_aliases.py`) would need new `import_run`-creation code added, which CONTEXT.md's "In scope" list does not mention. Low risk — confirmed by a direct grep showing zero `PipelineRun` references in either seed-loader file. |
| A2 | Native PG enum (not varchar+CHECK) is the right choice for `source`/`method`, per the 5-of-7-existing-enums precedent. | Standard Stack | If wrong (operator prefers varchar+CHECK for easier future evolution), the DDL and ORM column definitions change shape but the migration's overall structure and every write-path call site are unaffected — low blast-radius to reverse. |
| A3 | Keeping per-step `import_run` grain (not collapsing to per-argument) is the right call for this phase, deferring the deeper run-model reshape to the later "Path rework" phase. | Architecture Patterns, Pattern 1 | This is the highest-stakes assumption in this research. If the planner/operator wants the full per-argument collapse now, three additional files (`api/services/arguments.py`, `api/services/admin_jobs.py`, `api/services/admin_arguments.py`) need query rewrites this research explicitly scoped OUT — the plan's task list and time estimate would need to grow. Flagged prominently for planner/operator confirmation before locking. |
| A4 | Dual-writing `import_run.external_id` alongside the untouched `Argument.oyez_transcript_id` (rather than moving the column) satisfies PROV-04 without violating the "read model untouched" constraint. | Common Pitfalls #1 | If wrong (operator actually wants `Argument.oyez_transcript_id` removed per the ER sketch as literally drawn), this phase's scope must expand to touch the public API schema and a frontend file — currently outside CONTEXT.md's stated scope. High-value assumption to confirm before planning locks it in. |

## Open Questions

1. **Should `import_run.step` be renamed to something less PDF-shaped (e.g., `phase` or kept as `step`) even though its 3 values (`ingest`/`parse`/`resolve`) stay unchanged this phase?**
   - What we know: Keeping the column and its values is the low-risk recommendation (Pattern 1).
   - What's unclear: Whether the column's NAME should change even though its meaning/values don't, purely for "generalized" naming consistency with the new `import_run` table name.
   - Recommendation: Leave the column name as `step` — renaming it with no behavior change adds churn to every one of the ~15 call sites that reference `.step` for zero functional benefit; the "Path rework" phase is the natural place to revisit this alongside the deeper grain question.

2. **Does the corpus path's `PIPELINE_RUN_STRATEGY = "convokit_import"` module constant get removed entirely, or kept as a legacy reference?**
   - What we know: `import_convokit.py:118` defines this constant and uses it in 2 places (`import_convokit.py:567`, and it's imported by `api/services/admin_jobs.py` for the `strategy ==` check).
   - What's unclear: Whether any historical row (pre-clean-rebuild) needs this string preserved for any archival reason — D-01 says no (disposable DB), so likely safe to delete entirely once `source=ImportSource.CORPUS` replaces its only two consumers.
   - Recommendation: Delete the constant and both its consumers in the same commit that adds `source`/`method` — leaving it around as dead code invites a future reader to wonder if it's still load-bearing.

## Environment Availability

Skipped — this phase has no new external dependencies. The existing Postgres 16 dev database, Alembic 1.19.1, SQLAlchemy 2.0.52, and asyncpg 0.31.0 are already confirmed installed and at migration head `0025` (`alembic current` run this session).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (see `pytest.ini`: `asyncio_mode = auto`, `testpaths = tests pipeline/tests api/tests`) `[VERIFIED: pytest.ini, read this session]` |
| Config file | `pytest.ini` (repo root) |
| Quick run command | `./.venv/bin/python -m pytest pipeline/tests/test_parse.py pipeline/tests/test_pipeline_run.py -x -q` |
| Full suite command | `./.venv/bin/python -m pytest` (per `.planning/config.json`'s `workflow.test_command`) |

DB-gated tests skip automatically if `TEST_DATABASE_URL` is unset (`pipeline/tests/conftest.py::test_db_url`), and the root `conftest.py` redirects `DATABASE_URL` to `TEST_DATABASE_URL` for every invocation shape (Phase 46 fix) — any new test this phase adds must go through `async_session`/`get_session()` fixtures exactly as `test_run_id_strategy` already does, never a bare `DATABASE_URL` connection.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| PROV-01/02 | `import_run` row has non-null `source`+`method` from closed vocab on every writer | unit/integration | `pytest pipeline/tests/test_import_run_provenance.py -x -q` | ❌ Wave 0 — new file |
| PROV-03 | Utterances reference `import_run_id`; existing FK-shape tests still pass | integration | `pytest pipeline/tests/test_pipeline_run.py -x -q` (rename to `test_import_run.py` recommended) | ✅ exists (`pipeline/tests/test_pipeline_run.py`) — needs rename+rewrite for new column/table names |
| PROV-04 | `import_run.external_id` populated for corpus rows; `Argument.oyez_transcript_id` unchanged | integration | `pytest pipeline/tests/test_import_convokit_core.py -x -q` | ✅ exists — add assertion for new `external_id` field to an existing corpus-import test |
| PROV-05 | D-06 guardrail: `corpus/direct`, `pdf_pipeline/rule_based`, `pdf_pipeline/llm_corrective` all provable by re-seed + row-read | integration | `pytest pipeline/tests/test_import_run_provenance.py -x -q` (new) + reuse `reset_to_fixture` route test for corpus/direct | ❌ Wave 0 — new pdf-path test cases (see Pitfall 2) |
| PROV-06 | `pdf_path`/`pdf_url` null for corpus rows, populated for pdf_pipeline rows | unit | Same new test file — assert both branches | ❌ Wave 0 — new assertions |

### Sampling Rate

- **Per task commit:** `./.venv/bin/python -m pytest pipeline/tests/test_parse.py pipeline/tests/test_pipeline_run.py pipeline/tests/test_import_convokit_core.py -x -q`
- **Per wave merge:** `./.venv/bin/python -m pytest pipeline/tests api/tests -q`
- **Phase gate:** Full suite green (`./.venv/bin/python -m pytest`) before `/gsd-verify-work` — this MUST include `tests/test_pytest_isolation_invocation_shapes.py` to confirm the rootdir conftest redirect still holds after the `_WATCHED_TABLES` edit (Runtime State Inventory finding).

### Wave 0 Gaps

- [ ] `pipeline/tests/test_import_run_provenance.py` — new file covering PROV-01/02/05/06 (the two new PDF-path monkeypatch tests from Pitfall 2, plus a corpus-path assertion)
- [ ] Rename/rewrite `pipeline/tests/test_pipeline_run.py` → reflects `ImportRun`/`import_run_id` naming (PROV-03)
- [ ] Update `tests/conftest.py`'s `_WATCHED_TABLES` and `pipeline/tests/conftest.py`'s two TRUNCATE lists to reference `import_run` (Runtime State Inventory) — without this, `clean_db` fixtures will raise `UndefinedTable` against the renamed schema and silently break every DB-gated pipeline test.
- [ ] Update `api/services/admin_dev.py`'s `TRUNCATE_SQL` (used by `reset_to_fixture`) — without this, the dev-only reset endpoint breaks immediately after the migration lands.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | This phase touches no auth surface — pipeline is offline CLI, FastAPI stays read-only. |
| V3 Session Management | No | N/A. |
| V4 Access Control | No | No new endpoints; `reset_to_fixture` is already dev-only gated (`settings.environment == "development"`), unchanged by this phase. |
| V5 Input Validation | Yes | The new `source`/`method` columns are native PG enums — the database itself rejects any value outside the closed vocabulary, which is the strongest possible input-validation control for a closed-set field (matches `SideEnum`/`ArgumentStatusEnum` precedent). |
| V6 Cryptography | No | N/A. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Migration accidentally run against the shared dev DB instead of a disposable/test DB, destroying data thought to be retained | Tampering (of data integrity assumptions) | D-01 already confirms the dev DB is genuinely disposable and fixture-reseedable; still, run `alembic current` before applying (per STATE.md's existing blocker note) to confirm head is `0025` before this phase's `0026` migration is applied, and confirm `TEST_DATABASE_URL` vs `DATABASE_URL` distinction is respected for any test run (root `conftest.py` guard, already verified in place). |
| A stale hardcoded table-name string (`_WATCHED_TABLES`, TRUNCATE lists) silently stops watching/truncating the renamed table, letting a test leak into the shared dev DB undetected | Tampering / Repudiation (a leak that should have tripped the guard goes unnoticed) | Update all three literal-string lists (Runtime State Inventory) in the SAME commit as the migration — never split across separate PRs, per this project's own documented Phase 45 incident (`.planning/todos/pending/2026-08-12-pytest-explicit-paths-bypass-db-isolation.md`, referenced in `conftest.py`'s own header). |

## Sources

### Primary (HIGH confidence — files read directly this session)

- `api/models/models.py` — full 13-table model file, all enum definitions, `PipelineRun`/`Utterance` column definitions
- `pipeline/commands/import_convokit.py` — corpus write path, full file
- `pipeline/commands/ingest.py`, `parse.py`, `resolve.py` — PDF write path (targeted sections)
- `alembic/versions/0001_initial_schema.py`, `0003_add_admin_jobs.py`, `0008_side_enum_and_argument_status.py`, `0025_rename_participant_title_to_descriptor.py` — enum-creation and rename precedent
- `api/services/arguments.py`, `admin_jobs.py`, `admin_arguments.py`, `admin_dev.py` — read-path and reset-tool call sites
- `api/schemas/utterance.py` — public API contract
- `tests/conftest.py`, `pipeline/tests/conftest.py` — leak-detection tripwire and TRUNCATE lists
- `pipeline/tests/test_parse.py`, `test_pipeline_run.py` — existing test patterns for strategy/run-id verification
- `.planning/notes/import-architecture-diagnosis.md`, `provenance-and-trust-model.md`, `import-entity-sketch.md` — design basis (canonical refs)
- `.planning/FIXTURES.md` — confirms `reset_to_fixture`'s fixture set is 100% corpus-sourced
- `alembic current` / `alembic heads` (bash) — confirmed head `0025`
- `pip show sqlalchemy alembic asyncpg psycopg2-binary` (bash) — confirmed installed versions

### Secondary (MEDIUM confidence)

None — no external web sources were needed; every claim traces to a file read or command run this session.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in active use; versions confirmed via `pip show`.
- Architecture: HIGH — grain decision, method-mapping, and the `oyez_transcript_id` pitfall are all grounded in direct reads of the actual write/read paths, not inference from the design notes alone.
- Pitfalls: HIGH — all three pitfalls were found by cross-referencing the design notes against actual code (not merely restating the design notes).

**Research date:** 2026-08-17
**Valid until:** 30 days (stable in-repo schema domain; no external library churn risk) — but re-verify `alembic current` immediately before planning execution if any other phase's migration has landed in the interim.
