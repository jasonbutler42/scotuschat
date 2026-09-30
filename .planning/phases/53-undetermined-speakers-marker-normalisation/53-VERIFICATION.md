---
phase: 53-undetermined-speakers-marker-normalisation
verified: 2026-09-30T15:33:04Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - ".planning/codebase/DESIGN-SYSTEM.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-01-PLAN.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-01-SUMMARY.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-02-PLAN.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-02-SUMMARY.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-03-PLAN.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-03-SUMMARY.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-04-PLAN.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-04-SUMMARY.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-05-PLAN.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-05-SUMMARY.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-REVIEW-DISPOSITION.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-REVIEW.md"
  - ".planning/phases/53-undetermined-speakers-marker-normalisation/53-UAT.md"
  - "alembic/versions/0033_utterance_speaker_and_marker_facts.py"
  - "api/domain/trust.py"
  - "api/models/models.py"
  - "api/schemas/utterance.py"
  - "api/services/arguments.py"
  - "api/services/trust.py"
  - "api/tests/test_published_gate.py"
  - "api/tests/test_trust_domain.py"
  - "api/tests/test_trust_public_leak_ban.py"
  - "api/tests/test_trust_recompute.py"
  - "app/src/app.css"
  - "app/src/lib/admin/blockerSentence.js"
  - "app/src/lib/public/ChatBubble.svelte"
  - "app/src/lib/public/SpeakerPopover.svelte"
  - "app/src/lib/public/StageDirection.svelte"
  - "app/src/lib/public/UndeterminedBubble.svelte"
  - "app/src/lib/public/UndeterminedSpeakerCard.svelte"
  - "app/src/routes/admin/arguments/+page.server.ts"
  - "app/src/routes/admin/arguments/+page.svelte"
  - "app/src/routes/admin/arguments/[id]/+page.server.ts"
  - "app/src/routes/admin/arguments/[id]/+page.svelte"
  - "app/src/routes/admin/review/+page.server.ts"
  - "app/src/routes/admin/review/+page.svelte"
  - "app/src/routes/arguments/[slug]/+page.svelte"
  - "app/tests/blocker-sentence.test.mjs"
  - "app/tests/helpers/transcript-page.mjs"
  - "app/tests/undetermined-bubble.browser.test.mjs"
  - "app/tests/undetermined-speaker-card.browser.test.mjs"
  - "pipeline/commands/import_convokit.py"
  - "pipeline/corpus/stage_directions.py"
  - "pipeline/tests/test_corpus_stage_directions.py"
  - "pipeline/tests/test_import_convokit_utterances.py"
  - "tests/test_schema.py"
covered_digest: "v2:sha256:b1d4d2b8ecde5284b098b6bf177cdc9ce07c5452374b27b906c65ccaee8ad564"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 8/8
  gaps_closed: []
  human_items_resolved:
    - "Treatment D visual read-check (Figma 33:2): passed in 53-UAT.md (commit 3fcb68883)"
    - "Explanation card visual + real touch device (Figma 33:62): passed in 53-UAT.md (commit 3fcb68883)"
    - "Live admin round-trip, majority-undetermined sentence + override publish: passed in 53-UAT.md (commit 3fcb68883)"
  gaps_remaining: []
  regressions: []
---

# Phase 53: Undetermined Speakers & Marker Normalisation Verification Report

**Phase Goal:** A turn the source could not attribute is shown honestly rather than guessed at or rendered broken, such arguments are publishable, and every transcription marker reads the same way everywhere.
**Verified:** 2026-09-30T15:33:04Z
**Status:** passed
**Re-verification:** Yes. The prior report (2026-09-29T15:46:13Z, human_needed, 8/8) went stale when commit `21c3a96d6` changed a covered file. This pass re-checks that change and records the human UAT outcome from commit `3fcb68883`.

## What changed since the prior verification

| Commit | Scope | Effect on verification |
|---|---|---|
| `21c3a96d6` fix(53): clamp the transcript popover to the viewport on phones | `app/src/routes/arguments/[slug]/+page.svelte`: 3 lines added, 1 removed. Adds `collisionPadding={16}` and changes `min-width`/`max-width` from `300px`/`400px` to `min(300px, calc(100vw - 2 * var(--space-lg)))` / `min(400px, calc(100vw - 2 * var(--space-lg)))` | The only production-code change. It is CSS plus one bits-ui prop, with no logic change. It was re-verified behaviorally (see Spot-Checks). |
| `c39a2b7cc` docs: reset progress bar future enhancement | `.planning` only | None |
| `3fcb68883` test(53): complete UAT | `53-UAT.md`: 3/3 passed, 0 issues | Resolves all three prior human-verification items |

