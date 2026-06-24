---
phase: 12-people-admin-improvements
plan: "06"
subsystem: frontend
tags: [gap-fix, bio-save, delete-eligibility, photo-action]
status: complete

dependency_graph:
  requires: [12-05]
  provides: [bio-only-save, alias-safe-delete-frontend]
  affects:
    - app/src/routes/admin/people/[id]/+page.server.ts

tech_stack:
  added: []
  patterns: [early-return-guard, eligibility-condition-trim]

key_files:
  modified:
    - app/src/routes/admin/people/[id]/+page.server.ts

decisions:
  - Bio-only save redirects immediately after bio PATCH — no FastAPI photo call when outForm is empty (Gap C closed)
  - Aliases removed from can_delete and delete_block_count — backend deletes them before orphan check, frontend must match (Gap D closed)

metrics:
  duration_minutes: 3
  completed_date: "2026-06-24"
  tasks_completed: 2
  files_modified: 1
---

# Phase 12 Plan 06: Gap Fix — Bio Save Independence + Delete Eligibility Summary

**One-liner:** Closes Gap C (bio-only save no longer triggers a 422 photo call) and Gap D (alias-only persons now show the delete button enabled, matching the backend's Plan 05 fix).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Skip FastAPI photo upload when only bio text is saved | 4e236ec |
| 2 | Remove aliases from can_delete / delete_block_count | 2b4d9b2 |

## What Was Built

### Task 1 — Bio-only save (Gap C)

**File:** `app/src/routes/admin/people/[id]/+page.server.ts`

Added an early-return guard immediately after `outForm` construction and before `let res: Response;` in the `photo` action:

```typescript
// If neither a file nor a URL was provided, bio-only save — skip photo upload
if (!outForm.has('photo_file') && !outForm.has('photo_url')) {
    throw redirect(303, '/admin/people/' + params.id);
}
```

The bio PATCH still runs unconditionally before this check — only the FastAPI photo POST is skipped. The redirect re-runs the load function, returning fresh data exactly as the full photo-save path does.

**Root cause closed:** `outForm` was always POSTed to FastAPI even when empty. FastAPI's `upload_person_photo` requires at least one of `photo_file` or `photo_url` and returned 422 when both were absent. The guard prevents the call entirely.

### Task 2 — Delete eligibility fix (Gap D)

**File:** `app/src/routes/admin/people/[id]/+page.server.ts`

Removed `counts.aliases` from both the `can_delete` condition and `delete_block_count`:

Before:
```typescript
const total = counts.utterances + counts.aliases + counts.appearances + counts.argument_participants;
can_delete = counts.utterances === 0 && counts.aliases === 0 && counts.appearances === 0 && counts.argument_participants === 0;
delete_block_count = total;
```

After:
```typescript
can_delete = counts.utterances === 0 && counts.appearances === 0 && counts.argument_participants === 0;
delete_block_count = counts.utterances + counts.appearances + counts.argument_participants;
```

**Root cause closed:** Plan 05 (backend) deletes aliases before the orphan check, so alias count no longer blocks deletion. The frontend condition must match — alias-only persons (aliases > 0, all others = 0) now correctly show `can_delete = true`.

## Deviations from Plan

None — plan executed exactly as written. Both fixes matched the plan's code snippets precisely.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. Changes are purely frontend logic within the existing admin-authenticated action.

## Self-Check: PASSED

- Early-return guard present: `grep -n "outForm.has" +page.server.ts` shows guard at lines 292-293
- `counts.aliases` absent from `can_delete`: `grep -n "can_delete\|aliases" +page.server.ts` shows no `counts.aliases` in the condition block
- Commit `4e236ec` — confirmed (Task 1)
- Commit `2b4d9b2` — confirmed (Task 2)
