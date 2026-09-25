---
phase: 52-justice-identity
plan: 02
subsystem: identity
tags: [pydantic, sqlalchemy, svelte5, node-test, cdp-browser-test, avatar-initials]

# Dependency graph
requires:
  - phase: 52-01
    provides: "Person.first_name/last_name/name_suffix structured parts (Phase 38), Person.display_name + COALESCE(display_name, full_name) speaker_name projection (52-01), the oyez_speaker_id join this plan's fixtures build on"
provides:
  - "api.domain.person_names.derive_initials — the single avatar-initials derivation, structured-parts-first with a D-13 legacy fallback over full_name, co-located with _KNOWN_SUFFIXES"
  - "SpeakerPopoverEntry.initials and UtteranceResponse.speaker_initials — server-computed avatar-initials fields on both public payloads"
  - "SpeakerPopover.svelte and arguments/[slug]/+page.svelte — both client-side name-string splitters (getInitials, the $derived.by initials block) deleted outright; both read the server field"
  - "app/tests/speaker-initials.browser.test.mjs — real-Chromium regression proving the JI -> JH fix, the OH case, the null-initials '?' path, and popover reactivity across a speaker-prop reassignment"
affects: [54.1, 55, 56]

# Actuals (#2632)
actuals:
  tokens: 11367
  tasks: 3
  commits: 4
  plan_head_before: 1536055f775504fe84eb1d3477877d67cc97e576

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-derivation-call-site discipline: when a computed field has two source branches (structured parts vs. a raw-label fallback), pre-select the branch's arguments in a plain if/else, then call the pure derivation function exactly once — not once per branch — so a grep for the function name finds one call, not two."
    - "TDD RED via a stub-then-strengthen return, not an import error: a task tagged tdd=\"true\" for a brand-new function first ships a stub returning the trivial/None value, so the test file imports cleanly and the RED tests fail on a real assertion (not a collection-level ImportError, which this repo's RED-evidence discipline treats as INVALID_RED)."

key-files:
  created:
    - app/tests/speaker-initials.browser.test.mjs
    - .planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md
  modified:
    - api/domain/person_names.py
    - api/tests/test_person_names.py
    - api/schemas/speakers.py
    - api/services/speakers.py
    - api/schemas/utterance.py
    - api/services/arguments.py
    - api/tests/test_speakers_service.py
    - api/tests/test_arguments.py
    - app/src/lib/types/speaker.ts
    - app/src/lib/public/SpeakerPopover.svelte
    - app/src/routes/arguments/[slug]/+page.svelte
    - app/src/routes/arguments/[slug]/+page.server.ts

key-decisions:
  - "derive_initials lives in api/domain/person_names.py, not a new module — co-located with _KNOWN_SUFFIXES because D-13's fallback is defined in terms of that exact vocabulary, and separating them would let a fourth splitter appear elsewhere later without anyone noticing the suffix set had drifted."
  - "arguments.py's utterance loop pre-selects first_name/last_name/name_suffix/full_name (or the raw_speaker_label fallback) in a plain if/else BEFORE calling derive_initials, rather than branching inside the call — this keeps derive_initials to a single call site per file, matching the plan's own acceptance criterion and making a future audit of 'who calls the derivation' trivial."
  - "A third, independent initials splitter (byte-identical algorithm) was found in app/src/lib/admin/ResolveCard.svelte during the structural ban sweep. It was not named in this plan's files_modified or in 52-CONTEXT.md's discretion note (which only knew of two copies), operates on admin-only unresolved-candidate data that may not correspond to a persisted Person's structured parts, and converging it would require its own investigation of what data is actually available at that point in the admin resolve flow. Left untouched as a scope question for the operator, not auto-fixed, and filed as a todo."

patterns-established:
  - "Structural ban sweep as the Testing Policy's narrow source-text exception: `grep -rn getInitials app/src/routes/arguments app/src/lib/public app/src/lib/types` proves absence across a computed file set, which is exactly what source text CAN prove — not a claim about rendered behavior, which is proven separately by the real-Chromium test."

requirements-completed: [JUSTICE-06, JUSTICE-03]

