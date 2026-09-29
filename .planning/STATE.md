---
gsd_state_version: "1.0"
milestone: v1.9
milestone_name: The Site Becomes Complete
current_phase: 53
current_phase_name: Undetermined Speakers & Marker Normalisation
status: executing
stopped_at: Completed 53-05-PLAN.md
last_updated: "2026-09-29T12:32:39.506Z"
last_activity: 2026-09-29
last_activity_desc: Phase 53 execution — 53-01, 53-02, 53-05 complete; 53-03, 53-04 still outstanding
state_head: d2a325465606e77b8b3fd5b243591dcfc7d2eba3
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 11
  completed_plans: 9
  percent: 13
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-28 after Phase 52)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

**Current focus:** Phase 53 — Undetermined Speakers & Marker Normalisation
the site can go live (correct data, the full corpus published, a finished public surface), so that
v2.0 is purely the deployment.

**Standing policies** (full text in CLAUDE.md, adopted 2026-08-27 by the operator): the **Defect Policy**
— defects whose correct behavior is already determined are fixed silently and reported in one line;
only questions needing the operator's taste are escalated — and the **Testing Policy** — no static
source-text contract tests for frontend behavior, tests retire with the behavior they pinned, no
phase-numbered test modules, ~2:1 test:code as a guideline. Both govern all later work.

## Current Position

Phase: 53 (Undetermined Speakers & Marker Normalisation) — EXECUTING
Plan: 3 of 5 complete (53-01, 53-02, 53-05) — 53-03 and 53-04 still outstanding
(wave order note: 53-05 depended only on 53-01 and ran ahead of 53-03/53-04 in
this phase's wave plan; the automatic advance-plan counter does not track wave
order — see project memory "advance-plan ignores wave order" — this position
was corrected by hand against the actual *-SUMMARY.md files on disk)
Status: Ready to execute
Last activity: 2026-09-29 — Phase 53 execution — 53-05 complete

Progress: [█░░░░░░░░░] 13% (1/8 phases)

## Milestone Roadmap — v1.9 (Phases 52–58)

| # | Phase | Requirements | Depends on |
|---|-------|--------------|------------|
| 52 | Justice Identity | JUSTICE-01–06 | — |
| 53 | Undetermined Speakers & Marker Normalisation | SPEAKER-01–08 | 52 |
| 54 | Publishing at Scale & Verification Debt | PUBLISH-01–05, VERIFY-01/02 | 53 |
| 54.1 | Justice Portraits & Biographical Enrichment (INSERTED) | PERSON-01–06 | 52, 54 |
| 55 | Search | SITE-03/04/05/06, PLUMBING-07 | 52, 54 |
| 56 | Landing Page, About & Oyez Source Links | SITE-01, SITE-02, SITE-07 | 55, 54.1 |
| 57 | Surface Plumbing | PLUMBING-01–06 | 56 |
| 58 | Analytics & Privacy | ANALYTICS-01–05 | 55, 57 |

**Ordering is load-bearing, not cosmetic.** Data correctness sequences before the public site — a
speaker-name search run before justice dedup would surface the exact duplicate-person bug Phase 52
exists to close. Publishing comes early because every surface after it is better verified at real
volume (~108 arguments in a term) than against four fixtures. Search is a backend concern that
precedes the landing page, which leans on it. Analytics is deliberately last and isolated: it brings
the first client-side third-party script and the first `PUBLIC_` env var this codebase has ever had.

## Performance Metrics

- v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12)
- v1.6: 11 phases, 51 plans, 17 days (2026-07-12 → 2026-07-29)
- v1.7: 6 phases, 29 plans, 18 days (2026-07-29 → 2026-08-15)
- v1.8: 5 phases, 45 plans, 120 tasks, 37 days (2026-08-17 → 2026-09-23), 368 commits
- v1.9: 8 phases, 46 requirements — started 2026-09-23 (Phase 54.1 inserted 2026-09-24)

**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 52 P01 | 46min | 3 tasks | 9 files |
| Phase 52 P02 | 58min | 3 tasks | 14 files |
| Phase 52 P03 | 24min | 2 tasks | 4 files |
| Phase 52 P04 | 43min | 3 tasks | 3 files |
| Phase 52 P05 | 57min | 2 tasks | 9 files |
| Phase 52 P06 | 10min | 2 tasks | 5 files |
| Phase 53 P01 | 54min | 2 tasks | 9 files |
| Phase 53 P02 | 62min | 2 tasks | 6 files |
| Phase 53 P05 | 20min | 2 tasks | 8 files |

