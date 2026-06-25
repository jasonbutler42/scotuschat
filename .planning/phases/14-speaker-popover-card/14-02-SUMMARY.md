---
phase: 14-speaker-popover-card
plan: "02"
subsystem: frontend
tags:
  - sveltekit
  - bits-ui
  - speakers
  - popover
  - server-load
dependency_graph:
  requires:
    - api/routers/arguments.py (GET /arguments/{id}/speakers — Plan 01)
    - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts (argument page load)
  provides:
    - bits-ui@^2.18.1 in app/package.json dependencies
    - speakers array with photo_url_full returned by argument page load function
  affects:
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte (Plan 03 consumes speakers)
tech_stack:
  added:
    - bits-ui@^2.18.1 (headless Svelte 5 UI primitives, runtime dependency)
  patterns:
    - Server-side photo_url_full reconstruction (mirrors admin/people/[id]/+page.server.ts lines 74–79)
    - Graceful degradation — speakers fetch failure returns [] without breaking argument page
    - Plain array return (not Map) — SvelteKit Map serialization pitfall avoided
key_files:
  created: []
  modified:
    - app/package.json (bits-ui added to dependencies)
    - app/package-lock.json (lockfile updated)
    - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts (speakers fetch + photo_url_full)
decisions:
  - "FASTAPI_BASE_URL never sent to client — photo_url_full reconstructed server-side before return (T-14-04 mitigated)"
  - "Speakers fetch degrades to [] on non-OK or network error — argument page must not break if endpoint fails"
  - "speakers returned as plain array — SvelteKit serializes Map as {} (Pitfall 2); Plan 03 +page.svelte builds Map via $derived"
  - "bits-ui installed as runtime dependency (not devDependency) — it is imported by Svelte components at runtime"
metrics:
  duration_minutes: 6
  completed_date: "2026-06-25"
  tasks_completed: 2
  files_changed: 3
status: complete
requirements:
  - PUB-01
  - PUB-03
---

# Phase 14 Plan 02: bits-ui Install + Speakers Server Load Summary

**One-liner:** bits-ui@^2.18.1 installed as runtime dependency and argument page load extended to fetch /arguments/{id}/speakers with server-side photo_url_full reconstruction.

## What Was Built

Two tasks prepare the frontend foundation for the speaker popover card:

1. **app/package.json** — `bits-ui@^2.18.1` added to the `dependencies` section (not devDependencies — bits-ui is imported by Svelte components at runtime). npm install populated `app/node_modules/bits-ui/` with 14 packages.

2. **app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts** — Load function extended with a second fetch to `${FASTAPI_BASE_URL}/arguments/${params.id}/speakers`. Key behaviors:
   - Non-OK response or network error degrades gracefully to `speakers: []` — the argument page still loads
   - `photo_url_full` reconstructed for each speaker: relative paths (`/`) prepend `FASTAPI_BASE_URL`; absolute URLs pass through; null maps to null
   - `is_bench` derived from `tenure.length > 0`
   - Returns plain array (not Map) — SvelteKit serializes Map as `{}` (Pitfall 2)
   - `FASTAPI_BASE_URL` is `$env/static/private` — never a `PUBLIC_` variable; the URL string itself is not included in the serialized `speakers` array

## Verification Results

All checks passed:

1. `node -e "... p.dependencies['bits-ui']"` → `^2.18.1`
2. `node -e "... s.includes('/speakers'), s.includes('photo_url_full'), !s.includes('PUBLIC_')"` → `true true true`
3. `npm run check` → 0 errors, 14 warnings (all pre-existing, unrelated to Plan 02 changes)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 8fc1a42 | chore(14-02): install bits-ui@^2.18.1 |
| Task 2 | 96e5b2e | feat(14-02): extend argument page load to fetch speakers with photo_url_full |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-14-04 | Mitigated — `photo_url_full` is the only URL sent to client; `FASTAPI_BASE_URL` string is not in the `speakers` array; `FASTAPI_BASE_URL` is `$env/static/private` (tree-shaken from client bundle) |
| T-14-05 | Mitigated — bits-ui package legitimacy verified in RESEARCH.md audit (OK verdict); version constraint `^2.18.1` enforced; no postinstall script warnings during install |

## Known Stubs

None — this plan installs a package and wires server-side data. No UI rendering, no placeholder data. The `speakers` array flows to Plan 03 for popover UI.

## Threat Flags

None — no new network endpoints; no schema changes; `FASTAPI_BASE_URL` remains server-side only.

## Self-Check: PASSED

- [x] app/package.json contains `"bits-ui": "^2.18.1"` in dependencies
- [x] app/node_modules/bits-ui/ exists
- [x] +page.server.ts fetches `/speakers` endpoint
- [x] +page.server.ts computes `photo_url_full` for each speaker
- [x] +page.server.ts does NOT contain `PUBLIC_FASTAPI_BASE_URL`
- [x] +page.server.ts returns `speakers` as plain array
- [x] Commit 8fc1a42 exists
- [x] Commit 96e5b2e exists
- [x] svelte-check: 0 errors
