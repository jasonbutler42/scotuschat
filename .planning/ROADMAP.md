# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- ✅ **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (shipped 2026-06-29)
- ✅ **v1.4 Admin Completeness** — Phases 18–21 (shipped 2026-07-02)
- ✅ **v1.5 Admin Screens Cleanup** — Phases 22–30, 30.1 (shipped 2026-07-12)
- ✅ **v1.6 Backlog Cleanup** — Phases 31–40, 40.1 (shipped 2026-07-29)
- 🚧 **v1.7 Corpus Fidelity & Resolve Rework** — Phases 41–45 (in progress, started 2026-07-29)

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

### 🚧 v1.7 Corpus Fidelity & Resolve Rework (Phases 41–45) — IN PROGRESS

**Overview:** Trust the corpus-import data pipeline end to end on one representative case, rework the Resolve table into a real editing tool, and close two known UI bugs — with a dev-only reset harness to make it all iterable. The corpus track is deliberately gated: a 4-fixture set (one structurally-complex argument plus three chosen for publish/pipeline-state variety) is chosen and operator-confirmed (Phase 41) before any diff or importer change happens. Only the complex fixture goes through Phase 42's diff/fix work; the dev reset tool (Phase 43) reseeds the full four-fixture set so the state-variety fixtures are available for Phase 43/45's publish-unpublish testing. The Resolve rework (Phase 44) and the two bug fixes (Phase 45) are independent of the corpus track and can run in parallel with it. Deployment (DEPLOY-01/03) and the remaining 999.x backlog (999.2–999.8) are explicitly out of scope; so is any full-corpus backfill of Phase 42's importer fixes.

- [x] **Phase 41: Canonical Corpus Fixture Selection** - Analyze the ~7,800-argument ConvoKit dataset and get a 4-fixture set (1 structurally-complex audit fixture + 3 publish-state variants) operator-confirmed for the milestone (completed 2026-07-29)
- [ ] **Phase 42: Corpus Import Fidelity Diff & Fix** - Field-by-field diff of the fixture's raw ConvoKit source against its imported DB rows, then fix every real gap and re-import clean
- [ ] **Phase 43: Dev-Only Reset to Fixture** - Admin action that wipes all argument/people data and reseeds exactly the fixture, hard-gated against ever running outside a dev environment
- [ ] **Phase 44: Resolve Table Rework** - SEED-001's mockup-driven rework: 5 columns, segmented Bench/Advocate toggle, writable Argument Role, always-on Descriptor, consistent extracted hints, bench lock affordance
- [ ] **Phase 45: Deferred UI Bug Fixes** - Unpublished arguments no longer leak into `/cases/` or direct URLs; popover scrollbar stays inside the card boundary

## Phase Details

### Phase 41: Canonical Corpus Fixture Selection

