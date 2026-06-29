---
phase: 12-people-admin-improvements
plan: "07"
subsystem: frontend
tags: [gap-fix, bio-card-position, merge-preview, soft-navigation, svelte5-runes]
status: complete

dependency_graph:
  requires: [12-06]
  provides: [bio-photo-card-above-save, merge-preview-reload-fix, merge-state-reset]
  affects:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/merge-preview/+server.ts

tech_stack:
  added: []
  patterns: [html-form-attribute-association, svelte5-effect-reset, cache-control-no-store]

key_files:
  modified:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/merge-preview/+server.ts

decisions:
  - Save Changes button uses HTML form= attribute to associate with save-form without nesting — Gap E closed
  - Merge onchange reads e.target.value directly instead of stale $state variable — Gap F closed
  - Cache-Control no-store on merge-preview proxy prevents browser caching stale counts — Gap F closed
  - $effect tracking data.person.id resets all four merge state variables on soft navigation — Gap G closed

metrics:
  duration_minutes: 8
  completed_date: "2026-06-24"
  tasks_completed: 3
  files_modified: 2
---

# Phase 12 Plan 07: Gap Fix — Bio Card Position + Merge State Summary

**One-liner:** Closes three UAT gaps: Bio & Photo card now renders above Save Changes (HTML form= association), merge preview correctly reloads on second target selection (event.target.value + Cache-Control: no-store), and merge picker resets on SvelteKit soft navigation ($effect reset on person.id change).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Move Save Changes button below Bio & Photo card using form= attribute | 483c5f3 |
| 2 | Fix merge preview reload — read event.target.value, add Cache-Control | 6ec401d |
| 3 | Reset merge state on SvelteKit soft navigation to different person | c578757 |

## What Was Built

### Task 1 — Bio & Photo card position (Gap E)

**File:** `app/src/routes/admin/people/[id]/+page.svelte`

Three coordinated edits:
1. Added `id="save-form"` to the save form opening tag (line 182)
2. Removed the Save Changes button and `{#if form?.error}` block from inside the form — closed the form with only `</form>`
3. Placed the Save Changes button and error block AFTER the Bio & Photo card closing `</div>`, using `form="save-form"` HTML attribute to associate the button with the save form without nesting forms (HTML nesting prohibition)

The Bio & Photo card is now a sibling `<div>` that appears visually between the Appointment section and the Save Changes button.

### Task 2 — Merge preview reload (Gap F)

**File:** `app/src/routes/admin/people/[id]/+page.svelte`

Changed the merge target select's `onchange` handler from:
```svelte
onchange={() => fetchMergePreview(mergeTargetId)}
```
to:
```svelte
onchange={(e) => fetchMergePreview((e.target as HTMLSelectElement).value)}
```

Root cause: In Svelte 5 Runes, `bind:value` and `onchange` both react to the same DOM change event. The `$state` update may not have flushed by the time `onchange` fires, so the second call was passing the stale previous value. Reading from `e.target.value` bypasses this race condition entirely.

**File:** `app/src/routes/admin/people/[id]/merge-preview/+server.ts`

Added `Cache-Control: no-store` header to the `json()` response:
```typescript
return json(await res.json(), { headers: { 'Cache-Control': 'no-store' } });
```

This prevents browsers from serving cached counts when the operator changes the merge target.

### Task 3 — Merge state reset on soft navigation (Gap G)

**File:** `app/src/routes/admin/people/[id]/+page.svelte`

Added a `$effect` block immediately after the merge `$state` declarations:
```typescript
$effect(() => {
    data.person.id;
    mergeTargetId = '';
    mergePreview = null;
    mergeError = null;
    mergeLoading = false;
});
```

Root cause: SvelteKit soft-navigates between `/admin/people/[id]` routes with different `[id]` params by reusing the existing component instance and updating `data`. The `$state` variables were never reset between navigations. The `$effect` tracks `data.person.id` as a dependency — when it changes (new person loaded), the effect body runs and resets all four merge state variables.

## Deviations from Plan

None — all three fixes matched the plan's code snippets exactly.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. All changes are purely frontend reactivity fixes within the existing admin-authenticated UI.

## Self-Check: PASSED

- `grep -n "id=\"save-form\"\|form=\"save-form\""` shows both at lines 182 and 652
- `grep -n "e.target as HTMLSelectElement"` shows fix at line 691 (onchange) and pre-existing at line 51 (handleRoleChange)
- `grep -n "Cache-Control"` shows header in +server.ts at line 42
- `grep -n "data.person.id"` shows $effect at line 126 and merge-preview URL at line 140
- `npx svelte-check`: 0 errors, 11 warnings (all pre-existing)
- Commit 483c5f3 — confirmed (Task 1)
- Commit 6ec401d — confirmed (Task 2)
- Commit c578757 — confirmed (Task 3)
