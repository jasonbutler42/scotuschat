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
- 🚧 **v1.8 Import & Provenance Re-model** — Phases 47–51 (in progress, started 2026-08-17)

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

### 🚧 v1.8 Import & Provenance Re-model (Phases 47–51) — IN PROGRESS

**Overview:** A targeted re-model of the import/provenance layer — not a rewrite. Provenance becomes first-class: every import unit declares its `source` and `method`, so trust is a stated attribute of the row rather than archaeology across `strategy` strings and nullable `oyez_*` columns. On that foundation, every argument is born a *candidate* carrying a materialized trust tier and is promoted to *published* through a single review-gated promotion (the gate sits at promotion, not row-creation; status-based staging, no separate staging table), an operator review queue surfaces everything needing attention, and the two import paths (corpus and PDF) collapse into peer strategies of one unified, idempotent, authority-governed import model. The public noun finally aligns to "arguments" and a shared design system lands last, once the corrected domain language is settled. The read model, people, tenures, and utterance display are stable and out of scope. Hard constraints throughout: Alembic is the sole DDL authority, the pipeline stays offline-only, trust is operator-facing and never shown publicly (apolitical framing), and backfill must preserve existing corpus + PDF data. Sequencing is dependency-ordered and load-bearing — provenance (47) is the keystone everything else builds on, then trust/lifecycle (48), then the review model (49), then the unified import path (50), with the design system + noun alignment (51) deliberately last.

- [x] **Phase 47: Provenance Foundation** - `import_run` generalizes `pipeline_run` with declared `source`/`method` + external-id lineage; PDF-only fields go nullable; every import path stamps provenance at write time (disposable DB → clean rebuild, no legacy backfill) (completed 2026-08-18)
- [x] **Phase 48: Trust & Lifecycle** - Materialized `trust_tier` rollup, `candidate`-on-arrival status, and a single `published_at` promotion gate hard-blocked on UNCERTAIN with a logged operator override (completed 2026-08-21)
- [x] **Phase 49: Review Model** - Four-state `review_state` on operator-editable rows, discrepancy recording on re-import, and a filterable operator review queue (generalizes `name_needs_review`) (completed 2026-08-25)
- [ ] **Phase 50: Unified Import Path** - Corpus import writes `import_run` directly as a first-class strategy (no fabricated PDF-pipeline artifacts); `admin_job` re-points; re-import is idempotent and authority-governed so it never clobbers operator work (PDF half split to 999.11 on 2026-08-25 per the corpus-first decision)
- [ ] **Phase 51: Design System & Noun Alignment** - Public noun aligned to "arguments" (`/cases` → arguments, redirects preserved) plus shared component library, design tokens, and listing style (absorbs backlog 999.4 / 999.6 / 999.8)

## Phase Details

### Phase 47: Provenance Foundation