## Accumulated Context

### Design and analysis already on disk — do NOT re-derive

Substantial work was done during v1.9 scoping and is committed. Phases must build against it, not
repeat it.

| Artifact | What it settles |
|---|---|
| `.planning/notes/justice-identity-and-seeding.md` | Join-key decision, the 49-of-114 name-mismatch measurement, why a derivation rule was rejected, proposed schema/code changes |
| `.planning/notes/justice-identity-mapping-DRAFT.csv` | 114 rows — 65 exact, 45 derived, 4 flagged for the operator. **Unverified**: an input to planning, not a deliverable |
| `.planning/notes/undetermined-speaker-display.md` | Treatment D approval, the full-corpus measurements (do not re-run the 900MB pass), the trust decision, the marker vocabulary split |
| `.planning/notes/transcript-rendering-decision-tree.md` | 10-scenario inventory, normalisation decision, the settled 50% denominator, the rules that must not regress |
| Figma `KICu66PtMLHk4fmxJYPggx`, page Public, node `33:2` | Approved Treatment D mockup |
| `.planning/positioning/` (7 docs + `README.md`) | Homepage brief, voice, principles, audience; README indexes the Figma homepage concepts and records what has gone stale in them |
| `.planning/notes/launch-readiness.md` | Verified public-surface gap inventory; the Admin-link decision |
| `.planning/research/SUMMARY.md` + 4 source docs | Stack (no new npm/pip packages), architecture integration map, 8 pitfalls, the analytics/consent legal position |

### Decisions that arrive already made

- **Justice join key** is a verified `oyez_speaker_id` mapping stored as data. Name-overrides and a
  corpus-first identity spine were both considered and not chosen. A derivation rule reproduces 100
  of 114 forms and was rejected — right 88% of the time is the worst outcome available.
- **Treatment D** is approved for undetermined speakers. Treatments A, B and C were explored; C was
  rejected deliberately because it asserts a side the source does not support.
- **A source-sentinel speaker maps to PROVISIONAL, not UNCERTAIN.** No human judgment is involved —
  `speakers.json` types the speaker `"U"`, so the source itself states machine-readably that it does
  not know. The fact must be **stored on the utterance at import**, never re-derived from
  `raw_speaker_label`.
- **>50% undetermined blocks publish.** 6 arguments corpus-wide. The denominator question is settled
  by measurement: all-turns and excluding-room-events yield the identical 6.
- **Whole-turn markers normalise; inline markers do not.** `detect_stage_direction` already returns
  the canonical label and the importer discards it one line later.
- **Voice Overlap stays a stage direction**; a whole-turn inaudible with a known speaker does not.
- **Consecutive undetermined turns (1.1%) are WON'T FIX** — shown honestly rather than hidden.
- **Remove the Admin link from the public nav.** Not a security fix; auth already gates the page.
- **Analytics only, no public "request a case" form** in v1.9 — deferred to Phase 999.12.

### Open decisions that belong to a phase, not to research

- **Search query strategy (Phase 55).** `STACK.md` recommends trigram + weighted `tsvector`/GIN;
  `ARCHITECTURE.md` holds trigram alone is adequate at ~7,800 rows and cautions against `tsvector`
  as premature optimisation. **Both agree trigram is needed.** Settle the `tsvector` half against a
  performance measurement before engineering starts.
- **`unaccent` on DigitalOcean Managed PostgreSQL is unverified** (Phase 55). Confirm with
  `SELECT * FROM pg_available_extensions` before any migration depends on it.
- **Analytics vendor (Phase 58)** is an operator choice. GoatCounter is the researched candidate;
  Plausible / Fathom / self-hosted Umami are documented alternatives. Once picked, inspect the actual
  script for device storage/access behaviour rather than trusting the "cookieless" label.
- **Oyez `external_id` URL format (Phase 56)** — spot-check that stored values resolve to real Oyez
  URLs. A verification task, not a build task.

### Standing pitfalls this milestone must not walk into

1. **Search or sitemap re-implements the publish gate and leaks unpublished rows** — the same class
   as the already-fixed BUG-01, and easy to reintroduce through a second code path. Reuse the
   service-layer gate; prove zero leakage against a deliberately-unpublished row.
2. **Bulk publish bypasses the trust gate under performance pressure.** A raw bulk `UPDATE` silently
   readmits the gate Phase 48 exists to enforce. Call `publish_argument` per row.
