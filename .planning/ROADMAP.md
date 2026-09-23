# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- ✅ **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (shipped 2026-06-29)
- ✅ **v1.4 Admin Completeness** — Phases 18–21 (shipped 2026-07-02)
- ✅ **v1.5 Admin Screens Cleanup** — Phases 22–30, 30.1 (shipped 2026-07-12)
- ✅ **v1.6 Backlog Cleanup** — Phases 31–40, 40.1 (shipped 2026-07-29)
- ✅ **v1.7 Corpus Fidelity & Resolve Rework** — Phases 41–46 (shipped 2026-08-15)
- ✅ **v1.8 Import & Provenance Re-model** — Phases 47–51 (shipped 2026-09-23)

**No milestone is active.** Run `/gsd-new-milestone` to scope the next one.

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

<details>
<summary>✅ v1.5 Admin Screens Cleanup (Phases 22–30, 30.1) — SHIPPED 2026-07-12</summary>

**Overview:** Screen-by-screen audit and refinement of all 7 admin screens — defining what belongs on each, removing redundant elements, and adding missing capabilities. Absorbed an out-of-band addition mid-milestone: bulk historical corpus import (~7,800 arguments, 1955–2019, from Cornell ConvoKit), routed through the same resolve/publish workflow as PDF ingest. A milestone-audit gap-closure phase (30.1) wired the shared Argument Details component and dashboard status filter into the arguments admin page.

- [x] Phase 22: Schema Foundations (3/3 plans) — completed 2026-07-02
- [x] Phase 23: Shared Argument Details Component (7/7 plans) — completed 2026-07-06
- [x] Phase 24: Pipeline List Page (5/5 plans) — completed 2026-07-07
- [x] Phase 25: Pipeline Job Detail Page (4/4 plans) — completed 2026-07-07
- [x] Phase 26: Arguments Admin (6/6 plans) — completed 2026-07-08
- [x] Phase 27: People Admin (11/11 plans) — completed 2026-07-09
- [x] Phase 28: Dashboard (3/3 plans) — completed 2026-07-11
- [x] Phase 29: Historical Corpus Import (9/9 plans) — completed 2026-07-10
- [x] Phase 30: Corpus Import Resolve Workflow (4/4 plans) — completed 2026-07-10
- [x] Phase 30.1: Close gap AEDIT-04/DASH-02 (INSERTED, 3/3 plans) — completed 2026-07-12

Full phase details: `.planning/milestones/v1.5-ROADMAP.md`

</details>

<details>
<summary>✅ v1.6 Backlog Cleanup (Phases 31–40, 40.1) — SHIPPED 2026-07-29</summary>

**Overview:** Closed out the 10 phases promoted from the 999.x backlog on 2026-07-12 — an escalated data-integrity risk (stale test fixtures + real data leakage), four small pipeline/people-admin bug fixes, one operator UX pattern, two open design questions resolved during discuss-phase (tenure Seat toggle, Full Name auto-derivation), a public-UI enrichment (bench popover context), and a README gap. Phase 38's own UAT uncovered and closed a real security gap (G-38-6, authenticated-admin path-traversal/arbitrary-file-write in docket handling). Phase 40.1 was inserted by the pre-close artifact audit to re-fix that same G-38-6 gap from a stale debug-session record — the planner's source audit found it already fixed and closed the phase via documentation reconciliation instead of duplicate work.

- [x] Phase 31: Audit ~28 stale DB-gated test fixtures + fix real data leakage into shared dev DB (8/8 plans) — completed 2026-07-13
- [x] Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths (2/2 plans) — completed 2026-07-13
- [x] Phase 33: `update_argument_metadata` unique-constraint guard (4/4 plans) — completed 2026-07-14
- [x] Phase 34: Blank case_name/docket_number validation (4/4 plans) — completed 2026-07-14
- [x] Phase 35: Remove pipeline job rerun capability (3/3 plans) — completed 2026-07-14
- [x] Phase 36: Click-to-copy extracted values design pattern (3/3 plans) — completed 2026-07-15
- [x] Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text (5/5 plans) — completed 2026-07-21
- [x] Phase 38: Rethink Full Name vs. name-part fields in the people editor (10/10 plans) — completed 2026-07-27
- [x] Phase 39: Bench popover — additional context data for Justices (9/9 plans) — completed 2026-07-29
- [x] Phase 40: README — how to start the local stack (3/3 plans) — completed 2026-07-14
- [x] Phase 40.1: Sanitize docket input to close path-traversal/arbitrary-file-write gap (INSERTED, SUPERSEDED — 0 plans, closed via reconciliation, see `.planning/milestones/v1.6-phases/40.1-sanitize-docket-input-to-close-path-traversal-arbitrary-file/40.1-SUMMARY.md`) — completed 2026-07-29

