# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- ✅ **v1.1 Operator Admin Interface** — Phases 5–8 (shipped 2026-06-18)
- ✅ **v1.2 Pre-Launch Polish** — Phases 9–14 (shipped 2026-06-25)
- ✅ **v1.3 Speaker Accuracy + Pipeline Confidence** — Phases 15–17 (shipped 2026-06-29)
- ✅ **v1.4 Admin Completeness** — Phases 18–21 (shipped 2026-07-02)
- ✅ **v1.5 Admin Screens Cleanup** — Phases 22–30, 30.1 (shipped 2026-07-12)
- 🚧 **v1.6 Backlog Cleanup** — Phases 31–40 (in progress)

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

### 🚧 v1.6 Backlog Cleanup (Phases 31–40) — IN PROGRESS

**Overview:** Close out the 10 phases promoted from the 999.x backlog on 2026-07-12 before starting anything new — an escalated data-integrity risk (stale test fixtures + real data leakage), four small pipeline/people-admin bug fixes, one operator UX pattern, two open design questions to resolve during discuss-phase, a public-UI enrichment, and a README gap. Deployment (DEPLOY-01/03) and the remaining 999.x backlog (999.2–999.8) are explicitly out of scope.

- [x] **Phase 31: Audit ~28 stale DB-gated test fixtures + fix real data leakage into shared dev DB** - Escalated data-integrity risk; fix test isolation so service-function commits can't leak synthetic Person/Argument rows (completed 2026-07-13)
- [x] **Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths** - Merge/delete on a Justice with tenure rows no longer 500s (completed 2026-07-13)
- [x] **Phase 33: `update_argument_metadata` unique-constraint guard** - Colliding (source_docket, question_number) returns 409/422 instead of 500 (completed 2026-07-14)
- [x] **Phase 34: Blank case_name/docket_number validation** - Prevents slug/dedup corruption from cleared fields (completed 2026-07-14)
- [x] **Phase 35: `rerun_job` never spawns ingest for locally-uploaded jobs** - Local-upload reruns actually progress instead of sitting at PENDING forever (completed 2026-07-14)
- [x] **Phase 36: Click-to-copy extracted values design pattern** - Consistent click-to-copy affordance across pipeline run pages and argument editor (completed 2026-07-15)
- [x] **Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text** - Open design question (numbered-seat data vs. binary toggle) resolved during discuss-phase (completed 2026-07-21)
- [x] **Phase 38: Rethink Full Name vs. name-part fields in the people editor** - Open design question (auto-derive vs. independently editable) resolved during discuss-phase; includes G-38-6 security gap closure (completed 2026-07-27)
- [ ] **Phase 39: Bench popover — additional context data for Justices** - Birthdate, death date, and per-tenure appointment context, presented apolitically
- [x] **Phase 40: README — how to start the local stack** - Documents SvelteKit + FastAPI + Postgres local setup end to end (completed 2026-07-14)

## Phase Details

### Phase 31: Audit ~28 stale DB-gated test fixtures + fix real data leakage into shared dev DB

