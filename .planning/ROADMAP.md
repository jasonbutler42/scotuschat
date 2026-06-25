# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- 🔜 **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (planned)

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

### 🔜 v1.3 Speaker Accuracy + Pipeline Confidence — PLANNED

**Milestone Goal:** Fix speaker role accuracy on the live popover, make ingestion reliable enough to process large volumes of older transcripts, and give the operator enough pipeline visibility to trust the process.

- [ ] **Phase 15: Speaker Role Accuracy** - Justice role in popover determined by tenure date lookup; advocate roles stored and editable per argument
- [ ] **Phase 16: Parser Improvements** - Parse step extracts case metadata and advocate sides from transcript PDF
- [ ] **Phase 17: Pipeline UI Polish** - Stage stat cards, pre-populated argument fields, source PDF access

### ✅ v1.2 Pre-Launch Polish — SHIPPED 2026-06-25

**Milestone Goal:** Complete admin tooling and public experience needed before the site is ready to deploy — structured people data, unified navigation, argument editing, people admin improvements, and the speaker popover card.

- [x] **Phase 9: People Data Model Migration** - Add structured name fields and appointing president/party to the people schema (completed 2026-06-19)
- [x] **Phase 10: Unified Navigation** - Admin and public pages share one top navigation component (completed 2026-06-22)
- [x] **Phase 11: Argument Metadata Editing** - Operator can correct case title, docket, and date before resolving (completed 2026-06-22)
- [x] **Phase 12: People Admin Improvements** - Image upload, delete orphaned records, and merge duplicate people (completed 2026-06-23)
- [x] **Phase 13: Ingestion Flow Polish** - Fix progress indicators, typeahead, and incomplete filter (completed 2026-06-24)
- [x] **Phase 14: Speaker Popover Card** - Avatar click shows bench speaker details with photo, role, and tenure (completed 2026-06-25)

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

**Plans**: 7/7 plans complete

Plans:

- [x] 12-05-PLAN.md
- [x] 12-06-PLAN.md
- [x] 12-07-PLAN.md

**Wave 1**

- [x] 12-01-PLAN.md — Backend services + schemas: spaces upload_photo_to_spaces, admin_people merge/preview/orphan-delete/photo functions, MergeRequest/MergePreview

**Wave 2** *(blocked on Wave 1)*

- [x] 12-02-PLAN.md — admin.py 4 endpoints (photo/merge-preview/merge/delete) + main.py StaticFiles mount

**Wave 3** *(blocked on Wave 2)*

- [x] 12-03-PLAN.md — SvelteKit +page.server.ts photo/merge/delete actions + extended load + merge-preview proxy +server.ts

**Wave 4** *(blocked on Wave 3)*

- [x] 12-04-PLAN.md — +page.svelte photo widget + merge section + delete section (human-verify checkpoint)

**UI hint**: yes

### Phase 13: Ingestion Flow Polish

**Goal**: The pipeline runner UI accurately reflects job state at all times and gives the operator correct tools to act on incomplete jobs
**Depends on**: Nothing (independent fixes to the existing pipeline runner)
**Requirements**: PIPE-18, PIPE-19, PIPE-20
**Success Criteria** (what must be TRUE):

  1. Step status badges on a running pipeline job never show stale or incorrect state — the displayed step matches the actual DB state
  2. Operator typing in the speaker alias typeahead sees relevant candidate matches and can select one; the selected value is applied correctly
  3. Operator toggling the incomplete filter on the pipeline list sees only jobs that require their action; toggling it off restores the full list

**Plans**: 3/3 plans complete

Plans:
**Wave 1**

- [x] 13-01-PLAN.md — Pre-Phase-13 cleanup + backend list_jobs incomplete filter & GET /api/admin/jobs param (PIPE-20)
- [x] 13-03-PLAN.md — Job detail: step-badge null-transition fallback (PIPE-18) + custom combobox replacing datalist (PIPE-19)

**Wave 2** *(blocked on 13-01)*

- [x] 13-02-PLAN.md — Pipeline list incomplete toggle + load param forwarding + filter-on empty state (PIPE-20) [rolled into 13-01]

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

**Plans**: 3/3 plans complete

Plans:
**Wave 1**

- [x] 14-01-PLAN.md — Backend: SpeakerPopoverEntry schema + get_argument_speakers service + GET /arguments/{id}/speakers route

**Wave 2** *(blocked on Wave 1)*

- [x] 14-02-PLAN.md — bits-ui install + +page.server.ts speakers fetch and photo_url_full reconstruction

**Wave 3** *(blocked on Wave 2)*