Full phase details: `.planning/milestones/v1.6-ROADMAP.md`

</details>

<details>
<summary>✅ v1.7 Corpus Fidelity & Resolve Rework (Phases 41–46) — SHIPPED 2026-08-15</summary>

**Overview:** Trusted the corpus-import data pipeline end to end on one representative case, reworked the Resolve table into a real editing tool, closed two known UI bugs, and (inserted mid-milestone once Windows admin access became available) made the local dev environment reliable — closing the pytest DB-isolation bug that twice wiped the shared dev database and relocating the repository/toolchain to WSL-native infrastructure.

- [x] Phase 41: Canonical Corpus Fixture Selection (3/3 plans) — completed 2026-07-29
- [x] Phase 42: Corpus Import Fidelity Diff & Fix (5/5 plans) — completed 2026-07-30
- [x] Phase 43: Dev-Only Reset to Fixture (4/4 plans) — completed 2026-07-31
- [x] Phase 44: Resolve Table Rework (9/9 plans) — completed 2026-08-11
- [x] Phase 45: Deferred UI Bug Fixes (2/2 plans) — completed 2026-08-12
- [x] Phase 46: Dev Environment Reliability (INSERTED, 6/6 plans) — completed 2026-08-15

Full phase details: `.planning/milestones/v1.7-ROADMAP.md`

</details>

<details>
<summary>✅ v1.8 Import & Provenance Re-model (Phases 47–51) — SHIPPED 2026-09-23</summary>

**Overview:** A targeted re-model of the import/provenance layer — not a rewrite. Provenance became first-class: every import unit declares its `source` and `method`, so trust is a stated attribute of the row rather than archaeology across `strategy` strings and nullable `oyez_*` columns. On that foundation every argument is born a *candidate* carrying a materialized trust tier and is promoted to *published* through a single review-gated promotion, an operator review queue surfaces everything needing attention, and the corpus import path collapsed into the unified, idempotent, authority-governed import model. The public noun finally aligned to "arguments" and the design system landed last, once the corrected domain language was settled. Sequencing was dependency-ordered and load-bearing throughout.

- [x] Phase 47: Provenance Foundation (6/6 plans) — completed 2026-08-18
- [x] Phase 48: Trust & Lifecycle (10/10 plans) — completed 2026-08-21
- [x] Phase 49: Review Model (12/12 plans) — completed 2026-08-25
- [x] Phase 50: Unified Import Path (7/7 plans) — completed 2026-08-27
- [x] Phase 51: Design System & Noun Alignment (10/10 plans) — completed 2026-09-22

**Shipped with one deliberate gap:** IMPORT-02 (the PDF pipeline path adapting to `import_run` as a peer strategy) was split out of Phase 50 on 2026-08-25 to Phase 999.11, under the corpus-first / PDF-deferred scope decision. 24 of 25 v1.8 requirements validated.

Full phase details: `.planning/milestones/v1.8-ROADMAP.md`

</details>

## Backlog

Standard: all backlog items live here as 999.x entries (`.planning/phases/999.N-slug/`), captured via `/gsd-capture --backlog` and reviewed/promoted via `/gsd-review-backlog`. `.planning/BACKLOG.md` (the flat B-NNN file previously used, 2026-07-01 to 2026-07-09) has been retired and its 14 still-open items migrated below (2026-07-09); 5 items (B-001, B-003, B-004, B-005, B-006) were dropped as already shipped by Phase 24/27, and B-014 was merged into 999.1 as a duplicate capture of the same idea.

**v1.8 note (closed 2026-09-23):** backlog items 999.4 (shared component library), 999.6 (arguments listing style), and 999.8 (Figma design system) were absorbed into Phase 51 (DS-02 / DS-04 / DS-03 respectively). Phase 51 shipped with v1.8, so all three are now **CLOSED — absorbed**; their entries below are kept for provenance only and are not open work. Separately, 999.11 is the reverse direction — a *split out of* v1.8: Phase 50's PDF half (IMPORT-02) moved here on 2026-08-25 rather than shipping in the milestone, per the corpus-first decision.

### Phase 999.2: Share specific utterances via social media (BACKLOG)

