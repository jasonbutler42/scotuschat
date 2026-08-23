---
phase: 49-review-model
plan: 06
subsystem: review-model
tags: [fastapi, sqlalchemy, sveltekit, svelte5, dev-tools, authority-ladder, review-queue]

requires:
  - phase: 49-review-model plan 01
    provides: "the /admin/review tracer, review_state enum, admin_job_id deep-link routing"
  - phase: 49-review-model plan 04
    provides: "the authority ladder (api/domain/authority.py), the ONE gated writer, the full confirm/confirm_unattributable/reflag action set"
  - phase: 49-review-model plan 05
    provides: "the full /admin/review queue screen (filters, sort, dashboard COUNT, tabs, expand/collapse) this plan's D-32 walkthrough exercises"

provides:
  - "api/services/admin_dev.py::seed_unresolved_speaker_fixture — dev-only, idempotent, nulls one deterministically-selected participant's person_id (preferring an already-UNKNOWN-side row) plus its matching Utterance rows, recomputes the argument's trust tier"
  - "POST /api/admin/dev/seed-unresolved-speaker — mounted only when settings.environment == development, no request surface"
  - "Dev Tools 'Seed unresolved speaker' control on /admin — secondary/muted treatment, single-step, no confirm gate"
  - "26-UAT Test 26 and 14-UAT Test 8 reclassified waived -> blocked with dated, script-verified observations (not a pass — visual confirmation still needs a human)"
  - "api/services/admin_review.py: _argument_attention_predicate gains a fourth leg (open participant discrepancy) — a real, phase-central gap found and fixed during this plan's own D-32 walkthrough"
  - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts: readonlyMode split into resolveCardReadonly/metadataReadonly, closing the item 49-04/49-05 both flagged and deferred"
  - ".planning/phases/49-review-model/49-EVIDENCE.md — requirement/threat traceability, the D-32 walkthrough transcript, and the corrected Pitfall 4 premise"

affects: [50-import-unification]

actuals:
  tokens: 62000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "A dev-only fixture seeder must select its target row by tracing the ACTUAL downstream consumers (list_argument_speakers' side passthrough, ChatBubble's person_id gate) rather than by the plan's literal 'first non-BENCH participant' text — the two disagreed here, and only the traced version reproduces the UAT states the seeder exists to close"
    - "_argument_attention_predicate / _person_attention_predicate must stay symmetric — an inclusion leg added to one side's predicate (discrepancy-open) but not the other is a silent queue gap, not a stylistic asymmetry"

key-files:
  created:
    - api/tests/test_admin_dev_unresolved_fixture.py
    - .planning/phases/49-review-model/49-EVIDENCE.md
  modified:
    - api/services/admin_dev.py
    - api/routers/admin_dev.py
    - api/schemas/admin_dev.py
    - api/services/admin_review.py
    - api/tests/test_admin_review_service.py
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - .planning/milestones/v1.5-phases/26-arguments-admin/26-UAT.md
    - .planning/milestones/v1.2-phases/14-speaker-popover-card/14-UAT.md
    - .planning/todos/completed/2026-08-21-widen-participant-editability-to-all-unpublished-states.md
    - .planning/WINDOWS.md

