---
phase: 45-deferred-ui-bug-fixes
verified: 2026-08-12T00:00:00Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 2
overrides:
  - must_have: "The element that owns overflow-y auto and max-height min(560px, 80vh) is the same element that owns background-color #1e293b, border 1px solid #334155, and border-radius 8px, so the native scrollbar track renders inside the card's visible rounded boundary (D-03)."
    reason: "D-03 was REVISED at the Task 3 live checkpoint after the original whole-card-scroll approach failed operator visual verification. Operator supplied a Figma reference (\"person popover with bio examples\", node 4230:121) showing the card sizing to its content with no outer scroll; only the bio paragraph scrolls internally, capped at 150px via a `.bio-scroll` class. Popover.Content now owns surface/border/radius/width-bounds only — max-height/overflow-y were removed entirely, not merely relocated. Operator explicitly approved the revised shape in-browser (\"that scrollbar placement is perfect! looks good at all heights. Approved\"). Confirmed current source matches this revision exactly (test_phase45_popover_boxmodel_contract.py, 26 assertions, all passing)."
    accepted_by: "operator (live checkpoint, Phase 45 Plan 02 Task 3)"
    accepted_at: "2026-08-12"
  - must_have: "EDGE boundary (BUG-02): behavior is continuous at the overflow threshold — content at or below min(560px, 80vh) renders with no scrollbar and content above it scrolls, in both branches of the min() ... the 300px min-width and 400px max-width bounds are enforced on that same boundary-owning element."
    reason: "The min(560px, 80vh) outer-card threshold no longer exists under the approved revision — the whole premise of an outer-card scroll ceiling was replaced with a bio-scoped 150px cap. This truth described the pre-revision architecture. The width bounds (300px/400px) part of this truth remains true and is verified on Popover.Content in the current source. Superseded by the same operator-approved pivot documented in 45-02-SUMMARY.md's Deviations section."
    accepted_by: "operator (live checkpoint, Phase 45 Plan 02 Task 3)"
    accepted_at: "2026-08-12"
requirements_coverage:
  - id: BUG-01
    status: satisfied
  - id: BUG-02
    status: satisfied
---

# Phase 45: Deferred UI Bug Fixes Verification Report

**Phase Goal:** Close BUG-01 (unpublished arguments must be unreachable from the public surface) and BUG-02 (the speaker popover's scrollbar must render inside the visible card boundary), both deferred UI/data-integrity bugs identified after Phase 43.
**Verified:** 2026-08-12
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — authoritative contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | An argument in Draft/Unpublished status does not appear in the public `/cases/` list | ✓ VERIFIED | `api/services/cases.py`'s pre-existing D-06 gate unchanged (empty diff outside this phase's 4 files); re-asserted unbroken by `TestPublishedGate` (4 tests, all pass); operator confirmed live at 45-01 Task 3 step 1 |
| 2 | Requesting an unpublished argument's URL directly returns the chosen non-content response (404) instead of the transcript, on both client-side nav and hard SSR refresh | ✓ VERIFIED | `api/services/arguments.py::get_argument_with_utterances` and `api/services/speakers.py::get_argument_speakers` both gate on `Argument.published_at.isnot(None)` / `is None`, returning `None` → router raises `HTTPException(404, "Argument not found")` (`api/routers/arguments.py:44-45,66-68`); `+page.server.ts`'s pre-existing `error(res.status, ...)` confirmed unchanged and sufficient by source-contract test `test_page_server_loader_throws_on_non_ok_and_has_no_publish_branch`; operator confirmed live at 45-01 Task 3 steps 2-3 |
| 3 | Publishing an argument makes it appear in the list and become directly accessible again, with no restart or cache clear | ✓ VERIFIED | Every request re-reads `published_at` from PostgreSQL (no caching layer in the gate); operator confirmed live round-trip at 45-01 Task 3 step 5 (argument 1953 published/verified, argument re-tested) |
| 4 | When a Justice popover's content overflows (long bio with Read more expanded), the scrollbar renders flush inside the card's visible rounded boundary | ✓ VERIFIED (via approved architecture revision) | Original whole-card-scroll approach failed live checkpoint; revised to scope the scroll to the bio `<p>` alone (`.bio-scroll`, `max-height:150px`, custom thin scrollbar reusing `#334155` token) confirmed present in `SpeakerPopover.svelte:185-200,239-258`; `Popover.Content` confirmed to own no `max-height`/`overflow-y` in `+page.svelte:139-148`; 26-assertion contract test (`test_phase45_popover_boxmodel_contract.py`) passes; operator approved live ("that scrollbar placement is perfect! looks good at all heights. Approved") |
| 5 | The popover still shows every field Phase 39 added, with no content truncated or escaping the card | ✓ VERIFIED | All 9 UI-SPEC regression-checklist fields (avatar/initials, name+pill, birth/death halves, advocate descriptor, bio clamp+toggle, tenure rows, 4 dividers, padding, width bounds) individually asserted in `test_phase45_popover_boxmodel_contract.py` Group D (9 tests, pass); `test_phase39_popover_ui_contract.py` unchanged at 17/17 passing; markup in `SpeakerPopover.svelte` confirmed byte-identical to pre-phase field-rendering blocks by direct read |

