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
- 🚧 **v1.9 The Site Becomes Complete** — Phases 52–58 (active)

**Active milestone: v1.9 The Site Becomes Complete** — Phases 52–58. Requirements: `.planning/REQUIREMENTS.md`. Current position: `.planning/STATE.md`.

## Phases

### 🚧 v1.9 The Site Becomes Complete (Phases 52–58) — ACTIVE

**Overview:** Make everything true that has to be true before the site can go live, so that v2.0 is purely the deployment. Data correctness first (justice identity, then undetermined speakers), because search over speaker names before justice dedup would surface the exact duplicate-person bug that work exists to close. Then the corpus actually published, because every surface after it is better verified at real volume than against four fixtures. Then the public surface a reader arrives at — search (backend, precedes the landing page), landing page and About, then plumbing. Analytics is deliberately last and isolated: it introduces the first client-side third-party script and the first `PUBLIC_` env var this codebase has ever had.

- [ ] **Phase 52: Justice Identity** — One person row per justice, joined to the corpus by a verified `oyez_speaker_id`, surviving every fixture reset
- [ ] **Phase 53: Undetermined Speakers & Marker Normalisation** — Treatment D for source-unattributed turns, a PROVISIONAL trust floor, and one canonical form for every whole-turn marker
- [ ] **Phase 54: Publishing at Scale & Verification Debt** — Bulk publish through the existing trust gate, the corpus live, and every surface finally seen at real volume
- [ ] **Phase 55: Search** — Find an argument by case, docket, speaker or term, with a zero-result state that names the coverage boundary
- [ ] **Phase 56: Landing Page, About & Oyez Source Links** — A front door that explains the format, an About page, and a way back to the source transcript
- [ ] **Phase 57: Surface Plumbing** — robots, sitemap, page metadata, favicon, a root error page, and the Admin link off the public nav
- [ ] **Phase 58: Analytics & Privacy** — Cookieless measurement, zero-result search queries on the admin dashboard, and a privacy policy that says what is measured

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

## Phase Details

Active milestone: **v1.9 The Site Becomes Complete** (Phases 52–58). Details for Phases 1–51 live in the per-milestone archives under `.planning/milestones/`.

**Design and analysis already on disk — do NOT re-derive any of it:**

| Artifact | What it already settles |
|---|---|
| `.planning/notes/justice-identity-and-seeding.md` | The join-key decision, the 49-of-114 name-mismatch measurement, why a derivation rule was rejected, the proposed schema and code changes |
| `.planning/notes/justice-identity-mapping-DRAFT.csv` | 114 rows — 65 exact, 45 derived, 4 flagged. **Unverified.** An input to planning, not a deliverable |
| `.planning/notes/undetermined-speaker-display.md` | Treatment D approval, the full-corpus measurements (do not re-run the 900MB pass), the trust decision, the marker vocabulary split |
| `.planning/notes/transcript-rendering-decision-tree.md` | The 10-scenario inventory, the normalisation decision, the settled 50% denominator question, the rules that must not regress |
| Figma file `KICu66PtMLHk4fmxJYPggx`, page **Public**, node `33:2` | The approved Treatment D mockup (`unattributed-speaker-exploration › unattributed-D`) |
| `.planning/positioning/` (seven documents) | `HOMEPAGE-BRIEF.md` content priority, `VOICE.md` copy guidance, `PRINCIPLES.md` non-editorial rules — plus `README.md`, which indexes the Figma homepage concepts and records what has changed since they were drawn |
| `.planning/notes/launch-readiness.md` | The verified public-surface gap inventory and the Admin-link decision |
| `.planning/research/SUMMARY.md` + its four source documents | Stack (no new npm/pip packages), architecture integration map, 8 pitfalls, the analytics/consent legal position |

**Cross-cutting obligation (PLUMBING-07).** `api/tests/test_trust_public_leak_ban.py` derives "the public surface" from hand-maintained lists (`PUBLIC_ROUTER_MODULE_NAMES`, `PUBLIC_SCHEMA_MODULE_PATHS`, `PUBLIC_FRONTEND_PATHS`). It does **not** auto-discover. The requirement is owned by Phase 55 (the first phase adding a new public route), but the obligation applies to **every** phase that adds a public route, schema module or frontend path — Phases 53, 55, 56, 57 and 58 all do. Register in the same phase that adds it, or the apolitical leak ban silently stops covering it.

### Phase 52: Justice Identity

**Goal**: Every justice in the corpus resolves to exactly one person record, joined by a verified stable key that survives a fixture reset, with each name form shown where it belongs.
**Depends on**: Nothing (first phase of v1.9)
**Requirements**: JUSTICE-01, JUSTICE-02, JUSTICE-03, JUSTICE-04, JUSTICE-05, JUSTICE-06
**Success Criteria** (what must be TRUE):

  1. Seeding the justice CSV and then importing the corpus produces exactly one person row per justice — all 114 corpus justices resolve on `oyez_speaker_id`, and a spelling difference between the two sources no longer mints a second row.
  2. A justice's utterance attribution reads the corpus name form (`Byron R. White`) while their bio card reads the fuller CSV form (`Byron Raymond White`); an advocate, who has no display name, still shows their full name unchanged.
  3. Running `reset_to_fixture` and then opening the People directory shows the full justice roster, not an empty bench.
  4. A second row carrying an already-used `oyez_speaker_id` is refused by the database itself, not only by application code.
  5. `John Marshall Harlan, II` renders the avatar initials `JH`, not `JI`.