**Goal:** [Captured for future planning] Let visitors share a specific utterance (a single speaker turn) from an oral argument to social media, to increase site exposure and utilization. Needs discussion on: what gets shared (permalink to the utterance vs. a rendered card/image), which platforms, and how this interacts with the apolitical-framing hard constraint — an isolated utterance shared out of the argument's full context could read as editorializing even though the underlying transcript content is unchanged.
**Requirements:** TBD
**Plans:** 3/3 plans complete

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Link participant names on job detail page to their edit entries (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-002, added 2026-06-18] On the pipeline job detail page (`/admin/pipeline/[job_id]`), the resolved participants section lists people by name as plain text. Each participant name should link directly to their people editor entry at `/admin/people/[id]` so the operator can navigate from a job result straight to the person's edit form. Confirmed still open (2026-07-09): the page currently only links to a filtered people list, not individual person records.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.4: Frontend design system: shared component library (CLOSED — absorbed into Phase 51, v1.8)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-007, added 2026-07-01] Refactor the frontend to extract common UI patterns (buttons, badges, cards, form inputs) into a shared component library. Reduces duplication between admin and public pages and makes future changes consistent. **Absorbed into v1.8 Phase 51 (DS-02).**
**Requirements:** DS-02 (Phase 51)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: Move speaker avatars to gutters outside the argument body (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-008, added 2026-07-01] Speaker avatars currently appear inline within the chat bubbles on the public argument view. Moving them to fixed gutters (bench left, advocates right) would reinforce the two-sided layout and free up horizontal space for transcript text.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.6: Decide on listing style for cases/arguments (CLOSED — absorbed into Phase 51, v1.8)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-009, added 2026-07-01] The current case list is a basic list of links. No decision has been made on whether it should be cards, a table, grouped by term, searchable, etc. Needs a design decision before implementation. **Absorbed into v1.8 Phase 51 (DS-04).**
**Requirements:** DS-04 (Phase 51)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.7: Improve in-argument section navigation (BACKLOG)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-010, added 2026-07-01] In-argument navigation — jumping between sections (amicus, petitioner, respondent, etc.) within a single argument view. The current section rail exists but could be improved with better scroll-spy, jump links, or a collapsible outline.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.8: Figma design system (CLOSED — absorbed into Phase 51, v1.8)

**Goal:** [Captured for future planning] [Migrated from BACKLOG.md B-011, added 2026-07-01] Implement the design system in Figma to document components, tokens, and layout patterns. Useful before any significant frontend refactor or handoff. **Absorbed into v1.8 Phase 51 (DS-03).**
**Requirements:** DS-03 (Phase 51)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.9: Edit affordance on utterances and speaker popover (BACKLOG)

**Goal:** [Captured for future planning] Give authenticated operators a direct way to correct an individual utterance's text or speaker attribution from the public argument view. Add an operator-only Edit affordance to each utterance and the speaker popover, backed by a new utterance-level edit surface/endpoint and a safe auth-gating pattern for admin-only controls on a public route.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.10: Unify People, Arguments, and Pipeline Runner into one filterable admin screen (BACKLOG)

**Goal:** [Captured for future planning] Generalize the `/admin/review` pattern into the single entry point for operator work, folding today's three separate screens (`/admin/people`, `/admin/arguments`, `/admin/pipeline`) into one filterable surface. The review page's proven pieces to carry over: the Arguments|People tab split, composable status × trust-tier × review-state filters with the unrecognised-value-applies-no-filter allow-list convention (49-05 D1), server-side deterministic sort (D-03), expandable rows whose expanded panel holds per-participant action blocks with a fixed-order action row, and the blockers fallback for a row with zero flagged participants. Open questions for discussion: whether Pipeline Runner is a third tab or a different axis entirely (it is a run-oriented view, not an entity-oriented one, so it may not fit the tab metaphor); how the unified filter set avoids becoming unusable as the axis count grows; and what happens to the existing deep-link targets that other screens point at today (`argumentEditHref` in `admin/review/+page.svelte:215-219` already branches between a pipeline run and an argument, and G-49-4a is an open label defect on exactly that link).
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Provenance:** Raised unprompted by the operator during Phase 49 UAT test 5 (2026-08-24) — "I like the review tab! In fact, I think this will be the basis for a future Phase that folds the existing People, Arguments, and Pipeline Runner into one screen with filtering." Recorded first as a Deferred Follow-Up in `.planning/phases/49-review-model/49-UAT.md` (explicitly NOT a Phase 49 gap — it must not spawn a Phase 49 fix plan), then promoted here. Formerly-open Phase 49 gaps on this same surface are now ALL CLOSED and need no work here: G-49-4a (bare "Edit" link label -> "Edit pipeline run"), G-49-4b ("constituent" terminology leak -> "participant"), G-49-5a/5c/17/18 (narrow-viewport overflow — every admin route now measures 360/360 at 375px). Carry forward instead: `npm run audit:viewport` (49-12 D3) is not wired into CI, and four instances of that overflow defect class were each found by an operator rather than a sweep.