**Score:** 5/5 ROADMAP success criteria verified.

### Additional PLAN-level must_haves.truths

45-01 (BUG-01) — 10 truths, all verified:

| # | Truth (abbreviated) | Status | Evidence |
|---|------|--------|----------|
| 1 | 404 for unpublished, 200 once published (utterances) | ✓ VERIFIED | Source gate confirmed; live integration tests written (`TestArgumentDetailPublishedGateLive`), skip cleanly without `DATABASE_URL` |
| 2 | 404/200 for speakers endpoint | ✓ VERIFIED | Same pattern in `get_argument_speakers`, confirmed by direct source read |
| 3 | 404 indistinguishable from nonexistent-ID 404 | ✓ VERIFIED | Identical `HTTPException(404, "Argument not found")` string, count=2 confirmed by `test_speakers_router_404_detail_matches_utterances_router`; body-equality integration tests present |
| 4 | `/cases/` D-06 gate re-asserted unbroken | ✓ VERIFIED | `TestPublishedGate` (4 pre-existing tests) still pass |
| 5 | Publish/unpublish round trip, no restart/cache | ✓ VERIFIED | No caching introduced; operator-confirmed live |
| 6 | EDGE adjacency — identical predicate, no clock comparison | ✓ VERIFIED | `test_publish_gate_adjacency_across_gated_functions` passes |
| 7 | EDGE empty — empty speaker list never becomes 404 | ✓ VERIFIED | `if not person_ids: return []` short-circuit confirmed intact in `speakers.py:156-157`; `test_get_argument_speakers_preserves_empty_list_short_circuit` passes |
| 8 | EDGE ordering — WHERE-only change, ordering unchanged | ✓ VERIFIED | `Utterance.sequence.asc()`, `func.max(PipelineRun.id)`, `Argument.argued_date.desc()` all confirmed present by direct source read and `test_ordering_preserved_after_publish_gate` |
| 9 | Admin path unchanged | ✓ VERIFIED | `git diff --name-only api/routers/admin.py api/services/admin_arguments.py` across the full commit range for this phase (f49af5ae..0e804589) produces no output |
| 10 | No SvelteKit change required | ✓ VERIFIED | `+page.server.ts` confirmed unchanged by this phase; source-contract test present |

45-02 (BUG-02) — 8 truths, all verified (2 via operator-approved architecture revision, tracked as overrides above):

