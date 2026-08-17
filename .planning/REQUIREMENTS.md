# Requirements: SCOTUS Chat — v1.8 Import & Provenance Re-model

**Defined:** 2026-08-17
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

**Design basis:** `.planning/notes/import-architecture-diagnosis.md`, `provenance-and-trust-model.md`, `import-entity-sketch.md`.

## v1 Requirements

Requirements for milestone v1.8. Each maps to exactly one roadmap phase.

### Provenance (PROV)

- [x] **PROV-01**: Every import unit records a declared `source` (operator / corpus / pdf_pipeline / seed)
- [x] **PROV-02**: Every import unit records a declared `method` (manual / direct / normalized / rule_based / llm_corrective)
- [x] **PROV-03**: `import_run` generalizes `pipeline_run` as the lineage backbone; utterances reference `import_run`
- [x] **PROV-04**: External-source lineage (oyez ids) captured on `import_run.external_id`
- [ ] **PROV-05**: Every import path stamps `source` / `method` / `external_id` at write time (mapping: `convokit_import → corpus/direct`, `rule_based → pdf_pipeline/rule_based`, `llm_corrective → pdf_pipeline/llm_corrective`), verified by re-seeding a fixture and reading provenance directly off the rows _(reframed 2026-08-17: the project DB is disposable/fixture-reseedable, so provenance is guaranteed by write-time stamping rather than in-migration backfill of legacy rows — see `phases/47-provenance-foundation/47-CONTEXT.md` D-03)_
- [x] **PROV-06**: PDF-only fields (`pdf_path` / `pdf_url`) are nullable and populated only for `pdf_pipeline` source

### Trust & Lifecycle (TRUST)

- [ ] **TRUST-01**: Every argument carries a `trust_tier` (verified / trusted / provisional / uncertain) derived from provenance + review state
- [ ] **TRUST-02**: An argument's `trust_tier` is the floor rollup of its utterances and participants, materialized and recomputed on change
- [ ] **TRUST-03**: A newly imported argument is born a `candidate` (not public) with its tier set on arrival
- [ ] **TRUST-04**: Promotion to published is a single gate (`published_at`); publish is hard-blocked while any UNCERTAIN element remains
- [ ] **TRUST-05**: Operator can override the publish block with a deliberate, logged per-argument acknowledgment

### Review Model (REVIEW)

- [ ] **REVIEW-01**: Operator-editable rows (person names, argument participants) carry a four-state `review_state` (unreviewed / needs_review / operator_confirmed / operator_edited)
- [ ] **REVIEW-02**: Re-import records a discrepancy for operator review instead of overwriting an equal-or-higher-authority value
- [ ] **REVIEW-03**: Operator review queue lists items needing review, filterable by trust tier / review state
- [ ] **REVIEW-04**: Operator can resolve a review item (confirm or edit), advancing its `review_state` and recomputing trust
- [ ] **REVIEW-05**: `name_needs_review` / `name_extraction_metadata` generalized into the unified review_state + provenance record (no parallel mechanism)

### Unified Import Path (IMPORT)

- [ ] **IMPORT-01**: Corpus import writes `import_run` directly (source=corpus) without fabricating PDF-pipeline artifacts
- [ ] **IMPORT-02**: PDF pipeline path adapts to `import_run` as one strategy among peers
- [ ] **IMPORT-03**: `admin_job` references an `import_run` rather than inventing one; corpus CLI batch needs no admin_job
- [ ] **IMPORT-04**: Re-import is idempotent — re-running yields the same result and never clobbers operator-authored values
- [ ] **IMPORT-05**: Authority ordering (operator > corpus > pdf/rule > pdf/llm) governs overwrite decisions on every writer

### Design System & Noun Alignment (DS)

- [ ] **DS-01**: Public route/noun aligned to "arguments" (`/cases` → arguments) with redirects preserving existing URLs
- [ ] **DS-02**: Shared component library extracted for reused UI (absorbs backlog 999.4)
- [ ] **DS-03**: Design tokens (color / type / spacing) established as the visual foundation (absorbs backlog 999.8)
- [ ] **DS-04**: Arguments listing style decided and implemented (absorbs backlog 999.6)

## v2 / Future Requirements

- **DEPLOY-01**: Application deployed to Digital Ocean App Platform (carried forward, not in v1.8)
- **DEPLOY-03**: Continuous deployment from GitHub main branch (carried forward, not in v1.8)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Public-facing trust/tier display | Trust is operator-facing only; showing it publicly risks the apolitical framing constraint |
| Literal separate staging table for candidates | Decided against — status-based staging (candidate rows in `arguments`) gives the same guarantee without duplicating schema |
| Person-dedup mismatch across justice-import tools (White/Black/Clark/Douglas) | Known deferred item from v1.7 Phase 42; kept out to prevent scope creep, revisit as its own phase |
| Deployment (DEPLOY-01/03) | Carried forward to a later milestone; not part of the import re-model |

## Traceability

Mappings confirmed by the v1.8 roadmap (`.planning/ROADMAP.md`), created 2026-08-17. Every v1 requirement maps to exactly one phase; the five requirement categories map 1:1 onto five dependency-ordered phases (47–51).

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 47 | Complete |
| PROV-02 | Phase 47 | Complete |
| PROV-03 | Phase 47 | Complete |
| PROV-04 | Phase 47 | Complete |
| PROV-05 | Phase 47 | Pending |
| PROV-06 | Phase 47 | Complete |
| TRUST-01 | Phase 48 | Pending |
| TRUST-02 | Phase 48 | Pending |
| TRUST-03 | Phase 48 | Pending |
| TRUST-04 | Phase 48 | Pending |
| TRUST-05 | Phase 48 | Pending |
| REVIEW-01 | Phase 49 | Pending |
| REVIEW-02 | Phase 49 | Pending |
| REVIEW-03 | Phase 49 | Pending |
| REVIEW-04 | Phase 49 | Pending |
| REVIEW-05 | Phase 49 | Pending |
| IMPORT-01 | Phase 50 | Pending |
| IMPORT-02 | Phase 50 | Pending |
| IMPORT-03 | Phase 50 | Pending |
| IMPORT-04 | Phase 50 | Pending |
| IMPORT-05 | Phase 50 | Pending |
| DS-01 | Phase 51 | Pending |
| DS-02 | Phase 51 | Pending |
| DS-03 | Phase 51 | Pending |
| DS-04 | Phase 51 | Pending |

**Coverage:**

- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-17*
*Last updated: 2026-08-17 — v1.8 roadmap created; traceability confirmed (25/25 mapped to Phases 47–51, no orphans, no duplicates)*