**Goal**: Fixing the FastAPI lifespan/session-factory bug (999.17, resolved 2026-07-10) means DB-gated tests across `pipeline/tests/` and `api/tests/` now genuinely execute against the live local dev Postgres instead of silently erroring at session setup, surfacing two problems: (1) ~28 tests fail on real schema/data-assumption mismatches never actually exercised before now (e.g. `test_rerun_creates_new_rows` inserts an `Utterance` without the NOT NULL `strategy` field) — spread across `test_ingest.py`, `test_parse.py`, `test_resolve.py`, `test_seed_aliases.py`, `test_pipeline_run.py`, `test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`, `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, `test_arguments.py`; (2) confirmed real data leakage — the `db_session` fixture's rollback pattern only protects against a test's own direct writes, not against production service functions (`create_person_for_job`, `publish_argument`, `run_import_convokit`) that commit internally, so full-suite runs have left leaked `Person` rows (duplicate "Ketanji Brown Jackson" plus synthetic test names) and synthetic `Argument` rows in the shared dev DB — one leaked duplicate actively broke `import-justices` with `MultipleResultsFound` mid-execution of a prior operator runbook. Needs a real fix (dedicated test database, snapshot/restore fixture, or savepoint-based nesting that survives inner commits) — the manual DELETE cleanup performed so far is only a stopgap.
**Depends on**: Nothing (first phase of v1.6 — escalated data-integrity risk, run first)
**Requirements**: TEST-01, TEST-02
**Success Criteria** (what must be TRUE):

  1. Full pytest suite (`pipeline/tests/` and `api/tests/`) runs without leaving any new synthetic Person or Argument rows in the shared dev DB — verified via a before/after row-count check.
  2. All ~28 previously-failing DB-gated test fixtures pass against the current schema (no NOT NULL/enum mismatches).
  3. The chosen isolation mechanism (dedicated test DB, snapshot/restore, or savepoint nesting) demonstrably survives an inner commit made by a production service function (e.g. `create_person_for_job` or `run_import_convokit`) during a test.
  4. Running `import-justices` or `import-convokit` immediately after a full test-suite run does not fail with `MultipleResultsFound` or any other error caused by leaked test data.

**Plans**: 8/8 plans complete
**Wave 1**

- [x] 31-01-PLAN.md — Provision scotus_test + session auto-reset fixture (D-01/D-02/D-03)
- [x] 31-02-PLAN.md — Root conftest DATABASE_URL redirect + leak-detection hook (D-01/D-11/D-12/D-13)
- [x] 31-03-PLAN.md — Consolidate the 7 duplicated db_session fixtures (D-09/D-10)
- [x] 31-04-PLAN.md — Build leaked-row cleanup script, dry-run default (D-04–D-08)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 31-05-PLAN.md — Fix stale api/tests DB-gated fixtures (TEST-02)
- [x] 31-06-PLAN.md — Fix stale pipeline/tests DB-gated fixtures (TEST-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 31-07-PLAN.md — Inner-commit regression test + full-suite green run (criteria 1/2/3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 31-08-PLAN.md — Operator-gated cleanup execution + import-justices smoke (criterion 4)

### Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths

**Goal**: `CourtTenure.person_id` is `nullable=False` with a plain `ForeignKeyConstraint` and no `ON DELETE CASCADE` in any Alembic migration, but none of `get_merge_preview`, `merge_people`, or `delete_person_if_orphan` (`api/services/admin_people.py`) account for `CourtTenure` rows. Merging or deleting any Bench person with one or more tenure rows raises an unhandled `IntegrityError` (500) instead of the documented graceful response. This predates Phase 27 (`CourtTenure` and the merge/delete paths were introduced in Phase 22) but became newly reachable once Phase 27 added full tenure-row CRUD to the People editor. Fix: count `CourtTenure` in `get_merge_preview`'s counted-tables loop, transfer `CourtTenure` rows to the target person in `merge_people`, and include `CourtTenure` in `delete_person_if_orphan`'s orphan check — mirroring the existing `Utterance`/`SpeakerAlias`/`CaseAppearance`/`ArgumentParticipant` handling.
**Depends on**: Nothing (independent bug fix)
**Requirements**: PADM-05
**Success Criteria** (what must be TRUE):

  1. Merge preview for a Justice with one or more CourtTenure rows shows an accurate count of tenure rows that will be transferred, not silently omitted.
  2. Merging two Justice person records transfers all CourtTenure rows to the target person without raising an IntegrityError.
  3. Attempting to delete a Justice with CourtTenure rows returns the documented graceful non-orphan response instead of an unhandled 500.
  4. Deleting a genuinely orphaned Justice (no CourtTenure rows) still succeeds exactly as before.

**Plans**: 2/2 plans complete

Plans:

- [x] 32-01-PLAN.md — Backend: add CourtTenure to MergePreview schema + all 3 service FK loops (preview/merge/delete) + mirrored tests (D-01–D-04)
- [x] 32-02-PLAN.md — Frontend: sync merge-preview contract — tenures in server-load can_delete/block-count + component breakdown/all-zero check (D-05)

### Phase 33: `update_argument_metadata` unique-constraint guard

**Goal**: `update_argument_metadata` writes `source_docket`/`question_number` without first checking whether another Argument row already holds that combination. Introduced in Phase 19, untouched by Phase 26. Saving a metadata edit that collides with an existing row raises an unhandled `IntegrityError` (500) instead of a clean, user-facing validation error. Fix: add a pre-write existence check (or catch `IntegrityError` and map it to a 409/422 with a clear message) before committing the update.
**Depends on**: Nothing (independent bug fix)
**Requirements**: PIPE-27
**Success Criteria** (what must be TRUE):

  1. Saving argument metadata with a `(source_docket, question_number)` combination that collides with an existing argument returns a 409/422 with a clear message instead of an unhandled 500.
  2. Saving argument metadata with a unique combination continues to succeed exactly as before.
  3. The fix is applied consistently to every code path that writes `source_docket`/`question_number`, not just the primary save action.

**Plans**: 4/4 plans complete

Plans:

- [x] 33-04-PLAN.md

- [x] 33-01-PLAN.md — Backend final-pair pre-check and race-safe HTTP conflict recovery
- [x] 33-02-PLAN.md
- [x] 33-03-PLAN.md

### Phase 34: Blank case_name/docket_number validation

**Goal**: `ArgumentUpdate.case_name`/`.docket_number` are `Optional[str] = None` with no non-empty validation; `update_argument` treats "not None" as "provided," not "non-empty." The edit form's `?/save` action always sends a trimmed string (never undefined) and the `<input>` elements have no `required` attribute. If an operator clears either field and saves: for a DRAFT argument, `_derive_slug("")` corrupts the case's public URL slug; for any status, `docket_number`/`docket_number_norm` can be wiped to `""`, breaking dedup semantics. The same gap exists in the sibling `update_argument_metadata` (`case_name`, `source_docket`). Fix: add a Pydantic `field_validator` rejecting blank/whitespace-only values on `ArgumentUpdate` and `MetadataUpdate`, plus `required` on both `<input>` elements as defense-in-depth.
**Depends on**: Nothing (independent bug fix)
**Requirements**: PIPE-28
**Success Criteria** (what must be TRUE):

  1. Clearing `case_name` or `docket_number` to blank/whitespace-only in the argument editor is rejected with a validation error, not silently saved.
  2. Clearing `case_name` or `source_docket` to blank/whitespace-only via `update_argument_metadata` (pipeline job metadata card) is likewise rejected.
  3. Argument slug and `docket_number`/`docket_number_norm` can never be corrupted to an empty string through either save path.
  4. Both affected `<input>` elements carry a `required` attribute as UI-level defense-in-depth.

**Plans**: 4/4 plans complete

**Wave 1**

- [x] 34-01-PLAN.md — Authoritative Pydantic normalization, deterministic docket precedence, safe service writes, and backend regression tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 34-02-PLAN.md — Structured 422 location parsing and attempted-value preservation across both SvelteKit action owners

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 34-03-PLAN.md — Exact native/pill validation feedback, required defenses, ARIA wiring, and first-invalid focus

**UI hint**: yes

### Phase 35: Remove pipeline job rerun capability

**Goal**: Remove pipeline-job reruns because recreating a job with the same source and inputs no longer provides meaningful operator value. Remove the rerun action from the admin UI, delete the rerun API endpoint and service function, and remove rerun-specific tests and references. Preserve ordinary job creation, failed-step recovery, source-PDF access, and existing job data.
**Depends on**: Nothing (independent cleanup)
**Requirements**: PIPE-29
**Success Criteria** (what must be TRUE):

  1. The admin UI no longer offers an action to rerun a pipeline job.
  2. The rerun API endpoint and service function are removed.
  3. Rerun-specific tests and stale code references are removed or rewritten.
  4. Creating jobs, recovering failed steps, viewing source PDFs, and viewing existing jobs continue to work unchanged.

**Plans**: 3/3 plans complete

Plans:
**Wave 1**

- [x] 35-01-PLAN.md — Remove backend rerun route/service ownership and align surviving recovery wording
- [x] 35-02-PLAN.md — Remove the hidden frontend rerun action and guard historical detail composition

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 35-03-PLAN.md — Add focused removal regressions and run the complete backend/frontend verification matrix

### Phase 36: Click-to-copy extracted values design pattern

**Goal**: Whenever a value has been extracted from a source PDF, use a consistent design pattern that lets the operator click the value to copy it to their clipboard. If a value was not extracted (showing N/A), clicking to copy is disabled. Includes an appropriate icon and tooltip. The pattern must be identical everywhere it appears — pipeline run pages and argument editor pages alike — including extracted docket number(s). Expected to decompose into at least: (1) a reusable tooltip component, and (2) the click-to-copy implementation for extracted hint values.
**Depends on**: Nothing (independent UX pattern)
**Requirements**: UX-01
**Success Criteria** (what must be TRUE):

  1. Every extracted-value display on pipeline run pages offers a click-to-copy affordance with icon and tooltip.
  2. Every extracted-value display on argument editor pages (including extracted docket number pills) offers the identical click-to-copy affordance.
  3. Click-to-copy is visibly disabled when the underlying value is N/A (not extracted).
  4. The pattern is implemented as one reusable component, not duplicated per page.

**Plans**: 3/3 plans complete

**Wave 1**

- [x] 36-01-PLAN.md — Reusable CopyableExtractedValue primitive and ArgumentDetailsCard adoption

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 36-02-PLAN.md — Remaining extracted-value surfaces, durable D-13 guidance, and blocking browser UAT

**UI hint**: yes

### Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text

**Goal**: During Phase 27 UAT, Jason asked for the tenure-row Seat field (currently free text) to become the same segmented-toggle component used for the Bench/Advocate choice, since for a Justice it's really just Chief or Associate. This was deferred rather than fixed immediately because real historical `court_tenures.seat` data includes specific numbered seats (e.g. "Associate Justice Seat 3"), not just a binary Chief/Associate split — collapsing to a 2-option toggle is a genuine data-model simplification that needs a decision on whether the numbered-seat detail is dropped, kept as a secondary field, or reconciled some other way, plus a migration/backfill pass over existing rows. **Open design question — resolve during `/gsd-discuss-phase 37`, not during roadmapping:** does numbered-seat detail get dropped, retained as a secondary field, or reconciled some other way?
**Depends on**: Nothing (independent design decision + implementation; open question resolved at discuss-phase)
**Requirements**: PEOPLE-08
**Success Criteria** (what must be TRUE):

  1. Tenure Seat is captured via a decision-backed UI control instead of unconstrained free text — the exact control shape (binary toggle vs. a richer control preserving numbered-seat detail) is resolved during `/gsd-discuss-phase 37`.
  2. Existing `court_tenures.seat` data (including numbered-seat rows) is preserved or migrated according to the resolved design decision — no silent data loss.
  3. Operator can set or change a person's tenure Seat through the new control, and the value round-trips correctly through save and reload.

**Plans**: 5/5 plans executed

**Wave 1**

- [x] 37-01-PLAN.md — Wave 0 regression harnesses for migration safety and accessible Office editing

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 37-02-PLAN.md — Staged rename, immutable dry-run report, atomic normalization, and final database constraint

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 37-03-PLAN.md — Strict canonical Office contracts across ORM, API, services, and CSV import

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 37-04-PLAN.md — Office read projections, formal Justice titles, and public rendering regression coverage

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 37-05-PLAN.md — Accessible Office editor, migration/application gate, and final Nyquist verification

**UI hint**: yes

### Phase 38: Rethink Full Name vs. name-part fields in the people editor

**Goal**: Jason expected that filling in only the component name fields (first/last/middle/suffix) without Full Name would auto-backfill Full Name on save — instead, Full Name is currently required standalone. Proposed direction (not yet locked): stop making Full Name operator-editable at all, and derive it entirely from the component fields. **Open design question — resolve during `/gsd-discuss-phase 38`, not during roadmapping:** exactly how derivation should work (ordering, suffix placement, punctuation) and what changes on the pipeline/parsing side are needed before this can be scoped. Distinct from the real bug this surfaced alongside (create route silently discarding name-part fields when Full Name is also filled — already fixed in Phase 27 gap-closure); this item is the broader "should Full Name exist as a separate editable field at all" question, still open.
**Depends on**: Nothing (independent design decision + implementation; open question resolved at discuss-phase)
**Requirements**: PEOPLE-09
**Success Criteria** (what must be TRUE):

  1. Full Name field behavior is resolved per a locked design decision (auto-derived vs. independently editable) — decided during `/gsd-discuss-phase 38`, not here.
  2. Operator can save a person record after filling in only the component name fields, consistent with whichever direction the locked decision takes (auto-derive removes the standalone Full Name requirement; independently-editable keeps it but the editor clearly explains why).
  3. Existing Full Name values for already-created people are not corrupted or silently overwritten by the new behavior.
  4. Any pipeline/parsing-side changes needed to support the decision are identified and applied consistently with the admin editor's behavior.

**Plans**: 10/10 plans executed

- [x] 38-01-PLAN.md
- [x] 38-02-PLAN.md
- [x] 38-03-PLAN.md
- [x] 38-04-PLAN.md
- [x] 38-05-PLAN.md
- [x] 38-06-PLAN.md
- [x] 38-07-PLAN.md — canonical docket-value rule + 422 guard at the create_job boundary (G-38-6)
- [x] 38-08-PLAN.md — independent pipeline-side ingest path/slug hardening + write containment (G-38-6)
- [x] 38-09-PLAN.md — parity-locked client mirror, inline docket error, SvelteKit re-check (G-38-6)
- [x] 38-10-PLAN.md — consolidated regression gate + operator re-verification of UAT Test 6 (G-38-6)

**UI hint**: yes

### Phase 39: Bench popover — additional context data for Justices

**Goal**: When a visitor clicks a Justice's avatar on the public argument view, the popover should show richer persistent context about them: birthdate, death date, and a list of tenures with start/end dates, appointing president, that president's party affiliation, and why they left that tenure (death, retirement, promotion) — presented identically for every Justice per the apolitical-framing constraint. `SpeakerPopover.svelte` currently shows photo, name, role, tenure dates, and appointing president, but no birthdate/death date despite `Person.birthdate` existing since Phase 27. Case-specific presentation (age at argument, tenure length, case-heard count) needs explicit exploration before implementation per the apolitical constraint and is not required for this phase's scope.
**Depends on**: Nothing (independent public UI feature)
**Requirements**: PUB-04
**Success Criteria** (what must be TRUE):

  1. Justice bench popover on the public argument page displays birthdate and death date (when known), in addition to the existing name/photo/role.
  2. Popover displays each tenure with start/end dates, appointing president, that president's party affiliation, and reason for leaving (death, retirement, promotion) when known.
  3. All added fields are presented identically for every Justice — no differential framing, omission, or emphasis based on any political consideration.
  4. Case-specific presentation (age at argument, tenure-length indicators, case-heard counts) remains out of scope for this phase.

**Plans**: 5/6 plans executed
**UI hint**: yes

**Wave 1**

- [x] 39-01-PLAN.md — Tracer: reason-left end to end (migration → model → schema → service → popover line) + people.death_date (D-01/D-02/D-03/D-04/D-15)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 39-02-PLAN.md — Justices CSV importer reads Birthdate / Death Date / Reason Left with null-only backfill (D-04–D-07)
- [x] 39-03-PLAN.md — Activate the person editor's Death Date input and per-tenure Reason Left dropdown (D-08/D-09/D-10)
- [x] 39-04-PLAN.md — Public API: T-14-02 party-exposure reversal + promote appointing_president to per-tenure + birthdate/death_date/bio_text (D-11/D-12/D-13/D-14)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 39-05-PLAN.md — Rebuild the popover card: role pill, birth/death line, bio clamp + expand, 3-line tenure blocks, advocate descriptor slot (D-14/D-15/D-16, D-17 deferred)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 39-06-PLAN.md — Operator runbook: apply migrations + run import-justices on the real dev DB, then live UAT of both card types

### Phase 40: README — how to start the local stack

**Goal**: No README documents how to start the full local stack (SvelteKit dev server, FastAPI backend, Postgres). Add one so setup steps don't have to be rediscovered each session.
**Depends on**: Nothing (documentation only, no code dependency)
**Requirements**: DOCS-01
**Success Criteria** (what must be TRUE):

  1. A README documents step-by-step how to start Postgres, the FastAPI backend, and the SvelteKit frontend locally, end to end.
  2. README covers required environment variables/config for local dev, referencing existing `.env` patterns without exposing secrets.
  3. A contributor (or the operator after time away) can follow the README from a clean checkout to a running local stack without needing to rediscover steps from memory or git history.

**Plans**: 2/3 plans executed

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
| 39. Bench popover — additional context data for Justices | v1.6 | 5/6 | In Progress|  |
| 40. README — how to start the local stack | v1.6 | 3/3 | Complete    | 2026-07-14 |

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

- [x] 36-03-PLAN.md

- [x] 34-04-PLAN.md

- [x] 40-01-PLAN.md
- [x] 40-02-PLAN.md
- [x] 40-03-PLAN.md

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