### Phase 999.11: PDF pipeline path adapts to `import_run` as a peer strategy (BACKLOG)

**Goal:** [Split out of Phase 50 on 2026-08-25 at planning time] Make the PDF pipeline path read and write `import_run` as one strategy among peers rather than as the model's privileged shape, keeping its parse/resolve lifecycle intact. This is the PDF half of the original Phase 50 "Unified Import Path" goal. It sits on the **deferred PDF route** (2026-08-18 corpus-first decision): the project returns to PDF work only after corpus import can properly import *and reconcile* case details. Phase 50 ships the corpus half plus the full four-rung authority ordering, so what remains here is specifically the PDF *import path's* adaptation — reading/writing `import_run` directly, dropping the assumption that its own lifecycle fields (`pdf_path`, `prompt_version`) are the run's universal shape, and proving idempotent re-import on a PDF source. Blocked on a real PDF fixture, which does not exist yet — building one is itself work on the deprioritized path (this is the same gap recorded in `.planning/todos/pending/2026-08-18-pdf-provenance-live-fixture-verification.md`). Promote this when the operator confirms the PDF route is back on.
**Requirements:** IMPORT-02
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Provenance:** Not a fresh capture — a scope split. The v1.8 roadmap paired both import halves in Phase 50; the 2026-08-18 corpus-first decision recorded a scope flag on that phase requiring re-scoping at planning time. Resolved 2026-08-25 during `/gsd-plan-phase 50`: the operator chose "corpus-only, split PDF out" so IMPORT-02 lands here rather than sitting silently unplanned inside Phase 50 (which would have failed Phase 50's requirements-coverage gate). The 999.11 slot was vacated when its original occupant was promoted to Phase 39 on 2026-07-12; this is a reuse of that vacant slot, consistent with the 999.9 / 999.10 precedent below.

**Note:** 999.10 (bulk-import historical justices CSV) was removed 2026-07-12 during backlog review — SUPERSEDED/ABSORBED into Phase 29's `import-justices` command per CONTEXT.md D-01, 2026-07-09. 999.17 (FastAPI test lifespan/session-factory failure) was removed 2026-07-12 — FIXED 2026-07-10 during Phase 30 Wave 1, commits `1a99f28a`/`f7ad3082`. 999.1, the earlier 999.9 (README), 999.11, 999.12, 999.13, 999.14, 999.15, 999.16, 999.18, 999.19 were promoted 2026-07-12 to Phases 36, 40, 39, 35, 34, 33, 38, 37, 32, 31 respectively, and folded into the v1.6 milestone on 2026-07-13. The canonical allocator later reused the now-vacant 999.9 slot for the edit-affordance backlog item captured 2026-07-13, and subsequently reused the now-vacant 999.10 slot for the Node.js path-mangling test backlog item captured 2026-07-31 (unrelated to the original 999.10, bulk-import historical justices CSV). See the Phase Details section above for promoted-item scope. That Node.js path-mangling item (the second 999.10) was itself removed 2026-08-18 by the cross-phase UAT audit — VERIFIED FIXED: `api/tests/test_phase38_people_ui_contract.py` runs 23 passed / 0 failed with `node` on PATH. The mangled `C:\workspace\...` path came from the pre-relocation Windows checkout and the WSL relocation resolved it. One caveat carried forward in STATE.md: those 4 tests SKIP rather than fail when `node` is absent from PATH (the default for a pytest run launched outside an nvm shell), so a future regression there would be invisible. The 999.10 slot was vacant again until 2026-08-24, when the canonical allocator reused it a third time for the unified-admin-screen item captured above during Phase 49 UAT (unrelated to either prior 999.10). The 999.11 slot, vacated by its 2026-07-12 promotion to Phase 39, was likewise reused on 2026-08-25 for the PDF-import-path item split out of Phase 50 (unrelated to the original 999.11).
