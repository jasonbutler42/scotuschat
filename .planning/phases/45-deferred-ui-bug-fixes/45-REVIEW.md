---
phase: 45-deferred-ui-bug-fixes
reviewed: 2026-08-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - api/routers/arguments.py
  - api/services/arguments.py
  - api/services/speakers.py
  - api/tests/test_phase45_popover_boxmodel_contract.py
  - api/tests/test_published_gate.py
  - app/src/lib/components/SpeakerPopover.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-08-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the BUG-01 publish-gate change (`api/routers/arguments.py`, `api/services/arguments.py`, `api/services/speakers.py`, plus the two test files) and the BUG-02 popover box-model revision (`SpeakerPopover.svelte`, the argument-detail `+page.svelte`).

**BUG-01** is implemented correctly for the core threat model: both `get_argument_with_utterances()` and `get_argument_speakers()` now gate on `Argument.published_at.isnot(None)` / `published_at is None`, both short-circuit to `None` after exactly one query for both the "nonexistent" and "unpublished" cases (no timing side-channel), and the router raises the byte-identical `HTTPException(404, "Argument not found")` for both. I confirmed by grep that no admin/authenticated code path calls either service function (the admin router has its own separate query paths in `api/routers/admin.py`), so the admin regression the task description warned about does not occur. The new tests in `test_published_gate.py` correctly assert the predicate text and the absence of a `resolved_at`/clock-based comparison.

**BUG-02** matches its own static contract test file exactly — I diffed the actual source against every assertion in `test_phase45_popover_boxmodel_contract.py` and found no mismatches (dividers count, ternary mutual exclusivity, scrollbar scoping, color token subset, apolitical guard, etc. all hold).

Neither bug fix introduces a Critical/Blocker-level defect. I did find three Warning-level robustness/data-integrity gaps (one pre-existing but directly exercised by this phase's contract, two pre-existing and merely visible in the reviewed files) and three Info-level quality items. Details below.

## Warnings

### WR-01: Removing the outer popover's viewport cap leaves no overflow safety net

**File:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:139-148`
**Issue:** The prior `Popover.Content` style was `max-height: min(560px, 80vh); overflow-y: auto;` — a viewport-bounded safety net for the whole card. The revision removes both properties entirely (confirmed intentional, per the Figma-driven checkpoint and enforced by `test_popover_content_has_no_max_height_or_overflow`), and only the bio paragraph now scrolls, capped at a fixed 150px. Nothing else in the card is capped: the header, birth/death line, tenure list (which can have 2+ rows, each with an optional second "appointed_by/reason_left" line) all render at natural height with no scroll affordance. For a Chief Justice with two tenure entries, a full birth/death line, and an expanded 150px bio, the card can exceed a phone's viewport height with no way to reach the tail of the tenure list — `bits-ui`'s `Popover.Content` positioning (via `customAnchor`) will reposition but does not resize content to fit.
**Fix:** This is a design-approved shape, so I'm not proposing reverting it — but it should be validated against worst-case data (2-tenure Justice, full appointed_by + reason_left, expanded bio) on a short mobile viewport before shipping. If it overflows, consider a `max-height: 90vh` fallback on `Popover.Content` that only engages when total content actually exceeds the viewport, rather than reopening the "whole-card scroll" debate:
```css
/* only as a last-resort safety net, not a replacement for the 150px bio cap */
max-height: 90vh;
overflow-y: auto;
```

### WR-02: `argument_id` has no upper-bound check against the DB column width

**File:** `api/routers/arguments.py:29,49`; `api/services/arguments.py:46-51`; `api/services/speakers.py:139-144`
**Issue:** `argument_id: int` is validated only as "is this a Python int" by FastAPI/Pydantic. The underlying column is `Column(Integer, primary_key=True)` in `api/models/models.py` (Postgres `int4`, 32-bit). A request like `GET /arguments/99999999999/utterances` passes FastAPI's type coercion but will fail deep inside the asyncpg driver when SQLAlchemy tries to bind the out-of-range value to an `int4` parameter, raising an unhandled `OverflowError`/`DataError` that FastAPI turns into a generic 500 — not the uniform 404 contract BUG-01 was built to guarantee for every "argument the caller can't legitimately see" case. This doesn't leak the published/unpublished distinction (both states 500 identically for the same oversized ID), but it is an unhandled-exception path on a public, read-only endpoint, and a stack trace/500 is a worse failure mode than the clean 404 this phase otherwise achieves everywhere else.
**Fix:** Constrain the path parameter explicitly so out-of-range IDs 422 cleanly instead of 500ing:
```python
from fastapi import Path

async def get_utterances(
    argument_id: int = Path(..., ge=1, le=2_147_483_647),
    db: AsyncSession = Depends(get_db),
) -> ArgumentUtterancesResponse:
    ...
```
(same change for `get_speakers`).

### WR-03: Bench/advocate classification has a single point of failure with a silent wrong-label fallback

**File:** `api/services/speakers.py:219-230`
**Issue:** `get_argument_speakers()` decides whether to run the tenure-based title lookup solely from `side == SideEnum.BENCH` (`side` comes from `ArgumentParticipant.side`, Step 4). If that row is ever missing or NULL for a resolved Justice (e.g. a resolve-step data gap), `side` is `None`, the `if side == SideEnum.BENCH` branch is skipped, and the code falls straight into `ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)` → `"Counsel"`. A sitting/former Justice would silently render with an advocate-style role pill and no tenure history is even looked up. Separately, `app/src/routes/.../+page.server.ts` (not in this review's file list, but the consumer of this same payload) derives its own independent `is_bench` flag from `tenure.length > 0` — a second, non-reconciled source of truth for the exact same fact, which can diverge from `side` for the same person without either code path treating the mismatch as an error.
**Fix:** Add a defensive fallback (and/or a log line) so a missing `side` row degrades to the tenure-derived signal instead of a wrong label:
```python
if side == SideEnum.BENCH or (side is None and person.id in date_tenures_by_person):
    role_name = _tenure_role_name(date_tenures_by_person.get(person.id) or [], argued_date)
