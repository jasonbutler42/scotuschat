---
phase: 52-justice-identity
plan: 03
subsystem: admin-ui
tags: [fastapi, pydantic, sveltekit, svelte5, admin, identity]

# Dependency graph
requires:
  - phase: 52-01
    provides: "Person.display_name column (migration 0032) and oyez_speaker_id as the load-bearing join key"
provides:
  - "PersonDetail.display_name / PersonDetail.oyez_speaker_id — server-derived, read-only, returned on GET/PATCH responses, never accepted by PersonUpdate or PersonCreateRequest"
  - "api/tests/test_admin_people_schema_readonly.py — proves the 422 refusal through real PATCH requests, not by inspecting model_fields"
  - "Corpus Display Name / Oyez Speaker ID read-only rows in the admin person page's Identity card, between Full Name and Name Parts"
affects: [52-04, 52-05, 54.1]

# Actuals (#2632)
actuals:
  tokens: 3298
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only PersonDetail field precedent (established by full_name) reused verbatim for a second and third field — returned-but-never-accepted, extra=\"forbid\" is the enforcement mechanism, no service-layer guard needed"
    - "Identity-card read-only row markup (label span + explanation span + <output> with aria-labelledby/aria-live) is a reusable shape, not a component — copied verbatim rather than abstracted for two call sites"

key-files:
  created:
    - api/tests/test_admin_people_schema_readonly.py
  modified:
    - api/schemas/admin_people.py
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte

key-decisions:
  - "Both fields read directly off data.person in the Svelte template (not a $derived or top-level const) — the simplest reactive-safe form, matching how full_name is already read at the same call site."

requirements-completed: [JUSTICE-03]

coverage:
  - id: D1
    description: "GET /api/admin/people/{id} returns display_name and oyez_speaker_id; PATCH with either field returns 422; an unrelated writable field still PATCHes successfully"
    requirement: "JUSTICE-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people_schema_readonly.py#test_update_person_rejects_display_name_field"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_schema_readonly.py#test_update_person_rejects_oyez_speaker_id_field"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_schema_readonly.py#test_update_person_writable_field_still_succeeds"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_schema_readonly.py#test_get_person_returns_display_name_and_oyez_speaker_id"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two read-only rows render in the Identity card between Full Name and Name Parts, using the Full Name readout's exact markup/box treatment, with correct empty-state ('Not in corpus', secondary/italic) and populated-state (primary/normal) styling for a corpus-joined justice vs. an advocate or D-04 justice"
    requirement: "JUSTICE-03"
    verification:
      - kind: other
        ref: "grep -c 'Corpus Display Name' — 3 occurrences (label + comment); grep -n 'Not in corpus' — exactly 2, one per row"
        status: pass
      - kind: other
        ref: "npm --prefix app run check — 0 errors, 32 pre-existing warnings (unchanged from baseline)"
        status: pass
      - kind: other
        ref: "npm --prefix app run build — exit 0"
        status: pass
    human_judgment: true
    rationale: "Visual placement, box treatment, and empty/populated color-and-style contrast are carried as the plan's own <verify><human-check> per CLAUDE.md's Testing Policy (frontend behavior verified by the operator's eye, not a static contract test) and this project's end-of-phase human_verify_mode — deferred to the phase UAT batch rather than a mid-flight checkpoint."

duration: 24min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 03: Justice Identity Fields on Admin Person Page Summary

**Two read-only fields — `display_name` and `oyez_speaker_id` — now surface on the admin person page's Identity card, proven unwritable by a real-request 422 test rather than a schema-declaration check.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-25T12:25:00Z
- **Completed:** 2026-09-25T12:49:49Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `PersonDetail.display_name` and `PersonDetail.oyez_speaker_id` return on the admin read path, following the exact `full_name` precedent (server-derived, documented, never on `PersonUpdate`/`PersonCreateRequest`).
- A PATCH carrying either field now returns 422 through `PersonUpdate`'s existing `extra="forbid"` allow-list — no new guard code, the allow-list omission is the whole mechanism.
- `api/tests/test_admin_people_schema_readonly.py` proves the 422 through a real request against the ASGI app (not `model_fields` inspection), plus proves the read path returns both fields and that an unrelated writable field (`bio_text`) still PATCHes successfully.
- The hand-maintained TypeScript `PersonDetail` interface in `+page.server.ts` mirrors both fields as `string | null`.
- Two new `<output>` rows — Corpus Display Name, Oyez Speaker ID — sit in the Identity card between the Full Name readout and the Name Parts inputs, copying the Full Name readout's markup/box treatment verbatim, per the UI-SPEC Layout & Placement Contract and Copywriting Contract exactly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Return both identity fields on the read path, and prove they never reached the write path** - `07e967f06` (feat)
2. **Task 2: Two read-only rows in the Identity card, built from the Full Name readout's own shape** - `85008a51e` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `api/schemas/admin_people.py` - Added `display_name`/`oyez_speaker_id` to `PersonDetail`; extended docstring naming D-09/D-10; `PersonUpdate` untouched.
- `api/tests/test_admin_people_schema_readonly.py` - New test module proving the 422 refusal and the read-path return through real ASGI requests.
- `app/src/routes/admin/people/[id]/+page.server.ts` - Mirrored both fields onto the hand-maintained `PersonDetail` TypeScript interface.
- `app/src/routes/admin/people/[id]/+page.svelte` - Added the two read-only Identity card rows, reading `data.person.display_name` / `data.person.oyez_speaker_id` reactively in the template.

## Decisions Made
- Read both new values directly off `data.person` in the template markup rather than introducing a `$derived` or capturing them into a top-level `const` — matches the existing `data.person.full_name` idiom at the same call site and avoids the stale-prop-capture bug class this codebase has been bitten by once (published-lock, ~two-week bug).

## Deviations from Plan

None - plan executed exactly as written. One self-correction during Task 2: an explanatory code comment happened to contain the literal string "Not in corpus", which would have produced a third grep match against the plan's own acceptance criterion ("no third occurrence"); reworded the comment to "empty-value wording" before committing, so no deviation reached the commit.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- JUSTICE-03 complete. Both identity facts (which name form drives attribution, whether the person is corpus-joined) are now visible and unwritable on the admin person page.
- The Task 2 `<verify><human-check>` (visual placement/treatment on a corpus-joined justice and on an advocate/D-04 justice) is deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase` — not yet observed by the operator.
- No blockers for 52-04 or 52-05.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

- FOUND: `.planning/phases/52-justice-identity/52-03-SUMMARY.md`
- FOUND: `api/tests/test_admin_people_schema_readonly.py`
- FOUND commit: `07e967f06` (Task 1)
- FOUND commit: `85008a51e` (Task 2)
- `pytest api/tests -q`: 930 passed, 0 failed
- `npm --prefix app run check`: 0 errors, 32 pre-existing warnings (unchanged)
- `npm --prefix app run build`: exit 0
