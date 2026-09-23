---
gsd_state_version: "1.0"
milestone: v1.9
milestone_name: The Site Becomes Complete
status: planning
last_updated: "2026-09-23T19:23:44.569Z"
last_activity: 2026-09-23
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-23 after the v1.8 milestone close)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** No active milestone. v1.8 shipped 2026-09-23; run `/gsd-new-milestone` to scope the next one.

**Standing policies** (full text in CLAUDE.md, adopted 2026-08-27 by the operator): the **Defect Policy**
— defects whose correct behavior is already determined are fixed silently and reported in one line;
only questions needing the operator's taste are escalated — and the **Testing Policy** — no static
source-text contract tests for frontend behavior, tests retire with the behavior they pinned, no
phase-numbered test modules, ~2:1 test:code as a guideline. Both govern all later work.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-09-23 — Milestone v1.9 started

## Performance Metrics

- v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12)
- v1.6: 11 phases, 51 plans, 17 days (2026-07-12 → 2026-07-29)
- v1.7: 6 phases, 29 plans, 18 days (2026-07-29 → 2026-08-15)
- v1.8: 5 phases, 45 plans, 120 tasks, 37 days (2026-08-17 → 2026-09-23), 368 commits

## Deferred Items

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
| scope | Person-dedup mismatch across the justice-import tools (White/Black/Clark/Douglas) | deferred to its own future phase | v1.7 Phase 42 |

## Accumulated Context

Per-phase decisions, deviations and evidence for v1.8 (Phases 47–51) are archived under
`.planning/milestones/v1.8-phases/*/` and summarised in `.planning/milestones/v1.8-ROADMAP.md`.
The cross-milestone decision log lives in PROJECT.md's Key Decisions table. Cleared here at the
milestone close per the standard STATE.md reset.

### Open concerns carried into the next milestone

**Verification debt**

- **Phase 04 accessibility is asserted, not measured.** No assistive-technology walkthrough and no
  axe-core/WAVE scan has ever run against the argument view; the ARIA markup and contrast tokens were
  only ever checked by reading source. Waived by the operator on 2026-08-18 via `04-VERIFICATION.md`'s
  `overrides` block. Phases 14, 38, 39, 45 **and now 51** have all changed the popover and argument
  view since, so the drift is worse than when the waiver was granted — Phase 51 reworked this exact UI
  and did not add an axe-core assertion. The cheap permanent fix is still an axe-core assertion inside
  a browser test rather than a human checklist.
- **Three UAT behaviours are implemented but have never been observed:** the failed-run error panel
  (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder and per-row Save gate on the
  argument editor, and the non-interactive avatar for an unresolved utterance.
- **Phase 49's live-browser human checks** are consolidated in `49-EVIDENCE.md` §9 (now under
  `.planning/milestones/v1.8-phases/49-review-model/`). Every underlying data/API layer was verified by
  script; the on-screen render was blocked at the time on sandbox `.env` credential access. Browser
  tooling works now — worth re-running that list rather than assuming it.

**Code debt**

- **32 `state_referenced_locally` svelte-check warnings across 9 admin files.** The same prop-capture
  class as Phase 51's CR-01. None on public surfaces; known open at the v1.8 close, not blocking.
- **Trivial-ACCEPT provenance restamp.** `decide_write` returns `ACCEPT` both for a genuine gap-fill and
  for a trivial agreement, and three callers restamp `source`/`method` for both — so a byte-identical
  re-import can demote an OPERATOR-stamped `Argument`/`Case` row to `corpus`. No data loss; what
  degrades is the provenance label. Fix is to gate each restamp on `_values_differ` (already imported
  in all three modules). Full write-up in the archived `49/deferred-items.md`.

**Environment**

- **4 `test_phase38_people_ui_contract.py` tests SKIP rather than fail when `node` is off PATH** — the
  default for a pytest run launched outside an nvm shell. A regression there would be invisible.
- **`TEST_DATABASE_URL` and `DATABASE_URL` resolve to the same physical Postgres database in this
  sandbox.** Running a full-suite pytest run and a direct dev-DB script concurrently produced spurious
  deadlock failures. Do not run both at once.

**Deployment blockers (carried unresolved since v1.4, explicitly out of v1.8 scope)**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1** (PROJECT.md Key Decisions, ⚠️ Revisit)

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence, flip
  the source debug session's / verification's `status` field in that same commit. v1.6 lost a phase slot
  (40.1) to a stale `diagnosed` status; no structural fix has shipped. The v1.8 close hit the same class
  again — the Phase 31 FK-cascade deferred item was still open on disk months after Phase 48 fixed it.

## Session Continuity

Last session: 2026-09-23
Stopped at: Milestone v1.8 closed and archived
Resume file: None

## Operator Next Steps

- Start the next milestone with `/gsd-new-milestone`