- [x] 14-03-PLAN.md — SpeakerPopover.svelte (new) + ChatBubble avatar button + +page.svelte Popover.Root wiring + roster avatars (human-verify checkpoint)

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
| 12. People Admin Improvements | v1.2 | 7/7 | Complete   | 2026-06-24 |
| 13. Ingestion Flow Polish | v1.2 | 3/3 | Complete    | 2026-06-25 |
| 14. Speaker Popover Card | v1.2 | 3/3 | Complete   | 2026-06-25 |
| 15. Speaker Role Accuracy | v1.3 | 1/4 | In Progress|  |
| 16. Parser Improvements | v1.3 | 0/2 | Pending | — |
| 17. Pipeline UI Polish | v1.3 | 0/2 | Pending | — |

### Phase 15: Speaker Role Accuracy

**Goal**: The public speaker popover shows accurate roles — Justices show the role they held at the time of the specific argument, and advocates show the role they played in that argument, not their default person-level role
**Depends on**: Phase 14 (popover exists and is live)
**Requirements**: ROLE-01, ROLE-02, ROLE-03
**Success Criteria** (what must be TRUE):

  1. A Justice who served as Associate Justice and later as Chief Justice shows the correct title in the popover based on the argument's argued_date
  2. An advocate who argued for the petitioner in one case and the respondent in another shows the correct role in each argument's popover
  3. Operator can change an advocate's role for a specific argument in the admin without affecting their role in other arguments
  4. Popovers for speakers with no tenure data and no per-argument role degrade gracefully (no crash, no misleading label)

**Plans**: 1/4 plans executed

**Wave 1**

- [x] 15-01-PLAN.md — Migration 0008: expand SideEnum (PETITIONER/RESPONDENT/AMICUS, backfill ADVOCATE→UNKNOWN) + new arguments.status enum column + ORM model updates

**Wave 2** *(blocked on 15-01)*

- [ ] 15-02-PLAN.md — Service + schemas + router: tenure date-range role lookup + advocate label map in get_argument_speakers; approve/rerun job transitions; IDOR-guarded participant-side PATCH; admin-list status filter; tenure-gap filter; 3 new admin endpoints

**Wave 3** *(blocked on 15-02; 15-03 and 15-04 run in parallel — disjoint frontend files)*

- [ ] 15-03-PLAN.md — Pipeline job detail UI: advocate role dropdowns (pipeline state), "Create Argument" approve button, post-approval read-only + two-step Re-run (human-verify checkpoint)
- [ ] 15-04-PLAN.md — Argument edit page advocate role editor + tenure-gap warnings; arguments-list status badge/column; people-directory tenure-gaps filter (human-verify checkpoint)

### Phase 16: Parser Improvements

**Goal**: The parse step extracts case name, docket number, argued date, and advocate sides directly from the transcript PDF so the operator reviews pre-populated fields rather than entering everything from scratch
**Depends on**: Phase 15 (argument_participants role field must exist before parser can populate it)
**Requirements**: PARSE-01, PARSE-02
**Success Criteria** (what must be TRUE):

  1. After parsing a standard SCOTUS transcript, the argument's case name, docket number, and argued date fields are pre-populated with values extracted from the PDF
  2. Each advocate in argument_participants has an initial role (petitioner/respondent/amicus) derived from the transcript structure, not left as UNKNOWN
  3. Pre-populated fields are editable — the operator can correct any extraction error before publishing
  4. Arguments from transcripts where extraction fails (older/non-standard formats) fall back to blank fields without breaking the parse step

**Plans**: 0/2 plans — pending

- [ ] 16-01-PLAN.md — Parser: extract cover-page metadata (case name, docket, date) and write to argument record at parse time
- [ ] 16-02-PLAN.md — Parser: detect advocate side from transcript section headers; write initial role to argument_participants

### Phase 17: Pipeline UI Polish

**Goal**: The pipeline admin gives the operator enough information at each stage to trust the process — detailed stats per card, clear source file identification, and direct access to the original PDF for speaker verification
**Depends on**: Phase 16 (parser extracts metadata that stage cards will display)
**Requirements**: PIPE-21, PIPE-22
**Success Criteria** (what must be TRUE):

  1. The Ingest stage card shows the original filename of the uploaded PDF
  2. The Parse stage card shows utterance count, distinct speaker count, and the extracted case metadata (name, docket, date)
  3. Operator can open or download the original source PDF for any argument directly from the pipeline job detail page
  4. Stats and file link are visible without leaving the pipeline admin view

**Plans**: 0/2 plans — pending

- [ ] 17-01-PLAN.md — Backend: store original filename at ingest; expose filename + parse stats in job detail API response
- [ ] 17-02-PLAN.md — Frontend: update stage cards with stats; add source PDF link to job detail page

## Backlog

### Phase 999.1: refactor front end to create a simple design system for common components (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: prefill argument metadata during pipeline run (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: move people avatar to gutters outside the arguments (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.4: decide on listing style for arguments (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: improve in-argument navigation (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.6: unify admin header navigation with public navigation (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.7: implement design system in Figma (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.8: create readme for git commits so I can remember how to start the stack locally (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
