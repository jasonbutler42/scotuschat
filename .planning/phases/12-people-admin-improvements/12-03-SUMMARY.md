---
phase: 12-people-admin-improvements
plan: "03"
subsystem: frontend-server
tags: [people, merge, delete, photo, sveltekit, server-actions, proxy]
status: complete

dependency_graph:
  requires:
    - POST /api/admin/people/{person_id}/photo — Plan 02
    - GET /api/admin/people/{person_id}/merge-preview — Plan 02
    - POST /api/admin/people/{person_id}/merge — Plan 02
    - DELETE /api/admin/people/{person_id} — Plan 02
  provides:
    - extended load (merge picker list, can_delete, delete_block_count, photo_url_full)
    - photo named action (?/photo) — multipart forward to FastAPI
    - merge named action (?/merge) — JSON POST to FastAPI, redirect to target
    - delete named action (?/delete) — DELETE to FastAPI, redirect to /admin/people
    - GET /admin/people/[id]/merge-preview proxy — injects ADMIN_TOKEN server-side
  affects:
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/merge-preview/+server.ts

tech_stack:
  added: []
  patterns:
    - people list fetched once and reused for both roles dedup AND merge picker
    - photo_url_full reconstructed server-side by prepending FASTAPI_BASE_URL to relative paths
    - multipart forwarding via FormData with no manual Content-Type header (Pitfall 4 avoidance)
    - can_delete + delete_block_count derived from merge-preview?target_id=0 in load
    - photo_url removed from save action JSON body (Pitfall 7 avoidance)
    - same-origin +server.ts proxy for ADMIN_TOKEN injection
    - $env/static/private for all server-only env vars (never PUBLIC_)

key_files:
  created:
    - app/src/routes/admin/people/[id]/merge-preview/+server.ts
  modified:
    - app/src/routes/admin/people/[id]/+page.server.ts

decisions:
  - "People list fetched once in load; filtered for merge picker (current person excluded) and deduped for roles dropdown — avoids a second round-trip"
  - "can_delete derived server-side from merge-preview?target_id=0 — FastAPI ignores target_id for counts (D-09 confirmed); client disabled state is defense-in-depth only (D-06)"
  - "photo_url_full constructed in load by prepending FASTAPI_BASE_URL to relative /uploads/… paths — client receives a fully-qualified URL without needing a public env var (Pitfall 5)"
  - "photo action passes only X-Admin-Token header to fetch; no Content-Type set — Node fetch adds the multipart boundary automatically (Pitfall 4)"
  - "save action JSON body no longer includes photo_url — photo is exclusively managed by the photo action to prevent a save from silently nulling a previously-uploaded photo (Pitfall 7)"
  - "merge action redirects to /admin/people/{target_id} after success — source no longer exists post-merge (D-11)"
  - "delete action redirects to /admin/people after success (D-07); 409 returns deleteError with friendly message"
  - "merge-preview +server.ts proxy imports ADMIN_TOKEN from $env/static/private; JSON response returned without the token (T-12-TOKENLEAK)"

metrics:
  duration_minutes: 8
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_changed: 2
---

# Phase 12 Plan 03: SvelteKit Server Layer Summary

**One-liner:** Extended load (merge picker, can_delete, photo_url_full) plus photo/merge/delete named actions and a token-injecting merge-preview proxy, all keeping ADMIN_TOKEN and FASTAPI_BASE_URL server-only.

## What Was Built

This plan provides every SvelteKit server entry point the Plan 04 Svelte component will bind to. Two files were modified/created — no new packages required.

### app/src/routes/admin/people/[id]/+page.server.ts — load extension + 3 new actions

**Load extension:**
- The existing people-list fetch (used for roles dedup) is now reused to also build the merge picker list. `people` is filtered to exclude `params.id` and returned to the page.
- `merge-preview?target_id=0` fetched after loading person detail to derive `can_delete` (all four FK counts equal zero) and `delete_block_count` (sum of the four counts). Degrades gracefully on network failure (can_delete defaults to false — safe).
- `person.photo_url_full` computed server-side: if `photo_url` starts with `/` (local relative path), prepend `FASTAPI_BASE_URL`; otherwise pass through as-is. Client always receives a fully-qualified URL.
- Returns: `{ person, roles, people, can_delete, delete_block_count }`.