key-decisions:
  - "The seeder's justification is its own standalone value (a deterministic, repeatable fixture for D-32/D-33's walkthroughs), NOT 49-RESEARCH.md Pitfall 4's claim ('no live corpus path can produce an unresolved speaker') — verified false against the live dev DB before this plan started (argument 1788 had 11 person_id-IS-NULL rows from a job parked pre-resolve). Not restated anywhere in this plan's code, docstrings, or this SUMMARY."
  - "The seeder prefers a participant whose side is ALREADY SideEnum.UNKNOWN over the plan's literal 'first non-BENCH participant ordered by id' pick — traced against list_argument_speakers/ChatBubble.svelte's actual source, the literal pick would have selected a resolved-side (PETITIONER) row and left 26-UAT Test 26's placeholder unreachable."
  - "The seeder also nulls the matching Utterance rows (scoped by raw_speaker_label), not just the ArgumentParticipant row — Utterance.person_id is an independent column the public chat page reads directly (api/services/arguments.py), so nulling only the participant would have left 14-UAT Test 8 unreachable too."
  - "readonlyMode split into metadataReadonly (unchanged, status != candidate) and resolveCardReadonly (status === published, matching 49-04's already-widened backend guard) rather than widening both — update_argument_metadata has no status guard of its own and nothing in this plan's scope asked that concern to change."
  - "_argument_attention_predicate gained a fourth leg (open participant discrepancy) rather than leaving the gap documented-not-fixed — this is REVIEW-02/REVIEW-04's central claim (an operator edit surviving a lower-authority disagreement, visibly, in the queue), found live during this plan's own D-32 walkthrough, and the fix mirrors an already-established pattern (_person_attention_predicate's own discrepancy leg) rather than inventing one."
  - "26-UAT Test 26 and 14-UAT Test 8 reclassified from waived to blocked, not to pass — the underlying data-layer blocker is resolved and script-verified live, but the literal on-screen observation neither test's own wording can be satisfied without has NOT been made (credential-access denial, consistent with 49-01/49-03/49-05)."

patterns-established:
  - "A live full-suite pytest run and a direct verification script must never touch the database at the same time in this sandbox — TEST_DATABASE_URL and DATABASE_URL resolve to the same physical database here (both hit Postgres OID 17111), so 'isolated by design' database-name separation the codebase's own comments assume does NOT hold in this environment. Running both concurrently produced two spurious DeadlockDetectedError failures this session, confirmed as an artifact (not a regression) by re-running in isolation."

requirements-completed: [REVIEW-02, REVIEW-03, REVIEW-04]

