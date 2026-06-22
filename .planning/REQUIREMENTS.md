# Requirements: SCOTUS Chat

**Defined:** 2026-06-18
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1.2 Requirements

Requirements for the Pre-Launch Polish milestone. Each maps to roadmap phases (phases 9–14).

### Navigation

- [x] **NAV-01**: Admin and public pages share the same top navigation component, with links to both the public case list and the admin area visible from either view

### Ingestion & Pipeline

- [ ] **PIPE-18**: Pipeline runner progress indicators accurately reflect step status without stale or incorrect state
- [ ] **PIPE-19**: Typeahead dropdown for speaker alias correction returns correct candidates and responds to operator input correctly
- [ ] **PIPE-20**: Incomplete filter toggle on the pipeline list shows only jobs requiring operator action

### Argument Metadata

- [x] **ARG-01**: Operator can view and edit a pending argument's case title, docket number, and argued date from the admin area
- [ ] **ARG-02**: Argument metadata fields are read-only after `resolved_at` is set

### People Data Model

- [x] **PEOP-01**: Operator can enter and edit structured name fields (first name, last name, middle name, suffix) on a person record in addition to the existing full name
- [x] **PEOP-02**: Operator can enter and edit appointing president name and party affiliation on a person record

### People Admin

- [ ] **PADM-01**: Operator can upload a profile photo file or enter a photo URL; both paths store the image on the server and update the person's photo
- [ ] **PADM-02**: Operator can delete a person record that has no associated utterances, aliases, or appearances
- [ ] **PADM-03**: Operator can merge two person records; all utterances, aliases, and appearances transfer from source to target before the source is deleted
- [ ] **PADM-04**: Merge confirmation shows a count of records that will transfer before the operator commits

### Public Experience

- [ ] **PUB-01**: Visitor can click any speaker's avatar to open a popover card showing the speaker's name and role
- [ ] **PUB-02**: Bench speaker popovers additionally show tenure dates and appointing president
- [ ] **PUB-03**: Speaker popover displays the speaker's profile photo when available, or styled initials as a fallback
- [ ] **PUB-04**: Speaker popover is keyboard accessible and dismissible with the Escape key

## Future Requirements

Deferred to v1.3 and beyond. Tracked but not in current roadmap.

### Deployment

- **DEPLOY-01**: Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres)
- **DEPLOY-03**: Continuous deployment from GitHub main branch

### Advocate Profiles

- **ADV-01**: Visitor can view advocate firm or organization affiliation in speaker popover (requires new people field)

### Enrichment

- **ENRICH-01**: Automated enrichment of person records from Oyez/FJC API

## Out of Scope

| Feature | Reason |
|---------|--------|
| Party affiliation in public popover | Admin metadata only — showing party affiliation publicly risks editorial framing; violates apolitical constraint |
| Image crop in upload flow | `object-fit: cover` handles display; crop adds complexity with no functional benefit at this scale |
| Post-resolve metadata editing | Resolved arguments are published; editing post-publish requires an explicit unpublish + re-resolve workflow (future) |
| AI-generated case summaries | Hard apolitical framing constraint |
| Cross-case justice statistics | Politically interpretable; contradicts non-editorial principle |
| Automated enrichment (Oyez/FJC) | Manual people editor sufficient for v1.2; automation deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 10 | Complete |
| PIPE-18 | Phase 13 | Pending |
| PIPE-19 | Phase 13 | Pending |
| PIPE-20 | Phase 13 | Pending |
| ARG-01 | Phase 11 | Complete |
| ARG-02 | Phase 11 | Pending |
| PEOP-01 | Phase 9 | Complete |
| PEOP-02 | Phase 9 | Complete |
| PADM-01 | Phase 12 | Pending |
| PADM-02 | Phase 12 | Pending |
| PADM-03 | Phase 12 | Pending |
| PADM-04 | Phase 12 | Pending |
| PUB-01 | Phase 14 | Pending |
| PUB-02 | Phase 14 | Pending |
| PUB-03 | Phase 14 | Pending |
| PUB-04 | Phase 14 | Pending |

**Coverage:**

- v1.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after roadmap creation*