**Goal**: Provenance becomes a first-class, declared attribute of every import unit — the keystone the whole re-model rests on. A new `import_run` table generalizes today's `pipeline_run` as the single lineage backbone, carrying a declared `source` (operator / corpus / pdf_pipeline / seed) and `method` (manual / direct / normalized / rule_based / llm_corrective) plus external-source lineage (`external_id` for oyez ids). Utterances reference `import_run` instead of `pipeline_run`. PDF-only fields (`pdf_path` / `pdf_url`) become nullable and are populated only for `pdf_pipeline` runs, so the corpus path stops fabricating them. Every import path stamps `source`/`method` at write time, so "did this come clean from the corpus or was it LLM-guessed from a smudgy PDF?" is answerable by reading the row, not by archaeology. The project DB is disposable (fixture-reseedable), so this is delivered as a clean rebuild — drop `pipeline_runs`, create `import_run` fresh, and re-seed through the updated import code — rather than an in-migration backfill of legacy rows _(reframed 2026-08-17; see `phases/47-provenance-foundation/47-CONTEXT.md` D-01/D-03)_. Alembic is the sole DDL authority.
**Depends on**: Nothing (first phase of v1.8; builds on the shipped v1.7 schema)
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06
**Success Criteria** (what must be TRUE):

  1. Every `import_run` row records a declared `source` and a declared `method` from the closed vocabularies, readable directly with no join-and-infer step.
  2. `import_run` is the lineage backbone that generalizes `pipeline_run`, and every utterance references its `import_run`.
  3. External-source lineage (oyez transcript/case ids) is captured on `import_run.external_id` for corpus-sourced runs.
  4. Every import path stamps provenance at write time, verified by re-seeding a fixture and reading it directly off the rows — a corpus row reads `source=corpus / method=direct`, a rule-parsed PDF row reads `pdf_pipeline / rule_based`, an LLM-corrected row reads `pdf_pipeline / llm_corrective`. The verification fixture must exercise all three combinations. _(Operator override 2026-08-18: satisfied as a composition — `corpus/direct` proven by a live `reset_to_fixture` re-seed read directly off `import_run` rows; the two `pdf_pipeline` legs proven by real-writer tests driving `run_parse` with `parse_with_llm` monkeypatched. The live-reseed vehicle for the PDF legs is deferred with the PDF route itself — no PDF fixture exists and building one was declined as work on the deprioritized path. See PROJECT.md Key Decisions and `todos/pending/2026-08-18-pdf-provenance-live-fixture-verification.md`.)_
  5. `pdf_path` / `pdf_url` are nullable and populated only for `pdf_pipeline` runs; corpus runs carry no fabricated PDF artifacts.

**Plans**: 6/6 plans executed (4 waves)

Plans:
**Wave 1**

