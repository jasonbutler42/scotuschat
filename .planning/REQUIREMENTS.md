# Requirements: SCOTUS Chat — v1.7 Corpus Fidelity & Resolve Rework

**Defined:** 2026-07-29
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1 Requirements

### Corpus Fidelity Audit

- [ ] **CORPUS-12**: A 4-argument fixture set is identified from the ~7,800-argument ConvoKit dataset: one canonical audit fixture selected for structural complexity (most advocates/speakers, consolidated multi-docket case, longest transcript, or similar signals) that Phase 42 diffs, plus three additional arguments selected for publish/pipeline-state variety (e.g. unpublished/DRAFT, published, mid-pipeline) to support Phase 43's reset tool and Phase 45's bug testing — the full set confirmed with the user before use
- [ ] **CORPUS-13**: A field-by-field comparison exists between the fixture's raw ConvoKit source data and what actually lands in our DB (cases, arguments, utterances, people, argument_participants, court_tenures) after `import-convokit`, surfacing any fields dropped, mis-mapped, or silently defaulted
- [ ] **CORPUS-14**: Every gap found in CORPUS-13 for the fixture is fixed in the corpus importer and verified by re-importing the fixture cleanly (fixes apply to this one fixture's import path this milestone; full-corpus backfill is out of scope)

### Dev Reset Tool

- [ ] **DEVTOOL-01**: Operator can trigger a "Reset to Fixture" action from the admin panel that wipes all arguments, utterances, people, court_tenures, and argument_participants, then reseeds exactly the CORPUS-12 fixture set (all 4 arguments) plus their associated people
- [ ] **DEVTOOL-02**: The reset action is hard-gated so it cannot execute against a real/production environment (e.g. explicit environment check), given its fully destructive nature

### Resolve Table Rework

- [ ] **RESOLVE-01**: Resolve table renders 5 columns — Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor — with no separate Action column; row actions (select/change person) live inside the Resolved As cell
- [ ] **RESOLVE-02**: Bench/Advocate is a two-button segmented toggle (only one active) instead of a `<select>` dropdown
- [ ] **RESOLVE-03**: Argument Role is a real writable dropdown for advocate rows (Petitioner's Counsel / Respondent's Counsel / select role), while remaining a locked, tenure-derived value for Bench rows
- [ ] **RESOLVE-04**: The Title column is renamed Descriptor and always renders (shows "–" for Bench rows) instead of being conditionally hidden
- [ ] **RESOLVE-05**: Every column (Resolved As, Bench/Advocate, Argument Role, Descriptor) shows a consistent "Extracted: ..." hint of the raw extracted value
- [ ] **RESOLVE-06**: A resolved, tenure-valid Bench row shows a lock icon signaling its role is system-derived and not editable, distinct from the existing "Missing tenure" warning state

### Bug Fixes

- [ ] **BUG-01**: An unpublished argument is not visible in the `/cases/` list and is not directly accessible by URL (both listing and direct-access are gated on publish status)
- [ ] **BUG-02**: The speaker popover's scrollbar renders flush inside the card's visible rounded boundary instead of outside it, on long/expanded content

## v2 Requirements

_(None deferred from this milestone's scope — all four target features are in v1 above.)_

## Out of Scope

| Feature | Reason |
|---------|--------|
| Deployment to Digital Ocean App Platform (DEPLOY-01, DEPLOY-03) | Deferred — remains in PROJECT.md Requirements > Active, untouched this milestone; the operator wants pipeline/data confidence before shipping |
| Full-corpus backfill of any CORPUS-14 fixes across all ~7,800 arguments | Explicitly scoped to the single complexity fixture this milestone (not the other 3 state-variety fixtures); broader rollout is future work once the fixture proves the fix |
| Renaming "Case" to "Argument" across DB schema, API routes, and frontend | Cross-cutting rename (DB model, `/cases/` routes, corpus-loader naming) surfaced during Phase 41 discuss; genuinely correct observation but out of scope for this milestone — candidate for its own future phase/milestone |
| 999.x backlog review (999.2–999.8) | Separate `/gsd-review-backlog` concern, not part of this milestone's scope |
| Reset tool as a permanent operator-facing production feature | Built as a dev-only iteration tool for this milestone; not intended to ship as a real admin feature without further design/safety review |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORPUS-12 | Phase 41 | Pending |
| CORPUS-13 | Phase 42 | Pending |
| CORPUS-14 | Phase 42 | Pending |
| DEVTOOL-01 | Phase 43 | Pending |
| DEVTOOL-02 | Phase 43 | Pending |
| RESOLVE-01 | Phase 44 | Pending |
| RESOLVE-02 | Phase 44 | Pending |
| RESOLVE-03 | Phase 44 | Pending |
| RESOLVE-04 | Phase 44 | Pending |
| RESOLVE-05 | Phase 44 | Pending |
| RESOLVE-06 | Phase 44 | Pending |
| BUG-01 | Phase 45 | Pending |
| BUG-02 | Phase 45 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13 ✓
- Unmapped: 0 ✓
- Duplicated across phases: 0 ✓

**Phase distribution:**

| Phase | Requirements | Count |
|-------|--------------|-------|
| 41. Canonical Corpus Fixture Selection | CORPUS-12 | 1 |
| 42. Corpus Import Fidelity Diff & Fix | CORPUS-13, CORPUS-14 | 2 |
| 43. Dev-Only Reset to Fixture | DEVTOOL-01, DEVTOOL-02 | 2 |
| 44. Resolve Table Rework | RESOLVE-01–06 | 6 |
| 45. Deferred UI Bug Fixes | BUG-01, BUG-02 | 2 |

---
*Requirements defined: 2026-07-29*
*Last updated: 2026-07-29 after roadmap creation (Phases 41–45 mapped, 13/13 coverage); CORPUS-12/DEVTOOL-01 widened to a 4-fixture set during Phase 41 discuss-phase*
