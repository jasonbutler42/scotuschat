# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- ✅ **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (shipped 2026-06-29)
- ✅ **v1.4 Admin Completeness** — Phases 18–21 (shipped 2026-07-02)
- 🚧 **v1.5 Admin Screens Cleanup** — Phases 22–28 (in progress)

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

<details>
<summary>✅ v1.4 Admin Completeness (Phases 18–21) — SHIPPED 2026-07-02</summary>

**Overview:** Made the admin interface fully self-sufficient — is_justice flag + conditional people editor, argument and pipeline run delete, live pipeline status polling, duplicate argument prevention, metadata prefill, and unified admin navigation.

- [x] Phase 18: People Schema + Editor (3/3 plans) — completed 2026-06-29
- [x] Phase 19: Pipeline Reliability (4/4 plans) — completed 2026-06-30
- [x] Phase 20: Live Pipeline Status (1/1 plan) — completed 2026-07-01
- [x] Phase 21: Admin UI Surface (4/4 plans) — completed 2026-07-01

Full phase details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

### 🚧 v1.5 Admin Screens Cleanup (In Progress)

**Milestone Goal:** Screen-by-screen audit and refinement of all 7 admin screens — defining what belongs on each, removing redundant elements, and adding missing capabilities now that the admin interface is functionally complete.

- [x] **Phase 22: Schema Foundations** - Cross-cutting Alembic migrations and pipeline changes that all v1.5 screens depend on (completed 2026-07-02)
- [x] **Phase 23: Shared Argument Details Component** - Reusable docket/question/date card used on both pipeline job detail and argument edit pages (completed 2026-07-02)
- [x] **Phase 24: Pipeline List Page** - Redesigned run-start form and run table at `/admin/pipeline/` (completed 2026-07-07)
- [x] **Phase 25: Pipeline Job Detail Page** - Restructured job detail layout with run status card, resolve redesign, and no floating buttons at `/admin/pipeline/[id]` (completed 2026-07-07)
- [x] **Phase 26: Arguments Admin** - New `unpublished` status lifecycle + refined list and edit screens at `/admin/arguments/` and `/admin/arguments/[id]` (completed 2026-07-08)
- [ ] **Phase 27: People Admin** - Benchmarks/advocate tabs, tenure-per-row appointment data, and create-person flow at `/admin/people/` and `/admin/people/[id]`
- [ ] **Phase 28: Dashboard** - Intentional stat cards, "needs attention" section, and actionable CTAs at `/admin/`

## Phase Details

### Phase 22: Schema Foundations

**Goal**: All new database tables, columns, enum values, and pipeline data changes required by v1.5 UI are in place — migrations run clean, data is backfilled, and downstream phases can build UI without waiting on schema
**Depends on**: Phase 21
**Requirements**: ALIST-01, AEDIT-02, PJOB-13, PEDIT-10
**Success Criteria** (what must be TRUE):

  1. Alembic migration adds `unpublished` to `argument_status` enum and runs without error on existing data
  2. Alembic migration creates `argument_status_log` table with required columns and FK to arguments; existing arguments each receive a `created` log entry via backfill
  3. `argument_participants.title` VARCHAR column exists; parse step extracts advocate title from PDF TOC and writes it on new runs
  4. `appointed_by` and `appointing_president_party` columns exist on `court_tenures` (not `people`), with data backfilled from `people` and old columns removed via migration

**Plans**: 3/3 plans complete
**Wave 1**

