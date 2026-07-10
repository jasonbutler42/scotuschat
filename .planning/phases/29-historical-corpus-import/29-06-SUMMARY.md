---
phase: 29-historical-corpus-import
plan: 06
subsystem: ui
tags: [sveltekit, fastapi, attribution, licensing, ccbyunc]

# Dependency graph
requires:
  - phase: 29-01
    provides: Migration adding Argument.oyez_transcript_id column
provides:
  - Static /attributions page crediting Oyez.org, Cornell ConvoKit, and SCDB with the CC BY-NC 4.0 license fact
  - Per-argument attribution note gated server-side to corpus-sourced arguments (oyez_transcript_id non-null)
  - oyez_transcript_id surfaced on the public argument payload (ArgumentMetadataResponse)
  - Public TopNav "Attributions" entry point
  - README.md credits section
affects: [29-04, 29-05, historical-corpus-import-importer]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-side attribution gating: +page.server.ts derives a boolean (is_corpus_sourced) from a backend field so the browser never decides visibility from raw data — mirrors Architecture Rule 2 (FASTAPI_BASE_URL never reaches the client)"
    - "Quiet apolitical house tone for metadata notes: 13px muted caption, no colored badge, no icon, just text + an existing '→' link convention"

key-files:
  created:
    - app/src/routes/attributions/+page.svelte
    - api/tests/test_argument_oyez_field.py
    - README.md
  modified:
    - api/schemas/utterance.py
    - api/services/arguments.py
    - app/src/lib/components/TopNav.svelte
    - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte

key-decisions:
  - "oyez_transcript_id is the only corpus-sourced signal added to the public payload — no win_side/votes_side/outcome data, preserving the apolitical constraint on the public surface (T-29-02)"
  - "Per-argument note visibility computed in +page.server.ts, not in browser code (T-29-11)"
  - "D-25 (Oyez CC BY-NC 4.0 vs. monetization tension) is surfaced publicly via this page's license fact but intentionally not resolved here — recorded in PROJECT.md Constraints during discuss-phase"

patterns-established:
  - "Attribution/licensing pages for third-party data sources live at a static top-level route with no server load function when the content requires no per-request data"

requirements-completed: [CORPUS-09, CORPUS-10]

coverage:
  - id: D1
    description: "oyez_transcript_id field surfaced on the public argument payload (ArgumentMetadataResponse + utterances service dict)"
    requirement: "CORPUS-09"
    verification:
      - kind: unit
        ref: "api/tests/test_argument_oyez_field.py#test_argument_metadata_response_has_oyez_transcript_id"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_oyez_field.py#test_utterances_payload_includes_oyez_transcript_id"
        status: unknown
    human_judgment: false
    rationale: "The live-DB integration test skips in this environment via the established _db_configured() pattern rather than failing; the schema test alone proves the field contract deterministically"
  - id: D2
    description: "Static /attributions page with three credit blocks (Oyez.org, Cornell ConvoKit, SCDB) and the CC BY-NC 4.0 license callout, exact UI-SPEC copy/styling"
    requirement: "CORPUS-10"
    verification: []
    human_judgment: true
    rationale: "Visual/copy fidelity to UI-SPEC requires human eyes; confirmed via the Task 4 checkpoint (approved)"
  - id: D3
    description: "Public TopNav 'Attributions' link (after Cases, before Admin) and README.md credits section"
    requirement: "CORPUS-10"
    verification: []
    human_judgment: true
    rationale: "Confirmed via the Task 4 checkpoint (approved) alongside D2"
  - id: D4
    description: "Per-argument attribution note gated server-side, present only on corpus-sourced arguments and absent on PDF-ingested arguments"
    requirement: "CORPUS-10"
    verification: []
    human_judgment: true
    rationale: "Conditional rendering across two argument types (corpus-sourced vs. PDF-ingested) requires human visual confirmation; confirmed via the Task 4 checkpoint (approved) using a temporary dev-DB test value, since reverted"

duration: ~7min (Tasks 1-3) + checkpoint wait + 5min (wrap-up)
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 06: Attribution & Licensing Surfaces Summary

**Static /attributions page (Oyez.org/ConvoKit/SCDB credits + CC BY-NC 4.0 callout), a server-gated per-argument attribution note, TopNav entry point, and README credit — clearing the D-26 gate before any corpus-imported argument can go live**

## Performance

- **Duration:** ~12 min execution across two agent sessions (Tasks 1-3 autonomous, Task 4 human-verify checkpoint, then wrap-up)
- **Started:** 2026-07-09T18:26:16-05:00 (first task commit)
- **Completed:** 2026-07-10T11:12:59Z
- **Tasks:** 4 (3 auto + 1 checkpoint)
- **Files modified:** 8

