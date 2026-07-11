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
- [x] **Phase 27: People Admin** - Benchmarks/advocate tabs, tenure-per-row appointment data, and create-person flow at `/admin/people/` and `/admin/people/[id]` (11 of 11 plans executed 2026-07-09, including gap-closure plan 27-11 fixing the `effect_update_depth_exceeded` regression from 27-10's CR-02 fix; 4th UAT retest re-run pending — see known GSD Roadmap Premature-Completion pattern) (completed 2026-07-09)
- [x] **Phase 28: Dashboard** - Intentional stat cards, "needs attention" section, and actionable CTAs at `/admin/` (3/3 plans executed 2026-07-11; UAT 2/2 passed, 28-SECURITY.md threats_open: 0, 28-VERIFICATION.md status `passed`) (completed 2026-07-11)

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
**Requirements**: PDIR-01, PDIR-02, PDIR-03, PDIR-04, PDIR-05, PDIR-06, PDIR-07, PEDIT-01, PEDIT-02, PEDIT-03, PEDIT-05, PEDIT-06, PEDIT-07, PEDIT-09, PEDIT-10 (UI surface), PEDIT-11, PEDIT-12 (PEDIT-04, PEDIT-08 superseded — see 27-CONTEXT.md D-10)
**Success Criteria** (what must be TRUE):

  1. People list page is titled "People" and has Bench and Advocate tabs; Bench tab columns include tenure coverage and tenure gap indicator; Advocate tab columns include argument count
  2. Click-to-filter missing-field pills work per tab (replaces the old "Incomplete only" toggle per D-04); "Justices with tenure gaps" filter is present and functional on the Bench tab only
  3. "Create person" button navigates to a blank person editor — operator can create a Justice before any argument is uploaded
  4. Justice Details card is collapsed by default; checking "Is Justice" opens it with animation; unchecking hides the fields without deleting tenure or appointment data
  5. Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date — data reads correctly from the migrated `court_tenures` columns

**Plans**: 11/11 plans complete
**Wave 1**

- [x] 27-01-PLAN.md — Schema foundation: birthdate migration + Pydantic schemas (BLOCKING migration)
- [x] 27-07-PLAN.md — Gap closure (UAT Gap 1): people-list middle-column padding gutter fix
- [x] 27-08-PLAN.md — Gap closure (UAT Gap 3): create-person persists structured name parts (schema + service + action)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 27-02-PLAN.md — List directory service: tab/missing filters + per-tab columns
- [x] 27-09-PLAN.md — Gap closure (UAT Gap 2): President's Party dropdown (D-16 reversal for that field only)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 27-03-PLAN.md — Detail/write service + create_person + POST /people endpoint
- [x] 27-04-PLAN.md — List page UI: tabs, click-to-filter pills, per-tab tables
- [x] 27-10-PLAN.md — Gap closure (CR-01/CR-02, BLOCKER): preserve tenure/birthdate on Bench→Advocate toggle + reset tenureRows after merge redirect (PEDIT-07)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 27-05-PLAN.md — Person editor restructure: Person Type card, tenure sub-cards, role removal

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 27-06-PLAN.md — Create-person page (/admin/people/new) reusing the shared template

**Wave 6** *(gap closure — from 27-UAT.md 4th retest, Test 1: blocker)*

- [x] 27-11-PLAN.md — Gap closure: fix Svelte `effect_update_depth_exceeded` infinite loop in the person-id-change reset effect, introduced by 27-10's CR-02 fix (PEDIT-07)

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

**Plans**: 3/3 plans complete

**Wave 1**

- [x] 28-01-PLAN.md — Backend stats data layer: admin_dashboard.py schemas + 7 read-only aggregation service functions (COUNT/MAX/LIMIT) across admin_arguments/people/jobs + DB-gated tests (DASH-01, DASH-03)

**Wave 2** *(blocked on Wave 1)*

- [x] 28-02-PLAN.md — Seven resource-scoped dashboard routes in admin.py with literal-before-{id} ordering discipline + route resolution tests (DASH-01, DASH-03)

**Wave 3** *(blocked on Wave 2)*

- [x] 28-03-PLAN.md — Frontend: shared StatCard.svelte + degrade-gracefully load() (logout preserved) + rewritten +page.svelte (Needs Attention first, 4 neutral stat cards, Web Traffic placeholder) (DASH-01, DASH-02, DASH-03, DASH-04, DASH-05)

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
| 27. People Admin | v1.5 | 11/11 | Complete    | 2026-07-09 |
| 28. Dashboard | v1.5 | 3/3 | Complete    | 2026-07-11 |

## Backlog

Standard: all backlog items live here as 999.x entries (`.planning/phases/999.N-slug/`), captured via `/gsd-capture --backlog` and reviewed/promoted via `/gsd-review-backlog`. `.planning/BACKLOG.md` (the flat B-NNN file previously used, 2026-07-01 to 2026-07-09) has been retired and its 14 still-open items migrated below (2026-07-09); 5 items (B-001, B-003, B-004, B-005, B-006) were dropped as already shipped by Phase 24/27, and B-014 was merged into 999.1 as a duplicate capture of the same idea.

### Phase 999.1: Click-to-copy extracted values design pattern (BACKLOG)

**Goal:** Whenever a value has been extracted from a source PDF, use a consistent design pattern that lets the operator click the value to copy it to their clipboard. If a value was not extracted (showing N/A), clicking to copy is disabled. Includes an appropriate icon and tooltip. The pattern must be identical everywhere it appears — pipeline run pages and argument editor pages alike — including extracted docket number(s). Expected to decompose into at least: (1) reusable tooltip component, (2) click-to-copy implementation for extracted hint values, and possibly others.
**Requirements:** TBD
**Plans:** 11/11 plans complete

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Share specific utterances via social media (BACKLOG)

**Goal:** [Captured for future planning] Let visitors share a specific utterance (a single speaker turn) from an oral argument to social media, to increase site exposure and utilization. Needs discussion on: what gets shared (permalink to the utterance vs. a rendered card/image), which platforms, and how this interacts with the apolitical-framing hard constraint — an isolated utterance shared out of the argument's full context could read as editorializing even though the underlying transcript content is unchanged.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Link participant names on job detail page to their edit entries (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-002, added 2026-06-18] On the pipeline job detail page (`/admin/pipeline/[job_id]`), the resolved participants section lists people by name as plain text. Each participant name should link directly to their people editor entry at `/admin/people/[id]` so the operator can navigate from a job result straight to the person's edit form. Confirmed still open (2026-07-09): the page currently only links to a filtered people list, not individual person records.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.4: Frontend design system: shared component library (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-007, added 2026-07-01] Refactor the frontend to extract common UI patterns (buttons, badges, cards, form inputs) into a shared component library. Reduces duplication between admin and public pages and makes future changes consistent.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: Move speaker avatars to gutters outside the argument body (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-008, added 2026-07-01] Speaker avatars currently appear inline within the chat bubbles on the public argument view. Moving them to fixed gutters (bench left, advocates right) would reinforce the two-sided layout and free up horizontal space for transcript text.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.6: Decide on listing style for cases/arguments (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-009, added 2026-07-01] The current case list is a basic list of links. No decision has been made on whether it should be cards, a table, grouped by term, searchable, etc. Needs a design decision before implementation.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.7: Improve in-argument section navigation (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-010, added 2026-07-01] In-argument navigation — jumping between sections (amicus, petitioner, respondent, etc.) within a single argument view. The current section rail exists but could be improved with better scroll-spy, jump links, or a collapsible outline.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.8: Figma design system (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-011, added 2026-07-01] Implement the design system in Figma to document components, tokens, and layout patterns. Useful before any significant frontend refactor or handoff.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.9: README: how to start the local stack (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-012, added 2026-07-01] No README documents how to start the full local stack (SvelteKit dev server, FastAPI backend, Postgres). Add one so setup steps don't have to be rediscovered each session.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.10: Bulk-import historical justices from CSV (BACKLOG) — SUPERSEDED

**Status:** SUPERSEDED / ABSORBED into Phase 29 (Historical Corpus Import) per CONTEXT.md D-01, 2026-07-09. The bulk justice CSV import is Step Zero of Phase 29 (Plan 29-03, `import-justices` command, requirement CORPUS-01) — it must land as a prerequisite of the corpus import, not as a separate standalone backlog phase. Do not promote this entry; it is closed.

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-013, added 2026-07-07] Operator currently has to manually enter every historical Supreme Court justice one at a time in the People admin screen. Jason already has a CSV covering all historical justices. Add an import path (upload + parse + create/update Person rows with is_justice=true, tenure/appointment data) so the full bench roster can be seeded in one operation instead of by hand. Needs a decision on dedup behavior against existing entries and which CSV columns map to which fields. Operator does not need this as a standing feature, just at the beginning of the project — could be a one-off script rather than a UI feature. The database is already seeded with current justices; this would extend that same seeding approach to historical ones.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.11: Bench popover: additional context data for Justices (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-015, added 2026-07-07] When a visitor clicks a Justice's avatar on the public argument view, the popover should show richer context about them and the case. Persistent data (doesn't change case to case): name, photo, birthdate, death date, and a list of tenures with start/end dates, appointing president, that president's party affiliation, and why they left that tenure (death, retirement, promotion). Case-specific data to explore further: their age at the time of the argument, how long they'd been in their position (possibly a case-heard count, possibly a visual indicator of where the argument falls on their tenure), and how to present all of this in the least biased way possible — this needs explicit exploration before implementation, per the apolitical-framing constraint. Confirmed still open (2026-07-09): SpeakerPopover.svelte currently shows photo, name, role, tenure dates, and appointing president, but no birthdate/death date/age/case-count despite Person.birthdate existing since Phase 27.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.12: `rerun_job` never spawns ingest for locally-uploaded jobs (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-016, added 2026-07-08, from 26-REVIEW.md CR-01] `create_job`'s upload path stores the PDF at `data/uploads/{job.id}.pdf` and sets neither `spaces_key` nor `pdf_url` when `settings.do_spaces_bucket` is falsy (local/dev mode, no DO Spaces configured). `rerun_job` copies `pdf_url`/`spaces_key`/`original_filename`/`source_dockets` onto the new job, but the rerun endpoint (`api/routers/admin.py:1042-1076`) only branches on `spaces_key` or `pdf_url` — no branch exists for a local-disk-backed original, so no ingest subprocess is ever spawned for the rerun. The endpoint still returns 202 with a fresh PENDING job, giving the operator every indication the rerun started, but the job sits at PENDING/INGEST forever with no error surfaced. Confirmed unresolved across two review passes; not touched by Phase 26. Fix: persist the resolved local file path on AdminJob at creation time and add a third rerun branch that re-spawns ingest with `--local-file`, or at minimum raise a ValueError (422) instead of silently creating a job that can never progress.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.13: Blank case_name/docket_number can corrupt slug and dedup-key data (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-017, added 2026-07-08, from 26-REVIEW.md CR-02] `ArgumentUpdate.case_name`/`.docket_number` are `Optional[str] = None` with no non-empty validation; `update_argument` treats "not None" as "provided," not "non-empty." The edit form's `?/save` action always sends a trimmed string (never undefined) and the `<input>` elements have no `required` attribute. If an operator clears either field and clicks Save: for a DRAFT argument, `_derive_slug("")` returns `""`, corrupting the case's public URL slug; for any status, `docket_number`/`docket_number_norm` can be wiped to `""`, breaking dedup semantics. The same gap exists in the sibling `update_argument_metadata` (case_name, source_docket). Fix: add a Pydantic field_validator rejecting blank/whitespace-only values on ArgumentUpdate and MetadataUpdate, plus `required` on both `<input>` elements as defense-in-depth.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.14: `update_argument_metadata` has no unique-constraint guard (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-018, added 2026-07-08, from 26-REVIEW.md CR-03] `update_argument_metadata` writes `source_docket`/`question_number` without first checking whether another Argument row already holds that combination. Introduced in Phase 19, untouched by Phase 26. Saving a metadata edit that collides with an existing row raises an unhandled IntegrityError (500) instead of a clean, user-facing validation error. Fix: add a pre-write existence check (or catch IntegrityError and map it to a 409/422 with a clear message) before committing the update.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.15: Rethink Full Name vs. name-part fields in the people editor (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-019, added 2026-07-09, from Phase 27 UAT] Jason expected that filling in only the component name fields (first/last/middle/suffix) without Full Name would auto-backfill Full Name on save — instead, Full Name is currently required standalone. Proposed direction: stop making Full Name operator-editable at all, and derive it entirely from the component fields ("We'd have to adjust the way parsing works but that feels like the better way to go"). Needs a design decision on exactly how derivation should work (ordering, suffix placement, punctuation) and what changes on the pipeline/parsing side before this can be scoped. Distinct from the real bug this surfaced alongside (create route silently discarding name-part fields when Full Name is also filled — fixed in Phase 27 gap-closure plan 27-08); this item is the broader "should Full Name exist as a separate editable field at all" question, still open.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.16: Represent tenure Seat as a Chief/Associate toggle instead of free text (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-020, added 2026-07-09, from Phase 27 UAT] During Phase 27 UAT, Jason asked for the tenure-row Seat field (currently free-text, restored during Phase 27 verification per PEDIT-09) to become the same segmented-toggle component used for the Bench/Advocate choice, since for a Justice it's really just Chief or Associate. Deferred rather than fixed immediately (Jason offered this exit himself) because real historical court_tenures.seat data includes specific numbered seats (e.g. "Associate Justice Seat 3"), not just a binary Chief/Associate split — collapsing to a 2-option toggle is a genuine data-model simplification that needs a decision on whether the numbered-seat detail is dropped, kept as a secondary field, or reconciled some other way, plus a migration/backfill pass over existing rows. Companion to 999.10 (bulk CSV import of historical justices), since both touch how much seat-numbering granularity the system needs to preserve.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.17: Fix FastAPI test lifespan/session-factory failure (BACKLOG) — FIXED 2026-07-10

