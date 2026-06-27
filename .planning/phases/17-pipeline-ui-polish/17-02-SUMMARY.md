---
phase: 17-pipeline-ui-polish
plan: "02"
subsystem: frontend
status: checkpoint
tags: [frontend, svelte, proxy, admin-pipeline, pdf-serving, typescript]
dependency_graph:
  requires: [17-01-PLAN.md (AdminJobResponse.original_filename + parse_stats + GET /api/admin/jobs/{job_id}/pdf)]
  provides: [pdf proxy +server.ts, ParseStats interface, extended Job interface, formatDate(), template additions pending human-verify]
  affects: [app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts, app/src/routes/admin/pipeline/[job_id]/+page.svelte]
tech_stack:
  added: []
  patterns: [same-origin-proxy, redirect-manual, stream-body, $env/static/private, svelte5-runes-conditional]
key_files:
  created:
    - app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
decisions:
  - "PDF proxy uses redirect:'manual' to pass FastAPI 302 (Spaces pre-signed URL) through to the browser without the token transiting SvelteKit"
  - "Opaque redirect fallback: re-fetch with redirect:'follow' and stream body when Location header is unreadable (CORS-mode fetch behavior)"
  - "formatDate() declared as script-level function (not {@const}) to be accessible from the {#each STEP_ORDER} loop scope (Pitfall 5)"
  - "ParseStats interface mirrors 17-01 Pydantic model field names exactly: utterance_count / speaker_count (not utterances/speakers)"
metrics:
  duration_minutes: 2
  completed: "2026-06-27"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 2
---

# Phase 17 Plan 02: Frontend Pipeline UI Polish Summary

SvelteKit PDF proxy route and Job interface extensions for pipeline admin polish: same-origin PDF proxy that keeps ADMIN_TOKEN server-side, and type-safe additions to the job detail page script block.

## What Was Built

### Task 1: SvelteKit PDF proxy route +server.ts

Created `app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts` exporting a typed `GET: RequestHandler`:

- Imports `ADMIN_TOKEN` and `FASTAPI_BASE_URL` exclusively from `$env/static/private` (T-17-TOKENLEAK)
- Fetches FastAPI server-side with `redirect: 'manual'` and `X-Admin-Token` header
- Handles readable 302 (Spaces case): extracts `Location` header, returns same-origin `302` to browser — pre-signed Spaces URL lands in address bar without token
- Handles opaque redirect (status 0): re-fetches with `redirect: 'follow'` and streams the resolved response body
- Handles 200 FileResponse (disk case): streams `res.body` via `new Response(res.body, {...})` — no buffering
- Non-OK/non-redirect: throws `error(404|502, 'Source PDF not available')`
- Auth guard inherited from `hooks.server.ts` (all `/admin/*` including `+server.ts` endpoints protected)
- Token never echoed to any response header or body

### Task 2: Extend Job interface + add standalone formatDate() in +page.svelte

Added to `<script lang="ts">` block of `+page.svelte`:

- `ParseStats` interface: `utterance_count: number; speaker_count: number;` (mirrors 17-01 Pydantic model)
- Extended `Job` interface with: `pdf_url?: string | null`, `spaces_key?: string | null`, `original_filename?: string | null`, `parse_stats?: ParseStats | null` — so `data.job.*` type-checks (Pitfall 4)
- Script-level `function formatDate(iso: string | null | undefined): string` using `toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })` with `'—'` fallback — accessible from `{#each STEP_ORDER}` loop scope (Pitfall 5)
- Pre-existing `{@const formatArgDate}` inside `{#if data.argument}` untouched

### Task 3: Template additions (PENDING human-verify checkpoint)

Task 3 (Ingest source row, Parse stat rows, View source PDF link card) was not executed — plan reaches a `checkpoint:human-verify` gate. Template additions will be implemented after the operator approves the checkpoint.

## Decisions Made

- `redirect: 'manual'` is mandatory so a FastAPI 302 is not followed server-side — the pre-signed Spaces URL goes directly to the browser (keeps PDF bytes off SvelteKit, acceptable per 17-RESEARCH Security Domain)
- Opaque redirect fallback re-fetches with `redirect: 'follow'` rather than erroring — necessary because some fetch environments produce `type: 'opaqueredirect'` where Location is unreadable
- `formatDate` is a script-level function (not `{@const}`) because `{@const}` declarations inside `{#if}` blocks are scoped to that block and are not accessible from sibling `{#each}` loops

## Deviations from Plan

None — Tasks 1 and 2 executed exactly as specified. Task 3 is held at its checkpoint gate.

## Threat Surface Scan

- T-17-TOKENLEAK: mitigated — `ADMIN_TOKEN` imported only from `$env/static/private`; injected into server-side fetch header; never written to a response header/body; anchor in Task 3 targets same-origin proxy, not FastAPI directly
- T-17-AUTHZ: mitigated — route lives under `/admin/*`; `hooks.server.ts` guards every `/admin/*` request before the handler runs
- T-17-OPENREDIRECT: mitigated — `Location` value sourced from FastAPI's own response (server-controlled pre-signed Spaces URL), never from a client-supplied query param
- T-17-PRESIGN: accepted — URL visible to operator only, admin-only flow, 15-minute TTL (inherited from 17-01)
- T-17-XSS: Task 3 pending; when implemented, Svelte auto-escapes interpolated text (`{...}`) so filename/URL rendered as text content, not unsanitized HTML

## Self-Check

- [x] `app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts` exists
- [x] Exports `GET: RequestHandler` typed from `./$types`
- [x] Imports from `$env/static/private` only
- [x] `redirect: 'manual'` on FastAPI fetch
- [x] `res.body` streamed (not buffered) in disk case
- [x] Token never appears in any returned header or body
- [x] `ParseStats` interface: `utterance_count: number`, `speaker_count: number`
- [x] `Job` interface extended with all four optional fields
- [x] `function formatDate(...)` declared at script top level (not inside any `{#if}/{#each}/{@const}`)
- [x] `formatArgDate` {@const} untouched
- [x] `npx tsc --noEmit` clean for both modified files
- [x] Commits present: c0c8b2c2 (Task 1), de2dc848 (Task 2)

## Self-Check: PASSED