coverage:
  - id: D1
    description: "Single derive_initials implementation (structured-parts-first, D-13 legacy fallback), replacing every prior client-side splitter"
    requirement: JUSTICE-06
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py::test_derive_initials_structured_parts_with_suffix"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py (13 derive_initials tests total, full module 67/67 passing)"
        status: pass
      - kind: other
        ref: "grep -n 'def derive_initials' api/domain/person_names.py -> single definition line"
        status: pass
    human_judgment: false
  - id: D2
    description: "SpeakerPopoverEntry.initials, server-computed from the Person row already in hand in get_argument_speakers (no second query)"
    requirement: JUSTICE-06
    verification:
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersInitials::test_initials_from_structured_parts_ignores_suffix"
        status: pass
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersInitials::test_initials_from_full_name_when_no_structured_parts"
        status: pass
      - kind: other
        ref: "pytest api/tests/test_trust_public_leak_ban.py -q -> 0 failed"
        status: pass
    human_judgment: false
  - id: D3
    description: "UtteranceResponse.speaker_initials, structured parts when person_id is set, raw_speaker_label fallback when it is not, single derive_initials call site per row"
    requirement: JUSTICE-06
    verification:
      - kind: integration
        ref: "api/tests/test_arguments.py::test_speaker_initials_from_person_parts_when_resolved"
        status: pass
      - kind: integration
        ref: "api/tests/test_arguments.py::test_speaker_initials_falls_back_to_raw_speaker_label_when_unresolved"
        status: pass
      - kind: integration
        ref: "api/tests/test_arguments.py::test_speaker_initials_null_when_both_person_and_label_absent"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both client-side splitters deleted (SpeakerPopover.svelte's $derived.by block, +page.svelte's getInitials and its 6 call sites); John Marshall Harlan, II renders JH and Oliver W. Holmes, Jr. renders OH in a real browser, the null-initials case renders '?', and the popover updates across a speaker-prop reassignment"
    requirement: JUSTICE-06
    verification:
      - kind: automated_ui
        ref: "app/tests/speaker-initials.browser.test.mjs (real Chromium via CDP, 4 subtests including the literal rendered strings JH/OH/?)"
        status: pass
      - kind: other
        ref: "grep -rn getInitials app/src/routes/arguments app/src/lib/public app/src/lib/types -> 0 hits (structural ban sweep)"
        status: pass
    human_judgment: false
  - id: D5
    description: "JUSTICE-03 (bio card reads full_name, transcript reads the coalesced display_name form) is unchanged by this plan — confirmed by re-running the 52-01 coverage test, since 52-02 touches neither field's source"
    requirement: JUSTICE-03
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py::test_speaker_name_coalesces_display_name_then_full_name (52-01, re-run green in this plan's full-suite pass)"
        status: pass
    human_judgment: false

duration: 58min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 02: Justice Identity — Avatar Initials Summary

**Avatar initials move from two byte-identical client-side name-string splitters to one server-side `derive_initials` over structured `Person` name parts, proving `John Marshall Harlan, II` renders `JH` (not `JI`) in a real Chromium.**

## Performance

- **Duration:** 58 min
- **Started:** 2026-09-25T11:40:00Z (approx.)
- **Completed:** 2026-09-25T12:37:09Z
- **Tasks:** 3
- **Files modified:** 14 (12 modified, 2 created)

## Accomplishments
- `derive_initials(*, first_name, last_name, name_suffix, full_name)` in `api/domain/person_names.py`: structured parts win and `name_suffix` is deliberately ignored (the `JI` -> `JH` fix); when no parts exist, a D-13 legacy fallback strips a trailing comma per token, drops `_KNOWN_SUFFIXES` tokens, and takes the first/last surviving tokens' initials — pinned by 13 new tests via a genuine RED -> GREEN cycle (9 targeted assertion failures against a stub, then a passing implementation; 67/67 tests green)
- `SpeakerPopoverEntry.initials` and `UtteranceResponse.speaker_initials` both server-computed and shipped on the two public payloads that previously left the client to guess; `api/services/arguments.py`'s utterance assembly pre-selects structured parts or the `raw_speaker_label` fallback in a plain `if/else` so `derive_initials` has exactly one call site per file
- Both client-side splitters deleted outright — `SpeakerPopover.svelte`'s `$derived.by` block (now a one-line `$derived(speaker.initials ?? '?')`) and `+page.svelte`'s `getInitials` function and all 6 call sites (4 roster entries, 2 transcript-run avatars)
- `app/tests/speaker-initials.browser.test.mjs`: real-Chromium regression against a mock FASTAPI backend, proving `JH`/`OH` render in both the transcript avatar and the popover fallback avatar, the null-initials case renders `?`, and reassigning the popover's `speaker` prop to a second person updates the rendered initials (the `$derived`-not-`const` discipline)
- Structural ban sweep: `getInitials` reaches zero files under the plan's targeted directories (`app/src/routes/arguments`, `app/src/lib/public`, `app/src/lib/types`)

## Task Commits

Each task was committed atomically (Task 1 followed the TDD RED -> GREEN cycle per its `tdd="true"` tag):

1. **Task 1 RED: add failing tests for derive_initials** - `f2d0a24a3` (test)
2. **Task 1 GREEN: implement derive_initials over structured name parts** - `4d0b0e637` (feat)
3. **Task 2: ship server-computed initials on both public payloads** - `4a0d1a8a0` (feat)
4. **Task 3: delete both client splitters and prove JH in a real browser** - `b870f9e97` (feat)

## Files Created/Modified
- `api/domain/person_names.py` - `derive_initials`, co-located with `_KNOWN_SUFFIXES`
- `api/tests/test_person_names.py` - 13 new tests covering every `<behavior>` bullet
- `api/schemas/speakers.py` - `SpeakerPopoverEntry.initials: Optional[str] = None`
- `api/services/speakers.py` - Step 5 assembly calls `derive_initials` on the `Person` row already in hand
- `api/schemas/utterance.py` - `UtteranceResponse.speaker_initials: Optional[str] = None`
- `api/services/arguments.py` - extended SELECT with labeled structured-part columns; single `derive_initials` call site per row, structured-parts-first with a `raw_speaker_label` fallback
- `api/tests/test_speakers_service.py` - `_SPEAKER_KEYS` widened with `initials`; 2 new DB-backed tests
- `api/tests/test_arguments.py` - 3 new DB-backed tests (person-parts, raw-label fallback, both-absent null)
- `app/src/lib/types/speaker.ts` - `SpeakerDetail.initials: string | null`
- `app/src/lib/public/SpeakerPopover.svelte` - `$derived.by` splitter replaced with `$derived(speaker.initials ?? '?')`
- `app/src/routes/arguments/[slug]/+page.svelte` - `getInitials` deleted; roster carries `speaker_initials`; transcript run reads `first.speaker_initials`
- `app/src/routes/arguments/[slug]/+page.server.ts` - `RawSpeaker.initials?: string | null` typed through
- `app/tests/speaker-initials.browser.test.mjs` - new real-Chromium regression (4 subtests)
- `.planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md` - flags the admin-only third splitter found during the ban sweep

## Decisions Made
See `key-decisions` in frontmatter. The most consequential: keeping `derive_initials` to a single call site per file required restructuring `arguments.py`'s dict comprehension into an explicit loop that pre-selects the branch's arguments before the one derivation call — a ternary with two inline calls would have satisfied the behavior but failed the plan's own "exactly one call site" acceptance criterion.

## Deviations from Plan

### Auto-fixed Issues

None beyond the design choice above (not a bug fix, a structural choice to satisfy the plan's own acceptance criterion).

### Discovered, Not Fixed (scope question, filed for the operator)

**1. [Scope] A third initials splitter survives in `app/src/lib/admin/ResolveCard.svelte`**
- **Found during:** Task 3's structural ban sweep (`grep -rn getInitials app/src/` returned 2 hits in an admin file neither named in this plan's `files_modified` nor in 52-CONTEXT.md's "Claude's Discretion" note, which only knew of the two public-surface copies)
- **Why not auto-fixed:** Converging it isn't a delete-and-replace — the admin resolve flow's candidate/unresolved-speaker names may not correspond to a persisted `Person` row with structured parts, so wiring it to `derive_initials` needs its own look at what data is actually available at that call site. That is a scope/design question (CLAUDE.md Defect Policy: "whether a newly discovered requirement belongs in this phase, a later phase, or the backlog"), not a correctness bug.
- **Action:** Filed `.planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md` for the operator; left untouched.

---

**Total deviations:** 0 auto-fixed. 1 discovered-and-deferred (scope question, filed as a todo per Defect Policy).
**Impact on plan:** None on this plan's own scope — D-12's stated goal ("one implementation, one place to test") is now true for every public-surface path this phase targets; the admin surface is a separate, pre-existing concern.

## Issues Encountered

**Flaky pre-existing browser test, confirmed not caused by this plan.** `arguments-listing.browser.test.mjs`'s test 5 ("term-scoped empty state") failed once during verification with a vague CDP "Uncaught" error. Reverting this plan's frontend changes via `git stash` and re-running showed the SAME test still flaked (a different subtest, test 4, failed on a subsequent run with the changes restored) — confirming pre-existing CDP/headless-Chromium timing flakiness in this sandbox, not a regression from this plan's code. Two clean back-to-back runs of the full relevant browser suite (11/11 and 9/9 passing) after the investigation confirm this. No code change was made in response; this is the same class of sandbox-scoped flakiness noted in MEMORY.md's Playwright entry.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `derive_initials` and both public `initials`/`speaker_initials` fields are available for any later phase touching speaker payloads (54.1 justice portraits, 55 search) without re-deriving name-parsing logic.
- The admin `ResolveCard.svelte` third splitter is a known, filed, non-blocking item for the operator to schedule.
- Full test suite: 1384 passed, 5 xfailed (baseline was 1366 passed, 5 xfailed — the +18 delta is exactly this plan's new tests, no regressions). Full `*.browser.test.mjs` suite: 11/11 passing.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

All created files verified present on disk (`app/tests/speaker-initials.browser.test.mjs`,
`.planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md`).
All four task commits (`f2d0a24a3`, `4d0b0e637`, `4a0d1a8a0`, `b870f9e97`) verified present
in `git log`. All acceptance criteria re-run and passing (Task 1: 5/5 CLI checks + 67/67
tests; Task 2: 6/6 CLI checks + 146/146 tests across the three targeted files; Task 3: 6/6
CLI checks + 9-then-11/11 browser tests). Plan-level `<verification>` re-run: `pytest -q`
-> 1384 passed, 5 xfailed, 0 failed; `node --test app/tests/*.browser.test.mjs` -> 11/11
pass; `npm run check` -> 0 errors (32 pre-existing warnings); `npm run build` -> exit 0.
Hand check against UI-SPEC scope note: avatar markup, size, font tokens and fallback
rendering are unchanged in both `SpeakerPopover.svelte` and `+page.svelte` — only the value
inside the circle changed.