`git diff --stat 1e64fdf01~1 HEAD -- . ':!.planning'` confirms that one file is the only non-planning change.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | SC1 / SPEAKER-01,03: a `type: "U"` sentinel utterance renders as Treatment D, based on a fact stored at import and never re-derived from `raw_speaker_label`. No literal `<INAUDIBLE>` reaches the page | ✓ VERIFIED | Importer: `_UNATTRIBUTED_TYPE_VALUES` (import_convokit.py:164) and `_is_unattributed_speaker_type` (:1624) key on `type` only. Migration 0033 enforces it with a CHECK. The route's `renderItems` classifies `'undetermined'` from `u.speaker_undetermined === true` before the run-continuation check. `undetermined-bubble.browser.test.mjs` passed when re-run this session. The full pytest run passes, including the type-not-name keying tests. Operator UAT item 1 passed. |
| 2 | SC2 / SPEAKER-02: hovering reveals the dashed `?` avatar in both rails, and clicking either opens the explanation card in the bio-card shape | ✓ VERIFIED | Still exactly one shared `Popover.Root` (`grep -c` = 3, unchanged). `undetermined-speaker-card.browser.test.mjs` passed 2/2 when re-run in a real windowed Chromium. It covers hover-reveal of both avatars, click to open, keyboard, and touch (touch ran via `Emulation.setTouchEmulationEnabled` + `Input.dispatchTouchEvent`). Operator UAT item 2 passed on desktop and a real touch device. |
| 3 | SC3 / SPEAKER-04,05: an argument with sentinels and no other blocker publishes without override, and one that is more than 50% undetermined is held until the operator overrides it | ✓ VERIFIED | `api/services/trust.py`: the `speaker_undetermined is True` PROVISIONAL branch (:143) comes before the `person_id is None` fallback. `MAJORITY_UNDETERMINED_BLOCKER_CODE` is emitted post-loop with `percent` (:220). `api/domain/trust.py` still provides `exceeds_undetermined_majority`/`undetermined_share_percent`. The full pytest run passes, including the DB-backed publish tests (blocked without override, succeeds with override). Operator UAT item 3 passed: the identical sentence showed on all three admin surfaces, and the override publish is unchanged. |
| 4 | SC4 / SPEAKER-07,08: a whole-turn inaudible with a known speaker stays that speaker's attributed bubble. Laughter still splits, and Voice Overlap is still a stage direction | ✓ VERIFIED | The three-way `_ROW_SPEECH`/`_ROW_ROOM_EVENT`/`_ROW_INAUDIBLE` classification is present (`_ROW_INAUDIBLE` at import_convokit.py:1988). The pre-existing laughter-split and stage-direction regression tests pass in the full run. The inaudible-body styling passed in the browser test re-run. |
| 5 | SC5 / SPEAKER-06: every curated whole-turn marker shows one canonical form, and inline markers are left verbatim | ✓ VERIFIED | `canonical_marker_text` (stage_directions.py:115) is still the single wrapper. The 13-form canonicalisation test and the inline-untouched test pass in the full run. `verbatim_text` is absent from the public schema, the services, and the frontend (grep empty). |

**Score:** 5/5 ROADMAP success criteria verified. All 8 requirement IDs (SPEAKER-01..08) are satisfied, giving 8/8 must-haves. 0 present-but-behavior-unverified.

### ROADMAP Notes (regression check)

All six Notes checks from the prior report still hold. Two were directly re-confirmed:
- The design-system tokens `--font-style-italic` and `--opacity-muted` are still declared in `app/src/app.css` (:165-166) and consumed at :233.
- PROVISIONAL and trust vocabulary never reach public paths: `grep -rniE "provisional|trust_tier|review_state" app/src/lib/public app/src/routes/arguments` is empty, and the leak-ban test passes in the full run.

The popover fix uses `var(--space-lg)` (16px, app.css:141), so it adds no new raw spacing value. The `300px`/`400px` literals predate this change.

### Required Artifacts

| Artifact | Status | Details |
|---|---|---|
| `alembic/versions/0033_utterance_speaker_and_marker_facts.py` | ✓ VERIFIED | Unchanged since prior verification; schema tests pass |
| `api/domain/trust.py`, `api/services/trust.py` | ✓ VERIFIED | Unchanged; symbols present; tests pass |
| `pipeline/corpus/stage_directions.py`, `pipeline/commands/import_convokit.py` | ✓ VERIFIED | Unchanged; symbols present; tests pass |
| `api/schemas/utterance.py` | ✓ VERIFIED | `speaker_undetermined`/`is_inaudible_marker` default `False`; no `verbatim_text` |
| `app/src/lib/public/UndeterminedBubble.svelte`, `UndeterminedSpeakerCard.svelte` | ✓ VERIFIED | Unchanged; browser tests pass |
| `app/src/routes/arguments/[slug]/+page.svelte` | ✓ VERIFIED | Changed by `21c3a96d6`. Re-read in full: single `Popover.Root`, both content modes intact, `renderItems`/`roster`/`speakerSlots` undetermined skips intact. Geometry re-verified. |
| `app/src/lib/admin/blockerSentence.js` | ✓ VERIFIED | Exactly one `function blockerSentence`; 14 unit cases pass |

### Key Link Verification