3. **Forgiving matching on docket numbers produces confidently wrong results.** Trigram is right for
   case and speaker names and wrong for dockets, where a one-character edit is a different docket.
4. **The leak-ban test does not auto-discover.** Every new public route, schema module and frontend
   path must be registered in `test_trust_public_leak_ban.py` in the same phase that adds it
   (PLUMBING-07, owned by Phase 55, obligation applies to 53/55/56/57/58).
5. **Laughter inside a speaker's turn must still split** into speech plus a room-event row. Easy to
   break by reaching for the simpler "stop splitting parentheticals" fix.

### Open concerns carried into this milestone

**Verification debt** (VERIFY-01/02 pull the addressable part of this into Phase 54)

- **Phase 04 accessibility is asserted, not measured.** No assistive-technology walkthrough and no
  axe-core/WAVE scan has ever run against the argument view. Waived by the operator 2026-08-18 via
  `04-VERIFICATION.md`'s `overrides` block. Phases 14, 38, 39, 45 and 51 have all changed that UI
  since, so the drift is worse than when the waiver was granted. **Explicitly out of v1.9 scope**
  (operator decision, 2026-09-23); recorded as a known risk in `launch-readiness.md`.
- **Three UAT behaviours implemented but never observed** — the failed-run error panel
  (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder with its per-row Save gate,
  and the non-interactive avatar for an unresolved utterance. → VERIFY-01, Phase 54.
- **Phase 49's live-browser checks** are consolidated in `49-EVIDENCE.md` §9 (now under
  `.planning/milestones/v1.8-phases/49-review-model/`) and still unrun. They were blocked on sandbox
  `.env` access; browser tooling works now. → VERIFY-02, Phase 54.

**Code debt**

- **32 `state_referenced_locally` svelte-check warnings across 9 admin files.** The same prop-capture
  class as Phase 51's CR-01. None on public surfaces; known open at the v1.8 close, not blocking.
- **Trivial-ACCEPT provenance restamp.** `decide_write` returns `ACCEPT` both for a genuine gap-fill
  and for a trivial agreement, and three callers restamp `source`/`method` for both — so a
  byte-identical re-import can demote an OPERATOR-stamped `Argument`/`Case` row to `corpus`. No data
  loss; what degrades is the provenance label. Fix is to gate each restamp on `_values_differ`.
  Relevant to Phase 52, which re-runs the justice seed. Full write-up in the archived
  `49/deferred-items.md`.

**Environment**

- **4 `test_phase38_people_ui_contract.py` tests SKIP rather than fail when `node` is off PATH** —
  the default for a pytest run launched outside an nvm shell. A regression there would be invisible.
- **`TEST_DATABASE_URL` and `DATABASE_URL` resolve to the same physical Postgres database in this
  sandbox.** Running a full-suite pytest run and a direct dev-DB script concurrently produced
  spurious deadlock failures. Do not run both at once.
- **`scotus_test` dies around 1600 columns** — mass missing-column test failures are a DB tombstone
  ceiling, not a code bug. Check before debugging.

**Deployment blockers (carried unresolved since v1.4, explicitly out of v1.9 scope — v2.0 is the deploy)**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1** (PROJECT.md Key Decisions, ⚠️ Revisit)

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence,
  flip the source debug session's / verification's `status` field in that same commit. v1.6 lost a
  phase slot (40.1) to a stale `diagnosed` status; no structural fix has shipped. The v1.8 close hit
  the same class again — the Phase 31 FK-cascade deferred item was still open on disk months after
  Phase 48 fixed it.

### Roadmap Evolution

- Phase 54.1 inserted after Phase 54: Justice Portraits & Biographical Enrichment — photos and FJC bios had no home in v1.9; two external deliverables (portrait set, Figma bio card) commissioned 2026-09-24

## Deferred Items

### Resolved by this roadmap

| Category | Item | Resolution |
|----------|------|------------|
| scope | Person-dedup mismatch across the justice-import tools (White/Black/Clark/Douglas), deferred at v1.7 Phase 42 | **Scheduled** — Phase 52. It is not four bad rows; it is 49 of 114, visible as four only because four fixtures are imported |

### Acknowledged at the v1.8 close (2026-09-23)