- [x] 47-01-PLAN.md — Schema spine + corpus tracer: `ImportRun` model, migration 0026, the three hardcoded table-name sites, corpus writer stamping `corpus`/`direct`/`external_id` (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 47-02-PLAN.md — PDF pipeline writers stamp `pdf_pipeline` with `normalized` / `rule_based` / `llm_corrective`; the two PDF legs of the D-06 guardrail (wave 2)
- [x] 47-03-PLAN.md — API read layer + public schema; retires the `strategy == "convokit_import"` hack for `ImportRun.source == ImportSource.CORPUS` (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 47-04-PLAN.md — `pipeline/tests` conversion; `test_pipeline_run.py` renamed to `test_import_run.py` (wave 3)
- [x] 47-05-PLAN.md — `api/tests` and root `tests/` conversion, including the two schema-contract files (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 47-06-PLAN.md — Live re-seed, D-06 three-combination evidence, full-suite gate, operator verification (wave 4)

### Phase 48: Trust & Lifecycle

**Goal**: Every argument is born a *candidate* carrying a trust verdict and is promoted to *published* through one review-gated promotion. A materialized `trust_tier` (verified / trusted / provisional / uncertain) is derived from `(authority, method, review_state)` via one documented function and stored on the argument as the floor rollup of its utterances and participants, recomputed on every mutation path (import, edit, review). A newly imported argument is `status=candidate` (not public) with its tier set on arrival — the pre-published, tiered row is the holding pen; there is no separate staging table. Promotion is the single `published_at` gate, hard-blocked while any UNCERTAIN element remains, with the operator retaining final authority via a deliberate, logged per-argument override. Trust is operator-facing only — never shown on the public site — preserving the apolitical constraint.
**Depends on**: Phase 47 (trust tier derives from declared provenance)
**Requirements**: TRUST-01, TRUST-02, TRUST-03, TRUST-04, TRUST-05
**Success Criteria** (what must be TRUE):

  1. Every argument carries a `trust_tier` (verified / trusted / provisional / uncertain) derived from provenance + review state by one documented function.
  2. An argument's `trust_tier` is the floor (minimum) of its utterances and participants, materialized and recomputed whenever a constituent changes.
  3. A newly imported argument is born a `candidate` (not public) with its tier set on arrival.
  4. Attempting to publish an argument while any UNCERTAIN element remains is hard-blocked at the single `published_at` promotion gate.
  5. The operator can override the publish block with a deliberate, per-argument acknowledgment that is logged.

**Carried defect folded in 2026-08-18** (cross-phase UAT audit): `api/services/admin_arguments.py::delete_argument`
omits `argument_status_log` from its FK-ordered cascade. Its steps are Utterance → ImportRun →
ArgumentParticipant → CaseArgument → NULL `AdminJob.argument_id` → Argument, with no
`ArgumentStatusLog` delete. `argument_status_log.argument_id` is a NOT NULL FK to `arguments.id`
with no `ondelete` clause (`api/models/models.py:507`, migration
`0012_unpublished_enum_and_status_log.py:75`), so PostgreSQL applies RESTRICT — and `approve_job`
writes an `ArgumentStatusLog(DRAFT)` row for every argument it creates
(`api/services/admin_jobs.py:591`). Every approve-created DRAFT therefore carries a status-log row,
and the Danger Zone delete on `/admin/arguments/[id]` should raise `ForeignKeyViolation` rather than
succeed. Originally found in Phase 31 (Plan 31-04) and left open ever since; re-confirmed by reading
current source on 2026-08-18, still with no live repro (the audit had no DB access), so treat it as
static analysis until reproduced.

  - Fix is one step: `delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)`
    anywhere before the final `Argument` delete — nothing else FKs to `argument_status_log`.

  - Add the regression test Phase 31 recommended: delete succeeds for a DRAFT argument that has at
    least one status-log row.

  - Correct the comment at `scripts/delete_fixture_argument.py:25`, which asserts "a DRAFT argument
    can never have one" — that claim is wrong and is what let the gap survive three milestones.

  - Belongs here because Phase 48 owns argument lifecycle and the `published_at` promotion gate, and
    because Phases 47/50's re-import and idempotency paths depend on this cascade being correct
    (STATE.md carries the same warning).

**Plans**: 10/10 plans executed

Plans:

**Wave 1**

- [x] 48-01-PLAN.md — Trust derivation foundation + end-to-end tracer: `api/domain/trust.py`, migration 0027 (`candidate` enum value, `arguments.trust_tier`, `argument_status_log` override columns), `recompute_argument_tier`, and the two Wave 0 test modules (wave 1)

**Wave 2** *(all five parallel; blocked on 48-01's migration)*

- [x] 48-02-PLAN.md — Carried defect: `delete_argument` → `argument_status_log` cascade, failing-then-passing regression test, corrected fixture-script comment (wave 2)
- [x] 48-03-PLAN.md — D-23 public trust-leak ban: structural contract over every public response model + live per-endpoint assertions (wave 2)
- [x] 48-04-PLAN.md — Candidate status vocabulary across all six admin guard sites (plus the frontend `readonlyMode` literal) + recompute wiring into all four `admin_jobs` writers (wave 2)
- [x] 48-05-PLAN.md — Born-candidate pipeline writers: corpus + PDF birth logging, tier on arrival, recompute in parse and resolve (wave 2)
- [x] 48-06-PLAN.md — Offline `pipeline recompute-trust` CLI: drift repair and the D-09/D-21 zero-rows-changed verification vehicle (wave 2)

**Wave 3** *(blocked on 48-02 releasing `admin_arguments.py`)*

- [x] 48-07-PLAN.md — Two-gate publish: the overridable UNCERTAIN block, the required-reason override logged to `argument_status_log`, and `trust_tier` on the admin detail contract (wave 3)

**Wave 4** *(blocked on 48-07's error shape)*

- [x] 48-08-PLAN.md — Minimal admin UI on `/admin/arguments/[id]`: block-reason panel with per-blocker counts, override prompt, and the UI source contract (wave 4)

**Wave 5**

- [x] 48-10-PLAN.md — Gap closure: list-page publish-block/override UI parity, per-row trust-tier indicator, and the unpublish public-visibility fix across three read paths (wave 5)

**Wave 6** *(blocked on 48-10)*

- [x] 48-09-PLAN.md — Live fixture reseed, zero-drift proof, full-suite gate, requirement traceability, and operator sign-off (wave 6)

### Phase 49: Review Model

**Goal**: The operator gets a real review workflow over the candidate pool. Operator-editable rows (person name-parts, argument participants) carry a four-state `review_state` (unreviewed / needs_review / operator_confirmed / operator_edited), generalizing today's `name_needs_review` / `name_extraction_metadata` into the unified review_state + provenance record so no parallel mechanism survives. Re-import records a discrepancy for operator attention instead of overwriting an equal-or-higher-authority value (generalizing today's `admin_jobs.discrepancies`). A new operator review queue lists everything needing attention, filterable by trust tier and review state; resolving an item (confirm or edit) advances its `review_state` and triggers trust recomputation. "Operator work is sacred" is the invariant throughout — a re-import never overwrites a human-confirmed or human-edited value.
**Depends on**: Phase 48 (the review queue filters by trust tier; resolving items recomputes trust)
**Requirements**: REVIEW-01, REVIEW-02, REVIEW-03, REVIEW-04, REVIEW-05
**Success Criteria** (what must be TRUE):

  1. Operator-editable rows (person names, argument participants) carry a four-state `review_state` (unreviewed / needs_review / operator_confirmed / operator_edited).
  2. A re-import that disagrees with an equal-or-higher-authority value records a discrepancy for operator review instead of silently overwriting it.
  3. The operator can open a review queue listing every item needing review, filterable by trust tier and review state.
  4. The operator can resolve a review item (confirm or edit) from the queue, and doing so advances its `review_state` and recomputes the affected argument's trust.
  5. The legacy `name_needs_review` / `name_extraction_metadata` mechanism is folded into the unified review_state + provenance record, with no parallel mechanism remaining.

**Plans**: 12/12 plans executed (6 gap-closure plans added 2026-08-24 after UAT reopened the phase; 49-09 split into 49-09 + 49-10 when operator decision D-35 replaced the G-49-3 checkpoint with a convergence mandate; 49-11 added when the operator scoped D-35 to the whole argument, not just participant data — D-35a; 49-12 added when the phase's first authenticated live-browser pass found a FOURTH horizontal-scroll cause, `AdminSubNav`, that three green source-text gates could not see — G-49-5c)
**UI hint**: yes

Plans:
**Wave 1**

- [x] 49-01-PLAN.md — Tracer: migration 0028 (`review_state` enum + participant provenance columns + `value_discrepancy`), real per-participant trust, and an end-to-end inline-confirm slice on `/admin/review` (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 49-02-PLAN.md — Legacy fold (REVIEW-05): migration 0029 swaps the two `people` columns, every consumer re-points, and a structural test proves no parallel mechanism survives (wave 2)
- [x] 49-03-PLAN.md — Folded-todo cleanup: create-person popover side inheritance and selection, Status-card label fix, and a new `/admin/help` status × tier × review-state page (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 49-04-PLAN.md — Authority ladder (`api/domain/authority.py`), the `value_discrepancy` record, the one gated writer all three existing writers delegate to, the four resolve actions, and the extended public-leak ban (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 49-05-PLAN.md — Full `/admin/review` screen: tabs, tier × review-state × status filters, expandable rows with discrepancy detail, subnav entry, and the dashboard StatCard (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 49-06-PLAN.md — Dev-only unresolved-speaker seeder, the D-32 live authority-conflict walkthrough, closure of 26-UAT Test 26 and 14-UAT Test 8, and requirement traceability (wave 5)

**Gap closure** *(added 2026-08-24; UAT `49-UAT.md` reopened the phase with 4 open gaps)*

- [x] 49-07-PLAN.md — Operator-facing copy: the destination-naming action-verb link label, the domain-noun rename in rendered copy only, and the zero-one-many agreement fix — closes `G-49-4a`, `G-49-4b`, `G-49-5b` (wave 1)
- [x] 49-08-PLAN.md — Narrow-viewport containment: overflow containers for both queue tables and the status segment group, and an auto-fit dashboard grid with an executable track-fit gate — closes `G-49-5a` (wave 2, blocked on 49-07 releasing `admin/review/+page.svelte`)
- [x] 49-09-PLAN.md — WR-01 popover open-time side resync, plus the published lock on `update_participant_side` (D-35 half one) made visible on the Speakers card and a full inventory of the write paths still unlocked (wave 4)
- [x] 49-10-PLAN.md — Convergence (D-35 half two): one shared side module, a single Speakers row template reaching every stored side value behind a boundary confirm, and `T-15-02-BENCH` retired as satisfied — closes `G-49-3` (wave 5, blocked on 49-09)
- [x] 49-11-PLAN.md — Whole-argument lock (D-35a): published guards on `update_argument`, `update_argument_metadata`, `resolve_job`, and `create_person_for_job`; live proof that unpublish and review-state writes still work; the always-editable page decision reversed in place and the Case + Argument Details cards locked (wave 6, blocked on 49-10)
- [x] 49-12-PLAN.md — Narrow-viewport chrome (`G-49-5c`): `flex-wrap` on `AdminSubNav` (the fourth and last horizontal-scroll cause, on every admin page) and on `TopNav`, proved by real-browser page-scroll measurement rather than a fourth grep, plus a computed page-chrome sweep that fails on an unfixed component nobody named (wave 7, independent)

### Phase 50: Unified Import Path

**Goal**: The corpus import path stops being "a guest in a house built for the PDF pipeline" — it becomes a first-class strategy of one import model rather than a caller that fabricates PDF-pipeline artifacts to fit. Corpus import writes `import_run` directly (`source=corpus`) with no synthetic run carrying a meaningless `pdf_path` / `prompt_version`; `admin_job` references an existing `import_run` rather than inventing one, and the corpus CLI batch needs no admin_job at all. Re-import is idempotent by construction — re-running yields the same result and never clobbers operator-authored values — governed by a single total authority ordering (operator > corpus > pdf/rule_based > pdf/llm_corrective) applied at every writer, with disagreements at equal-or-higher authority surfaced as discrepancies (via Phase 49's review model) rather than silent overwrites.
**Depends on**: Phase 49 (re-import discrepancy recording builds on the review model; requires the full provenance + trust + review schema in place)
**✅ Scope resolved (2026-08-25, at planning time)**: the original phase paired a corpus half with a PDF half. Per the 2026-08-18 corpus-first decision, the PDF half — old success criterion 2, "the PDF pipeline path reads and writes `import_run` as one strategy among peers" (IMPORT-02) — **split out to Phase 999.11 (BACKLOG)** and is no longer in this phase's scope. The authority ordering (IMPORT-05) stays here in full: it is one total ordering function, and defining all four rungs costs nothing extra without the PDF import path being reworked. Its `operator` and `corpus` rungs are exercised by live corpus flows; the `pdf/rule_based` and `pdf/llm_corrective` rungs are proven by real-writer tests — the same verification split Phase 47 established for PDF provenance. See PROJECT.md Key Decisions.
**Requirements**: IMPORT-01, IMPORT-03, IMPORT-04, IMPORT-05
**Success Criteria** (what must be TRUE):

  1. Corpus import writes an `import_run` directly with `source=corpus` and fabricates no PDF-pipeline artifacts (no synthetic run with meaningless `pdf_path` / `prompt_version`).
  2. `admin_job` references an existing `import_run`; the corpus CLI batch runs with no admin_job at all.
  3. Re-running any import is idempotent — the same input yields the same rows and never clobbers operator-authored values.
  4. The authority ordering (operator > corpus > pdf/rule > pdf/llm) governs the overwrite decision on every writer.

**Plans**: 7 plans (4 waves)

Plans:

- [ ] 50-01-PLAN.md — Migration 0030, the frozen content-digest contract, and the tracer: one corpus conversation imported twice, unchanged, with no AdminJob anywhere (wave 1)
- [ ] 50-02-PLAN.md — `apply_argument_value_change` / `apply_case_value_change` peer gates with the OQ-1 fail-closed NULL semantics, plus the argument- and case-level legs on the review attention predicate (wave 2)
- [ ] 50-03-PLAN.md — The argument-scoped approve route, operator provenance stamping on the five Argument/Case compare-set columns, and delete-in-every-state-except-published with the value_discrepancy cascade fix (wave 2)
- [ ] 50-04-PLAN.md — `/admin/review` surfaces: argument- and case-level discrepancy render, and the Approve action on a candidate row (wave 3)
- [ ] 50-05-PLAN.md — The reconcile compare-and-record pass: D-02 walk, D-07 restamp, D-08 published freeze, D-10 whole-set utterance replacement, `--dry-run` and the batch counters (wave 3)
- [ ] 50-06-PLAN.md — The D-22 delegation sweep across resolve.py, parse.py and import_justices_csv.py, plus the D-24 executable behavioral gate (wave 3)
- [ ] 50-07-PLAN.md — The offline `prune-runs` command, the extended public-leak ban, the dispositioned writer inventory, and D-23's closure (wave 4)

### Phase 51: Design System & Noun Alignment

**Goal**: With the corrected domain language settled, the public side finally reflects it. The public route/noun aligns to "arguments" (`/cases` → arguments) with redirects preserving every existing shareable URL. A shared component library is extracted for reused UI (absorbs backlog 999.4), design tokens (color / type / spacing) are established as the visual foundation (absorbs backlog 999.8), and the arguments listing style is decided and implemented (absorbs backlog 999.6). Deliberately sequenced last so the UI reflects the corrected domain model and unified import lifecycle rather than being reworked twice.
**Depends on**: Phase 50 (deliberately last — the UI reflects the fully corrected domain language and unified import model)
**Requirements**: DS-01, DS-02, DS-03, DS-04
**Success Criteria** (what must be TRUE):

  1. The public route/noun is aligned to "arguments" (`/cases` → arguments), and every previously shareable URL still resolves via redirects.
  2. Reused UI is extracted into a shared component library (absorbs backlog 999.4).
  3. Design tokens (color / type / spacing) are established as the visual foundation (absorbs backlog 999.8).
  4. The arguments listing style is decided and implemented (absorbs backlog 999.6).

**Plans**: TBD
**UI hint**: yes

Plans:

- [ ] TBD (planned via `/gsd-plan-phase 51`)

## Progress

**Execution Order:** Phases execute in numeric order: 47 → 48 → 49 → 50 → 51

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
| 47. Provenance Foundation | v1.8 | 6/6 | Complete    | 2026-08-18 |
| 48. Trust & Lifecycle | v1.8 | 10/10 | Complete    | 2026-08-21 |
| 49. Review Model | v1.8 | 12/12 | Complete    | 2026-08-25 |
| 50. Unified Import Path | v1.8 | 0/TBD | Not started | - |
| 51. Design System & Noun Alignment | v1.8 | 0/TBD | Not started | - |

## Backlog

Standard: all backlog items live here as 999.x entries (`.planning/phases/999.N-slug/`), captured via `/gsd-capture --backlog` and reviewed/promoted via `/gsd-review-backlog`. `.planning/BACKLOG.md` (the flat B-NNN file previously used, 2026-07-01 to 2026-07-09) has been retired and its 14 still-open items migrated below (2026-07-09); 5 items (B-001, B-003, B-004, B-005, B-006) were dropped as already shipped by Phase 24/27, and B-014 was merged into 999.1 as a duplicate capture of the same idea.

**v1.8 note:** backlog items 999.4 (shared component library), 999.6 (arguments listing style), and 999.8 (Figma design system) are absorbed into Phase 51 (DS-02 / DS-04 / DS-03 respectively). They remain listed below for provenance until Phase 51 ships, at which point they are closed as absorbed. Separately, 999.11 is the reverse direction — a *split out of* v1.8: Phase 50's PDF half (IMPORT-02) moved here on 2026-08-25 rather than shipping in the milestone, per the corpus-first decision.

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

### Phase 999.6: Decide on listing style for cases/arguments (BACKLOG)

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

### Phase 999.8: Figma design system (BACKLOG)

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