**Goal:** [Captured for future planning] [Added 2026-07-09, surfaced during Phase 27 execution] **FIXED 2026-07-10, during Phase 30 Wave 1 post-merge gate investigation.** Root cause confirmed: nothing in the suite invoked FastAPI's `lifespan()` (httpx's ASGITransport doesn't fire ASGI lifespan events), so `AsyncSessionLocal` stayed `None` whenever `DATABASE_URL` leaked into the full-suite run via `tests/conftest.py`'s `load_dotenv()`. Fixed with a new `api/tests/conftest.py` autouse fixture that runs `lifespan()` per-test — critically importing `lifespan`/`app` *locally inside the fixture*, not at module level, because `tests/test_admin_router.py::test_api_main_imports_without_error` deletes and re-imports every `api.*` module mid-suite; a module-level import would bind to the pre-reset module object while other fixtures (which import `api.main.app` inside their own function bodies) pick up the post-reset object, silently splitting the process into two disconnected module graphs — this is why the fix didn't work on the first attempt. Also renamed a nonexistent `async_session_factory` import (real name: `AsyncSessionLocal`) in 3 files, and fixed the 3 stale hardcoded assertions in `tests/test_models_import.py` (12→13 tables, add `argument_status_log`; 3→6 SideEnum values, add PETITIONER/RESPONDENT/AMICUS). **Result:** full-suite errors 40→0, failures 59→28. See [[999.19]] for the follow-on issue this fix exposed.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [x] Fixed inline during Phase 30 execution (no formal plan file) — see commits `1a99f28a`, `f7ad3082`