22 open artifacts were acknowledged and deferred rather than resolved, per operator direction at
`/gsd-complete-milestone`. This table is the disclosure record; the suppression itself lives in each
artifact and lapses automatically if that artifact's state changes again.

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| seeds | SEED-001-rework-resolve-table-requirements | dormant | 2026-09-23 | v1.8 |
| seeds | SEED-002-scotus-teams-video-call-presentation | dormant | 2026-09-23 | v1.8 |
| uat_gaps | 04/04-UAT.md (archived v1.0) | passed — 0 pending scenarios (stale marker) | 2026-09-23 | v1.8 |
| deferred_items | 49/deferred-items.md: `test_admin_jobs_service.py` trust-tier regressions vs the deferred PDF-pipeline wiring gap | acknowledged | 2026-09-23 | v1.8 |
| deferred_items | 49/deferred-items.md: D-35 convergence — the public chat page's independently derived bench flag is not reconciled | acknowledged | 2026-09-23 | v1.8 |
| deferred_items | 49/deferred-items.md: D-35 convergence — person-to-participant assignment remains uneditable on the Speakers card | acknowledged | 2026-09-23 | v1.8 |
| deferred_items | 49/deferred-items.md: Trivial-ACCEPT provenance restamp (accepted as known debt, override in `50-VERIFICATION.md`) | acknowledged | 2026-09-23 | v1.8 |
| deferred_items | 46/deferred-items.md (archived v1.7): pre-existing full-suite failures found at the 46-03 checkpoint | acknowledged | 2026-09-23 | v1.8 |
| deferred_items | 31/deferred-items.md (archived v1.6): `delete_argument` FK cascade — **fixed in Phase 48 plan 48-02**; record was stale | acknowledged | 2026-09-23 | v1.8 |
| todos | 2026-08-12-speakers-bench-classification-silent-fallback.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-14-revisit-pre-relocation-checkout-removal.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-18-pdf-provenance-live-fixture-verification.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-20-reset-error-copy-overclaims-db-corruption.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-20-reset-has-no-timeout-or-progress.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-20-reset-to-fixture-stale-created-at-timestamps.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-28-transcript-long-utterance-paragraph-splitting.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-28-transcript-style-switcher.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-29-bionic-reading-investigation.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-08-31-harden-variant-switcher.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-09-03-consolidated-dockets-unreachable-without-pdf-path.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-09-03-dense-admin-tables-at-mobile-widths.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-09-03-speaker-colour-on-bubbles-and-photo-avatars.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-09-03-speaker-popover-height-and-scroll-placement.md | (presence-only) | 2026-09-23 | v1.8 |
| todos | 2026-09-03-transcript-nav-return-to-top-segment.md | (presence-only) | 2026-09-23 | v1.8 |

**Also resolved during the close, not acknowledged:** the D-35a published-write inventory in
`49/deferred-items.md` was already `Status: closed` (D-23, operator, 2026-08-25). Its four GFM tables
were being read by the audit scanner as 14 separate open items that its own acknowledge writer cannot
suppress by design, so the section was moved verbatim to
`.planning/milestones/v1.8-phases/49-review-model/49-PUBLISHED-WRITE-INVENTORY.md` and marked
`resolved` in place. No content was lost.

### Carried from earlier milestone closes

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| backlog | Phase 999.9 — edit affordance on utterances + speaker popover | backlog candidate | 2026-07-13 |
| backlog | Phases 999.2, 999.3, 999.5, 999.7, 999.10 | backlog candidates for `/gsd-review-backlog` | 2026-07-12 |
| backlog | Phases 999.4 / 999.6 / 999.8 | **CLOSED 2026-09-23 — absorbed into Phase 51 (DS-02 / DS-04 / DS-03)** | 2026-07-12 |
| backlog | Phase 999.11 — PDF pipeline path adapts to `import_run` as a peer strategy (IMPORT-02) | split out of Phase 50 under the corpus-first decision | 2026-08-25 |
| backlog | Phase 999.12 — "request a case" from the zero-result search state | captured during v1.9 scoping; promote only if Phase 58's logged-query data proves insufficient | 2026-09-23 |
| scope | Recent terms (post-2019) | requires the deferred PDF route, Phase 999.11 | 2026-09-23 |
| scope | Phase 04 accessibility audit / axe-core assertion | operator decision 2026-09-23 — waiver stands, out of v1.9 | 2026-09-23 |

## Session Continuity

Last session: 2026-09-29T12:19:27.341Z
Stopped at: Completed 53-05-PLAN.md
Resume file: None

## Operator Next Steps

- Review `.planning/ROADMAP.md` (Phases 52–58) and `.planning/REQUIREMENTS.md` traceability
- Then `/gsd-plan-phase 52` to plan Justice Identity

## Decisions

