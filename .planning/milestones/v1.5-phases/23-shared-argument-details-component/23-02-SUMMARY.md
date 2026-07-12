---
phase: 23-shared-argument-details-component
plan: "02"
subsystem: frontend/components
tags: [svelte5, runes, form, pill-input, component, admin-ui]
status: complete

dependency_graph:
  requires:
    - "23-01-PLAN.md (backend API: ParseStats, ArgumentDetail, MetadataUpdate schemas)"
  provides:
    - "app/src/lib/components/ArgumentDetailsCard.svelte — reusable argument details form component"
  affects:
    - "23-03-PLAN.md (wiring component into pipeline job detail page)"
    - "Phase 26 (argument edit page consumer — plug-in via action prop)"

tech_stack:
  added: []
  patterns:
    - "Svelte 5 Runes: $props, $state, $effect (no export let, no $:, no legacy stores)"
    - "use:enhance with saving state; update({reset:false}) on success to preserve $state"
    - "Hidden input per pill (name='docket[]') — server reads FormData.getAll('docket[]')"
    - "$effect restores pill state from form.dockets on failed save (not from savedValues)"
    - "Always-visible hint rows — never conditionally hidden"

key_files:
  created:
    - "app/src/lib/components/ArgumentDetailsCard.svelte"
  modified: []

decisions:
  - "D-01 implemented: action prop drives form target; identical component on both consumers"
  - "D-04/D-05: Enter-to-add docket pill, hidden inputs per pill"
  - "D-06: $effect restores pills from form.dockets on failed save"
  - "D-07/D-08/D-09: always-visible extracted hints with 'Extracted:' prefix; docket hints as read-only pills"
  - "Pitfall 2 guard: e.preventDefault() before addPill() on Enter keydown"
  - "Pitfall 4 guard: update({reset:false}) on success prevents $state wipe"

metrics:
  duration_minutes: 2
  completed_date: "2026-07-02"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 23 Plan 02: Shared Argument Details Component (Component Build) Summary

**One-liner:** Reusable `ArgumentDetailsCard.svelte` with docket pill input, free-text question number, argued date, always-visible extracted hints, and action-prop-driven form — built in Svelte 5 Runes exclusively.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ArgumentDetailsCard.svelte with props, pill state, and form mechanics | bb9bdcf8 | app/src/lib/components/ArgumentDetailsCard.svelte |

## What Was Built

A self-contained, purely presentational Svelte 5 component implementing the full UI-SPEC contract for the argument details form:

### Component Structure

**Props contract (`ArgumentDetailsCardProps`):**
- `savedValues: { dockets: string[]; question_number: string; argued_date: string | null }` — operator-confirmed values from the DB
- `hints: { dockets: string[]; question_number: string | null; argued_date: string | null; case_name: string | null }` — raw extraction output from `cover_metadata`
- `action: string` — SvelteKit form action string (e.g., `?/saveJobMetadata`)
- `readonly?: boolean` — disables all inputs and hides × buttons and save button (AEDIT-04)
- `form?: { dockets?: string[]; saveError?: string; saved?: boolean } | null` — server form response

**Internal state (Svelte 5 `$state` only):**
- `pills: string[]` — initialized from `savedValues.dockets`; restored from `form.dockets` on failed save (D-06)
- `docketInput: string` — controlled value cleared on each successful pill add
- `saving: boolean` — set true on submit, false in enhance callback

### Key Interaction Mechanics

**Docket pill/tag system (PJOB-05/D-04/D-05):**
- Operator types docket and presses Enter → `addPill()` called after `e.preventDefault()` (Pitfall 2 guard)
- Silent reject for empty strings and duplicate values
- Each pill renders with ×  remove button (`aria-label="Remove docket {value}"`, 28×28px min touch)
- Each pill serializes as `<input type="hidden" name="docket[]">` — server reads `FormData.getAll('docket[]')`

**Failed save restore (D-06):**
- `$effect(() => { if (form?.dockets) { pills = form.dockets; } })` — only restore path
- Does NOT re-derive from `savedValues` (which would reflect the old saved state, not the operator's unsaved edits)

**Form enhancement (Pattern 2):**
- `use:enhance` sets `saving = true` on submit
- On failure: `await update()` (triggers SvelteKit to apply form response without resetting)
- On success: `await update({ reset: false })` — mandatory to prevent Svelte resetting pill `$state` (Pitfall 4 guard)

### Always-Visible Extracted Hints (PJOB-04/D-07/D-08/D-09)

Below each editable field, a hint row renders unconditionally:
- Docket hints: read-only pills (12px, `#94a3b8`, `#0f1117` background, no × button, 24px height) prefixed "Extracted:"
- When `hints.dockets` is empty: italic "N/A" text
- Question number / argued date: `"Extracted: {value ?? 'N/A'}"` — italic when null (D-08)
- Hint rows are NEVER conditionally hidden — even when the operator has filled the field

### Readonly Mode (AEDIT-04)

When `readonly={true}`:
- All inputs have `disabled` attribute
- Pill × buttons are not rendered
- Save button is not rendered
- All hint rows still render (operator retains historic extraction view)

### Visual Contract Compliance

| Element | Spec | Implemented |
|---------|------|-------------|
| Card bg | `#1e293b`, 1px `#334155`, radius 8px, padding 24px | Yes |
| Heading | "Argument Details", 20px/600 | Yes (PJOB-03) |
| Inputs | `#0f1117` bg, `#334155` border, radius 6px, 8px 12px padding, 16px, `#e2e8f0` | Yes |
| Hint text | 14px/400, `#94a3b8`, `margin-top: 4px` | Yes |
| Hint N/A | italic in addition to muted color | Yes |
| Editable pill | `#1e293b`, `#334155` border, radius 4px, 14px `#e2e8f0` | Yes |
| × button | `#94a3b8`, hover `#ef4444`, min 28×28px touch | Yes |
| Hint pills | `#0f1117`, `#334155` border, radius 4px, 12px `#94a3b8`, 24px height | Yes |
| Save button | full width, 44px min-height, `#93c5fd` border, "Saving…" + opacity 0.7 when saving | Yes |
| Success | "Saved." in `#4ade80` | Yes |
| Error | `role="alert"`, `#ef4444` | Yes |

## Deviations from Plan

None — plan executed exactly as written. All decisions (D-01 through D-09), pitfall guards (Pitfall 2, Pitfall 4), and UI-SPEC tokens implemented as specified.

## Verification

- `svelte-check --threshold error`: 0 errors, 0 warnings for `ArgumentDetailsCard.svelte`
- Zero legacy Svelte patterns: no `export let`, no `$:`, no `import from 'svelte/store'`
- Component is purely presentational: no data fetching, no server imports
- Accessibility: all inputs have associated `<label for>`, pill × buttons have `aria-label`, error uses `role="alert"`

## Known Stubs

None — component is fully implemented per the plan. It has no data dependencies; all data arrives via props from `+page.server.ts` load (which is wired in Plan 23-03).

## Threat Surface Scan

No new trust boundaries beyond what was identified in the plan's `<threat_model>`. Svelte's auto-escaping of interpolated text (`{pill}`) provides the T-23-02-02 mitigation — no `{@html}` or `innerHTML` usage in the component.

## Self-Check: PASSED

- `app/src/lib/components/ArgumentDetailsCard.svelte` — FOUND
- Commit `bb9bdcf8` — FOUND (`git log --oneline | grep bb9bdcf8`)