**Notes**:

  - The mapping draft at `.planning/notes/justice-identity-mapping-DRAFT.csv` already exists (114 rows: 65 exact, 45 derived by first-initial + last-name, 4 flagged). It is **unverified** — this phase verifies and promotes it to authoritative data. It does not re-derive it.
  - The 4 flagged rows need the operator's eye, not an algorithm: the two Harlans (grandfather 1877–1911 vs. grandson 1955–1971), `Salmon P. Chase` vs. the different justice `Samuel Chase`, and `Henry Brockholst Livingston`, whom the CSV files under the first name "Brockholst".
  - A derivation rule was already considered and **rejected** — first-initial abbreviation reproduces 100 of 114 corpus forms, and a rule that is right 88% of the time is the worst outcome available. Do not revisit.
  - Closes the Person-dedup item carried since v1.7 Phase 42. It is not four bad rows; it is 49 of 114, visible as four only because four fixtures are imported.
  - Per the reseed-don't-migrate doctrine, existing duplicates are cleared by the reset, not by a backfill migration.

**Plans**: 6/6 plans executed

Plans:

- [x] 52-06-PLAN.md

**Wave 1**

- [x] 52-01-PLAN.md — Tracer: the identity spine — verified mapping artifact, migration 0032 (`display_name` + partial unique index), importer keyed on `oyez_speaker_id`, `speaker_name` COALESCE

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 52-02-PLAN.md — Server-computed avatar initials on both public payloads; both client splitters deleted; `JI` → `JH` proven in a real browser
- [x] 52-03-PLAN.md — Admin person page: Corpus Display Name and Oyez Speaker ID as read-only rows, absent from the write path
- [x] 52-04-PLAN.md — `reset_to_fixture` seeds the bench after its TRUNCATE; fail-before-destroy pre-flight; stale `created_at` skew fixed

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 52-05-PLAN.md — Reset per-fixture progress and evidence-based failure copy via one dev-only fixture-state GET
- [ ] 52-06-PLAN.md — Converge the third initials splitter in admin `ResolveCard.svelte` onto the single server-side `derive_initials`, completing D-12 codebase-wide *(added 2026-09-25 by operator decision after 52-02 surfaced it)*

**UI hint**: yes

### Phase 53: Undetermined Speakers & Marker Normalisation

**Goal**: A turn the source could not attribute is shown honestly rather than guessed at or rendered broken, such arguments are publishable, and every transcription marker reads the same way everywhere.
**Depends on**: Phase 52 (both rework corpus import and person resolution; Treatment D is best proven by a reseed against a deduplicated bench)
**Requirements**: SPEAKER-01, SPEAKER-02, SPEAKER-03, SPEAKER-04, SPEAKER-05, SPEAKER-06, SPEAKER-07, SPEAKER-08
**Success Criteria** (what must be TRUE):

  1. An utterance whose corpus speaker is a `type: "U"` sentinel renders as Treatment D — a narrower bubble centred between two reserved-but-empty rails, labelled "undetermined speaker" — read from a fact stored on the utterance at import, never re-derived from `raw_speaker_label`. No literal `<INAUDIBLE>` string reaches the page.
  2. Hovering an undetermined bubble reveals a dashed question-mark avatar in **both** rails, and clicking either opens an explanation card in the same shape as the speaker-bio card.
  3. An argument containing sentinel speakers and no other blocker publishes with no per-argument override, while an argument more than 50% undetermined refuses to publish until the operator deliberately intervenes.
  4. A whole turn that is only an inaudible marker but carries a known speaker renders as that speaker's ordinary attributed bubble with the marker as its body — the attribution the source supplied is no longer discarded — while laughter inside a speaker's turn still splits into speech plus a separate room-event row, and Voice Overlap is still a stage direction.
  5. Every whole-turn marker in the curated vocabulary shows one canonical form wherever it appears, and a marker inline within a spoken sentence is left exactly as the source wrote it.

**Notes**:

  - Treatment D is **approved**, with the mockup at Figma `KICu66PtMLHk4fmxJYPggx` › page Public › `unattributed-speaker-exploration › unattributed-D`, node `33:2`. Treatments A, B and C were considered and not chosen; C was rejected deliberately because it asserts a side the source does not support. Do not re-explore.
  - The measurements are done: 88,102 unattributed utterances (5.18%), 4,638 of 7,817 conversations affected, ~13,221 whole-turn inaudibles with a known speaker, 31 distinct verbatim marker forms, 6 arguments above 50%. The full 900MB pass is recorded in the note — **do not re-run it to rediscover them.**
  - The 50% denominator question is **already settled by measurement**: all-turns and excluding-room-events yield the identical 6 arguments. Confirm the implementation denominator, do not re-litigate the boundary.
  - Consecutive undetermined turns (1.1%) are **WON'T FIX** by operator decision — shown honestly rather than hidden.
  - `detect_stage_direction` already returns the canonical label and the importer discards it one line later. Normalising is a matter of keeping that value, not building a normaliser.
  - The italic and 70%-opacity treatment for the "undetermined speaker" label is approved, and must land as **design-system additions** in `app/src/app.css` and `.planning/codebase/DESIGN-SYSTEM.md` — not inline one-offs. Phase 51's whole point was that nothing in `app/src` carries a raw value; italic is a new type axis.
  - Trust stays operator-facing. PROVISIONAL must never reach a public response — the reader-facing honesty is Treatment D's explanation card. If this phase touches a public schema module or frontend path not already in the leak-ban lists, register it here (PLUMBING-07).

