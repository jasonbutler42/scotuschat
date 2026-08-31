---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Import & Provenance Re-model
current_phase: 51
current_phase_name: Design System & Noun Alignment
status: "Phase 50 COMPLETE and VERIFIED 2026-08-27; debridement pass done 2026-08-27. All 7 plans, all 4 waves, 4/4 success criteria verified in 50-VERIFICATION.md. UAT complete 35/35. Phase-50 verification also closed 50-REVIEW.md CR-01 and CR-02 and the SC-4 ungated-writer gap. One provenance-label defect (trivial-ACCEPT restamp) accepted as known debt under an operator override and logged to deferred-items.md. Next: Phase 51 (Design System & Noun Alignment), the last v1.8 phase."
stopped_at: Completed 51-09-PLAN.md (all 3 tasks). Next: 51-10 — the operator-ruling checkpoint, autonomous:false.
last_updated: "2026-08-31T14:55:00.000Z"
last_activity: 2026-08-31
last_activity_desc: Plan 51-09 complete — tokenize-styles script (26 unit tests), 1,566 literals converted across 22 .svelte files, and 51-ADMIN-ARTIFACTS.md written for the 51-10 ruling checkpoint. Zero mapped hex / numeric font-size / numeric font-weight remain; the 29 surviving hexes are the token map's 10 open rows, awaiting operator decisions. Five real-browser tests could not run in this environment (Chromium missing libnspr4).
state_head: 504171a6c4dcdb96233dd97a5ab2ce045ff06ab1
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 45
  completed_plans: 44
  percent: 82
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-18 — Phase 47 complete; corpus-first / PDF-deferred scope decision recorded)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 51 — Design System & Noun Alignment

**Phase 50 scope resolved 2026-08-25** (at `/gsd-plan-phase 50` time, by the operator): the phase's 2026-08-18 scope flag is closed **corpus-only**. Its PDF half — old success criterion 2, IMPORT-02, "the PDF pipeline path reads and writes `import_run` as one strategy among peers" — **split out to Phase 999.11 (BACKLOG)**, on the deferred PDF route. Phase 50 now carries 4 requirements (IMPORT-01, IMPORT-03, IMPORT-04, IMPORT-05) and 4 success criteria, renumbered. IMPORT-05's authority ordering stays here **in full** (all four rungs, one total ordering function); its `operator`/`corpus` rungs get live corpus proof, its `pdf/rule_based`/`pdf/llm_corrective` rungs get real-writer-test proof — the same verification split Phase 47 established. Recorded in ROADMAP.md (Phase 50 section + v1.8 bullet + Backlog 999.11), REQUIREMENTS.md (IMPORT-02 remapped, coverage note), and PROJECT.md Key Decisions. Discuss and plan are both DONE: `50-CONTEXT.md` (30 locked decisions), `50-RESEARCH.md`, `50-PATTERNS.md`, `50-VALIDATION.md` and 7 PLAN.md files are on disk.

## Debridement Pass (2026-08-27)

A one-off cleanup between Phase 50 and Phase 51, at operator direction. Not a
phase; no requirements, no plans.

**Two standing policies now live in CLAUDE.md** and govern all later work:

- **Defect Policy** — defects whose correct behavior is already determined
  (concurrency, FK cascades, idempotency, failing tests, stale-state bugs) are
  fixed silently and reported in one line. Only questions needing the operator's
  taste (what a screen shows, whether a state is reachable, domain semantics,
  scope) get asked. This overrides GSD's default checkpoint/UAT instincts.

- **Testing Policy** — no static source-text contract tests for frontend
  behavior; tests retire with the behavior they pinned; no phase-numbered test
  modules for new work; ~2:1 test:code as a guideline whose real question is
  whether a given piece of tooling makes sense for the developers actually on
  this project (one person, no hand-off).

**What changed:**

- 16 test files deleted (6,319 LOC) — fourteen pure static frontend contract
  modules plus two pinned to behavior later phases removed. 4 more files trimmed
  of their `.svelte`-reading tests while keeping every live DB assertion.

- 728 lines across 45 production files stripped of planning-artifact citations
  (D-NN / Phase N / plan refs / T-NN). Pass 1 of two; explanation prose kept
  intact. A token-stream check proved no executable code changed.

- Local tool state (`.claude/`, `.codex/`, `.gsd/`), operator uploads, dry-run
  output, and root screenshots are now gitignored.

**Suite: 1306 passed, 5 xfailed, 0 failed** (was 1666/5/0 — every disappeared
test was deleted deliberately). Test:code ratio 2.44:1 -> 2.04:1.

**Deferred:** Pass 2 of the comment cleanup — collapsing multi-line narration to
the invariant the code depends on, and citations that are the grammatical
subject of their sentence. Needs judgment, not a regex; review file-by-file
whenever the operator wants it.

**Corrected during the pass:** an earlier recommendation to delete `AdminJob`
was wrong. It is still the live backbone of the PDF ingest/parse/resolve path
and the `/admin/pipeline` UI — 26 production files. The only genuinely dead
weight is two `is_corpus` subquery branches already commented as retained for
999.11. Leave it alone.

## Current Position

Phase: 51 (Design System & Noun Alignment) — EXECUTING
Last activity: 2026-08-28 — Wave 1 complete (plans 51-01, 51-02). Wave 2 plans `51-03`
(design tokens, D-01/D-02/D-03) and `51-04` (term-grouped public API, D-14/D-15/D-16)
complete. Tailwind removed (0 packages added, 69
removed); full two-layer token set (14 primitives + 37 semantic names) authored in
`app/src/app.css`, matching plan 51-01's Figma `semantic` collection exactly;
`51-TOKEN-MAP.md` published; `.planning/codebase/DESIGN-SYSTEM.md` rewritten. Full
suite unchanged after 51-03: 1318 passed / 5 xfailed / 0 failed. `npm run check`/`npm run build`
both green. **Open for a human:** 3 of 4 required browser tests and the plan's
backstop visual truth (no layout shift from preflight removal) could not be
observed — no Chromium/Edge binary in this sandbox (same constraint 51-02 hit).
See `51-03-SUMMARY.md` Issues Encountered.

**Wave 2 plan `51-04` — COMPLETE (2026-08-28).** `GET /arguments/terms` (term
index with published-argument counts) and `GET /arguments/term/{term_year}`
(term-scoped listing), backed by `list_terms`/`list_arguments_for_term` in
`api/services/arguments.py` — both extend the same `is_lead`-joined,
both-published-predicates query shape `get_cases()` already uses, grouping on
`Case.term_year` and counting `DISTINCT Argument.id` so a consolidated docket
never inflates a count. D-16 Variant A (locked in `51-01`) applied: no
`argument_participants` -> `people` join, no `advocates` field —
`api/schemas/arguments.py`'s `ArgumentListItem` ships the minimal row only.
The structural leak-ban (`test_trust_public_leak_ban.py`) and published-gate
contract (`test_published_gate.py`) were both extended to cover the new
module/functions, and — per the plan's own non-vacuity requirement — both
extensions were proven live rather than asserted: a temporary `trust_tier`
field made the leak-ban fail (reverted), and a temporary
`response_model=None` route returning a raw dict with an injected banned key
made the new live decoded-JSON assertion fail while the static leak-ban
module still passed (reverted byte-identical). 16 new tests in
`api/tests/test_public_arguments_listing.py`. Full suite: 1378 passed, 5
xfailed, 0 failed (was 1318 before this plan). See `51-04-SUMMARY.md`.

**Wave 2 plan `51-05` — COMPLETE (2026-08-28).** `app/src/lib/components/` (15
files) split into `lib/public/` (5: `ChatBubble`, `StageDirection`,
`SectionRail`, `SpeakerPopover`, `MobileNavBar`) and `lib/admin/` (9:
`AdminSubNav`, `ArgumentDetailsCard`, `CopyableExtractedValue`,
`CreatePersonPopover`, `DocketPillInput`, `FailedStepGuidance`,
`ResolveCard`, `RunStatusCard`, `StatCard`), with `lib/components/` slimmed
to `TopNav.svelte` alone — the one component genuinely imported by both the
root and admin layouts (confirmed by grep, not assumed).
`app/src/lib/README.md` states the four-location placement rule for future
components. Pure `git mv` rename with zero behavioural change, mechanically
proven: every changed line across both move commits is an import path.
One stale import fixed in a test fixture
(`app/tests/fixtures/copyable-extracted-value-main.ts`), found by the
plan's own required whole-repo grep. `npm run check`/`npm run build` both
green; full suite unchanged at 1378 passed / 5 xfailed / 0 failed. DS-02
stays `Pending` — shared with plan `51-06` (creates `lib/primitives/`),
which has not yet produced a SUMMARY (shared-ID gate). **Open for a
human:** all four `app/tests/*.browser.test.mjs` could not run to
completion — no Chromium/Edge binary in this sandbox (same constraint
51-02/51-03 hit); `npm run check`+`npm run build` both green is the
strongest available signal for an import-only rename. See
`51-05-SUMMARY.md`.