coverage:
  - id: D1
    description: "seed_unresolved_speaker_fixture produces a NULL-person_id ArgumentParticipant row on the real Complexity fixture, idempotently, with the trust tier recomputed, and the endpoint is genuinely absent (404, not 403) outside development"
    requirement: "REVIEW-02"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_unresolved_fixture.py#test_seeder_nulls_person_id_of_one_advocate_participant_and_flags_needs_review"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_unresolved_fixture.py#test_seeder_called_twice_is_idempotent_no_second_row_touched"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_dev_unresolved_fixture.py#test_seed_unresolved_speaker_route_absent_outside_development"
        status: pass
      - kind: other
        ref: "49-EVIDENCE.md §2b — live run against the real dev DB (not a synthetic fixture): argument 1793, participant 3586 (Lloyd N. Cutler)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The seeder reproduces the EXACT states 26-UAT Test 26 (side=UNKNOWN) and 14-UAT Test 8 (Utterance.person_id IS NULL) need — not just an unresolved participant row"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_unresolved_fixture.py#test_seeder_also_nulls_matching_utterances_scoped_by_raw_speaker_label"
        status: pass
      - kind: other
        ref: "49-EVIDENCE.md §2b/§2c — live query confirms participant.side==UNKNOWN and all 5 matching Utterance rows read person_id=NULL on the real dev DB"
        status: pass
    human_judgment: false
  - id: D3
    description: "26-UAT Test 26 and 14-UAT Test 8's underlying blocking states are resolved and script-verified; neither is marked pass (the literal on-screen observation each requires was not made — credential-access denial)"
    verification: []
    human_judgment: true
    rationale: "This sandbox's permission policy denies reading .env (ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET), so no authenticated /admin/** or public-site browser session was reachable — consistent with 49-01/49-03/49-05's identical gap. A human must open the Speakers card and the public chat page and flip each UAT test's own result field based on what they see; 49-EVIDENCE.md §3/§9 give the exact, minimal remaining steps."
  - id: D4
    description: "D-32's live authority-conflict walkthrough performed end to end via a repeatable script against the real dev DB: operator edit survives a lower-authority re-import's disagreement, the discrepancy is visible with both values and provenance, reflag closes it, the tier reflects a fresh (correct) recompute"
    requirement: "REVIEW-04"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_discrepancy_alone_includes_argument_and_lists_constituent"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_argument_no_longer_listed_once_its_only_discrepancy_closes"
        status: pass
      - kind: other
        ref: "49-EVIDENCE.md §5 — full script + verbatim transcript against the live dev DB"
        status: pass
    human_judgment: true
    rationale: "The mechanism (value survival, discrepancy recording, queue inclusion, resolve/close) is fully verified at the data and API layer, including finding and fixing a real gap (D5 below). The actual browser rendering of the Discrepancy badge (color, placement, click behavior) was never observed — same credential-access denial as D3."
  - id: D5
    description: "_argument_attention_predicate gains a fourth leg (open participant discrepancy) — before this fix, an operator-edited, already-resolved participant with an open discrepancy (exactly D-32's own scenario) was invisible in the review queue, satisfying none of the original three legs"
    requirement: "REVIEW-04"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_discrepancy_alone_includes_argument_and_lists_constituent"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_argument_no_longer_listed_once_its_only_discrepancy_closes"
        status: pass
      - kind: other
        ref: "49-EVIDENCE.md §5c — before/after transcript of the same D-32 script, proving the fix"
        status: pass
    human_judgment: false
  - id: D6
    description: "readonlyMode split into resolveCardReadonly (status===published, matching 49-04's widened backend guard) and metadataReadonly (unchanged) — closes the item 49-04 and 49-05 both flagged and deferred"
    requirement: "REVIEW-04"
    verification:
      - kind: other
        ref: "npm --prefix app run check -> 0 errors, 37 warnings (unchanged baseline)"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase44_resolve_table_contract.py -q -> 111 passed (unaffected)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full suite green, no new skips, versus the 1403-test baseline this plan inherited from 49-05"
    verification:
      - kind: other
        ref: "./.venv/bin/python -m pytest (isolated run) -> 1414 passed, 5 xfailed, 0 failed"
        status: pass
      - kind: other
        ref: "python3 -m compileall -q pipeline api scripts tests alembic -> 0"
        status: pass
    human_judgment: false
  - id: D8
    description: "Requirement-to-evidence traceability (REVIEW-01..05, D-34, all four T-49-* threat refs) plus the D-32 transcript, the corrected Pitfall 4 premise, and every outstanding human-verification item across the phase consolidated into one list"
    verification:
      - kind: other
        ref: "49-EVIDENCE.md — self-contained; every command transcribed verbatim"
        status: pass
    human_judgment: false

duration: 100min
completed: 2026-08-23
status: complete
---

# Phase 49 Plan 06: Dev-Only Unresolved-Speaker Seeder, D-32 Walkthrough, and Phase Close-Out Summary

