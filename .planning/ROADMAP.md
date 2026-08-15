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
| 29. Historical Corpus Import | v1.5 | 9/9 | Complete | 2026-07-10 |
| 30. Corpus Import Resolve Workflow | v1.5 | 4/4 | Complete | 2026-07-10 |
| 30.1. Close gap AEDIT-04/DASH-02 | v1.5 | 3/3 | Complete | 2026-07-12 |
| 31. Audit ~28 stale DB-gated test fixtures + fix real data leakage into shared dev DB | v1.6 | 8/8 | Complete    | 2026-07-13 |
| 32. Fix CourtTenure FK bookkeeping gap in merge/delete person service paths | v1.6 | 2/2 | Complete    | 2026-07-13 |
| 33. `update_argument_metadata` unique-constraint guard | v1.6 | 4/4 | Complete   | 2026-07-14 |
| 34. Blank case_name/docket_number validation | v1.6 | 4/4 | Complete    | 2026-07-14 |
| 35. `rerun_job` never spawns ingest for locally-uploaded jobs | v1.6 | 3/3 | Complete    | 2026-07-14 |
| 36. Click-to-copy extracted values design pattern | v1.6 | 3/3 | Complete    | 2026-07-15 |
| 37. Represent tenure Seat as a Chief/Associate toggle instead of free text | v1.6 | 5/5 | Complete    | 2026-07-21 |
| 38. Rethink Full Name vs. name-part fields in the people editor | v1.6 | 10/10 | Complete    | 2026-07-27 |
| 39. Bench popover — additional context data for Justices | v1.6 | 9/9 | Complete    | 2026-07-29 |
| 40. README — how to start the local stack | v1.6 | 3/3 | Complete    | 2026-07-14 |
| 40.1. Sanitize docket input to close path-traversal/arbitrary-file-write gap (SUPERSEDED) | v1.6 | 0/0 | Complete (reconciliation, no execution) | 2026-07-29 |
| 41. Canonical Corpus Fixture Selection | v1.7 | 3/3 | Complete    | 2026-07-29 |
| 42. Corpus Import Fidelity Diff & Fix | v1.7 | 5/5 | Complete    | 2026-07-30 |
| 43. Dev-Only Reset to Fixture | v1.7 | 4/4 | Complete    | 2026-07-31 |
| 44. Resolve Table Rework | v1.7 | 9/9 | Complete    | 2026-08-11 |
| 45. Deferred UI Bug Fixes | v1.7 | 2/2 | Complete    | 2026-08-12 |
| 46. Dev Environment Reliability | v1.7 | 6/6 | Complete    | 2026-08-14 |

## Backlog

Standard: all backlog items live here as 999.x entries (`.planning/phases/999.N-slug/`), captured via `/gsd-capture --backlog` and reviewed/promoted via `/gsd-review-backlog`. `.planning/BACKLOG.md` (the flat B-NNN file previously used, 2026-07-01 to 2026-07-09) has been retired and its 14 still-open items migrated below (2026-07-09); 5 items (B-001, B-003, B-004, B-005, B-006) were dropped as already shipped by Phase 24/27, and B-014 was merged into 999.1 as a duplicate capture of the same idea.

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

### Phase 999.9: Edit affordance on utterances and speaker popover (BACKLOG)

**Goal:** [Captured for future planning] Give authenticated operators a direct way to correct an individual utterance's text or speaker attribution from the public argument view. Add an operator-only Edit affordance to each utterance and the speaker popover, backed by a new utterance-level edit surface/endpoint and a safe auth-gating pattern for admin-only controls on a public route.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.10: Node.js path-mangling failure in api/tests/test_phase38_people_ui_contract.py (WSL environment) (BACKLOG)

**Goal:** [Captured for future planning] Fix a pre-existing Node.js subprocess path-join bug affecting 4 tests (`test_personnames_ts_format_cases_match_shared_fixture`, `test_personnames_ts_normalization_cases_match_shared_fixture`, `test_personnames_ts_invalid_cases_raise_matching_error_codes`, `test_personnames_ts_preview_returns_na_until_first_or_last`) in `api/tests/test_phase38_people_ui_contract.py`. Each spawns a Node.js subprocess that fails with `ENOENT` on a mangled path — the WSL-mounted path and the Windows path appear concatenated instead of joined (e.g. `C:\workspace\scotuschat\project\workspacescotuschatprojectapi\tests\fixtures...`). First observed during Phase 42 (42-02, logged in `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md`) and reconfirmed during Phase 43 (43-01, logged in `.planning/phases/43-dev-only-reset-to-fixture/deferred-items.md`) — pre-existing both times, unrelated to either phase's actual changes (confirmed via git diff/stash showing the affected test file untouched by either phase). Needs a future phase/session that owns this test file or the WSL/Windows dev split to fix the Node subprocess path-join logic.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Note:** 999.10 (bulk-import historical justices CSV) was removed 2026-07-12 during backlog review — SUPERSEDED/ABSORBED into Phase 29's `import-justices` command per CONTEXT.md D-01, 2026-07-09. 999.17 (FastAPI test lifespan/session-factory failure) was removed 2026-07-12 — FIXED 2026-07-10 during Phase 30 Wave 1, commits `1a99f28a`/`f7ad3082`. 999.1, the earlier 999.9 (README), 999.11, 999.12, 999.13, 999.14, 999.15, 999.16, 999.18, 999.19 were promoted 2026-07-12 to Phases 36, 40, 39, 35, 34, 33, 38, 37, 32, 31 respectively, and folded into the v1.6 milestone on 2026-07-13. The canonical allocator later reused the now-vacant 999.9 slot for the edit-affordance backlog item captured 2026-07-13, and subsequently reused the now-vacant 999.10 slot for the Node.js path-mangling test backlog item captured 2026-07-31 (unrelated to the original 999.10, bulk-import historical justices CSV). See the Phase Details section above for promoted-item scope.
