# Phase 47: Provenance Foundation - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Provenance becomes a first-class, declared attribute of every import unit. A new
`import_run` table generalizes today's `pipeline_run` as the single lineage
backbone, carrying a declared `source` (operator / corpus / pdf_pipeline / seed)
and `method` (manual / direct / normalized / rule_based / llm_corrective) plus
external-source lineage (`external_id` for oyez transcript ids). Utterances
reference `import_run` instead of `pipeline_run`. PDF-only fields (`pdf_path` /
`pdf_url`) become nullable and are populated only for `pdf_pipeline` runs, so the
corpus path stops fabricating them. Alembic is the sole DDL authority.

**In scope:** `import_run` table + `source`/`method` vocab + `external_id` lineage
+ nullable PDF fields + utterance FK repoint + import paths stamping provenance at
write time + drop of the redundant `utterance.strategy` column.

**Out of scope (later phases):**
- `trust_tier` materialized rollup, `candidate` status, publish gate → Phase 48
- `review_state`, discrepancy recording, operator review queue → Phase 49
- `admin_job` re-point to `import_run`, corpus-writes-`import_run`-directly path
  rework → later "Path rework" phase
</domain>

<decisions>
## Implementation Decisions

### Migration Strategy
- **D-01:** **Clean rebuild, not in-place backfill.** The project database holds no
  data that must be retained (dev-stage; corpus is re-importable from ConvoKit,
  and Phase 43 shipped a reset-to-fixture tool). The migration drops
  `pipeline_runs` and creates `import_run` fresh with the new shape rather than
  ALTER-and-backfill-existing-rows. No in-migration `strategy → source/method`
  translation step is required. — **Reversibility:** one-way — undoing it needs a
  reverse Alembic migration; the disposable DB softens the blast radius but the
  DDL contract change (`import_run` table, utterance FK) is still a schema
  migration.
- **D-02:** **The `strategy → source/method` mapping lives in the go-forward import
  code, not a migration backfill.** Corpus (`import_convokit`) and PDF
  (ingest/parse/resolve) paths are updated to stamp `source` / `method` /
  `external_id` at write time. Provenance is correct by construction on every new
  row, verified by re-seeding a fixture and reading provenance directly off the
  rows.

### Requirement Change (needs roadmap follow-through)
- **D-03:** **PROV-05 is reframed from "backfill existing rows deterministically,
  no data loss" to go-forward provenance.** New intent: *every import path stamps
  `source`/`method`/`external_id` at write time, verified by re-seeding a fixture
  and reading provenance directly off the rows.* Success criterion #4 (the
  backfill/row-count-unchanged criterion) is superseded by this write-time
  guarantee. This matches how the DB actually behaves now (disposable,
  fixture-reseedable). **DONE 2026-08-17 (operator-approved):** REQUIREMENTS.md
  (PROV-05) and ROADMAP.md (Phase 47 goal + success criterion #4) edited to
  reflect this. — **Reversibility:** costly — reverting
  to a true in-place backfill requirement would re-introduce migration logic and
  a row-count-preservation constraint the current DB no longer needs.

### admin_jobs
- **D-04:** **`admin_jobs` is NOT touched in Phase 47.** The `admin_job →
  import_run` re-point (and the corpus-writes-`import_run`-directly rework) is
  deferred to the later "Path rework" phase. Phase 47 keeps its migration tight:
  `import_run` + provenance + `external_id` + nullable PDF fields + utterance FK
  repoint only.

### utterance.strategy
- **D-05:** **Drop `utterance.strategy` in this migration.** The column is
  NOT-NULL today and now redundant — utterances inherit provenance from their
  `import_run` (`source`/`method`). Removed as part of this migration for a clean
  end-state. — **Reversibility:** one-way — column drop; re-adding needs a
  migration and a re-population source.

### Verification guardrail
- **D-06:** The fixture re-seed used to verify write-time provenance MUST exercise
  **all** provenance combinations the code can produce — at minimum
  `corpus/direct`, `pdf_pipeline/rule_based`, `pdf_pipeline/llm_corrective` — so
  verification is not blind to a path the fixtures don't cover. If the existing
  4-fixture set (Phase 41) doesn't cover every combination, that gap must be
  surfaced during research/planning.

### Carried Forward (locked by design notes — do NOT re-litigate)
- `import_run` replaces `pipeline_run` as the lineage backbone; utterances FK to
  `import_run` (`import_run_id`).
- `source` closed vocabulary: `operator` / `corpus` / `pdf_pipeline` / `seed`.
- `method` closed vocabulary: `manual` / `direct` / `normalized` / `rule_based` /
  `llm_corrective`.
- `external_id` is populated from today's `oyez_transcript_id` (lives on
  `arguments`, per `api/models/models.py:309`); `oyez_case_id` / `oyez_speaker_id`
  remain where they are.
- `pdf_path` / `pdf_url` become nullable, populated only for `pdf_pipeline` runs;
  corpus runs carry no fabricated PDF artifacts.