**Goal**: The operator has a named, justified 4-argument fixture set confirmed that every later phase in this milestone references: one structurally-complex argument (the canonical audit fixture Phase 42 diffs against raw ConvoKit source) plus three additional arguments chosen for publish/pipeline-state variety (e.g. unpublished/DRAFT, published, mid-pipeline) so Phase 43's reset tool and Phase 45's publish/unpublish bug work have real states to exercise. This is a decision gate, not an implementation phase — the ~7,800-argument corpus is analyzed for structural complexity signals (speaker count, advocate count, consolidated multi-docket cases, transcript length, re-argument/question-number shape), a ranked shortlist plus one recommendation is presented for the complex fixture, the three state-variety fixtures are proposed separately by state rather than complexity, and the operator explicitly confirms the whole set before Phase 42's diff work or Phase 43's reseed target is locked in. Choosing badly here means auditing a case that exercises none of the importer's hard paths, so the choice is surfaced rather than silently auto-decided.
**Depends on**: Nothing (first phase of v1.7)
**Requirements**: CORPUS-12
**Success Criteria** (what must be TRUE):

  1. A ranked shortlist of candidate arguments drawn from the full ConvoKit dataset is presented, each with the concrete structural-complexity signals that ranked it (speaker count, advocate count, number of source dockets, utterance count).
  2. Exactly one argument is recommended as the canonical complexity fixture, with a stated reason why it exercises more of the importer's paths than the runners-up, plus three additional arguments recommended for publish/pipeline-state variety.
  3. The operator explicitly confirms (or rejects and redirects) the full 4-fixture recommendation before any downstream corpus work begins — no phase proceeds on an assumed fixture set.
  4. The confirmed fixture set is recorded in a durable, referenceable form (ConvoKit conversation id, case name, docket(s), term, argued date, and each fixture's role — complexity fixture vs. which state variant) that Phases 42 and 43 both read instead of re-deriving; Phase 42 reads only the complexity fixture, Phase 43 reads the full set.
  5. No importer code and no database rows are changed by this phase — selection and confirmation only.

**Plans**: 3/3 plans executed
**Wave 1**

- [x] 41-01-PLAN.md — Build `scripts/select_corpus_fixtures.py`: read-only path-coverage scoring over the ConvoKit corpus, apolitical exclusion enforced structurally and at commit time, deterministic top-5 shortlist with per-candidate flag annotations

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 41-02-PLAN.md — Run the full-corpus streaming pass once (persisted aggregate cache), then author `.planning/FIXTURES.md` at status PROPOSED with the four-fixture table plus its ranking evidence

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 41-03-PLAN.md — Blocking operator confirmation of the four-fixture set; record the decision in `.planning/FIXTURES.md` at status CONFIRMED and prove no importer code or database rows changed

### Phase 42: Corpus Import Fidelity Diff & Fix

**Goal**: Everything `import-convokit` drops, mis-maps, or silently defaults for the confirmed fixture is identified, classified, and fixed — so the fixture's rows in `cases`, `arguments`, `utterances`, `people`, `argument_participants`, and `court_tenures` faithfully reflect its raw ConvoKit source. Some current omissions are intentional (the apolitical field allow-list from Phase 29 strips partisan/outcome fields by design, and SCDB data is excluded entirely), so the diff must separate real defects from deliberate exclusions rather than "restoring" fields the apolitical hard constraint forbids. Fixes land on the importer's code path and are proven by re-importing this one fixture; backfilling the other ~7,800 arguments is explicitly out of scope.
**Depends on**: Phase 41 (needs the confirmed complexity fixture — the other 3 fixtures in Phase 41's set are not diffed here, they're reserved for Phase 43/45)
**Requirements**: CORPUS-13, CORPUS-14
**Success Criteria** (what must be TRUE):

  1. A field-by-field comparison of the fixture's raw ConvoKit source against its imported rows exists for all six affected tables, with every field marked faithful, dropped, mis-mapped, or silently defaulted.
  2. Each discrepancy is classified as a real importer defect or an intentional exclusion (apolitical allow-list, schema-absent field, upstream-missing data), with the reason recorded next to it.
  3. Re-importing the fixture after the fixes produces rows where every field flagged as a real defect is now correct, re-verified against the same comparison rather than assumed.
  4. The re-imported fixture's utterance count, speaker roster, and source-docket set match the raw ConvoKit source exactly — no dropped, duplicated, or merged turns.
  5. Corpus-import behavior for arguments other than the fixture is unchanged and no full-corpus backfill is triggered.

**Plans**: 1/5 plans executed

Plans:
**Wave 1**

- [x] 42-01-PLAN.md — Scoped single-conversation import path (`--conversation-id`), landing conversation 15169 in the dev DB (tracer)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 42-02-PLAN.md — Fixture delete-and-reimport routine, with the round trip proven against the real fixture

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 42-03-PLAN.md — Field-by-field fidelity diff generator and the durable `.planning/CORPUS-FIDELITY-DIFF.md` document (CORPUS-13)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 42-04-PLAN.md — Operator batch classification review gate (D-05/D-06) and the approved importer fixes

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 42-05-PLAN.md — Post-fix delete, re-import, and re-verification against the same comparison (CORPUS-14)

### Phase 43: Dev-Only Reset to Fixture

**Goal**: The operator can return a local database to a known four-fixture state from the admin panel in a single action, making the corpus and resolve work iterable instead of requiring hand-built SQL cleanup between attempts. The action is fully destructive by design — it wipes every argument, utterance, person, court tenure, and argument participant, then reseeds exactly Phase 41's four-fixture set plus their associated people — so an environment gate that makes it impossible to fire against a real/production database is a hard requirement of the feature, not follow-up polish. Reseeding runs through the same `import-convokit` path a normal corpus import uses, so Phase 42's importer fixes flow through automatically rather than being duplicated in a hand-rolled seeder.
**Depends on**: Phase 41 (needs the confirmed fixture set as the reseed target). Not blocked by Phase 42 — it reseeds through whatever the current importer produces.
**Requirements**: DEVTOOL-01, DEVTOOL-02
**Success Criteria** (what must be TRUE):

  1. Operator triggers "Reset to Fixture" from the admin panel and, on completion, the database contains exactly the four fixture arguments plus their associated people — zero other arguments, utterances, people, court tenures, or argument participants.
  2. With a production-like environment setting active, the action refuses to execute and says why; the refusal is demonstrated by actually attempting it, not asserted from the code.
  3. The action requires an explicit operator confirmation step that states exactly what will be wiped before anything is deleted.
  4. After a reset, each fixture argument is immediately usable in the normal resolve → approve → publish workflow (its paired admin job exists) with no manual repair, and the state-variety fixtures land in their intended publish/pipeline states (not all reset to the same default state).
  5. A reset run after Phase 42's importer fixes lands the corrected field values on the complexity fixture, confirming the reseed shares the real import path rather than a stale copy of it.

**Plans**: TBD
**UI hint**: yes

### Phase 44: Resolve Table Rework

**Goal**: The Resolve table becomes a real editing tool instead of a display with one overloaded control. Today (Phase 25) the Bench/Advocate `<select>` is the only writable field and the Argument Role column is a read-only mirror of it, so the operator cannot directly say "this speaker is Petitioner's Counsel" — they have to work through a single dropdown that conflates the coarse category with the advocate role. SEED-001's mockup splits these into separate controls, drops the redundant Action column into the Resolved As cell, makes Descriptor always-present (the extracted value is genuinely free-form — sometimes a title, sometimes a location — so a single generic field is intentional), gives every column a consistent extracted-value hint, and adds a lock affordance so a system-derived bench role reads as deliberate rather than broken. SEED-001's own finding is that the backend already accepts every value this needs (`SideEnum`, `ADVOCATE_LABEL_MAP`, `ResolveRowUpdate.side`), so this is expected to be a frontend rework of `ResolveCard.svelte` — to be confirmed at plan time, not assumed.
**Depends on**: Nothing (independent of the corpus track — can run in parallel with Phases 41–43)
**Requirements**: RESOLVE-01, RESOLVE-02, RESOLVE-03, RESOLVE-04, RESOLVE-05, RESOLVE-06
**Success Criteria** (what must be TRUE):

  1. The Resolve table renders exactly five columns — Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor — and every row action (select person, change person) is reachable from inside the Resolved As cell, with no separate Action column anywhere.
  2. Operator sets Bench vs. Advocate with a two-button segmented toggle in which exactly one option reads as active at a time, replacing the dropdown.
  3. For an advocate row, operator can directly pick Petitioner's Counsel or Respondent's Counsel from the Argument Role control and the choice persists across a reload; for a resolved bench row with valid tenure, Argument Role stays non-editable, shows the tenure-derived value, and carries a lock affordance.
  4. A bench row with missing tenure still shows the existing "Missing tenure" warning and Edit-person path, and reads as visibly distinct from the locked valid-tenure state.
  5. Resolved As, Bench/Advocate, Argument Role, and Descriptor each show an "Extracted: …" hint of the raw extracted value, and Descriptor renders on bench rows (as "–") instead of the column disappearing.

**Plans**: TBD
**UI hint**: yes

### Phase 45: Deferred UI Bug Fixes

**Goal**: Two operator-reported defects carried out of v1.6 are closed. They are unrelated in cause and are grouped only because both are small and already root-caused. BUG-01 is a real content-exposure gap: an argument that has not been published still appears in the public `/cases/` list and can be opened directly by URL — publish status must gate both listing and direct access, and the intended direct-access response (404 vs. an explicit not-published state) is a decision to settle before implementing. BUG-02 is a styling/boundary mismatch, already diagnosed: `Popover.Content` in the argument page owns `max-height`/`overflow-y`, but the visible rounded card (background, border, radius) lives on an inner element in `SpeakerPopover.svelte`, so the native scrollbar renders at the edge of the invisible scroll box instead of flush inside the card.
**Depends on**: Nothing (independent of every other phase — can run in parallel)
**Requirements**: BUG-01, BUG-02
**Success Criteria** (what must be TRUE):

  1. An argument in Draft or Unpublished status does not appear in the public `/cases/` list.
  2. Requesting an unpublished argument's URL directly returns the chosen non-content response instead of rendering the transcript, on both in-app navigation and a hard SSR refresh.
  3. Publishing an argument makes it appear in the list and become directly accessible again, with no restart or cache clear needed.
  4. When a Justice popover's content overflows (long bio with Read more expanded), the scrollbar renders flush inside the card's visible rounded boundary.
  5. The popover still shows every field Phase 39 added, with no content truncated or escaping the card.

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
| 42. Corpus Import Fidelity Diff & Fix | v1.7 | 1/5 | In Progress|  |
| 43. Dev-Only Reset to Fixture | v1.7 | 0/0 | Not started | - |
| 44. Resolve Table Rework | v1.7 | 0/0 | Not started | - |
| 45. Deferred UI Bug Fixes | v1.7 | 0/0 | Not started | - |

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

**Note:** 999.10 (bulk-import historical justices CSV) was removed 2026-07-12 during backlog review — SUPERSEDED/ABSORBED into Phase 29's `import-justices` command per CONTEXT.md D-01, 2026-07-09. 999.17 (FastAPI test lifespan/session-factory failure) was removed 2026-07-12 — FIXED 2026-07-10 during Phase 30 Wave 1, commits `1a99f28a`/`f7ad3082`. 999.1, the earlier 999.9 (README), 999.11, 999.12, 999.13, 999.14, 999.15, 999.16, 999.18, 999.19 were promoted 2026-07-12 to Phases 36, 40, 39, 35, 34, 33, 38, 37, 32, 31 respectively, and folded into the v1.6 milestone on 2026-07-13. The canonical allocator later reused the now-vacant 999.9 slot for the edit-affordance backlog item captured 2026-07-13. See the Phase Details section above for promoted-item scope.