### Phase 999.18: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths (BACKLOG)

**Goal:** [Captured for future planning] [Added 2026-07-09, from 27-REVIEW.md CR-01, surfaced during Phase 27 gap-closure execution] `CourtTenure.person_id` is `nullable=False` with a plain `ForeignKeyConstraint` and no `ON DELETE CASCADE` in any Alembic migration, but none of `get_merge_preview`, `merge_people`, or `delete_person_if_orphan` (`api/services/admin_people.py`) account for `CourtTenure` rows. Merging or deleting any Bench person with one or more tenure rows raises an unhandled `IntegrityError` (500) instead of the documented graceful response. Predates Phase 27 — `CourtTenure` and the merge/delete service paths were introduced in Phase 22 — but is newly reachable now that Phase 27 added full tenure-row CRUD to the People editor. Fix: count `CourtTenure` in `get_merge_preview`'s counted-tables loop, transfer `CourtTenure` rows to the target person in `merge_people`, and include `CourtTenure` in `delete_person_if_orphan`'s orphan check — mirroring the existing `Utterance`/`SpeakerAlias`/`CaseAppearance`/`ArgumentParticipant` handling.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.19: Audit ~28 stale DB-gated test fixtures + fix real data leakage into the shared dev DB (BACKLOG)

**Goal:** [Captured for future planning] [Added 2026-07-10, surfaced while fixing 999.17 during Phase 30 Wave 1; escalated 2026-07-10 during Phase 30 Wave 3 after leaked test rows actively blocked the 30-04 operator runbook] Fixing the FastAPI lifespan/session-factory bug (999.17) means DB-gated tests across `pipeline/tests/` and `api/tests/` now genuinely execute against the live local dev Postgres (`postgresql+asyncpg://scotus:scotus@localhost:5432/scotus`) instead of silently erroring at session setup. Two distinct consequences:

