# Requirements: SCOTUS Chat

**Defined:** 2026-06-29
**Milestone:** v1.4 Admin Completeness
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1 Requirements

### People Schema & Editor

- [ ] **PEOPLE-05**: `is_justice` boolean column added to `people` table via Alembic migration; backfilled `True` for any person with existing tenure records
- [ ] **PEOPLE-06**: People editor shows bench-only sections (Role, Court Tenure, Appointment) only when `is_justice` is `True`; hides them entirely for non-justice people
- [ ] **PEOPLE-07**: Operator can toggle `is_justice` on a person record in the people editor

### Admin Data Management

- [ ] **ADMIN-01**: Operator can delete a mis-created argument from the admin UI (with confirmation; blocked if argument has published utterances)
- [ ] **ADMIN-02**: Operator can delete a pipeline run from the admin UI (with confirmation)

### Pipeline Reliability

- [ ] **PIPE-23**: Pipeline list page updates job status badges automatically while any run is active — no manual reload needed
- [ ] **PIPE-24**: Pipeline job detail page updates step cards live while the run is active — operator can watch step progression in real time
- [ ] **PIPE-25**: System enforces a unique DB constraint preventing duplicate arguments; UI warns the operator before starting a new run if a matching argument already exists
- [ ] **PIPE-26**: Argument metadata (case name, docket, argued date) pre-populated from cover extraction results visible to operator during/after the pipeline run

### Admin Navigation

- [ ] **NAV-02**: Admin header navigation unified with public navigation in style and component structure

## v2 Requirements

- **DEPLOY-01**: Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres)
- **DEPLOY-03**: Continuous deployment from GitHub main branch

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend design system / inline CSS refactor | Deliberately deferred to v1.5 — reward after admin completeness |
| Public view design changes | Deferred to post-deployment milestone |
| Deployment | Deferred to its own milestone after admin and design system work |
| Full CRUD for all reference tables | Not needed — is_justice flag + conditional editor handles the bench/non-bench distinction without exposing role type management |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PEOPLE-05 | TBD | Pending |
| PEOPLE-06 | TBD | Pending |
| PEOPLE-07 | TBD | Pending |
| ADMIN-01 | TBD | Pending |
| ADMIN-02 | TBD | Pending |
| PIPE-23 | TBD | Pending |
| PIPE-24 | TBD | Pending |
| PIPE-25 | TBD | Pending |
| PIPE-26 | TBD | Pending |
| NAV-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 10 ⚠️

---
*Requirements defined: 2026-06-29*
*Last updated: 2026-06-29 after initial definition*