- [x] 22-01-PLAN.md — Migration 0012: unpublished enum value + argument_status_log table + backfill (ALIST-01, AEDIT-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 22-02-PLAN.md — Migration 0013: participant title column + move appointed_by to court_tenures + all code-layer cleanup (PEDIT-10, PJOB-13 schema)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 22-03-PLAN.md — Parse step advocate-title extraction from PDF TOC (PJOB-13 logic)

### Phase 23: Shared Argument Details Component

**Goal**: A single reusable Argument Details card component exists that renders docket pill/tag input, free-text question number, argued date, and extracted hints from `cover_metadata` — wired up on the pipeline job detail page as its first consumer
**Depends on**: Phase 22
**Requirements**: AEDIT-03, AEDIT-04, PJOB-03, PJOB-04, PJOB-05, PJOB-06, PJOB-07, PJOB-09, PJOB-10, PJOB-11, PJOB-12
**Success Criteria** (what must be TRUE):

  1. Pipeline job detail page shows "Argument Details" card with docket pill/tag input, free-text question number, argued date, and extracted hints alongside each editable field (or "N/A" when nothing was extracted)
  2. Docket pill/tag UI allows adding multiple docket numbers one at a time and removing individual pills — consistent with PLIST-02 target behavior
  3. Parse stat card shows utterance count, speaker counts (Bench / Advocate / Total), case name, argued date, docket(s), and question number(s); fields not extracted display "N/A" rather than being hidden
  4. Saving Argument Details saves run metadata only and does not create the argument
  5. Ingest card no longer shows the source file (moved to run status card in Phase 25)

**Plans**: 7/7 plans complete

- [x] 23-05-PLAN.md

**Wave 1** *(parallel — disjoint files)*

- [x] 23-01-PLAN.md — Backend: expand ParseStats (bench/advocate/total + cover_metadata fields) and add question_number to MetadataUpdate/ArgumentDetail (PJOB-07, PJOB-10, PJOB-11, PJOB-12)
- [x] 23-02-PLAN.md — ArgumentDetailsCard.svelte: docket pills, free-text question number, argued date, always-visible extracted hints (AEDIT-03, AEDIT-04, PJOB-03, PJOB-04, PJOB-05, PJOB-06)

**Wave 2** *(blocked on Wave 1)*

- [x] 23-03-PLAN.md — Wire pipeline job detail: saveJobMetadata action, render ArgumentDetailsCard, expand parse stat card, remove ingest source file row (AEDIT-04, PJOB-04, PJOB-05, PJOB-06, PJOB-07, PJOB-09, PJOB-10, PJOB-11, PJOB-12)

**Wave 3** *(gap closure — blocked on Wave 2 UAT)*

- [x] 23-04-PLAN.md — Gap closure: remove orphaned Argument card and View Source PDF card, fix docket-clear save bug, freeze question_number hint to null, move docket instruction to static label

**Wave 4** *(gap closure — UAT round 2)*

- [x] 23-06-PLAN.md — Gap closure: restore "View source PDF" link inside the Ingest step card (deleted whole in 4278c9fb)
- [x] 23-07-PLAN.md — Gap closure: full-stack multi-docket support (source_dockets text[] column + array-aware schema/service/action/component; source_docket retained as dedup key)

**UI hint**: yes

### Phase 24: Pipeline List Page

**Goal**: The pipeline list page at `/admin/pipeline/` has a free-text question number field, a docket pill/tag input consistent with Phase 23, a complete runs table, the "show incomplete only" toggle, and accurate compound status badges
**Depends on**: Phase 23
**Requirements**: PLIST-01, PLIST-02, PLIST-03, PLIST-04, PLIST-05
**Success Criteria** (what must be TRUE):

  1. Operator can type any free text into the question number field when starting a run (not constrained to a dropdown)
  2. Operator can add multiple docket numbers as pills and remove individual pills before submitting — matching the Phase 23 component behavior
  3. Runs table shows all pipeline runs, not just recent ones
  4. "Show incomplete only" toggle is present and functional
  5. Status badges display compound labels (e.g., "Parse · Running", "Resolve · Needs Review", "Completed") that accurately reflect current stage and status

**Plans**: 5/5 plans complete

**Wave 1** *(parallel — disjoint files)*

- [x] 24-01-PLAN.md — Backend: remove limit=10 from list_jobs service + router so runs table shows all runs (PLIST-03)
- [x] 24-02-PLAN.md — Create shared DocketPillInput.svelte extracted from ArgumentDetailsCard (PLIST-02)

**Wave 2** *(blocked on 24-02 — both consume DocketPillInput; disjoint files from each other)*

- [x] 24-03-PLAN.md — Refactor ArgumentDetailsCard.svelte to consume DocketPillInput, behavior-identical (PLIST-02)
- [x] 24-04-PLAN.md — Pipeline list page: free-text question, DocketPillInput + per-pill preflight, full multi-docket run-start persistence, compound badge, Step column removed, All Runs heading (PLIST-01, PLIST-02, PLIST-04, PLIST-05)

**Gap closure** *(from 24-VERIFICATION.md CR-01 — independent, no deps)*

- [x] 24-05-PLAN.md — Reject `-`-prefixed docket values at API boundary (422) + startup guard writes best-effort FAILED on pre-run_ingest exit, closing the silent-stuck-job argv-injection gap (PLIST-02)

**UI hint**: yes

### Phase 25: Pipeline Job Detail Page

**Goal**: The pipeline job detail page at `/admin/pipeline/[id]` has a run status card as the primary status element, a fully restructured resolve card, and all previously floating action buttons moved into contextually appropriate cards
**Depends on**: Phase 23
**Requirements**: PJOB-01, PJOB-02, PJOB-08, PJOB-14, PJOB-15, PJOB-16, PJOB-17, PJOB-18, PJOB-19, PJOB-20, PJOB-21, PJOB-22, PJOB-23
**Success Criteria** (what must be TRUE):

  1. Run status card shows status badge and source file link and has 3 states: Not ready (lists blockers), Ready ("Create Argument" CTA), Already created (link to argument edit page)
  2. Failed step card shows the error message and contextual next-step actions including re-run — no standalone floating "Re-run" button exists anywhere on the page
  3. Resolve card columns show: Raw label, Resolved as (avatar + name), Bench/Advocate side, Argument Role, Title (advocates only), and Action — no confirmation checkmark column
  4. Resolve card is fully editable in Not ready and Ready states and read-only in Already created state; bench roles display tenure lookup result or "Missing tenure" when no matching tenure exists
  5. Saving Argument Details triggers bench role recalculation visible in the resolve card; "Create Argument" and "Continue Resolve" actions live inside their respective cards, not as floating buttons

**Plans**: 4/4 plans complete
**UI hint**: yes

### Phase 26: Arguments Admin

**Goal**: The arguments admin screens accurately represent the three-state argument lifecycle (Draft / Published / Unpublished), the arguments list excludes pipeline-only rows, and the argument edit page has a status log, a unified Argument Details card, and a speakers section replacing the old advocate roles card
**Depends on**: Phase 22, Phase 23
**Requirements**: ALIST-02, ALIST-03, ALIST-04, AEDIT-01, AEDIT-02 (UI surface), AEDIT-05, AEDIT-06, AEDIT-07, AEDIT-08, AEDIT-09
**Success Criteria** (what must be TRUE):

  1. Arguments list shows only Draft / Published / Unpublished rows — arguments in pipeline-only status do not appear
  2. Status column displays distinct badges for all three statuses; "Created" column shows the date/time the argument was first created
  3. Argument edit page shows a status card with the current badge, created date, and published date; below it a full status log with a timestamped entry for every transition
  4. Speakers section lists all argument participants with utterance counts; advocate rows have a role dropdown (PETITIONER / RESPONDENT / AMICUS), a title field, and inline save without full-page refresh; bench rows show tenure-derived role or "Missing tenure" with edit link
  5. Publish / Unpublish / re-Publish transitions are all functional: Draft → Published, Published → Unpublished, Unpublished → Published

**Plans**: 6/6 plans complete

**Wave 1** *(parallel — disjoint files)*

- [x] 26-01-PLAN.md — Backend argument lifecycle: three-state publish/unpublish, status-log writes, list filter, slug-freeze + delete gates (ALIST-02, AEDIT-02, AEDIT-08, AEDIT-09)
- [x] 26-03-PLAN.md — Frontend list page three-state badges + Created column + status-driven row actions, and RunStatusCard Archived badge (ALIST-02, ALIST-03, ALIST-04)

**Wave 2** *(blocked on 26-01)*

- [x] 26-02-PLAN.md — Backend Speakers data query + status_log/speakers in ArgumentDetail + advocate title persistence (AEDIT-01, AEDIT-02, AEDIT-05, AEDIT-06, AEDIT-07)

**Wave 3** *(blocked on 26-02)*

- [x] 26-04-PLAN.md — Frontend edit page: Status card + Status history, publish placement, unified Speakers section, Draft-only delete gate (AEDIT-01, AEDIT-02, AEDIT-05, AEDIT-06, AEDIT-07, AEDIT-08, AEDIT-09)

**Gap closure** *(from 26-VERIFICATION.md — 2 confirmed gaps)*

- [x] 26-05-PLAN.md — DRAFT-only backend delete gate (PIPELINE now blocked) + regression tests; authoritative UNKNOWN/ADVOCATE advocate-side rejection + explicit "Unresolved" placeholder and Save-disable on the edit page (AEDIT-06, AEDIT-09)

**Gap closure** *(from 26-UAT.md — Test 18: Archived badge missing on pipeline list)*

- [x] 26-06-PLAN.md — Add is_archived to AdminJobResponse + outerjoin Argument in list_jobs; render grey Archived badge on the pipeline list page to match RunStatusCard (PLIST-05)

**UI hint**: yes

### Phase 27: People Admin

**Goal**: The people list is split into Bench and Advocate tabs with columns appropriate to each, a "Create person" button works before any argument exists, and the person editor consolidates all Justice-specific fields into a collapsible Justice Details card with appointment data now stored per tenure row
**Depends on**: Phase 22
**Requirements**: PDIR-01, PDIR-02, PDIR-03, PDIR-04, PDIR-05, PDIR-06, PDIR-07, PEDIT-01, PEDIT-02, PEDIT-03, PEDIT-04, PEDIT-05, PEDIT-06, PEDIT-07, PEDIT-08, PEDIT-09, PEDIT-10 (UI surface), PEDIT-11, PEDIT-12
**Success Criteria** (what must be TRUE):

  1. People list page is titled "People" and has Bench and Advocate tabs; Bench tab columns include tenure coverage and tenure gap indicator; Advocate tab columns include argument count
  2. "Incomplete only" filter works per tab; "Justices with tenure gaps" filter is present and functional on the Bench tab only
  3. "Create person" button navigates to a blank person editor — operator can create a Justice before any argument is uploaded
  4. Justice Details card is collapsed by default; checking "Is Justice" opens it with animation; unchecking hides the fields without deleting tenure or appointment data
  5. Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date — data reads correctly from the migrated `court_tenures` columns

**Plans**: TBD
**UI hint**: yes

### Phase 28: Dashboard

**Goal**: The `/admin/` dashboard presents intentionally designed stat cards with actionable CTAs, a "needs attention" section surfacing real operator tasks, and a web traffic placeholder card — giving the operator an at-a-glance view of the admin state on every login
**Depends on**: Phase 22, Phase 26, Phase 27
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):

  1. Stat cards show: Arguments (total / published / draft / unpublished), People (total / incomplete), Utterances (total), and Pipeline runs (recent count + last activity date)
  2. Each applicable stat card has an inline CTA linking to the relevant admin screen (e.g., "12 people missing fields → Review")
  3. "Needs attention" section shows people with incomplete fields, Justices with tenure gaps, and draft arguments — intentionally unpublished arguments are excluded from this section
  4. A web traffic placeholder card is present and labelled "coming soon"
  5. Dashboard layout is intentionally designed — not a generic table dump; visual hierarchy guides the operator to the most urgent items

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
| 9. People Data Model Migration | v1.2 | 3/3 | Complete | 2026-06-19 |
| 10. Unified Navigation | v1.2 | 1/1 | Complete | 2026-06-22 |
| 11. Argument Metadata Editing | v1.2 | 4/4 | Complete | 2026-06-22 |
| 12. People Admin Improvements | v1.2 | 7/7 | Complete | 2026-06-24 |
| 13. Ingestion Flow Polish | v1.2 | 3/3 | Complete | 2026-06-25 |
| 14. Speaker Popover Card | v1.2 | 3/3 | Complete | 2026-06-25 |
| 15. Speaker Role Accuracy | v1.3 | 4/4 | Complete | 2026-06-26 |
| 16. Parser Improvements | v1.3 | 2/2 | Complete | 2026-06-26 |
| 17. Pipeline UI Polish | v1.3 | 3/3 | Complete | 2026-06-29 |
| 18. People Schema + Editor | v1.4 | 3/3 | Complete | 2026-06-29 |
| 19. Pipeline Reliability | v1.4 | 5/5 | Complete | 2026-06-30 |
| 20. Live Pipeline Status | v1.4 | 1/1 | Complete | 2026-07-01 |
| 21. Admin UI Surface | v1.4 | 4/4 | Complete | 2026-07-01 |
| 22. Schema Foundations | v1.5 | 3/3 | Complete    | 2026-07-02 |
| 23. Shared Argument Details Component | v1.5 | 7/7 | Complete   | 2026-07-06 |
| 24. Pipeline List Page | v1.5 | 5/5 | Complete    | 2026-07-07 |
| 25. Pipeline Job Detail Page | v1.5 | 4/4 | Complete    | 2026-07-07 |
| 26. Arguments Admin | v1.5 | 6/6 | Complete    | 2026-07-08 |
| 27. People Admin | v1.5 | 0/TBD | Not started | - |
| 28. Dashboard | v1.5 | 0/TBD | Not started | - |

## Backlog

See `.planning/BACKLOG.md` for unscheduled items (B-001 through B-012).

### Phase 999.1: Click-to-copy extracted values design pattern (BACKLOG)

**Goal:** Whenever a value has been extracted from a source PDF, use a consistent design pattern that lets the operator click the value to copy it to their clipboard. If a value was not extracted (showing N/A), clicking to copy is disabled. Includes an appropriate icon and tooltip. Expected to decompose into at least: (1) reusable tooltip component, (2) click-to-copy implementation for extracted hint values, and possibly others.
**Requirements:** TBD
**Plans:** 6/6 plans complete

Plans:

- [x] 25-01-PLAN.md
- [x] 25-02-PLAN.md
- [x] 25-03-PLAN.md
- [x] 25-04-PLAN.md

- [ ] TBD (promote with /gsd-review-backlog when ready)
