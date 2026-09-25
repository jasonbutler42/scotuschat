---
phase: 52-justice-identity
plan: 06
subsystem: identity
tags: [pydantic, sqlalchemy, svelte5, avatar-initials, structural-ban-sweep]

# Dependency graph
requires:
  - phase: 52-02
    provides: "api.domain.person_names.derive_initials — the single avatar-initials derivation, structured-parts-first with a D-13 legacy fallback over full_name"
provides:
  - "ResolveRow.initials — the admin Resolve card's avatar glyph, computed server-side by the same derive_initials call 52-02 established for SpeakerPopoverEntry and UtteranceResponse"
  - "D-12 closed in its original, unscoped form: exactly one initials implementation exists in the codebase, repository-wide"
affects: [54.1]

# Actuals (#2632)
actuals:
  tokens: 3736
  tasks: 2
  commits: 2
  plan_head_before: 4d8772cd8be535394883606ddcf6082712339ed5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-derivation-call-site discipline extended to a third payload: derive_initials is called once, before the bench/advocate branch in list_resolve_rows_for_job's loop, and the result is reused in both dict literals — not called once per branch."

key-files:
  created:
    - api/tests/test_admin_people_resolve_initials.py
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - app/src/lib/admin/ResolveCard.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts

key-decisions:
  - "list_resolve_rows_for_job's SELECT extended with Person.first_name/last_name/name_suffix (previously only full_name/photo_url) so the service has structured parts in hand at the exact point 52-02's SpeakerPopoverEntry/UtteranceResponse pattern expects them — no second query."
  - "The null-initials case gets no client-side rendering branch: person_id null implies full_name null too (both come from the same outer join), so the existing {#if fullName}...{:else}—{/if} guard already covers it. Rendering {initials} directly (no ?? '?' fallback) keeps the fix a pure delete-and-wire, per the plan's explicit prohibition on a client-side helper for the unresolved case."

requirements-completed: [JUSTICE-06]

coverage:
  - id: D1
    description: "ResolveRow carries a server-computed, read-only initials field derived through derive_initials — not a second implementation, not a client-side port of the D-13 fallback"
    requirement: JUSTICE-06
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people_resolve_initials.py::test_initials_from_structured_parts_ignores_suffix"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_resolve_initials.py::test_initials_from_full_name_when_no_structured_parts"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_resolve_initials.py::test_initials_null_for_unresolved_row"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_resolve_initials.py::test_resolve_row_schema_carries_initials_field"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_resolve_initials.py::test_resolve_row_update_schema_has_no_initials_field"
        status: pass
      - kind: other
        ref: "grep -c 'derive_initials' api/services/admin_people.py -> 2 (one import, one call site)"
        status: pass
      - kind: other
        ref: "grep -rn 'def derive_initials|def getInitials|def get_initials' api/ pipeline/ | wc -l -> 1"
        status: pass
    human_judgment: false
  - id: D2
    description: "The third client-side splitter (ResolveCard.svelte's getInitials, found during 52-02's structural ban sweep) is deleted; personDisplay takes initials as a parameter and renders it; a suffixed name (John Marshall Harlan, II) shows JH in the admin Resolve card"
    requirement: JUSTICE-06
    verification:
      - kind: other
        ref: "grep -c getInitials app/src/lib/admin/ResolveCard.svelte -> 0"
        status: pass
      - kind: other
        ref: "grep -rn 'getInitials|get_initials' app/src/ | wc -l -> 0"
        status: pass
      - kind: other
        ref: "grep -rnE 'split\\(/\\\\s\\+/\\)' app/src/ | wc -l -> 0"
        status: pass
      - kind: other
        ref: "npm --prefix app run check -> 0 errors, 32 warnings (pre-existing baseline, no increase)"
        status: pass
      - kind: other
        ref: "npm --prefix app run build -> exit 0"
        status: pass
    human_judgment: true
    rationale: "The admin resolve surface sits behind session auth with no browser harness in this repo, so the rendered JH-for-Harlan result and the unresolved-row's unchanged empty avatar are carried as a <human-check> per CLAUDE.md's Testing Policy (no static source-text contract test for rendered behavior) and harvested into the phase UAT batch under workflow.human_verify_mode: end-of-phase, exactly as the plan specifies."

duration: 10min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 06: Justice Identity — Admin Resolve Card Initials Summary