All 8 key links from the prior report are unchanged. Their code paths are untouched, and the full backend suite plus the browser tests exercise them end to end. The only link that touches the changed file, avatar click into `UndeterminedSpeakerCard` inside the shared `Popover.Root` via `onUndeterminedAvatarClick` and `popoverMode = 'undetermined'`, was re-read and re-exercised. ✓ WIRED.

### Behavioral Spot-Checks (all re-run in this session)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full backend suite (single full run) | bare `pytest -q` from repo root | **1484 passed, 5 xfailed, 0 failed** (541s), exit 0 | ✓ PASS |
| Svelte type/diagnostic check | `npm --prefix app run check` | **0 errors**, 32 warnings in 9 files, exit 0. None are in a file 21c3a96d6 touched. The one warning in a Phase 53-touched file (`admin/arguments/[id]/+page.svelte:119`, `state_referenced_locally`) comes from blame `f7a7521fb9` (2026-07-22), which predates Phase 53. | ✓ PASS |
| Production build | `npm --prefix app run build` | adapter-node build done, exit 0 | ✓ PASS |
| App unit tests | `node --test tests/blocker-sentence.test.mjs tests/reset-outcome-classifier.test.mjs` | 20 pass, 0 fail | ✓ PASS |
| Phase 53 real-browser tests | `node --test --test-concurrency=1 tests/undetermined-bubble.browser.test.mjs tests/undetermined-speaker-card.browser.test.mjs` | 3 pass, 0 fail | ✓ PASS |
| Other app browser tests (speaker-initials and tenure-public-title use the transcript page's shared popover and bio-card path) | `node --test --test-concurrency=1` over the remaining 5 `*.browser.test.mjs` files | 11 pass, 0 fail | ✓ PASS |
| **Popover clamp (the 21c3a96d6 fix itself)** | Throwaway CDP probe (scratchpad, not committed) using `openTranscriptPage`, measuring the popover's `getBoundingClientRect()` | 390px: explanation card from right avatar = 16 to 374px (width 358); from left avatar = 16 to 374px; bio card = 59 to 359px (width 300). 1280px: explanation card width 400, bio card width 300 (unchanged desktop behavior) | ✓ PASS |

### Probe Execution

Not applicable. This is not a migration/tooling phase, and no PLAN or SUMMARY declares a `probe-*.sh`.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|---|---|---|---|
| SPEAKER-01 | 53-02, 53-03, 53-04 | ✓ SATISFIED | Truth 1; UAT item 1 |
| SPEAKER-02 | 53-04 | ✓ SATISFIED | Truth 2; UAT item 2 |
| SPEAKER-03 | 53-01 | ✓ SATISFIED | Truth 1 |
| SPEAKER-04 | 53-01 | ✓ SATISFIED | Truth 3 |
| SPEAKER-05 | 53-01, 53-05 | ✓ SATISFIED | Truth 3; UAT item 3 |
| SPEAKER-06 | 53-02, 53-03 | ✓ SATISFIED | Truth 5 |
| SPEAKER-07 | 53-02, 53-03 | ✓ SATISFIED | Truth 4 |
| SPEAKER-08 | 53-02 | ✓ SATISFIED | Truth 4 |

There are no orphaned requirements. REQUIREMENTS.md maps SPEAKER-01..08 to Phase 53, and all eight are claimed by a plan and marked Complete. PUBLISH-04, which references SPEAKER-05, belongs to a later phase.

### Anti-Patterns Found

None. `TBD|FIXME|XXX` across every non-planning file changed since the phase base (`6ce3721eb..HEAD`): 0 matches. `TODO|HACK|PLACEHOLDER` in the changed route file: 0 matches.

### Code Review Disposition

Unchanged. WR-01, WR-02 and IN-02 were fixed in `8f9a30ed9`. IN-01 was deferred as non-behavioral. `21c3a96d6` postdates the review, and its change is covered by the geometry spot-check above.

### Human Verification

All three items the prior report routed to human verification were **passed by the operator** in `53-UAT.md` (status complete, 3 passed, 0 issues, 0 pending; commit `3fcb68883`):

1. Treatment D at rest against Figma node 33:2, desktop and 390px: **pass**
2. Explanation card against Figma node 33:62, desktop and a real touch device, including the D-15 inaudible swap: **pass**
3. Live admin round-trip showing the majority-undetermined sentence on all three surfaces, with the override publish unchanged: **pass**

UAT was recorded after `21c3a96d6` (UAT updated 2026-09-30, fix committed 2026-09-29), so the phone-device check in item 2 ran against the clamped popover. No human items remain open.

### Gaps Summary

None. The single production change since the last verification (the popover viewport clamp) is correct: its geometry was measured at 390px and 1280px, and it caused no regression. Every check passed:
- full backend suite
- svelte-check (0 errors)
- build
- app unit tests
- all 7 browser test files

The three human-verification items are closed by operator UAT. All 5 success criteria and all 8 requirements are verified, so the phase goal is achieved.

---

_Verified: 2026-09-30T15:33:04Z_
_Verifier: Claude (gsd-verifier)_