**photo action:**
- Reads `photo_file` (File) and `photo_url` (string) from form data.
- Builds a new `FormData`; appends only the non-empty fields.
- POSTs to `FASTAPI_BASE_URL/api/admin/people/{id}/photo` with `X-Admin-Token` header only — no `Content-Type` (Node fetch sets the multipart boundary automatically, Pitfall 4).
- 422 → `fail(422, { photoError: '...' })`; network error or other non-OK → `fail(502, { photoError: '...' })`.
- On success: `redirect(303, /admin/people/{id})`.

**merge action:**
- Reads `target_id` from form data; returns `fail(400, { mergeError: ... })` if absent.
- POSTs `{ target_id: parseInt(...) }` as JSON to `FASTAPI_BASE_URL/api/admin/people/{id}/merge`.
- On non-OK: parses FastAPI `detail` field; returns `fail(422 | 502, { mergeError: ... })`.
- On success: `redirect(303, /admin/people/{target_id})` — source no longer exists (D-11).

**delete action:**
- DELETEs `FASTAPI_BASE_URL/api/admin/people/{id}` with `X-Admin-Token`.
- 409 → `fail(409, { deleteError: 'This person cannot be deleted — they have associated records.' })`.
- Other non-OK → `fail(502, { deleteError: '...' })`.
- On success: `redirect(303, /admin/people)` (D-07).

**save action change:**
- `photo_url` removed from the `JSON.stringify({...})` PATCH body. The backend leaves `photo_url` untouched when the key is absent from the request body. This prevents a save operation from silently nulling a previously-uploaded photo (Pitfall 7).

### app/src/routes/admin/people/[id]/merge-preview/+server.ts — NEW proxy route

- Exports `GET: RequestHandler`.
- Reads `target_id` from `url.searchParams`; returns `error(400, 'target_id is required')` when absent.
- Proxies to `FASTAPI_BASE_URL/api/admin/people/{id}/merge-preview?target_id={n}` with `X-Admin-Token: ADMIN_TOKEN` injected server-side.
- Returns `json(await res.json())` — the browser receives `{ utterances, aliases, appearances, argument_participants }` with no token visible.
- `ADMIN_TOKEN` and `FASTAPI_BASE_URL` imported exclusively from `$env/static/private` (T-12-TOKENLEAK mitigated).

## Deviations from Plan

None — plan executed exactly as written.

All threat mitigations verified:
- T-12-TOKENLEAK: ADMIN_TOKEN imported from `$env/static/private` only; proxy returns counts without token
- T-12-MULTIPART: photo action passes no Content-Type header; Node fetch sets multipart boundary (Pitfall 4)
- T-12-PHOTOCLEAR: save action JSON body excludes `photo_url` (Pitfall 7)
- T-12-SELF: merge action surfaces 422 from FastAPI with `detail` message
- T-12-ORPHAN: delete action surfaces 409 from FastAPI; load-derived `can_delete` is defense-in-depth

## Known Stubs

None. All returned values (`person`, `people`, `can_delete`, `delete_block_count`, `person.photo_url_full`) are populated from live FastAPI responses. The merge-preview proxy returns live counts from the database.

## Threat Flags

No new threat surface beyond the plan's threat model. All five threat entries (T-12-TOKENLEAK, T-12-MULTIPART, T-12-PHOTOCLEAR, T-12-SELF, T-12-ORPHAN) have mitigations implemented in this plan's code.

## Self-Check

- [x] `app/src/routes/admin/people/[id]/+page.server.ts` — FOUND
- [x] `app/src/routes/admin/people/[id]/merge-preview/+server.ts` — FOUND
- [x] Commit `6b008df` — FOUND (feat(12-03): extend load + add photo/merge/delete actions)
- [x] Commit `3d2b866` — FOUND (feat(12-03): add merge-preview proxy +server.ts route)
- [x] `photo_url` absent from save action `JSON.stringify` body — VERIFIED
- [x] `photo` action fetch has no `Content-Type` header — VERIFIED
- [x] ADMIN_TOKEN imported from `$env/static/private` in merge-preview +server.ts — VERIFIED
- [x] TypeScript: no errors for either file — VERIFIED (npx tsc --noEmit exits 0)

## Self-Check: PASSED

All artifacts confirmed present and verified.

Commits:
- 6b008df: feat(12-03): extend load + add photo/merge/delete actions to people [id] server
- 3d2b866: feat(12-03): add merge-preview proxy +server.ts route
