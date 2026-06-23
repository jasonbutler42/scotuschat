# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- 🚧 **v1.2 Pre-Launch Polish** — Phases 9–14 (in progress)

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

### 🚧 v1.2 Pre-Launch Polish (In Progress)

**Milestone Goal:** Complete admin tooling and public experience needed before the site is ready to deploy — structured people data, unified navigation, argument editing, people admin improvements, and the speaker popover card.

- [x] **Phase 9: People Data Model Migration** - Add structured name fields and appointing president/party to the people schema (completed 2026-06-19)
- [x] **Phase 10: Unified Navigation** - Admin and public pages share one top navigation component (completed 2026-06-22)
- [x] **Phase 11: Argument Metadata Editing** - Operator can correct case title, docket, and date before resolving (completed 2026-06-22)
- [ ] **Phase 12: People Admin Improvements** - Image upload, delete orphaned records, and merge duplicate people
- [ ] **Phase 13: Ingestion Flow Polish** - Fix progress indicators, typeahead, and incomplete filter
- [ ] **Phase 14: Speaker Popover Card** - Avatar click shows bench speaker details with photo, role, and tenure

## Phase Details

### Phase 9: People Data Model Migration

**Goal**: The people schema carries structured name parts and appointing president/party so all downstream features can read and display that data
**Depends on**: Phase 8 (people editor exists; migration extends it)
**Requirements**: PEOP-01, PEOP-02
**Success Criteria** (what must be TRUE):

  1. Operator can type a first name, last name, middle name, and suffix into separate fields on a person edit form and save them
  2. Operator can type an appointing president name and select a party affiliation on a person edit form and save them
  3. Existing full_name values are preserved after the migration runs; no person record loses its resolution anchor
  4. All new fields accept null/empty and do not break existing people records that have not been filled in

**Plans**: 3/3 plans complete

- [x] 09-01-PLAN.md — Migration 0006 + Person ORM + PersonDetail/PersonUpdate schema fields
- [x] 09-02-PLAN.md — Service layer: _derive_full_name (TDD), update_person derivation, get_person_detail dict, list_people sort
- [x] 09-03-PLAN.md — SvelteKit edit form: name-parts grid + Appointment section + server action (human verify checkpoint)

### Phase 10: Unified Navigation

**Goal**: Every page — admin and public — shares the same top navigation header component so the site feels cohesive and navigation is consistent
**Depends on**: Nothing (zero data dependencies; can land in any order)
**Requirements**: NAV-01
**Success Criteria** (what must be TRUE):

  1. Visitor on a public argument page can see a top navigation bar with a link to the public case list and to the admin area
  2. Operator on any admin page sees the same navigation bar with the same links
  3. The navigation component is a single shared Svelte component — no duplicate markup in admin and public layouts

**Plans**: 1/1 plans complete

Plans:

- [x] 10-01-PLAN.md — Create shared TopNav.svelte (variant prop) and wire both root and admin layouts to it

**UI hint**: yes

### Phase 11: Argument Metadata Editing

**Goal**: Operator can correct a pending argument's title, docket number, and argued date from the admin area before it is published
**Depends on**: Phase 9 (no schema dependency; can proceed after Phase 9 for sequencing clarity)
**Requirements**: ARG-01, ARG-02
**Success Criteria** (what must be TRUE):

  1. Operator can open a pending argument in the admin area and edit its case title, docket number, and argued date, then save successfully
  2. Changes to case title, docket, and date are reflected immediately in the admin view after saving
  3. After an argument's resolved_at is set, its title, docket, and date fields are displayed as read-only and cannot be submitted for editing

**Plans**: 4/4 plans complete

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Migration 0007 (published_at) + Argument ORM column + get_cases visibility gate swap

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — Backend: admin_arguments schemas + service (slug/docket collision, publish guards) + admin router routes

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 11-03-PLAN.md — SvelteKit /admin/arguments list + [id] edit pages + TopNav Arguments link
- [x] 11-04-PLAN.md — Job detail page argument preview card + Ready-to-publish CTA

