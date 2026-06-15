# Requirements: SCOTUS Chat

**Defined:** 2026-06-15
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1.1 Requirements

Requirements for the Operator Admin Interface milestone. Phases continue numbering from v1.0 (Phase 5+).

### Auth

- [ ] **AUTH-01**: Operator can log in at `/admin/login` with username and password stored in env vars; invalid credentials show an error
- [ ] **AUTH-02**: All `/admin/*` routes (pages and API endpoints) redirect unauthenticated requests to `/admin/login` before any content renders
- [ ] **AUTH-03**: Operator can log out and session is invalidated immediately

### Pipeline Runner

- [ ] **PIPE-12**: Operator can start a new pipeline run by entering a transcript PDF URL
- [ ] **PIPE-13**: Operator can start a new pipeline run by uploading a local PDF file
- [ ] **PIPE-14**: A running pipeline displays step status (Ingest / Parse / Resolve) and auto-advances when each step completes without discrepancies
- [ ] **PIPE-15**: Pipeline pauses after a step when discrepancies exist and displays them for operator review before continuing
- [ ] **PIPE-16**: Operator can confirm or correct speaker alias matches during resolve review; confirmed matches are saved to the alias table
- [ ] **PIPE-17**: Pipeline job state is persisted to DB so the operator can close the browser and resume an in-progress run

### People

- [ ] **PEOPLE-01**: Operator can view all people in a directory listing
- [ ] **PEOPLE-02**: Operator can filter the directory to show only people with one or more missing metadata fields
- [ ] **PEOPLE-03**: Operator can edit a person's name, role, bio text, photo URL, and tenure dates
- [ ] **PEOPLE-04**: After a pipeline run completes resolve, operator can review that argument's resolved participants and fill in missing metadata inline

## v1.2 Requirements

Deferred to next milestone.

### Deployment

- **DEPLOY-01**: Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres)
- **DEPLOY-03**: Continuous deployment from GitHub main branch

### Pipeline Enrichment

- **ENRICH-01**: Pipeline step 4 (Enrich) — bio text, photo URL, tenure dates from Oyez/FJC for each argument participant
- **ENRICH-02**: Bio schema uniform across all speakers — same fields and depth for Justices and advocates
- **ENRICH-03**: Bio cards render in the UI, linked from speaker avatars

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSE / real-time log streaming | PgBouncer transaction mode makes this structurally difficult; polling is sufficient |
| Celery / Redis task queue | Two new infra components for one operator processing a handful of arguments per month |
| Bulk import | Batching obscures per-argument discrepancy review, which is inherently sequential |
| Inline utterance editing | Directly violates the immutable-PDF / regenerate-from-source principle |
| RBAC / multi-user admin | Single operator; no current beneficiary |
| Analytics dashboard | Politically interpretable data; contradicts non-editorial principle |
| Citation pipeline step (CITE-01/02) | Not in scope for v1.1; schema already supports it |
| Automated enrichment (Oyez/FJC API) | Manual people editor serves this for v1.1; automated enrichment deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 6 | Pending |
| AUTH-02 | Phase 6 | Pending |
| AUTH-03 | Phase 6 | Pending |
| PIPE-12 | Phase 7 | Pending |
| PIPE-13 | Phase 7 | Pending |
| PIPE-14 | Phase 7 | Pending |
| PIPE-15 | Phase 7 | Pending |
| PIPE-16 | Phase 7 | Pending |
| PIPE-17 | Phase 7 | Pending |
| PEOPLE-01 | Phase 8 | Pending |
| PEOPLE-02 | Phase 8 | Pending |
| PEOPLE-03 | Phase 8 | Pending |
| PEOPLE-04 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

**Note on Phase 5:** Phase 5 (Admin Foundation) is a pure infrastructure phase — Alembic migration 0003 (`admin_jobs` table) and `api/routers/admin.py` (FastAPI admin router). It carries no REQUIREMENTS.md REQ-IDs by design because it delivers no operator-observable feature; it exists solely as a prerequisite for Phase 6 (auth) and Phase 7 (pipeline runner).

---
*Requirements defined: 2026-06-15*
*Last updated: 2026-06-15 after v1.1 roadmap created (Phases 5–8)*