1. ~28 tests fail on real schema/data-assumption mismatches never actually exercised in a full-suite run before now (e.g. `pipeline/tests/test_pipeline_run.py::test_rerun_creates_new_rows` inserts an `Utterance` without `strategy`, which is `nullable=False` per pre-existing PIPE-04 — a stale fixture, not a regression). Spread across `pipeline/tests/test_ingest.py`, `test_parse.py`, `test_resolve.py`, `test_seed_aliases.py`, `test_pipeline_run.py`, `api/tests/test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`, `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, `test_arguments.py`.
2. **Confirmed real data leakage, more serious than originally scoped:** the `db_session` fixture's `session.begin()` + explicit `rollback()` pattern only protects against the test's OWN direct writes — it does NOT protect against writes made by production service functions the test calls (e.g. `create_person_for_job`, `publish_argument`) that commit internally as normal application behavior. Once a service function commits, the fixture's later rollback is a no-op — those rows are permanent. Confirmed 2026-07-10: 3 full-suite pytest runs left 18 leaked `Person` rows (duplicate "Ketanji Brown Jackson" x3 plus 5 fake test names x3 each: "Advocate Example", "Bench Example", "John Smith", "Justice Example", "Status Log Advocate") and 15 fully-synthetic `Argument` rows (no docket, no date, no utterances) in the shared dev DB — one of which actively broke `python -m pipeline import-justices` (`MultipleResultsFound` on the duplicated "Ketanji Brown Jackson" `Person.full_name` lookup in `pipeline/commands/import_justices_csv.py:182`) mid-execution of plan 30-04. Cleaned up manually (scoped DELETE, verified each row was zero-content synthetic test data, keeping the one legitimate `Person` id=116 with a real `court_tenures` row) — this is a stopgap, not a fix. **Needs its own investigation:** likely fix is a dedicated test database (not the shared dev DB) for any test that exercises commit-invoking service code, or an autouse fixture that snapshots/restores affected tables, or savepoint-based nesting that survives inner commits. **Confirmed to also affect `pipeline/tests/`, not just `api/tests/`** (2026-07-10, during Phase 30 final regression check): `pipeline/tests/test_import_convokit_core.py`'s `isolated_session` fixture uses the identical flawed pattern ("test-owned session, rolled back after the test" — but `run_import_convokit` commits internally), so `test_full_name_only_match_backfills_oyez_speaker_id` re-leaks a duplicate "John Smith" `Person` row on every run, which is exactly the kind of duplicate that broke `import-justices` earlier in this same phase. This recurs on every full-suite run with `DATABASE_URL` configured — the manual DELETE cleanup performed earlier in Phase 30 was already stale by the next full-suite run.

**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 29: Historical Corpus Import

**Goal:** Bulk-import historical oral arguments (terms 1955-2019, ~7,800 arguments) from the Cornell ConvoKit supreme-corpus dataset directly into cases/arguments/utterances/people/court_tenures, bypassing PDF download and LLM parsing for this batch. Source files: supreme-corpus/{utterances.jsonl,conversations.json,speakers.json}, a separately-located cases.jsonl (title/docket/dates/citation), and a justices tenure CSV (appointment/tenure backfill). Open questions: dedup against existing Person/CourtTenure rows, stage-direction inline-vs-row policy, apolitical-field stripping (win_side/votes_side/scdb_docket_id must never be persisted), lead-docket-only limitation for consolidated cases, advocate identity QA. Existing PDF ingest/parse/resolve pipeline stays for terms 2020+ and all future terms -- this is a new, separate one-time bulk-import CLI command, not a replacement.
**Requirements**: CORPUS-01, CORPUS-02, CORPUS-03, CORPUS-04, CORPUS-05, CORPUS-06, CORPUS-07, CORPUS-08, CORPUS-09, CORPUS-10, CORPUS-11
**Depends on:** Phase 28
**Plans:** 9/9 plans complete

**Wave 1** *(parallel — disjoint files)*

- [x] 29-01-PLAN.md — Migration 0017 (3 nullable oyez external-ID columns) + data/corpus/ source-file infra + python-dateutil (CORPUS-02, CORPUS-04)
- [x] 29-02-PLAN.md — Corpus parsing helpers: streaming loader, curated stage-direction detector, apolitical allowlist (test-first) (CORPUS-05, CORPUS-06)

**Wave 2** *(parallel — disjoint files; blocked on 29-01)*

- [x] 29-03-PLAN.md — Justice CSV importer (Step Zero, absorbs 999.10): upgrade 13 seeded rows in place + create roster + import-justices subcommand (CORPUS-01, CORPUS-11)
- [x] 29-06-PLAN.md — Frontend: Attributions/License page + per-argument note (server-gated) + TopNav link + README credit + oyez_transcript_id payload field (CORPUS-09, CORPUS-10)

**Wave 3** *(blocked on 29-01, 29-02, 29-03)*

- [x] 29-04-PLAN.md — Corpus importer core: import-convokit CLI, term batching, Case/Argument/CaseArgument/PipelineRun creation, speaker resolution (CORPUS-03, CORPUS-05)

**Wave 4** *(blocked on 29-04)*

- [x] 29-05-PLAN.md — Utterance import (streaming, \n preserved, stage-direction row-splitting) + per-batch summary report (CORPUS-06, CORPUS-07, CORPUS-08)

**Gap closure** *(from 29-VERIFICATION.md BLOCKER gap #13 / 29-REVIEW.md CR-01 — independent, no deps)*

- [x] 29-07-PLAN.md — Widen ArgumentMetadataResponse.argued_date and CaseItem.argued_date to Optional (matches nullable Argument.argued_date), fix one frontend null-date-guard parity gap, add regression tests (CORPUS-03, CORPUS-10)

**Gap closure** *(newly discovered during this gap-closure session, not in 29-VERIFICATION.md — independent, no deps)*

- [x] 29-08-PLAN.md — Relabel corpus importer's PipelineRun.step from "ingest" to "parse" so GET /arguments/{id}/utterances actually returns utterances for corpus-imported arguments (previously silently empty), add end-to-end regression test (CORPUS-03, CORPUS-07)

**Gap closure** *(from 29-VERIFICATION.md BLOCKER CR-01 — docket/question uniqueness collision — independent, no deps)*

- [x] 29-09-PLAN.md — Derive question_number per docket (aligns importer with the real uq_arguments_source_docket_question constraint) so reargued cases and PDF-ingest-overlap dockets import at question_number=2+ instead of silently colliding; add distinct docket_question_conflict counter to the per-batch summary + explicit IntegrityError handling; add regression tests (CORPUS-03, CORPUS-08)

### Phase 30: Corpus Import Resolve Workflow

**Goal:** Corpus-imported arguments currently land at `status=draft` with `resolved_at` permanently NULL, which means they can never pass the existing publish gate. Route them through the same AdminJob-based paused/resolve review workflow the PDF-ingest pipeline already uses, so an operator can review and fix auto-created people (missing name parts) and speaker attributions before an argument becomes publishable.
**Requirements**: PJOB-01, PJOB-02, PJOB-14, PJOB-15, PJOB-18, PJOB-19, PJOB-20, PJOB-21 (reused family — no new REQ IDs)
**Depends on:** Phase 29
**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 30-01-PLAN.md — Pipeline write-path fix: Argument.status→PIPELINE + paired PAUSED/RESOLVE AdminJob + HIT-shaped discrepancies (crux; D-01, D-03, D-05)
- [x] 30-02-PLAN.md — API `source` derived field on AdminJobResponse via exists() in list_jobs()/get_job() (no migration)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 30-03-PLAN.md — Pipeline list "Source" tag/column (PDF vs Corpus), list page only (D-05 scope boundary)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 30-04-PLAN.md — Operator runbook: FK-safe scoped wipe + re-import of the term-1955 batch (D-02)

### Phase 30.1: Close gap: AEDIT-04/DASH-02 — wire ArgumentDetailsCard + status filter into arguments admin page (INSERTED)

**Goal:** `/admin/arguments/[id]` actually reuses the shared `ArgumentDetailsCard` component (not a hand-rolled duplicate form), and the dashboard's Draft/Published/Unpublished status CTAs on `/admin/arguments?status=X` actually filter the arguments list instead of being silently ignored.
**Requirements**: AEDIT-04, DASH-02
**Depends on:** Phase 23, Phase 26, Phase 28
**Plans:** 2 plans

Source: v1.5-MILESTONE-AUDIT.md (gaps_found, 2026-07-11) — both requirements were marked "Complete" in REQUIREMENTS.md by their originating phase, but neither phase's own verification checked actual cross-phase consumption; the integration checker caught it at milestone-audit time.

**Wave 1** *(parallel — disjoint files)*

Plans:

- [ ] 30.1-01-PLAN.md — DASH-02: thread `?status=` through list_arguments() service + GET /arguments route + list load(), add segmented status filter control + active-filter indicator + filtered empty-state (DASH-02)
- [ ] 30.1-02-PLAN.md — AEDIT-04: consume shared ArgumentDetailsCard on /admin/arguments/[id] — split Card 1 into a "Case" card + second ArgumentDetailsCard consumer, new saveArgumentDetails action reusing PATCH /metadata (AEDIT-04)