**Plans**: TBD
**UI hint**: yes

### Phase 54: Publishing at Scale & Verification Debt

**Goal**: The corpus is actually live, and every surface has been seen working at real volume instead of against four fixtures.
**Depends on**: Phase 53 (the PROVISIONAL floor and the >50% gate are what make the corpus publishable at all)
**Requirements**: PUBLISH-01, PUBLISH-02, PUBLISH-03, PUBLISH-04, PUBLISH-05, VERIFY-01, VERIFY-02
**Success Criteria** (what must be TRUE):

  1. `pipeline bulk-publish --dry-run` reports exactly which arguments it would publish and leaves the database untouched; the real run publishes them and reports a per-row outcome the operator can read.
  2. Bulk publish interrupted partway and re-run picks up where it stopped with no checkpoint table, publishes nothing twice, and completes against the full corpus without exhausting PgBouncer.
  3. Every newly-published argument carries the status-log entry `publish_argument` writes, and zero UNCERTAIN arguments are published — the trust gate was not bypassed by a bulk `UPDATE`.
  4. The corpus is published — every argument eligible under the trust rules, with only the >50%-undetermined arguments held back.
  5. A real term page renders correctly at real volume (~108 arguments, not four fixtures), and the three never-observed UAT behaviours plus Phase 49's outstanding live-browser checks have each been watched working on screen.

**Notes**:

  - Follow the existing `recompute-trust` / `prune-runs` command template in `pipeline/__main__.py`. This is a standard pattern with precedent in the codebase, not new territory.
  - The known trap: looping `publish_argument` over 7,811 rows is 7,811 transactions, 7,811 trust recomputations and 7,811 PgBouncer round trips. Chunk the commits; make it resumable **by construction** (`WHERE status != 'PUBLISHED'`), not via a checkpoint table. Do not reach for a raw bulk `UPDATE` under performance pressure — that silently readmits the gate Phase 48 exists to enforce.
  - VERIFY-01's three behaviours: the failed-run error panel (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder with its per-row Save gate, and the non-interactive avatar for an unresolved utterance. The third overlaps Treatment D from Phase 53 — verify the behaviour that actually ships.
  - VERIFY-02's checks are enumerated in `49-EVIDENCE.md` §9, now under `.planning/milestones/v1.8-phases/49-review-model/`. They were blocked on sandbox `.env` access at the time; browser tooling works now.
  - `/arguments/term/1955` has never been rendered with real content, in either layout or query performance. That is the point of PUBLISH-05.

**Plans**: TBD

### Phase 54.1: Justice Portraits & Biographical Enrichment (INSERTED)

**Goal**: Every justice carries a sourced portrait and a sourced biography, joined on the stable corpus key, and the speaker card renders both without asserting anything about the person.
**Depends on**: Phase 52 (`oyez_speaker_id` is the join key and the asset filename stem) — sequenced after Phase 54 so the corpus is fully published first. Must precede Phase 56, whose About page carries the image attribution this phase lands.
**Requirements**: PERSON-01, PERSON-02, PERSON-03, PERSON-04, PERSON-05, PERSON-06
**Success Criteria** (what must be TRUE):

  1. Every justice with a delivered portrait renders that portrait in the speaker card; a justice without one renders the existing coloured-initials fallback, and neither reads as broken or second-class.
  2. Portraits are stored and retrieved by `oyez_speaker_id`, so running `reset_to_fixture` and re-importing leaves every portrait attached to the same person it was before.
  3. A justice's card shows their education and career history drawn verbatim from the FJC Biographical Directory — no generated prose, no summary, no characterisation anywhere on the surface.
  4. An advocate's card renders through the same component with the same section order; the sections for which no advocate data exists are absent, not filled with placeholder or "not available" text.
  5. Every delivered image has a recorded source URL, licence, and creator, queryable without opening the files.
  6. The longest career on record (Kagan, 14 entries) and the shortest (Shiras, 2 entries) both render correctly at 375px and at desktop width.

