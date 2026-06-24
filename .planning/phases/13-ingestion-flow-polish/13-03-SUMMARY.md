---
phase: 13-ingestion-flow-polish
plan: "03"
subsystem: frontend
status: partial
tags: [svelte, combobox, polling, badge, ux, accessibility]
requires: []
provides: [lastKnownStep-fallback, custom-combobox]
affects: [job-detail-page]
tech_stack:
  added: []
  patterns: [svelte-action-outside-click, svelte5-runes-combobox]
key_files:
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
decisions:
  - "lastKnownStep $state declared outside the poll $effect; updated inside setInterval on non-null current_step; effectiveJob spreads in the fallback at the stepStatus call site"
  - "comboOutsideClick is a Svelte action (not a bare $effect) so each combobox instance registers and cleans up its own document listener independently"
  - "filteredCandidates is a {@const $derived} expression inside the #each loop rather than a top-level $derived, because candidates are per-row and keyed by rowKey"
  - "Combobox always shows dropdown on focus (not only when query length > 0) per UI-SPEC open/close rules; matches Interaction State Map row 'Correcting, empty query'"
  - "comboHighlight index includes filteredCandidates.length as the sentinel for the Add new person item, so Up/Down wraps cleanly"
metrics:
  duration: "~3 minutes"
  completed: 2026-06-24
  task_count: 2
  file_count: 1
---

# Phase 13 Plan 03: Step Badge Fallback + Custom Combobox Summary

**One-liner:** `lastKnownStep` $state fallback keeps Running badge stable during null `current_step` transitions; custom Svelte 5 Runes combobox (no dep) replaces the browser-inconsistent native datalist typeahead.

**Status:** PARTIAL — Tasks 1 and 2 complete and committed; Task 3 (human-verify checkpoint) is pending operator review.

---

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | PIPE-18: lastKnownStep fallback + 1s poll interval + console.debug diagnostic | 7ddc157 |
| 2 | PIPE-19: custom Svelte combobox replacing native datalist | 63118c6 |

---

## What Was Built

### Task 1 — PIPE-18: Step Badge Null-Transition Fallback (7ddc157)

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`

Three changes:

1. **`lastKnownStep` $state** — declared outside the `$effect` poll loop, initialized from `data.job.current_step ?? null`. Tracks the most recent non-null `current_step` so the UI can fall back to it during transitions.

2. **Poll loop updates + diagnostic log** — inside the `setInterval` callback (after `invalidateAll()`), `lastKnownStep` is assigned when `data.job.current_step` is non-null. A `console.debug('[poll]', { status, current_step })` call remains in place for live diagnostics (D-02).

3. **`effectiveJob` at the call site** — the `{#each STEP_ORDER}` block now computes `effectiveJob` using a spread that substitutes `lastKnownStep` for `current_step` when `status === 'running'` and `current_step === null`. This is passed to `stepStatus()` instead of `data.job` directly. The `failed`/`paused`/`completed` branches of `stepStatus()` are unchanged.

4. **Poll interval** — `setInterval` delay changed from `2500` to `1000`. The `TERMINAL` short-circuit (`completed`/`failed`/`paused`) is unchanged.

### Task 2 — PIPE-19: Custom Svelte Combobox (63118c6)

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`

Replaced the `<input list> + <datalist>` block inside `{:else if s?.correcting}` with a fully custom combobox.

**State additions to `RowState`:** `comboQuery: string`, `comboOpen: boolean`, `comboHighlight: number` (index into filteredCandidates; `filteredCandidates.length` = "Add new person" sentinel).

**`comboOutsideClick` Svelte action:** registered on the container `<div>`; uses an internal `$effect` to add/remove a `document` click listener that closes the dropdown when the click target is outside the container.

**Combobox structure:**
- Container `<div style="position: relative; width: 100%;">` with `use:comboOutsideClick`
- `<input role="combobox" aria-expanded aria-haspopup="listbox" aria-controls aria-autocomplete="list" aria-label="Search for speaker" placeholder="Type to search…">` — styled per UI-SPEC (bg `#0f1117`, border `1px solid #93c5fd`, radius 6px, padding `6px 10px`, 16px text, `#e2e8f0`)
- `{#if s.comboOpen}` → `<ul role="listbox" id={comboId}>` (absolute, top 100%, full width, bg `#1e293b`, border `#334155`, radius 6px, max-height 240px, z-index 10)
- `{#each filteredCandidates}` → `<li role="option" aria-selected={false}>` with hover/keyboard highlight (`#334155` bg when highlighted, else `#1e293b`)
- "Add new person" `<li>` always last, color `#93c5fd`, 14px, calls `handleSelectPerson(rowKey, '__add_new__')`

**Filter:** `{@const filteredCandidates = candidates.filter(c => text.toLowerCase().includes(query.toLowerCase()))}` — case-insensitive contains on `full_name + role_name`.

**Keyboard:** Up/Down moves highlight, Enter selects highlighted item (or "Add new person"), Escape clears query and closes dropdown.

**Behavior:** `handleSelectPerson` and `getRowCandidates` functions are unchanged. `AddNewPersonForm` block is unchanged and still renders below the combobox when `s.addingPerson` is true.

---

## Deviations from Plan

### Auto-fixed Issues

None.

### Notes

1. `filteredCandidates` is computed as a `{@const}` block inside the `{#each}` loop (not a top-level `$derived`) because candidates are scoped per row and there is no stable per-row `$derived` anchor outside the template. This is idiomatic for per-row data in a Svelte `{#each}` loop.

2. The `comboOutsideClick` action uses an internal `$effect` to register the document listener within the Svelte reactivity lifecycle, ensuring cleanup runs correctly when the correcting branch unmounts.

3. `handleSelectPerson` sets `s.correcting = true` after a correction (keeping the correcting UI visible but with a "Corrected" disposition). This pre-existing behavior is unchanged — the combobox closes its dropdown on selection (`s.comboOpen = false`) but does not touch `s.correcting`.

---

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The combobox query string is used only for client-side `.includes` filtering of already-loaded in-memory data (`data.people`). Selection submits a numeric `person_id` through the existing validated resolve action. Matches T-13-05 and T-13-06 dispositions from the plan threat register (both accepted).

---

## Known Stubs

None. Both changes are complete behavioral implementations with no placeholder data or TODO markers.

---

## Self-Check: PASSED

- [x] `app/src/routes/admin/pipeline/[job_id]/+page.svelte` modified and committed
- [x] Commit 7ddc157 exists (Task 1)
- [x] Commit 63118c6 exists (Task 2)
- [x] `grep -c "<datalist"` → 0
- [x] `grep -n 'role="combobox"'` → line 574
- [x] `grep -n 'role="listbox"'` → line 630
- [x] `grep -n 'role="option"'` → lines 650, 671
- [x] `grep -n "lastKnownStep"` → 4 matches (declaration, update, call site, effectiveJob)
- [x] `grep -n "1000"` → line 57 (setInterval delay)
- [x] `grep -c "2500"` → 0
- [x] `npx svelte-check` → 0 errors
- [x] `git diff app/package.json` → empty (no new dependencies)

**Pending:** Task 3 (human-verify checkpoint) — operator must confirm step badge fallback and combobox behavior in a live running app before plan is marked complete.
