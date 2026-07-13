# Requirements: SCOTUS Chat

**Defined:** 2026-07-12
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1.6 Requirements

Requirements for the v1.6 Backlog Cleanup milestone. Each maps to a roadmap phase (31–40, already numbered via the 2026-07-12 backlog review).

### Data Integrity & Testing

- [ ] **TEST-01**: Full test suite runs without leaking synthetic Person/Argument rows into the shared dev database
- [ ] **TEST-02**: The ~28 identified stale DB-gated test fixtures pass against the current schema (no nullable/enum mismatches)

### People Admin

- [ ] **PADM-05**: Merging or deleting a Justice with CourtTenure rows no longer raises an unhandled 500 (CourtTenure counted in merge preview, transferred on merge, checked on delete)

### Pipeline Reliability

- [ ] **PIPE-27**: Saving argument metadata that collides with an existing `(source_docket, question_number)` returns a clean 409/422 instead of an unhandled 500
- [ ] **PIPE-28**: Clearing `case_name` or `docket_number` to blank is rejected with a validation error instead of corrupting the slug or dedup key
- [ ] **PIPE-29**: Rerunning a locally-uploaded (non-Spaces) pipeline job actually spawns ingest instead of sitting at PENDING forever

### Operator UX

- [ ] **UX-01**: Every extracted-value display (pipeline run pages, argument editor) offers a consistent click-to-copy affordance, disabled when the value is N/A

### People Data Model

- [ ] **PEOPLE-08**: Tenure Seat is captured via a decision-backed UI control instead of unconstrained free text
- [ ] **PEOPLE-09**: Full Name field behavior is resolved per a locked design decision (auto-derived vs. independently editable)

### Public UI

- [ ] **PUB-04**: Justice bench popover shows richer persistent context (birthdate, death date, per-tenure appointing president + party + reason for leaving), presented apolitically

### Documentation

- [ ] **DOCS-01**: A README documents how to start the full local stack (SvelteKit, FastAPI, Postgres) end to end

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Deployment

- **DEPLOY-01**: Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres)
- **DEPLOY-03**: Continuous deployment from GitHub main branch

### Backlog (not yet reviewed)

- **999.2**: Share specific utterances via social media
- **999.3**: Link participant names on job detail page to their edit entries
- **999.4**: Frontend design system — shared component library
- **999.5**: Move speaker avatars to gutters outside the argument body
- **999.6**: Decide on listing style for cases/arguments
- **999.7**: Improve in-argument section navigation
- **999.8**: Figma design system

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Deployment (DEPLOY-01/03) | Deferred to a future milestone; this milestone is a backlog cleanup pass, not the deployment push |
| Remaining 999.x backlog (999.2–999.8) | Capture-only, "Requirements: TBD" — no locked decisions to plan from yet; left for a future `/gsd-review-backlog` pass |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 31 | Pending |
| TEST-02 | Phase 31 | Pending |
| PADM-05 | Phase 32 | Pending |
| PIPE-27 | Phase 33 | Pending |
| PIPE-28 | Phase 34 | Pending |
| PIPE-29 | Phase 35 | Pending |
| UX-01 | Phase 36 | Pending |
| PEOPLE-08 | Phase 37 | Pending |
| PEOPLE-09 | Phase 38 | Pending |
| PUB-04 | Phase 39 | Pending |
| DOCS-01 | Phase 40 | Pending |

**Coverage:**
- v1.6 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-12*
*Last updated: 2026-07-12 after initial definition*
