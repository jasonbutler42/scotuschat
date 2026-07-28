---
phase: 39-bench-popover-additional-context-data
plan: 05
subsystem: ui
tags: [svelte, svelte5-runes, sveltekit, bits-ui, popover, apolitical-framing]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    plan: "04"
    provides: "Widened GET /arguments/{id}/speakers contract — per-tenure appointed_by/appointing_president_party, person-level birthdate/death_date/bio_text, retired top-level appointing_president"
provides:
  - "Rebuilt SpeakerPopover.svelte: header row + full-width stacked sections (role pill, birth/death line, advocate descriptor slot, clamped bio with Read more/Show less, per-tenure 3-line blocks)"
  - "UTC-pinned formatShort() date helper for the compact birth/death line format"
  - "Argument page's TenureRow/SpeakerDetail interfaces widened to match the component and the API contract"
  - "max-height/overflow-y scroll backstop on Popover.Content for the rare 3+-tenure Justice"
affects: [39-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bio clamp/expand toggle visibility driven by a mount-time $effect measuring bioEl.scrollHeight > bioEl.clientHeight + 1, following the file's existing showInitials $state idiom — no character-length threshold fallback was needed"
    - "One neutral style string per line type, applied unconditionally to every rendered value (birth/death, appointed_by+party, reason_left) — no per-value branching on party or reason, matching the apolitical framing hard constraint"

key-files:
  created: []
  modified:
    - app/src/lib/components/SpeakerPopover.svelte
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte

key-decisions:
  - "Used the scrollHeight/clientHeight measurement approach for bio-toggle visibility (39-UI-SPEC.md's first option), not the character-length threshold fallback — measurement proved reliable via bind:this + $effect, so no fallback was needed."
  - "Card container changed from flex-row to display:block (39-UI-SPEC.md's 'or a block' option) rather than flex-column, since each stacked section already carries its own margin-top and a block container avoids double-gap composition with those margins."

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "Birth/death line renders 'b. {short date} · d. {short date}', omits the death half when null, omits the whole line when both are null"
    requirement: "PUB-04"
    verification: []
    human_judgment: true
    rationale: "No frontend test framework exists in this repo (no vitest/testing-library, confirmed in 39-RESEARCH.md); visual/layout correctness is verified only by manual UAT, deferred to Plan 39-06 per this plan's own <verification> section."
  - id: D2
    description: "One 3-line block per tenure: office+dates, then appointed_by+party (each half independently omittable), then reason_left — each line omitted entirely when its data is null"
    requirement: "PUB-04"
    verification: []
    human_judgment: true
    rationale: "Same as D1 — no automated frontend test framework; manual UAT deferred to Plan 39-06."
  - id: D3
    description: "Bio text renders 3-line-clamped with a working Read more/Show less toggle; toggle is absent for bios that fit; absent entirely when bio_text is null"
    requirement: "PUB-04"
    verification: []
    human_judgment: true
    rationale: "Toggle-visibility logic (scrollHeight measurement) is structurally verifiable by code inspection, but genuine visual clamping/toggle behavior requires manual UAT in a real browser, deferred to Plan 39-06."
  - id: D4
    description: "Advocate popover shows 'Coming soon' descriptor beneath the role pill and no tenure section"
    requirement: "PUB-04"
    verification: []
    human_judgment: true
    rationale: "Manual UAT deferred to Plan 39-06; the literal string and the isBench-gated {#if} guard are inspectable in source but visual placement needs human confirmation."
  - id: D5
    description: "Every added line renders in one neutral style per line type — no color/weight/size/ordering/emphasis difference by party value or reason value"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "grep -Eq 'Republican|Democratic|Federalist|Whig|Democratic-Republican' app/src/lib/components/SpeakerPopover.svelte (expect no match)"
        status: pass
      - kind: other
        ref: "grep -Eq \"reason_left ===|reason_left ==|appointing_president_party ===\" app/src/lib/components/SpeakerPopover.svelte (expect no match)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Popover content that exceeds a sane height scrolls inside Popover.Content rather than extending off-screen; no tenure row is ever hidden"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "grep -q 'max-height: min(560px, 80vh)' and grep -q 'overflow-y: auto' on the argument page (both pass)"
        status: pass
    human_judgment: true
    rationale: "The CSS backstop is mechanically present and grep-verified, but confirming it actually prevents off-screen extension for a real 3+-tenure Justice requires manual UAT (39-UI-SPEC.md's documented 🧪 backstop, no automated coverage exists in this repo)."
  - id: D7
    description: "A stored office or reason value outside the canonical vocabulary omits its line rather than crashing or blanking the whole popover"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "officeTitle()/reasonLeftTitle() unchanged degrade-to-empty-string helpers, unit-verifiable by inspection; both feed {#if}-guarded lines"
        status: pass
    human_judgment: false
  - id: D8
    description: "Date rendering is timezone-independent (an ISO date renders as the same calendar day regardless of local UTC offset)"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "grep -q \"timeZone: 'UTC'\" app/src/lib/components/SpeakerPopover.svelte"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 05: Rebuild the popover card and render the widened speaker data Summary

**Rebuilt `SpeakerPopover.svelte` from a narrow flex-row card into a header-row-plus-stacked-sections layout that renders every field Plan 39-04 added (birth/death line, per-tenure appointed-by/party, clamped bio with toggle, advocate descriptor slot), and widened the argument page's speaker types plus a scroll backstop on the popover wrapper to match.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments

- `SpeakerPopover.svelte` restructured from "avatar beside a narrow text column" into a header row (avatar + name + role pill) followed by full-width stacked sections, per 39-UI-SPEC.md's layout contract.
- Added a UTC-pinned `formatShort()` date helper (`Intl.DateTimeFormat` with `timeZone: 'UTC'`) so the birth/death line renders the same calendar day regardless of the browser's local offset — every date in this payload is a date-only DB value with no time component.
- Birth/death line renders `b. {date}` and, when known, ` · d. {date}`, each half independently omittable, whole line omitted when both `birthdate`/`death_date` are null.
- Bio paragraph clamps to 3 lines with a measurement-driven `Read more`/`Show less` toggle (`aria-expanded`), rendered only when the text genuinely overflows; omitted entirely when `bio_text` is null.
- Per-tenure block now renders up to 3 lines: office+dates (unchanged), `{appointed_by}` optionally followed by ` · {appointing_president_party}`, and `{reasonLeftTitle(reason_left)}` — each line independently omitted when its underlying value is null.
- Advocate descriptor slot added: an unconditional italic "Coming soon" paragraph beneath the role pill for every non-bench speaker (D-16) — a real UI slot, not a fake data placeholder.
- Retired `SpeakerDetail.appointing_president` from both the component's and the argument page's TypeScript interfaces, matching Plan 39-04's API-side retirement (promote, not add-alongside — D-13).
- Card widened to `min-width: 300px; max-width: 400px` (from 280/360); the `@media (max-width: 767px)` column-stacking override deleted entirely — the header row now always stays horizontal.
- Argument page's `Popover.Content` wrapper gained `max-height: min(560px, 80vh); overflow-y: auto;` alongside its existing `z-index: 50` — a scroll backstop for the rare 3+-tenure Justice, applied to the wrapper (not `.popover-card`) so the card's own border/padding stay intact and no tenure row is ever hidden.
- `+page.server.ts` was deliberately left untouched — confirmed by reading it and by a `git diff --quiet` gate: its `RawSpeaker` index signature and `{ ...s, photo_url_full, is_bench }` spread already forward every new API key without modification.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild the popover card layout and render every new field** - `3842ba57` (feat)
2. **Task 2: Update the argument page's speaker types and add the popover height backstop** - `f8647b81` (feat)

## Files Created/Modified

- `app/src/lib/components/SpeakerPopover.svelte` - Rewritten template: header row (avatar/name/pill) + stacked full-width sections (birth/death line, advocate descriptor, clamped bio + toggle, tenure list); widened card; `formatShort()`; `bioExpanded`/`bioOverflows`/`bioEl` state; retired `appointing_president` from `SpeakerDetail`; added `appointed_by`/`appointing_president_party` to `TenureRow` and `birthdate`/`death_date`/`bio_text` to `SpeakerDetail`.
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` - `TenureRow`/`SpeakerDetail` interfaces widened to match the component (required for the `speakersMap` `$derived` cast to type-check); `Popover.Content`'s `style` attribute extended with the scroll backstop.

## Decisions Made

- **Bio-toggle visibility mechanism:** used the `scrollHeight > clientHeight + 1` measurement approach (39-UI-SPEC.md's primary option) via `bind:this={bioEl}` and a mount-time `$effect`, not the character-length threshold fallback — measurement worked reliably against the lazily-mounted popover content, so no fallback threshold was needed or recorded.
- **`.popover-card` container display mode:** changed from `flex-row` to `display: block` (39-UI-SPEC.md explicitly permits "vertical flex or a block") rather than `flex-column` — every stacked section already carries its own `margin-top`, so a block container avoids composing double gaps with a flex `gap` property.
- Followed the plan's styling convention exactly: literal hex values and inline `style="..."` attributes throughout, no `var(--color-*)` introduced mid-file, matching the rest of this codebase's zero-Tailwind-utility-class convention.

## Deviations from Plan

None - plan executed exactly as written. Both tasks completed without requiring an auto-fix; the only `npm run check` finding along the way was the exact type-mismatch error the plan's own Task 1 acceptance criteria anticipated ("no new errors versus the pre-task baseline" — the interim error was the page's stale `SpeakerDetail` type not yet matching the rewritten component, resolved by Task 2 as designed) and one pre-existing `state_referenced_locally` warning at the same line/construct that existed in the file before this plan (confirmed via `git show HEAD:...` before editing).

## Verification Results

- `cd app && npm run check`: **0 errors, 34 warnings** (identical warning count to the codebase's pre-existing baseline; the two speaker-related interim states — 1 error after Task 1 only, 0 errors after Task 2 — matched the plan's own expected progression).
- `grep -o 'font-size:[^;]*' app/src/lib/components/SpeakerPopover.svelte | sort -u` → `12px, 13px, 14px, 16px, 18px` (18px is the pre-existing avatar-initials size; exactly the approved four-size scale plus that one carve-out, matching 39-UI-SPEC.md Typography).
- `grep -o 'font-weight:[^;]*' app/src/lib/components/SpeakerPopover.svelte | sort -u` → `400, 600` only.
- `grep -Ec 'N/A|Unknown|No bio' app/src/lib/components/SpeakerPopover.svelte` → 1 match, but it is a source-code comment ("no 'No bio available' filler") documenting the omission rule, not rendered filler copy. No filler placeholder text is rendered anywhere in the component.
- `grep -Ec 'href=|Edit person' app/src/lib/components/SpeakerPopover.svelte` → 0. No edit affordance was added (correctly deferred to backlog item 999.9, D-17).
- `grep -c '{@html' app/src/lib/components/SpeakerPopover.svelte` → 0 (T-39-18 mitigation intact — all interpolation is Svelte's default-escaped `{value}` text binding).
- Interface field-set diff (Task 2 acceptance criterion): the component's and the argument page's `TenureRow` interfaces declare an identical field set — `office`, `start_date`, `end_date`, `reason_left`, `appointed_by`, `appointing_president_party` — differing only in comment wording (the page's comments note formal-title projection happens in the component, matching that file's pre-existing convention).
- `git diff --quiet -- 'app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts'` → exits 0, confirmed untouched.
- `./.venv/Scripts/python.exe -m pytest` (full suite, run from WSL against the Windows venv): **756 passed, 5 xfailed, 4 errors**. The 4 errors are all in `api/tests/test_phase38_people_ui_contract.py`'s node-driver tests, failing on a pre-existing Windows-path bug (`ENOENT` on a mangled `C:\...\workspacescotuschatprojectapi\tests\...` path) already documented and left undisturbed at Phase 38 Plan 10 (STATE.md: "38-UAT.md's pre-existing test_phase38_people_ui_contract.py node-driver failure was left undisturbed and only noted, per plan scope"). This plan touches no Python files, so this pre-existing, already-documented failure is not a regression from this plan's changes.

## Known Stubs

| File | Reason |
|------|--------|
| `app/src/lib/components/SpeakerPopover.svelte` (advocate descriptor slot) | Renders the literal string "Coming soon" for every advocate speaker. This is an intentional placeholder per 39-CONTEXT.md D-16 and 39-UI-SPEC.md §Advocate descriptor placeholder — the real per-advocate descriptor data has no extraction pipeline yet; the slot exists to validate layout/spacing now. Logged to `.planning/WINDOWS.md` (entry id 1, kind `stub`, phase 39) per the broken-windows ledger process; resolution is a future phase that builds the extraction pipeline, not this plan. |

## Issues Encountered

None beyond the pre-existing pytest node-driver issue documented above under Verification Results, which is out of this plan's scope (no Python changes).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The public popover now renders every field Plan 39-04's API contract widening exposed, for both bench and advocate speakers, with omission-on-null discipline and uniform apolitical treatment.
- Plan 39-06 owns the manual UAT: visual verification of both card types, the multi-tenure scroll backstop against a real 2+-tenure Justice (e.g. Rehnquist), and the bio expand/collapse toggle in a real browser — this repo has no frontend test framework, so no automated substitute exists for any of D1-D4/D6 above.
- No blockers. `npm run check` is clean (0 errors) and the full Python test suite shows no regression from this plan.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*

## Self-Check: PASSED

- `app/src/lib/components/SpeakerPopover.svelte` — FOUND
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — FOUND
- `.planning/phases/39-bench-popover-additional-context-data/39-05-SUMMARY.md` — FOUND
- Commit `3842ba57` — FOUND in `git log --oneline --all`
- Commit `f8647b81` — FOUND in `git log --oneline --all`
- Commit `44302f62` — FOUND in `git log --oneline --all`