- [Phase 52]: oyez_speaker_id promoted from unused side-column to primary justice identity key (Phase 52-01); full_name equality demoted to fallback for unmapped D-04 rows.
- [Phase 52]: Person.display_name is written by plain assignment, never through the apply_person_value_change authority ladder -- D-09 keeps it off PersonUpdate's allow-list, so no operator edit can ever exist to arbitrate against.
- [Phase 52]: derive_initials co-located in api/domain/person_names.py with _KNOWN_SUFFIXES rather than a new module. — D-13's fallback is defined in terms of the exact suffix vocabulary; separating them risks a fourth splitter appearing elsewhere unnoticed.
- [Phase 52]: arguments.py pre-selects structured-parts-vs-raw_speaker_label arguments in a plain if/else before one derive_initials call per row. — Keeps derive_initials to a single call site per file (the plan's own acceptance criterion), not a ternary with two inline calls.
- [Phase 52]: Both new identity fields (display_name, oyez_speaker_id) are read directly off data.person in the Svelte template, never captured into a top-level const or $derived. — Matches the existing data.person.full_name idiom at the same call site and avoids the stale-prop-capture bug class this codebase has already been bitten by once.
- [Phase 52]: Phase 52-04: justice bench seed inserted after reset_to_fixture's TRUNCATE commit and before the FIXTURE_SET reseed loop (D-16), with a pre-flight requiring both justice CSVs before any destructive statement. — An absent mapping must never be able to leave the database empty; the seed must run before the reseed loop so oyez_speaker_id resolution hits on the corpus importer's first lookup key.
- [Phase 52]: Phase 52-04: fixed the reset_to_fixture stale-created_at defect with one extra db.commit() between the fixture-verification loop and the state-realization block, rather than restructuring the whole reset's transaction boundaries. — approve_argument/publish_argument already commit at their own end; the loop's own stale open transaction was the only missing commit boundary.
- [Phase 52]: Phase 52-05: backend fixture-state progress carries a machine token ('seeding_justices' | 'reseeding_fixture_N'), not the rendered copy string; the frontend owns the Copywriting Contract's literal strings and maps the token to them, so the two layers can't drift independently.
- [Phase 52]: Phase 52-05: the D-14 re-read runs directly against FASTAPI_BASE_URL from +page.server.ts's own server action rather than through the new dev-fixture-state proxy — that proxy exists only for the browser's client-side polling, which has no FASTAPI_BASE_URL access.
- [Phase 52]: Phase 52-05: AbortSignal sized at 180s (~2.5x the 71.67s measured floor from 52-04), not re-measured through the live HTTP path in this plan — deferred to the phase's end-of-phase human-check UAT item.
- [Phase 52]: Phase 52-06: list_resolve_rows_for_job's SELECT extended with Person.first_name/last_name/name_suffix so derive_initials has structured parts in hand at one call site per row, reused across the bench and advocate dict branches.
- [Phase 52]: Phase 52-06: the null-initials case gets no client-side rendering branch in ResolveCard.svelte -- person_id null implies full_name null too, so the existing {#if fullName} guard already covers it; no ?? '?' fallback was added.
- [Phase 53]: Phase 53-01: speaker_undetermined is computed once in _incoming_utterance_rows immediately after speaker_id is read and before the resolved_participants cache branch, so a cached and a freshly-resolved speaker both carry the identical D-05 fact.
- [Phase 53]: Phase 53-01: the D-06 majority denominator/numerator (non_stage_total/undetermined_count) are counted inline in _load_constituents' existing utterance loop, never via a second query or per-row blocker bump -- a single post-loop check.
- [Phase 53]: Phase 53-01: _seed_argument's utterance spec gained an optional 4th (speaker_undetermined) tuple element instead of a second seeding helper -- every existing 3-element caller, including test_published_gate.py's wrapper, keeps working unchanged.
- [Phase 53]: Three-way row classification (speech/room-event/inaudible) replaces the boolean is_stage_direction split in the corpus importer; a known speaker's whole-turn Inaudible marker is stored as their own attributed row instead of a stage direction.
- [Phase 53]: Phase 53-05: blockerSentence extracted from three verbatim-duplicated per-page copies into one shared, unit-tested app/src/lib/admin/blockerSentence.js (following the resetOutcome.js precedent) -- the D-18 majority_undetermined_speaker sentence is added once and rendered identically on all three admin surfaces.

### Blockers

- A third, independent initials splitter (byte-identical logic) survives in app/src/lib/admin/ResolveCard.svelte -- out of this plan's scope, filed as .planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md for the operator.