**Notes**:

  - Two external deliverables gate this phase, both commissioned 2026-09-24: the portrait set (spec: `.planning/notes/person-photo-asset-spec.md`) and the bio card design (brief: `.planning/notes/bio-card-figma-brief.md`). Neither is produced by this phase; this phase ingests and implements them.
  - **The portrait set has been delivered and validated** — 114 WebP files plus `manifest.csv` at `/home/jason/scotuschat/person-photos`, **outside this repository**. Every mechanical check passes and every licence is public domain. See `.planning/notes/person-photo-delivery-validation.md` for the report and the three open operator items: three unverified-but-plausible PD claims, one tight crop (`j__byron_r_white`), and background-luminance variance that will make ~12 engravings read as bright discs against the dark page.
  - The Figma bio card mockup is still outstanding as of 2026-09-24.
  - **Bio data is already on disk and needs no external sourcing.** `data/corpus/judges.csv` is the FJC Biographical Directory — 4,070 federal judges, 201 columns, referenced nowhere in the codebase today. 113 of 115 SCOTUS justices match on last+first name; the two misses are name-form only (`Brockholst Livingston` → FJC "Henry Brockholst"; `Fred Vinson` → FJC "Frederick Moore") and are fixed by hand, not by a matching rule.
  - `Professional Career` is filled for 113/113 — a semicolon-delimited chronological career list, median 343 characters / 6 entries, max 754 characters / 14 entries.
  - **Do not generate prose bios from this data.** Assembling and formatting sourced fields is presentation; writing a paragraph from them makes editorial choices about what mattered, which the apolitical constraint forbids. It would also put unverifiable text into a corpus where everything else traces to a source.
  - **The open design question is P-06.** The popover forbids truncation — no clamp, no "Read more", no internal scroll — and a 754-character career history does not fit a popover on a 375px viewport. The Figma brief asks for the tradeoff to be shown, not silently resolved; the three candidate routes are splitting to a dedicated person page, restructuring the career string as a dated timeline, or amending P-06 specifically for list-shaped content. Whichever lands, it amends a locked decision and needs saying so.
  - `people.photo_url` is a single scalar column and the uploader writes one object per person, so a responsive image set cannot be stored without a schema change. Single-file delivery is a constraint, not a preference.
  - The bench/advocate asymmetry was ruled on by the operator 2026-09-24: photographs aid comprehension more than they risk partisanship, and asymmetric source data is not asymmetric treatment. The CLAUDE.md apolitical constraint was rewritten the same day to say so. Do not re-litigate.
  - `Gender` and `Race or Ethnicity` are present in the FJC data for all 113. Whether either appears on a public card is an unresolved operator decision, not a default.

**Plans**: TBD
**UI hint**: yes

### Phase 55: Search

**Goal**: A reader can find an argument by case name, docket number, speaker or term, and when nothing matches they learn why rather than hitting a dead end.
**Depends on**: Phase 52 (a speaker-name search before justice dedup would surface the exact duplicate-person bug Phase 52 closes) and Phase 54 (real volume to search against)
**Requirements**: SITE-03, SITE-04, SITE-05, SITE-06, PLUMBING-07
**Success Criteria** (what must be TRUE):

  1. Searching a case name, a speaker name or a term returns the matching published arguments, and a partial or slightly-misspelled case or speaker name still finds them.
  2. A docket number matches exactly or by normalised-exact only — a one-character near-miss never returns a confidently wrong argument, because a one-character edit is a different real docket.
  3. No unpublished argument ever appears in a search result, proven against a deliberately-unpublished row rather than asserted — and the new search route and response schema are registered in `test_trust_public_leak_ban.py`'s coverage lists, which do not auto-discover.
  4. A results surface shows enough per row for a reader to choose between hits, with bounded pagination rather than the whole corpus.
  5. A search that matches nothing states the OT 1955–2019 coverage boundary plainly — the one place a reader needs that fact to interpret what they are seeing.

**Notes**:

  - **DECISION REQUIRED IN THIS PHASE, not a research gap:** `.planning/research/STACK.md` and `.planning/research/ARCHITECTURE.md` genuinely disagree. STACK.md recommends `pg_trgm` GIN trigram **plus** a weighted `tsvector`/GIN combined column for a single ranked multi-field search; ARCHITECTURE.md holds that trigram alone is adequate at ~7,800 rows and explicitly cautions against `tsvector` as premature optimisation. **They agree trigram is needed.** Settle the `tsvector` question before engineering starts, ideally against a performance measurement rather than an opinion.
  - `unaccent` availability on DigitalOcean Managed PostgreSQL is **unverified**. Confirm with `SELECT * FROM pg_available_extensions` before any migration depends on it.
  - Search is a pure-read query added to the **existing** `api/routers/arguments.py`, not a new router, reusing the `ArgumentListItem` schema and the exact same two-predicate published gate (`published_at IS NOT NULL AND status == PUBLISHED`) every other public route uses. Reimplementing that gate is the highest-consequence pitfall in the milestone — the same bug class as the already-fixed BUG-01.
  - Relevance ranking is an **anti-feature** here: it editorialises which case matters. Out of scope by constraint, not by budget.
  - No external search engine. Postgres is sufficient at ~7,800 rows.

**Plans**: TBD
**UI hint**: yes

### Phase 56: Landing Page, About & Oyez Source Links