**A dev-only seeder that nulls both an `ArgumentParticipant` and its matching `Utterance` rows (preferring an already-UNKNOWN-side participant, traced against the real consumer code rather than the plan's literal pick) closes 26-UAT Test 26 and 14-UAT Test 8's data-layer blocker; a live, scripted D-32 authority-conflict walkthrough found and fixed a real gap in the review queue's own discrepancy-inclusion logic; the phase-carried `readonlyMode` split lands; full suite closes at 1414 passed / 5 xfailed / 0 failed.**

## Performance

- **Duration:** ~100 min
- **Tasks:** 3
- **Files touched:** 15 (2 created, 13 modified)
- **Commits:** 6 (5 task/fix commits + this plan's metadata commit)

## Accomplishments

- **`seed_unresolved_speaker_fixture`** (`api/services/admin_dev.py`) — dev-only (mounted only when
  `settings.environment == "development"`, the same gate `reset_to_fixture` uses), idempotent,
  and deterministic: it nulls one participant's `person_id` on the Complexity fixture, preferring
  a participant whose `side` is already `SideEnum.UNKNOWN` (a real, pre-existing state in the
  corpus data, not synthetic) over the plan's literal "first non-BENCH participant" instruction —
  traced against the actual downstream consumers (`list_argument_speakers`, `ChatBubble.svelte`)
  before writing the fixture, because the literal pick would have selected a resolved-side row and
  left 26-UAT Test 26's placeholder unreachable. It also nulls the matching `Utterance` rows
  (scoped by `raw_speaker_label`) — an independent column the public chat page reads directly —
  closing the second half of 14-UAT Test 8's own precondition. `POST
  /api/admin/dev/seed-unresolved-speaker` has no request surface of its own.
- **Dev Tools "Seed unresolved speaker" control** on `/admin` — single-step, secondary/muted
  treatment (not the destructive reset-button styling), with its own distinct error copy.
- **26-UAT Test 26 and 14-UAT Test 8 reclassified `waived -> blocked`**, each carrying a dated,
  script-verified observation of exactly what is and is not confirmed — not marked `pass`, because
  the literal on-screen observation both tests require was not made (this sandbox denies reading
  `.env` for admin credentials, the same constraint 49-01/49-03/49-05 hit).
- **D-32's live authority-conflict walkthrough**, performed end to end via a repeatable script
  against the real dev database (transcript in `49-EVIDENCE.md` §5): an operator edit survives a
  simulated lower-authority corpus re-import's disagreement; the discrepancy is visible with both
  competing values and provenance; `reflag` closes it; the tier reflects a fresh, correct
  recompute. **This walkthrough found a real, phase-central defect**: the review queue's own
  `_argument_attention_predicate` had no leg for "a constituent has an open discrepancy" — the
  People-tab predicate already did — so an operator-edited, already-resolved participant that a
  re-import disagreed with (exactly REVIEW-02/REVIEW-04's central claim) was invisible in
  `/admin/review`. Fixed in the same plan, same file, with two new regression tests.
- **The frontend `readonlyMode` split**, carried forward and flagged by both 49-04 and 49-05,
  closed here: `resolveCardReadonly` (`status === 'published'`, matching 49-04's already-widened
  backend guard) and `metadataReadonly` (unchanged) replace the one shared boolean that
  incorrectly kept DRAFT/UNPUBLISHED arguments' Resolve cards read-only in the UI even after the
  backend started accepting those writes.
- **Corrected a false premise inherited from `49-RESEARCH.md` Pitfall 4** ("no live corpus path
  can produce an unresolved speaker") — verified false against the live dev DB before this plan
  started (argument 1788 had 11 `person_id IS NULL` rows from a job parked pre-resolve). The
  seeder's real justification (a deterministic, repeatable fixture) is stated plainly in its own
  docstring; the false claim is not restated anywhere.
- **`49-EVIDENCE.md`** — requirement-to-evidence traceability for REVIEW-01 through REVIEW-05 and
  all four `T-49-*` threat refs, the full D-32 script and transcript, the corrected premise, and
  every outstanding human-verification item across all six plans of this phase consolidated into
  one ordered list for a single sitting.
- **Full suite: 1414 passed, 5 xfailed, 0 failed** (from 1403 at the start of this plan — +9 new
  seeder tests, +2 new discrepancy-leg regression tests). Confirmed in a fully isolated run after
  an earlier concurrent run (this plan's own live-DB verification scripts running alongside a
  background pytest process) produced two spurious `DeadlockDetectedError` failures — an
  environment artifact (this sandbox's `TEST_DATABASE_URL` and `DATABASE_URL` resolve to the same
  physical database), not a regression; re-running the two named tests in isolation passed
  cleanly, and the final isolated full-suite run confirms it.

## Task Commits

1. **Task 1 — dev-only unresolved-speaker seeder:** `26b00a56c` (feat)
2. **Task 1 fix — seeder must reproduce the states 26-UAT/14-UAT actually need:** `c8a4bee82` (fix)
3. **Task 2 — Dev Tools control + UAT re-triage:** `c706d46c4` (feat)
4. **Task 2 follow-on — readonlyMode split:** `110a5b80a` (fix)
5. **Task 3 — review queue discrepancy-inclusion fix (found during the D-32 walkthrough):** `5c089267d` (fix)

_Task 3's own deliverable (the D-32 walkthrough transcript, full-suite gate, and requirement
traceability) is `49-EVIDENCE.md` — a documentation artifact, folded into this plan's final
metadata commit rather than a separate code commit._

## Files Created/Modified

- `api/services/admin_dev.py` — `seed_unresolved_speaker_fixture`, `FixtureNotSeededError`, the
  UNKNOWN-side preference and Utterance-nulling fix
- `api/routers/admin_dev.py` — `POST /seed-unresolved-speaker`
- `api/schemas/admin_dev.py` — `SeedUnresolvedSpeakerResponse`
- `api/tests/test_admin_dev_unresolved_fixture.py` — new, 9 tests
- `api/services/admin_review.py` — `_argument_attention_predicate`'s fourth leg;
  `list_review_queue_arguments`'s widened constituent-inclusion check
- `api/tests/test_admin_review_service.py` — 2 new regression tests for the discrepancy-leg fix
- `app/src/routes/admin/+page.server.ts` — `seedUnresolvedSpeaker` form action
- `app/src/routes/admin/+page.svelte` — the Dev Tools control
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `+page.svelte` — `readonlyMode` split
- `.planning/milestones/v1.5-phases/26-arguments-admin/26-UAT.md` — Test 26 reclassified
- `.planning/milestones/v1.2-phases/14-speaker-popover-card/14-UAT.md` — Test 8 reclassified
- `.planning/todos/completed/2026-08-21-widen-participant-editability-to-all-unpublished-states.md`
  — moved from `pending/`, closing note added
- `.planning/WINDOWS.md` — 9 new entries (2 deviations, 1 fixed-in-place correction, 8
  unrun-verify browser items — see §9 below and 49-EVIDENCE.md §9)
- `.planning/phases/49-review-model/49-EVIDENCE.md` — new

## Decisions Made

See `key-decisions` in frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The seeder's literal "first non-BENCH participant" pick does not reproduce 26-UAT Test 26's actual precondition**
- **Found during:** Task 1, before writing any test — traced `list_argument_speakers` and the
  Speakers card's `speakerSideById` mapping against the plan's literal selection text
- **Issue:** 26-UAT Test 26 needs `ArgumentParticipant.side == 'UNKNOWN'`. The plan's literal
  action text ("select the first non-BENCH participant ordered by id ASC") would have selected a
  resolved-side (`PETITIONER`) participant on the real Complexity fixture, never `UNKNOWN` —
  verified live against the dev DB before fixing.
- **Fix:** The seeder now queries for a `side == UNKNOWN` participant first, falling back to the
  plan's original "first non-BENCH ordered by id" pick only when none exists — still fully
  deterministic.
- **Files modified:** `api/services/admin_dev.py`
- **Verification:** `test_seeder_nulls_person_id_of_one_advocate_participant_and_flags_needs_review`
  (asserts the UNKNOWN-side row is selected over a lower-id resolved-side decoy); live dev-DB run
  confirmed the real Complexity fixture's own participant 3586 (Lloyd N. Cutler, `side=UNKNOWN`)
  is selected, not the lower-id `PETITIONER` row.
- **Committed in:** `c8a4bee82`

**2. [Rule 2 - Missing Critical] Nulling only the ArgumentParticipant leaves 14-UAT Test 8 unreachable**
- **Found during:** Task 1, same trace — `api/services/arguments.py` reads `Utterance.person_id`
  directly for the public chat page, never through `ArgumentParticipant`
- **Issue:** `Utterance.person_id` is an independent column from `ArgumentParticipant.person_id`;
  nulling only the participant leaves every utterance that speaker gave still reading a resolved
  person_id, so the public `ChatBubble` avatar would still render as clickable/resolved.
- **Fix:** The seeder also nulls every `Utterance` row on the same argument whose
  `raw_speaker_label` matches the target participant's, mirroring how
  `api/services/admin_jobs.py`'s real resolve flow writes the two columns separately.
- **Files modified:** `api/services/admin_dev.py`
- **Verification:** `test_seeder_also_nulls_matching_utterances_scoped_by_raw_speaker_label`; live
  dev-DB run confirmed all 5 matching `Utterance` rows now read `person_id IS NULL`.
- **Committed in:** `c8a4bee82`

**3. [Rule 2 - Missing Critical, found live during Task 3's D-32 walkthrough] Review queue never surfaced a participant's own open discrepancy unless it ALSO independently qualified via needs_review or person_id IS NULL**
- **Found during:** Task 3 — running the plan's own D-32 script for the first time, step 3 raised
  `StopIteration` because the constituent with the open discrepancy was not in the returned list
- **Issue:** `_argument_attention_predicate` (`api/services/admin_review.py`) had three legs, none
  of which check for an open discrepancy — an operator-edited, already-resolved participant that a
  lower-authority re-import disagreed with (exactly D-32's own scenario, and REVIEW-02/REVIEW-04's
  central claim) satisfied none of them. The equivalent People-tab predicate already had this leg.
- **Fix:** Added a fourth leg to `_argument_attention_predicate` (open discrepancy on any
  constituent); widened `list_review_queue_arguments`'s per-constituent inclusion check to match,
  pre-fetching the discrepant-participant-id set once. `get_review_queue_stats` picks this up
  automatically (shared predicate, D-30).
- **Files modified:** `api/services/admin_review.py`, `api/tests/test_admin_review_service.py`
- **Verification:** re-ran the exact D-32 script after the fix — step 3 now succeeds (full
  before/after transcript in `49-EVIDENCE.md` §5c); two new regression tests
  (`test_discrepancy_alone_includes_argument_and_lists_constituent`,
  `test_argument_no_longer_listed_once_its_only_discrepancy_closes`).
- **Committed in:** `5c089267d`

**4. [Rule 2/carried item, explicitly resolved not silently passed along a third time] Frontend readonlyMode split**
- **Found during:** flagged by plans 49-04 and 49-05, both of which deferred it
- **Issue:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` computed one shared
  `readonlyMode` boolean gating both the Resolve card (widened by 49-04's backend) and the
  unrelated `ArgumentDetailsCard` metadata form — a real UI/backend inconsistency for
  DRAFT/UNPUBLISHED arguments.
- **Fix:** Split into `resolveCardReadonly` (`status === 'published'`) and `metadataReadonly`
  (unchanged, `status !== 'candidate'` — `update_argument_metadata` has no status guard of its
  own, and nothing in this plan's scope asked that concern to change).
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `+page.svelte`
- **Verification:** `npm --prefix app run check` (0 errors, unchanged warning count);
  `api/tests/test_phase44_resolve_table_contract.py` (111 passed, unaffected).
- **Committed in:** `110a5b80a`

### Documented, Not Fixed

**5. [Genuinely outside this plan's mandate] 14-UAT Test 8's second precondition — the fixture must be published**
- The Complexity fixture is deliberately left `CANDIDATE`/`DRAFT` by `reset_to_fixture` (other
  Phase 44/49 work relies on it staying editable). Test 8 needs the argument reachable on the
  public chat page, which requires `PUBLISHED`. Auto-publishing a fixture as a side effect of a
  "seed unresolved speaker" dev action would be surprising, unscoped behavior with no test
  coverage of its own — deliberately not added. A human who wants the public view must publish
  this fixture themselves, understanding that leaves it in a modified state until the next reset.
- **Not fixed.** Documented in `14-UAT.md`'s own `phase_49_06_update` and `49-EVIDENCE.md` §3/§11.

---

**Total deviations:** 4 auto-fixed (2 Rule 1/2 fixes closing this plan's own stated purpose, 1
Rule 2 fix found live during the D-32 walkthrough, 1 carried-item resolution), 1 documented-not-fixed
(a genuine scope boundary, not an oversight).
**Impact on plan:** All fixes were either required to achieve this plan's own stated goals (26-UAT/14-UAT
reachability) or found live by exercising the exact scenario the phase's central requirement
(REVIEW-02/REVIEW-04) describes — not scope creep, and not silently smoothed over.

## Issues Encountered

**Could not complete any live browser walkthrough** — same credential-access constraint recorded
in 49-01/49-03/49-05-SUMMARY.md: authenticating to `/admin/**` requires
`ADMIN_USERNAME`/`ADMIN_PASSWORD` (or `SESSION_SECRET` to forge a session cookie) from `.env`, and
this sandbox's permission policy denies reading `.env`. No workaround was attempted. Instead,
every mechanism this plan needed to verify was exercised directly against the live dev database
via short, repeatable scripts (the same technique the plan's own Task 3 text sanctions for D-32),
and the results are transcribed verbatim in `49-EVIDENCE.md`. All eight outstanding
human-verification items across the whole phase are consolidated into one list there (§9) rather
than left scattered across five SUMMARY files.

**A genuine environment discovery, not a code defect:** running a full-suite pytest process and a
direct dev-DB verification script at the same time produced two spurious `DeadlockDetectedError`
failures (`test_admin_dev_routes.py::test_reset_against_empty_database`,
`::test_reset_incomplete_reseed_raises`) — this sandbox's `TEST_DATABASE_URL` and `DATABASE_URL`
resolve to the same physical Postgres database (both hit OID 17111), so the codebase's own
"isolated by database name" assumption does not hold here. Confirmed as an artifact (not a
regression) by re-running the two tests in isolation (9/9 passed) and by a subsequent fully
isolated full-suite run (1414 passed, 0 failed). Recorded in `49-EVIDENCE.md` §6 and §11 so a
future executor in this sandbox does not repeat the mistake.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Phase 49 (Review Model) is complete.** All five REVIEW-0X requirements are `Complete` in
  `.planning/REQUIREMENTS.md`.
- **Eight outstanding human-verification items** (26-UAT Test 26, 14-UAT Test 8, D-32's visual
  rendering, the new Dev Tools button, and four inherited from 49-01/49-03/49-05) are consolidated
  into one ordered list in `49-EVIDENCE.md` §9 for a single sitting, and each is also recorded in
  `.planning/WINDOWS.md` as `unrun-verify`.
- **14-UAT Test 8's own second precondition** (publish the fixture to reach the public page) is a
  standing, deliberate gap between this seeder and that test — recorded, not silently closed.
- **`api/domain/trust.py` confirmed byte-identical throughout this plan** (`git diff --stat`
  empty). **`api/domain/authority.py` confirmed to import nothing beyond its own dependencies.**
  No new migration authored — `alembic/versions/` still ends at `0029`.
- **This sandbox's shared TEST_DATABASE_URL/DATABASE_URL discovery** is worth a look before Phase
  50 starts running its own live-DB verification scripts.

## Self-Check: PASSED

- `api/services/admin_dev.py`, `api/routers/admin_dev.py`, `api/schemas/admin_dev.py`,
  `api/tests/test_admin_dev_unresolved_fixture.py`, `api/services/admin_review.py`,
  `app/src/routes/admin/+page.server.ts`, `app/src/routes/admin/+page.svelte`,
  `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `+page.svelte`,
  `.planning/phases/49-review-model/49-EVIDENCE.md` — all confirmed present via `git show`/`[ -f ]`.
- Commits `26b00a56c`, `c8a4bee82`, `c706d46c4`, `110a5b80a`, `5c089267d` all found in
  `git log --oneline --grep="49-06"`.
- `./.venv/bin/python -m pytest api/tests/test_admin_dev_unresolved_fixture.py -q` -> 9 passed.
- `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py -q` -> 30 passed.
- Full isolated `./.venv/bin/python -m pytest -q` -> 1414 passed, 5 xfailed, 0 failed.
- `python3 -m compileall -q pipeline api scripts tests alembic` -> clean.
- `npm --prefix app run check` -> 0 errors, 37 warnings (unchanged baseline).
- `git diff --stat api/domain/trust.py` -> empty.
- `./.venv/bin/alembic current` -> `0029 (head)`.
- `.planning/REQUIREMENTS.md`: REVIEW-01 through REVIEW-05 all `[x]` / `Complete`.

---
*Phase: 49-review-model*
*Completed: 2026-08-23*
