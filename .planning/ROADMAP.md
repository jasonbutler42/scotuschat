# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- ✅ **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (shipped 2026-06-29)
- 🔄 **v1.4 Admin Completeness** — Phases 18–21 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–4) — SHIPPED 2026-06-15</summary>

**Overview:** Four vertical slices proving the core concept end-to-end — schema and pipeline (Phase 1), speaker resolution (Phase 2), full browseable UI (Phase 3), and WCAG 2.1 AA accessibility (Phase 4).

- [x] Phase 1: Foundation + Proof of Concept (5/5 plans) — completed 2026-06-11
- [x] Phase 2: Speaker Resolution (4/4 plans) — completed 2026-06-12
- [x] Phase 3: Full UI (4/4 plans) — completed 2026-06-13
- [x] Phase 4: Accessibility + Hardening (2/2 plans) — completed 2026-06-15

Full phase details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Operator Admin Interface (Phases 5–8) — SHIPPED 2026-06-18</summary>

**Overview:** Password-protected operator web interface driving the ingestion pipeline step-by-step and managing speaker metadata — making it fast to ingest new arguments without touching the CLI.

- [x] Phase 5: Admin Foundation (2/2 plans) — completed 2026-06-15
- [x] Phase 6: Auth (3/3 plans) — completed 2026-06-16
- [x] Phase 7: Pipeline Runner (8/8 plans) — completed 2026-06-17
- [x] Phase 8: People Editor (6/6 plans) — completed 2026-06-18

Full phase details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Pre-Launch Polish (Phases 9–14) — SHIPPED 2026-06-25</summary>

**Overview:** Complete admin tooling and public experience needed before the site is ready to deploy — structured people data, unified navigation, argument editing, people admin improvements, and the speaker popover card.

- [x] Phase 9: People Data Model Migration (3/3 plans) — completed 2026-06-19
- [x] Phase 10: Unified Navigation (1/1 plan) — completed 2026-06-22
- [x] Phase 11: Argument Metadata Editing (4/4 plans) — completed 2026-06-22
- [x] Phase 12: People Admin Improvements (7/7 plans) — completed 2026-06-24
- [x] Phase 13: Ingestion Flow Polish (3/3 plans) — completed 2026-06-25
- [x] Phase 14: Speaker Popover Card (3/3 plans) — completed 2026-06-25

Full phase details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Speaker Accuracy + Pipeline Confidence (Phases 15–17) — SHIPPED 2026-06-29</summary>

**Overview:** Fix speaker role accuracy on the live popover, make ingestion reliable enough to process large volumes of older transcripts, and give the operator enough pipeline visibility to trust the process.

- [x] Phase 15: Speaker Role Accuracy (4/4 plans) — completed 2026-06-26
- [x] Phase 16: Parser Improvements (2/2 plans) — completed 2026-06-26
- [x] Phase 17: Pipeline UI Polish (3/3 plans) — completed 2026-06-29

Full phase details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

### v1.4 Admin Completeness (Phases 18–21)

- [x] **Phase 18: People Schema + Editor** - is_justice boolean migration, backfill, and conditional editor UI (completed 2026-06-29)
- [x] **Phase 19: Pipeline Reliability** - Duplicate argument prevention and metadata prefill (completed 2026-06-30)
- [x] **Phase 20: Live Pipeline Status** - Real-time polling on list and job detail pages (completed 2026-07-01)
- [ ] **Phase 21: Admin UI Surface** - Delete actions for arguments and pipeline runs; unified admin navigation

## Phase Details

### Phase 18: People Schema + Editor

**Goal**: The people editor accurately represents bench vs. non-bench people — Justices show tenure and appointment fields, non-Justice people do not, and the operator can correct the classification on any record
**Depends on**: Phase 17
**Requirements**: PEOPLE-05, PEOPLE-06, PEOPLE-07
**Success Criteria** (what must be TRUE):

  1. After migration runs, every person with existing tenure records has `is_justice = True` and all others default to `False`
  2. When viewing a Justice's edit page, Role, Court Tenure, and Appointment sections are visible
  3. When viewing a non-Justice person's edit page, Role, Court Tenure, and Appointment sections are absent from the form
  4. Operator can toggle `is_justice` on a person record and the editor immediately reflects the new field visibility on save

**Plans**: 3/3 plans complete
**Wave 1**