## Accomplishments
- Surfaced `oyez_transcript_id` on the public argument payload (`ArgumentMetadataResponse` + the utterances service dict) as the single backend signal for corpus-sourced detection — no outcome/vote data added, preserving the apolitical public-surface constraint
- Built the static `/attributions` page with the three required credit blocks (Oyez.org, Cornell ConvoKit with its two academic citations, SCDB) and the CC BY-NC 4.0 license callout, using the codebase's existing inline-style convention (no shadcn/Tailwind utilities)
- Added a public TopNav "Attributions" link and a README.md credits section
- Added a per-argument attribution note, gated entirely server-side in `+page.server.ts` via a new `is_corpus_sourced` boolean, rendering only on corpus-sourced arguments and linking to `/attributions`
- Human visual verification (Task 4 checkpoint) approved all of the above with no issues found

## Task Commits

Each task was committed atomically:

1. **Task 1: Surface oyez_transcript_id on the public argument payload** - `ed17cc8e` (feat)
2. **Task 2: Static Attributions/License page + TopNav link + README credit** - `0043ed6a` (feat)
3. **Task 3: Per-argument attribution note, server-gated to corpus-sourced arguments** - `4342f090` (feat)
4. **Task 4: Visual verification checkpoint** - no code commit (human-verify only); resolved "approved"

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `api/schemas/utterance.py` - Added `oyez_transcript_id: str | None = None` to `ArgumentMetadataResponse`
- `api/services/arguments.py` - Added `"oyez_transcript_id"` key to the argument dict returned by the utterances service
- `api/tests/test_argument_oyez_field.py` - Schema-field test (DB-independent) + live-DB payload test
- `app/src/routes/attributions/+page.svelte` - Static Attributions & Licensing page
- `app/src/lib/components/TopNav.svelte` - Added "Attributions" link to the public variant
- `README.md` - Created with an Attribution/Credits section
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` - Derives `is_corpus_sourced` from `oyez_transcript_id`
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` - Renders the conditional attribution note

## Decisions Made
- Only `oyez_transcript_id` crosses into the public payload — no win_side/votes_side/scdb_docket_id — keeping the apolitical constraint intact on the public surface (T-29-02)
- Note visibility computed entirely in `+page.server.ts`, never in browser code, per Architecture Rule 2 (T-29-11)
- D-25's Oyez NonCommercial-license vs. monetization tension is surfaced (the CC BY-NC 4.0 fact is now public) but deliberately not resolved by this plan — that business/legal call was already logged in PROJECT.md's Constraints table during discuss-phase and remains open

## Deviations from Plan

### Auto-fixed Issues

None - Tasks 1-3 executed exactly as written.

### Checkpoint-Adjacent Note (not a deviation from plan scope, but tracked for audit clarity)

To perform the Task 4 human visual verification, the prior agent session temporarily set `Argument.id=74`'s `oyez_transcript_id` to a throwaway dev-DB value (`'TEST-VERIFY-13127'`) via a direct `UPDATE`, since the real corpus importer (Plans 29-04/29-05) has not landed yet and no genuinely corpus-sourced argument exists in the dev DB to inspect. This was **not** a migration, seed, or code change — it was a manual dev-DB data mutation solely to produce a page shaped like the target state for visual inspection.

- **Reverted during this wrap-up session:** `Argument.id=74`'s `oyez_transcript_id` set back to `NULL`, confirmed via direct query (before: `'TEST-VERIFY-13127'`, after: `None`). No migration or code artifact was involved in either the original set or this revert; the dev database is now clean of the stale fake value.

**Total deviations:** 0 auto-fixed. One dev-DB-only test-data revert (not a code deviation).
**Impact on plan:** None on shipped code. Dev DB state fully restored to pre-verification condition.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The D-26 attribution gate is now cleared: Plans 29-04/29-05 (the ConvoKit importer) can publish corpus-sourced arguments without violating the CC BY-NC 4.0 attribution obligation, since the note (Task 3) and the public credit page (Task 2) both exist and both key off the same `oyez_transcript_id` field this plan added (Task 1).
- No blockers. The dev-DB test value used for Task 4's visual check has been reverted to `NULL`; the first *real* corpus-sourced argument will come from the actual importer, not a manual test row.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: app/src/routes/attributions/+page.svelte
- FOUND: api/tests/test_argument_oyez_field.py
- FOUND: README.md
- FOUND: .planning/phases/29-historical-corpus-import/29-06-SUMMARY.md
- FOUND: commit ed17cc8e
- FOUND: commit 0043ed6a
- FOUND: commit 4342f090