- Provenance grain: the go-forward mapping is `convokit_import → corpus/direct`,
  `rule_based → pdf_pipeline/rule_based`, `llm_corrective → pdf_pipeline/llm_corrective`.
  Research must confirm what `source`/`method` the PDF-lifecycle ingest/resolve
  steps (which carry no `strategy` today) should stamp.

### Claude's Discretion
- Enum representation for `source`/`method` (native PG enum type vs. varchar +
  CHECK constraint) is left to research/planning — a technical implementation
  detail. Note the trade-off: native PG enums match the existing `SAEnum` pattern
  in `api/models/models.py` but cannot drop values later; varchar+CHECK is easier
  to evolve as the milestone adds vocabulary.
- Whether `import_run` keeps today's per-step grain (one row per
  ingest/parse/resolve) or collapses to per-argument — the row-count-preservation
  constraint that would have forced per-step is gone (D-01), so this is now an
  open modeling choice for research. The design notes lean per-argument; the
  utterance FK must be preserved either way.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design (the worked-out model — read first)
- `.planning/notes/import-architecture-diagnosis.md` — Why the re-model exists; the
  root cause (schema encodes the PDF pipeline as the shape of reality) and the
  agreed "unified import with provenance as discriminator" direction.
- `.planning/notes/provenance-and-trust-model.md` — The provenance vocabulary
  (`source` / `method` / lineage / `review_state`), authority ladder, and the
  old→new backfill mapping table. **Column names are illustrative — Alembic is the
  sole DDL authority.**
- `.planning/notes/import-entity-sketch.md` — The target ER sketch; the
  `IMPORT_RUN` / `ARGUMENT` / `UTTERANCE` / `ADMIN_JOB` shapes with [NEW]/[CHG]/[RET]
  annotations. Note Phase 47 delivers only the `import_run` + provenance slice;
  `trust_tier`, `candidate`, `review_state` are later phases.

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — PROV-01 … PROV-06. **PROV-05 is being reframed
  (D-03) — edit before phase close.**
- `.planning/ROADMAP.md` §"Phase 47: Provenance Foundation" — goal + success
  criteria. **Success criterion #4 is superseded by D-03 — edit before phase close.**

### Code touch points (verified during scout)
- `api/models/models.py` — `PipelineRun` (`:387`, PDF-centric columns, `strategy`
  at `:403`), `Utterance` (`:416`, `pipeline_run_id` FK at `:421`, `strategy`
  NOT-NULL at `:429`), `oyez_transcript_id` (`:309`), existing `SAEnum` pattern for
  PG enums.
- `pipeline/commands/import_convokit.py` — corpus path; fabricates a
  `PipelineRun` with `strategy="convokit_import"` (`:563`, `:567`) purely because
  `Utterance.pipeline_run_id` is NOT-NULL. This is the fabrication to eliminate.
- `pipeline/commands/ingest.py:528`, `parse.py:256`, `resolve.py:145` — PDF-path
  `PipelineRun` creation, one row per step (ingest/parse/resolve carry no
  `strategy`; only parse does).
- `CLAUDE.md` — architecture rules: pipeline offline-only; Alembic sole DDL
  authority; public `/cases` filters on `published_at`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 43 reset-to-fixture tool + the 4-fixture set (Phase 41): the mechanism for
  re-seeding fixtures through the real import/publish pipeline — this is the
  verification vehicle for D-02/D-06 (re-seed, then read provenance off rows).
- Existing `SAEnum(..., values_callable=...)` pattern in `api/models/models.py`
  for declaring PG enums, if native enums are chosen for `source`/`method`.

### Established Patterns
- `pipeline_runs` are created **per step** today (ingest/parse/resolve are separate
  rows per argument); only parse rows carry a `strategy`. Corpus imports create a
  single run per argument. Research must decide how `source`/`method` attach across
  these grains.
- Alembic is the sole DDL authority (CLAUDE.md) — all schema changes flow through a
  migration; no ad-hoc DDL.

### Integration Points
- `Utterance.pipeline_run_id` FK → repoint to `import_run.id` (`import_run_id`).
- Both import paths (`import_convokit.py`, ingest/parse/resolve) write provenance
  at row creation.
- `admin_jobs` deliberately untouched this phase (D-04).
</code_context>

<specifics>
## Specific Ideas

- Operator confirmed the current DB is disposable — "no data in the project
  database that needs to be retained." This is the pivot that turned a
  backfill-heavy migration into a clean rebuild + go-forward provenance (D-01,
  D-02, D-03).
- Verification should be positive and testable: re-seed a fixture, read the row,
  assert the provenance — not the absence of a backfill (D-06).
</specifics>

<deferred>
## Deferred Ideas

- `admin_job → import_run` re-point and corpus-writes-`import_run`-directly →
  later "Path rework" phase (D-04).
- `trust_tier`, `candidate` status, publish gate → Phase 48.
- `review_state`, discrepancy recording, operator review queue → Phase 49.
- Optional `import_batch` grouping for corpus term-range runs (design notes flag it
  as a possible later grouping; per-argument is the current lean).
</deferred>

---

*Phase: 47-provenance-foundation*
*Context gathered: 2026-08-17*