- [x] 18-01-PLAN.md — Migration 0010 + Person.is_justice column with tenure-based backfill (PEOPLE-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 18-02-PLAN.md — Wire is_justice through PersonDetail/PersonUpdate/PersonListItem schemas + service read/write (PEOPLE-05, PEOPLE-07)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 18-03-PLAN.md — Editor checkbox + conditional bench sections + save wiring + directory Justice badge (PEOPLE-06, PEOPLE-07)

### Phase 19: Pipeline Reliability

**Goal**: The pipeline cannot silently create duplicate arguments, and argument metadata extracted from the PDF cover is visible to the operator without manual entry
**Depends on**: Phase 17
**Requirements**: PIPE-25, PIPE-26
**Success Criteria** (what must be TRUE):

  1. The database enforces a unique constraint on arguments such that re-running ingest for the same source cannot produce a second Argument row
  2. Operator sees a warning in the pipeline start UI before submitting if a matching argument already exists
  3. After a pipeline run completes parse, case name, docket, and argued date fields are pre-populated from cover extraction results without the operator typing them manually
  4. Operator can still override any pre-populated metadata field before publishing

**Plans**: 4/4 plans complete

Plans:

- [x] 19-01-PLAN.md — Migration 0011: source_docket, cover_metadata JSONB, argued_date nullable, unique constraint (PIPE-25, PIPE-26)
- [x] 19-02-PLAN.md — Pipeline layer: cover extractor docket extraction, ingest source_docket + IntegrityError, parse cover_metadata write-back (PIPE-25, PIPE-26)
- [x] 19-03-PLAN.md — FastAPI layer: MetadataUpdate schema, check-duplicate + metadata PATCH endpoints, ArgumentDetail extension (PIPE-25, PIPE-26)
- [x] 19-04-PLAN.md — UI layer: check-duplicate proxy, start form preflight + banner, job detail metadata card (PIPE-25, PIPE-26)

### Phase 20: Live Pipeline Status

**Goal**: Operator can watch pipeline progress on both the list page and the job detail page without manually reloading — status badges and step cards update automatically while a run is active
**Depends on**: Phase 17
**Requirements**: PIPE-23, PIPE-24
**Success Criteria** (what must be TRUE):

  1. On the pipeline list page, job status badges reflect the current run state and update automatically while any run is active
  2. When the operator navigates away from a running job and returns to the list, the badge shows the correct current state without a manual reload
  3. On the job detail page, step cards (Ingest / Parse / Resolve) update to show step completion in real time while the run is active
  4. Polling stops automatically once the run reaches a terminal state (completed, failed, needs_review)

**Plans**: 1/1 plans complete

Plans:

- [x] 20-01-PLAN.md — Add 1s list-page polling $effect (PIPE-23) + human-verify detail-page live step cards (PIPE-24)

**UI hint**: yes

### Phase 21: Admin UI Surface

**Goal**: Operator can delete mis-created arguments and bad pipeline runs from the admin UI without touching the database, and the admin navigation is visually and structurally consistent with the public navigation
**Depends on**: Phase 17
**Requirements**: ADMIN-01, ADMIN-02, NAV-02
**Success Criteria** (what must be TRUE):

  1. Operator can delete an argument from the admin UI after a confirmation step; the action is blocked if the argument has published utterances
  2. Operator can delete a pipeline run from the admin UI after a confirmation step
  3. The admin header navigation matches the public navigation in visual style and shares the same component or structure (no duplicate ad-hoc markup)
  4. Deleting an argument or pipeline run returns the operator to the correct listing page with the deleted item gone

**Plans**: 3 plans

Plans:

**Wave 1** *(parallel — no shared files)*

- [ ] 21-01-PLAN.md — Argument delete: delete_argument service (FK-ordered cascade) + DELETE endpoint + edit-page two-step confirm UI (ADMIN-01)
- [ ] 21-03-PLAN.md — AdminSubNav component + layout wiring + remove dead TopNav admin variant (NAV-02)

**Wave 2** *(blocked on 21-01 — shares api/routers/admin.py)*

- [ ] 21-02-PLAN.md — Pipeline run delete: delete_job service (admin_job row only) + DELETE endpoint + job-detail two-step confirm UI (ADMIN-02)

**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation + Proof of Concept | v1.0 | 5/5 | Complete | 2026-06-11 |
| 2. Speaker Resolution | v1.0 | 4/4 | Complete | 2026-06-12 |
| 3. Full UI | v1.0 | 4/4 | Complete | 2026-06-13 |
| 4. Accessibility + Hardening | v1.0 | 2/2 | Complete | 2026-06-15 |
| 5. Admin Foundation | v1.1 | 2/2 | Complete | 2026-06-15 |
| 6. Auth | v1.1 | 3/3 | Complete | 2026-06-16 |
| 7. Pipeline Runner | v1.1 | 8/8 | Complete | 2026-06-17 |
| 8. People Editor | v1.1 | 6/6 | Complete | 2026-06-18 |
| 9. People Data Model Migration | v1.2 | 3/3 | Complete | 2026-06-19 |
| 10. Unified Navigation | v1.2 | 1/1 | Complete | 2026-06-22 |
| 11. Argument Metadata Editing | v1.2 | 4/4 | Complete | 2026-06-22 |
| 12. People Admin Improvements | v1.2 | 7/7 | Complete | 2026-06-24 |
| 13. Ingestion Flow Polish | v1.2 | 3/3 | Complete | 2026-06-25 |
| 14. Speaker Popover Card | v1.2 | 3/3 | Complete | 2026-06-25 |
| 15. Speaker Role Accuracy | v1.3 | 4/4 | Complete | 2026-06-26 |
| 16. Parser Improvements | v1.3 | 2/2 | Complete | 2026-06-26 |
| 17. Pipeline UI Polish | v1.3 | 3/3 | Complete | 2026-06-29 |
| 18. People Schema + Editor | v1.4 | 3/3 | Complete    | 2026-06-29 |
| 19. Pipeline Reliability | v1.4 | 5/5 | Complete    | 2026-06-30 |
| 20. Live Pipeline Status | v1.4 | 1/1 | Complete   | 2026-07-01 |
| 21. Admin UI Surface | v1.4 | 0/3 | Planned | - |

## Backlog

See `.planning/BACKLOG.md` for unscheduled items (B-001 through B-012).