| # | Truth (abbreviated) | Status | Evidence |
|---|------|--------|----------|
| 1 | Single element owns scroll + boundary | PASSED (override) | Superseded by revision — see override entry above; revised architecture (bio-scoped scroll) achieves the same visual outcome the truth was protecting against, confirmed operator-approved |
| 2 | Phase 39 field set fully populated case | ✓ VERIFIED | 9-test field-set group + unchanged 17-test Phase 39 suite |
| 3 | Partially-populated case still renders per-field | ✓ VERIFIED | Conditional guards (`{#if speaker.birthdate}`, `{#if speaker.death_date}`, etc.) confirmed unchanged in `SpeakerPopover.svelte` |
| 4 | Overflow content scrolls within bordered box, nothing escapes | ✓ VERIFIED | Bio content capped/scrollable inside the card's visible border; confirmed by source + operator visual check |
| 5 | Long bio clamps to 3 lines, Read more/Show less works, expanded reachable by scroll | ✓ VERIFIED | `-webkit-line-clamp:3` (collapsed) / `max-height:150px;overflow-y:auto` (expanded) ternary confirmed in `SpeakerPopover.svelte:189`; both toggle labels present |
| 6 | EDGE boundary — min(560px,80vh) continuity | PASSED (override) | Superseded — see override entry above; threshold concept replaced by the bio-scoped cap, width bounds portion (300px/400px) independently verified true |
| 7 | EDGE precision — border/padding accounted inside bounds via border-box | ✓ VERIFIED | `app/src/app.css`'s universal border-box rule confirmed unchanged; no `box-sizing` override introduced (2 dedicated tests pass) |
| 8 | Only the two Svelte files + new test file touched | ✓ VERIFIED | `git diff --name-only` for the 45-02 commit range lists exactly `+page.svelte`, `SpeakerPopover.svelte`, `test_phase45_popover_boxmodel_contract.py` |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/arguments.py` | `get_argument_with_utterances` carries the published_at gate | ✓ VERIFIED | Line 50: `.where(Argument.published_at.isnot(None))`, ordering (line 115) and pipeline-run filter (lines 87-93) intact; docstring updated (line 28-29, closes review IN-01) |
| `api/services/speakers.py` | `get_argument_speakers` returns `list[dict] \| None`, gates on published_at | ✓ VERIFIED | Line 115 (annotation), lines 139-144 (Step 0 gate + None return), line 156-157 (empty-list short-circuit preserved) |
| `api/routers/arguments.py` | `get_speakers` raises 404 on None; both endpoints bound `argument_id` | ✓ VERIFIED | Lines 66-68 (None→404 branch), lines 29,51 (`Path(..., ge=1, le=2_147_483_647)` — closes review WR-02) |
| `api/tests/test_published_gate.py` | Source-contract + DB-gated integration classes | ✓ VERIFIED | `TestArgumentDetailPublishedGate` (9 tests) + `TestArgumentDetailPublishedGateLive` (6 tests, DB-gated) present and passing/skipping correctly |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | `Popover.Content` owns surface/border/radius/width-bounds | ✓ VERIFIED | Lines 139-148: confirmed `background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; min-width: 300px; max-width: 400px;` present, `max-height`/`overflow-y` confirmed absent (revised architecture) |
| `app/src/lib/components/SpeakerPopover.svelte` | `.popover-card` reduced to padding/display; bio owns its own scroll | ✓ VERIFIED | Lines 234-237 (`.popover-card { padding: 24px; display: block; }`), lines 185-200 (bio scroll ternary), lines 239-258 (`.bio-scroll` custom scrollbar rules) |
| `api/tests/test_phase45_popover_boxmodel_contract.py` | Static source-contract regression guard | ✓ VERIFIED | 26 tests across 6 groups (A: box ownership, B: bio scroll, C: scrollbar theming, D: field set, E: precision, F: prohibitions), all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `get_argument_with_utterances` returns None | `get_utterances` router's pre-existing None→404 branch | Direct return-value check | ✓ WIRED | `api/routers/arguments.py:44-45` |
| `get_argument_speakers` returns None | `get_speakers` router's new None→404 branch | Direct return-value check | ✓ WIRED | `api/routers/arguments.py:66-68` |
| FastAPI 404 | SvelteKit `+page.server.ts` `error(res.status, ...)` | HTTP status passthrough | ✓ WIRED | Confirmed unchanged and sufficient by source-contract test |
| `Popover.Content` inline `style=` | bits-ui's style-merge behavior | Pre-existing pattern reused (z-index/etc. already proven) | ✓ WIRED | Confirmed by direct source read, no wrapper element introduced |
| Bio `<p bind:this={bioEl}>` | `.bio-scroll` class (conditional) | Svelte class binding | ✓ WIRED | `class={bioExpanded ? 'bio-scroll' : ''}` confirmed at line 188 |

### Behavioral Spot-Checks / Test Execution (run directly by this verifier, not trusted from SUMMARY)

| Command | Result | Status |
|---------|--------|--------|
| `./.venv/Scripts/python.exe -m pytest api/tests/test_published_gate.py api/tests/test_phase45_popover_boxmodel_contract.py api/tests/test_phase39_popover_ui_contract.py -q` | `56 passed, 6 skipped in 0.87s` (skips are the DB-gated live tests, correctly skipping without `DATABASE_URL`) | ✓ PASS |
| `python3 -m compileall -q api` | exit 0 | ✓ PASS |
| `git diff --name-only api/routers/admin.py api/services/admin_arguments.py` across the full phase-45 commit range | no output | ✓ PASS (admin path untouched) |
| `git log --oneline --all \| grep -E "e620eb16\|b83ab9b7\|f49af5ae\|3ae41acf\|a064ab13\|bac9173e\|0e804589"` | all 7 commits found | ✓ PASS (all claimed commits exist) |

**Note on an additional, non-mandated check this verifier ran independently:** attempting to directly re-run the 4 test files fixed by commit `b83ab9b7` (`api/tests/test_argument_oyez_field.py`, `api/tests/test_arguments.py`, `api/tests/test_speakers_service.py`, `pipeline/tests/test_import_convokit_utterances.py`) via explicit file paths reproduced a `UniqueViolationError` on `roles_name_key` — this is the exact pre-existing, already-self-documented pytest DB-isolation infrastructure bug described in commit `b83ab9b7`'s own message (explicit test-file paths bypass `tests/conftest.py`'s `TEST_DATABASE_URL` redirect, so the tests ran against the shared dev DB instead of an isolated test DB). This is not a Phase 45 code defect — it is the same infra issue the executor already flagged and deliberately deferred as a todo, out of this phase's scope. It is called out here for the record, not as a phase gap, and no further live-DB test invocations were made after this was identified.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BUG-01 | 45-01-PLAN.md | Unpublished argument not visible in `/cases/` and not directly accessible by URL | ✓ SATISFIED | Publish gate applied at both public detail endpoints, 404 indistinguishable, operator-confirmed live round trip |
| BUG-02 | 45-02-PLAN.md | Popover scrollbar renders flush inside the card's visible rounded boundary | ✓ SATISFIED | Bio-scoped scroll architecture (operator-approved revision), 26-test contract guard, operator-confirmed live |

No orphaned requirements — `REQUIREMENTS.md`'s traceability table maps exactly these two IDs to Phase 45, both are declared in the two plans' `requirements` frontmatter.

**Minor documentation lag (not a gap):** `.planning/REQUIREMENTS.md`'s checklist items for BUG-01/BUG-02 are still unchecked (`- [ ]`) and its traceability table still reads "Pending" for both, despite both being implemented, tested, code-reviewed, and operator-approved. This is a stale-documentation item, typically updated during a milestone-completion/ship step — flagged here for the record, not treated as a phase-blocking gap since the requirement IDs are present and fully accounted for.

### Anti-Patterns Found

None. Scanned all 7 files touched across the phase's commit range (`api/services/arguments.py`, `api/services/speakers.py`, `api/routers/arguments.py`, `api/tests/test_published_gate.py`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`, `app/src/lib/components/SpeakerPopover.svelte`, `api/tests/test_phase45_popover_boxmodel_contract.py`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` — zero matches.

Three code-review INFO items remain open by design (not phase-blocking, not introduced defects): duplicate `avatarBg`/`sideColor` constants (IN-02), duplicated `TenureRow`/`SpeakerDetail` interfaces across two files (IN-03), and one code-review WARNING accepted as a known future-work item: WR-01 (no outer-viewport safety net now that Popover.Content's own cap was removed) — explicitly flagged by the reviewer as "design-approved shape... should be validated against worst-case data... before shipping" rather than a defect; WR-03 (bench/advocate classification silent-fallback edge case) was deliberately deferred as a todo per this phase's own scope decision, confirmed in the task briefing.

### Human Verification Required

None outstanding. Both blocking checkpoints (45-01 Task 3, 45-02 Task 3) were already run and approved by the human operator directly in conversation, as confirmed in this verification's task briefing and corroborated by direct quotes preserved in both SUMMARY.md files ("Operator ran all seven checkpoint steps against seeded fixtures... confirmed all pass" / "that scrollbar placement is perfect! looks good at all heights. Approved").

### Gaps Summary

No gaps found. Both BUG-01 and BUG-02 are closed:

- **BUG-01**: the publish gate is applied identically to both public argument-detail endpoints (utterances, speakers), keyed solely on `published_at` (never `resolved_at`), returning a byte-identical 404 for absent-vs-unpublished arguments, with the admin path and existing `/cases/` gate confirmed untouched. A post-checkpoint code review found and fixed a real robustness gap (unbounded `argument_id` path parameter causing an unhandled 500) and 11 pre-existing test fixtures broken by the new gate — both fixes are present in the codebase and independently confirmed by this verifier via direct file read and git history, not merely trusted from SUMMARY narrative.
- **BUG-02**: the original whole-card-scroll approach (as literally specified in the PLAN's must_haves) failed live operator verification and was revised, with explicit operator sign-off, to a bio-scoped 150px scroll with a custom thin scrollbar. The revision is fully reflected in the current source, locked by a 26-assertion regression test, and does not regress any Phase 39 field. Two PLAN-level truths that described the pre-revision architecture are recorded as accepted overrides rather than failures, since the underlying visual goal (scrollbar rendering inside the visible card) is achieved by the approved alternative implementation and both ROADMAP-level success criteria (#4, #5) are independently verified true.

Both mandated test commands (`pytest` targeted run, `compileall`) were executed directly by this verifier and passed cleanly.

---

*Verified: 2026-08-12*
*Verifier: Claude (gsd-verifier)*