**Wave 3 plan `51-06` — COMPLETE (2026-08-28).** Four D-17 primitives
(`Button`, `Badge`, `Input`, `Card`) landed in `app/src/lib/primitives/`,
filenames matching the Figma `Primitives` frame names, every value a
`var(--token)` reference, no primitive importing from `lib/public` or
`lib/admin`. `StatCard.svelte` now delegates to `Card` (one card definition
site, live render path on the admin dashboard); `DocketPillInput.svelte`'s
free-text field now delegates to `Input` (external prop shape and behavior
unchanged). Task 1's blocking package-legitimacy checkpoint (T-51-SC) caught
a real defect before it landed: `lucide-svelte` — the package D-18
recorded — is deprecated in favor of the scoped `@lucide/svelte` successor
(same maintainer/repo, clean `svelte ^5` peer range vs. the deprecated
package's prerelease range). Operator approved the substitution;
`@lucide/svelte@^1.35.0` installed, exactly one dependency added, zero
transitive deps. A pre-existing MIT->ISC license misstatement for the
package was corrected in `51-UI-SPEC.md` and `51-DESIGN-DECISIONS.md`.
`Button`'s icon-only accessible-name contract (label/ariaLabel/
ariaLabelledby) is enforced by a TypeScript discriminated union — proven
live with a deliberate temporary violation (compile error), then reverted,
same for `Badge`'s required `label`. `51-DESIGN-DECISIONS.md` gained the
D-18 bits-ui-vs-hand-rolled report (all four primitives hand-rolled; none
needed a focus-managed overlay or roving-tabindex control). `npm run
check`/`npm run build` both green; bare `pytest -q`: 1378 passed, 5
xfailed, 0 failed (unchanged — frontend-only plan). DS-02/DS-03 stay
`Pending` — shared-ID gate holds them for later sibling plans in this
phase. **Open for a human:** the admin dashboard's stat cards, the
pipeline page's docket field, and `case-required-recovery.browser.test.mjs`
itself were not observed in a real browser — no Chromium/Edge binary in
this sandbox (same constraint every prior plan in this phase hit); that
browser test also does not exercise `DocketPillInput`'s field even where a
browser is available (confirmed by reading it — it drives a different,
unrelated `docket_number` field on the argument-detail page). See
`51-06-SUMMARY.md` Issues Encountered.