**Goal**: A first-time visitor arrives somewhere that explains the format, can read what this project is and is not, and can get from any argument back to its source on Oyez.
**Depends on**: Phase 55 (the homepage brief is search-forward and the landing page leans on search existing; Phase 54.1, whose image provenance data the About page's attribution draws on)
**Requirements**: SITE-01, SITE-02, SITE-07
**Success Criteria** (what must be TRUE):

  1. `/` serves a landing page following `HOMEPAGE-BRIEF.md`'s content priority — format-first, with no coverage claim anywhere and a quiet note that the archive is incomplete and being extended.
  2. Nothing on the landing page ranks, features or counts arguments in a way that implies importance — no trending, no most-viewed, no prominent coverage statistic.
  3. An About page states scope, licensing, maintainer and non-goals in the project's own voice.
  4. Every published argument carries a working link to its source transcript on Oyez, built from the `external_id` lineage captured in Phase 47 and spot-checked against real Oyez URLs rather than assumed to resolve.

**Notes**:

  - `.planning/positioning/` holds seven documents from 2026-07-09, **none superseded**, indexed by `README.md`. `HOMEPAGE-BRIEF.md` carries the content priority and success criteria; `VOICE.md` has copy guidance and About-page content already drafted; `PRINCIPLES.md` states the non-editorial boundary as rules. Build against these — do not re-derive the positioning.
  - The Figma homepage exploration (file `9PDECvbdHM2vYVxt3SCwru`, page "Homepage concepts - positioning pass", node `4060:2`, three concepts) is **starting material, not a shortlist**. Operator, 2026-09-23: "That exploration did not have any conclusions. We should use it as a starting point not as a place where we are ready to make a lot of decisions."
  - The concepts are stale in three known ways recorded in `positioning/README.md`: they feature OT 2023 cases that do not exist in the data, they assume a search that did not exist when drawn, and their transcript preview predates Phase 51's shipped Style B2. Current transcript source of truth is Figma `KICu66PtMLHk4fmxJYPggx`, page Public.
  - Oyez links are a link template over data that already shipped in Phase 47 — not new collection.
  - Register the new public frontend paths in the leak-ban coverage lists in this phase (PLUMBING-07, owned by Phase 55).
  - Page metadata for these new pages lands in Phase 57 (PLUMBING-03), which covers every public page at once.

**Plans**: TBD
**UI hint**: yes

### Phase 57: Surface Plumbing

**Goal**: The site is legible to crawlers and link previews, and no URL or missing asset produces a broken page.
**Depends on**: Phase 56 (metadata and the sitemap need every public route to exist first)
**Requirements**: PLUMBING-01, PLUMBING-02, PLUMBING-03, PLUMBING-04, PLUMBING-05, PLUMBING-06
**Success Criteria** (what must be TRUE):

  1. `robots.txt` is served, and the sitemap lists every published argument and **only** published arguments, generated at request time from the same publish predicate every other public route uses — so it reflects the corpus as it stands after a bulk publish rather than as it was at build time.
  2. Every public page carries its own `<title>`, meta description and Open Graph tags, so a shared link shows a real preview instead of nothing.
  3. A page load no longer 404s on the favicon.
  4. Any bad URL — not only one under `/arguments` — lands on the project's own error page rather than SvelteKit's default.
  5. The public navigation no longer advertises the Admin surface; `/admin` is reached by typing it.

**Notes**:

  - Sitemap is a SvelteKit `+server.ts` endpoint with a short cache TTL — not a build-time artifact (stale the moment bulk publish runs) and not served from FastAPI (that breaks the server-load-function discipline). Protocol limits are 50,000 URLs / 50MB, so this corpus needs no sitemap index.
  - Per-page metadata uses native `svelte:head`. No library needed.
  - Removing the Admin link is not a security fix — auth already gates the page. Nothing reader-facing should advertise an operator surface (operator decision, 2026-09-23, `launch-readiness.md`).
  - Register any new public route the sitemap or robots endpoint introduces in the leak-ban coverage lists (PLUMBING-07, owned by Phase 55).

**Plans**: TBD
**UI hint**: yes

### Phase 58: Analytics & Privacy

**Goal**: The operator can see what visitors look for — above all what they searched for and did not find — without the site storing anything on a visitor's device and without any of it reaching a public surface.
**Depends on**: Phase 55 (search must exist to capture queries from) and Phase 57 (the public surface is complete and the privacy page joins it)
**Requirements**: ANALYTICS-01, ANALYTICS-02, ANALYTICS-03, ANALYTICS-04, ANALYTICS-05
**Success Criteria** (what must be TRUE):

  1. Page views and referrers are recorded on public pages, and no analytics script loads on any `/admin/*` route.
  2. The chosen tool has been **observed in a browser** writing no cookie, no `localStorage` entry, no `IndexedDB` entry and reading no fingerprinting signal — and the consent determination is written down with its jurisdictional caveats, rather than resting on the vendor's "cookieless" label.
  3. The admin dashboard lists zero-result search queries and distinguishes an out-of-range query (a genuine content gap, needing the deferred PDF route) from an in-range one (a search-quality bug, since coverage in range is essentially complete).
  4. No case, docket or speaker identity appears as an event property, and no search or popularity data reaches any public surface.
  5. A privacy policy page states plainly what is measured and what is not.

**Notes**:

  - **This phase is last and isolated on purpose.** It introduces the first client-side third-party script in this codebase and the first `PUBLIC_` env var it has ever had. That is distinct from — not a violation of — the standing rule that `FASTAPI_BASE_URL` stays server-only. Treat it as a change in kind, not degree.
  - Vendor choice is an open **operator** decision. GoatCounter is the researched candidate (free tier, no `document.cookie`, no `localStorage`, no persistent client id, no new backend); Plausible, Fathom and self-hosted Umami are documented alternatives. GA4, Meta Pixel, ad-tech tag managers and cookie-consent platform tooling are all explicitly excluded.
  - The consent research is done and holds: the EU ePrivacy trigger (Art. 5(3), per EDPB's October 2024 guidelines) is *storage of, or access to, information on the device* — not "analytics" and not "personal data" — so genuinely storage-free tooling falls outside the consent requirement. Real caveats to carry into the written determination: CNIL's audience-measurement exemption is French-specific soft law whose framework changes 1 Jan 2026; the UK ICO reads this more strictly with no equivalent carve-out and its PECR guidance is mid-consultation; and this is cross-checked secondary sources, **not legal advice**.
  - A privacy policy page is required regardless of whether a consent UI is.
  - Attaching case, docket or speaker identity as an event property would recreate the banned cross-case-statistics anti-feature through analytics taxonomy rather than through code. A public "trending" or "most searched" surface is an anti-feature for the same reason trust tiers never reach a public response.
  - Search data stays operator-facing. The public "request a case" form is deferred to Phase 999.12 — promote it only if logged-query data proves insufficient.
  - Register the privacy policy page's frontend path in the leak-ban coverage lists (PLUMBING-07, owned by Phase 55).

**Plans**: TBD
**UI hint**: yes

## Progress

**v1.9 The Site Becomes Complete** — 0/7 phases complete

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 52. Justice Identity | 6/6 | In Progress|  |
| 53. Undetermined Speakers & Marker Normalisation | 0/? | Not started | - |
| 54. Publishing at Scale & Verification Debt | 0/? | Not started | - |
| 54.1. Justice Portraits & Biographical Enrichment (INSERTED) | 0/? | Not started | - |
| 55. Search | 0/? | Not started | - |
| 56. Landing Page, About & Oyez Source Links | 0/? | Not started | - |
| 57. Surface Plumbing | 0/? | Not started | - |
| 58. Analytics & Privacy | 0/? | Not started | - |

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

### Phase 999.12: "Request a case" from the zero-result search state (BACKLOG)

**Goal:** [Captured for future planning] When a search returns nothing, offer the visitor a way to request that argument, raising a notification on the admin dashboard to help prioritise what gets added next. Captured 2026-09-23 during v1.9 scoping, where the operator chose analytics-only for v1.9 and asked that the form itself be revisited later.

**Why it was deferred, not dropped:**

- It is the project's **first public write path**. CLAUDE.md states "the website is never interactive for end users", PROJECT.md lists "user accounts or public contributions" under Out of Scope, and Architecture Rule 1 is "FastAPI is read-only". Building it is a deliberate deviation from three stated constraints — not forbidden, but a decision rather than a side effect.
- It brings a spam surface on an unauthenticated public form, and PII if contact details are captured, which interacts with the privacy-policy work v1.9 is already doing.
- **Most zero-result searches will be unfulfillable.** The corpus holds ~7,817 arguments across OT 1955-2019 — roughly 120 per term, essentially complete coverage for that range. So a search returning nothing is almost always (a) a case outside 1955-2019, overwhelmingly post-2019, which needs the deferred PDF route in Phase 999.11; (b) a case that IS in range but did not match, which is a **search-quality bug**, not a content gap; or (c) a misspelling. A request queue would mostly collect asks that cannot be actioned until 999.11 is revived.

**What to check before promoting this:** v1.9's zero-result search analytics should already surface demand, and it does so with no write path, no spam surface and no PII. Promote this only if the logged-query data proves insufficient — specifically, if intent strength (someone cared enough to ask) turns out to matter beyond what query volume shows. The in-range zero-result queries are the more urgent signal either way, because those are matching bugs.

**Requirements:** TBD
**Plans:** 0 plans

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Provenance:** Raised by the operator during v1.9 milestone scoping (2026-09-23) alongside the decision to log search queries for prioritisation. Operator chose analytics-only for v1.9 and asked explicitly for a backlog item to revisit the form.

**Note:** 999.10 (bulk-import historical justices CSV) was removed 2026-07-12 during backlog review — SUPERSEDED/ABSORBED into Phase 29's `import-justices` command per CONTEXT.md D-01, 2026-07-09. 999.17 (FastAPI test lifespan/session-factory failure) was removed 2026-07-12 — FIXED 2026-07-10 during Phase 30 Wave 1, commits `1a99f28a`/`f7ad3082`. 999.1, the earlier 999.9 (README), 999.11, 999.12, 999.13, 999.14, 999.15, 999.16, 999.18, 999.19 were promoted 2026-07-12 to Phases 36, 40, 39, 35, 34, 33, 38, 37, 32, 31 respectively, and folded into the v1.6 milestone on 2026-07-13. The canonical allocator later reused the now-vacant 999.9 slot for the edit-affordance backlog item captured 2026-07-13, and subsequently reused the now-vacant 999.10 slot for the Node.js path-mangling test backlog item captured 2026-07-31 (unrelated to the original 999.10, bulk-import historical justices CSV). See the Phase Details section above for promoted-item scope. That Node.js path-mangling item (the second 999.10) was itself removed 2026-08-18 by the cross-phase UAT audit — VERIFIED FIXED: `api/tests/test_phase38_people_ui_contract.py` runs 23 passed / 0 failed with `node` on PATH. The mangled `C:\workspace\...` path came from the pre-relocation Windows checkout and the WSL relocation resolved it. One caveat carried forward in STATE.md: those 4 tests SKIP rather than fail when `node` is absent from PATH (the default for a pytest run launched outside an nvm shell), so a future regression there would be invisible. The 999.10 slot was vacant again until 2026-08-24, when the canonical allocator reused it a third time for the unified-admin-screen item captured above during Phase 49 UAT (unrelated to either prior 999.10). The 999.11 slot, vacated by its 2026-07-12 promotion to Phase 39, was likewise reused on 2026-08-25 for the PDF-import-path item split out of Phase 50 (unrelated to the original 999.11).

### Phase 999.13: Seed advocates into the baseline fixture (BACKLOG)

**Goal:** [Captured for future planning] Do for advocates what Phase 52 does for justices: seed them into the launch fixture as identified people with per-argument side and a normalised role, so the baseline database is complete on both sides of the bench rather than only the bench. Captured 2026-09-25 during Phase 52 execution, when the operator described the launch dataset he wants — every corpus argument, every justice, and as much advocate data as the corpus supports, all populated by an idempotent script rather than manual work.

**Why this is a real gap, not an oversight:**

- **Nothing on the roadmap seeds advocates.** They appear across the roadmap only as *rendering* concerns — their speaker cards, the unresolved-advocate role placeholder, the bench/advocate photograph asymmetry ruled on 2026-09-24. Phases 55-58 are Search, Landing Page, Surface Plumbing and Analytics. No phase does for advocates what 52-01 (identity mapping) and 52-04 (seed on reset) do for justices.
- **The scale is the inverse of the justices.** `data/corpus/speakers.json` holds 114 justice entries of whom 35 actually speak; it holds **9,535 advocate entries, of whom 8,944 actually speak**. The bench is the small half of the problem.
- **It blocks the launch fixture the operator described.** An idempotent `reset_to_fixture` that seeds every argument and every justice but no advocates produces a database where most speakers in most arguments are unresolved.

**What the corpus actually supports — check this before scoping:**

| | Justices | Advocates |
|---|---|---|
| Roster entries in `speakers.json` | 114 | 9,535 |
| Who actually speak in `utterances.jsonl` | 35 | 8,944 |
| Structured name parts | yes — `supreme_court_justices_sections.csv` | **no** |
| Per-argument side | yes | yes |
| Role | tenure-derived | free text, needs normalising |

- **Advocates have no structured name parts and no second source.** Every non-justice entry in `speakers.json` is exactly `{"name": "Harry F. Murphy", "type": "A"}` — 9,535 of 9,535 carry only those two keys. There is no advocate equivalent of the justices CSV. So advocate `first_name`/`middle_name`/`last_name`/`name_suffix` cannot be populated from this corpus at all, and advocates will permanently resolve through `derive_initials`'s D-13 `full_name` fallback (built in 52-02, already correct for this case). Any plan promising structured advocate names needs a data source that does not currently exist.
- **Advocate roles need normalising before they are shown.** `conversations.json` carries 20,601 advocate appearances with a per-case `role` string. 7,558 are the literal `"inferred"`; the remainder is a long free-text tail expressing a handful of concepts in hundreds of spellings — `"on behalf of the Petitioner"` (759), `"for petitioner"` (562), `"for the petitioner"` (466), `"Argued the cause for the petitioner"` (351), `"argued the cause for Petitioner"` (185), and so on. Seeding these raw would put hundreds of near-duplicate role labels on the public site. The normalisation is the real work in this phase, and it is a domain judgment call (which spellings collapse to which canonical role) rather than a mechanical transform.
- **`side` is already clean.** Each advocate appearance carries a `side` integer alongside the role string, so petitioner/respondent placement does not depend on parsing the free text.

**Apolitical-constraint note:** advocates render through the same component, in the same section order, at the same visual weight as justices — CLAUDE.md's identical-treatment rule. Sections for which no advocate data exists are absent, not filled with placeholder text. The absence of structured name parts for advocates is asymmetric *source data*, which the 2026-09-24 ruling explicitly distinguishes from asymmetric *treatment*. Do not re-litigate that; do not invent advocate data to balance a layout.

**What to check before promoting this:**

- Whether the PDF route (999.11) is live, since post-2019 arguments bring advocates the ConvoKit corpus does not carry, and a seeding design that assumes corpus-only input would need reworking.
- Whether advocate identity needs a stable join key the way justices needed `oyez_speaker_id`. The corpus speaker ids for advocates are slug-form (`harry_f_murphy`) and appear stable within the corpus, but they have not been verified for collisions the way Phase 52 verified the justice ids bidirectionally. That verification is a prerequisite, not an implementation detail — it is exactly what 52-01 had to do first.
- Whether the role normalisation should ship as operator-reviewable mapping data (the shape 52-01 used for `justice_identity_mapping.csv`) rather than as logic buried in the importer.

**Requirements:** TBD
**Plans:** 0 plans

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Provenance:** Surfaced by Claude on 2026-09-25 while the operator was describing the launch fixture he wants during Phase 52 Wave 2. The operator confirmed the gap was real and asked for it to be backlogged rather than scoped into v1.9. Corpus figures above were measured directly against `data/corpus/speakers.json`, `conversations.json` and `utterances.jsonl` on the same date, not estimated.

### Phase 999.14: Evaluate prerendering the public site to static output (BACKLOG)

**Goal:** [Captured for future planning] Evaluate moving the public read-only site from a live Node server + FastAPI + Postgres deployment to prerendered static output, built locally or in CI and pushed to hosting, with the admin surface and the API running only on the operator's machine. Captured 2026-09-25 during Phase 52 execution, when the operator raised the idea and asked whether it was crazy. It is not — the project has been converging on it — but it is an architecture decision that touches three stated rules and one unplanned phase, so it needs an ADR or a discuss-phase rather than a config change.

**Why it fits this project better than it would fit most:**

- **Architecture Rule 2 already did the hard part.** Every FastAPI call goes through a `+page.server.ts` server load function. Those are exactly what SvelteKit executes at prerender time — switching from request-time to build-time execution needs no restructuring of the data-access layer. The load functions run earlier, not differently.
- **The published gate gets stronger, not weaker.** Today it is a runtime predicate (`published_at IS NOT NULL AND status == PUBLISHED`) every public route must remember to apply; Phase 55's notes call reimplementing it "the highest-consequence pitfall in the milestone", and it is the same bug class as the already-fixed BUG-01. Under prerendering an unpublished argument simply never gets a page emitted — there is no route to leak from. That is a structural guarantee rather than a tested one.
- **The site is genuinely read-only.** CLAUDE.md: "the website is never interactive for end users." PROJECT.md puts user accounts and public contributions out of scope. Architecture Rule 1 makes FastAPI read-only. The precondition static generation needs is already a constraint.
- **Content only changes when the operator runs the pipeline**, which is offline-only by constraint. There is no live data to go stale between builds.
- **Production collapses to files.** No Node server, no Postgres, no PgBouncer, and the `statement_cache_size=0` asyncpg workaround stops being a production concern. The admin surface (7 route trees) and the API become local-only — which matches the operator's stated stance that pre-launch data is disposable and launch data is script-populated.

**Use SvelteKit's own static adapter — NOT Eleventy.** The idea as first raised named Eleventy. That would discard Phase 51's design system, the Svelte 5 component library, `SpeakerPopover`, and Phase 52's server-computed initials work, to arrive at the same place. The project is currently on `@sveltejs/adapter-node` with no `prerender` declared anywhere; the change is `@sveltejs/adapter-static` plus `export const prerender = true`, not a rewrite. Any plan promoted from this item must start there.

**Known costs — scope against these, not around them:**

- **7,817 argument pages** to prerender, averaging ~218 utterances each (1,700,789 utterances total). Build time is the open question — plausibly tens of minutes. Acceptable for a scheduled CI build, annoying for a one-word fix. Measure before committing.
- **No hotfixing content without a rebuild.** Mostly theoretical given the pipeline is already offline-only.
- **999.12 ("request a case")** is the one known future exception to read-only. It would need a form service or serverless function. That does not break static output, but it should be decided knowingly rather than discovered later.
- The **admin surface never deploys**. That is a simplification, but it means any future need for a hosted admin is a reversal, not an extension.

**THE TIMING CONSTRAINT — read this before scheduling anything else:**

**Phase 55 (Search) is the forcing function, and it is close.** Its notes already carry an unresolved *"DECISION REQUIRED IN THIS PHASE"* between `pg_trgm` trigram and a weighted `tsvector`/GIN column, plus an unverified `unaccent` availability question on DigitalOcean Managed Postgres. If the site goes static, **that entire decision is moot** — search becomes a client-side index, and the trigram-vs-tsvector debate never needs settling.

And the scale makes it easy rather than hard: Phase 55 searches *arguments* by case name, docket number, speaker and term — **~7,800 records, not 1.7M utterances**. An index over 7,800 argument summaries is a few megabytes; Pagefind or an equivalent handles it comfortably. The thing that normally rules out static-site search is not in scope here.

So the cheapest moment to decide is **before Phase 55 is planned**. Deciding after it ships a Postgres search means replacing working, tested code.

**What to check before promoting this:**

- Measure a prerender of the full 7,817-page set on real hardware. Build time is the only genuinely unknown cost.
- Confirm the four public route trees (`/`, `/arguments`, `/arguments/[slug]`, `/arguments/term`, `/attributions`) have no request-time dependency that prerendering cannot satisfy.
- Decide where Phase 58's analytics lands — client-side is fine on static, but it should be chosen rather than inherited.
- Settle whether the admin surface stays local-only permanently, since that is the part hardest to reverse.
- Check this against 999.11 (PDF pipeline path) and 999.13 (advocate seeding): both add data volume, and both assume a pipeline that writes to a database the public site then reads. Static output does not change that, but the build step becomes a new dependency in their flow.

**Requirements:** TBD
**Plans:** 0 plans

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Provenance:** Raised by the operator on 2026-09-25 during Phase 52 Wave 3 ("one of my lingering suspicions is that the front end of this site could operate as a static site... is that a crazy idea?"). Assessed by Claude against the live codebase the same day: adapter and prerender state read from `app/svelte.config.js`, route split counted from `app/src/routes/`, corpus scale measured from `data/corpus/conversations.json` and `utterances.jsonl`, and Phase 55's open search decision read from this roadmap. Backlogged at the operator's request rather than scoped into v1.9.