**The last surviving client-side initials splitter (`ResolveCard.svelte`'s `getInitials`) is deleted; the admin Resolve card's avatar now renders `ResolveRow.initials`, computed server-side by the same `derive_initials` call 52-02 wired into the two public speaker payloads — closing D-12 in its original, repository-wide form.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-09-25T14:39:58Z (approx., per STATE.md session marker)
- **Completed:** 2026-09-25T14:49:53Z
- **Tasks:** 2
- **Files modified:** 5 (4 modified, 1 created)

## Accomplishments
- `ResolveRow.initials: Optional[str] = None` — a server-derived, read-only field, documented in the same voice as the schema's other read-only fields, never added to any write schema on this surface (`ResolveRowUpdate` has no `initials` field, confirmed by a dedicated test)
- `list_resolve_rows_for_job`'s participant `SELECT` extended with `Person.first_name`/`last_name`/`name_suffix` (previously only `full_name`/`photo_url`), and `derive_initials` called exactly once per row — one call site in source text, reused across the bench and advocate dict branches, matching 52-02's single-call-site discipline
- `api/tests/test_admin_people_resolve_initials.py`: 5 tests covering the schema shape, the write-schema absence, a suffixed person (`John Marshall Harlan, II` -> `JH`, not `JI`), the `full_name`-only fallback case, and the unresolved-row null case — asserted against `list_resolve_rows_for_job`'s real output, not a re-call of `derive_initials`
- `ResolveCard.svelte`'s `getInitials` function deleted outright; `personDisplay`'s snippet signature gained an `initials` parameter, its avatar span renders that parameter directly, and its single `{@render personDisplay(...)}` call site passes `row.initials`
- A repository-wide sweep now returns exactly one initials implementation: `grep -rn 'def derive_initials\|def getInitials\|def get_initials' api/ pipeline/` and `grep -rn 'getInitials\|get_initials' app/src/` both return zero extra hits — D-12's original, unscoped form is satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: Ship server-computed initials on ResolveRow, from the one existing function** - `7d6c56bc7` (feat)
2. **Task 2: Delete the third splitter and render the server value** - `9dae1ce51` (feat)

## Files Created/Modified
- `api/schemas/admin_people.py` - `ResolveRow.initials: Optional[str] = None`, documented read-only
- `api/services/admin_people.py` - extended `SELECT`, single `derive_initials` call site per row
- `api/tests/test_admin_people_resolve_initials.py` - 5 new tests (schema, write-schema absence, suffix, fallback, null)
- `app/src/lib/admin/ResolveCard.svelte` - `getInitials` deleted; `ResolveRow` interface, `personDisplay` snippet and its call site all carry `initials`
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - hand-mirrored `ResolveRow` interface gained `initials` (deviation, see below)

## Decisions Made
See `key-decisions` in frontmatter. The most consequential: no client-side fallback was added for a null `initials` — the unresolved-row case coincides exactly with a null `full_name`, which the surrounding `{#if fullName}` guard already routes to the existing empty-avatar path, so `{initials}` renders directly with no `?? '?'` defensive code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated a second hand-mirrored `ResolveRow` TypeScript interface not named in the plan's `files_modified`**
- **Found during:** Task 2 (wiring `ResolveCard.svelte`'s `initials` prop)
- **Issue:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` declares its own local `ResolveRow` interface (this repo has no shared-type codegen from FastAPI, per 52-PATTERNS.md's documented Pitfall 5) for the `load` function's `resolveRows: ResolveRow[]` return type. Without the `initials` field, this type would silently lack it — `resolveRowsRes.json()` returns `any`, so the mismatch would not surface until the value was passed to `<ResolveCard resolveRows={data.resolveRows} />`, whose own `ResolveRow` interface (updated in this task) makes `initials` a required field. Left unfixed, `npm run check` would report a missing-property type error.
- **Fix:** Added `initials: string | null;` to the same position (immediately after `photo_url`) in this second interface, mirroring the Pydantic field precedent's placement.
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
- **Verification:** `npm run check` reports 0 errors, 32 warnings (unchanged pre-existing baseline)
- **Committed in:** `9dae1ce51` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking type-check gap).
**Impact on plan:** Necessary for `npm run check`/`npm run build` to pass as the plan's own acceptance criteria require. No scope creep — this is the same "hand-mirrored interface" class of edit the plan already named for `ResolveCard.svelte` itself, just at a second occurrence the plan's read_first list didn't enumerate.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- D-12 is now satisfiable in its original, unscoped form: `grep -rn 'def derive_initials\|def getInitials\|def get_initials' api/ pipeline/` returns exactly one result (`api/domain/person_names.py`), and no `.svelte`/`.ts` file computes initials from a name string anywhere in the repo.
- `.planning/todos/pending/2026-09-25-admin-resolvecard-third-initials-implementation.md` (filed by 52-02) is now resolved by this plan and can be closed/archived by the operator.
- The Task 2 `<human-check>` (confirm `JH` renders for a suffixed bench row and the unresolved-row avatar is unchanged) is carried into the phase-end UAT batch per `workflow.human_verify_mode: end-of-phase` — not yet observed in a browser, since the admin surface has no automated harness.
- Full `api/tests` suite: 947 passed, 0 failed (targeted new-test run: 5 passed). `npm run check`: 0 errors, 32 pre-existing warnings (no increase). `npm run build`: exit 0.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

Verified `api/tests/test_admin_people_resolve_initials.py` exists on disk. Verified both task
commits (`7d6c56bc7`, `9dae1ce51`) present in `git log`. Re-ran all acceptance criteria:
Task 1 — `grep -n 'initials' api/schemas/admin_people.py` shows the field; `grep -c
'derive_initials' api/services/admin_people.py` -> 2; `grep -rn 'def derive_initials\|def
getInitials\|def get_initials' api/ pipeline/ | wc -l` -> 1; targeted test file 5/5 passing.
Task 2 — `grep -c getInitials app/src/lib/admin/ResolveCard.svelte` -> 0; `grep -rn
'getInitials\|get_initials' app/src/ | wc -l` -> 0; `grep -rnE "split\(/\\\\s\+/\)" app/src/
| wc -l` -> 0; `grep -n initials app/src/lib/admin/ResolveCard.svelte` shows the interface
field, the snippet parameter and the render site, no function definition. Plan-level
`<verification>` re-run: full-repo sweep for an initials implementation returns exactly one
result. `pytest api/tests -q` -> 947 passed, 0 failed. `npm run check` -> 0 errors, 32
warnings (baseline). `npm run build` -> exit 0.