**Wave 3 plan `51-07` — COMPLETE (2026-08-28).** Closed the folded
IN-02/IN-03 duplication todo (`app/src/lib/types/speaker.ts` — single
`TenureRow`/`SpeakerDetail` site; `SpeakerPopover.svelte`'s duplicated
side-colour ternary collapsed to one computation site) and shipped D-19's
Style B2 transcript reading layer: run grouping via `$derived.by` before
layout (the structural unit — consecutive same-speaker utterances,
stage directions always terminate a run), one sticky outside-rail avatar
per run (`position:sticky;bottom:var(--space-sm)`, flex-column
`justify-content:flex-end` so it rests at the run's bottom when short and
travels/pins when tall), and the 6/2px corner-rounding table via a new
`position` prop on `ChatBubble`. All five `lib/public/` components plus
the transcript route are now token-only (zero raw hex, confirmed after
excluding a `{#each` grep false-positive — Svelte's each-block syntax
happens to match the hex-literal regex, pre-existing, not a real
literal). P-06 compliance found and fixed along the way: `SpeakerPopover`'s
bio text used a 3-line `-webkit-line-clamp` + "Read more" toggle (Phase 45
BUG-02's fix for an unrelated card-overflow problem) — removed, since P-06
explicitly bans truncating popover content; the bio now always renders in
full. Landmine audit: zero top-level `const` captures off `data` in the
route (already all `$derived`/`$derived.by`). Verified live via a real
vite dev server + mock API + curl SSR fetch (no browser tool in this
sandbox): 2 `role="article"` runs, 1 `role="note"` stage direction,
correct 6/2px radii per run position, correct section-anchor id, live
`position:sticky` declaration all present. `npm run check`/`build` both
green; bare `pytest -q`: 1378 passed, 5 xfailed, 0 failed (unchanged —
frontend-only plan). Fixed a pre-existing stale selector in
`tenure-public-title.browser.test.mjs` (queried `.popover-card p` for
tenure info that has rendered as `<span>` since some prior pass, not this
plan). **Open for a human:** the sticky-avatar scroll behavior over real
distance, the Figma frame comparison at 375px/1280px, the Justice-vs-
advocate visual-weight side-by-side, and a full-length argument scroll
test — no browser tool / Figma MCP available to this executor. See
`51-07-SUMMARY.md` Issues Encountered.

**Wave 4 plan `51-08` — COMPLETE (2026-08-28).** `/arguments` is now the
term index (`GET /arguments/terms`), `/arguments/term/{year}` the term
detail (`GET /arguments/term/{term_year}`), replacing plan 51-02's
transitional flat listing. `TermRow.svelte` ships D-16 Variant A's locked
three-field row (case name, argued date, docket number) — no advocate
line, no `argument_participants` -> `people` join, exactly as
`51-DESIGN-DECISIONS.md` recorded. `app/src/lib/formatting.ts` is the
single `formatDate`/`formatArgumentCount` definition site both listing
routes share. Added `app/src/routes/arguments/+error.svelte` (Rule 2 —
not in the plan's file list) so the Copywriting Contract's error string
renders with no leaked HTTP status number, which SvelteKit's default
fallback error page would otherwise expose. Task 3 retired the `/cases`
API surface (`api/routers/cases.py`, `api/services/cases.py`,
`api/schemas/cases.py`) now that its last consumer (plan 51-02's
transitional listing) is gone — every guarantee its tests carried
(is_lead consolidated-docket filter, `create_all` ban, server-only
`FASTAPI_BASE_URL`, published-gate source assertions, unpublish
invisibility, the live trust-tier leak-ban half, two router-mount
regression guards) was migrated onto its replacement rather than dropped;
`GET /cases` now 404s. A whole-repo grep sweep (not just the plan's own
suggested patterns) found and fixed a consumer the plan's read_first list
missed: `tests/test_admin_router.py::test_main_py_still_registers_all_existing_routers`
asserted `cases_router` presence and would have failed the suite — flipped
to assert absence. Bare `pytest -q`: 1348 passed, 5 xfailed, 0 failed
(was 1378 before this plan — net count reflects both new tests added and
the deleted cases-specific test modules/classes). `npm run check`/`build`
both green. **Open for a human:** the plan's own first real-browser test
for the public listing (`app/tests/arguments-listing.browser.test.mjs`,
6 cases) is written but unrun — no Chromium/Edge binary in this sandbox,
same constraint every prior Phase 51 plan hit; the ~65-term/~150-row
viewport-scroll backstop truths and the Figma `d16-comparison` frame
match are also unobserved (no Figma MCP access to this executor either).
See `51-08-SUMMARY.md`.

**Next action:** `/gsd-verify-work 51` once the remaining plans
(`51-09` token sweep, `51-10` phase-wide inventory) are done — those two
are unaffected by 51-08's scope and can proceed independently.

**Wave 1 outcomes that bind later waves:**

- `51-01` closed the three blocking rulings, recorded in `51-DESIGN-DECISIONS.md`:
  D-16 → **Variant A** (minimal term row; advocate join deferred, not discarded),
  D-18 → **`lucide-svelte`** (blocked on the 51-06 package-legitimacy gate before install),
  UI-SPEC E4 → loading variant on the **shared** Button primitive.

- Figma file `KICu66PtMLHk4fmxJYPggx` is the reference 51-03 (semantic variable names →
  `app/src/app.css :root`) and 51-06 (frame names → `lib/primitives/*.svelte`) read from.

- **A `gsd-executor` subagent cannot reach the Figma MCP in this project** — `ToolSearch` is
  disabled in subagents and the Figma tools are deferred. Figma-touching tasks must run
  inline in the orchestrator session. 51-01 ran inline for this reason.

**Wave 1 plan `51-02` — COMPLETE (2026-08-28).** `Argument.slug` (migration
0031, nullable, no backfill), `api.domain.argument_slug.derive_argument_slug`
(reserved-word guard D-13; `question_number` chosen as the primary
collision discriminator after querying the real ~7,800-row ConvoKit corpus —
`argued_date` collides or is null in 45.6% of the 952 cases that ever need a
suffix), and the `type="tracer"` slice: one published corpus argument
reachable end to end at `/arguments/{slug}` — `GET /arguments/by-slug/{slug}/
{utterances,speakers}` sharing `get_argument_with_utterances`'s exact
published gate, `/cases` route tree deleted with no redirect layer (D-10/D-11),
DS-01 and the Phase 51 ROADMAP entry amended to match. Checkpoints 1/2 (the
stored-immutable-slug and flat-no-redirect one-way-door decisions) resolved
directly from `51-CONTEXT.md`'s already-locked decisions, not re-prompted.
Live-proven: a real `POST /admin/dev/reset-to-fixture` reseed left zero
published-with-null-slug rows, and a real vite dev server + uvicorn backend
rendered `/arguments` and `/arguments/{slug}` correctly (verified via curl —
no browser binary in this sandbox; logged as an unrun-verify item). Two
pre-existing tests broken by this plan's own edits were found and fixed
(byte-identical-404 count, one stale frontend static-contract test deleted
per the Testing Policy). Full suite: 1318 passed, 5 xfailed, 0 failed. See
`51-02-SUMMARY.md`.

**Workflow config changed 2026-08-27 (operator):** `nyquist_validation`, `security_enforcement`, `ui_review`, and `api_coverage_gate` are now OFF; `code_review` stays ON. Rationale: across phase 50 the three disabled review gates produced nothing (two never ran; nyquist left a draft VALIDATION.md), `api_coverage_gate` emitted only an advisory asking to confirm a true statement, and `code_review` was the gate that found the two most substantive defects. Both verify:pre and verify:post now resolve to zero active gates.

- **Wave 1: `50-01` — COMPLETE (2026-08-26).** Migration `0030` (six nullable columns, no backfill), the frozen `api/domain/content_digest.py` contract (Task 0 checkpoint: `freeze-as-proposed`), and the `type="tracer"` slice: corpus import creates zero `AdminJob` rows, stamps `oyez_speaker_id`/`content_digest`, survives a byte-identical double-import across all eight affected tables, and `approve_argument` + a reworked `reset_to_fixture` replace the AdminJob-based approve path. `_reconcile_conversation` establishes only the branch/digest-read/no-op guarantee — the real compare-and-write body is `50-05`'s. Full suite: 1507 passed, 5 xfailed, 0 failed. See `50-01-SUMMARY.md`.
- **Wave 2 plan `50-02` — COMPLETE (2026-08-26).** `apply_argument_value_change`/`apply_case_value_change` — true peers of the two Phase 49 gate functions, both routing through the single `decide_write`. PD-07 fail-closed NULL-provenance pre-check. PD-13 gap-fill pre-check applied to all four gate functions, with a deliberate OPERATOR-authority scope guard on the two EXISTING gates (deviation — the literal unconditional plan text would have reopened the CR-02/CR-04 defect; see `50-02-SUMMARY.md`). `_argument_attention_predicate` legs 5/6 + `ReviewQueueArgumentItem.argument_discrepancies` make an argument-level or lead-case-level discrepancy visible in `/admin/review` (render itself is `50-04`'s). Full suite: 1535 passed, 5 xfailed, 0 failed (was 1507/5; +28 new tests, zero regressions). See `50-02-SUMMARY.md`.
- **Wave 2 plan `50-03` — COMPLETE (2026-08-26).** `POST /api/admin/arguments/{id}/approve` (D-14) makes a jobless corpus argument publishable end to end. `_stamp_operator_provenance` (PD-08) makes `Argument`/`Case`'s five compare-set columns reach OPERATOR authority — proved by a round-trip where a disagreeing corpus write is `REJECT_AND_RECORD`. `delete_argument`'s gate inverted to published-only (D-25/PD-11) with a `value_discrepancy` cascade fix (D-26) — including a real FK-orphaning gap this plan's own testing found and fixed (a surviving discrepancy row could reference an `ImportRun` about to be deleted; now NULLed first, mirroring the existing `AdminJob.argument_id` pattern). Full suite: 1554 passed, 5 xfailed, 0 failed (was 1535/5; +19 net new tests). See `50-03-SUMMARY.md`.
- **Wave 2 — DONE.** Both plans (`50-02`, `50-03`) complete.
- **Wave 3 plan `50-04` — COMPLETE (2026-08-26).** `/admin/review`: an argument-level or lead-case-level `value_discrepancy` now renders (a Discrepancy badge on the collapsed row's case name, a stored/incoming detail block at the top of the expanded panel, reusing the participant-level styling verbatim), and a CANDIDATE argument's expanded panel carries an "Approve — move to Draft" action posting to `50-03`'s argument-scoped approve route. Deviation: the Approve form was placed OUTSIDE the per-constituent `{#each}` loop the plan's read_first pointer named — a literal per-constituent placement would have either duplicated the button or (for a candidate argument with zero flagged constituents, queued solely via a degraded tier or an argument/case discrepancy) never rendered it at all, breaking D-14's own stated purpose. Task 2's browser `<human-check>` was NOT observed this session — no browser tool / `.env` admin credential access available; recorded as `WINDOWS.md` entry 30. Full suite: 1561 passed, 5 xfailed, 0 failed (was 1554/5; +7 is exactly the new contract-test assertions, zero regressions). See `50-04-SUMMARY.md`.
- **Wave 3 plan `50-05` — COMPLETE (2026-08-26).** The real D-02 compare-and-record field walk replaces `50-01`'s placeholder: `Argument`/`Case`/`ArgumentParticipant`/`Person` compare-set fields walked through the Phase 49/50-02 gates in PD-14's fixed order on every reconcile pass; D-04 `oyez_speaker_id`-only pairing; D-06's lazy `step="reconcile"` run (predictor imports `admin_review`'s own no-opinion/gap-fill helpers directly, never re-implements — PD-15); D-07's unconditional restamp; D-08's PUBLISHED-argument record-only freeze; D-10/D-11/D-13's whole-set utterance replacement under a new `step="parse"` run; D-28's `--dry-run` plus PD-17's five new batch counters. Two auto-fixed deviations found via the tracer test: (1) Rule 2 — `Argument`/`Case` never stamped `source`/`method` at first-import creation (unlike `ArgumentParticipant`/`ImportRun`), breaking D-09's byte-identical proof once D-07's restamp started firing; (2) Rule 1 — a brand-new `Person`'s `review_state` is `None` in-memory pre-flush, crashing `apply_person_value_change`. 35 new tests; `WINDOWS.md` #29 (the deferred-body placeholder) marked fixed, #31 added for D-09's live walkthrough (phase gate, not this plan's own verify). Full suite: 1596 passed, 5 xfailed, 0 failed (was 1561/5; +35 new tests, zero regressions). See `50-05-SUMMARY.md`.
- **Wave 3 plan `50-06` — COMPLETE (2026-08-26).** Closes the D-22 delegation sweep: `resolve.py`'s bulk `ArgumentParticipant.person_id` UPDATE replaced by a per-row `apply_participant_value_change` call (`Utterance.person_id` deliberately stays ungated, PD-19); `parse.py`'s `argued_date`/`case_name`/`source_docket` cover-metadata writes route through `apply_argument_value_change`/`apply_case_value_change` (the unconditional `case_name` overwrite is gone, T-50-20); `import_justices_csv.py`'s four blank-only name-part assignments become four `apply_person_value_change` calls (`incoming_source=seed`). SC-4 closes with `pipeline/tests/test_gated_column_writers.py` — 8 real-writer tests (not a source-text grep) plus a falsifiability control, hand-verified by temporarily reverting `resolve.py`'s writer and watching its named test fail. One test-fixture deviation (not a production bug): `test_rerun_preserves_operator_edited_parts_blank_only_prefill`'s fixture updated to carry `review_state=OPERATOR_EDITED`, revealing that `review_state` is PERSON-level (not per-field) — a new test (`test_rerun_upgrade_fills_all_blank_name_parts`) covers the all-blank prefill case separately. Full suite: 1618 passed, 5 xfailed, 0 failed (was 1596/5; +22 net new tests, zero regressions). See `50-06-SUMMARY.md`.
- Wave 3 — DONE. All plans (`50-04`, `50-05`, `50-06`) complete.
- **Wave 4 plan `50-07` — COMPLETE (2026-08-26).** `python -m pipeline prune-runs` (D-12): offline, deliberate reclamation of superseded `ImportRun`/`Utterance` rows — the served run (PD-22's exact `MAX(ImportRun.id)` select shape) is never a candidate, and a run with an OPEN `value_discrepancy` row is refused under every flag combination (PD-23). The public-leak ban extends to `content_digest`/`oyez_speaker_id`/`argument_discrepancies` and PD-17's six batch-counter names, with the false-green-guard convention extended in the same pass (an honest ORM-layer proof where no schema exposes a key yet). `/admin/pipeline` gains a one-line D-19 note; both `is_corpus` derivation sites in `admin_jobs.py` are commented as unreachable-by-construction, citing 999.11. `50-WRITER-INVENTORY.md` (24 rows, D-24) pairs plan 50-06's executable gate and found a third ungated writer pair (`parse.py`'s `_update_participant_sides`/`_update_participant_descriptors`) neither D-22's enumeration nor 50-06 caught — logged to `deferred-items.md`, not fixed (out of this plan's scope). D-23 closed in the same commit as the inventory (Phase 40.1 lesson): `deferred-items.md`'s Person-scoped `Status: open` now records the operator's no-Person-level-published-lock answer. Full suite: 1666 passed, 5 xfailed, 0 failed (was 1618/5; +48 new tests, zero regressions). See `50-07-SUMMARY.md`.
- **Wave 4 — DONE. Phase 50 (Unified Import Path) is fully complete — all 7 plans, all 4 waves.**

Three researcher open questions were resolved by the operator at planning time and are LOCKED in the plans: **OQ-1** — nullable `source`/`method` on both `Argument` and `Case`, no backfill, NULL is unknown and fails closed; **OQ-2** — `reset_to_fixture` keeps all four reference states, "Mid-pipeline" preserved by seeding a `step="reconcile"` ImportRun; **OQ-3** — the comparison digest is read from the latest `step="parse"` run, and a diff writes a new `step="parse"` run.

Planner deviations to watch at execute/verify time: **PD-01** dropped `side` from the digest field list; **PD-07/PD-08** make `update_argument`/`update_argument_metadata` stamp operator authority (a scoped deviation from Phase 49's D-22); **PD-13** adds a gap-fill rule to all four gates — the one change to Phase 49's frozen `decide_write` behavior, and it must be named in the phase summary.

Phase 49 close-out (historical, superseded — Phase 49 is closed and verified): Wave 6 (49-11, D-35a — the whole-argument published lock) is now **complete** — see `49-11-SUMMARY.md`. Six argument-data writers (`update_argument`, `update_argument_metadata`, `update_participant_side`, `update_resolve_row_for_job`, `resolve_job`, `create_person_for_job`) now share one published predicate and one error-prose clause, proved by live non-persistence tests; the deliberate non-locks (`unpublish_argument`, `resolve_participant_review`) are proved live too. The argument-detail page's `readonly is always false here` decision is reversed in place, cited to D-35/D-35a/operator/2026-08-24; the Case card and Argument Details card are locked behind 49-09's single `speakersLocked` flag with one page-level statement. `deferred-items.md`'s write-path inventory is now complete and four-way dispositioned; `49-CONTEXT.md` carries `### D-35a (locked)`. Full suite: 1150 passed across two split runs (no failures, no new skips, 12 pre-existing warnings). 49-12 (G-49-5c, narrow-viewport nav) also completed concurrently — see `49-12-SUMMARY.md`. **All Phase 49 plans (01-12) and all four reopened gaps are now closed.** Five browser human-check items from 49-11 Task 3 were NOT observed this session — no browser tool available to this executor; logged to `WINDOWS.md` entry 28. One NEW operator question remains open (Person-scoped write boundary — see `deferred-items.md`). Still open and NOT in any gap_ids: G-49-9a needs a visual re-check, and UAT sub-item 5.6 was never observed. (Phase 49 was subsequently re-verified and closed on 2026-08-25 — the `/gsd-verify-work 49` step named here is DONE.)

Phase 49-06 close-out notes (2026-08-23):

- Dev-only `seed_unresolved_speaker_fixture` (D-33a) ships: nulls one deterministically-selected `ArgumentParticipant.person_id` (preferring a participant whose `side` is already `UNKNOWN`, traced against the real consumer code rather than the plan's literal pick) plus its matching `Utterance.person_id` rows — closing the data-layer blocker for 26-UAT Test 26 and 14-UAT Test 8, both reclassified `waived -> blocked` (not `pass`) with dated, script-verified observations.
- **D-32's live authority-conflict walkthrough performed end to end via a repeatable script against the real dev DB** — found and fixed a real, phase-central gap in the same session: `_argument_attention_predicate` had no leg for "a constituent has an open discrepancy," so an operator-edited, already-resolved participant that a lower-authority re-import disagreed with (exactly REVIEW-02/REVIEW-04's central claim) was invisible in `/admin/review`. Fixed, tested, verified by re-running the same script.
- Corrected `49-RESEARCH.md` Pitfall 4's false premise ("no live corpus path can produce an unresolved speaker") — verified false against the live dev DB (argument 1788 had 11 `person_id IS NULL` rows from a job parked pre-resolve) before this plan started; not restated anywhere in the seeder's code/docstrings.
- The frontend `readonlyMode` split (flagged and deferred by both 49-04 and 49-05) is closed: `resolveCardReadonly` (`status === 'published'`) / `metadataReadonly` (unchanged).
- All five REVIEW-0X requirements now `Complete` in REQUIREMENTS.md.
- Full suite: **1414 passed, 5 xfailed, 0 failed** (up from 1403 at phase start). Confirmed in a fully isolated run — an earlier concurrent run (this plan's own dev-DB scripts running alongside a background pytest process) produced 2 spurious `DeadlockDetectedError` failures, an environment artifact (TEST_DATABASE_URL and DATABASE_URL resolve to the same physical database in this sandbox), not a regression.
- `.planning/WINDOWS.md` gained 9 entries this plan (2 deviations found+fixed, 1 corrected-premise deviation, 8 unrun-verify browser items covering the whole phase).

Phase 49-05 close-out notes (2026-08-23):

- Full `/admin/review` screen shipped: Arguments|People tabs, the trust-tier × review-state × status filter set with a fully specified server-side sort (published-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break — never created_at), expandable argument rows with discrepancy detail and the fixed-order Confirm/Confirm-as-unattributable/Edit/Re-flag action row, and the zero-constituent blockers fallback.
- Dashboard COUNT (`get_review_queue_stats`/`GET /api/admin/review/stats`) shares its inclusion predicate with the list queries by construction (`_argument_attention_predicate`/`_person_attention_predicate`), so the card and the screen can never disagree. AdminSubNav gained a Review link; the dashboard grid widened to 5 columns with a fifth StatCard.
- 27 new tests (11 query-behavior + 2 backstop in `test_admin_review_service.py`, 14 in new `test_phase49_review_ui_contract.py`). Full suite: 1403 passed, 5 xfailed, 0 failed (up from 1376/5/0).
- **Open for a human:** the Task 2 seven-item browser `<human-check>` walkthrough was not completed — same `.env`-credential-access constraint as 49-01/49-03. See `49-05-SUMMARY.md` coverage D4/D5.
- Person's provenance-note format deviates from the plan's literal `"{Source} · {method}"` spec (Person has no `method` field anywhere in `provenance_metadata`) — implemented as `"{Source} · {confidence}"` instead; documented in 49-05-SUMMARY.md Deviations.
- The frontend `readonlyMode` split (flagged by 49-04) remains open — not this plan's scope; left for 49-06 or a follow-up.
- REVIEW-03/REVIEW-04 remain `Pending` — both shared with 49-06 (not yet complete); shared-ID gate correctly held both back.

Phase 49-04 close-out notes (2026-08-23):

- Authority ladder (`api/domain/authority.py`) + the ONE gated writer (`api/services/admin_review.py`) shipped and exhaustively tested; all three named writers (`update_participant_side`, `update_resolve_row_for_job`, `update_person`) delegate — no ungated write path to `argument_participants`/`people` value columns survives.
- Fixed the D-18 regression deferred at plan 49-02 (`WINDOWS.md` #11, now marked `fixed`): `resolve_job`/`update_resolve_row_for_job` backfill `ArgumentParticipant.source`/`.method` from the job's parse-step `ImportRun` when never stamped. Full suite: 1376 passed, 5 xfailed, 0 failed (up from 1252/2 failed/5 xfailed baseline).
- REVIEW-02 and REVIEW-04 remain `Pending` in REQUIREMENTS.md — both shared with 49-05/49-06 (not yet complete); shared-ID gate correctly held both back.
- Participant editability widened to every unpublished state (candidate/draft/unpublished) — backend/API complete; the frontend `readonlyMode` flag at `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294` deliberately NOT widened (conflates Resolve-card editability with an unrelated ArgumentDetailsCard metadata form) — left for 49-05 or a follow-up. Folded todo `2026-08-21-widen-participant-editability-to-all-unpublished-states.md` stays in `pending/` (backend half done, frontend half open).

Phase 48 close-out notes (2026-08-21):

- All five requirements (TRUST-01 through TRUST-05) traced to named, green, automated checks in
  `48-EVIDENCE.md`'s requirement-traceability table, plus the carried D-22 cascade-defect fix and
  the D-23 public-leak-ban contract.

- Two new open items carried forward as standalone todos (not folded into Phase 48's own scope):
  `.planning/todos/pending/2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` (the
  underlying stale-value root cause behind the display-ordering bug this plan fixed — dev-only,
  `reset_to_fixture`'s session/transaction reuse) and
  `.planning/todos/pending/2026-08-21-widen-participant-editability-to-all-unpublished-states.md`
  (operator-requested widening of Resolve-card editability scope, deliberately deferred).

- 14-UAT Test 8 and 26-UAT Test 26 remain open (see Deferred Items below) — Phase 48's Finding 1
  (48-EVIDENCE.md) shows the reason D-21 gave for not closing them may not fully hold; worth a look
  before assuming new fixture work is required.

- Three of Phase 48's defects were found by **operator browser testing**, not the automated suite
  (silent list-page 422 swallow, unpublish/public-visibility across three read paths, shared-`form`
  error-routing bug on the detail page — all in plan 48-10) — the suite grew from 1114 to 1209 tests
  across the phase and passed clean over all three fixes.

- Test suite: **1209 passed, 5 xfailed, 0 failed, 0 skipped** (baseline at Phase 48 start was 1049;
  the 5 xfailed are the never-implemented Phase 31 stubs, tracked below, unchanged).

Progress: [████████░░] 80% (4 of 5 v1.8 phases complete)

## Deferred Items

Items deferred at v1.6 close on 2026-07-29, and where they landed in v1.7:

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-07-28-unpublished-argument-visible-in-cases-list.md (bug) | absorbed → BUG-01, Phase 45 |
| todo | 2026-07-29-popover-scrollbar-outside-card.md (ui) | absorbed → BUG-02, Phase 45 |
| seed | SEED-001-rework-resolve-table-requirements | surfaced and absorbed → RESOLVE-01–06, Phase 44 |

Still open from earlier milestones:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| backlog | Phase 999.9 — edit affordance on utterances + speaker popover | backlog (todo file moved to `todos/completed/`, tracked as 999.9) | 2026-07-13 |
| backlog | Phases 999.2–999.8 | 999.4/999.6/999.8 absorbed into v1.8 Phase 51 (DS-02/04/03); rest remain backlog candidates for `/gsd-review-backlog` | 2026-07-12 |
| verification | 01-VERIFICATION.md, 03-VERIFICATION.md | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — status flipped to `passed`; 03's five items map 1:1 onto `03-HUMAN-UAT.md` (complete, 5/5 pass) and 01's two are superseded by them | 2026-06-15 |
| verification | 04-VERIFICATION.md | CLOSED 2026-08-18 — 3 of 5 items verified against `04-UAT.md` (8/8 pass); the other 2 **WAIVED by operator, not verified**: no screen reader and no axe-core/WAVE scan has ever been run against this codebase. Recorded via the file's `overrides` block so `status: passed` never implies they were checked. **Accepted risk** on a phase whose goal is WCAG 2.1 AA — see the Blockers/Concerns entry | 2026-06-15 |
| verification | 11-VERIFICATION.md | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — status flipped to `passed`; all three items map 1:1 onto `11-UAT.md` Tests 1–3 (pass), and 11-UAT's one failed Gap was closed as BUG-01 in Phase 45 | 2026-06-29 |
| context_question | Phase 999.2 (999.2-CONTEXT.md, 3 open questions) | not started | 2026-07-12 |
| test_coverage | Phase 31 — 5 never-implemented `xfail(strict=True)` test stubs (`test_resolve_alias_hit`, `test_resolve_interactive_prompt`, `test_resolve_resumes_after_interrupt`, `test_seed_creates_justices`, `test_seed_idempotent`) | STILL OPEN — surfaced by the 2026-08-18 UAT audit as the one non-stale item in Phase 31's deferred-items.md besides the `delete_argument` cascade. All 5 bodies are `pytest.fail("not implemented")` behind `xfail(strict=True)`, so the suite reports 0 failures and the gap is invisible; they are exactly the full suite's `5 xfailed`. Real coverage work (mocked interactive `input()` flow, a resume-after-interrupt DB scenario, full seed-aliases integration), not a documentation fix | 2026-07-29 |
| human_uat | 4 UAT items the audit confirmed still testable | CLOSED 2026-08-18. **07-UAT Test 14 → pass**, verified automatically (ran `pipeline {ingest,parse,resolve} --help`; all flags present — the original blocker was an unactivated venv, never a defect). The other three **WAIVED by operator, not verified**: 07-UAT Test 13 (failed-state panel — needs a deliberately failed live run; re-test at Phase 50 with the PDF path), 26-UAT Test 26 (unresolved-advocate placeholder + Save gate — code confirmed present at `admin/arguments/[id]/+page.svelte:497,544` but never exercised in a browser; natural fit for Phase 49), 14-UAT Test 8 (needs an argument containing an unresolved speaker, which has never existed) | 2026-08-18 |

Acknowledged and deferred at v1.7 close on 2026-08-15 (all pre-existing backlog unrelated to what v1.7 shipped — no gaps in v1.7's own delivered scope):

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-08-11-create-person-popover-side-and-selection.md (ui) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speaker-popover-frontend-duplication-cleanup.md (ui, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speakers-bench-classification-silent-fallback.md (api, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-14-revisit-pre-relocation-checkout-removal.md (dev-environment, low) | pending — revisit after the relocated repo has run without incident for a period |
| seed | SEED-001-rework-resolve-table-requirements | dormant — the bulk of this seed was already absorbed into RESOLVE-01–06 (Phase 44); remaining scope, if any, is a candidate for `/gsd-review-backlog` |
| deferred_item | Phase 43/44 — 4 pre-existing `test_phase38_people_ui_contract.py` Node-subprocess path-concatenation failures (Windows/WSL path glued without separators) | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — VERIFIED FIXED: 23 passed / 0 failed with `node` on PATH; the mangled `C:\workspace\...` path came from the pre-relocation Windows checkout. Backlog 999.10 removed from ROADMAP.md. **Caveat:** these 4 tests SKIP (not fail) when `node` is absent from PATH, which is the default for pytest launched outside an nvm shell — a future regression there would be invisible |
| deferred_item | Phase 44 — full-suite invocation quirk (`pytest api/tests -q` skips the `tests/conftest.py` DB redirect since `tests/` is a sibling, not ancestor, path) | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — fully superseded, not just in spirit: Phase 46 moved `conftest.py` to the pytest rootdir so the redirect fires for every invocation shape, locked in by `tests/test_pytest_isolation_invocation_shapes.py` |

Cross-phase UAT audit — 2026-08-18 (`/gsd-audit-uat`):

Scanned all 18 UAT / VERIFICATION / deferred-items files across 15 phases (v1.0–v1.7) and
cross-referenced every item against current source plus two full test-suite runs. **72 outstanding
items → 14.** Every closure carries its evidence in the file it closes; the consolidated record is
`.planning/notes/2026-08-18-uat-audit-closure.md`.

- **60 of the 72 closed as stale** — 38 deferred-item bullets, 13 human-verification items, 6 UAT
  gaps, 1 UAT test block, 2 parser false positives. The bulk is ~35 "pre-existing DB-gated test
  failure" deferrals across Phases 25/26/28/29/31 that Phase 31's `TEST_DATABASE_URL` isolation and
  Phase 46's rootdir `conftest.py` relocation had already fixed without anyone closing the records.
  The rest: UAT gaps closed by later phases (Phase 44's Resolve rework, Phase 25's CR-01, the
  `published_at` gate, Phase 45's BUG-01/BUG-02); human-verification items whose `status` was never
  flipped after the closing work landed elsewhere; a stale `alembic current` assertion (head is now
  0026); and two phantom items from a commented-out bullet list in 25-UAT.md that still parses as
  `## Gaps` entries.

- **12 of the originals remain open**, all genuinely so: 6 facets of the one `delete_argument`
  cascade defect (folded into Phase 48), 4 live UAT items, and Phase 04's 2 never-run accessibility
  checks. The audit query now reports **14** because the audit added two tracking bullets to that
  `delete_argument` entry (the re-confirmation and the Phase 48 pointer).

- **3 findings recorded in no existing file.** Two were fixed during the audit:
  (N-1) 4 tests in `api/tests/test_phase44_argument_role_roundtrip.py` failed in full-suite order —
  `isinstance(body.side, SideEnum)` was False because `tests/test_admin_router.py::test_api_main_imports_without_error`
  purges and re-imports every `api.*` module mid-session, so the test's fresh `SideEnum` import was a
  different class object from the one `ResolveRowUpdate` was built with (same hazard Phase 31's
  T-31-19 documents for `ImportRun`); now resolved via `model_fields["side"].annotation`.
  (N-2) all 6 live tests in `api/tests/test_published_gate.py` were silently skipping for want of
  seed data, so Phase 45's BUG-01 integration evidence was not actually executing; they now seed and
  tear down their own published/unpublished rows. (N-3) the 4 `test_phase38_people_ui_contract.py`
  node tests skip rather than fail when `node` is off PATH — carried as a caveat above.

- **Test-suite baseline after the audit's fixes:** see the run recorded in the closure note.

## Performance Metrics

- v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12)
- v1.6: 11 phases, 51 plans, 17 days (2026-07-12 → 2026-07-29)
- v1.7: 6 phases, 29 plans, 18 days (2026-07-29 → 2026-08-15)
- v1.8: 5 phases (47–51), plans TBD — roadmap created 2026-08-17

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| — | — | — | — |
| Phase 48 P01 | 15min | 3 tasks | 7 files |
| Phase 48 P02 | 20min | 2 tasks | 3 files |
| Phase 48 P03 | ~35min | 2 tasks | 2 files |
| Phase 48 P04 | ~50min | 3 tasks | 13 files |
| Phase 48 P05 | ~50min | 3 tasks | 7 files |
| Phase 48 P06 | ~40min | 2 tasks | 3 files |
| Phase 48 P07 | ~45min | 3 tasks | 6 files |
| Phase 48 P08 | ~35min | 3 tasks | 3 files |
| Phase 48 P10 | ~2h across 3 sessions | 4 tasks | 18 files |
| Phase 49-review-model P01 | 45min | 2 tasks | 14 files |
| Phase 49-review-model P02 | 2h | 3 tasks | 20 files |
| Phase 49-review-model P03 | 25min | 3 tasks | 6 files |
| Phase 49-review-model P04 | 100min | 3 tasks | 15 files |
| Phase 49-review-model P05 | 50min | 3 tasks | 10 files |
| Phase 49-review-model P06 | ~100min | 3 tasks | 15 files |
| Phase 49 P07 | 45min | 2 tasks | 4 files |
| Phase 49-review-model P08 | ~55min | 3 tasks | 5 files |
| Phase 49 P09 | 1h 5m | 3 tasks | 6 files |
| Phase 49-review-model P12 | 70min | 4 tasks | 6 files |
| Phase 49 P11 | 70min | 3 tasks | 9 files |
| Phase 50 P01 | 70min | 4 tasks | 14 files |
| Phase 50 P02 | 55min | 2 tasks | 5 files |
| Phase 50 P03 | 100min | 3 tasks | 6 files |
| Phase 50-unified-import-path P04 | 45min | 2 tasks | 3 files |
| Phase 50 P05 | 195min | 3 tasks | 3 files |
| Phase 50 P06 | 130min | 3 tasks | 7 files |
| Phase 50 P07 | 70min | 3 tasks | 8 files |
| Phase 51 P02 | 65min | 4 tasks | 23 files |
| Phase 51 P03 | 50min | 3 tasks | 7 files |
| Phase 51 P04 | 80min | 3 tasks | 6 files |
| Phase 51 P05 | 45min | 3 tasks | 23 files |
| Phase 51 P06 | 46min | 3 tasks | 10 files |
| Phase 51 P07 | 45min | 3 tasks | 8 files |
| Phase 51 P08 | 66min | 3 tasks | 26 files |

v1.7 per-plan metrics cleared at this milestone boundary per the standard STATE.md reset; the underlying per-plan SUMMARY files remain in `.planning/milestones/v1.7-phases/`.

## Accumulated Context

### Decisions

Full cross-milestone decision log lives in PROJECT.md's Key Decisions table. Per-phase decisions for v1.7 (Phases 41–46) are archived in `.planning/milestones/v1.7-phases/*/`-SUMMARY.md and `.planning/milestones/v1.7-ROADMAP.md`; cleared here at milestone close per the standard STATE.md reset.

**Design basis for v1.8 (read before planning any phase):** `.planning/notes/import-architecture-diagnosis.md`, `provenance-and-trust-model.md`, `import-entity-sketch.md`.

**Carry-forward constraints that v1.8 planning must respect:**

- [Diagnosis → affects Phase 47]: This is a targeted re-model of the import/provenance layer, NOT a rewrite. The read model, people, tenures, and utterance display are stable and explicitly out of scope. Do not touch CASE, CASE_ARGUMENT, or the utterance/participant/person read shapes beyond the provenance/review fields the sketch calls out.
- [Provenance model → affects Phase 47/50]: `import_run` generalizes `pipeline_run`; the corpus path must STOP fabricating PDF-shaped `pipeline_run` artifacts. `pdf_path`/`pdf_url` are nullable and only populated for `source=pdf_pipeline`. Utterances FK to `import_run_id`, not `pipeline_run_id`.
- [Provenance model → affects Phase 48]: Every argument is born a `candidate` carrying a trust verdict; the gate is at promotion (`published_at`), NOT at row-creation. Status-based staging (candidate rows in `arguments`), NOT a separate staging table.
- [Trust model → affects Phase 48/49/50]: "Operator work is sacred" is the single most important invariant — a re-import never overwrites a human-confirmed or human-edited value. The authority ladder (operator > corpus > pdf/rule_based > pdf/llm_corrective) governs every writer; equal-or-higher-authority disagreement records a discrepancy rather than silently overwriting.
- [Trust model + apolitical constraint → affects Phase 48/49/51]: Trust tiers are operator-facing ONLY. Never surface trust/tier on the public site — it risks the apolitical framing hard constraint. Public sees published-or-not, nothing more.
- [Backfill → affects Phase 47]: Migration must preserve existing corpus + PDF data with zero loss; backfill provenance deterministically from today's `strategy` + `oyez_*` nullability per the documented old→new mapping. Alembic is the sole DDL authority — never `Base.metadata.create_all`.
- [CLAUDE.md → affects Phase 47/50]: Pipeline is offline-only (CLI, never HTTP endpoints). PG enum values can't be dropped — likely ADD `candidate` and stop using `pipeline` rather than rename.
- [Phase 29 → affects Phase 50]: The ConvoKit importer applies a positive apolitical allow-list, not a blocklist — partisan/outcome fields are dropped by design and SCDB data is never imported. Preserve this when corpus import moves to writing `import_run` directly.
- [Phase 29 CR-01 → affects Phase 50]: `question_number` is derived per-docket via `select(func.max(...))` against the real `(source_docket, question_number)` UNIQUE constraint. Any re-import/idempotency path must preserve that derivation, not hardcode `1`.
- [Phase 31 → affects every phase]: The test suite runs against `scotus_test` via `TEST_DATABASE_URL` with a rootdir `conftest.py` (Phase 46) that fails any run changing shared-dev-DB row counts. New DB-gated tests must respect this isolation.
- [Phase 44/RESOLVE-05 → affects Phase 49]: `name_needs_review`/`name_extraction_metadata` is the existing pattern REVIEW-05 must generalize into the unified `review_state` + provenance record — generalize it, do not build a parallel mechanism. Extracted-value hints use the shared `CopyableExtractedValue` component (stacked provenance mode from Phase 38).
- [Phase ?]: derive_tier rule 3 (operator+manual -> VERIFIED) is a flagged planner assumption pending operator confirmation at /gsd-verify-work
- [Phase ?]: Task 2 corrected the plan's erroneous third fail-closed test case to match derive_tier's actual, locked precedence semantics (unrecognised review_state alone does not override an otherwise-trusted source/method pair)
- [Phase ?]: Phase 48 Plan 02: cascade regression tests use try/finally cleanup so a failed assertion mid-test still leaves the shared scotus_test DB clean for the row-count tripwire
- [Phase ?]: Phase 48 Plan 02: kept test_delete_argument_returns_false_for_pipeline as the retired-enum-value fixture and added a distinct test_delete_argument_still_refuses_candidate rather than repurposing it
- [Phase ?]: Phase 48 Plan 03: left the admin-contract false-green guard failing loudly (not xfail) since it resolves automatically once 48-07 lands trust_tier on ArgumentDetail (D-20) -- recorded in WINDOWS.md as kind unmet-truth
- [Phase ?]: Phase 48 Plan 03: corrected the plan's /api/-prefixed endpoint paths to the actual mounted public routes (/cases, /arguments/{id}/..., /people/{id}) -- only the admin router carries an /api/admin prefix
- [Phase ?]: Phase 48 Plan 04: Rule 3 fix flipped pipeline/commands/import_convokit.py's birth-write status kwarg from PIPELINE to CANDIDATE ahead of plan 48-05's own scheduled edit, to keep this plan's guard swap internally consistent; recorded in WINDOWS.md (kind=deviation) so 48-05 finds this line already done
- [Phase ?]: Phase 48 Plan 04: renamed test_approve_job_accepts_freshly_created_argument_and_rejects_second_call to include 'candidate' so the plan's own -k filter matches all three vocabulary-block tests it names
- [Phase ?]: Phase 48 Plan 05: import_convokit.py's birth-write status kwarg was already flipped to CANDIDATE by plan 48-04's Rule 3 fix; confirmed already-done and WINDOWS.md entry 7 marked fixed
- [Phase ?]: Phase 48 Plan 05: fixed a stale test assumption in api/tests/test_admin_dev_routes.py (test_reset_writes_status_log_rows) that asserted zero status-log rows for candidate arguments -- D-03's birth-log write now produces exactly one row for those arguments, as CONTEXT.md predicted
- [Phase ?]: Phase 48 Plan 06: test file bootstraps AsyncSessionLocal via a module-local FastAPI-lifespan fixture (mirroring api/tests/conftest.py::_api_lifespan) to reuse plan 48-01's _seed_argument/_teardown_argument helper unmodified
- [Phase ?]: Phase 48 Plan 06: added a function-scoped, genuinely committed TRUNCATE fixture (mirroring pipeline/tests/conftest.py's _reset_test_db safety guard) since clean_db's rollback-based truncation is invisible to recompute-trust's separate pipeline.db.get_session() engine
- [Phase ?]: Phase 48 Plan 07: adapted 3 pre-existing zero-constituent publish tests in test_admin_arguments_service.py to pass an override_reason since floor_tier's zero-constituent base case now hits the new UNCERTAIN gate by construction
- [Phase ?]: Phase 48 Plan 07: blank-reason and pre-existing publish ValueErrors share one except ValueError router handler distinguished by inspecting str(exc), since Python cannot dispatch two handlers on the same exception class
- [Phase ?]: Phase 48 Plan 08: reused the static-source-contract shape (test_phase45_popover_boxmodel_contract.py / test_phase39_popover_ui_contract.py) for the publish-override UI contract, since this repo has no frontend test framework and node is not guaranteed on PATH for every pytest invocation
- [Phase ?]: Phase 48 Plan 10: found and fixed a real defect at the Task 4 checkpoint — the detail page's Status card never rendered publish/unpublish errors (form?.error only rendered in the unrelated case-metadata card); tagged fail() payloads with source and widened the Status-card guard
- [Phase ?]: Phase 48 Plan 10: unpublish-error rendering fix accepted on static contract test alone, not observed live (failure path requires the backend call itself to fail, unreachable from any UI state)
- [Phase ?]: Phase 48 Plan 10: WINDOWS.md entry #8 (D-14 non-overridable gate, unrun-verify) marked fixed -- the deferred live check is what surfaced the checkpoint-found defect, not a false alarm
- [Phase ?]: Phase 48 Plan 09: found and fixed a Status History display-ordering bug via live evidence-gathering -- get_argument_detail's argument_status_log query now orders by id ASC only, not created_at first, since PostgreSQL now() reflects transaction-start time not per-statement time
- [Phase ?]: Phase 48 Plan 09: derive_tier rule 3 (operator+manual -> VERIFIED) confirmed by the operator on 2026-08-21, closing plan 48-01's flagged assumption; api/domain/trust.py docstrings updated to record confirmation, logic unchanged
- [Phase ?]: Phase 48 Plan 09: two corpus fixtures (15169, 22372) read trust_tier=uncertain not trusted after reseed -- traced to ConvoKit's own unattributed-speaker sentinel rows, not a Phase 48 defect; derive_tier is correct and the plan's must-have assumption was wrong. Accepted by operator as an open item
- [Phase ?]: Phase 48 Plan 09: operator requested widening Resolve-card editability from CANDIDATE-only to {candidate, draft, unpublished} (published stays read-only) -- recorded as a new open item and standalone todo, deliberately NOT implemented (design-scope change, not a bug)
- [Phase 49]: 49-02 checkpoint decision (human, resolved): migration 0029's downgrade() is clean-reverse — reconstructs no data from review_state/provenance_metadata, matching migration 0027's precedent.
- [Phase 49]: 49-02: fixed a pre-existing 49-01 regression (import_convokit.py ArgumentParticipant rows never stamped source/method, flooring trust tier to UNCERTAIN under D-18) — in scope, implements D-20's locked mapping. A second, analogous regression in admin_jobs.py/resolve_job was left open and documented (deferred-items.md, WINDOWS.md #11) since D-20 has no locked mapping for that path and fixing it requires a new architectural decision.
- [Phase 49]: 49-03: Status-card label fix took option 1 (relabel to 'Resolved', no schema change) per the plan's pre-made decision.
- [Phase 49]: 49-03: review_state badge on the new /admin/help page sized like the 14px status badge (not the 12px passive tier badge), since review_state is a primary operator-actionable axis per the UI-SPEC screen contract -- this page's own presentational choice, not binding on plan 49-05's real queue screen.
- [Phase 49]: 49-03: could not complete the plan's live-browser human-check walkthroughs (Task 1 popover, Task 3 Help page) -- authenticating to /admin/** requires ADMIN_USERNAME/ADMIN_PASSWORD or SESSION_SECRET from .env, and this sandbox's permission policy denied reading .env. Recorded as human_judgment:true in 49-03-SUMMARY.md coverage; a human should complete both walkthroughs before UAT sign-off.
- [Phase 49]: 49-04: D-18 provenance-gap fix backfills source/method from the job's parse-step ImportRun (corpus/direct), not by routing incoming writes as operator/manual authority as the environment note's prose suggested — verified against derive_tier's actual rule table (only rule 4 reaches TRUSTED, which both failing tests assert).
- [Phase 49]: 49-04: participant editability widened from CANDIDATE-only to every unpublished state (candidate/draft/unpublished); only PUBLISHED stays read-only. Backend/API complete; frontend readonlyMode flag deliberately not widened (conflates two different editability concerns) — left for 49-05.
- [Phase 49]: 49-06: 49-RESEARCH.md Pitfall 4's premise ("no live corpus path can produce an unresolved speaker") is false — verified against the live dev DB before this plan started. The dev-only seeder was built anyway, justified by its own standalone value (a deterministic, repeatable fixture), not by the false claim.
- [Phase 49]: 49-06: the seeder prefers a participant whose side is already UNKNOWN (traced against list_argument_speakers/ChatBubble.svelte's real source) over the plan's literal "first non-BENCH participant" pick, and also nulls the matching Utterance rows — both required to actually reproduce 26-UAT Test 26 and 14-UAT Test 8's states, not just an unresolved-participant row.
- [Phase 49]: 49-06: found and fixed a real gap during D-32's own live walkthrough — _argument_attention_predicate had no leg for "a constituent has an open discrepancy" (the People-tab predicate already did), so the review queue never surfaced exactly the scenario REVIEW-02/REVIEW-04 exist to prove. Fixed same-plan.
- [Phase 49]: 49-06: readonlyMode split into resolveCardReadonly (status===published) / metadataReadonly (unchanged) — closes the item 49-04/49-05 both flagged and deferred.
- [Phase 49]: 49-06: discovered TEST_DATABASE_URL and DATABASE_URL resolve to the same physical Postgres database in this sandbox — running a full-suite pytest run and a direct dev-DB verification script concurrently produced 2 spurious DeadlockDetectedError failures (confirmed as an artifact, not a regression, by re-running in isolation). Future work in this sandbox should not run both at once.
- [Phase 49]: 49-07: rename stopped at operator-facing copy; no_constituents/ReviewQueueConstituent/constituents field left unchanged (wire code + D-34 security guard)
- [Phase 49]: 49-08: closed G-49-5a's three horizontal-overflow causes (two queue tables + the previously-undiagnosed status segment group) with overflow-x: auto containers and a repeat(auto-fit, minmax(120px, 1fr)) grid track floor; the 120px floor resolves the UAT sub-item 5 vs 7 conflict without trading one for the other, proven by an executable _tracks_that_fit arithmetic gate. Structural closure only — browser visual re-confirmation remains blocked by the same denied .env credential access as 49-01/49-03/49-05.
- [Phase 49]: 49-09: published-status guard on update_participant_side placed after the pre-existing BENCH/unresolved-side input checks (not literally first), to keep a sentinel-session unit test's no-DB-touch contract intact — still runs before the participant SELECT and both authority-gate calls, satisfying D-16's no-residue requirement.
- [Phase 49]: 49-09: two new contract assertions (test_update_participant_side_still_accepts_unpublished_and_draft, test_popover_does_not_resync_side_on_every_prop_change) were green from the start of the RED phase — documented as negative-space/continuity checks, not presented as red-then-green.
- [Phase 49]: D-35 (second half): T-15-02-BENCH retired as satisfied (not weakened) — Speakers card and Resolve card converged onto one shared side/bucket module, closing G-49-3
- [Phase 49]: 49-12: closed G-49-5c (last open Phase 49 gap) — AdminSubNav/TopNav gained flex-wrap:wrap; a computed page-chrome sweep replaces hand-enumerated regression gates and found TopNav as a second zero-slack near-miss unprompted; a re-runnable narrow-viewport-audit.mjs operator tool shipped per D-49-12-c. Two new out-of-scope table-overflow findings on /admin/arguments and /admin/people recorded (WINDOWS.md #26/#27), not fixed.
- [Phase 49]: 49-11: the two pre-existing published guards cite the folded-todo slug in their raised text; the four new guards cite 'D-35/D-35a, operator, 2026-08-24' instead (same structural shape, same 'is published (current status:' clause) since the folded todo is participant-editability-specific
- [Phase 49]: 49-11: create_person_for_job's published guard only fires when the job resolves to an actual PUBLISHED Argument — a job with no linked argument still legitimately creates a bare Person, which is Person-only territory outside D-35a's scope
- [Phase 49]: 49-11: the page-level lock statement and Case card reuse 49-09's speakersLocked flag verbatim rather than renaming it, even though its scope now covers the whole page
- [Phase 50]: 50-01 Task 0 checkpoint: froze the D-13 content-digest contract as freeze-as-proposed (sha256, JSON-framed 4-field tuple, byte-exact, person_id/side/section_hint excluded). — One-way door per D-13 — must be frozen before any digest is stored in the DB.
- [Phase 50]: 50-01: _incoming_utterance_rows is a single shared, DB-write-free helper used by both the first-import write path and the reconcile no-op digest comparison. — Guarantees the digest can never disagree with the rows actually written, and lets the reconcile branch prove zero DB writes for D-09's byte-identical guarantee.
- [Phase 50]: PD-13 gap-fill pre-check on the two EXISTING gates (apply_participant_value_change/apply_person_value_change) is scoped to rows whose existing authority has not already reached OPERATOR — The plan's literal unconditional text would have reopened the Phase 49 CR-02/CR-04 defect where a re-import could silently overwrite a participant an operator explicitly confirmed as unattributable; the two NEW gates (Argument/Case) apply PD-13 unconditionally since those tables have no review_state and no analogous risk
- [Phase 50]: 50-03: found and fixed a real FK-orphaning gap in delete_argument's own D-26 cascade during test-writing — a surviving value_discrepancy row (target_type=person, or another argument's participant) can reference an ImportRun belonging to the argument being deleted; NULLing import_run_id on survivors before deleting ImportRun rows (mirroring the existing AdminJob.argument_id pattern) closes it.
- [Phase 50]: 50-03: update_argument_metadata deliberately does NOT stamp operator provenance when it writes argued_date — only question_number/source_docket trigger _stamp_operator_provenance there, matching the plan's own action text and its call-site count acceptance criterion (1 definition + exactly 3 call sites).
- [Phase 50]: 50-04: The Approve form action was placed OUTSIDE the {#each item.constituents} loop, not inside the per-constituent action row the plan's read_first pointer named -- a literal per-constituent placement would either duplicate the button once per flagged constituent, or never render at all for a CANDIDATE argument queued solely via a degraded-tier or argument/case-discrepancy leg with zero flagged constituents, which is the primary use case D-14 exists to unblock.
- [Phase 50]: 50-04: The local ReviewQueueArgumentItem TypeScript type Task 1 asked to extend lives in +page.server.ts, not in +page.svelte's module script (the .svelte file declares no local types; it infers PageData). Edited +page.server.ts instead.
- [Phase 50]: Plan 50-05: the D-06 lazy-reconcile-run predictor imports admin_review's own _values_differ/_is_gap_fill/_normalize_generic directly rather than re-implementing them, so it can never diverge from the gate's own write/record decision (PD-15).
- [Phase 50]: Plan 50-05: Argument/Case first-import creation now stamps source=corpus/method=direct (matching ArgumentParticipant/ImportRun) -- a Rule 2 fix required for D-07's restamp to not itself break D-09's byte-identical re-import guarantee.
- [Phase 50]: resolve.py/parse.py/import_justices_csv.py delegate every gated-column write to api.services.admin_review's authority gates (D-22 delegation sweep closed); SC-4 closed by an 8-test real-writer behavioral gate (test_gated_column_writers.py), not a source-text grep.
- [Phase 50]: parse.py's source_docket write and import_convokit's name-provenance prefill are structurally gap-fill-only by design (a source-inspection test and a has_any_part guard respectively) -- their D-24 tests prove gap-fill correctness, not REJECT_AND_RECORD, and this is documented rather than silently narrowed.
- [Phase 50]: 50-07: prune-runs' --dry-run path issues zero writes (never "write then roll back") -- an initial defensive session.rollback() under --dry-run was destroying isolated_session-based tests' own uncommitted seed data, since (unlike recompute-trust, whose rollback is load-bearing) this module's dry-run branch structurally never writes; removed once traced.
- [Phase 50]: 50-07: content_digest/oyez_speaker_id are banned from public schemas in test_trust_public_leak_ban.py even though no schema (admin included) exposes either yet -- the usual false-green admin-schema-carries-it guard is documented as honestly unsatisfiable for these two keys, proven instead at the ORM layer, rather than fabricating an admin exposure this plan had no mandate to add.
- [Phase 50]: 50-07: found (not fixed) a third ungated writer pair during the D-24 inventory build -- parse.py's _update_participant_sides/_update_participant_descriptors write ArgumentParticipant.side/.descriptor by direct assignment on every parse pass with no gate call, risking a re-parse silently overwriting an operator's own reassignment. Neither D-22's enumeration nor 50-06's parse.py conversion named it. Logged as a new deferred-items.md item (parse.py not in 50-07's files_modified); candidate for a small follow-up plan mirroring resolve.py's 50-06 conversion.
- [Phase 50]: Phase 50 (Unified Import Path) is COMPLETE as of plan 50-07 -- all four in-scope requirements (IMPORT-01, IMPORT-03, IMPORT-04, IMPORT-05) satisfied. Two phase-gate human items remain open in WINDOWS.md (#30: 50-04's browser walkthrough; #31: 50-05's D-09 live double-import + operator-edit-survival walkthrough) -- neither closed by any plan in this phase; both need a human with `.env` admin credential access.
- [Phase 50]: Phase 50 complete: prune-runs (D-12), extended leak ban, /admin/pipeline PDF-only narrowing (D-19), D-24 writer inventory, D-23 closed. — Plan 50-07 was the phase's final plan; all four requirements (IMPORT-01/03/04/05) now satisfied.
- [Phase 51]: Checkpoints 1/2 resolved from already-locked 51-CONTEXT.md decisions (D-10/D-11/D-12/D-13), not re-prompted — CLAUDE.md Defect Policy: a locked decision in a phase CONTEXT.md is Claude's to act on, not re-ask
- [Phase 51]: question_number chosen over argued_date as the Argument.slug collision-suffix discriminator — Verified against the real ~7,800-row corpus: argued_date collides or is null in 45.6% of the 952 multi-argument cases; question_number is always populated and unique-by-construction
- [Phase 51]: 10 of 24 hex values found in app/src recorded as open rows in 51-TOKEN-MAP.md rather than mapped to a token — No match in the Figma-sourced 14-primitive palette; plan explicitly forbids inventing a token for an unmapped value
- [Phase 51]: color-text-advocate token dropped rather than aliased (zero live var() call sites confirmed via grep) — Existing components hardcode 93c5fd/94a3b8 hex literals directly rather than reading the CSS variable, so removing it left nothing referenced-but-undefined
- [Phase 51]: Phase 51 plan 51-04: term-grouped public API (GET /arguments/terms, GET /arguments/term/{term_year}) shipped per D-14/D-15/D-16 Variant A (minimal row, no advocate join). Leak-ban and published-gate contracts extended and proven non-vacuous live. Full suite 1378 passed, 5 xfailed, 0 failed.
- [Phase 51]: Substituted @lucide/svelte for the deprecated lucide-svelte D-18 named (operator-approved) — Package-legitimacy gate found lucide-svelte deprecated in favor of the actively-maintained scoped successor, same maintainer/repo
- [Phase 51]: Button's icon-only accessible-name contract enforced by a TypeScript discriminated union, not a runtime check — Plan required the omission to be impossible to construct; a compile error satisfies that more strongly than a runtime assertion
- [Phase 51]: D-19 Style B2 transcript redesign shipped: run grouping via $derived.by before layout, one sticky outside-rail avatar per run (position:sticky;bottom, flex-column justify-content:flex-end), 6/2px corner-rounding table on ChatBubble's new position prop. — Closes DS-02's reading-layer half; the folded IN-02/IN-03 duplication todo closed in the same plan (shared file, shared scope).
- [Phase 51]: Bio clamp+expand (Phase 45 BUG-02's -webkit-line-clamp) removed from SpeakerPopover.svelte — P-06 bans truncating popover content; bio now always renders in full. — Auto-fixed under Defect Policy Rule 2 (missing critical constraint compliance), found while sweeping lib/public/ for the plan's own hard prohibition.
- [Phase 51]: Added app/src/routes/arguments/+error.svelte (Rule 2) so the Copywriting Contract's error string renders with no leaked HTTP status number — SvelteKit's built-in fallback error page renders the raw status code, which the plan's error-state contract forbids
- [Phase 51]: Renamed api/tests/test_case_item_argued_date_optional.py to test_argument_list_item_argued_date_optional.py — Plan instruction: rename a retargeted test whose name still says CaseItem once its assertions moved onto ArgumentListItem

### Roadmap Evolution

v1.6's roadmap evolution is archived in `.planning/milestones/v1.6-ROADMAP.md`; v1.7's in `.planning/milestones/v1.7-ROADMAP.md`. Cleared here at each milestone close.

2026-08-17: v1.8 roadmap created — Phases 47–51 derived from the milestone's 25 requirements (PROV-01–06, TRUST-01–05, REVIEW-01–05, IMPORT-01–05, DS-01–04). Numbering continues from v1.7's last phase (46). Coverage 25/25, no orphans, no duplicates — the five requirement categories map 1:1 onto five dependency-ordered phases (granularity `standard`, 5 phases sits in the 4–6 band; each phase carries 4–6 requirements of real scope, so no folding was warranted). Sequencing is load-bearing: PROV (47) is the keystone everything depends on and must come first; TRUST (48) depends on provenance existing; REVIEW (49) depends on trust + provenance; IMPORT (50) depends on the new schema + review model being in place; DS (51) is deliberately last so the UI reflects the corrected domain language, and it absorbs backlog 999.4/999.6/999.8. UI hints flagged on Phase 49 (new operator review queue screen) and Phase 51 (design system / component library / listing). Out of scope confirmed in REQUIREMENTS.md: public trust display, a literal separate staging table, the White/Black/Clark/Douglas person-dedup mismatch (deferred from v1.7 Phase 42), and deployment (DEPLOY-01/03).

### Pending Todos

- `2026-08-12-speakers-bench-classification-silent-fallback.md` (api, low) — unassigned, from Phase 45 code review.
- `2026-08-12-speaker-popover-frontend-duplication-cleanup.md` (ui, low) — unassigned, from Phase 45 code review.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (dev-environment, low) — revisit after the relocated repo has run without incident for a period.
- `2026-08-18-pdf-provenance-live-fixture-verification.md` (pipeline, minor) — from Phase 47's SC-4 operator override. The `pdf_pipeline/rule_based` and `pdf_pipeline/llm_corrective` provenance legs are proven by pytest against `TEST_DATABASE_URL`, but not by a live `reset_to_fixture` re-seed, because no PDF fixture exists in the repo. Deliberately deferred with the PDF route per the corpus-first scope decision; pick up when the PDF upload path comes back (Phase 50 or later). *Was missing from this list — added 2026-08-18 during the UAT audit's pre-Phase-48 sweep, found via `gsd-tools audit-open`.*

### Blockers/Concerns

**Directly relevant to v1.8:**

- **[FOLDED INTO PHASE 48 — 2026-08-18]** `api/services/admin_arguments.py::delete_argument` still omits `argument_status_log` from its FK cascade (found during Phase 31, re-confirmed by reading current source during the 2026-08-18 UAT audit). The cascade runs Utterance → ImportRun → ArgumentParticipant → CaseArgument → NULL `AdminJob.argument_id` → Argument with no `ArgumentStatusLog` step; that FK has no `ondelete` (`api/models/models.py:507`) and `approve_job` writes an `ArgumentStatusLog(DRAFT)` row for every argument it creates (`api/services/admin_jobs.py:591`), so the Danger Zone delete on an approve-created DRAFT should raise `ForeignKeyViolation`. Still static analysis — no live repro yet. Now carried as explicit Phase 48 scope (see ROADMAP.md Phase 48, "Carried defect folded in 2026-08-18"), including correcting the wrong comment at `scripts/delete_fixture_argument.py:25`. Phases 47/50's re-import and idempotency paths depend on this cascade being correct.
- **[affects Phase 47]** Run `alembic current` before assuming a migration needs applying — the dev DB was believed to be at head `0024`/`0025` (v1.7 added migration 0025 for the descriptor rename). Confirm the real head first; Alembic is the sole DDL authority for the new `import_run` schema.
- **[affects Phase 48/49]** `argument_status` is a PG enum and PG cannot drop enum values — adding `candidate` and ceasing use of `pipeline` is the likely path (per `import-entity-sketch.md` open items), not a rename. Decide `import_run` per-argument vs. a separate `import_batch` grouping at Phase 47 plan time (leaning per-argument to preserve the Utterance FK).

**Accepted risk from the 2026-08-18 human-UAT waiver:**

- **[affects Phase 51]** Phase 04's accessibility compliance is asserted, not measured. No assistive
  technology walkthrough and no axe-core/WAVE scan has ever been run against the argument view; the
  ARIA markup and contrast tokens were only ever checked by reading source. Waived by operator on
  2026-08-18 via `04-VERIFICATION.md`'s `overrides` block. Phases 14, 38, 39 and 45 have all changed
  the popover and argument view since, so the covered surface has drifted from the verified one. The
  cheap permanent fix is an axe-core assertion inside a browser test rather than a human checklist —
  worth folding into Phase 51 when it reworks this UI.

- **[affects Phase 49/50]** Three UAT behaviours are implemented but have never been observed:
  the failed-run error panel (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder
  and per-row Save gate on the argument editor, and the non-interactive avatar for an unresolved
  utterance. Each is a plausible free rider on Phase 49's review work or Phase 50's import rework.

**Deployment blockers (v1.4, unresolved — explicitly out of v1.8 scope, carried to a later milestone):**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1 (PROJECT.md Key Decisions, ⚠️ Revisit):**

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence, flip the source debug session's / verification's `status` field in that same commit. v1.6 lost a phase slot (40.1) to a stale `diagnosed` status; no structural fix shipped.
- api/tests/test_admin_jobs_service.py's 2 failing tests (resolve_job/update_resolve_row_for_job never stamp ArgumentParticipant.source/method) — **RESOLVED by plan 49-04** (WINDOWS.md entry 11, status `fixed`).
- **All eight outstanding live-browser human-check items across Phase 49 (49-01, 49-03, 49-05, 49-06) are consolidated into one ordered list in `.planning/phases/49-review-model/49-EVIDENCE.md` §9** — every underlying data/API layer has been verified by script; only the actual on-screen render is unconfirmed, blocked on this sandbox denying `.env` read access for admin credentials. Each item is also recorded in `.planning/WINDOWS.md` (kind `unrun-verify`).

### Milestone-close queue (not Phase 48 blockers)

`gsd-tools audit-open` reported 6 items needing a decision before v1.8 closes as of Phase 48
close; 49-03 closed one of them (the create-person-popover todo). 5 remain: the 4 pending todos
above and the dormant SEED-001. None of them blocks Phase 49 — they are `/gsd-review-backlog` and
`/gsd-audit-milestone` material. Recorded here so the distinction is explicit rather than rediscovered
at close.

## Session Continuity

Last session: 2026-08-28T19:24:49.154Z
Stopped at: Completed 51-08-PLAN.md
Resume file: None

## Operator Next Steps

- **Phase 50 (Unified Import Path) is complete — all 7 plans, all 4 waves.** Run `/gsd-verify-work 50` to verify the phase goal, then `/gsd-discuss-phase 51` to start Phase 51 (the last v1.8 phase, design system work).
- **New deferred item from 50-07:** `pipeline/commands/parse.py`'s `_update_participant_sides`/`_update_participant_descriptors` write `ArgumentParticipant.side`/`.descriptor` ungated on every parse pass — a real risk of a re-parse silently overwriting an operator's own reassignment. See `deferred-items.md`'s "D-24 writer inventory (50-07)" section. Candidate for a small follow-up plan.
- **Phase 49 (Review Model) is complete, including all four gap-closure plans (49-09 through 49-12).** All five REVIEW-0X requirements are `Complete`. Run `/gsd-verify-work 49` to re-close the phase against the reopened gaps.
- **Recommended single-sitting browser pass** (see `49-EVIDENCE.md` §9 for the pre-49-11 order, plus the 5 new 49-11 Task 3 items in `49-11-SUMMARY.md`'s Human-Check Items section — WINDOWS.md entry 28): open `/admin`, click Reset to Fixture then Seed unresolved speaker; open the Complexity fixture's argument edit page (26-UAT Test 26); open `/admin/review` (49-01/49-05's items, D-32's visual rendering); exercise `CreatePersonPopover`/`/admin/help` (49-03's items); on `/admin/arguments/{id}` for a PUBLISHED argument, confirm the page-level lock statement, the Case card and Argument Details card render disabled, and Publish/Unpublish/Delete still work; optionally publish the Complexity fixture to check 14-UAT Test 8's public-page rendering.
- **Operator question from 49-11 (D-35a) — ANSWERED, closed 2026-08-25 (D-23, 50-CONTEXT.md):** no `Person`-level published lock. Zero implementation; see `deferred-items.md`'s Person-scoped section (status flipped to closed in the same commit as `50-07`'s writer inventory, per the Phase 40.1 lesson).
- One standalone todo remains open from Phase 48: `2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` — candidate for a future plan or `/gsd-review-backlog`. (`2026-08-21-widen-participant-editability-to-all-unpublished-states.md` is now closed — see `.planning/todos/completed/`.)
- When ready, begin Phase 50 (Import Unification) with `/gsd-discuss-phase 50`.