else:
    role_name = ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)
```

## Info

### IN-01: `get_argument_with_utterances()` docstring not updated for the publish gate

**File:** `api/services/arguments.py:23-44`
**Issue:** The function's docstring still reads "Return argument metadata + latest-run utterances, or None if not found." after BUG-01 changed the function to also return `None` for a published-but-nonexistent-vs-unpublished argument. Only an inline step comment (`# hide unpublished arguments (BUG-01/D-02)` at line 49) documents the new behavior; a reader who only skims the docstring (as `get_argument_speakers()`'s much more thorough docstring update in the same commit shows is the expected standard) would miss it.
**Fix:** Update the summary line to mirror `get_argument_speakers()`'s docstring, e.g. "...or None if not found or not published (BUG-01/D-02)."

### IN-02: Duplicate identical constants in `SpeakerPopover.svelte`

**File:** `app/src/lib/components/SpeakerPopover.svelte:65-68`
**Issue:** `avatarBg` and `sideColor` are computed with the exact same expression (`isBench ? '#94a3b8' : '#93c5fd'`), then used interchangeably. This is dead duplication that could silently drift out of sync if one is edited without the other.
**Fix:**
```ts
const sideColor = isBench ? '#94a3b8' : '#93c5fd';
const avatarBg = sideColor;
```

### IN-03: `TenureRow`/`SpeakerDetail` interfaces duplicated verbatim across two files

**File:** `app/src/lib/components/SpeakerPopover.svelte:2-60`; `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:9-39`
**Issue:** Both files declare byte-for-byte identical `TenureRow` and `SpeakerDetail` interfaces (including the same comments). A future field addition/rename to one (as already happened across Phase 37/39 per the inline history) risks being applied to only one copy.
**Fix:** Extract both interfaces into a shared module (e.g. `$lib/types/speaker.ts`) and import from both call sites.

---

_Reviewed: 2026-08-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