**UI hint**: yes

### Phase 12: People Admin Improvements

**Goal**: Operator can upload a profile photo, delete an orphaned person record, and merge duplicate person records — all from the admin people directory
**Depends on**: Phase 9 (structured name fields available in the edit form)
**Requirements**: PADM-01, PADM-02, PADM-03, PADM-04
**Success Criteria** (what must be TRUE):

  1. Operator can upload a photo file from their computer and have it stored on DO Spaces; the person's avatar updates to show the uploaded photo
  2. Operator can enter a photo URL as an alternative to file upload; the person's avatar updates to the URL-sourced image
  3. Operator can delete a person record that has no utterances, aliases, or appearances; the person no longer appears in the directory
  4. Operator can select a source and a target person and initiate a merge; all utterances, aliases, and appearances transfer to the target before the source is deleted
  5. Before committing a merge, the operator sees a count of utterances, aliases, and appearances that will transfer

**Plans**: 1/4 plans executed

Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Backend services + schemas: spaces upload_photo_to_spaces, admin_people merge/preview/orphan-delete/photo functions, MergeRequest/MergePreview

**Wave 2** *(blocked on Wave 1)*

- [ ] 12-02-PLAN.md — admin.py 4 endpoints (photo/merge-preview/merge/delete) + main.py StaticFiles mount

**Wave 3** *(blocked on Wave 2)*

- [ ] 12-03-PLAN.md — SvelteKit +page.server.ts photo/merge/delete actions + extended load + merge-preview proxy +server.ts

**Wave 4** *(blocked on Wave 3)*

- [ ] 12-04-PLAN.md — +page.svelte photo widget + merge section + delete section (human-verify checkpoint)

**UI hint**: yes

### Phase 13: Ingestion Flow Polish

**Goal**: The pipeline runner UI accurately reflects job state at all times and gives the operator correct tools to act on incomplete jobs
**Depends on**: Nothing (independent fixes to the existing pipeline runner)
**Requirements**: PIPE-18, PIPE-19, PIPE-20
**Success Criteria** (what must be TRUE):

  1. Step status badges on a running pipeline job never show stale or incorrect state — the displayed step matches the actual DB state
  2. Operator typing in the speaker alias typeahead sees relevant candidate matches and can select one; the selected value is applied correctly
  3. Operator toggling the incomplete filter on the pipeline list sees only jobs that require their action; toggling it off restores the full list

**Plans**: TBD
**UI hint**: yes

### Phase 14: Speaker Popover Card

**Goal**: Visitors can click any speaker's avatar on an argument page to see a floating card with the speaker's identity and role details
**Depends on**: Phase 9 (structured names and appointing president data), Phase 12 (profile photos via Spaces)
**Requirements**: PUB-01, PUB-02, PUB-03, PUB-04
**Success Criteria** (what must be TRUE):

  1. Visitor can click any speaker avatar on an argument page and a popover card opens showing the speaker's name and role
  2. Bench speaker popovers additionally show tenure dates and the name of the appointing president (no party affiliation shown)
  3. The popover shows the speaker's profile photo when one is available, or a styled initials fallback when it is not
  4. Visitor can dismiss the popover by pressing the Escape key; keyboard-only users can reach and dismiss the popover without a mouse

**Plans**: TBD
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
| 9. People Data Model Migration | v1.2 | 3/3 | Complete    | 2026-06-19 |
| 10. Unified Navigation | v1.2 | 1/1 | Complete   | 2026-06-22 |
| 11. Argument Metadata Editing | v1.2 | 4/4 | Complete   | 2026-06-22 |
| 12. People Admin Improvements | v1.2 | 1/4 | In Progress|  |
| 13. Ingestion Flow Polish | v1.2 | 0/? | Not started | — |
| 14. Speaker Popover Card | v1.2 | 0/? | Not started | — |
