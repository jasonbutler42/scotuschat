---
phase: 07-pipeline-runner
plan: 04
subsystem: ui
tags: [sveltekit, svelte5, runes, admin, pipeline, form-actions, multipart, upload]

requires:
  - phase: 07-02
    provides: POST /api/admin/jobs and GET /api/admin/jobs FastAPI endpoints with X-Admin-Token auth

provides:
  - /admin/pipeline start page: two-mode New Run form (URL / file upload) + Recent Runs history table
  - Pipeline Runner nav link in admin layout (replaces disabled span)
  - SvelteKit form action that creates a job via FastAPI and redirects to per-job status page

affects:
  - 07-05 (job status page uses pipeline/+page.server.ts patterns and shared UI tokens)
  - Phase 8 (People Editor nav item remains disabled — same layout pattern)

tech-stack:
  added: []
  patterns:
    - SvelteKit multipart form action forwarding file bytes to FastAPI (no DO_SPACES_* in frontend)
    - Svelte 5 Runes state machine for mode toggle (aria-pressed, conditional input rendering)
    - StatusBadge inline style helper function mapping job status to UI-SPEC color tokens
    - Hidden form field carries active mode so server action can branch without JS detection

key-files:
  created:
    - app/src/routes/admin/pipeline/+page.server.ts
    - app/src/routes/admin/pipeline/+page.svelte
  modified:
    - app/src/routes/admin/+layout.svelte

key-decisions:
  - "DO_SPACES_* / AWS_* env vars belong to the FastAPI service only in DO App Platform — SvelteKit forwards raw bytes and needs none of these credentials; boto3 is Python-only"
  - "BODY_SIZE_LIMIT=10M must be set in DO App Platform env for SvelteKit to accept real SCOTUS PDFs past the 512 KB default (documented blocker in STATE.md)"
  - "enctype=multipart/form-data on the form for both modes — safe for URL mode and required for file mode; avoids conditional enctype logic"
  - "Only the active mode input (URL or file) is rendered in the DOM so inactive fields are never submitted"

patterns-established:
  - "Svelte 5 mode toggle: $state rune + type=button buttons + aria-pressed + conditional {#if} for input rendering"
  - "StatusBadge as inline style helper function (no component file) mapping status string to UI-SPEC color tokens"
  - "SvelteKit file upload action: read File from formData, forward to FastAPI FormData body, no Content-Type override"

requirements-completed: [PIPE-12, PIPE-13]

duration: 15min
completed: 2026-06-16
---

# Phase 07 Plan 04: Pipeline Runner Start Page Summary

**Two-mode /admin/pipeline start page (URL + file upload) with SvelteKit form actions, Recent Runs history table, and StatusBadge components; Pipeline Runner nav link now live**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-16T19:15:00Z
- **Completed:** 2026-06-16T19:18:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Pipeline Runner nav link activated in admin layout — was a disabled span, now a real anchor to /admin/pipeline
- /admin/pipeline start page server wired: load fetches GET /api/admin/jobs with X-Admin-Token; action branches on mode (url/upload) and posts to POST /api/admin/jobs, redirecting to /admin/pipeline/{id} on success
- Start page UI built in Svelte 5 Runes: ModeToggle (aria-pressed, conditional input rendering), multipart form, Start Run button with real disabled attribute, StatusBadge per UI-SPEC color map, HistoryTable with empty state
- svelte-check passes with 0 errors (5 pre-existing warnings in unrelated files)

## Task Commits

1. **Task 1: Pipeline Runner nav link + start-page server load and create-job action** - `5fc41e3` (feat)
2. **Task 2: Start-page UI — mode toggle, inputs, Start Run, and Recent Runs history table** - `fb75edd` (feat)

## Files Created/Modified

- `app/src/routes/admin/+layout.svelte` - Pipeline Runner disabled span replaced with `<a href="/admin/pipeline">`; People Editor span unchanged (Phase 8)
- `app/src/routes/admin/pipeline/+page.server.ts` - load (GET /api/admin/jobs → jobs array) + default action (branch on mode, POST /api/admin/jobs, throw redirect 303 or return fail 400)
- `app/src/routes/admin/pipeline/+page.svelte` - ModeToggle, URL input, file input, Start Run button, form error, HistoryTable, empty state; all Svelte 5 Runes

## Decisions Made

- **DO_SPACES_* / AWS_* env vars in SvelteKit:** Not needed. SvelteKit forwards raw file bytes to FastAPI via multipart FormData. FastAPI (boto3, Python) performs the actual Spaces upload. Keeping these credentials off the SvelteKit service reduces attack surface and respects the tier boundary (Decision [07-01] confirmed).

- **BODY_SIZE_LIMIT=10M (documented blocker):** SvelteKit's default 512 KB request body limit will reject real SCOTUS PDF uploads. The `BODY_SIZE_LIMIT=10M` env var must be set in DO App Platform on the SvelteKit service before upload mode can be used in production. Noted in STATE.md blockers section.

- **enctype=multipart/form-data on form for both modes:** Using a single form with `enctype=multipart/form-data` regardless of mode simplifies the action — no conditional enctype manipulation needed. URL string submissions work fine with multipart.

- **Only active input rendered in DOM:** `{#if mode === 'url'}` / `{:else}` ensures the inactive field is never submitted, preventing empty `pdf_url=""` or empty `pdf_file` from crossing the server boundary unexpectedly.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Threat Model Coverage

| Threat | Status |
|--------|--------|
| T-07-11 Unauthenticated access to /admin/pipeline | Mitigated — hooks.server.ts session guard (Phase 6) protects all /admin/* routes |
| T-07-12 Missing X-Admin-Token on SvelteKit→FastAPI | Mitigated — every fetch in +page.server.ts sends `X-Admin-Token: ADMIN_TOKEN` |
| T-07-13 FastAPI error detail leaking to operator | Accepted — action returns generic "Could not start the run" message; FastAPI body not surfaced |
| T-07-14 Oversized PDF upload DoS | Accepted — single trusted operator; BODY_SIZE_LIMIT=10M caps payload; not public-facing |

## Known Stubs

None — all data paths are wired to real FastAPI endpoints (GET /api/admin/jobs, POST /api/admin/jobs). The history table displays live job data from the load function.

## User Setup Required

**BODY_SIZE_LIMIT env var required before file upload mode works in production:**

Add to the SvelteKit service in DO App Platform:
```
BODY_SIZE_LIMIT=10M
```

Without this, the SvelteKit runtime will reject PDF uploads larger than ~512 KB with a 413 error before the action runs.

## Next Phase Readiness

- /admin/pipeline start page is complete and ready for operator use
- Plan 05 (job status page at /admin/pipeline/[job_id]) can now be built — it uses the same layout tokens, server patterns, and UI-SPEC contract
- People Editor nav item remains disabled — Phase 8 will activate it following the same pattern used here

---
*Phase: 07-pipeline-runner*
*Completed: 2026-06-16*
